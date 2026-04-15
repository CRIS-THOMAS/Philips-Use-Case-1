from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Any

from doc_intel_poc.models import DocumentType, Plan, PlanStep, WorkflowState

if TYPE_CHECKING:
    from doc_intel_poc.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lightweight LLM client (optional – falls back to rules)
# ---------------------------------------------------------------------------


class LLMClient:
    """Thin wrapper around OpenAI chat completions.

    If ``OPENAI_API_KEY`` is not set the client stays disabled and the
    planner will use the built-in rule engine instead.
    """

    def __init__(self) -> None:
        self.enabled = False
        self.model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            try:
                import openai  # noqa: F401  (deferred import)

                self._client = openai.OpenAI(api_key=api_key)
                self.enabled = True
            except Exception:
                logger.warning("OpenAI import failed – falling back to rule planner.")

    def generate_plan(
        self,
        goal: str,
        doc_preview: str,
        available_tools: list[dict[str, str]],
        current_state_summary: str,
    ) -> list[dict[str, Any]] | None:
        if not self.enabled:
            return None

        tool_list = "\n".join(
            f"- {t['name']}: {t['description']}" for t in available_tools
        )

        prompt = (
            "You are an intelligent document-processing planner.\n"
            f"Available tools:\n{tool_list}\n\n"
            f"User goal: {goal}\n"
            f"Document preview (first 500 chars):\n{doc_preview[:500]}\n\n"
            f"Current state:\n{current_state_summary}\n\n"
            "Return a JSON array of plan steps. Each step must have:\n"
            '  {"action": "<tool_name>", "reason": "<why>", '
            '"dependencies": ["<prior_action>", ...], "optional": true|false}\n'
            "Only use tools from the available list. Order matters.\n"
            "Respond ONLY with valid JSON, no markdown fences."
        )

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=512,
            )
            text = (response.choices[0].message.content or "").strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
            return json.loads(text)  # type: ignore[no-any-return]
        except Exception as exc:
            logger.warning("LLM plan generation failed: %s", exc)
            return None


# ---------------------------------------------------------------------------
# Hybrid Planner
# ---------------------------------------------------------------------------


class PlannerAgent:
    """Hybrid planner: tries LLM first, falls back to deterministic rules."""

    name = "planner"

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.llm = LLMClient()
        self.registry = registry

    # -- public API ---------------------------------------------------------

    def generate_plan(self, state: WorkflowState) -> Plan:
        """Create (or re-create) the full execution plan."""
        goal = state.goal or "Summarize documents and extract key insights"

        # Try LLM-based planning first
        if self.llm.enabled and self.registry:
            llm_steps = self.llm.generate_plan(
                goal=goal,
                doc_preview=state.combined_text[:500] if state.combined_text else "(not yet read)",
                available_tools=self.registry.describe(),
                current_state_summary=self._state_summary(state),
            )
            if llm_steps:
                plan = Plan(goal=goal)
                for s in llm_steps:
                    plan.steps.append(PlanStep.from_dict(s))
                self._record_plan(state, plan, source="llm")
                return plan

        # Deterministic rule-based plan
        plan = self._rule_plan(state, goal)
        self._record_plan(state, plan, source="rules")
        return plan

    def revise_plan(
        self,
        state: WorkflowState,
        failed_action: str,
        error: str,
    ) -> Plan:
        """Mutate the current plan after a step failure."""
        plan = state.plan or Plan(goal=state.goal)

        # Remove the failed step
        plan.remove_step(failed_action)

        # If reader failed – nothing else can run
        if failed_action == "reader":
            plan.steps = [
                PlanStep(action="summarizer", reason="Produce partial summary from available data."),
            ]
            self._record_plan(state, plan, source="revision-fallback")
            return plan

        # If an optional tool failed, just drop it
        # If a required tool failed, try to insert a fallback
        if failed_action == "analyzer":
            # Skip analysis – go straight to summarizer
            plan.remove_step("keyword_extractor")
            self._record_plan(state, plan, source="revision-skip-analysis")
        elif failed_action == "question_extractor":
            self._record_plan(state, plan, source="revision-skip-questions")

        return plan

    def decide_next(self, state: WorkflowState) -> str | None:
        """Legacy-compatible: return the next action name or None."""
        if state.plan is None:
            state.plan = self.generate_plan(state)

        completed = set(state.completed_agents)
        step = state.plan.next_step(completed)
        if step is None:
            self._trace(state, "stop", "All planned steps completed.")
            return None

        self._trace(state, step.action, step.reason)
        return step.action

    # -- rule engine --------------------------------------------------------

    def _rule_plan(self, state: WorkflowState, goal: str) -> Plan:
        """Generate a deterministic plan based on document type and goal."""
        plan = Plan(goal=goal)
        goal_lower = goal.lower()

        # Step 1: always read
        plan.steps.append(
            PlanStep(action="reader", reason="Parse input files first.")
        )

        # Step 2: analyse
        plan.steps.append(
            PlanStep(
                action="analyzer",
                reason="Compute text statistics for downstream tools.",
                dependencies=["reader"],
            )
        )

        # Adaptive steps based on document type
        doc_type = state.document_type

        # Keyword extraction – useful for reports and data sheets
        if doc_type != DocumentType.FORM or "keyword" in goal_lower or "key point" in goal_lower:
            plan.steps.append(
                PlanStep(
                    action="keyword_extractor",
                    reason="Extract key topics and phrases.",
                    dependencies=["analyzer"],
                    optional=True,
                )
            )

        # Table analysis – only for data sheets / Excel
        has_excel = any(
            str(p).lower().endswith((".xlsx", ".xls", ".csv"))
            for p in state.input_paths
        )
        if has_excel or doc_type == DocumentType.DATA_SHEET:
            plan.steps.append(
                PlanStep(
                    action="table_analyzer",
                    reason="Analyse tabular structure in Excel/CSV files.",
                    dependencies=["reader"],
                    optional=True,
                )
            )

        # Multi-document reasoning
        if len(state.input_paths) > 1:
            plan.steps.append(
                PlanStep(
                    action="multi_doc_reasoner",
                    reason="Cross-reference insights across multiple documents.",
                    dependencies=["analyzer"],
                    optional=True,
                )
            )

        # Question extraction – skip if user said "only key points"
        wants_questions = state.options.get("extract_questions", True)
        if wants_questions and "only" not in goal_lower:
            plan.steps.append(
                PlanStep(
                    action="question_extractor",
                    reason="Extract questions detected in the text.",
                    dependencies=["analyzer"],
                )
            )

        # Always end with summariser
        deps = ["analyzer"]
        if wants_questions and "only" not in goal_lower:
            deps.append("question_extractor")
        plan.steps.append(
            PlanStep(
                action="summarizer",
                reason="Produce final human-readable summary.",
                dependencies=deps,
            )
        )

        return plan

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _state_summary(state: WorkflowState) -> str:
        parts = [
            f"documents_read={len(state.documents)}",
            f"doc_type={state.document_type.value}",
            f"completed={state.completed_agents}",
            f"errors={state.errors}",
        ]
        return ", ".join(parts)

    @staticmethod
    def _trace(state: WorkflowState, next_agent: str, reason: str) -> None:
        state.plan_trace.append({"next_agent": next_agent, "reason": reason})

    @staticmethod
    def _record_plan(state: WorkflowState, plan: Plan, source: str) -> None:
        state.plan = plan
        state.plan_history.append({"source": source, **plan.to_dict()})

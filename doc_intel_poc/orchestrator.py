from __future__ import annotations

import logging
import sys
from pathlib import Path

from doc_intel_poc.agents import (
    AnalyzerAgent,
    KeywordExtractorAgent,
    MultiDocReasonerAgent,
    PlannerAgent,
    QuestionExtractorAgent,
    ReaderAgent,
    SummarizerAgent,
    TableAnalyzerAgent,
)
from doc_intel_poc.models import TraceEntry, WorkflowState
from doc_intel_poc.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class DocumentIntelligenceWorkflow:
    """Coordinator: generates a plan, executes tools, handles failures."""

    def __init__(self) -> None:
        # Build tool registry
        self.registry = ToolRegistry()
        self._register_tools()

        # Planner has access to the registry for dynamic tool selection
        self.planner = PlannerAgent(registry=self.registry)

    def _register_tools(self) -> None:
        self.registry.register(ReaderAgent())
        self.registry.register(AnalyzerAgent())
        self.registry.register(QuestionExtractorAgent())
        self.registry.register(SummarizerAgent())
        self.registry.register(KeywordExtractorAgent())
        self.registry.register(TableAnalyzerAgent())
        self.registry.register(MultiDocReasonerAgent())

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(
        self,
        input_paths: list[Path],
        extract_questions: bool = True,
        goal: str = "",
    ) -> WorkflowState:
        state = WorkflowState(
            input_paths=input_paths,
            goal=goal,
            options={"extract_questions": extract_questions},
        )

        max_steps = 20
        step_num = 0

        for _ in range(max_steps):
            next_action = self.planner.decide_next(state)
            if next_action is None:
                break

            agent = self.registry.get(next_action)
            if agent is None:
                state.errors.append(f"Planner requested unknown tool: {next_action}")
                break

            step_num += 1
            try:
                tool_result = agent.run(state)

                # Record trace
                trace = TraceEntry(
                    step=step_num,
                    action=next_action,
                    reason=state.plan_trace[-1]["reason"] if state.plan_trace else "",
                    output_summary=str(tool_result.result or "")[:200],
                    confidence=tool_result.confidence,
                    error=tool_result.error,
                )
                state.execution_trace.append(trace)

                if tool_result.success:
                    state.completed_agents.append(next_action)
                else:
                    # Failure-aware: let planner revise the plan
                    logger.warning(
                        "Tool '%s' returned error: %s", next_action, tool_result.error
                    )
                    state.errors.append(
                        f"Tool '{next_action}' error: {tool_result.error}"
                    )
                    self.planner.revise_plan(
                        state,
                        failed_action=next_action,
                        error=tool_result.error or "",
                    )

            except Exception as exc:  # pragma: no cover - safety net
                step_num_for_err = step_num
                trace = TraceEntry(
                    step=step_num_for_err,
                    action=next_action,
                    reason=state.plan_trace[-1]["reason"] if state.plan_trace else "",
                    output_summary="",
                    confidence=0.0,
                    error=str(exc),
                )
                state.execution_trace.append(trace)
                state.errors.append(f"Tool '{next_action}' exception: {exc}")

                # Let planner decide how to proceed
                self.planner.revise_plan(
                    state, failed_action=next_action, error=str(exc)
                )
        else:
            state.errors.append("Workflow stopped after reaching max planner steps.")

        return state

    # ------------------------------------------------------------------
    # Trace visualisation
    # ------------------------------------------------------------------

    @staticmethod
    def print_trace(state: WorkflowState, file: object = None) -> None:
        """Pretty-print the execution trace to *file* (default: stdout)."""
        out = file or sys.stdout
        print("\n╔══════════════════════════════════════╗", file=out)  # type: ignore[arg-type]
        print("║       EXECUTION TRACE                ║", file=out)  # type: ignore[arg-type]
        print("╚══════════════════════════════════════╝\n", file=out)  # type: ignore[arg-type]

        for entry in state.execution_trace:
            status = "✓" if entry.error is None else "✗"
            print(f"  Step {entry.step} [{status}] {entry.action}", file=out)  # type: ignore[arg-type]
            print(f"    Reason : {entry.reason}", file=out)  # type: ignore[arg-type]
            print(f"    Output : {entry.output_summary}", file=out)  # type: ignore[arg-type]
            print(f"    Confidence: {entry.confidence:.2f}", file=out)  # type: ignore[arg-type]
            if entry.error:
                print(f"    Error  : {entry.error}", file=out)  # type: ignore[arg-type]
            print(file=out)  # type: ignore[arg-type]

        if state.plan:
            print("  Plan goal :", state.plan.goal, file=out)  # type: ignore[arg-type]
            print("  Plan revisions:", state.plan.revision, file=out)  # type: ignore[arg-type]

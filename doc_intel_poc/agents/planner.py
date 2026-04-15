from __future__ import annotations

from doc_intel_poc.models import WorkflowState


class PlannerAgent:
    """Decides the next agent call dynamically from workflow state."""

    name = "planner"

    def decide_next(self, state: WorkflowState) -> str | None:
        completed = set(state.completed_agents)

        if "reader" not in completed:
            self._trace(state, "reader", "Input files must be parsed first.")
            return "reader"

        if not state.documents:
            self._trace(state, "stop", "No readable documents were extracted.")
            return None

        if "analyzer" not in completed:
            self._trace(state, "analyzer", "Analyze extracted text before synthesis.")
            return "analyzer"

        wants_questions = state.options.get("extract_questions", True)
        already_extracted = "question_extractor" in completed
        if wants_questions and not already_extracted:
            self._trace(
                state,
                "question_extractor",
                "Question extraction enabled and analysis completed.",
            )
            return "question_extractor"

        if "summarizer" not in completed:
            self._trace(state, "summarizer", "Produce final human-readable summary.")
            return "summarizer"

        self._trace(state, "stop", "All relevant agents completed.")
        return None

    @staticmethod
    def _trace(state: WorkflowState, next_agent: str, reason: str) -> None:
        state.plan_trace.append({"next_agent": next_agent, "reason": reason})

from __future__ import annotations

from pathlib import Path

from doc_intel_poc.agents import (
    AnalyzerAgent,
    PlannerAgent,
    QuestionExtractorAgent,
    ReaderAgent,
    SummarizerAgent,
)
from doc_intel_poc.models import WorkflowState


class DocumentIntelligenceWorkflow:
    """Coordinator that executes whichever agent the planner selects next."""

    def __init__(self) -> None:
        self.planner = PlannerAgent()
        self.agents = {
            "reader": ReaderAgent(),
            "analyzer": AnalyzerAgent(),
            "question_extractor": QuestionExtractorAgent(),
            "summarizer": SummarizerAgent(),
        }

    def run(self, input_paths: list[Path], extract_questions: bool = True) -> WorkflowState:
        state = WorkflowState(
            input_paths=input_paths,
            options={"extract_questions": extract_questions},
        )

        max_steps = 20
        for _ in range(max_steps):
            next_agent = self.planner.decide_next(state)
            if next_agent is None:
                break

            agent = self.agents.get(next_agent)
            if agent is None:
                state.errors.append(f"Planner requested unknown agent: {next_agent}")
                break

            try:
                agent.run(state)
                state.completed_agents.append(next_agent)
            except Exception as exc:  # pragma: no cover - safety net
                state.errors.append(f"Agent '{next_agent}' failed: {exc}")
                break
        else:
            state.errors.append("Workflow stopped after reaching max planner steps.")

        return state

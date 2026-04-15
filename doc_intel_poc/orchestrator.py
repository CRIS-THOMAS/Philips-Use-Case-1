from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from doc_intel_poc.executor import Executor
from doc_intel_poc.planner import Planner
from doc_intel_poc.registry import ToolRegistry
from doc_intel_poc.tools import (
    analyze_text,
    extract_questions,
    read_documents,
    summarize,
)

logger = logging.getLogger(__name__)


def build_default_registry() -> ToolRegistry:
    """Create a :class:`ToolRegistry` pre-loaded with the standard tools."""
    registry = ToolRegistry()
    registry.register("read_documents", read_documents)
    registry.register("analyze_text", analyze_text)
    registry.register("extract_questions", extract_questions)
    registry.register("summarize", summarize)
    return registry


class DocumentIntelligenceWorkflow:
    """Coordinator that uses a Planner + Executor to process documents."""

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or build_default_registry()
        self.planner = Planner()
        self.executor = Executor(self.registry, self.planner)

    def run(
        self,
        input_paths: list[Path],
        extract_questions: bool = True,
    ) -> dict[str, Any]:
        state: dict[str, Any] = {
            "input_paths": input_paths,
            "options": {"extract_questions": extract_questions},
            "documents": [],
            "combined_text": "",
            "analysis": {},
            "questions": [],
            "summary": "",
            "completed_actions": [],
            "execution_log": [],
            "errors": [],
        }

        # Ask planner to generate the initial plan.
        state["plan"] = self.planner.generate_plan(state)
        logger.info("Initial plan: %s", state["plan"])

        # Execute the plan.
        state = self.executor.run(state)

        return state

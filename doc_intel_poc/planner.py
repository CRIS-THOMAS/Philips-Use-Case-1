"""Planner: generates and revises action plans at runtime."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Planner:
    """Generates a list of actions based on input state and document preview.

    The plan is built dynamically by inspecting the shared state — there is
    no hardcoded sequence baked into the planner.
    """

    def generate_plan(self, state: dict[str, Any]) -> list[str]:
        """Return an ordered list of action names for the executor to run.

        The planner inspects ``state`` (input paths, options, what has already
        been completed) and decides which actions are relevant and in what
        order they should execute.
        """
        actions: list[str] = []

        input_paths: list[Path] = state.get("input_paths", [])
        options: dict[str, Any] = state.get("options", {})
        completed: set[str] = set(state.get("completed_actions", []))

        # --- dynamically decide which actions are relevant ---
        has_unread_inputs = bool(input_paths) and "read_documents" not in completed
        has_text = bool(state.get("combined_text"))
        needs_analysis = "analyze_text" not in completed
        wants_questions = options.get("extract_questions", True)
        needs_summary = "summarize" not in completed

        if has_unread_inputs:
            actions.append("read_documents")
            # After reading we will have text, so anticipate downstream steps.
            has_text = True

        if has_text and needs_analysis:
            actions.append("analyze_text")

        if has_text and wants_questions and "extract_questions" not in completed:
            actions.append("extract_questions")

        if needs_summary:
            actions.append("summarize")

        logger.info("Generated plan: %s", actions)
        return actions

    def revise_plan(
        self,
        remaining: list[str],
        state: dict[str, Any],
    ) -> list[str]:
        """Optionally revise the remaining plan based on latest state.

        Called after every action so that the plan can adapt to intermediate
        results (e.g., skip question extraction when the analysis shows no
        question candidates, or honour dynamically inserted actions).
        """
        revised = list(remaining)
        analysis = state.get("analysis", {})

        # If analysis found no question candidates, drop extraction.
        min_question_score = 1
        if "extract_questions" in revised:
            score = analysis.get("question_candidate_score")
            if score is not None and score < min_question_score:
                revised.remove("extract_questions")
                logger.info(
                    "Revised plan: removed 'extract_questions' (score=0)"
                )

        # If no documents were read successfully, drop analysis.
        if "analyze_text" in revised and not state.get("documents"):
            revised.remove("analyze_text")
            logger.info("Revised plan: removed 'analyze_text' (no documents)")

        # Honour dynamically inserted actions requested by a tool.
        for action in state.pop("_insert_actions", []):
            if action not in revised:
                revised.append(action)
                logger.info(
                    "Revised plan: inserted '%s' from tool request", action
                )

        return revised

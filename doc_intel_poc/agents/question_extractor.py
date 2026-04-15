from __future__ import annotations

import re

from doc_intel_poc.agents.base import Agent
from doc_intel_poc.models import WorkflowState


class QuestionExtractorAgent(Agent):
    name = "question_extractor"

    # Match sentences that end with '?' — the only reliable question marker.
    _QUESTION_RE = re.compile(
        r"([A-Z][^?.!]*\?)",
        flags=re.MULTILINE,
    )

    # Heuristic filters to ignore noisy fragments
    _MIN_LENGTH = 10
    _CODE_BLOCK_RE = re.compile(r"[{}<>=/;]")

    def run(self, state: WorkflowState) -> None:
        text = state.combined_text or ""
        extracted: list[str] = []

        for match in self._QUESTION_RE.finditer(text):
            candidate = " ".join(match.group(1).split()).strip()

            # Skip very short fragments
            if len(candidate) < self._MIN_LENGTH:
                continue

            # Skip code-like or noisy fragments
            if self._CODE_BLOCK_RE.search(candidate):
                continue

            extracted.append(candidate)

        state.questions = self._dedupe(extracted)

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for item in items:
            normalized = " ".join(item.lower().split())
            if normalized in seen:
                continue
            seen.add(normalized)
            unique.append(item)
        return unique

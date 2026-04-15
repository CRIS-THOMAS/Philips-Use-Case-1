from __future__ import annotations

import re

from doc_intel_poc.agents.base import Agent
from doc_intel_poc.models import ToolResult, WorkflowState


class QuestionExtractorAgent(Agent):
    name = "question_extractor"
    description = "Extracts questions from combined document text."

    STARTER_PATTERN = re.compile(
        r"^(what|why|how|when|where|which|who|is|are|can|could|should|would|do|does|did)\b",
        flags=re.IGNORECASE,
    )

    def run(self, state: WorkflowState) -> ToolResult:
        text = state.combined_text or ""
        if not text.strip():
            return ToolResult(
                result=None, confidence=0.0, error="No text to extract questions from."
            )

        extracted: list[str] = []

        # Direct questions ending with a question mark.
        by_qmark = re.findall(r"([^\n?.!][^\n?]{2,}\?)", text)
        extracted.extend(q.strip() for q in by_qmark)

        # Question-like lines that might not have a trailing '?'.
        for line in text.splitlines():
            clean = " ".join(line.split()).strip()
            if len(clean) < 3:
                continue
            if self.STARTER_PATTERN.search(clean):
                extracted.append(clean)

        state.questions = self._dedupe(extracted)

        confidence = min(1.0, len(state.questions) / max(1, len(state.documents)))
        return ToolResult(
            result=f"Extracted {len(state.questions)} question(s)",
            confidence=confidence,
        )

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

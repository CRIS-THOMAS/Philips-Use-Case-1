from __future__ import annotations

import re
from collections import Counter

from doc_intel_poc.agents.base import Agent
from doc_intel_poc.models import ToolResult, WorkflowState


class SummarizerAgent(Agent):
    name = "summarizer"
    description = "Produces a human-readable summary from analysis, keywords, and questions."

    STOPWORDS = {
        "the",
        "and",
        "for",
        "that",
        "with",
        "this",
        "from",
        "have",
        "are",
        "was",
        "were",
        "has",
        "had",
        "will",
        "would",
        "could",
        "should",
        "about",
        "into",
        "their",
        "there",
        "them",
        "then",
        "than",
        "also",
        "your",
        "you",
        "our",
        "but",
    }

    def run(self, state: WorkflowState) -> ToolResult:
        if not state.documents:
            state.summary = "No readable content found in the provided files."
            return ToolResult(result=state.summary, confidence=0.3)

        lines: list[str] = []
        analysis = state.analysis or {}
        per_doc = analysis.get("per_document", [])

        lines.append(
            f"Processed {analysis.get('document_count', len(state.documents))} document(s) "
            f"with ~{analysis.get('total_word_count', 0)} words."
        )

        source_breakdown = ", ".join(
            f"{item['source_type']} ({item['word_count']} words)" for item in per_doc
        )
        if source_breakdown:
            lines.append(f"Source breakdown: {source_breakdown}.")

        # Prefer extracted keywords if available, else compute on the fly
        if state.keywords:
            lines.append("Key topics: " + ", ".join(state.keywords[:10]) + ".")
        else:
            top_terms = self._top_terms(state.combined_text, top_n=8)
            if top_terms:
                lines.append("Top recurring terms: " + ", ".join(top_terms) + ".")

        preview = self._high_signal_lines(state.combined_text, max_lines=4)
        if preview:
            lines.append("Highlights: " + " | ".join(preview))

        question_count = len(state.questions)
        lines.append(f"Detected {question_count} question(s) in total.")

        # Include multi-doc insights if present
        if state.multi_doc_insights:
            common = state.multi_doc_insights.get("common_themes", [])
            if common:
                lines.append("Common themes across documents: " + ", ".join(common) + ".")

        state.summary = "\n".join(lines)
        return ToolResult(result=state.summary, confidence=0.9)

    def _top_terms(self, text: str, top_n: int) -> list[str]:
        tokens = re.findall(r"\b[a-zA-Z][a-zA-Z-]{2,}\b", text.lower())
        filtered = [tok for tok in tokens if tok not in self.STOPWORDS]
        counts = Counter(filtered)
        return [term for term, _ in counts.most_common(top_n)]

    @staticmethod
    def _high_signal_lines(text: str, max_lines: int) -> list[str]:
        selected: list[str] = []
        for line in text.splitlines():
            clean = " ".join(line.split()).strip()
            if len(clean) < 30:
                continue
            selected.append(clean)
            if len(selected) >= max_lines:
                break
        return selected

from __future__ import annotations

import re
from collections import Counter

from doc_intel_poc.agents.base import Agent
from doc_intel_poc.models import WorkflowState


class SummarizerAgent(Agent):
    name = "summarizer"

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

    def run(self, state: WorkflowState) -> None:
        if not state.documents:
            state.summary = "No readable content found in the provided files."
            return

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

        top_terms = self._top_terms(state.combined_text, top_n=8)
        if top_terms:
            lines.append("Top recurring terms: " + ", ".join(top_terms) + ".")

        preview = self._high_signal_lines(state.combined_text, max_lines=4)
        if preview:
            lines.append("Highlights: " + " | ".join(preview))

        question_count = len(state.questions)
        lines.append(f"Detected {question_count} question(s) in total.")

        state.summary = "\n".join(lines)

    def _top_terms(self, text: str, top_n: int) -> list[str]:
        tokens = re.findall(r"\\b[a-zA-Z][a-zA-Z-]{2,}\\b", text.lower())
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

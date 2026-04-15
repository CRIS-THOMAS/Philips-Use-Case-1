from __future__ import annotations

import re
from collections import Counter

from doc_intel_poc.agents.base import Agent
from doc_intel_poc.models import WorkflowState


class SummarizerAgent(Agent):
    name = "summarizer"

    STOPWORDS = {
        "the", "and", "for", "that", "with", "this", "from", "have",
        "are", "was", "were", "has", "had", "will", "would", "could",
        "should", "about", "into", "their", "there", "them", "then",
        "than", "also", "your", "you", "our", "but", "not", "all",
        "been", "its", "may", "can", "each", "which", "does", "did",
        "source", "pdf", "page", "sheet", "csv",
    }

    # Lines that look like internal markers, not document content.
    _MARKER_RE = re.compile(r"^\[?SOURCE:|^---\s*(PDF Page|Sheet:)")

    def run(self, state: WorkflowState) -> None:
        if not state.documents:
            state.summary = "No readable content found in the provided files."
            return

        lines: list[str] = []
        analysis = state.analysis or {}
        per_doc = analysis.get("per_document", [])

        total_words = analysis.get("total_word_count", 0)
        total_sentences = analysis.get("total_sentence_count", 0)
        doc_count = analysis.get("document_count", len(state.documents))

        lines.append(
            f"Processed {doc_count} document(s) "
            f"containing {total_words} words across {total_sentences} sentences."
        )

        source_breakdown = ", ".join(
            f"{item['source_type']} ({item['word_count']} words, "
            f"{item['sentence_count']} sentences)"
            for item in per_doc
        )
        if source_breakdown:
            lines.append(f"Source breakdown: {source_breakdown}.")

        top_terms = self._top_terms(state.combined_text, top_n=8)
        if top_terms:
            lines.append("Top recurring terms: " + ", ".join(top_terms) + ".")

        preview = self._high_signal_sentences(state.combined_text, max_sentences=3)
        if preview:
            lines.append("Key highlights:")
            for sentence in preview:
                lines.append(f"  - {sentence}")

        question_count = len(state.questions)
        lines.append(f"Detected {question_count} question(s) in total.")

        state.summary = "\n".join(lines)

    def _top_terms(self, text: str, top_n: int) -> list[str]:
        tokens = re.findall(r"\b[a-zA-Z][a-zA-Z-]{2,}\b", text.lower())
        filtered = [tok for tok in tokens if tok not in self.STOPWORDS]
        counts = Counter(filtered)
        return [term for term, _ in counts.most_common(top_n)]

    def _high_signal_sentences(self, text: str, max_sentences: int) -> list[str]:
        """Extract a few meaningful sentences rather than raw lines."""
        # Split text into sentences
        raw_sentences = re.split(r"(?<=[.!?])\s+", text)
        selected: list[str] = []
        for sent in raw_sentences:
            clean = " ".join(sent.split()).strip()
            # Skip short fragments, internal markers, and section headers
            if len(clean) < 40:
                continue
            if self._MARKER_RE.search(clean):
                continue
            # Truncate very long sentences for readability
            if len(clean) > 200:
                clean = clean[:197] + "..."
            selected.append(clean)
            if len(selected) >= max_sentences:
                break
        return selected

from __future__ import annotations

import re
from collections import Counter

from doc_intel_poc.agents.base import Agent
from doc_intel_poc.models import ToolResult, WorkflowState


class KeywordExtractorAgent(Agent):
    """Extracts the most significant keywords / key-phrases from the combined text."""

    name = "keyword_extractor"
    description = "Extracts top keywords and key-phrases from document text."

    STOPWORDS = {
        "the", "and", "for", "that", "with", "this", "from", "have", "are",
        "was", "were", "has", "had", "will", "would", "could", "should",
        "about", "into", "their", "there", "them", "then", "than", "also",
        "your", "you", "our", "but", "not", "all", "been", "being", "its",
        "does", "did", "just", "more", "most", "other", "some", "such",
        "only", "over", "very", "can", "each", "may", "which", "these",
        "what", "when", "where", "how", "who", "page", "source", "sheet",
        "pdf", "csv", "table", "row", "column",
    }

    def run(self, state: WorkflowState) -> ToolResult:
        text = state.combined_text or ""
        if not text.strip():
            return ToolResult(result=None, confidence=0.0, error="No text for keyword extraction.")

        # single-word keywords
        tokens = re.findall(r"\b[a-zA-Z][a-zA-Z-]{2,}\b", text.lower())
        filtered = [t for t in tokens if t not in self.STOPWORDS]
        word_counts = Counter(filtered)

        # bigrams (simple adjacent pairs)
        bigrams: list[str] = []
        for i in range(len(filtered) - 1):
            bigrams.append(f"{filtered[i]} {filtered[i + 1]}")
        bigram_counts = Counter(bigrams)

        # Merge: top 10 single words + top 5 bigrams
        top_words = [w for w, _ in word_counts.most_common(10)]
        top_bigrams = [b for b, c in bigram_counts.most_common(5) if c >= 2]

        keywords = list(dict.fromkeys(top_bigrams + top_words))[:15]
        state.keywords = keywords

        return ToolResult(
            result=f"Extracted {len(keywords)} keyword(s)",
            confidence=0.85,
        )

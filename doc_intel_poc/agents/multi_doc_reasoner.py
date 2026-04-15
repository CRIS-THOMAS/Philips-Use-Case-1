from __future__ import annotations

import re
from collections import Counter
from typing import Any

from doc_intel_poc.agents.base import Agent
from doc_intel_poc.models import ToolResult, WorkflowState


class MultiDocReasonerAgent(Agent):
    """Merges insights across multiple documents to find common themes and conflicts."""

    name = "multi_doc_reasoner"
    description = "Cross-references multiple documents to find shared themes and unique insights."

    STOPWORDS = {
        "the", "and", "for", "that", "with", "this", "from", "have", "are",
        "was", "were", "has", "had", "will", "would", "could", "should",
        "about", "into", "their", "there", "them", "then", "than", "also",
        "your", "you", "our", "but", "not", "all", "been", "being", "its",
        "page", "source", "sheet", "pdf", "csv",
    }

    def run(self, state: WorkflowState) -> ToolResult:
        docs = state.documents
        if len(docs) < 2:
            return ToolResult(
                result="Single document – cross-doc reasoning skipped.",
                confidence=1.0,
            )

        per_doc_terms = self._per_doc_top_terms(docs, top_n=20)

        # Common terms across all docs
        all_sets = [set(terms) for terms in per_doc_terms.values()]
        common = set.intersection(*all_sets) if all_sets else set()

        # Unique per doc
        unique_per_doc: dict[str, list[str]] = {}
        for path, terms in per_doc_terms.items():
            others = set()
            for p2, t2 in per_doc_terms.items():
                if p2 != path:
                    others.update(t2)
            unique_per_doc[path] = [t for t in terms if t not in others][:5]

        state.multi_doc_insights = {
            "document_count": len(docs),
            "common_themes": sorted(common)[:10],
            "unique_per_document": unique_per_doc,
        }

        return ToolResult(
            result=f"Found {len(common)} common theme(s) across {len(docs)} documents",
            confidence=0.75,
        )

    def _per_doc_top_terms(self, docs: list[Any], top_n: int) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for doc in docs:
            tokens = re.findall(r"\b[a-zA-Z][a-zA-Z-]{2,}\b", doc.content.lower())
            filtered = [t for t in tokens if t not in self.STOPWORDS]
            counts = Counter(filtered)
            result[doc.path] = [w for w, _ in counts.most_common(top_n)]
        return result

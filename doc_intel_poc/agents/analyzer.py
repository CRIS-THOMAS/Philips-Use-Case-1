from __future__ import annotations

import re

from doc_intel_poc.agents.base import Agent
from doc_intel_poc.models import ToolResult, WorkflowState


class AnalyzerAgent(Agent):
    name = "analyzer"
    description = "Analyses extracted text to produce word counts, question scores, and per-document stats."

    QUESTION_WORDS = (
        "what",
        "why",
        "how",
        "when",
        "where",
        "which",
        "who",
        "is",
        "are",
        "can",
        "could",
        "should",
        "would",
        "do",
        "does",
        "did",
    )

    def run(self, state: WorkflowState) -> ToolResult:
        text = state.combined_text or ""
        if not text.strip():
            return ToolResult(result=None, confidence=0.0, error="No text to analyse.")

        words = re.findall(r"\b\w+\b", text)
        question_marks = text.count("?")
        question_word_hits = len(
            re.findall(
                rf"\b({'|'.join(self.QUESTION_WORDS)})\b", text, flags=re.IGNORECASE
            )
        )

        per_doc = []
        for doc in state.documents:
            doc_words = re.findall(r"\b\w+\b", doc.content)
            per_doc.append(
                {
                    "path": doc.path,
                    "source_type": doc.source_type,
                    "char_count": len(doc.content),
                    "word_count": len(doc_words),
                    "question_mark_count": doc.content.count("?"),
                }
            )

        state.analysis = {
            "document_count": len(state.documents),
            "total_char_count": len(text),
            "total_word_count": len(words),
            "question_mark_count": question_marks,
            "question_word_hits": question_word_hits,
            "question_candidate_score": question_marks + question_word_hits,
            "per_document": per_doc,
        }

        return ToolResult(
            result=f"Analysed {len(words)} words across {len(state.documents)} doc(s)",
            confidence=1.0,
        )

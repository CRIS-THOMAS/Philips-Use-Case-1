from __future__ import annotations

from doc_intel_poc.agents.base import Agent
from doc_intel_poc.models import WorkflowState
from doc_intel_poc.text_utils import count_sentences, count_words


class AnalyzerAgent(Agent):
    name = "analyzer"

    def run(self, state: WorkflowState) -> None:
        text = state.combined_text or ""
        total_words = count_words(text)
        total_sentences = count_sentences(text)
        question_marks = text.count("?")

        per_doc = []
        for doc in state.documents:
            doc_words = count_words(doc.content)
            doc_sentences = count_sentences(doc.content)
            per_doc.append(
                {
                    "path": doc.path,
                    "source_type": doc.source_type,
                    "char_count": len(doc.content),
                    "word_count": doc_words,
                    "sentence_count": doc_sentences,
                    "question_mark_count": doc.content.count("?"),
                }
            )

        state.analysis = {
            "result": "analysis_complete",
            "confidence": 1.0 if total_words > 0 else 0.0,
            "document_count": len(state.documents),
            "total_char_count": len(text),
            "total_word_count": total_words,
            "total_sentence_count": total_sentences,
            "question_mark_count": question_marks,
            "per_document": per_doc,
        }

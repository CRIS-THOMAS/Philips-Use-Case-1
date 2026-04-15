"""Tool functions for document intelligence pipeline.

Each tool is a plain function with signature ``(state: dict) -> None``
that reads from and writes to the shared *state* dictionary.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
import pdfplumber

from doc_intel_poc.models import DocumentContent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool: read_documents
# ---------------------------------------------------------------------------

def read_documents(state: dict[str, Any]) -> None:
    """Read PDF / Excel / CSV files listed in ``state['input_paths']``."""
    docs: list[DocumentContent] = []

    for path in state.get("input_paths", []):
        resolved = Path(path)
        if not resolved.exists():
            state.setdefault("errors", []).append(
                f"File not found: {resolved}"
            )
            continue

        suffix = resolved.suffix.lower()
        try:
            if suffix == ".pdf":
                text = _read_pdf(resolved)
                docs.append(DocumentContent(str(resolved), "pdf", text))
            elif suffix in {".xlsx", ".xls", ".csv"}:
                text = _read_excel_or_csv(resolved)
                docs.append(DocumentContent(str(resolved), "excel", text))
            else:
                state.setdefault("errors", []).append(
                    f"Unsupported file type: {resolved}"
                )
        except Exception as exc:
            state.setdefault("errors", []).append(
                f"Failed reading {resolved}: {exc}"
            )

    state["documents"] = docs
    state["combined_text"] = "\n\n".join(
        f"[SOURCE: {doc.path}]\n{doc.content}" for doc in docs
    )
    logger.info("Read %d document(s)", len(docs))


def _read_pdf(path: Path) -> str:
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            pages.append(f"--- PDF Page {i} ---\n{page_text.strip()}")
    return "\n\n".join(pages)


def _read_excel_or_csv(path: Path) -> str:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        return _format_sheet("CSV", df)

    sheets = pd.read_excel(path, sheet_name=None)
    rendered: list[str] = []
    for sheet_name, df in sheets.items():
        rendered.append(_format_sheet(sheet_name, df))
    return "\n\n".join(rendered)


def _format_sheet(
    sheet_name: str, df: pd.DataFrame, row_limit: int = 120
) -> str:
    clipped = df.fillna("").astype(str)
    truncated_note = ""
    if len(clipped) > row_limit:
        clipped = clipped.head(row_limit)
        truncated_note = f"\n[Truncated to first {row_limit} rows]"

    table_text = clipped.to_string(index=False)
    return f"--- Sheet: {sheet_name} ---\n{table_text}{truncated_note}"


# ---------------------------------------------------------------------------
# Tool: analyze_text
# ---------------------------------------------------------------------------

_QUESTION_WORDS = (
    "what", "why", "how", "when", "where", "which", "who",
    "is", "are", "can", "could", "should", "would", "do", "does", "did",
)


def analyze_text(state: dict[str, Any]) -> None:
    """Compute basic text statistics and store in ``state['analysis']``."""
    text = state.get("combined_text", "")
    words = re.findall(r"\b\w+\b", text)
    question_marks = text.count("?")
    question_word_hits = len(
        re.findall(
            rf"\b({'|'.join(_QUESTION_WORDS)})\b",
            text,
            flags=re.IGNORECASE,
        )
    )

    per_doc: list[dict[str, Any]] = []
    for doc in state.get("documents", []):
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

    state["analysis"] = {
        "document_count": len(state.get("documents", [])),
        "total_char_count": len(text),
        "total_word_count": len(words),
        "question_mark_count": question_marks,
        "question_word_hits": question_word_hits,
        "question_candidate_score": question_marks + question_word_hits,
        "per_document": per_doc,
    }
    logger.info(
        "Analysis complete: %d words, score=%d",
        len(words),
        question_marks + question_word_hits,
    )


# ---------------------------------------------------------------------------
# Tool: extract_questions
# ---------------------------------------------------------------------------

_STARTER_PATTERN = re.compile(
    r"^(what|why|how|when|where|which|who"
    r"|is|are|can|could|should|would|do|does|did)\b",
    flags=re.IGNORECASE,
)


def extract_questions(state: dict[str, Any]) -> None:
    """Pull question-like sentences from the combined text."""
    text = state.get("combined_text", "")
    extracted: list[str] = []

    # Direct questions ending with a question mark.
    by_qmark = re.findall(r"([^\n?.!][^\n?]{2,}\?)", text)
    extracted.extend(q.strip() for q in by_qmark)

    # Question-like lines that might not have a trailing '?'.
    for line in text.splitlines():
        clean = " ".join(line.split()).strip()
        if len(clean) < 3:
            continue
        if _STARTER_PATTERN.search(clean):
            extracted.append(clean)

    state["questions"] = _dedupe(extracted)
    logger.info("Extracted %d question(s)", len(state["questions"]))


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


# ---------------------------------------------------------------------------
# Tool: summarize
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "the", "and", "for", "that", "with", "this", "from", "have", "are",
    "was", "were", "has", "had", "will", "would", "could", "should",
    "about", "into", "their", "there", "them", "then", "than", "also",
    "your", "you", "our", "but",
}


def summarize(state: dict[str, Any]) -> None:
    """Produce a human-readable summary and store in ``state['summary']``."""
    documents = state.get("documents", [])
    if not documents:
        state["summary"] = "No readable content found in the provided files."
        return

    lines: list[str] = []
    analysis = state.get("analysis", {})
    per_doc = analysis.get("per_document", [])

    lines.append(
        f"Processed {analysis.get('document_count', len(documents))} "
        f"document(s) with ~{analysis.get('total_word_count', 0)} words."
    )

    source_breakdown = ", ".join(
        f"{item['source_type']} ({item['word_count']} words)"
        for item in per_doc
    )
    if source_breakdown:
        lines.append(f"Source breakdown: {source_breakdown}.")

    top_terms = _top_terms(state.get("combined_text", ""), top_n=8)
    if top_terms:
        lines.append("Top recurring terms: " + ", ".join(top_terms) + ".")

    preview = _high_signal_lines(state.get("combined_text", ""), max_lines=4)
    if preview:
        lines.append("Highlights: " + " | ".join(preview))

    question_count = len(state.get("questions", []))
    lines.append(f"Detected {question_count} question(s) in total.")

    state["summary"] = "\n".join(lines)
    logger.info("Summary generated (%d chars)", len(state["summary"]))


def _top_terms(text: str, top_n: int) -> list[str]:
    tokens = re.findall(r"\b[a-zA-Z][a-zA-Z-]{2,}\b", text.lower())
    filtered = [tok for tok in tokens if tok not in _STOPWORDS]
    counts = Counter(filtered)
    return [term for term, _ in counts.most_common(top_n)]


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

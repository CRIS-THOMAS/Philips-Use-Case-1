from __future__ import annotations

from pathlib import Path

import pandas as pd
import pdfplumber

from doc_intel_poc.agents.base import Agent
from doc_intel_poc.models import DocumentContent, DocumentType, ToolResult, WorkflowState


class ReaderAgent(Agent):
    name = "reader"
    description = "Reads PDF, Excel, and CSV files and extracts text content."

    def run(self, state: WorkflowState) -> ToolResult:
        docs: list[DocumentContent] = []

        for path in state.input_paths:
            resolved = Path(path)
            if not resolved.exists():
                state.errors.append(f"File not found: {resolved}")
                continue

            suffix = resolved.suffix.lower()
            try:
                if suffix == ".pdf":
                    text = self._read_pdf(resolved)
                    docs.append(
                        DocumentContent(
                            path=str(resolved),
                            source_type="pdf",
                            content=text,
                            metadata={"pages": text.count("--- PDF Page")},
                        )
                    )
                elif suffix in {".xlsx", ".xls", ".csv"}:
                    text = self._read_excel_or_csv(resolved)
                    docs.append(
                        DocumentContent(
                            path=str(resolved),
                            source_type="excel",
                            content=text,
                            metadata={"sheets": text.count("--- Sheet:")},
                        )
                    )
                else:
                    state.errors.append(f"Unsupported file type: {resolved}")
            except Exception as exc:  # pragma: no cover - safety net
                state.errors.append(f"Failed reading {resolved}: {exc}")

        state.documents = docs
        state.combined_text = "\n\n".join(
            f"[SOURCE: {doc.path}]\n{doc.content}" for doc in docs
        )

        # Detect dominant document type
        state.document_type = self._detect_type(docs)

        if not docs:
            return ToolResult(
                result=None,
                confidence=0.0,
                error="No readable documents found.",
            )

        return ToolResult(
            result=f"Read {len(docs)} document(s)",
            confidence=1.0,
        )

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _detect_type(docs: list[DocumentContent]) -> DocumentType:
        has_excel = any(d.source_type == "excel" for d in docs)
        has_pdf = any(d.source_type == "pdf" for d in docs)

        if has_excel and not has_pdf:
            return DocumentType.DATA_SHEET

        # Heuristic: if >20 % of lines end with '?', treat as form
        total_lines = 0
        question_lines = 0
        for doc in docs:
            for line in doc.content.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                total_lines += 1
                if stripped.endswith("?"):
                    question_lines += 1

        if total_lines and question_lines / total_lines > 0.20:
            return DocumentType.FORM

        if has_pdf:
            return DocumentType.REPORT

        return DocumentType.UNKNOWN

    @staticmethod
    def _read_pdf(path: Path) -> str:
        pages: list[str] = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                pages.append(f"--- PDF Page {i} ---\n{page_text.strip()}")
        return "\n\n".join(pages)

    @staticmethod
    def _read_excel_or_csv(path: Path) -> str:
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
            return ReaderAgent._format_sheet("CSV", df)

        sheets = pd.read_excel(path, sheet_name=None)
        rendered: list[str] = []
        for sheet_name, df in sheets.items():
            rendered.append(ReaderAgent._format_sheet(sheet_name, df))
        return "\n\n".join(rendered)

    @staticmethod
    def _format_sheet(sheet_name: str, df: pd.DataFrame, row_limit: int = 120) -> str:
        clipped = df.fillna("").astype(str)
        truncated_note = ""
        if len(clipped) > row_limit:
            clipped = clipped.head(row_limit)
            truncated_note = f"\n[Truncated to first {row_limit} rows]"

        table_text = clipped.to_string(index=False)
        return f"--- Sheet: {sheet_name} ---\n{table_text}{truncated_note}"

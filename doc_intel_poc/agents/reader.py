from __future__ import annotations

from pathlib import Path

import pandas as pd
import pdfplumber

from doc_intel_poc.agents.base import Agent
from doc_intel_poc.models import DocumentContent, WorkflowState
from doc_intel_poc.text_utils import clean_text


class ReaderAgent(Agent):
    name = "reader"

    def run(self, state: WorkflowState) -> None:
        docs: list[DocumentContent] = []

        for path in state.input_paths:
            resolved = Path(path)
            if not resolved.exists():
                state.errors.append(f"File not found: {resolved}")
                continue

            suffix = resolved.suffix.lower()
            try:
                if suffix == ".pdf":
                    text = clean_text(self._read_pdf(resolved))
                    docs.append(
                        DocumentContent(
                            path=str(resolved),
                            source_type="pdf",
                            content=text,
                        )
                    )
                elif suffix in {".xlsx", ".xls", ".csv"}:
                    text = clean_text(self._read_excel_or_csv(resolved))
                    docs.append(
                        DocumentContent(
                            path=str(resolved),
                            source_type="excel",
                            content=text,
                        )
                    )
                elif suffix == ".txt":
                    text = resolved.read_text(encoding="utf-8", errors="replace")
                    docs.append(
                        DocumentContent(
                            path=str(resolved),
                            source_type="txt",
                            content=text,
                        )
                    )
                elif suffix == ".docx":
                    text = self._read_docx(resolved)
                    docs.append(
                        DocumentContent(
                            path=str(resolved),
                            source_type="docx",
                            content=text,
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
    def _read_docx(path: Path) -> str:
        try:
            import docx  # imported as 'docx' (package: python-docx)  # noqa: PLC0415
        except ImportError:  # pragma: no cover
            raise ImportError(
                "python-docx is required to read .docx files. "
                "Install it with: pip install python-docx"
            )
        doc = docx.Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    @staticmethod
    def _format_sheet(sheet_name: str, df: pd.DataFrame, row_limit: int = 120) -> str:
        clipped = df.fillna("").astype(str)
        truncated_note = ""
        if len(clipped) > row_limit:
            clipped = clipped.head(row_limit)
            truncated_note = f"\n[Truncated to first {row_limit} rows]"

        table_text = clipped.to_string(index=False)
        return f"--- Sheet: {sheet_name} ---\n{table_text}{truncated_note}"

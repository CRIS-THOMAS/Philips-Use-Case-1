from __future__ import annotations

import re
from typing import Any

from doc_intel_poc.agents.base import Agent
from doc_intel_poc.models import ToolResult, WorkflowState


class TableAnalyzerAgent(Agent):
    """Analyses Excel / CSV tabular data for column stats, patterns, and anomalies."""

    name = "table_analyzer"
    description = "Analyses tabular data from Excel/CSV documents for column stats and patterns."

    def run(self, state: WorkflowState) -> ToolResult:
        excel_docs = [d for d in state.documents if d.source_type == "excel"]
        if not excel_docs:
            return ToolResult(result=None, confidence=0.0, error="No Excel/CSV documents to analyse.")

        insights: dict[str, Any] = {"sheets": []}
        for doc in excel_docs:
            sheet_info = self._analyse_sheet_text(doc.content, doc.path)
            insights["sheets"].extend(sheet_info)

        insights["total_sheets"] = len(insights["sheets"])
        state.table_insights = insights

        return ToolResult(
            result=f"Analysed {insights['total_sheets']} sheet(s)",
            confidence=0.8,
        )

    @staticmethod
    def _analyse_sheet_text(text: str, path: str) -> list[dict[str, Any]]:
        """Parse the rendered sheet text to extract basic column info."""
        sheets: list[dict[str, Any]] = []
        current_name = ""
        header_line: str | None = None
        row_count = 0

        for line in text.splitlines():
            if line.startswith("--- Sheet:"):
                # Save previous sheet
                if current_name and header_line is not None:
                    sheets.append(
                        {
                            "path": path,
                            "sheet": current_name,
                            "columns": [c.strip() for c in re.split(r"\s{2,}", header_line.strip()) if c.strip()],
                            "row_count": row_count,
                        }
                    )
                current_name = line.replace("--- Sheet:", "").strip().rstrip(" ---")
                header_line = None
                row_count = 0
                continue

            stripped = line.strip()
            if not stripped or stripped.startswith("[Truncated"):
                continue

            if header_line is None:
                header_line = stripped
            else:
                row_count += 1

        # Last sheet
        if current_name and header_line is not None:
            sheets.append(
                {
                    "path": path,
                    "sheet": current_name,
                    "columns": [c.strip() for c in re.split(r"\s{2,}", header_line.strip()) if c.strip()],
                    "row_count": row_count,
                }
            )

        return sheets

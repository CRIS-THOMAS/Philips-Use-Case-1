from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DocumentContent:
    path: str
    source_type: str
    content: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "source_type": self.source_type,
            "content_length": len(self.content),
        }


@dataclass
class WorkflowState:
    input_paths: list[Path]
    options: dict[str, Any] = field(default_factory=dict)
    documents: list[DocumentContent] = field(default_factory=list)
    combined_text: str = ""
    analysis: dict[str, Any] = field(default_factory=dict)
    questions: list[str] = field(default_factory=list)
    summary: str = ""
    completed_agents: list[str] = field(default_factory=list)
    plan_trace: list[dict[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "inputs": [str(p) for p in self.input_paths],
            "options": self.options,
            "documents": [doc.to_dict() for doc in self.documents],
            "analysis": self.analysis,
            "questions": self.questions,
            "summary": self.summary,
            "completed_agents": self.completed_agents,
            "plan_trace": self.plan_trace,
            "errors": self.errors,
        }

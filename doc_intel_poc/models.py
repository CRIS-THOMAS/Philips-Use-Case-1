from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class DocumentType(Enum):
    """Detected document category used by the planner."""

    REPORT = "report"
    FORM = "form"
    DATA_SHEET = "data_sheet"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Tool result – every tool returns one of these
# ---------------------------------------------------------------------------


@dataclass
class ToolResult:
    """Standardised return value for every tool execution."""

    result: Any = None
    confidence: float = 1.0
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "confidence": self.confidence,
            "error": self.error,
            "result_preview": str(self.result)[:200] if self.result else None,
        }


# ---------------------------------------------------------------------------
# Plan primitives
# ---------------------------------------------------------------------------


@dataclass
class PlanStep:
    """A single step in an execution plan."""

    action: str
    reason: str
    dependencies: list[str] = field(default_factory=list)
    optional: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "dependencies": self.dependencies,
            "optional": self.optional,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlanStep:
        return cls(
            action=data["action"],
            reason=data.get("reason", ""),
            dependencies=data.get("dependencies", []),
            optional=data.get("optional", False),
        )


@dataclass
class Plan:
    """Ordered list of plan steps with mutation helpers."""

    steps: list[PlanStep] = field(default_factory=list)
    goal: str = ""
    revision: int = 0

    # -- mutation helpers ---------------------------------------------------

    def insert_step(self, index: int, step: PlanStep) -> None:
        self.steps.insert(index, step)
        self.revision += 1

    def remove_step(self, action: str) -> bool:
        before = len(self.steps)
        self.steps = [s for s in self.steps if s.action != action]
        removed = len(self.steps) < before
        if removed:
            self.revision += 1
        return removed

    def reorder(self, action_order: list[str]) -> None:
        lookup = {s.action: s for s in self.steps}
        ordered = [lookup[a] for a in action_order if a in lookup]
        remaining = [s for s in self.steps if s.action not in action_order]
        self.steps = ordered + remaining
        self.revision += 1

    def pending_steps(self, completed: set[str]) -> list[PlanStep]:
        return [s for s in self.steps if s.action not in completed]

    def next_step(self, completed: set[str]) -> PlanStep | None:
        for step in self.steps:
            if step.action in completed:
                continue
            # check dependencies are satisfied
            if all(dep in completed for dep in step.dependencies):
                return step
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "revision": self.revision,
            "steps": [s.to_dict() for s in self.steps],
        }


# ---------------------------------------------------------------------------
# Document content
# ---------------------------------------------------------------------------


@dataclass
class DocumentContent:
    """Parsed content of a single input file."""

    path: str
    source_type: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "source_type": self.source_type,
            "content_length": len(self.content),
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Execution trace entry
# ---------------------------------------------------------------------------


@dataclass
class TraceEntry:
    """Single entry in the execution trace."""

    step: int
    action: str
    reason: str
    output_summary: str
    confidence: float
    error: str | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "action": self.action,
            "reason": self.reason,
            "output_summary": self.output_summary,
            "confidence": self.confidence,
            "error": self.error,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Workflow state
# ---------------------------------------------------------------------------


@dataclass
class WorkflowState:
    """Structured state shared by all agents throughout a workflow run."""

    input_paths: list[Path]
    goal: str = ""
    options: dict[str, Any] = field(default_factory=dict)

    # -- document data -------------------------------------------------------
    documents: list[DocumentContent] = field(default_factory=list)
    combined_text: str = ""
    document_type: DocumentType = DocumentType.UNKNOWN

    # -- extracted insights --------------------------------------------------
    analysis: dict[str, Any] = field(default_factory=dict)
    questions: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    table_insights: dict[str, Any] = field(default_factory=dict)
    multi_doc_insights: dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    # -- planning & execution ------------------------------------------------
    plan: Plan | None = None
    plan_history: list[dict[str, Any]] = field(default_factory=list)
    completed_agents: list[str] = field(default_factory=list)
    execution_trace: list[TraceEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    # legacy compat
    plan_trace: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "inputs": [str(p) for p in self.input_paths],
            "options": self.options,
            "document_type": self.document_type.value,
            "documents": [doc.to_dict() for doc in self.documents],
            "analysis": self.analysis,
            "keywords": self.keywords,
            "table_insights": self.table_insights,
            "multi_doc_insights": self.multi_doc_insights,
            "questions": self.questions,
            "summary": self.summary,
            "plan": self.plan.to_dict() if self.plan else None,
            "plan_history": self.plan_history,
            "completed_agents": self.completed_agents,
            "execution_trace": [t.to_dict() for t in self.execution_trace],
            "errors": self.errors,
        }

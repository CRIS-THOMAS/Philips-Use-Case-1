from __future__ import annotations

from abc import ABC, abstractmethod

from doc_intel_poc.models import ToolResult, WorkflowState


class Agent(ABC):
    """Base class for all tools / agents in the system."""

    name: str
    description: str = ""

    @abstractmethod
    def run(self, state: WorkflowState) -> ToolResult:
        """Execute the agent against the shared workflow state."""

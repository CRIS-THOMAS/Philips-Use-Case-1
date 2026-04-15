from __future__ import annotations

from abc import ABC, abstractmethod

from doc_intel_poc.models import WorkflowState


class Agent(ABC):
    name: str

    @abstractmethod
    def run(self, state: WorkflowState) -> None:
        """Execute the agent against the shared workflow state."""

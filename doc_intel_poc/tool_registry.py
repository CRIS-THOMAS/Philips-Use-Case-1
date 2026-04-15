"""Central registry of available tools for dynamic selection by the planner."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from doc_intel_poc.agents.base import Agent


class ToolRegistry:
    """Maintains a name → Agent mapping so the planner can discover tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        self._tools[agent.name] = agent

    def get(self, name: str) -> Agent | None:
        return self._tools.get(name)

    def available_names(self) -> list[str]:
        return list(self._tools.keys())

    def describe(self) -> list[dict[str, str]]:
        """Return a short description of each tool for the planner prompt."""
        out: list[dict[str, str]] = []
        for name, agent in self._tools.items():
            out.append(
                {
                    "name": name,
                    "description": getattr(agent, "description", name),
                }
            )
        return out

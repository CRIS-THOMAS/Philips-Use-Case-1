"""Tool registry: maps action names to callable functions."""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Tool function signature: (state: dict[str, Any]) -> None
ToolFunction = Callable[[dict[str, Any]], None]


class ToolRegistry:
    """Dictionary-backed registry that maps action names to tool functions."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolFunction] = {}

    def register(self, name: str, func: ToolFunction) -> None:
        """Register a tool function under the given action name."""
        self._tools[name] = func
        logger.debug("Registered tool: %s", name)

    def get(self, name: str) -> ToolFunction | None:
        """Look up a tool by action name.  Returns *None* if not found."""
        return self._tools.get(name)

    def available(self) -> list[str]:
        """Return sorted list of registered action names."""
        return sorted(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

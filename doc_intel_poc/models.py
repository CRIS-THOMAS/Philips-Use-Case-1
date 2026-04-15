from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DocumentContent:
    """Lightweight container for a parsed document."""

    path: str
    source_type: str
    content: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "source_type": self.source_type,
            "content_length": len(self.content),
        }

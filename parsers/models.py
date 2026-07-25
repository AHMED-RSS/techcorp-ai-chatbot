from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ParsedFile:
    """
    Standard result returned by every local file parser.
    """

    title: str
    text: str
    category: str
    mime_type: str
    extension: str
    metadata: dict[str, Any] = field(
        default_factory=dict
    )
    warnings: list[str] = field(
        default_factory=list
    )

    @property
    def has_text(self) -> bool:
        return bool(self.text.strip())

    @property
    def character_count(self) -> int:
        return len(self.text)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "text": self.text,
            "category": self.category,
            "mime_type": self.mime_type,
            "extension": self.extension,
            "metadata": self.metadata,
            "warnings": self.warnings,
            "has_text": self.has_text,
            "character_count": self.character_count,
        }
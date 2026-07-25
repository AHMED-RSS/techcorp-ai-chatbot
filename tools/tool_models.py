from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


ToolHandler = Callable[
    [dict[str, Any]],
    "ToolResult",
]


@dataclass(slots=True)
class ToolResult:
    """
    Standard result returned by every local tool.
    """

    success: bool
    tool_name: str
    content: str
    data: dict[str, Any] = field(
        default_factory=dict
    )
    error: str | None = None

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "success": self.success,
            "tool_name": self.tool_name,
            "content": self.content,
            "data": self.data,
            "error": self.error,
        }


@dataclass(slots=True)
class ToolDefinition:
    """
    Tool registration information.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler
    category: str = "general"
    requires_confirmation: bool = False

    def public_schema(
        self,
    ) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parameters": self.parameters,
            "requires_confirmation": (
                self.requires_confirmation
            ),
        }
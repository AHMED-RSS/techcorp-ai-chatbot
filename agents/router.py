from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_ROUTE_NAMES = {
    "general",
    "document",
    "code",
    "study",
    "tool",
}


@dataclass(slots=True)
class RouteDecision:
    """
    Structured output produced by the local intelligent router.
    """

    route: str
    confidence: float
    reason: str
    recommended_skill: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] = field(
        default_factory=dict
    )
    use_documents: bool = False
    source: str = "fallback"

    def __post_init__(self) -> None:
        cleaned_route = str(
            self.route or "general"
        ).strip().lower()

        if cleaned_route not in VALID_ROUTE_NAMES:
            cleaned_route = "general"

        self.route = cleaned_route

        try:
            cleaned_confidence = float(
                self.confidence
            )

        except (
            TypeError,
            ValueError,
        ):
            cleaned_confidence = 0.0

        self.confidence = max(
            0.0,
            min(
                1.0,
                cleaned_confidence,
            ),
        )

        self.reason = str(
            self.reason or ""
        ).strip()

        if self.recommended_skill is not None:
            cleaned_skill = str(
                self.recommended_skill
            ).strip()

            self.recommended_skill = (
                cleaned_skill or None
            )

        if self.tool_name is not None:
            cleaned_tool = str(
                self.tool_name
            ).strip().lower()

            self.tool_name = (
                cleaned_tool or None
            )

        if not isinstance(
            self.tool_arguments,
            dict,
        ):
            self.tool_arguments = {}

        self.use_documents = bool(
            self.use_documents
        )

        self.source = str(
            self.source or "fallback"
        ).strip()

    @property
    def wants_tool(self) -> bool:
        return (
            self.route == "tool"
            and bool(self.tool_name)
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "route": self.route,
            "confidence": self.confidence,
            "reason": self.reason,
            "recommended_skill": (
                self.recommended_skill
            ),
            "tool_name": self.tool_name,
            "tool_arguments": (
                self.tool_arguments
            ),
            "use_documents": (
                self.use_documents
            ),
            "source": self.source,
        }


def route_from_dict(
    data: dict[str, Any],
    *,
    source: str,
) -> RouteDecision:
    return RouteDecision(
        route=str(
            data.get(
                "route",
                "general",
            )
        ),
        confidence=data.get(
            "confidence",
            0.0,
        ),
        reason=str(
            data.get(
                "reason",
                "",
            )
        ),
        recommended_skill=(
            data.get(
                "recommended_skill"
            )
        ),
        tool_name=(
            data.get(
                "tool_name"
            )
        ),
        tool_arguments=(
            data.get(
                "tool_arguments",
                {},
            )
        ),
        use_documents=bool(
            data.get(
                "use_documents",
                False,
            )
        ),
        source=source,
    )
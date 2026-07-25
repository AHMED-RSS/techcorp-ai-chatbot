from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_MEMORY_KINDS = {
    "preference",
    "fact",
    "instruction",
    "project",
    "profile",
    "note",
}


@dataclass(slots=True)
class MemoryItem:
    """
    One persistent local memory.
    """

    id: str
    content: str
    kind: str = "note"
    keywords: list[str] = field(
        default_factory=list
    )
    source: str = "explicit"
    chat_id: str | None = None
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""
    access_count: int = 0
    last_accessed_at: str | None = None
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        self.id = str(
            self.id or ""
        ).strip()

        self.content = str(
            self.content or ""
        ).strip()[:5_000]

        cleaned_kind = str(
            self.kind or "note"
        ).strip().lower()

        if cleaned_kind not in VALID_MEMORY_KINDS:
            cleaned_kind = "note"

        self.kind = cleaned_kind

        if not isinstance(
            self.keywords,
            list,
        ):
            self.keywords = []

        cleaned_keywords: list[str] = []

        for keyword in self.keywords:
            value = str(
                keyword or ""
            ).strip().lower()

            if (
                value
                and value not in cleaned_keywords
            ):
                cleaned_keywords.append(
                    value[:60]
                )

        self.keywords = cleaned_keywords[:40]

        self.source = str(
            self.source or "explicit"
        ).strip()

        if self.chat_id is not None:
            cleaned_chat_id = str(
                self.chat_id
            ).strip()

            self.chat_id = (
                cleaned_chat_id
                or None
            )

        self.enabled = bool(
            self.enabled
        )

        try:
            self.access_count = max(
                0,
                int(
                    self.access_count
                ),
            )

        except (
            TypeError,
            ValueError,
        ):
            self.access_count = 0

        if not isinstance(
            self.metadata,
            dict,
        ):
            self.metadata = {}

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "kind": self.kind,
            "keywords": self.keywords,
            "source": self.source,
            "chat_id": self.chat_id,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "access_count": self.access_count,
            "last_accessed_at": (
                self.last_accessed_at
            ),
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class TaskState:
    """
    Durable state for a routed, planned or executed task.
    """

    id: str
    chat_id: str | None
    user_request: str
    goal: str
    status: str
    route: dict[str, Any] | None = None
    plan: dict[str, Any] | None = None
    execution: dict[str, Any] | None = None
    critic: dict[str, Any] | None = None
    final_output: str = ""
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        self.id = str(
            self.id or ""
        ).strip()

        if self.chat_id is not None:
            cleaned_chat_id = str(
                self.chat_id
            ).strip()

            self.chat_id = (
                cleaned_chat_id
                or None
            )

        self.user_request = str(
            self.user_request or ""
        ).strip()

        self.goal = str(
            self.goal
            or self.user_request
        ).strip()

        self.status = str(
            self.status or "pending"
        ).strip().lower()

        self.final_output = str(
            self.final_output or ""
        ).strip()

        if not isinstance(
            self.metadata,
            dict,
        ):
            self.metadata = {}

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "user_request": (
                self.user_request
            ),
            "goal": self.goal,
            "status": self.status,
            "route": self.route,
            "plan": self.plan,
            "execution": self.execution,
            "critic": self.critic,
            "final_output": (
                self.final_output
            ),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


def memory_item_from_dict(
    data: dict[str, Any],
) -> MemoryItem:
    return MemoryItem(
        id=str(
            data.get(
                "id",
                "",
            )
        ),
        content=str(
            data.get(
                "content",
                "",
            )
        ),
        kind=str(
            data.get(
                "kind",
                "note",
            )
        ),
        keywords=(
            data.get(
                "keywords",
                [],
            )
        ),
        source=str(
            data.get(
                "source",
                "explicit",
            )
        ),
        chat_id=(
            data.get(
                "chat_id"
            )
        ),
        enabled=bool(
            data.get(
                "enabled",
                True,
            )
        ),
        created_at=str(
            data.get(
                "created_at",
                "",
            )
        ),
        updated_at=str(
            data.get(
                "updated_at",
                "",
            )
        ),
        access_count=data.get(
            "access_count",
            0,
        ),
        last_accessed_at=(
            data.get(
                "last_accessed_at"
            )
        ),
        metadata=(
            data.get(
                "metadata",
                {},
            )
        ),
    )


def task_state_from_dict(
    data: dict[str, Any],
) -> TaskState:
    return TaskState(
        id=str(
            data.get(
                "id",
                "",
            )
        ),
        chat_id=(
            data.get(
                "chat_id"
            )
        ),
        user_request=str(
            data.get(
                "user_request",
                "",
            )
        ),
        goal=str(
            data.get(
                "goal",
                "",
            )
        ),
        status=str(
            data.get(
                "status",
                "pending",
            )
        ),
        route=(
            data.get(
                "route"
            )
        ),
        plan=(
            data.get(
                "plan"
            )
        ),
        execution=(
            data.get(
                "execution"
            )
        ),
        critic=(
            data.get(
                "critic"
            )
        ),
        final_output=str(
            data.get(
                "final_output",
                "",
            )
        ),
        created_at=str(
            data.get(
                "created_at",
                "",
            )
        ),
        updated_at=str(
            data.get(
                "updated_at",
                "",
            )
        ),
        metadata=(
            data.get(
                "metadata",
                {},
            )
        ),
    )
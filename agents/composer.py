from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_REASONING_MODES = {
    "normal",
    "focused",
    "deep",
}


@dataclass(slots=True)
class ComposerAttachment:
    """
    One file attached through the prompt composer.
    """

    name: str
    size_bytes: int
    mime_type: str
    document_id: str | None = None
    title: str | None = None
    indexed_chunks: int = 0
    error: str | None = None

    def __post_init__(self) -> None:
        self.name = str(
            self.name or "attachment"
        ).strip()

        try:
            self.size_bytes = max(
                0,
                int(self.size_bytes),
            )

        except (
            TypeError,
            ValueError,
        ):
            self.size_bytes = 0

        self.mime_type = str(
            self.mime_type
            or "application/octet-stream"
        ).strip()

        if self.document_id is not None:
            cleaned_document_id = str(
                self.document_id
            ).strip()

            self.document_id = (
                cleaned_document_id
                or None
            )

        if self.title is not None:
            cleaned_title = str(
                self.title
            ).strip()

            self.title = (
                cleaned_title
                or None
            )

        try:
            self.indexed_chunks = max(
                0,
                int(self.indexed_chunks),
            )

        except (
            TypeError,
            ValueError,
        ):
            self.indexed_chunks = 0

        if self.error is not None:
            self.error = str(
                self.error
            ).strip()

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "name": self.name,
            "size_bytes": self.size_bytes,
            "mime_type": self.mime_type,
            "document_id": self.document_id,
            "title": self.title,
            "indexed_chunks": self.indexed_chunks,
            "error": self.error,
        }


@dataclass(slots=True)
class ComposerSubmission:
    """
    A complete prompt-composer submission.
    """

    prompt: str
    reasoning_mode: str = "normal"
    web_search_enabled: bool = False
    document_search_enabled: bool = True
    attachments: list[Any] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        self.prompt = str(
            self.prompt or ""
        ).strip()

        cleaned_mode = str(
            self.reasoning_mode
            or "normal"
        ).strip().lower()

        if cleaned_mode not in VALID_REASONING_MODES:
            cleaned_mode = "normal"

        self.reasoning_mode = cleaned_mode

        self.web_search_enabled = bool(
            self.web_search_enabled
        )

        self.document_search_enabled = bool(
            self.document_search_enabled
        )

        if not isinstance(
            self.attachments,
            list,
        ):
            self.attachments = []

    @property
    def has_attachments(self) -> bool:
        return bool(
            self.attachments
        )

    @property
    def is_deep_think(self) -> bool:
        return (
            self.reasoning_mode
            == "deep"
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "reasoning_mode": (
                self.reasoning_mode
            ),
            "web_search_enabled": (
                self.web_search_enabled
            ),
            "document_search_enabled": (
                self.document_search_enabled
            ),
            "attachment_count": len(
                self.attachments
            ),
        }
from __future__ import annotations

import json
import os
import re
import uuid

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import Settings
from core.exceptions import ChatStorageError
from core.logging_config import get_logger


logger = get_logger(__name__)


DEFAULT_CHAT_TITLE = "New conversation"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )


def generate_chat_id() -> str:
    return str(uuid.uuid4())


def normalise_title(
    title: str,
    fallback: str = DEFAULT_CHAT_TITLE,
) -> str:
    cleaned = re.sub(
        r"\s+",
        " ",
        str(title or ""),
    ).strip()

    if not cleaned:
        return fallback

    return cleaned[:100]


def generate_title_from_message(
    message: str,
) -> str:
    cleaned = re.sub(
        r"\s+",
        " ",
        str(message or ""),
    ).strip()

    if not cleaned:
        return DEFAULT_CHAT_TITLE

    cleaned = cleaned[:60]

    if len(message.strip()) > 60:
        cleaned += "…"

    return cleaned


def normalise_message(
    message: Any,
) -> dict[str, Any] | None:
    if not isinstance(message, dict):
        return None

    role = str(
        message.get("role", "")
    ).strip().lower()

    if role not in {
        "user",
        "assistant",
        "system",
        "tool",
    }:
        return None

    content = str(
        message.get("content", "")
    ).strip()

    if not content:
        return None

    normalised = {
        "id": str(
            message.get("id")
            or uuid.uuid4()
        ),
        "role": role,
        "content": content,
        "created_at": str(
            message.get("created_at")
            or message.get("time")
            or utc_now()
        ),
    }

    if message.get("attachments"):
        normalised["attachments"] = deepcopy(
            message["attachments"]
        )

    if message.get("metadata"):
        normalised["metadata"] = deepcopy(
            message["metadata"]
        )

    return normalised


def normalise_chat(
    raw_chat: Any,
    *,
    fallback_id: str,
) -> dict[str, Any]:
    """
    Repair old chat files and convert them to the new schema.
    """

    if not isinstance(raw_chat, dict):
        raw_chat = {}

    chat_id = str(
        raw_chat.get("id")
        or raw_chat.get("chat_id")
        or fallback_id
    )

    raw_messages = raw_chat.get(
        "messages",
        [],
    )

    messages: list[dict[str, Any]] = []

    if isinstance(raw_messages, list):
        for raw_message in raw_messages:
            message = normalise_message(
                raw_message
            )

            if message:
                messages.append(message)

    created_at = str(
        raw_chat.get("created_at")
        or raw_chat.get("created")
        or utc_now()
    )

    updated_at = str(
        raw_chat.get("updated_at")
        or raw_chat.get("updated")
        or created_at
    )

    title = normalise_title(
        raw_chat.get("title", "")
    )

    if (
        title == DEFAULT_CHAT_TITLE
        and messages
    ):
        first_user_message = next(
            (
                message["content"]
                for message in messages
                if message["role"] == "user"
            ),
            "",
        )

        if first_user_message:
            title = generate_title_from_message(
                first_user_message
            )

    return {
        "schema_version": 2,
        "id": chat_id,
        "title": title,
        "pinned": bool(
            raw_chat.get("pinned", False)
        ),
        "archived": bool(
            raw_chat.get("archived", False)
        ),
        "created_at": created_at,
        "updated_at": updated_at,
        "messages": messages,
        "metadata": (
            deepcopy(
                raw_chat.get("metadata", {})
            )
            if isinstance(
                raw_chat.get("metadata", {}),
                dict,
            )
            else {}
        ),
    }


class ChatService:
    def __init__(
        self,
        settings: Settings,
    ) -> None:
        self.settings = settings
        self.chat_folder = settings.chat_folder

        self.chat_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

    def chat_path(
        self,
        chat_id: str,
    ) -> Path:
        safe_id = re.sub(
            r"[^a-zA-Z0-9_-]",
            "",
            str(chat_id),
        )

        if not safe_id:
            raise ChatStorageError(
                "Invalid conversation identifier."
            )

        return self.chat_folder / f"{safe_id}.json"

    def create_chat(
        self,
        title: str = DEFAULT_CHAT_TITLE,
    ) -> dict[str, Any]:
        chat_id = generate_chat_id()
        timestamp = utc_now()

        chat = {
            "schema_version": 2,
            "id": chat_id,
            "title": normalise_title(title),
            "pinned": False,
            "archived": False,
            "created_at": timestamp,
            "updated_at": timestamp,
            "messages": [],
            "metadata": {},
        }

        self.save_chat(chat)

        return chat

    def save_chat(
        self,
        chat: dict[str, Any],
    ) -> dict[str, Any]:
        chat_id = str(
            chat.get("id", "")
        ).strip()

        if not chat_id:
            raise ChatStorageError(
                "Conversation does not have an ID."
            )

        repaired_chat = normalise_chat(
            chat,
            fallback_id=chat_id,
        )

        path = self.chat_path(chat_id)
        temporary_path = path.with_suffix(
            ".json.tmp"
        )

        try:
            temporary_path.write_text(
                json.dumps(
                    repaired_chat,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            os.replace(
                temporary_path,
                path,
            )

            return repaired_chat

        except OSError as exc:
            logger.exception(
                "Could not save chat %s",
                chat_id,
            )

            try:
                if temporary_path.exists():
                    temporary_path.unlink()
            except OSError:
                pass

            raise ChatStorageError(
                f"Could not save conversation: {exc}"
            ) from exc

    def load_chat(
        self,
        chat_id: str,
    ) -> dict[str, Any] | None:
        path = self.chat_path(chat_id)

        if not path.exists():
            return None

        try:
            raw_chat = json.loads(
                path.read_text(
                    encoding="utf-8",
                )
            )

            repaired_chat = normalise_chat(
                raw_chat,
                fallback_id=path.stem,
            )

            if repaired_chat != raw_chat:
                self.save_chat(
                    repaired_chat
                )

            return repaired_chat

        except json.JSONDecodeError as exc:
            logger.error(
                "Invalid chat JSON: %s",
                path,
            )

            raise ChatStorageError(
                f"Conversation file is invalid: {path.name}"
            ) from exc

        except OSError as exc:
            raise ChatStorageError(
                f"Could not open conversation: {exc}"
            ) from exc

    def list_chats(
        self,
        *,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        chats: list[dict[str, Any]] = []

        for path in self.chat_folder.glob(
            "*.json"
        ):
            try:
                chat = self.load_chat(
                    path.stem
                )

                if not chat:
                    continue

                if (
                    chat.get("archived", False)
                    and not include_archived
                ):
                    continue

                chats.append(chat)

            except ChatStorageError as exc:
                logger.warning(
                    "Skipping chat file %s: %s",
                    path.name,
                    exc,
                )

        chats.sort(
            key=lambda chat: (
                not bool(
                    chat.get("pinned", False)
                ),
                str(
                    chat.get(
                        "updated_at",
                        "",
                    )
                ),
            ),
            reverse=False,
        )

        pinned = [
            chat
            for chat in chats
            if chat.get("pinned", False)
        ]

        normal = [
            chat
            for chat in chats
            if not chat.get("pinned", False)
        ]

        pinned.sort(
            key=lambda chat: chat.get(
                "updated_at",
                "",
            ),
            reverse=True,
        )

        normal.sort(
            key=lambda chat: chat.get(
                "updated_at",
                "",
            ),
            reverse=True,
        )

        return pinned + normal

    def search_chats(
        self,
        query: str,
    ) -> list[dict[str, Any]]:
        chats = self.list_chats()

        cleaned_query = str(
            query or ""
        ).strip().lower()

        if not cleaned_query:
            return chats

        results: list[dict[str, Any]] = []

        for chat in chats:
            title = str(
                chat.get("title", "")
            ).lower()

            message_text = " ".join(
                str(
                    message.get(
                        "content",
                        "",
                    )
                )
                for message in chat.get(
                    "messages",
                    [],
                )
            ).lower()

            if (
                cleaned_query in title
                or cleaned_query in message_text
            ):
                results.append(chat)

        return results

    def add_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        *,
        attachments: list[dict[str, Any]]
        | None = None,
        metadata: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        chat = self.load_chat(chat_id)

        if chat is None:
            raise ChatStorageError(
                "Conversation was not found."
            )

        message = normalise_message(
            {
                "id": str(uuid.uuid4()),
                "role": role,
                "content": content,
                "created_at": utc_now(),
                "attachments": attachments or [],
                "metadata": metadata or {},
            }
        )

        if message is None:
            raise ChatStorageError(
                "Message is invalid."
            )

        chat["messages"].append(message)
        chat["updated_at"] = utc_now()

        if (
            role == "user"
            and chat.get("title")
            == DEFAULT_CHAT_TITLE
        ):
            chat["title"] = (
                generate_title_from_message(
                    content
                )
            )

        self.save_chat(chat)

        return message

    def replace_messages(
        self,
        chat_id: str,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        chat = self.load_chat(chat_id)

        if chat is None:
            raise ChatStorageError(
                "Conversation was not found."
            )

        repaired_messages = []

        for message in messages:
            repaired = normalise_message(
                message
            )

            if repaired:
                repaired_messages.append(
                    repaired
                )

        chat["messages"] = repaired_messages
        chat["updated_at"] = utc_now()

        return self.save_chat(chat)

    def rename_chat(
        self,
        chat_id: str,
        title: str,
    ) -> dict[str, Any]:
        chat = self.load_chat(chat_id)

        if chat is None:
            raise ChatStorageError(
                "Conversation was not found."
            )

        chat["title"] = normalise_title(
            title
        )

        chat["updated_at"] = utc_now()

        return self.save_chat(chat)

    def toggle_pin(
        self,
        chat_id: str,
    ) -> dict[str, Any]:
        chat = self.load_chat(chat_id)

        if chat is None:
            raise ChatStorageError(
                "Conversation was not found."
            )

        chat["pinned"] = not bool(
            chat.get("pinned", False)
        )

        chat["updated_at"] = utc_now()

        return self.save_chat(chat)

    def delete_chat(
        self,
        chat_id: str,
    ) -> bool:
        path = self.chat_path(chat_id)

        if not path.exists():
            return False

        try:
            path.unlink()
            return True

        except OSError as exc:
            raise ChatStorageError(
                f"Could not delete conversation: {exc}"
            ) from exc

    def migrate_all_chats(
        self,
    ) -> dict[str, int]:
        migrated = 0
        skipped = 0
        failed = 0

        for path in self.chat_folder.glob(
            "*.json"
        ):
            try:
                raw_chat = json.loads(
                    path.read_text(
                        encoding="utf-8",
                    )
                )

                repaired = normalise_chat(
                    raw_chat,
                    fallback_id=path.stem,
                )

                if repaired != raw_chat:
                    self.save_chat(repaired)
                    migrated += 1
                else:
                    skipped += 1

            except Exception:
                failed += 1

                logger.exception(
                    "Migration failed for %s",
                    path.name,
                )

        return {
            "migrated": migrated,
            "unchanged": skipped,
            "failed": failed,
        }
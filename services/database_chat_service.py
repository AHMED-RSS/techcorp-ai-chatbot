from __future__ import annotations

import base64
import uuid

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import (
    Session,
    selectinload,
    sessionmaker,
)

from core.exceptions import ChatStorageError
from database.connection import (
    DatabaseSessionFactory,
    get_session_factory,
)
from database.models import Chat, ChatMessage
from services.chat_service import (
    DEFAULT_CHAT_TITLE,
    generate_title_from_message,
    normalise_chat,
    normalise_message,
    normalise_title,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(
    value: Any,
    *,
    fallback: datetime | None = None,
) -> datetime:
    if isinstance(value, datetime):
        result = value
    else:
        text = str(value or "").strip()

        if not text:
            return fallback or utc_now()

        try:
            result = datetime.fromisoformat(
                text.replace("Z", "+00:00")
            )
        except ValueError:
            return fallback or utc_now()

    if result.tzinfo is None:
        result = result.replace(
            tzinfo=timezone.utc
        )

    return result


def format_datetime(
    value: datetime,
) -> str:
    if value.tzinfo is None:
        value = value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(
        timezone.utc
    ).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if value is None or isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(
        value,
        (bytes, bytearray, memoryview),
    ):
        return base64.b64encode(
            bytes(value)
        ).decode("ascii")

    if isinstance(value, datetime):
        return format_datetime(value)

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        (list, tuple, set),
    ):
        return [
            json_safe(item)
            for item in value
        ]

    return str(value)


class DatabaseChatService:
    """
    PostgreSQL conversation storage.

    Every query includes the authenticated Auth0 user ID.
    """

    def __init__(
        self,
        *,
        user_id: str,
        session_factory: (
            DatabaseSessionFactory
            | sessionmaker[Session]
            | None
        ) = None,
    ) -> None:
        cleaned_user_id = str(
            user_id or ""
        ).strip()

        if not cleaned_user_id:
            raise ValueError(
                "A user ID is required for chat storage."
            )

        self.user_id = cleaned_user_id

        self._session_factory = (
            session_factory
            or get_session_factory()
        )

    def _owned_chat(
        self,
        session: Session,
        chat_id: str,
        *,
        include_messages: bool = True,
    ) -> Chat | None:
        statement = select(Chat).where(
            Chat.chat_id == str(chat_id),
            Chat.user_id == self.user_id,
        )

        if include_messages:
            statement = statement.options(
                selectinload(Chat.messages)
            )

        return session.scalar(statement)

    @staticmethod
    def _message_to_dict(
        message: ChatMessage,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": message.message_id,
            "role": message.role,
            "content": message.content,
            "created_at": format_datetime(
                message.created_at
            ),
        }

        if message.attachments_json:
            result["attachments"] = json_safe(
                message.attachments_json
            )

        if message.metadata_json:
            result["metadata"] = json_safe(
                message.metadata_json
            )

        return result

    def _chat_to_dict(
        self,
        chat: Chat,
    ) -> dict[str, Any]:
        return {
            "schema_version": 3,
            "id": chat.chat_id,
            "title": chat.title,
            "pinned": chat.pinned,
            "archived": chat.archived,
            "created_at": format_datetime(
                chat.created_at
            ),
            "updated_at": format_datetime(
                chat.updated_at
            ),
            "messages": [
                self._message_to_dict(message)
                for message in chat.messages
            ],
            "metadata": json_safe(
                chat.metadata_json or {}
            ),
        }

    def create_chat(
        self,
        title: str = DEFAULT_CHAT_TITLE,
    ) -> dict[str, Any]:
        chat = Chat(
            chat_id=str(uuid.uuid4()),
            user_id=self.user_id,
            title=normalise_title(title),
            pinned=False,
            archived=False,
            metadata_json={},
        )

        with self._session_factory() as session:
            session.add(chat)
            session.commit()
            session.refresh(chat)

            return self._chat_to_dict(chat)

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

        repaired = normalise_chat(
            chat,
            fallback_id=chat_id,
        )

        with self._session_factory() as session:
            stored = session.get(
                Chat,
                chat_id,
            )

            if (
                stored is not None
                and stored.user_id != self.user_id
            ):
                raise ChatStorageError(
                    "Conversation was not found."
                )

            if stored is None:
                stored = Chat(
                    chat_id=chat_id,
                    user_id=self.user_id,
                    created_at=parse_datetime(
                        repaired.get("created_at")
                    ),
                )

                session.add(stored)

            stored.title = normalise_title(
                repaired.get("title", "")
            )

            stored.pinned = bool(
                repaired.get("pinned", False)
            )

            stored.archived = bool(
                repaired.get("archived", False)
            )

            stored.metadata_json = json_safe(
                repaired.get("metadata", {})
            )

            stored.updated_at = parse_datetime(
                repaired.get("updated_at")
            )

            session.execute(
                delete(ChatMessage).where(
                    ChatMessage.chat_id == chat_id,
                    ChatMessage.user_id
                    == self.user_id,
                )
            )

            session.flush()

            used_ids: set[str] = set()

            for raw_message in repaired.get(
                "messages",
                [],
            ):
                message = normalise_message(
                    raw_message
                )

                if message is None:
                    continue

                message_id = str(
                    message["id"]
                )

                if (
                    message_id in used_ids
                    or session.get(
                        ChatMessage,
                        message_id,
                    )
                    is not None
                ):
                    message_id = str(uuid.uuid4())

                used_ids.add(message_id)

                session.add(
                    ChatMessage(
                        message_id=message_id,
                        chat_id=chat_id,
                        user_id=self.user_id,
                        role=message["role"],
                        content=message["content"],
                        attachments_json=json_safe(
                            message.get(
                                "attachments",
                                [],
                            )
                        ),
                        metadata_json=json_safe(
                            message.get(
                                "metadata",
                                {},
                            )
                        ),
                        created_at=parse_datetime(
                            message.get(
                                "created_at"
                            )
                        ),
                    )
                )

            session.commit()

            saved = self._owned_chat(
                session,
                chat_id,
            )

            if saved is None:
                raise ChatStorageError(
                    "Conversation could not be saved."
                )

            return self._chat_to_dict(saved)

    def load_chat(
        self,
        chat_id: str,
    ) -> dict[str, Any] | None:
        with self._session_factory() as session:
            chat = self._owned_chat(
                session,
                chat_id,
            )

            if chat is None:
                return None

            return self._chat_to_dict(chat)

    def list_chats(
        self,
        *,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        statement = (
            select(Chat)
            .where(
                Chat.user_id == self.user_id
            )
            .options(
                selectinload(Chat.messages)
            )
        )

        if not include_archived:
            statement = statement.where(
                Chat.archived.is_(False)
            )

        statement = statement.order_by(
            Chat.pinned.desc(),
            Chat.updated_at.desc(),
        )

        with self._session_factory() as session:
            chats = session.scalars(
                statement
            ).all()

            return [
                self._chat_to_dict(chat)
                for chat in chats
            ]

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
        attachments: list[
            dict[str, Any]
        ] | None = None,
        metadata: dict[
            str,
            Any,
        ] | None = None,
    ) -> dict[str, Any]:
        message = normalise_message(
            {
                "id": str(uuid.uuid4()),
                "role": role,
                "content": content,
                "created_at": format_datetime(
                    utc_now()
                ),
                "attachments": attachments or [],
                "metadata": metadata or {},
            }
        )

        if message is None:
            raise ChatStorageError(
                "Message is invalid."
            )

        with self._session_factory() as session:
            chat = self._owned_chat(
                session,
                chat_id,
                include_messages=False,
            )

            if chat is None:
                raise ChatStorageError(
                    "Conversation was not found."
                )

            stored_message = ChatMessage(
                message_id=message["id"],
                chat_id=chat.chat_id,
                user_id=self.user_id,
                role=message["role"],
                content=message["content"],
                attachments_json=json_safe(
                    message.get(
                        "attachments",
                        [],
                    )
                ),
                metadata_json=json_safe(
                    message.get(
                        "metadata",
                        {},
                    )
                ),
                created_at=parse_datetime(
                    message["created_at"]
                ),
            )

            session.add(stored_message)

            if (
                role == "user"
                and chat.title
                == DEFAULT_CHAT_TITLE
            ):
                chat.title = (
                    generate_title_from_message(
                        content
                    )
                )

            chat.updated_at = utc_now()

            session.commit()
            session.refresh(stored_message)

            return self._message_to_dict(
                stored_message
            )

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

        chat["messages"] = messages
        chat["updated_at"] = format_datetime(
            utc_now()
        )

        return self.save_chat(chat)

    def rename_chat(
        self,
        chat_id: str,
        title: str,
    ) -> dict[str, Any]:
        with self._session_factory() as session:
            chat = self._owned_chat(
                session,
                chat_id,
            )

            if chat is None:
                raise ChatStorageError(
                    "Conversation was not found."
                )

            chat.title = normalise_title(title)
            chat.updated_at = utc_now()

            session.commit()

            return self._chat_to_dict(chat)

    def toggle_pin(
        self,
        chat_id: str,
    ) -> dict[str, Any]:
        with self._session_factory() as session:
            chat = self._owned_chat(
                session,
                chat_id,
            )

            if chat is None:
                raise ChatStorageError(
                    "Conversation was not found."
                )

            chat.pinned = not chat.pinned
            chat.updated_at = utc_now()

            session.commit()

            return self._chat_to_dict(chat)

    def delete_chat(
        self,
        chat_id: str,
    ) -> bool:
        with self._session_factory() as session:
            chat = self._owned_chat(
                session,
                chat_id,
                include_messages=False,
            )

            if chat is None:
                return False

            session.delete(chat)
            session.commit()

            return True

    def migrate_all_chats(
        self,
    ) -> dict[str, int]:
        # Old JSON chats do not contain a trustworthy owner ID,
        # so they are not imported automatically.
        return {
            "migrated": 0,
            "unchanged": 0,
            "failed": 0,
        }

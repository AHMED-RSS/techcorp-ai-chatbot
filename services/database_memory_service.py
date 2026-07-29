from __future__ import annotations

import base64

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from agents.memory import MemoryItem, TaskState
from core.exceptions import MemoryServiceError
from database.connection import (
    DatabaseSessionFactory,
    get_session_factory,
)
from database.models import (
    Chat,
    MemoryRecord,
    TaskSnapshot,
)
from services.memory_service import MemoryService


def utc_datetime() -> datetime:
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
            return fallback or utc_datetime()

        try:
            result = datetime.fromisoformat(
                text.replace("Z", "+00:00")
            )
        except ValueError:
            return fallback or utc_datetime()

    if result.tzinfo is None:
        result = result.replace(
            tzinfo=timezone.utc
        )

    return result


def format_datetime(
    value: datetime | None,
) -> str | None:
    if value is None:
        return None

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


class DatabaseMemoryService(MemoryService):
    """
    PostgreSQL memory and task storage.

    Every database operation is restricted to one user ID.
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
                "A user ID is required for memory storage."
            )

        self.user_id = cleaned_user_id

        self._session_factory = (
            session_factory
            or get_session_factory()
        )

    def _validate_chat(
        self,
        session: Session,
        chat_id: str | None,
    ) -> None:
        if chat_id is None:
            return

        owned_chat_id = session.scalar(
            select(Chat.chat_id).where(
                Chat.chat_id == chat_id,
                Chat.user_id == self.user_id,
            )
        )

        if owned_chat_id is None:
            raise MemoryServiceError(
                "Conversation was not found."
            )

    @staticmethod
    def _memory_to_item(
        record: MemoryRecord,
    ) -> MemoryItem:
        return MemoryItem(
            id=record.memory_id,
            content=record.content,
            kind=record.kind,
            keywords=list(
                record.keywords_json or []
            ),
            source=record.source,
            chat_id=record.chat_id,
            enabled=record.enabled,
            created_at=(
                format_datetime(
                    record.created_at
                )
                or ""
            ),
            updated_at=(
                format_datetime(
                    record.updated_at
                )
                or ""
            ),
            access_count=record.access_count,
            last_accessed_at=format_datetime(
                record.last_accessed_at
            ),
            metadata=dict(
                record.metadata_json or {}
            ),
        )

    @staticmethod
    def _task_to_state(
        record: TaskSnapshot,
    ) -> TaskState:
        return TaskState(
            id=record.task_id,
            chat_id=record.chat_id,
            user_request=record.user_request,
            goal=record.goal,
            status=record.status,
            route=record.route_json,
            plan=record.plan_json,
            execution=record.execution_json,
            critic=record.critic_json,
            final_output=record.final_output,
            created_at=(
                format_datetime(
                    record.created_at
                )
                or ""
            ),
            updated_at=(
                format_datetime(
                    record.updated_at
                )
                or ""
            ),
            metadata=dict(
                record.metadata_json or {}
            ),
        )

    def save_memory(
        self,
        item: MemoryItem,
    ) -> MemoryItem:
        memory_id = str(
            item.id or ""
        ).strip()

        if not memory_id:
            raise MemoryServiceError(
                "Memory does not have an ID."
            )

        now = utc_datetime()

        with self._session_factory() as session:
            self._validate_chat(
                session,
                item.chat_id,
            )

            record = session.get(
                MemoryRecord,
                memory_id,
            )

            if (
                record is not None
                and record.user_id
                != self.user_id
            ):
                raise MemoryServiceError(
                    "Memory was not found."
                )

            if record is None:
                record = MemoryRecord(
                    memory_id=memory_id,
                    user_id=self.user_id,
                    created_at=parse_datetime(
                        item.created_at,
                        fallback=now,
                    ),
                )

                session.add(record)

            record.chat_id = item.chat_id
            record.content = item.content
            record.kind = item.kind
            record.keywords_json = json_safe(
                item.keywords
            )
            record.source = item.source
            record.enabled = bool(
                item.enabled
            )
            record.access_count = max(
                0,
                int(item.access_count),
            )

            record.last_accessed_at = (
                parse_datetime(
                    item.last_accessed_at
                )
                if item.last_accessed_at
                else None
            )

            record.metadata_json = json_safe(
                item.metadata or {}
            )

            record.updated_at = now

            session.commit()
            session.refresh(record)

            return self._memory_to_item(
                record
            )

    def load_memory(
        self,
        memory_id: str,
    ) -> MemoryItem | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(MemoryRecord).where(
                    MemoryRecord.memory_id
                    == str(memory_id),
                    MemoryRecord.user_id
                    == self.user_id,
                )
            )

            if record is None:
                return None

            return self._memory_to_item(
                record
            )

    def list_memories(
        self,
        *,
        include_disabled: bool = True,
        chat_id: str | None = None,
        limit: int = 500,
    ) -> list[MemoryItem]:
        statement = select(
            MemoryRecord
        ).where(
            MemoryRecord.user_id
            == self.user_id
        )

        if not include_disabled:
            statement = statement.where(
                MemoryRecord.enabled.is_(True)
            )

        if chat_id is not None:
            statement = statement.where(
                or_(
                    MemoryRecord.chat_id.is_(
                        None
                    ),
                    MemoryRecord.chat_id
                    == chat_id,
                )
            )

        statement = statement.order_by(
            MemoryRecord.updated_at.desc(),
            MemoryRecord.created_at.desc(),
        ).limit(
            max(1, limit)
        )

        with self._session_factory() as session:
            records = session.scalars(
                statement
            ).all()

            return [
                self._memory_to_item(record)
                for record in records
            ]

    def delete_memory(
        self,
        memory_id: str,
    ) -> bool:
        with self._session_factory() as session:
            record = session.scalar(
                select(MemoryRecord).where(
                    MemoryRecord.memory_id
                    == str(memory_id),
                    MemoryRecord.user_id
                    == self.user_id,
                )
            )

            if record is None:
                return False

            session.delete(record)
            session.commit()

            return True

    def save_task_state(
        self,
        state: TaskState,
    ) -> TaskState:
        task_id = str(
            state.id or ""
        ).strip()

        if not task_id:
            raise MemoryServiceError(
                "Task state does not have an ID."
            )

        now = utc_datetime()

        with self._session_factory() as session:
            self._validate_chat(
                session,
                state.chat_id,
            )

            record = session.get(
                TaskSnapshot,
                task_id,
            )

            if (
                record is not None
                and record.user_id
                != self.user_id
            ):
                raise MemoryServiceError(
                    "Task state was not found."
                )

            if record is None:
                record = TaskSnapshot(
                    task_id=task_id,
                    user_id=self.user_id,
                    created_at=parse_datetime(
                        state.created_at,
                        fallback=now,
                    ),
                )

                session.add(record)

            record.chat_id = state.chat_id
            record.user_request = (
                state.user_request
            )
            record.goal = state.goal
            record.status = state.status
            record.route_json = json_safe(
                state.route
            )
            record.plan_json = json_safe(
                state.plan
            )
            record.execution_json = json_safe(
                state.execution
            )
            record.critic_json = json_safe(
                state.critic
            )
            record.final_output = (
                state.final_output or ""
            )
            record.metadata_json = json_safe(
                state.metadata or {}
            )
            record.updated_at = now

            session.commit()
            session.refresh(record)

            return self._task_to_state(
                record
            )

    def load_task_state(
        self,
        task_id: str,
    ) -> TaskState | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(TaskSnapshot).where(
                    TaskSnapshot.task_id
                    == str(task_id),
                    TaskSnapshot.user_id
                    == self.user_id,
                )
            )

            if record is None:
                return None

            return self._task_to_state(
                record
            )

    def list_task_states(
        self,
        *,
        chat_id: str | None = None,
        limit: int = 100,
    ) -> list[TaskState]:
        statement = select(
            TaskSnapshot
        ).where(
            TaskSnapshot.user_id
            == self.user_id
        )

        if chat_id is not None:
            statement = statement.where(
                TaskSnapshot.chat_id
                == chat_id
            )

        statement = statement.order_by(
            TaskSnapshot.updated_at.desc()
        ).limit(
            max(1, limit)
        )

        with self._session_factory() as session:
            records = session.scalars(
                statement
            ).all()

            return [
                self._task_to_state(record)
                for record in records
            ]

    def delete_task_state(
        self,
        task_id: str,
    ) -> bool:
        with self._session_factory() as session:
            record = session.scalar(
                select(TaskSnapshot).where(
                    TaskSnapshot.task_id
                    == str(task_id),
                    TaskSnapshot.user_id
                    == self.user_id,
                )
            )

            if record is None:
                return False

            session.delete(record)
            session.commit()

            return True

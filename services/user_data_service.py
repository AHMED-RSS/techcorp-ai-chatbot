from __future__ import annotations

import json
import shutil

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import Settings
from database.connection import (
    DatabaseSessionFactory,
    get_session_factory,
)
from database.models import (
    Chat,
    ChatMessage,
    DocumentRecord,
    MemoryRecord,
    StudySessionRecord,
    TaskSnapshot,
    User,
    UserSettings,
)
from services.database_file_service import (
    DatabaseFileService,
)
from services.database_rag_service import (
    DatabaseRAGService,
)


class UserDataError(
    RuntimeError
):
    """User export or local-account deletion failed."""


class UserDataService:
    """
    Export and delete data belonging to one authenticated user.

    This deletes the application's local account record and
    local application data. It does not delete the identity
    maintained by Auth0.
    """

    def __init__(
        self,
        *,
        user_id: str,
        settings: Settings,
        file_service: DatabaseFileService,
        rag_service: DatabaseRAGService,
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
            raise UserDataError(
                "A user ID is required for "
                "account-data controls."
            )

        self.user_id = cleaned_user_id
        self.settings = settings
        self.file_service = file_service
        self.rag_service = rag_service
        self.session_factory = (
            session_factory
            or get_session_factory()
        )

    @staticmethod
    def _datetime_text(
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
        ).isoformat(
            timespec="seconds"
        )

    @classmethod
    def _json_safe(
        cls,
        value: Any,
    ) -> Any:
        if value is None or isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        ):
            return value

        if isinstance(
            value,
            datetime,
        ):
            return cls._datetime_text(
                value
            )

        if isinstance(
            value,
            dict,
        ):
            return {
                str(key): cls._json_safe(
                    item
                )
                for key, item
                in value.items()
            }

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):
            return [
                cls._json_safe(item)
                for item in value
            ]

        return str(value)

    def export_data(
        self,
    ) -> dict[str, Any]:
        with self.session_factory() as session:
            user = session.get(
                User,
                self.user_id,
            )

            if user is None:
                raise UserDataError(
                    "The local user account "
                    "does not exist."
                )

            preferences = session.get(
                UserSettings,
                self.user_id,
            )

            chats = session.scalars(
                select(
                    Chat
                ).where(
                    Chat.user_id
                    == self.user_id
                ).order_by(
                    Chat.created_at
                )
            ).all()

            messages = session.scalars(
                select(
                    ChatMessage
                ).where(
                    ChatMessage.user_id
                    == self.user_id
                ).order_by(
                    ChatMessage.created_at
                )
            ).all()

            memories = session.scalars(
                select(
                    MemoryRecord
                ).where(
                    MemoryRecord.user_id
                    == self.user_id
                ).order_by(
                    MemoryRecord.created_at
                )
            ).all()

            tasks = session.scalars(
                select(
                    TaskSnapshot
                ).where(
                    TaskSnapshot.user_id
                    == self.user_id
                ).order_by(
                    TaskSnapshot.created_at
                )
            ).all()

            documents = session.scalars(
                select(
                    DocumentRecord
                ).where(
                    DocumentRecord.user_id
                    == self.user_id
                ).order_by(
                    DocumentRecord.created_at
                )
            ).all()

            study_sessions = session.scalars(
                select(
                    StudySessionRecord
                ).where(
                    StudySessionRecord.user_id
                    == self.user_id
                ).order_by(
                    StudySessionRecord.created_at
                )
            ).all()

            export = {
                "schema_version": 1,
                "exported_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat(
                        timespec="seconds"
                    )
                ),
                "scope": (
                    "TechCorp AI local "
                    "application data"
                ),
                "account": {
                    "user_id": user.user_id,
                    "email": user.email,
                    "name": user.name,
                    "avatar_url": (
                        user.avatar_url
                    ),
                    "email_verified": (
                        user.email_verified
                    ),
                    "created_at": (
                        self._datetime_text(
                            user.created_at
                        )
                    ),
                    "updated_at": (
                        self._datetime_text(
                            user.updated_at
                        )
                    ),
                },
                "preferences": (
                    {
                        "preferred_chat_model": (
                            preferences
                            .preferred_chat_model
                        ),
                        "theme": (
                            preferences.theme
                        ),
                        "created_at": (
                            self._datetime_text(
                                preferences
                                .created_at
                            )
                        ),
                        "updated_at": (
                            self._datetime_text(
                                preferences
                                .updated_at
                            )
                        ),
                    }
                    if preferences is not None
                    else None
                ),
                "chats": [
                    {
                        "chat_id": record.chat_id,
                        "title": record.title,
                        "pinned": record.pinned,
                        "archived": (
                            record.archived
                        ),
                        "metadata": dict(
                            record.metadata_json
                            or {}
                        ),
                        "created_at": (
                            self._datetime_text(
                                record.created_at
                            )
                        ),
                        "updated_at": (
                            self._datetime_text(
                                record.updated_at
                            )
                        ),
                    }
                    for record in chats
                ],
                "messages": [
                    {
                        "message_id": (
                            record.message_id
                        ),
                        "chat_id": (
                            record.chat_id
                        ),
                        "role": record.role,
                        "content": (
                            record.content
                        ),
                        "attachments": list(
                            record.attachments_json
                            or []
                        ),
                        "metadata": dict(
                            record.metadata_json
                            or {}
                        ),
                        "created_at": (
                            self._datetime_text(
                                record.created_at
                            )
                        ),
                    }
                    for record in messages
                ],
                "memories": [
                    {
                        "memory_id": (
                            record.memory_id
                        ),
                        "chat_id": (
                            record.chat_id
                        ),
                        "content": (
                            record.content
                        ),
                        "kind": record.kind,
                        "keywords": list(
                            record.keywords_json
                            or []
                        ),
                        "source": record.source,
                        "enabled": record.enabled,
                        "access_count": (
                            record.access_count
                        ),
                        "last_accessed_at": (
                            self._datetime_text(
                                record
                                .last_accessed_at
                            )
                        ),
                        "metadata": dict(
                            record.metadata_json
                            or {}
                        ),
                        "created_at": (
                            self._datetime_text(
                                record.created_at
                            )
                        ),
                        "updated_at": (
                            self._datetime_text(
                                record.updated_at
                            )
                        ),
                    }
                    for record in memories
                ],
                "tasks": [
                    {
                        "task_id": record.task_id,
                        "chat_id": record.chat_id,
                        "user_request": (
                            record.user_request
                        ),
                        "goal": record.goal,
                        "status": record.status,
                        "route": record.route_json,
                        "plan": record.plan_json,
                        "execution": (
                            record.execution_json
                        ),
                        "critic": (
                            record.critic_json
                        ),
                        "final_output": (
                            record.final_output
                        ),
                        "metadata": dict(
                            record.metadata_json
                            or {}
                        ),
                        "created_at": (
                            self._datetime_text(
                                record.created_at
                            )
                        ),
                        "updated_at": (
                            self._datetime_text(
                                record.updated_at
                            )
                        ),
                    }
                    for record in tasks
                ],
                "documents": [
                    {
                        "document_id": (
                            record.document_id
                        ),
                        "title": record.title,
                        "original_name": (
                            record.original_name
                        ),
                        "mime_type": (
                            record.mime_type
                        ),
                        "extension": (
                            record.extension
                        ),
                        "category": (
                            record.category
                        ),
                        "size_bytes": (
                            record.size_bytes
                        ),
                        "sha256": record.sha256,
                        "extracted_text": (
                            record.extracted_text
                        ),
                        "character_count": (
                            record.character_count
                        ),
                        "text_truncated": (
                            record.text_truncated
                        ),
                        "metadata": dict(
                            record.metadata_json
                            or {}
                        ),
                        "warnings": list(
                            record.warnings_json
                            or []
                        ),
                        "created_at": (
                            self._datetime_text(
                                record.created_at
                            )
                        ),
                        "updated_at": (
                            self._datetime_text(
                                record.updated_at
                            )
                        ),
                    }
                    for record in documents
                ],
                "study_sessions": [
                    {
                        "session_id": (
                            record.session_id
                        ),
                        "study_type": (
                            record.study_type
                        ),
                        "title": record.title,
                        "instruction": (
                            record.instruction
                        ),
                        "document_ids": list(
                            record.document_ids_json
                            or []
                        ),
                        "document_titles": list(
                            record
                            .document_titles_json
                            or []
                        ),
                        "model": record.model,
                        "content": record.content,
                        "flashcards": list(
                            record.flashcards_json
                            or []
                        ),
                        "quiz_questions": list(
                            record
                            .quiz_questions_json
                            or []
                        ),
                        "sources": list(
                            record.sources_json
                            or []
                        ),
                        "metadata": dict(
                            record.metadata_json
                            or {}
                        ),
                        "created_at": (
                            self._datetime_text(
                                record.created_at
                            )
                        ),
                        "updated_at": (
                            self._datetime_text(
                                record.updated_at
                            )
                        ),
                    }
                    for record
                    in study_sessions
                ],
            }

        export["counts"] = {
            "chats": len(
                export["chats"]
            ),
            "messages": len(
                export["messages"]
            ),
            "memories": len(
                export["memories"]
            ),
            "tasks": len(
                export["tasks"]
            ),
            "documents": len(
                export["documents"]
            ),
            "study_sessions": len(
                export["study_sessions"]
            ),
        }

        return self._json_safe(
            export
        )

    def export_json(
        self,
    ) -> bytes:
        return json.dumps(
            self.export_data(),
            ensure_ascii=False,
            indent=2,
        ).encode(
            "utf-8"
        )

    def _delete_runtime_folders(
        self,
    ) -> dict[str, int]:
        deleted_folders = 0

        for attribute in (
            "task_folder",
            "agent_run_folder",
            "report_folder",
        ):
            folder = Path(
                getattr(
                    self.settings,
                    attribute,
                )
            ).resolve()

            if folder.parent.name != "users":
                raise UserDataError(
                    "Refusing to delete a shared "
                    f"runtime folder: {attribute}."
                )

            if folder.exists():
                try:
                    shutil.rmtree(
                        folder
                    )

                except OSError as exc:
                    raise UserDataError(
                        "Could not delete the user's "
                        f"runtime files: {exc}"
                    ) from exc

                deleted_folders += 1

        return {
            "deleted_folders": (
                deleted_folders
            ),
        }

    def delete_local_account(
        self,
    ) -> dict[str, Any]:
        with self.session_factory() as session:
            user_exists = (
                session.get(
                    User,
                    self.user_id,
                )
                is not None
            )

        if not user_exists:
            return {
                "deleted": False,
                "user_id": self.user_id,
                "reason": (
                    "Local account not found"
                ),
            }

        try:
            rag_cleanup = (
                self.rag_service
                .delete_user_index()
            )

            file_cleanup = (
                self.file_service
                .delete_user_storage()
            )

            runtime_cleanup = (
                self._delete_runtime_folders()
            )

        except Exception as exc:
            if isinstance(
                exc,
                UserDataError,
            ):
                raise

            raise UserDataError(
                "Local account storage cleanup "
                f"failed: {exc}"
            ) from exc

        deletion_counts: dict[
            str,
            int,
        ] = {}

        try:
            with self.session_factory() as session:
                ordered_models = (
                    (
                        "messages",
                        ChatMessage,
                    ),
                    (
                        "memories",
                        MemoryRecord,
                    ),
                    (
                        "tasks",
                        TaskSnapshot,
                    ),
                    (
                        "study_sessions",
                        StudySessionRecord,
                    ),
                    (
                        "documents",
                        DocumentRecord,
                    ),
                    (
                        "chats",
                        Chat,
                    ),
                    (
                        "preferences",
                        UserSettings,
                    ),
                )

                for name, model in ordered_models:
                    result = session.execute(
                        delete(
                            model
                        ).where(
                            model.user_id
                            == self.user_id
                        )
                    )

                    deletion_counts[name] = int(
                        result.rowcount or 0
                    )

                user_result = session.execute(
                    delete(
                        User
                    ).where(
                        User.user_id
                        == self.user_id
                    )
                )

                deletion_counts["users"] = int(
                    user_result.rowcount or 0
                )

                session.commit()

        except Exception as exc:
            raise UserDataError(
                "Could not delete the local "
                f"account records: {exc}"
            ) from exc

        return {
            "deleted": bool(
                deletion_counts[
                    "users"
                ]
            ),
            "user_id": self.user_id,
            "database": deletion_counts,
            "rag": rag_cleanup,
            "document_storage": (
                file_cleanup
            ),
            "runtime_storage": (
                runtime_cleanup
            ),
            "auth0_identity_deleted": False,
        }

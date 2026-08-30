from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from agents.study import (
    StudySession,
    study_session_from_dict,
)
from config.settings import Settings
from core.exceptions import StudyError
from core.providers import (
    AIProvider,
)
from database.base import utc_now
from database.connection import (
    DatabaseSessionFactory,
    get_session_factory,
)
from database.models import (
    DocumentRecord,
    StudySessionRecord,
)
from services.file_service import FileService
from services.rag_service import RAGService
from services.study_service import StudyService


class DatabaseStudyService(StudyService):
    """
    User-scoped study-session persistence backed by PostgreSQL.

    Study generation and export behavior remain inherited from
    StudyService. Only save, load, list, and delete persistence
    are replaced.
    """

    def __init__(
        self,
        *,
        user_id: str,
        settings: Settings,
        ai_provider: AIProvider | None = None,
        ollama_manager: AIProvider | None = None,
        rag_service: RAGService,
        file_service: FileService,
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
            raise StudyError(
                "A user ID is required for study storage."
            )

        self.user_id = cleaned_user_id

        if ai_provider is None:
            ai_provider = ollama_manager

        self.session_factory = (
            session_factory
            or get_session_factory()
        )

        super().__init__(
            settings=settings,
            ai_provider=ai_provider,
            rag_service=rag_service,
            file_service=file_service,
        )

    @staticmethod
    def _datetime_text(
        value: datetime | str | None,
    ) -> str:
        if value is None:
            return ""

        if isinstance(
            value,
            datetime,
        ):
            return value.isoformat(
                timespec="seconds"
            )

        return str(value)

    @staticmethod
    def _dict_list(
        value: Any,
    ) -> list[dict[str, Any]]:
        if not isinstance(
            value,
            list,
        ):
            return []

        return [
            dict(item)
            for item in value
            if isinstance(
                item,
                dict,
            )
        ]

    @staticmethod
    def _string_list(
        value: Any,
    ) -> list[str]:
        if not isinstance(
            value,
            list,
        ):
            return []

        return [
            str(item)
            for item in value
            if str(item).strip()
        ]

    def _record_to_session(
        self,
        record: StudySessionRecord,
    ) -> StudySession:
        return study_session_from_dict(
            {
                "id": record.session_id,
                "study_type": record.study_type,
                "title": record.title,
                "instruction": record.instruction,
                "document_ids": list(
                    record.document_ids_json or []
                ),
                "document_titles": list(
                    record.document_titles_json or []
                ),
                "model": record.model,
                "content": record.content,
                "flashcards": list(
                    record.flashcards_json or []
                ),
                "quiz_questions": list(
                    record.quiz_questions_json or []
                ),
                "sources": list(
                    record.sources_json or []
                ),
                "metadata": dict(
                    record.metadata_json or {}
                ),
                "created_at": self._datetime_text(
                    record.created_at
                ),
                "updated_at": self._datetime_text(
                    record.updated_at
                ),
            }
        )

    def _verify_documents_owned(
        self,
        *,
        database_session: Session,
        document_ids: list[str],
    ) -> None:
        cleaned_ids = list(
            dict.fromkeys(
                str(document_id).strip()
                for document_id in document_ids
                if str(document_id).strip()
            )
        )

        if not cleaned_ids:
            return

        owned_ids = set(
            database_session.scalars(
                select(
                    DocumentRecord.document_id
                ).where(
                    DocumentRecord.user_id
                    == self.user_id,
                    DocumentRecord.document_id.in_(
                        cleaned_ids
                    ),
                )
            ).all()
        )

        if owned_ids != set(
            cleaned_ids
        ):
            raise StudyError(
                "One or more study documents do not "
                "belong to the authenticated user."
            )

    def save_session(
        self,
        session: StudySession,
    ) -> StudySession:
        session_id = str(
            session.id or ""
        ).strip()

        if not session_id:
            raise StudyError(
                "Invalid study session identifier."
            )

        with self.session_factory() as database_session:
            existing = database_session.get(
                StudySessionRecord,
                session_id,
            )

            if (
                existing is not None
                and existing.user_id
                != self.user_id
            ):
                raise StudyError(
                    "The study session belongs to "
                    "another user."
                )

            self._verify_documents_owned(
                database_session=database_session,
                document_ids=session.document_ids,
            )

            now = utc_now()

            if existing is None:
                record = StudySessionRecord(
                    session_id=session_id,
                    user_id=self.user_id,
                    study_type=session.study_type,
                    title=session.title,
                    instruction=session.instruction,
                    document_ids_json=list(
                        session.document_ids
                    ),
                    document_titles_json=list(
                        session.document_titles
                    ),
                    model=session.model,
                    content=session.content,
                    flashcards_json=[
                        card.to_dict()
                        for card in session.flashcards
                    ],
                    quiz_questions_json=[
                        question.to_dict()
                        for question
                        in session.quiz_questions
                    ],
                    sources_json=self._dict_list(
                        session.sources
                    ),
                    metadata_json=dict(
                        session.metadata or {}
                    ),
                    created_at=now,
                    updated_at=now,
                )

                database_session.add(
                    record
                )

            else:
                record = existing
                record.study_type = session.study_type
                record.title = session.title
                record.instruction = session.instruction
                record.document_ids_json = list(
                    session.document_ids
                )
                record.document_titles_json = list(
                    session.document_titles
                )
                record.model = session.model
                record.content = session.content
                record.flashcards_json = [
                    card.to_dict()
                    for card in session.flashcards
                ]
                record.quiz_questions_json = [
                    question.to_dict()
                    for question
                    in session.quiz_questions
                ]
                record.sources_json = self._dict_list(
                    session.sources
                )
                record.metadata_json = dict(
                    session.metadata or {}
                )
                record.updated_at = now

            database_session.commit()
            database_session.refresh(
                record
            )

            return self._record_to_session(
                record
            )

    def load_session(
        self,
        session_id: str,
    ) -> StudySession | None:
        cleaned_session_id = str(
            session_id or ""
        ).strip()

        if not cleaned_session_id:
            return None

        with self.session_factory() as database_session:
            record = database_session.scalar(
                select(
                    StudySessionRecord
                ).where(
                    StudySessionRecord.session_id
                    == cleaned_session_id,
                    StudySessionRecord.user_id
                    == self.user_id,
                )
            )

            if record is None:
                return None

            return self._record_to_session(
                record
            )

    def list_sessions(
        self,
        *,
        study_type: str | None = None,
        limit: int = 100,
    ) -> list[StudySession]:
        query = select(
            StudySessionRecord
        ).where(
            StudySessionRecord.user_id
            == self.user_id
        )

        cleaned_type = str(
            study_type or ""
        ).strip().lower()

        if cleaned_type:
            query = query.where(
                StudySessionRecord.study_type
                == cleaned_type
            )

        query = query.order_by(
            StudySessionRecord.updated_at.desc()
        ).limit(
            max(
                1,
                int(limit),
            )
        )

        with self.session_factory() as database_session:
            records = database_session.scalars(
                query
            ).all()

            return [
                self._record_to_session(
                    record
                )
                for record in records
            ]

    def delete_session(
        self,
        session_id: str,
    ) -> bool:
        cleaned_session_id = str(
            session_id or ""
        ).strip()

        if not cleaned_session_id:
            return False

        with self.session_factory() as database_session:
            record = database_session.scalar(
                select(
                    StudySessionRecord
                ).where(
                    StudySessionRecord.session_id
                    == cleaned_session_id,
                    StudySessionRecord.user_id
                    == self.user_id,
                )
            )

            if record is None:
                return False

            database_session.delete(
                record
            )

            database_session.commit()

            return True


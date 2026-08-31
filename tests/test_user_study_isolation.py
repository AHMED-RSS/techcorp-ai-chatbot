from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sqlalchemy import (
    create_engine,
    select,
)
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

from agents.study import (
    Flashcard,
    QuizQuestion,
    StudySession,
)
from config.settings import get_settings
from core.exceptions import StudyError
from database.base import Base
from database.models import (
    DocumentRecord,
    StudySessionRecord,
    User,
)
from services.database_study_service import (
    DatabaseStudyService,
)


class DummyDependency:
    pass


@pytest.fixture()
def study_services(
    tmp_path: Path,
) -> dict[str, Any]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(
        engine
    )

    factory = sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )

    with factory() as session:
        session.add_all(
            [
                User(
                    user_id="auth0|user-a",
                    email="a@example.com",
                    name="User A",
                ),
                User(
                    user_id="auth0|user-b",
                    email="b@example.com",
                    name="User B",
                ),
            ]
        )

        session.add_all(
            [
                DocumentRecord(
                    document_id="document-a",
                    user_id="auth0|user-a",
                    title="User A document",
                    original_name="a.txt",
                    stored_filename="a.txt",
                    stored_path=str(
                        tmp_path / "a.txt"
                    ),
                    mime_type="text/plain",
                    extension=".txt",
                    category="text",
                    size_bytes=10,
                    sha256="a" * 64,
                    extracted_text="Alpha material",
                    character_count=14,
                ),
                DocumentRecord(
                    document_id="document-b",
                    user_id="auth0|user-b",
                    title="User B document",
                    original_name="b.txt",
                    stored_filename="b.txt",
                    stored_path=str(
                        tmp_path / "b.txt"
                    ),
                    mime_type="text/plain",
                    extension=".txt",
                    category="text",
                    size_bytes=10,
                    sha256="b" * 64,
                    extracted_text="Beta material",
                    character_count=13,
                ),
            ]
        )

        session.commit()

    settings = get_settings().model_copy(
        update={
            "report_folder": (
                tmp_path / "reports"
            ),
        }
    )

    dependencies = {
        "settings": settings,
        "rag_service": DummyDependency(),
        "file_service": DummyDependency(),
        "session_factory": factory,
    }

    return {
        "factory": factory,
        "study_a": DatabaseStudyService(
            user_id="auth0|user-a",
            **dependencies,
        ),
        "study_b": DatabaseStudyService(
            user_id="auth0|user-b",
            **dependencies,
        ),
    }


def build_study_session(
    *,
    session_id: str,
    document_id: str,
    document_title: str,
    title: str,
    study_type: str = "summary",
) -> StudySession:
    return StudySession(
        id=session_id,
        study_type=study_type,
        title=title,
        instruction="Review the important points.",
        document_ids=[
            document_id
        ],
        document_titles=[
            document_title
        ],
        model="llama3.2",
        content="Private generated study content.",
        flashcards=[
            Flashcard(
                id="card-1",
                front="Question",
                back="Answer",
                source_labels=[
                    "Source 1"
                ],
            )
        ],
        quiz_questions=[
            QuizQuestion(
                id="question-1",
                question="Choose the answer.",
                options=[
                    "A",
                    "B",
                    "C",
                    "D",
                ],
                correct_index=1,
                explanation="B is correct.",
                source_labels=[
                    "Source 1"
                ],
            )
        ],
        sources=[
            {
                "document_id": document_id,
                "document_title": document_title,
                "text": "Private source passage.",
            }
        ],
        metadata={
            "detail_level": "balanced",
        },
    )


def test_study_session_is_hidden_from_other_user(
    study_services: dict[str, Any],
) -> None:
    study_a = study_services[
        "study_a"
    ]

    study_b = study_services[
        "study_b"
    ]

    saved = study_a.save_session(
        build_study_session(
            session_id="session-a",
            document_id="document-a",
            document_title="User A document",
            title="User A private summary",
        )
    )

    assert saved.id == "session-a"

    assert study_b.load_session(
        "session-a"
    ) is None

    assert study_b.list_sessions() == []

    assert study_b.delete_session(
        "session-a"
    ) is False

    loaded = study_a.load_session(
        "session-a"
    )

    assert loaded is not None

    assert loaded.title == (
        "User A private summary"
    )

    assert loaded.content == (
        "Private generated study content."
    )

    assert len(
        loaded.flashcards
    ) == 1

    assert len(
        loaded.quiz_questions
    ) == 1


def test_users_list_only_their_study_sessions(
    study_services: dict[str, Any],
) -> None:
    study_a = study_services[
        "study_a"
    ]

    study_b = study_services[
        "study_b"
    ]

    study_a.save_session(
        build_study_session(
            session_id="summary-a",
            document_id="document-a",
            document_title="User A document",
            title="Summary A",
            study_type="summary",
        )
    )

    study_b.save_session(
        build_study_session(
            session_id="quiz-b",
            document_id="document-b",
            document_title="User B document",
            title="Quiz B",
            study_type="quiz",
        )
    )

    sessions_a = study_a.list_sessions()

    sessions_b = study_b.list_sessions()

    assert [
        session.id
        for session in sessions_a
    ] == [
        "summary-a"
    ]

    assert [
        session.id
        for session in sessions_b
    ] == [
        "quiz-b"
    ]

    assert study_a.list_sessions(
        study_type="quiz"
    ) == []

    assert [
        session.id
        for session in study_b.list_sessions(
            study_type="quiz"
        )
    ] == [
        "quiz-b"
    ]


def test_user_cannot_save_other_users_document(
    study_services: dict[str, Any],
) -> None:
    study_a = study_services[
        "study_a"
    ]

    with pytest.raises(
        StudyError,
        match="do not belong",
    ):
        study_a.save_session(
            build_study_session(
                session_id="invalid-a",
                document_id="document-b",
                document_title="User B document",
                title="Invalid session",
            )
        )


def test_user_cannot_overwrite_other_users_session(
    study_services: dict[str, Any],
) -> None:
    study_a = study_services[
        "study_a"
    ]

    study_b = study_services[
        "study_b"
    ]

    study_a.save_session(
        build_study_session(
            session_id="shared-id",
            document_id="document-a",
            document_title="User A document",
            title="Original title",
        )
    )

    with pytest.raises(
        StudyError,
        match="another user",
    ):
        study_b.save_session(
            build_study_session(
                session_id="shared-id",
                document_id="document-b",
                document_title="User B document",
                title="Attempted overwrite",
            )
        )

    loaded = study_a.load_session(
        "shared-id"
    )

    assert loaded is not None
    assert loaded.title == "Original title"


def test_every_study_record_contains_owner_id(
    study_services: dict[str, Any],
) -> None:
    study_a = study_services[
        "study_a"
    ]

    factory = study_services[
        "factory"
    ]

    study_a.save_session(
        build_study_session(
            session_id="owner-test",
            document_id="document-a",
            document_title="User A document",
            title="Owner test",
        )
    )

    with factory() as session:
        records = session.scalars(
            select(
                StudySessionRecord
            )
        ).all()

    assert len(records) == 1

    assert records[0].user_id == (
        "auth0|user-a"
    )

    assert records[0].document_ids_json == [
        "document-a"
    ]

from __future__ import annotations

import json

from pathlib import Path
from typing import Any

import pytest

from sqlalchemy import (
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

from config.settings import get_settings
from database.base import Base
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
from services.user_data_service import (
    UserDataError,
    UserDataService,
)


class FakeFileCleanup:
    def __init__(
        self,
    ) -> None:
        self.calls = 0

    def delete_user_storage(
        self,
    ) -> dict[str, int]:
        self.calls += 1

        return {
            "deleted_folders": 2,
        }


class FakeRAGCleanup:
    def __init__(
        self,
    ) -> None:
        self.calls = 0

    def delete_user_index(
        self,
    ) -> dict[str, Any]:
        self.calls += 1

        return {
            "deleted": True,
            "collection": "user-test",
            "deleted_chunks": 3,
        }


def add_user_records(
    session: Session,
    *,
    suffix: str,
) -> None:
    user_id = f"auth0|user-{suffix}"
    chat_id = f"chat-{suffix}"
    document_id = f"document-{suffix}"

    session.add(
        User(
            user_id=user_id,
            email=f"{suffix}@example.com",
            name=f"User {suffix.upper()}",
        )
    )

    session.add(
        UserSettings(
            user_id=user_id,
            preferred_chat_model=(
                f"model-{suffix}"
            ),
            theme="dark",
        )
    )

    session.add(
        Chat(
            chat_id=chat_id,
            user_id=user_id,
            title=f"Private chat {suffix}",
        )
    )

    session.add(
        ChatMessage(
            message_id=f"message-{suffix}",
            chat_id=chat_id,
            user_id=user_id,
            role="user",
            content=(
                f"Private message {suffix}"
            ),
        )
    )

    session.add(
        MemoryRecord(
            memory_id=f"memory-{suffix}",
            user_id=user_id,
            chat_id=chat_id,
            content=(
                f"Private memory {suffix}"
            ),
            kind="note",
            keywords_json=[
                suffix
            ],
            source="test",
        )
    )

    session.add(
        TaskSnapshot(
            task_id=f"task-{suffix}",
            user_id=user_id,
            chat_id=chat_id,
            user_request=(
                f"Private request {suffix}"
            ),
            goal=f"Private goal {suffix}",
            status="completed",
            final_output=(
                f"Private output {suffix}"
            ),
        )
    )

    session.add(
        DocumentRecord(
            document_id=document_id,
            user_id=user_id,
            title=f"Private document {suffix}",
            original_name=f"{suffix}.txt",
            stored_filename=f"{suffix}.txt",
            stored_path=(
                f"C:/private/{suffix}.txt"
            ),
            mime_type="text/plain",
            extension=".txt",
            category="text",
            size_bytes=20,
            sha256=suffix * 64,
            extracted_text=(
                f"Private document text {suffix}"
            ),
            character_count=(
                len(
                    f"Private document text {suffix}"
                )
            ),
        )
    )

    session.add(
        StudySessionRecord(
            session_id=f"study-{suffix}",
            user_id=user_id,
            study_type="summary",
            title=f"Private study {suffix}",
            instruction=(
                f"Study instruction {suffix}"
            ),
            document_ids_json=[
                document_id
            ],
            document_titles_json=[
                f"Private document {suffix}"
            ],
            model=f"model-{suffix}",
            content=(
                f"Private study content {suffix}"
            ),
            flashcards_json=[],
            quiz_questions_json=[],
            sources_json=[],
            metadata_json={},
        )
    )


@pytest.fixture()
def user_data_environment(
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
        add_user_records(
            session,
            suffix="a",
        )

        add_user_records(
            session,
            suffix="b",
        )

        session.commit()

    user_key = "user-a"

    settings = get_settings().model_copy(
        update={
            "task_folder": (
                tmp_path
                / "tasks"
                / "users"
                / user_key
            ),
            "agent_run_folder": (
                tmp_path
                / "runs"
                / "users"
                / user_key
            ),
            "report_folder": (
                tmp_path
                / "reports"
                / "users"
                / user_key
            ),
        }
    )

    for folder in (
        settings.task_folder,
        settings.agent_run_folder,
        settings.report_folder,
    ):
        folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        (
            folder / "private.txt"
        ).write_text(
            "Private runtime data",
            encoding="utf-8",
        )

    file_cleanup = FakeFileCleanup()
    rag_cleanup = FakeRAGCleanup()

    service = UserDataService(
        user_id="auth0|user-a",
        settings=settings,
        file_service=file_cleanup,
        rag_service=rag_cleanup,
        session_factory=factory,
    )

    return {
        "factory": factory,
        "settings": settings,
        "file_cleanup": file_cleanup,
        "rag_cleanup": rag_cleanup,
        "service": service,
    }


def test_export_contains_only_authenticated_user_data(
    user_data_environment: dict[str, Any],
) -> None:
    service = user_data_environment[
        "service"
    ]

    export = service.export_data()

    assert export["account"]["user_id"] == (
        "auth0|user-a"
    )

    assert export["account"]["email"] == (
        "a@example.com"
    )

    assert export["counts"] == {
        "chats": 1,
        "messages": 1,
        "memories": 1,
        "tasks": 1,
        "documents": 1,
        "study_sessions": 1,
    }

    encoded = json.dumps(
        export
    )

    assert "Private message a" in encoded
    assert "Private study content a" in encoded

    assert "b@example.com" not in encoded
    assert "Private message b" not in encoded
    assert "Private study content b" not in encoded


def test_export_omits_local_document_paths(
    user_data_environment: dict[str, Any],
) -> None:
    service = user_data_environment[
        "service"
    ]

    encoded = service.export_json().decode(
        "utf-8"
    )

    assert "C:/private/a.txt" not in encoded

    assert (
        "Private document text a"
        in encoded
    )


def test_delete_removes_only_owned_database_records(
    user_data_environment: dict[str, Any],
) -> None:
    service = user_data_environment[
        "service"
    ]

    factory = user_data_environment[
        "factory"
    ]

    result = service.delete_local_account()

    assert result["deleted"] is True

    owned_models = (
        Chat,
        ChatMessage,
        MemoryRecord,
        TaskSnapshot,
        DocumentRecord,
        StudySessionRecord,
        UserSettings,
    )

    with factory() as session:
        assert session.get(
            User,
            "auth0|user-a",
        ) is None

        assert session.get(
            User,
            "auth0|user-b",
        ) is not None

        for model in owned_models:
            user_a_count = session.scalar(
                select(
                    func.count()
                ).select_from(
                    model
                ).where(
                    model.user_id
                    == "auth0|user-a"
                )
            )

            user_b_count = session.scalar(
                select(
                    func.count()
                ).select_from(
                    model
                ).where(
                    model.user_id
                    == "auth0|user-b"
                )
            )

            assert user_a_count == 0
            assert user_b_count == 1


def test_delete_cleans_only_user_runtime_storage(
    user_data_environment: dict[str, Any],
) -> None:
    service = user_data_environment[
        "service"
    ]

    settings = user_data_environment[
        "settings"
    ]

    file_cleanup = user_data_environment[
        "file_cleanup"
    ]

    rag_cleanup = user_data_environment[
        "rag_cleanup"
    ]

    service.delete_local_account()

    assert file_cleanup.calls == 1
    assert rag_cleanup.calls == 1

    assert not settings.task_folder.exists()

    assert not (
        settings.agent_run_folder
    ).exists()

    assert not settings.report_folder.exists()


def test_missing_account_is_not_cleaned(
    user_data_environment: dict[str, Any],
) -> None:
    factory = user_data_environment[
        "factory"
    ]

    settings = user_data_environment[
        "settings"
    ]

    file_cleanup = FakeFileCleanup()
    rag_cleanup = FakeRAGCleanup()

    service = UserDataService(
        user_id="auth0|missing",
        settings=settings,
        file_service=file_cleanup,
        rag_service=rag_cleanup,
        session_factory=factory,
    )

    result = service.delete_local_account()

    assert result["deleted"] is False
    assert file_cleanup.calls == 0
    assert rag_cleanup.calls == 0

    with pytest.raises(
        UserDataError,
        match="does not exist",
    ):
        service.export_data()

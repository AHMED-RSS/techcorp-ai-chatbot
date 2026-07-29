from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
import pytest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from config.settings import get_settings
from core.exceptions import (
    FileProcessingError,
    ToolExecutionError,
)
from database.base import Base
from database.models import (
    DocumentRecord,
    User,
)
from services import database_rag_service as rag_module
from services.database_file_service import (
    DatabaseFileService,
)
from services.database_rag_service import (
    DatabaseRAGService,
)
from tools.local_tools import (
    enforce_user_document_access,
)


class TemporaryUpload:
    def __init__(
        self,
        *,
        name: str,
        content: bytes,
    ) -> None:
        self.name = name
        self.type = "text/plain"
        self.size = len(content)
        self._content = content

    def getvalue(
        self,
    ) -> bytes:
        return self._content


class FakeOllama:
    def embed(
        self,
        text: str,
        model: str | None = None,
    ) -> list[float]:
        length = float(
            max(1, len(text))
        )

        return [
            1.0,
            length % 7 + 1.0,
            length % 11 + 1.0,
            length % 13 + 1.0,
        ]


@pytest.fixture()
def document_services(
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

        session.commit()

    settings = get_settings().model_copy(
        update={
            "upload_folder": (
                tmp_path / "uploads"
            ),
            "document_folder": (
                tmp_path / "documents"
            ),
            "chroma_folder": (
                tmp_path / "chroma"
            ),
        }
    )

    return {
        "factory": factory,
        "settings": settings,
        "files_a": DatabaseFileService(
            user_id="auth0|user-a",
            settings=settings,
            session_factory=factory,
        ),
        "files_b": DatabaseFileService(
            user_id="auth0|user-b",
            settings=settings,
            session_factory=factory,
        ),
    }


def test_document_is_hidden_from_other_user(
    document_services: dict[str, Any],
) -> None:
    files_a = document_services[
        "files_a"
    ]

    files_b = document_services[
        "files_b"
    ]

    factory = document_services[
        "factory"
    ]

    document = files_a.process_uploaded_file(
        TemporaryUpload(
            name="private-a.txt",
            content=(
                b"Private information for User A."
            ),
        )
    )

    document_id = document["id"]
    stored_path = Path(
        document["stored_path"]
    )

    assert document["user_id"] == (
        "auth0|user-a"
    )

    assert stored_path.exists()

    stored_path.resolve().relative_to(
        files_a.upload_folder.resolve()
    )

    assert files_b.load_document(
        document_id
    ) is None

    assert files_b.list_documents() == []

    assert files_b.delete_document(
        document_id
    ) is False

    assert files_a.load_document(
        document_id
    ) is not None

    with factory() as session:
        record = session.scalar(
            select(
                DocumentRecord
            ).where(
                DocumentRecord.document_id
                == document_id
            )
        )

    assert record is not None
    assert record.user_id == "auth0|user-a"

    assert files_a.delete_document(
        document_id
    )

    assert not stored_path.exists()


def test_user_upload_directories_are_separate(
    document_services: dict[str, Any],
) -> None:
    files_a = document_services[
        "files_a"
    ]

    files_b = document_services[
        "files_b"
    ]

    assert (
        files_a.upload_folder
        != files_b.upload_folder
    )

    assert (
        files_a.document_folder
        != files_b.document_folder
    )

    assert "auth0|user-a" not in str(
        files_a.upload_folder
    )

    assert "auth0|user-b" not in str(
        files_b.upload_folder
    )


def test_rag_collections_are_user_isolated(
    document_services: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared_client = (
        chromadb.EphemeralClient()
    )

    monkeypatch.setattr(
        rag_module.chromadb,
        "PersistentClient",
        lambda path: shared_client,
    )

    settings = document_services[
        "settings"
    ]

    rag_a = DatabaseRAGService(
        user_id="auth0|user-a",
        settings=settings,
        ollama_manager=FakeOllama(),
    )

    rag_b = DatabaseRAGService(
        user_id="auth0|user-b",
        settings=settings,
        ollama_manager=FakeOllama(),
    )

    document_a = {
        "id": "document-a",
        "user_id": "auth0|user-a",
        "title": "Private A",
        "original_name": "private-a.txt",
        "text": (
            "Alpha confidential information "
            "belongs only to User A."
        ),
    }

    indexed = rag_a.index_document(
        document_a
    )

    assert indexed["indexed"] is True
    assert rag_a.count_chunks() > 0
    assert rag_b.count_chunks() == 0

    assert rag_a.collection_name != (
        rag_b.collection_name
    )

    own_results = rag_a.search(
        query="alpha confidential information",
        document_ids=["document-a"],
        top_k=5,
    )

    other_results = rag_b.search(
        query="alpha confidential information",
        document_ids=["document-a"],
        top_k=5,
    )

    assert own_results
    assert other_results == []

    deletion = rag_b.delete_document(
        "document-a"
    )

    assert deletion[
        "deleted_chunks"
    ] == 0

    assert rag_a.count_chunks() > 0

    with pytest.raises(
        FileProcessingError,
        match="another user's document",
    ):
        rag_b.index_document(
            document_a
        )


def test_filesystem_tool_blocks_other_user_storage(
    document_services: dict[str, Any],
) -> None:
    settings = document_services[
        "settings"
    ]

    files_a = document_services[
        "files_a"
    ]

    files_b = document_services[
        "files_b"
    ]

    private_file = (
        files_a.upload_folder
        / "private.txt"
    )

    private_file.write_text(
        "User A private file",
        encoding="utf-8",
    )

    enforce_user_document_access(
        settings=settings,
        file_service=files_a,
        path=private_file,
    )

    with pytest.raises(
        ToolExecutionError,
        match="another user's document",
    ):
        enforce_user_document_access(
            settings=settings,
            file_service=files_b,
            path=private_file,
        )

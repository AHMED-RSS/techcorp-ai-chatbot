from __future__ import annotations

import hashlib
import json

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from config.settings import Settings
from core.exceptions import FileProcessingError
from database.connection import (
    DatabaseSessionFactory,
    get_session_factory,
)
from database.models import DocumentRecord
from parsers.local_parsers import (
    build_default_parser_registry,
)
from parsers.registry import ParserRegistry
from services.file_service import (
    FileService,
    UploadedFileProtocol,
)


def user_storage_key(
    user_id: str,
) -> str:
    """
    Produce a filesystem-safe stable folder key without
    exposing the Auth0 user identifier in the path.
    """

    return hashlib.sha256(
        user_id.encode("utf-8")
    ).hexdigest()[:24]


def json_object(
    value: Any,
) -> dict[str, Any]:
    try:
        converted = json.loads(
            json.dumps(
                value,
                default=str,
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        return {}

    return (
        converted
        if isinstance(converted, dict)
        else {}
    )


def string_list(
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
    ]


def integer_value(
    value: Any,
    default: int = 0,
) -> int:
    try:
        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


class DatabaseFileService(FileService):
    """
    User-scoped uploaded-file storage backed by PostgreSQL.

    Raw files are stored in a separate hashed directory for
    each user. Parsed metadata and extracted text are stored
    in the documents table.
    """

    def __init__(
        self,
        *,
        user_id: str,
        settings: Settings,
        registry: ParserRegistry | None = None,
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
            raise FileProcessingError(
                "A user ID is required for document storage."
            )

        self.user_id = cleaned_user_id
        self.settings = settings

        self.registry = (
            registry
            or build_default_parser_registry()
        )

        self.session_factory = (
            session_factory
            or get_session_factory()
        )

        storage_key = user_storage_key(
            self.user_id
        )

        self.upload_folder = (
            settings.upload_folder
            / "users"
            / storage_key
        )

        self.document_folder = (
            settings.document_folder
            / "users"
            / storage_key
        )

        self.upload_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.document_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

    def process_uploaded_file(
        self,
        uploaded_file: UploadedFileProtocol,
    ) -> dict[str, Any]:
        record = super().process_uploaded_file(
            uploaded_file
        )

        stored = self.load_document(
            str(record["id"])
        )

        if stored is None:
            raise FileProcessingError(
                "The processed document could not be loaded."
            )

        return stored

    def _owned_file_path(
        self,
        value: Any,
    ) -> Path:
        text = str(
            value or ""
        ).strip()

        if not text:
            raise FileProcessingError(
                "Document storage path is missing."
            )

        try:
            path = Path(
                text
            ).expanduser().resolve()

            upload_root = (
                self.upload_folder.resolve()
            )

            path.relative_to(
                upload_root
            )

        except (
            OSError,
            ValueError,
        ) as exc:
            raise FileProcessingError(
                "Document path is outside the "
                "authenticated user's upload folder."
            ) from exc

        return path

    @staticmethod
    def _datetime_text(
        value: Any,
    ) -> str:
        if value is None:
            return ""

        isoformat = getattr(
            value,
            "isoformat",
            None,
        )

        if callable(isoformat):
            return str(
                isoformat(
                    timespec="seconds"
                )
            )

        return str(value)

    def _record_to_dict(
        self,
        record: DocumentRecord,
    ) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "id": record.document_id,
            "document_id": record.document_id,
            "user_id": record.user_id,
            "title": record.title,
            "original_name": (
                record.original_name
            ),
            "stored_filename": (
                record.stored_filename
            ),
            "stored_path": record.stored_path,
            "mime_type": record.mime_type,
            "extension": record.extension,
            "category": record.category,
            "size_bytes": record.size_bytes,
            "sha256": record.sha256,
            "created_at": self._datetime_text(
                record.created_at
            ),
            "updated_at": self._datetime_text(
                record.updated_at
            ),
            "text": record.extracted_text,
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
                record.metadata_json or {}
            ),
            "warnings": list(
                record.warnings_json or []
            ),
        }

    def save_document_record(
        self,
        record: dict[str, Any],
    ) -> None:
        document_id = str(
            record.get("id")
            or record.get("document_id")
            or ""
        ).strip()

        if not document_id:
            raise FileProcessingError(
                "Document record has no ID."
            )

        stored_path = self._owned_file_path(
            record.get("stored_path")
        )

        try:
            with self.session_factory() as session:
                existing = session.get(
                    DocumentRecord,
                    document_id,
                )

                if (
                    existing is not None
                    and existing.user_id
                    != self.user_id
                ):
                    raise FileProcessingError(
                        "Document identifier belongs "
                        "to another user."
                    )

                if existing is None:
                    existing = DocumentRecord(
                        document_id=document_id,
                        user_id=self.user_id,
                        title="",
                        original_name="",
                        stored_filename="",
                        stored_path="",
                        mime_type=(
                            "application/octet-stream"
                        ),
                        extension="",
                        category="unknown",
                        size_bytes=0,
                        sha256="",
                        extracted_text="",
                        character_count=0,
                        text_truncated=False,
                        metadata_json={},
                        warnings_json=[],
                    )

                    session.add(
                        existing
                    )

                existing.title = str(
                    record.get("title")
                    or record.get(
                        "original_name"
                    )
                    or "Untitled document"
                )

                existing.original_name = str(
                    record.get("original_name")
                    or "uploaded_file"
                )

                existing.stored_filename = str(
                    record.get("stored_filename")
                    or stored_path.name
                )

                existing.stored_path = str(
                    stored_path
                )

                existing.mime_type = str(
                    record.get("mime_type")
                    or "application/octet-stream"
                )

                existing.extension = str(
                    record.get("extension")
                    or ""
                )

                existing.category = str(
                    record.get("category")
                    or "unknown"
                )

                existing.size_bytes = max(
                    0,
                    integer_value(
                        record.get("size_bytes")
                    ),
                )

                existing.sha256 = str(
                    record.get("sha256")
                    or ""
                )

                existing.extracted_text = str(
                    record.get("text")
                    or record.get(
                        "extracted_text"
                    )
                    or ""
                )

                existing.character_count = max(
                    0,
                    integer_value(
                        record.get(
                            "character_count"
                        ),
                        len(
                            existing.extracted_text
                        ),
                    ),
                )

                existing.text_truncated = bool(
                    record.get(
                        "text_truncated",
                        False,
                    )
                )

                existing.metadata_json = (
                    json_object(
                        record.get("metadata")
                    )
                )

                existing.warnings_json = (
                    string_list(
                        record.get("warnings")
                    )
                )

                session.commit()

        except FileProcessingError:
            raise

        except Exception as exc:
            raise FileProcessingError(
                "Could not save document metadata "
                f"to PostgreSQL: {exc}"
            ) from exc

    def load_document(
        self,
        document_id: str,
    ) -> dict[str, Any] | None:
        cleaned_id = str(
            document_id or ""
        ).strip()

        if not cleaned_id:
            return None

        try:
            with self.session_factory() as session:
                record = session.scalar(
                    select(
                        DocumentRecord
                    ).where(
                        DocumentRecord.document_id
                        == cleaned_id,
                        DocumentRecord.user_id
                        == self.user_id,
                    )
                )

                if record is None:
                    return None

                return self._record_to_dict(
                    record
                )

        except Exception as exc:
            raise FileProcessingError(
                "Could not load document "
                f"metadata: {exc}"
            ) from exc

    def list_documents(
        self,
    ) -> list[dict[str, Any]]:
        try:
            with self.session_factory() as session:
                records = list(
                    session.scalars(
                        select(
                            DocumentRecord
                        )
                        .where(
                            DocumentRecord.user_id
                            == self.user_id
                        )
                        .order_by(
                            DocumentRecord
                            .updated_at
                            .desc()
                        )
                    )
                )

                return [
                    self._record_to_dict(
                        record
                    )
                    for record in records
                ]

        except Exception as exc:
            raise FileProcessingError(
                "Could not list user documents: "
                f"{exc}"
            ) from exc

    def delete_document(
        self,
        document_id: str,
    ) -> bool:
        cleaned_id = str(
            document_id or ""
        ).strip()

        if not cleaned_id:
            return False

        try:
            with self.session_factory() as session:
                record = session.scalar(
                    select(
                        DocumentRecord
                    ).where(
                        DocumentRecord.document_id
                        == cleaned_id,
                        DocumentRecord.user_id
                        == self.user_id,
                    )
                )

                if record is None:
                    return False

                stored_path = self._owned_file_path(
                    record.stored_path
                )

                if stored_path.exists():
                    stored_path.unlink()

                session.delete(
                    record
                )

                session.commit()

                return True

        except FileProcessingError:
            raise

        except OSError as exc:
            raise FileProcessingError(
                f"Could not delete document file: {exc}"
            ) from exc

        except Exception as exc:
            raise FileProcessingError(
                "Could not delete document "
                f"metadata: {exc}"
            ) from exc

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from config.settings import Settings
from core.exceptions import (
    FileProcessingError,
)
from core.logging_config import get_logger
from parsers.local_parsers import (
    build_default_parser_registry,
    parse_unknown_file,
)
from parsers.registry import ParserRegistry


logger = get_logger(__name__)


class UploadedFileProtocol(Protocol):
    name: str
    type: str | None
    size: int

    def getvalue(self) -> bytes:
        ...


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat(
        timespec="seconds"
    )


def safe_filename(
    filename: str,
) -> str:
    name = Path(filename).name

    cleaned = re.sub(
        r"[^a-zA-Z0-9._-]",
        "_",
        name,
    )

    cleaned = re.sub(
        r"_+",
        "_",
        cleaned,
    ).strip("._")

    return cleaned or "uploaded_file"


def sha256_bytes(
    data: bytes,
) -> str:
    return hashlib.sha256(
        data
    ).hexdigest()


class FileService:
    """
    Local uploaded-file storage and parsing service.
    """

    def __init__(
        self,
        settings: Settings,
        registry: ParserRegistry | None = None,
    ) -> None:
        self.settings = settings

        self.upload_folder = (
            settings.upload_folder
        )

        self.document_folder = (
            settings.document_folder
        )

        self.registry = (
            registry
            or build_default_parser_registry()
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
        try:
            data = uploaded_file.getvalue()

        except Exception as exc:
            raise FileProcessingError(
                f"Could not read uploaded file: {exc}"
            ) from exc

        if not data:
            raise FileProcessingError(
                f"'{uploaded_file.name}' is empty."
            )

        maximum_bytes = (
            self.settings.max_upload_size_mb
            * 1024
            * 1024
        )

        if len(data) > maximum_bytes:
            raise FileProcessingError(
                f"'{uploaded_file.name}' exceeds "
                f"the {self.settings.max_upload_size_mb} MB limit."
            )

        document_id = str(
            uuid.uuid4()
        )

        original_name = safe_filename(
            uploaded_file.name
        )

        mime_type = (
            uploaded_file.type
            or mimetypes.guess_type(
                original_name
            )[0]
            or "application/octet-stream"
        )

        stored_filename = (
            f"{document_id}_{original_name}"
        )

        stored_path = (
            self.upload_folder
            / stored_filename
        )

        temporary_path = (
            stored_path.with_suffix(
                stored_path.suffix + ".tmp"
            )
        )

        try:
            temporary_path.write_bytes(
                data
            )

            os.replace(
                temporary_path,
                stored_path,
            )

        except OSError as exc:
            raise FileProcessingError(
                f"Could not store "
                f"'{original_name}': {exc}"
            ) from exc

        try:
            parsed = self.registry.parse(
                data=data,
                filename=original_name,
                mime_type=mime_type,
                fallback_parser=(
                    parse_unknown_file
                ),
            )

        except Exception as exc:
            logger.exception(
                "Parsing failed for %s",
                original_name,
            )

            parsed = parse_unknown_file(
                data,
                original_name,
                mime_type,
            )

            parsed.warnings.append(
                f"Specialised parsing failed: {exc}"
            )

        extracted_text = parsed.text[
            : self.settings
            .max_extracted_text_chars
        ]

        text_truncated = (
            len(parsed.text)
            > len(extracted_text)
        )

        if text_truncated:
            parsed.warnings.append(
                "Extracted text was truncated to the "
                "configured application limit."
            )

        record = {
            "schema_version": 1,
            "id": document_id,
            "title": parsed.title,
            "original_name": original_name,
            "stored_filename": stored_filename,
            "stored_path": str(stored_path),
            "mime_type": parsed.mime_type,
            "extension": parsed.extension,
            "category": parsed.category,
            "size_bytes": len(data),
            "sha256": sha256_bytes(data),
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "text": extracted_text,
            "character_count": len(
                extracted_text
            ),
            "text_truncated": text_truncated,
            "metadata": parsed.metadata,
            "warnings": parsed.warnings,
        }

        self.save_document_record(
            record
        )

        return record

    def process_uploaded_files(
        self,
        uploaded_files: list[
            UploadedFileProtocol
        ],
    ) -> tuple[
        list[dict[str, Any]],
        list[str],
    ]:
        processed: list[
            dict[str, Any]
        ] = []

        errors: list[str] = []

        limited_files = uploaded_files[
            : self.settings
            .max_files_per_message
        ]

        for uploaded_file in limited_files:
            try:
                processed.append(
                    self.process_uploaded_file(
                        uploaded_file
                    )
                )

            except FileProcessingError as exc:
                errors.append(str(exc))

        if (
            len(uploaded_files)
            > len(limited_files)
        ):
            errors.append(
                "Some files were skipped because "
                "the maximum files-per-message limit "
                "was reached."
            )

        return processed, errors

    def record_path(
        self,
        document_id: str,
    ) -> Path:
        safe_id = re.sub(
            r"[^a-zA-Z0-9_-]",
            "",
            document_id,
        )

        if not safe_id:
            raise FileProcessingError(
                "Invalid document identifier."
            )

        return (
            self.document_folder
            / f"{safe_id}.json"
        )

    def save_document_record(
        self,
        record: dict[str, Any],
    ) -> None:
        document_id = str(
            record.get("id", "")
        ).strip()

        if not document_id:
            raise FileProcessingError(
                "Document record has no ID."
            )

        path = self.record_path(
            document_id
        )

        temporary_path = path.with_suffix(
            ".json.tmp"
        )

        try:
            temporary_path.write_text(
                json.dumps(
                    record,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            os.replace(
                temporary_path,
                path,
            )

        except OSError as exc:
            raise FileProcessingError(
                f"Could not save document "
                f"metadata: {exc}"
            ) from exc

    def load_document(
        self,
        document_id: str,
    ) -> dict[str, Any] | None:
        path = self.record_path(
            document_id
        )

        if not path.exists():
            return None

        try:
            return json.loads(
                path.read_text(
                    encoding="utf-8",
                )
            )

        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise FileProcessingError(
                f"Could not load document "
                f"record: {exc}"
            ) from exc

    def list_documents(
        self,
    ) -> list[dict[str, Any]]:
        records: list[
            dict[str, Any]
        ] = []

        for path in (
            self.document_folder.glob(
                "*.json"
            )
        ):
            try:
                record = json.loads(
                    path.read_text(
                        encoding="utf-8",
                    )
                )

                if isinstance(record, dict):
                    records.append(record)

            except Exception:
                logger.exception(
                    "Skipping invalid document "
                    "record %s",
                    path.name,
                )

        records.sort(
            key=lambda item: str(
                item.get(
                    "updated_at",
                    "",
                )
            ),
            reverse=True,
        )

        return records

    def delete_document(
        self,
        document_id: str,
    ) -> bool:
        record = self.load_document(
            document_id
        )

        if record is None:
            return False

        stored_path = Path(
            str(
                record.get(
                    "stored_path",
                    "",
                )
            )
        )

        metadata_path = self.record_path(
            document_id
        )

        try:
            if stored_path.exists():
                stored_path.unlink()

            if metadata_path.exists():
                metadata_path.unlink()

            return True

        except OSError as exc:
            raise FileProcessingError(
                f"Could not delete document: {exc}"
            ) from exc

    def get_documents(
        self,
        document_ids: list[str],
    ) -> list[dict[str, Any]]:
        records: list[
            dict[str, Any]
        ] = []

        for document_id in document_ids:
            record = self.load_document(
                document_id
            )

            if record:
                records.append(record)

        return records

    def build_document_context(
        self,
        document_ids: list[str],
        *,
        maximum_characters: int = 30_000,
    ) -> str:
        records = self.get_documents(
            document_ids
        )

        sections: list[str] = []
        total_length = 0

        for record in records:
            remaining = (
                maximum_characters
                - total_length
            )

            if remaining <= 0:
                break

            title = str(
                record.get(
                    "title",
                    "Untitled document",
                )
            )

            text = str(
                record.get(
                    "text",
                    "",
                )
            )

            section = (
                f"[Document: {title}]\n"
                f"{text}"
            )

            section = section[:remaining]

            sections.append(section)

            total_length += len(section)

        return "\n\n".join(
            sections
        )
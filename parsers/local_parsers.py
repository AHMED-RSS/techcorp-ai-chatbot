from __future__ import annotations

import csv
import io
import json
import mimetypes
import re
import zipfile

from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from docx import Document
from openpyxl import load_workbook
from PIL import Image
from pypdf import PdfReader
from pptx import Presentation

from parsers.models import ParsedFile
from parsers.registry import ParserRegistry


TEXT_EXTENSIONS = {
    "txt",
    "md",
    "markdown",
    "rst",
    "log",
    "ini",
    "cfg",
    "conf",
    "toml",
    "yaml",
    "yml",
}

CODE_EXTENSIONS = {
    "py",
    "js",
    "jsx",
    "ts",
    "tsx",
    "java",
    "c",
    "h",
    "cpp",
    "hpp",
    "cs",
    "go",
    "rs",
    "php",
    "rb",
    "swift",
    "kt",
    "kts",
    "scala",
    "sh",
    "bash",
    "ps1",
    "bat",
    "cmd",
    "html",
    "htm",
    "css",
    "scss",
    "sql",
    "r",
    "dart",
    "vue",
    "svelte",
}

IMAGE_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp",
    "bmp",
    "gif",
    "tif",
    "tiff",
}

SAFE_ARCHIVE_TEXT_EXTENSIONS = (
    TEXT_EXTENSIONS
    | CODE_EXTENSIONS
    | {
        "csv",
        "json",
        "xml",
    }
)


def clean_title(
    filename: str,
) -> str:
    stem = Path(filename).stem

    cleaned = re.sub(
        r"[_-]+",
        " ",
        stem,
    )

    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned,
    ).strip()

    return cleaned or filename


def decode_text_bytes(
    data: bytes,
) -> tuple[str, str]:
    encodings = (
        "utf-8",
        "utf-8-sig",
        "utf-16",
        "cp1252",
        "latin-1",
    )

    for encoding in encodings:
        try:
            return (
                data.decode(encoding),
                encoding,
            )

        except UnicodeDecodeError:
            continue

    return (
        data.decode(
            "utf-8",
            errors="replace",
        ),
        "utf-8-replacement",
    )


def parse_plain_text(
    data: bytes,
    filename: str,
    mime_type: str,
) -> ParsedFile:
    text, encoding = decode_text_bytes(
        data
    )

    extension = (
        Path(filename)
        .suffix
        .lower()
        .lstrip(".")
    )

    return ParsedFile(
        title=clean_title(filename),
        text=text,
        category="text",
        mime_type=mime_type,
        extension=extension,
        metadata={
            "encoding": encoding,
            "line_count": (
                len(text.splitlines())
            ),
        },
    )


def parse_source_code(
    data: bytes,
    filename: str,
    mime_type: str,
) -> ParsedFile:
    text, encoding = decode_text_bytes(
        data
    )

    extension = (
        Path(filename)
        .suffix
        .lower()
        .lstrip(".")
    )

    return ParsedFile(
        title=filename,
        text=text,
        category="code",
        mime_type=mime_type,
        extension=extension,
        metadata={
            "language_hint": extension,
            "encoding": encoding,
            "line_count": (
                len(text.splitlines())
            ),
        },
    )


def parse_pdf(
    data: bytes,
    filename: str,
    mime_type: str,
) -> ParsedFile:
    reader = PdfReader(
        io.BytesIO(data)
    )

    pages: list[str] = []
    warnings: list[str] = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        try:
            page_text = (
                page.extract_text()
                or ""
            ).strip()

        except Exception as exc:
            page_text = ""

            warnings.append(
                f"Page {page_number} could not "
                f"be extracted: {exc}"
            )

        if page_text:
            pages.append(
                f"[Page {page_number}]\n"
                f"{page_text}"
            )

    text = "\n\n".join(pages)

    if not text:
        warnings.append(
            "No selectable text was found. "
            "This may be a scanned or image-only PDF."
        )

    metadata: dict[str, Any] = {
        "page_count": len(reader.pages),
    }

    if reader.metadata:
        metadata.update(
            {
                "pdf_title": (
                    reader.metadata.title
                ),
                "author": (
                    reader.metadata.author
                ),
                "subject": (
                    reader.metadata.subject
                ),
            }
        )

    title = (
        str(
            metadata.get("pdf_title")
            or ""
        ).strip()
        or clean_title(filename)
    )

    return ParsedFile(
        title=title,
        text=text,
        category="document",
        mime_type=mime_type,
        extension="pdf",
        metadata=metadata,
        warnings=warnings,
    )


def parse_docx(
    data: bytes,
    filename: str,
    mime_type: str,
) -> ParsedFile:
    document = Document(
        io.BytesIO(data)
    )

    parts: list[str] = []

    for paragraph in document.paragraphs:
        paragraph_text = (
            paragraph.text.strip()
        )

        if paragraph_text:
            parts.append(paragraph_text)

    table_count = 0

    for table in document.tables:
        table_count += 1

        for row in table.rows:
            row_values = [
                cell.text.strip()
                for cell in row.cells
            ]

            if any(row_values):
                parts.append(
                    " | ".join(row_values)
                )

    text = "\n\n".join(parts)

    return ParsedFile(
        title=clean_title(filename),
        text=text,
        category="document",
        mime_type=mime_type,
        extension="docx",
        metadata={
            "paragraph_count": len(
                document.paragraphs
            ),
            "table_count": table_count,
        },
    )


def parse_csv_file(
    data: bytes,
    filename: str,
    mime_type: str,
) -> ParsedFile:
    decoded, encoding = decode_text_bytes(
        data
    )

    sample = decoded[:4096]

    try:
        dialect = csv.Sniffer().sniff(
            sample
        )

    except csv.Error:
        dialect = csv.excel

    reader = csv.reader(
        io.StringIO(decoded),
        dialect=dialect,
    )

    rows: list[list[str]] = []

    for row_number, row in enumerate(
        reader,
        start=1,
    ):
        rows.append(row)

        if row_number >= 5000:
            break

    text_lines = [
        " | ".join(
            str(value)
            for value in row
        )
        for row in rows
    ]

    return ParsedFile(
        title=clean_title(filename),
        text="\n".join(text_lines),
        category="data",
        mime_type=mime_type,
        extension="csv",
        metadata={
            "encoding": encoding,
            "row_count_loaded": len(rows),
            "column_count": max(
                (
                    len(row)
                    for row in rows
                ),
                default=0,
            ),
            "truncated_rows": (
                len(rows) >= 5000
            ),
        },
    )


def parse_json_file(
    data: bytes,
    filename: str,
    mime_type: str,
) -> ParsedFile:
    decoded, encoding = decode_text_bytes(
        data
    )

    parsed = json.loads(decoded)

    formatted = json.dumps(
        parsed,
        indent=2,
        ensure_ascii=False,
    )

    root_type = type(
        parsed
    ).__name__

    item_count = (
        len(parsed)
        if isinstance(
            parsed,
            (dict, list),
        )
        else 1
    )

    return ParsedFile(
        title=clean_title(filename),
        text=formatted,
        category="data",
        mime_type=mime_type,
        extension="json",
        metadata={
            "encoding": encoding,
            "root_type": root_type,
            "item_count": item_count,
        },
    )


def parse_xml_file(
    data: bytes,
    filename: str,
    mime_type: str,
) -> ParsedFile:
    root = ElementTree.fromstring(data)

    lines: list[str] = []

    for element in root.iter():
        text = (
            element.text
            or ""
        ).strip()

        attributes = " ".join(
            f"{key}={value}"
            for key, value
            in element.attrib.items()
        )

        value = " ".join(
            part
            for part in (
                element.tag,
                attributes,
                text,
            )
            if part
        )

        if value:
            lines.append(value)

    return ParsedFile(
        title=clean_title(filename),
        text="\n".join(lines),
        category="data",
        mime_type=mime_type,
        extension="xml",
        metadata={
            "root_tag": root.tag,
            "element_count": len(lines),
        },
    )


def parse_xlsx(
    data: bytes,
    filename: str,
    mime_type: str,
) -> ParsedFile:
    workbook = load_workbook(
        filename=io.BytesIO(data),
        read_only=True,
        data_only=True,
    )

    output: list[str] = []
    sheet_metadata: list[
        dict[str, Any]
    ] = []

    for sheet in workbook.worksheets:
        output.append(
            f"[Sheet: {sheet.title}]"
        )

        loaded_rows = 0
        maximum_columns = 0

        for row in sheet.iter_rows(
            values_only=True
        ):
            values = [
                "" if value is None
                else str(value)
                for value in row
            ]

            if not any(values):
                continue

            output.append(
                " | ".join(values)
            )

            loaded_rows += 1
            maximum_columns = max(
                maximum_columns,
                len(values),
            )

            if loaded_rows >= 5000:
                output.append(
                    "[Sheet truncated after "
                    "5000 non-empty rows]"
                )
                break

        sheet_metadata.append(
            {
                "name": sheet.title,
                "rows_loaded": loaded_rows,
                "columns": maximum_columns,
            }
        )

        output.append("")

    workbook.close()

    return ParsedFile(
        title=clean_title(filename),
        text="\n".join(output),
        category="data",
        mime_type=mime_type,
        extension="xlsx",
        metadata={
            "sheet_count": len(
                sheet_metadata
            ),
            "sheets": sheet_metadata,
        },
    )


def parse_pptx(
    data: bytes,
    filename: str,
    mime_type: str,
) -> ParsedFile:
    presentation = Presentation(
        io.BytesIO(data)
    )

    output: list[str] = []

    for slide_number, slide in enumerate(
        presentation.slides,
        start=1,
    ):
        slide_lines: list[str] = []

        for shape in slide.shapes:
            if hasattr(shape, "text"):
                shape_text = (
                    shape.text
                    or ""
                ).strip()

                if shape_text:
                    slide_lines.append(
                        shape_text
                    )

        if slide_lines:
            output.append(
                f"[Slide {slide_number}]\n"
                + "\n".join(
                    slide_lines
                )
            )

    return ParsedFile(
        title=clean_title(filename),
        text="\n\n".join(output),
        category="presentation",
        mime_type=mime_type,
        extension="pptx",
        metadata={
            "slide_count": len(
                presentation.slides
            ),
        },
    )


def parse_image(
    data: bytes,
    filename: str,
    mime_type: str,
) -> ParsedFile:
    warnings: list[str] = []

    with Image.open(
        io.BytesIO(data)
    ) as image:
        width, height = image.size
        image_format = (
            image.format or ""
        )
        mode = image.mode

        metadata = {
            "width": width,
            "height": height,
            "format": image_format,
            "colour_mode": mode,
            "animated": bool(
                getattr(
                    image,
                    "is_animated",
                    False,
                )
            ),
        }

    warnings.append(
        "The image was recognised, but visual "
        "understanding is not connected yet."
    )

    text = (
        f"Image file: {filename}\n"
        f"Format: {image_format}\n"
        f"Dimensions: {width} x {height}\n"
        f"Colour mode: {mode}"
    )

    return ParsedFile(
        title=clean_title(filename),
        text=text,
        category="image",
        mime_type=mime_type,
        extension=(
            Path(filename)
            .suffix
            .lower()
            .lstrip(".")
        ),
        metadata=metadata,
        warnings=warnings,
    )


def parse_zip_archive(
    data: bytes,
    filename: str,
    mime_type: str,
) -> ParsedFile:
    output: list[str] = []
    warnings: list[str] = []

    entry_count = 0
    total_uncompressed_size = 0
    extracted_text_entries = 0

    maximum_entries = 100
    maximum_uncompressed_size = (
        20 * 1024 * 1024
    )

    with zipfile.ZipFile(
        io.BytesIO(data)
    ) as archive:
        entries = archive.infolist()

        for entry in entries:
            if entry.is_dir():
                continue

            entry_count += 1

            if entry_count > maximum_entries:
                warnings.append(
                    "Archive processing stopped after "
                    f"{maximum_entries} files."
                )
                break

            total_uncompressed_size += (
                entry.file_size
            )

            if (
                total_uncompressed_size
                > maximum_uncompressed_size
            ):
                warnings.append(
                    "Archive processing stopped because "
                    "the uncompressed size limit was reached."
                )
                break

            entry_path = Path(
                entry.filename
            )

            if (
                entry_path.is_absolute()
                or ".."
                in entry_path.parts
            ):
                warnings.append(
                    f"Unsafe archive path skipped: "
                    f"{entry.filename}"
                )
                continue

            extension = (
                entry_path
                .suffix
                .lower()
                .lstrip(".")
            )

            output.append(
                f"[Archive file: "
                f"{entry.filename}]"
            )

            if (
                extension
                not in SAFE_ARCHIVE_TEXT_EXTENSIONS
            ):
                output.append(
                    "Binary or unsupported archive entry."
                )
                output.append("")
                continue

            try:
                entry_data = archive.read(
                    entry
                )

                entry_text, _ = (
                    decode_text_bytes(
                        entry_data
                    )
                )

                output.append(entry_text)
                output.append("")

                extracted_text_entries += 1

            except Exception as exc:
                warnings.append(
                    f"Could not read "
                    f"{entry.filename}: {exc}"
                )

    return ParsedFile(
        title=clean_title(filename),
        text="\n".join(output),
        category="archive",
        mime_type=mime_type,
        extension="zip",
        metadata={
            "entries_seen": entry_count,
            "text_entries_extracted": (
                extracted_text_entries
            ),
            "uncompressed_bytes_seen": (
                total_uncompressed_size
            ),
        },
        warnings=warnings,
    )


def parse_unknown_file(
    data: bytes,
    filename: str,
    mime_type: str,
) -> ParsedFile:
    extension = (
        Path(filename)
        .suffix
        .lower()
        .lstrip(".")
    )

    guessed_mime = (
        mime_type
        or mimetypes.guess_type(
            filename
        )[0]
        or "application/octet-stream"
    )

    warnings = [
        "The file type was recognised by name or MIME "
        "metadata, but no specialised parser is installed."
    ]

    text = (
        f"Filename: {filename}\n"
        f"Detected MIME type: {guessed_mime}\n"
        f"Extension: {extension or 'none'}\n"
        f"Size: {len(data)} bytes"
    )

    return ParsedFile(
        title=clean_title(filename),
        text=text,
        category="unknown",
        mime_type=guessed_mime,
        extension=extension,
        metadata={
            "size_bytes": len(data),
        },
        warnings=warnings,
    )


def build_default_parser_registry(
) -> ParserRegistry:
    registry = ParserRegistry()

    registry.register(
        extensions=("pdf",),
        mime_types=(
            "application/pdf",
        ),
        parser=parse_pdf,
        category="document",
    )

    registry.register(
        extensions=("docx",),
        mime_types=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        parser=parse_docx,
        category="document",
    )

    registry.register(
        extensions=tuple(
            sorted(TEXT_EXTENSIONS)
        ),
        mime_types=(
            "text/plain",
            "text/markdown",
        ),
        parser=parse_plain_text,
        category="text",
    )

    registry.register(
        extensions=tuple(
            sorted(CODE_EXTENSIONS)
        ),
        mime_types=(
            "text/x-python",
            "text/javascript",
            "application/javascript",
            "text/html",
            "text/css",
        ),
        parser=parse_source_code,
        category="code",
    )

    registry.register(
        extensions=("csv",),
        mime_types=(
            "text/csv",
            "application/csv",
        ),
        parser=parse_csv_file,
        category="data",
    )

    registry.register(
        extensions=("json",),
        mime_types=(
            "application/json",
            "text/json",
        ),
        parser=parse_json_file,
        category="data",
    )

    registry.register(
        extensions=("xml",),
        mime_types=(
            "application/xml",
            "text/xml",
        ),
        parser=parse_xml_file,
        category="data",
    )

    registry.register(
        extensions=("xlsx", "xlsm"),
        mime_types=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel.sheet.macroenabled.12",
        ),
        parser=parse_xlsx,
        category="data",
    )

    registry.register(
        extensions=("pptx",),
        mime_types=(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ),
        parser=parse_pptx,
        category="presentation",
    )

    registry.register(
        extensions=tuple(
            sorted(IMAGE_EXTENSIONS)
        ),
        mime_types=("image/*",),
        parser=parse_image,
        category="image",
    )

    registry.register(
        extensions=("zip",),
        mime_types=(
            "application/zip",
            "application/x-zip-compressed",
        ),
        parser=parse_zip_archive,
        category="archive",
    )

    return registry
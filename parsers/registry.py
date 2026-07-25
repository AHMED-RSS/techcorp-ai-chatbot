from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from parsers.models import ParsedFile


ParserFunction = Callable[
    [bytes, str, str],
    ParsedFile,
]


@dataclass(frozen=True, slots=True)
class ParserRegistration:
    extensions: tuple[str, ...]
    mime_types: tuple[str, ...]
    parser: ParserFunction
    category: str


class ParserRegistry:
    """
    Maps file extensions and MIME types to local parsers.
    """

    def __init__(self) -> None:
        self._registrations: list[
            ParserRegistration
        ] = []

    def register(
        self,
        *,
        extensions: tuple[str, ...],
        mime_types: tuple[str, ...],
        parser: ParserFunction,
        category: str,
    ) -> None:
        normalised_extensions = tuple(
            extension.lower().lstrip(".")
            for extension in extensions
        )

        normalised_mime_types = tuple(
            mime_type.lower()
            for mime_type in mime_types
        )

        self._registrations.append(
            ParserRegistration(
                extensions=normalised_extensions,
                mime_types=normalised_mime_types,
                parser=parser,
                category=category,
            )
        )

    def find_parser(
        self,
        filename: str,
        mime_type: str,
    ) -> ParserRegistration | None:
        extension = (
            Path(filename)
            .suffix
            .lower()
            .lstrip(".")
        )

        normalised_mime = (
            mime_type or ""
        ).lower()

        for registration in self._registrations:
            if (
                extension
                and extension
                in registration.extensions
            ):
                return registration

        for registration in self._registrations:
            if (
                normalised_mime
                and normalised_mime
                in registration.mime_types
            ):
                return registration

        for registration in self._registrations:
            for registered_mime in (
                registration.mime_types
            ):
                if (
                    registered_mime.endswith("/*")
                    and normalised_mime.startswith(
                        registered_mime[:-1]
                    )
                ):
                    return registration

        return None

    def parse(
        self,
        *,
        data: bytes,
        filename: str,
        mime_type: str,
        fallback_parser: ParserFunction,
    ) -> ParsedFile:
        registration = self.find_parser(
            filename=filename,
            mime_type=mime_type,
        )

        if registration is None:
            return fallback_parser(
                data,
                filename,
                mime_type,
            )

        return registration.parser(
            data,
            filename,
            mime_type,
        )

    def supported_extensions(
        self,
    ) -> list[str]:
        result: set[str] = set()

        for registration in self._registrations:
            result.update(
                registration.extensions
            )

        return sorted(result)
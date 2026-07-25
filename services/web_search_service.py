from __future__ import annotations

import json
import time
import uuid

from dataclasses import (
    asdict,
    dataclass,
    field,
)
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from threading import RLock
from typing import Any
from urllib.parse import (
    urlparse,
)

from core.exceptions import WebSearchError


@dataclass(slots=True)
class WebSearchResult:
    rank: int
    title: str
    url: str
    snippet: str = ""
    source: str = ""

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(
            self
        )

    @classmethod
    def from_dict(
        cls,
        value: dict[str, Any],
    ) -> "WebSearchResult":
        try:
            rank = max(
                1,
                int(
                    value.get(
                        "rank",
                        1,
                    )
                ),
            )

        except (
            TypeError,
            ValueError,
        ):
            rank = 1

        return cls(
            rank=rank,
            title=str(
                value.get(
                    "title",
                    "Untitled result",
                )
            ).strip()
            or "Untitled result",
            url=str(
                value.get(
                    "url",
                    "",
                )
            ).strip(),
            snippet=str(
                value.get(
                    "snippet",
                    "",
                )
            ).strip(),
            source=str(
                value.get(
                    "source",
                    "",
                )
            ).strip(),
        )


@dataclass(slots=True)
class WebSearchReport:
    id: str
    query: str
    results: list[WebSearchResult] = field(
        default_factory=list
    )
    provider: str = "DDGS"
    created_at: str = field(
        default_factory=lambda: (
            datetime.now(
                timezone.utc
            ).isoformat()
        )
    )
    duration_ms: int = 0
    error: str | None = None

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "results": [
                result.to_dict()
                for result in self.results
            ],
            "provider": self.provider,
            "created_at": self.created_at,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }

    @classmethod
    def from_dict(
        cls,
        value: dict[str, Any],
    ) -> "WebSearchReport":
        raw_results = value.get(
            "results",
            [],
        )

        results = [
            WebSearchResult.from_dict(
                item
            )
            for item in raw_results
            if isinstance(
                item,
                dict,
            )
        ]

        try:
            duration_ms = max(
                0,
                int(
                    value.get(
                        "duration_ms",
                        0,
                    )
                ),
            )

        except (
            TypeError,
            ValueError,
        ):
            duration_ms = 0

        return cls(
            id=str(
                value.get(
                    "id",
                    uuid.uuid4(),
                )
            ),
            query=str(
                value.get(
                    "query",
                    "",
                )
            ).strip(),
            results=results,
            provider=str(
                value.get(
                    "provider",
                    "DDGS",
                )
            ).strip()
            or "DDGS",
            created_at=str(
                value.get(
                    "created_at",
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
                )
            ),
            duration_ms=duration_ms,
            error=(
                str(
                    value.get(
                        "error"
                    )
                )
                if value.get(
                    "error"
                )
                else None
            ),
        )


class WebSearchService:
    """
    Keyless web search using DDGS.

    Search URLs are stored exactly as returned by DDGS. The service
    never asks an AI model to generate, complete or repair URLs.
    """

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.settings = self._resolve_settings(
            args,
            kwargs,
        )

        self.history_folder = (
            self._resolve_history_folder(
                args,
                kwargs,
            )
        )

        self.history_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = RLock()

    @staticmethod
    def _resolve_settings(
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any | None:
        for name in (
            "settings",
            "app_settings",
            "config",
        ):
            value = kwargs.get(
                name
            )

            if value is not None:
                return value

        for value in args:
            if value is None:
                continue

            if any(
                hasattr(
                    value,
                    attribute,
                )
                for attribute in (
                    "data_folder",
                    "web_search_folder",
                    "web_folder",
                )
            ):
                return value

        return None

    def _resolve_history_folder(
        self,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Path:
        for name in (
            "history_folder",
            "web_search_folder",
            "web_folder",
            "storage_folder",
            "folder",
        ):
            value = kwargs.get(
                name
            )

            if value:
                return Path(
                    value
                ).expanduser()

        for value in args:
            if isinstance(
                value,
                Path,
            ):
                return value.expanduser()

        if self.settings is not None:
            for name in (
                "web_search_folder",
                "web_folder",
                "search_folder",
            ):
                value = getattr(
                    self.settings,
                    name,
                    None,
                )

                if value:
                    return Path(
                        value
                    ).expanduser()

            data_folder = getattr(
                self.settings,
                "data_folder",
                None,
            )

            if data_folder:
                return (
                    Path(
                        data_folder
                    ).expanduser()
                    / "web_searches"
                )

        return (
            Path.cwd()
            / "data"
            / "web_searches"
        )

    @staticmethod
    def _normalise_query(
        query: str,
    ) -> str:
        return " ".join(
            str(
                query or ""
            ).split()
        ).strip()

    @staticmethod
    def _normalise_url(
        value: Any,
    ) -> str:
        url = str(
            value or ""
        ).strip()

        if not url.startswith(
            (
                "http://",
                "https://",
            )
        ):
            return ""

        try:
            parsed = urlparse(
                url
            )

        except ValueError:
            return ""

        if (
            parsed.scheme
            not in {
                "http",
                "https",
            }
            or not parsed.netloc
        ):
            return ""

        return url

    @staticmethod
    def _source_from_url(
        url: str,
    ) -> str:
        try:
            host = urlparse(
                url
            ).netloc.casefold()

        except ValueError:
            return ""

        if host.startswith(
            "www."
        ):
            host = host[4:]

        return host

    @classmethod
    def _normalise_raw_result(
        cls,
        raw_result: Any,
        *,
        rank: int,
    ) -> WebSearchResult | None:
        if not isinstance(
            raw_result,
            dict,
        ):
            return None

        url = cls._normalise_url(
            raw_result.get(
                "href"
            )
            or raw_result.get(
                "url"
            )
            or raw_result.get(
                "link"
            )
        )

        if not url:
            return None

        title = str(
            raw_result.get(
                "title"
            )
            or raw_result.get(
                "heading"
            )
            or ""
        ).strip()

        snippet = str(
            raw_result.get(
                "body"
            )
            or raw_result.get(
                "snippet"
            )
            or raw_result.get(
                "description"
            )
            or raw_result.get(
                "text"
            )
            or ""
        ).strip()

        source = str(
            raw_result.get(
                "source"
            )
            or raw_result.get(
                "publisher"
            )
            or ""
        ).strip()

        if not source:
            source = cls._source_from_url(
                url
            )

        if not title:
            title = source or url

        return WebSearchResult(
            rank=max(
                1,
                int(
                    rank
                ),
            ),
            title=title,
            url=url,
            snippet=snippet,
            source=source,
        )

    @staticmethod
    def _load_ddgs_class() -> Any:
        try:
            from ddgs import DDGS

            return DDGS

        except ImportError as exc:
            raise WebSearchError(
                "The ddgs package is not installed. Run "
                "`uv sync` before using Web search."
            ) from exc

    @staticmethod
    def _collect_raw_results(
        ddgs_instance: Any,
        *,
        query: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        text_method = getattr(
            ddgs_instance,
            "text",
            None,
        )

        if not callable(
            text_method
        ):
            raise WebSearchError(
                "The installed DDGS package does not provide "
                "the expected text-search method."
            )

        attempts = (
            {
                "query": query,
                "max_results": max_results,
            },
            {
                "keywords": query,
                "max_results": max_results,
            },
        )

        last_type_error: TypeError | None = None

        for arguments in attempts:
            try:
                raw_results = text_method(
                    **arguments
                )

                if raw_results is None:
                    return []

                return [
                    item
                    for item in raw_results
                    if isinstance(
                        item,
                        dict,
                    )
                ]

            except TypeError as exc:
                last_type_error = exc
                continue

        try:
            raw_results = text_method(
                query,
                max_results=max_results,
            )

            if raw_results is None:
                return []

            return [
                item
                for item in raw_results
                if isinstance(
                    item,
                    dict,
                )
            ]

        except Exception as exc:
            if last_type_error is not None:
                raise WebSearchError(
                    "The installed DDGS version uses an "
                    "unsupported text-search signature."
                ) from last_type_error

            raise WebSearchError(
                f"DDGS search failed: {exc}"
            ) from exc

    def search(
        self,
        query: str,
        *,
        max_results: int = 6,
        **_: Any,
    ) -> WebSearchReport:
        cleaned_query = self._normalise_query(
            query
        )

        if not cleaned_query:
            raise WebSearchError(
                "Enter a search query before running Web search."
            )

        try:
            safe_limit = max(
                1,
                min(
                    20,
                    int(
                        max_results
                    ),
                ),
            )

        except (
            TypeError,
            ValueError,
        ):
            safe_limit = 6

        started = time.perf_counter()

        DDGS = self._load_ddgs_class()

        try:
            ddgs_instance = DDGS()

            raw_results = self._collect_raw_results(
                ddgs_instance,
                query=cleaned_query,
                max_results=safe_limit,
            )

        except WebSearchError:
            raise

        except Exception as exc:
            raise WebSearchError(
                f"Web search failed: {exc}"
            ) from exc

        results: list[
            WebSearchResult
        ] = []

        seen_urls: set[str] = set()

        for raw_result in raw_results:
            result = self._normalise_raw_result(
                raw_result,
                rank=len(
                    results
                )
                + 1,
            )

            if result is None:
                continue

            if result.url in seen_urls:
                continue

            seen_urls.add(
                result.url
            )

            result.rank = len(
                results
            ) + 1

            results.append(
                result
            )

            if len(
                results
            ) >= safe_limit:
                break

        duration_ms = round(
            (
                time.perf_counter()
                - started
            )
            * 1000
        )

        report = WebSearchReport(
            id=str(
                uuid.uuid4()
            ),
            query=cleaned_query,
            results=results,
            provider="DDGS",
            created_at=(
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            duration_ms=duration_ms,
            error=None,
        )

        self.save_report(
            report
        )

        return report

    def build_context(
        self,
        report: WebSearchReport,
        *,
        maximum_characters: int = 20_000,
    ) -> str:
        try:
            character_limit = max(
                1_000,
                int(
                    maximum_characters
                ),
            )

        except (
            TypeError,
            ValueError,
        ):
            character_limit = 20_000

        if not report.results:
            return (
                "No verified web-search results were returned."
            )

        sections = [
            (
                "The following results came directly from DDGS. "
                "Use only these exact titles and URLs. Do not "
                "invent, reconstruct or repair any URL."
            ),
            "",
        ]

        for result in report.results:
            sections.extend(
                [
                    f"[Web {result.rank}]",
                    f"Title: {result.title}",
                    f"URL: {result.url}",
                    (
                        f"Website: {result.source}"
                        if result.source
                        else "Website: Unknown"
                    ),
                    (
                        f"Snippet: {result.snippet}"
                        if result.snippet
                        else "Snippet: Not provided"
                    ),
                    "",
                ]
            )

        context = "\n".join(
            sections
        ).strip()

        if len(
            context
        ) <= character_limit:
            return context

        return (
            context[
                :character_limit
            ].rstrip()
            + "\n\n[Web context truncated]"
        )

    def save_report(
        self,
        report: WebSearchReport,
    ) -> Path:
        path = (
            self.history_folder
            / f"{report.id}.json"
        )

        temporary_path = path.with_suffix(
            ".json.tmp"
        )

        payload = report.to_dict()

        with self._lock:
            temporary_path.write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            temporary_path.replace(
                path
            )

        return path

    def load_report(
        self,
        report_id: str,
    ) -> WebSearchReport | None:
        cleaned_id = str(
            report_id or ""
        ).strip()

        if not cleaned_id:
            return None

        path = (
            self.history_folder
            / f"{cleaned_id}.json"
        )

        if not path.exists():
            return None

        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise WebSearchError(
                f"Could not load web-search report: {exc}"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise WebSearchError(
                "The saved web-search report is invalid."
            )

        return WebSearchReport.from_dict(
            payload
        )

    def list_recent_searches(
        self,
        *,
        limit: int = 30,
    ) -> list[WebSearchReport]:
        try:
            safe_limit = max(
                1,
                int(
                    limit
                ),
            )

        except (
            TypeError,
            ValueError,
        ):
            safe_limit = 30

        files = sorted(
            self.history_folder.glob(
                "*.json"
            ),
            key=lambda path: (
                path.stat().st_mtime
            ),
            reverse=True,
        )

        reports: list[
            WebSearchReport
        ] = []

        for path in files:
            if len(
                reports
            ) >= safe_limit:
                break

            try:
                payload = json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                )

                if not isinstance(
                    payload,
                    dict,
                ):
                    continue

                reports.append(
                    WebSearchReport.from_dict(
                        payload
                    )
                )

            except Exception:
                continue

        return reports

    def list_reports(
        self,
        *,
        limit: int = 30,
    ) -> list[WebSearchReport]:
        return self.list_recent_searches(
            limit=limit
        )

    def delete_report(
        self,
        report_id: str,
    ) -> bool:
        cleaned_id = str(
            report_id or ""
        ).strip()

        if not cleaned_id:
            return False

        path = (
            self.history_folder
            / f"{cleaned_id}.json"
        )

        if not path.exists():
            return False

        try:
            path.unlink()

        except OSError as exc:
            raise WebSearchError(
                f"Could not delete web-search report: {exc}"
            ) from exc

        return True

    def clear_reports(
        self,
    ) -> int:
        deleted = 0

        with self._lock:
            for path in self.history_folder.glob(
                "*.json"
            ):
                try:
                    path.unlink()
                    deleted += 1

                except OSError:
                    continue

        return deleted
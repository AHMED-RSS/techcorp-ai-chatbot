from __future__ import annotations

import json
import os
import re
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.memory import (
    MemoryItem,
    TaskState,
    memory_item_from_dict,
    task_state_from_dict,
)
from config.settings import Settings
from core.exceptions import (
    MemoryServiceError,
)
from core.logging_config import (
    get_logger,
)


logger = get_logger(__name__)


class MemoryService:
    """
    Persistent local memory and task-state service.

    All information is stored as JSON under the existing
    local memory directory.
    """

    def __init__(
        self,
        settings: Settings,
    ) -> None:
        self.settings = settings

        self.memory_root = (
            settings.document_folder.parent
        )

        self.memory_item_folder = (
            self.memory_root
            / "memories"
        )

        self.task_state_folder = (
            self.memory_root
            / "task_state"
        )

        self.memory_item_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.task_state_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ========================================================
    # MEMORY ITEMS
    # ========================================================

    def create_memory(
        self,
        *,
        content: str,
        kind: str = "note",
        keywords: list[str] | str | None = None,
        source: str = "explicit",
        chat_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryItem:
        cleaned_content = str(
            content or ""
        ).strip()

        if len(cleaned_content) < 2:
            raise MemoryServiceError(
                "Memory content is too short."
            )

        cleaned_keywords = (
            self._clean_keywords(
                keywords
            )
        )

        if not cleaned_keywords:
            cleaned_keywords = (
                self._extract_keywords(
                    cleaned_content
                )
            )

        duplicate = self.find_duplicate(
            cleaned_content,
            chat_id=chat_id,
        )

        if duplicate is not None:
            duplicate.updated_at = (
                self._utc_now()
            )

            duplicate.enabled = True

            if cleaned_keywords:
                duplicate.keywords = list(
                    dict.fromkeys(
                        [
                            *duplicate.keywords,
                            *cleaned_keywords,
                        ]
                    )
                )[:40]

            self.save_memory(
                duplicate
            )

            return duplicate

        timestamp = self._utc_now()

        item = MemoryItem(
            id=str(
                uuid.uuid4()
            ),
            content=cleaned_content,
            kind=kind,
            keywords=cleaned_keywords,
            source=source,
            chat_id=chat_id,
            enabled=True,
            created_at=timestamp,
            updated_at=timestamp,
            access_count=0,
            last_accessed_at=None,
            metadata=metadata or {},
        )

        self.save_memory(
            item
        )

        return item

    def save_memory(
        self,
        item: MemoryItem,
    ) -> MemoryItem:
        item.updated_at = (
            self._utc_now()
        )

        path = self.memory_path(
            item.id
        )

        self._atomic_write_json(
            path,
            item.to_dict(),
        )

        return item

    def load_memory(
        self,
        memory_id: str,
    ) -> MemoryItem | None:
        path = self.memory_path(
            memory_id
        )

        if not path.exists():
            return None

        raw = self._read_json(
            path
        )

        return memory_item_from_dict(
            raw
        )

    def list_memories(
        self,
        *,
        include_disabled: bool = True,
        chat_id: str | None = None,
        limit: int = 500,
    ) -> list[MemoryItem]:
        memories: list[MemoryItem] = []

        for path in (
            self.memory_item_folder
            .glob(
                "*.json"
            )
        ):
            try:
                item = memory_item_from_dict(
                    self._read_json(
                        path
                    )
                )

            except Exception:
                logger.warning(
                    "Skipping invalid memory file: %s",
                    path.name,
                )

                continue

            if (
                not include_disabled
                and not item.enabled
            ):
                continue

            if (
                chat_id is not None
                and item.chat_id
                not in {
                    None,
                    chat_id,
                }
            ):
                continue

            memories.append(
                item
            )

        memories.sort(
            key=lambda item: (
                item.updated_at,
                item.created_at,
            ),
            reverse=True,
        )

        return memories[
            : max(
                1,
                limit,
            )
        ]

    def search_memories(
        self,
        query: str,
        *,
        chat_id: str | None = None,
        limit: int = 8,
    ) -> list[MemoryItem]:
        cleaned_query = str(
            query or ""
        ).strip().lower()

        if not cleaned_query:
            return []

        query_tokens = set(
            self._tokenise(
                cleaned_query
            )
        )

        scored: list[
            tuple[float, MemoryItem]
        ] = []

        for item in self.list_memories(
            include_disabled=False,
            chat_id=chat_id,
        ):
            content_lower = (
                item.content.lower()
            )

            keyword_tokens = set(
                token
                for keyword in item.keywords
                for token in self._tokenise(
                    keyword
                )
            )

            content_tokens = set(
                self._tokenise(
                    content_lower
                )
            )

            overlap = len(
                query_tokens
                & (
                    content_tokens
                    | keyword_tokens
                )
            )

            phrase_score = 0.0

            for keyword in item.keywords:
                if (
                    keyword
                    and keyword
                    in cleaned_query
                ):
                    phrase_score += 2.5

            if cleaned_query in content_lower:
                phrase_score += 4.0

            scope_score = (
                1.0
                if (
                    chat_id
                    and item.chat_id
                    == chat_id
                )
                else 0.0
            )

            recency_score = min(
                item.access_count,
                10,
            ) * 0.03

            score = (
                overlap
                + phrase_score
                + scope_score
                + recency_score
            )

            if score > 0:
                scored.append(
                    (
                        score,
                        item,
                    )
                )

        scored.sort(
            key=lambda pair: (
                pair[0],
                pair[1].updated_at,
            ),
            reverse=True,
        )

        selected = [
            item
            for _score, item in scored[
                : max(
                    1,
                    limit,
                )
            ]
        ]

        accessed_at = self._utc_now()

        for item in selected:
            item.access_count += 1
            item.last_accessed_at = (
                accessed_at
            )

            try:
                self.save_memory(
                    item
                )

            except MemoryServiceError:
                logger.warning(
                    "Could not update memory access count: %s",
                    item.id,
                )

        return selected

    def build_memory_context(
        self,
        memories: list[MemoryItem],
        *,
        maximum_characters: int = 6_000,
    ) -> str:
        sections: list[str] = []
        character_count = 0

        for index, item in enumerate(
            memories,
            start=1,
        ):
            section = (
                f"[Memory {index}]\n"
                f"Type: {item.kind}\n"
                f"Scope: "
                + (
                    "current chat"
                    if item.chat_id
                    else "global"
                )
                + "\n"
                f"Content: {item.content}"
            )

            remaining = (
                maximum_characters
                - character_count
            )

            if remaining <= 0:
                break

            section = section[:remaining]

            sections.append(
                section
            )

            character_count += len(
                section
            )

        return "\n\n---\n\n".join(
            sections
        )

    def update_memory(
        self,
        memory_id: str,
        *,
        content: str,
        kind: str,
        keywords: list[str] | str,
        enabled: bool,
    ) -> MemoryItem:
        item = self.load_memory(
            memory_id
        )

        if item is None:
            raise MemoryServiceError(
                "Memory was not found."
            )

        cleaned_content = str(
            content or ""
        ).strip()

        if len(cleaned_content) < 2:
            raise MemoryServiceError(
                "Memory content is too short."
            )

        item.content = cleaned_content
        item.kind = kind
        item.keywords = (
            self._clean_keywords(
                keywords
            )
        )
        item.enabled = bool(
            enabled
        )

        return self.save_memory(
            item
        )

    def delete_memory(
        self,
        memory_id: str,
    ) -> bool:
        path = self.memory_path(
            memory_id
        )

        if not path.exists():
            return False

        try:
            path.unlink()

        except OSError as exc:
            raise MemoryServiceError(
                f"Could not delete memory: {exc}"
            ) from exc

        return True

    def clear_memories(
        self,
        *,
        chat_id: str | None = None,
    ) -> int:
        deleted = 0

        for item in self.list_memories(
            include_disabled=True,
            chat_id=chat_id,
            limit=100_000,
        ):
            if (
                chat_id is not None
                and item.chat_id != chat_id
            ):
                continue

            if self.delete_memory(
                item.id
            ):
                deleted += 1

        return deleted

    def find_duplicate(
        self,
        content: str,
        *,
        chat_id: str | None,
    ) -> MemoryItem | None:
        normalised = self._normalise_text(
            content
        )

        for item in self.list_memories(
            include_disabled=True,
            chat_id=chat_id,
        ):
            if (
                item.chat_id == chat_id
                and self._normalise_text(
                    item.content
                )
                == normalised
            ):
                return item

        return None

    # ========================================================
    # TASK STATE
    # ========================================================

    def create_task_state(
        self,
        *,
        chat_id: str | None,
        user_request: str,
        goal: str,
        status: str,
        route: dict[str, Any] | None = None,
        plan: dict[str, Any] | None = None,
        execution: dict[str, Any] | None = None,
        critic: dict[str, Any] | None = None,
        final_output: str = "",
        metadata: dict[str, Any] | None = None,
        task_id: str | None = None,
    ) -> TaskState:
        timestamp = self._utc_now()

        state = TaskState(
            id=(
                task_id
                or str(
                    uuid.uuid4()
                )
            ),
            chat_id=chat_id,
            user_request=user_request,
            goal=goal,
            status=status,
            route=route,
            plan=plan,
            execution=execution,
            critic=critic,
            final_output=final_output,
            created_at=timestamp,
            updated_at=timestamp,
            metadata=metadata or {},
        )

        self.save_task_state(
            state
        )

        return state

    def save_task_state(
        self,
        state: TaskState,
    ) -> TaskState:
        existing = self.load_task_state(
            state.id
        )

        if (
            existing is not None
            and not state.created_at
        ):
            state.created_at = (
                existing.created_at
            )

        if not state.created_at:
            state.created_at = (
                self._utc_now()
            )

        state.updated_at = (
            self._utc_now()
        )

        self._atomic_write_json(
            self.task_state_path(
                state.id
            ),
            state.to_dict(),
        )

        return state

    def load_task_state(
        self,
        task_id: str,
    ) -> TaskState | None:
        path = self.task_state_path(
            task_id
        )

        if not path.exists():
            return None

        return task_state_from_dict(
            self._read_json(
                path
            )
        )

    def list_task_states(
        self,
        *,
        chat_id: str | None = None,
        limit: int = 100,
    ) -> list[TaskState]:
        states: list[TaskState] = []

        for path in (
            self.task_state_folder
            .glob(
                "*.json"
            )
        ):
            try:
                state = task_state_from_dict(
                    self._read_json(
                        path
                    )
                )

            except Exception:
                logger.warning(
                    "Skipping invalid task-state file: %s",
                    path.name,
                )

                continue

            if (
                chat_id is not None
                and state.chat_id
                != chat_id
            ):
                continue

            states.append(
                state
            )

        states.sort(
            key=lambda state: (
                state.updated_at
            ),
            reverse=True,
        )

        return states[
            : max(
                1,
                limit,
            )
        ]

    def delete_task_state(
        self,
        task_id: str,
    ) -> bool:
        path = self.task_state_path(
            task_id
        )

        if not path.exists():
            return False

        try:
            path.unlink()

        except OSError as exc:
            raise MemoryServiceError(
                f"Could not delete task state: {exc}"
            ) from exc

        return True

    def clear_task_states(
        self,
        *,
        chat_id: str | None = None,
    ) -> int:
        """
        Permanently delete task snapshots.

        When chat_id is supplied, only snapshots belonging
        to that conversation are deleted.
        """

        deleted = 0

        states = self.list_task_states(
            chat_id=chat_id,
            limit=100_000,
        )

        for state in states:
            if (
                chat_id is not None
                and state.chat_id != chat_id
            ):
                continue

            if self.delete_task_state(
                state.id
            ):
                deleted += 1

        return deleted

    # ========================================================
    # PATHS AND STORAGE
    # ========================================================

    def memory_path(
        self,
        memory_id: str,
    ) -> Path:
        safe_id = self._safe_id(
            memory_id
        )

        return (
            self.memory_item_folder
            / f"{safe_id}.json"
        )

    def task_state_path(
        self,
        task_id: str,
    ) -> Path:
        safe_id = self._safe_id(
            task_id
        )

        return (
            self.task_state_folder
            / f"{safe_id}.json"
        )

    @staticmethod
    def _read_json(
        path: Path,
    ) -> dict[str, Any]:
        try:
            raw = json.loads(
                path.read_text(
                    encoding="utf-8",
                )
            )

        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise MemoryServiceError(
                f"Could not read local state: {exc}"
            ) from exc

        if not isinstance(
            raw,
            dict,
        ):
            raise MemoryServiceError(
                "Stored local state is invalid."
            )

        return raw

    @staticmethod
    def _atomic_write_json(
        path: Path,
        data: dict[str, Any],
    ) -> None:
        temporary_path = path.with_suffix(
            ".json.tmp"
        )

        try:
            temporary_path.write_text(
                json.dumps(
                    data,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            os.replace(
                temporary_path,
                path,
            )

        except OSError as exc:
            raise MemoryServiceError(
                f"Could not save local state: {exc}"
            ) from exc

    @staticmethod
    def _safe_id(
        value: str,
    ) -> str:
        cleaned = re.sub(
            r"[^a-zA-Z0-9_-]",
            "",
            str(
                value or ""
            ),
        )

        if not cleaned:
            raise MemoryServiceError(
                "Invalid local-state identifier."
            )

        return cleaned

    @staticmethod
    def _normalise_text(
        text: str,
    ) -> str:
        return re.sub(
            r"\s+",
            " ",
            str(
                text or ""
            ).strip().lower(),
        )

    @staticmethod
    def _clean_keywords(
        keywords: list[str] | str | None,
    ) -> list[str]:
        if keywords is None:
            return []

        if isinstance(
            keywords,
            str,
        ):
            values = re.split(
                r"[,;\n]+",
                keywords,
            )

        else:
            values = list(
                keywords
            )

        result: list[str] = []

        for value in values:
            keyword = re.sub(
                r"\s+",
                " ",
                str(
                    value or ""
                ).strip().lower(),
            )

            if (
                keyword
                and keyword not in result
            ):
                result.append(
                    keyword[:60]
                )

        return result[:40]

    @classmethod
    def _extract_keywords(
        cls,
        content: str,
    ) -> list[str]:
        stop_words = {
            "about",
            "after",
            "again",
            "also",
            "because",
            "before",
            "being",
            "could",
            "from",
            "have",
            "into",
            "just",
            "more",
            "only",
            "should",
            "that",
            "their",
            "there",
            "these",
            "they",
            "this",
            "through",
            "user",
            "very",
            "want",
            "with",
            "would",
            "your",
        }

        result: list[str] = []

        for token in cls._tokenise(
            content
        ):
            if (
                len(token) >= 4
                and token not in stop_words
                and token not in result
            ):
                result.append(
                    token
                )

        return result[:20]

    @staticmethod
    def _tokenise(
        text: str,
    ) -> list[str]:
        return re.findall(
            r"[a-z0-9_+-]+",
            str(
                text or ""
            ).lower(),
        )

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat(
            timespec="seconds"
        )
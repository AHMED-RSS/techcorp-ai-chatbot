from __future__ import annotations

import json
import os
import re
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import Settings
from core.exceptions import ToolExecutionError
from core.logging_config import get_logger
from tools.tool_models import (
    ToolDefinition,
    ToolResult,
)


logger = get_logger(__name__)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat(
        timespec="seconds"
    )


class ToolService:
    """
    Registry and execution service for local tools.
    """

    def __init__(
        self,
        settings: Settings,
    ) -> None:
        self.settings = settings

        self._tools: dict[
            str,
            ToolDefinition,
        ] = {}

        self.run_folder = (
            settings.agent_run_folder
        )

        self.run_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

    def register(
        self,
        definition: ToolDefinition,
    ) -> None:
        tool_name = str(
            definition.name
        ).strip().lower()

        if not tool_name:
            raise ToolExecutionError(
                "Tool name cannot be empty."
            )

        if not re.fullmatch(
            r"[a-z][a-z0-9_]*",
            tool_name,
        ):
            raise ToolExecutionError(
                "Tool names may only contain lowercase "
                "letters, numbers and underscores."
            )

        if tool_name in self._tools:
            raise ToolExecutionError(
                f"Tool '{tool_name}' is already registered."
            )

        definition.name = tool_name

        self._tools[tool_name] = definition

    def has_tool(
        self,
        tool_name: str,
    ) -> bool:
        return (
            str(tool_name).strip().lower()
            in self._tools
        )

    def get_tool(
        self,
        tool_name: str,
    ) -> ToolDefinition | None:
        return self._tools.get(
            str(tool_name).strip().lower()
        )

    def list_tools(
        self,
    ) -> list[ToolDefinition]:
        return sorted(
            self._tools.values(),
            key=lambda tool: (
                tool.category,
                tool.name,
            ),
        )

    def public_schemas(
        self,
    ) -> list[dict[str, Any]]:
        return [
            tool.public_schema()
            for tool in self.list_tools()
        ]

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> ToolResult:
        normalised_name = str(
            tool_name or ""
        ).strip().lower()

        definition = self.get_tool(
            normalised_name
        )

        if definition is None:
            available = ", ".join(
                tool.name
                for tool in self.list_tools()
            )

            raise ToolExecutionError(
                f"Unknown tool '{normalised_name}'. "
                f"Available tools: {available}"
            )

        safe_arguments = (
            arguments
            if isinstance(arguments, dict)
            else {}
        )

        run_id = str(uuid.uuid4())
        started_at = utc_now()

        try:
            result = definition.handler(
                safe_arguments
            )

            if not isinstance(
                result,
                ToolResult,
            ):
                raise ToolExecutionError(
                    f"Tool '{normalised_name}' returned "
                    "an invalid result."
                )

        except ToolExecutionError as exc:
            result = ToolResult(
                success=False,
                tool_name=normalised_name,
                content=str(exc),
                error=str(exc),
            )

        except Exception as exc:
            logger.exception(
                "Unexpected tool failure: %s",
                normalised_name,
            )

            result = ToolResult(
                success=False,
                tool_name=normalised_name,
                content=(
                    f"Tool '{normalised_name}' failed: {exc}"
                ),
                error=str(exc),
            )

        completed_at = utc_now()

        self._save_run(
            {
                "schema_version": 1,
                "id": run_id,
                "tool_name": normalised_name,
                "arguments": safe_arguments,
                "started_at": started_at,
                "completed_at": completed_at,
                "result": result.to_dict(),
            }
        )

        return result

    def list_recent_runs(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        runs: list[dict[str, Any]] = []

        for path in self.run_folder.glob(
            "*.json"
        ):
            try:
                record = json.loads(
                    path.read_text(
                        encoding="utf-8",
                    )
                )

                if isinstance(record, dict):
                    runs.append(record)

            except Exception:
                logger.warning(
                    "Skipping invalid tool run: %s",
                    path.name,
                )

        runs.sort(
            key=lambda item: str(
                item.get(
                    "completed_at",
                    "",
                )
            ),
            reverse=True,
        )

        return runs[:max(1, limit)]

    def clear_run_history(
        self,
    ) -> int:
        deleted = 0

        for path in self.run_folder.glob(
            "*.json"
        ):
            try:
                path.unlink()
                deleted += 1

            except OSError:
                logger.warning(
                    "Could not delete tool run: %s",
                    path.name,
                )

        return deleted

    def _save_run(
        self,
        record: dict[str, Any],
    ) -> None:
        run_id = str(
            record.get("id", "")
        ).strip()

        if not run_id:
            return

        path = (
            self.run_folder
            / f"{run_id}.json"
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
            logger.warning(
                "Could not save tool run: %s",
                exc,
            )
from __future__ import annotations

import importlib
import json
import os
import platform
import sys
import uuid

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from config.settings import Settings
from core.logging_config import get_logger
from core.providers import (
    AIProvider,
)


logger = get_logger(__name__)


VALID_CHECK_STATUSES = {
    "passed",
    "warning",
    "failed",
    "skipped",
}


@dataclass(slots=True)
class ReadinessCheck:
    """
    Result of one release-readiness check.
    """

    key: str
    title: str
    status: str
    message: str
    details: dict[str, Any] = field(
        default_factory=dict
    )
    required: bool = True
    duration_ms: float = 0.0

    def __post_init__(self) -> None:
        self.key = str(
            self.key or "unknown"
        ).strip()

        self.title = str(
            self.title or self.key
        ).strip()

        cleaned_status = str(
            self.status or "failed"
        ).strip().lower()

        if cleaned_status not in VALID_CHECK_STATUSES:
            cleaned_status = "failed"

        self.status = cleaned_status

        self.message = str(
            self.message or ""
        ).strip()

        if not isinstance(
            self.details,
            dict,
        ):
            self.details = {}

        self.required = bool(
            self.required
        )

        try:
            self.duration_ms = max(
                0.0,
                float(
                    self.duration_ms
                ),
            )

        except (
            TypeError,
            ValueError,
        ):
            self.duration_ms = 0.0

    @property
    def successful(self) -> bool:
        return self.status in {
            "passed",
            "warning",
            "skipped",
        }

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "required": self.required,
            "duration_ms": self.duration_ms,
        }


@dataclass(slots=True)
class ReadinessReport:
    """
    Complete local release-readiness report.
    """

    id: str
    created_at: str
    project_root: str
    python_version: str
    platform: str
    checks: list[ReadinessCheck] = field(
        default_factory=list
    )

    @property
    def passed_count(self) -> int:
        return sum(
            1
            for check in self.checks
            if check.status == "passed"
        )

    @property
    def warning_count(self) -> int:
        return sum(
            1
            for check in self.checks
            if check.status == "warning"
        )

    @property
    def failed_count(self) -> int:
        return sum(
            1
            for check in self.checks
            if check.status == "failed"
        )

    @property
    def required_failure_count(self) -> int:
        return sum(
            1
            for check in self.checks
            if (
                check.required
                and check.status == "failed"
            )
        )

    @property
    def ready(self) -> bool:
        return self.required_failure_count == 0

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "project_root": self.project_root,
            "python_version": self.python_version,
            "platform": self.platform,
            "ready": self.ready,
            "passed_count": self.passed_count,
            "warning_count": self.warning_count,
            "failed_count": self.failed_count,
            "required_failure_count": (
                self.required_failure_count
            ),
            "checks": [
                check.to_dict()
                for check in self.checks
            ],
        }


class ReadinessService:
    """
    Performs local release and runtime diagnostics.

    Checks do not send application data to a cloud AI service.
    """

    REQUIRED_MODULES: tuple[str, ...] = (
        "streamlit",
        "ollama",
        "dotenv",
        "pydantic",
        "pydantic_settings",
        "tenacity",
        "orjson",
        "pypdf",
        "docx",
        "openpyxl",
        "pptx",
        "pandas",
        "PIL",
        "chromadb",
        "ddgs",
    )

    APPLICATION_MODULES: tuple[str, ...] = (
        "core.bootstrap",
        "core.ollama_client",
        "core.session",
        "agents.router",
        "agents.planner",
        "agents.executor",
        "agents.critic",
        "agents.memory",
        "agents.study",
        "agents.composer",
        "services.chat_service",
        "services.file_service",
        "services.rag_service",
        "services.skill_service",
        "services.tool_service",
        "services.router_service",
        "services.planner_service",
        "services.executor_service",
        "services.critic_service",
        "services.memory_service",
        "services.study_service",
        "services.web_search_service",
        "ui.composer",
        "ui.study_panel",
        "ui.memory_panel",
        "ui.critic_panel",
        "ui.execution_panel",
        "ui.plan_panel",
    )

    def __init__(
        self,
        *,
        settings: Settings,
        ai_provider: AIProvider,
        rag_service: Any | None = None,
    ) -> None:
        self.settings = settings
        self.ai = ai_provider
        self.rag = rag_service

        self.project_root = Path(
            getattr(
                settings,
                "project_root",
                Path.cwd(),
            )
        ).resolve()

        self.report_folder = (
            settings.report_folder
            / "readiness"
        )

        self.report_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

    def run_all(
        self,
        *,
        include_ollama: bool = True,
    ) -> ReadinessReport:
        checks: list[ReadinessCheck] = []

        check_functions: list[
            Callable[[], ReadinessCheck]
        ] = [
            self.check_python,
            self.check_project_files,
            self.check_dependencies,
            self.check_application_imports,
            self.check_directories,
            self.check_write_access,
            self.check_configuration,
        ]

        if include_ollama:
            check_functions.extend(
                [
                    self.check_ollama_connection,
                    self.check_ollama_models,
                    self.check_vector_store,
                ]
            )

        else:
            checks.append(
                ReadinessCheck(
                    key="ollama",
                    title="Ollama runtime",
                    status="skipped",
                    message=(
                        "Ollama checks were disabled "
                        "for this diagnostic run."
                    ),
                    required=False,
                )
            )

        for check_function in check_functions:
            try:
                checks.append(
                    check_function()
                )

            except Exception as exc:
                logger.exception(
                    "Readiness check failed unexpectedly: %s",
                    check_function.__name__,
                )

                checks.append(
                    ReadinessCheck(
                        key=check_function.__name__,
                        title=(
                            check_function.__name__
                            .removeprefix("check_")
                            .replace("_", " ")
                            .title()
                        ),
                        status="failed",
                        message=(
                            f"Unexpected check error: {exc}"
                        ),
                    )
                )

        report = ReadinessReport(
            id=str(
                uuid.uuid4()
            ),
            created_at=self._utc_now(),
            project_root=str(
                self.project_root
            ),
            python_version=(
                platform.python_version()
            ),
            platform=platform.platform(),
            checks=checks,
        )

        self.save_report(
            report
        )

        return report

    def check_python(
        self,
    ) -> ReadinessCheck:
        supported = (
            sys.version_info
            >= (
                3,
                11,
            )
        )

        return ReadinessCheck(
            key="python",
            title="Python runtime",
            status=(
                "passed"
                if supported
                else "failed"
            ),
            message=(
                f"Python {platform.python_version()} "
                + (
                    "meets the Python 3.11+ requirement."
                    if supported
                    else (
                        "does not meet the Python "
                        "3.11+ requirement."
                    )
                )
            ),
            details={
                "executable": sys.executable,
                "implementation": (
                    platform.python_implementation()
                ),
            },
        )

    def check_project_files(
        self,
    ) -> ReadinessCheck:
        required_files = [
            self.project_root
            / "main.py",
            self.project_root
            / "pyproject.toml",
            self.project_root
            / "config"
            / "settings.py",
            self.project_root
            / "core"
            / "bootstrap.py",
        ]

        missing = [
            str(
                path.relative_to(
                    self.project_root
                )
            )
            for path in required_files
            if not path.exists()
        ]

        return ReadinessCheck(
            key="project_files",
            title="Project files",
            status=(
                "passed"
                if not missing
                else "failed"
            ),
            message=(
                "Required project files are present."
                if not missing
                else (
                    "Required project files are missing: "
                    + ", ".join(
                        missing
                    )
                )
            ),
            details={
                "missing": missing,
            },
        )

    def check_dependencies(
        self,
    ) -> ReadinessCheck:
        missing: list[str] = []

        versions: dict[str, str] = {}

        for module_name in self.REQUIRED_MODULES:
            try:
                module = importlib.import_module(
                    module_name
                )

            except Exception:
                missing.append(
                    module_name
                )
                continue

            version = getattr(
                module,
                "__version__",
                None,
            )

            if version is not None:
                versions[module_name] = str(
                    version
                )

        return ReadinessCheck(
            key="dependencies",
            title="Python dependencies",
            status=(
                "passed"
                if not missing
                else "failed"
            ),
            message=(
                "All required Python packages can be imported."
                if not missing
                else (
                    "Missing or broken packages: "
                    + ", ".join(
                        missing
                    )
                )
            ),
            details={
                "missing": missing,
                "versions": versions,
            },
        )

    def check_application_imports(
        self,
    ) -> ReadinessCheck:
        failures: dict[str, str] = {}

        for module_name in self.APPLICATION_MODULES:
            try:
                importlib.import_module(
                    module_name
                )

            except Exception as exc:
                failures[module_name] = str(
                    exc
                )

        return ReadinessCheck(
            key="application_imports",
            title="Application imports",
            status=(
                "passed"
                if not failures
                else "failed"
            ),
            message=(
                "All application modules import successfully."
                if not failures
                else (
                    f"{len(failures)} application "
                    "module(s) failed to import."
                )
            ),
            details={
                "failures": failures,
            },
        )

    def check_directories(
        self,
    ) -> ReadinessCheck:
        directory_attributes = (
            "chat_folder",
            "upload_folder",
            "document_folder",
            "task_folder",
            "agent_run_folder",
            "log_folder",
            "report_folder",
            "skill_folder",
            "chroma_folder",
        )

        paths: dict[str, str] = {}

        missing: list[str] = []

        for attribute in directory_attributes:
            value = getattr(
                self.settings,
                attribute,
                None,
            )

            if value is None:
                continue

            path = Path(
                value
            )

            paths[attribute] = str(
                path
            )

            if not path.exists():
                missing.append(
                    attribute
                )

        return ReadinessCheck(
            key="directories",
            title="Runtime directories",
            status=(
                "passed"
                if not missing
                else "failed"
            ),
            message=(
                "All configured runtime directories exist."
                if not missing
                else (
                    "Missing runtime directories: "
                    + ", ".join(
                        missing
                    )
                )
            ),
            details={
                "paths": paths,
                "missing": missing,
            },
        )

    def check_write_access(
        self,
    ) -> ReadinessCheck:
        writable_paths: dict[str, bool] = {}

        failures: list[str] = []

        candidates = {
            "chats": self.settings.chat_folder,
            "uploads": self.settings.upload_folder,
            "documents": self.settings.document_folder,
            "tasks": self.settings.task_folder,
            "agent_runs": self.settings.agent_run_folder,
            "logs": self.settings.log_folder,
            "reports": self.settings.report_folder,
        }

        for name, raw_path in candidates.items():
            path = Path(
                raw_path
            )

            path.mkdir(
                parents=True,
                exist_ok=True,
            )

            test_path = (
                path
                / f".write_test_{uuid.uuid4().hex}"
            )

            try:
                test_path.write_text(
                    "ok",
                    encoding="utf-8",
                )

                test_path.unlink()

                writable_paths[name] = True

            except OSError:
                writable_paths[name] = False
                failures.append(
                    name
                )

        return ReadinessCheck(
            key="write_access",
            title="Local write access",
            status=(
                "passed"
                if not failures
                else "failed"
            ),
            message=(
                "Application storage folders are writable."
                if not failures
                else (
                    "Write access failed for: "
                    + ", ".join(
                        failures
                    )
                )
            ),
            details={
                "writable": writable_paths,
            },
        )

    def check_configuration(
        self,
    ) -> ReadinessCheck:
        chat_model = str(
            getattr(
                self.settings,
                "ollama_chat_model",
                "",
            )
        ).strip()

        embed_model = str(
            getattr(
                self.settings,
                "ollama_embed_model",
                "",
            )
        ).strip()

        problems: list[str] = []

        if not chat_model:
            problems.append(
                "OLLAMA_CHAT_MODEL is empty"
            )

        if not embed_model:
            problems.append(
                "OLLAMA_EMBED_MODEL is empty"
            )

        maximum_steps = int(
            getattr(
                self.settings,
                "agent_max_steps",
                0,
            )
            or 0
        )

        if maximum_steps < 1:
            problems.append(
                "AGENT_MAX_STEPS must be at least 1"
            )

        return ReadinessCheck(
            key="configuration",
            title="Application configuration",
            status=(
                "passed"
                if not problems
                else "failed"
            ),
            message=(
                "Required application settings are valid."
                if not problems
                else "; ".join(
                    problems
                )
            ),
            details={
                "chat_model": chat_model,
                "embedding_model": embed_model,
                "agent_max_steps": maximum_steps,
            },
        )

    def check_ollama_connection(
        self,
    ) -> ReadinessCheck:
        try:
            connected = (
                self.ai.health_check()
            )

        except Exception as exc:
            return ReadinessCheck(
                key="ollama_connection",
                title="Ollama connection",
                status="failed",
                message=(
                    f"Ollama connection failed: {exc}"
                ),
            )

        return ReadinessCheck(
            key="ollama_connection",
            title="Ollama connection",
            status=(
                "passed"
                if connected
                else "failed"
            ),
            message=(
                "The local Ollama service is available."
                if connected
                else (
                    "The local Ollama service "
                    "did not respond."
                )
            ),
            details={
                "host": str(
                    getattr(
                        self.settings,
                        "ollama_host",
                        "",
                    )
                ),
            },
        )

    def check_ollama_models(
        self,
    ) -> ReadinessCheck:
        chat_model = str(
            self.settings.ollama_chat_model
        )

        embed_model = str(
            self.settings.ollama_embed_model
        )

        try:
            models = (
                self.ai.list_models()
            )

        except Exception as exc:
            return ReadinessCheck(
                key="ollama_models",
                title="Ollama models",
                status="failed",
                message=(
                    f"Could not list Ollama models: {exc}"
                ),
            )

        missing = [
            model_name
            for model_name in (
                chat_model,
                embed_model,
            )
            if model_name not in models
        ]

        return ReadinessCheck(
            key="ollama_models",
            title="Ollama models",
            status=(
                "passed"
                if not missing
                else "failed"
            ),
            message=(
                "Configured chat and embedding "
                "models are installed."
                if not missing
                else (
                    "Missing configured model(s): "
                    + ", ".join(
                        missing
                    )
                )
            ),
            details={
                "installed_models": models,
                "required_models": [
                    chat_model,
                    embed_model,
                ],
                "missing_models": missing,
            },
        )

    def check_vector_store(
        self,
    ) -> ReadinessCheck:
        if self.rag is None:
            return ReadinessCheck(
                key="vector_store",
                title="Vector store",
                status="skipped",
                message=(
                    "RAG service was not supplied "
                    "to the readiness service."
                ),
                required=False,
            )

        try:
            collection = getattr(
                self.rag,
                "collection",
                None,
            )

            if collection is None:
                return ReadinessCheck(
                    key="vector_store",
                    title="Vector store",
                    status="failed",
                    message=(
                        "The RAG service does not expose "
                        "an active Chroma collection."
                    ),
                )

            count = int(
                collection.count()
            )

        except Exception as exc:
            return ReadinessCheck(
                key="vector_store",
                title="Vector store",
                status="failed",
                message=(
                    f"ChromaDB check failed: {exc}"
                ),
            )

        return ReadinessCheck(
            key="vector_store",
            title="Vector store",
            status="passed",
            message=(
                "The persistent ChromaDB collection "
                "is available."
            ),
            details={
                "record_count": count,
                "collection_name": str(
                    getattr(
                        collection,
                        "name",
                        "unknown",
                    )
                ),
            },
        )

    def save_report(
        self,
        report: ReadinessReport,
    ) -> ReadinessReport:
        path = (
            self.report_folder
            / f"{report.id}.json"
        )

        temporary_path = path.with_suffix(
            ".json.tmp"
        )

        try:
            temporary_path.write_text(
                json.dumps(
                    report.to_dict(),
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
            logger.warning(
                "Could not save readiness report: %s",
                exc,
            )

        return report

    def list_reports(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        reports: list[
            dict[str, Any]
        ] = []

        for path in self.report_folder.glob(
            "*.json"
        ):
            try:
                raw = json.loads(
                    path.read_text(
                        encoding="utf-8",
                    )
                )

                if isinstance(
                    raw,
                    dict,
                ):
                    reports.append(
                        raw
                    )

            except Exception:
                logger.warning(
                    "Skipping invalid readiness report: %s",
                    path.name,
                )

        reports.sort(
            key=lambda report: str(
                report.get(
                    "created_at",
                    "",
                )
            ),
            reverse=True,
        )

        return reports[
            : max(
                1,
                limit,
            )
        ]

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat(
            timespec="seconds"
        )




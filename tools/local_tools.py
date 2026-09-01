from __future__ import annotations

import ast
import math
import operator
import re

from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from config.settings import Settings
from core.providers import AIProvider
from core.exceptions import (
    FileProcessingError,
    ToolExecutionError,
)
from services.file_service import FileService
from services.rag_service import RAGService
from services.skill_service import SkillService
from services.tool_service import ToolService
from services.vision_service import (
    analyze_chart,
    analyze_image,
    compare_images,
)
from tools.tool_models import (
    ToolDefinition,
    ToolResult,
)


BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

ALLOWED_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "sqrt": math.sqrt,
    "ceil": math.ceil,
    "floor": math.floor,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
}

ALLOWED_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


def evaluate_expression(
    expression: str,
) -> int | float:
    cleaned = str(
        expression or ""
    ).strip()

    if not cleaned:
        raise ToolExecutionError(
            "The expression cannot be empty."
        )

    if len(cleaned) > 500:
        raise ToolExecutionError(
            "The expression is too long."
        )

    try:
        tree = ast.parse(
            cleaned,
            mode="eval",
        )

    except SyntaxError as exc:
        raise ToolExecutionError(
            f"Invalid mathematical expression: {exc.msg}"
        ) from exc

    def evaluate_node(
        node: ast.AST,
    ) -> int | float:
        if isinstance(
            node,
            ast.Expression,
        ):
            return evaluate_node(
                node.body
            )

        if isinstance(
            node,
            ast.Constant,
        ):
            if isinstance(
                node.value,
                (int, float),
            ):
                return node.value

            raise ToolExecutionError(
                "Only numeric constants are allowed."
            )

        if isinstance(
            node,
            ast.BinOp,
        ):
            operation = BINARY_OPERATORS.get(
                type(node.op)
            )

            if operation is None:
                raise ToolExecutionError(
                    "That mathematical operator is not allowed."
                )

            left = evaluate_node(
                node.left
            )

            right = evaluate_node(
                node.right
            )

            if (
                isinstance(node.op, ast.Pow)
                and abs(float(right)) > 100
            ):
                raise ToolExecutionError(
                    "Exponent is too large."
                )

            result = operation(
                left,
                right,
            )

            if abs(float(result)) > 1e100:
                raise ToolExecutionError(
                    "The result is too large."
                )

            return result

        if isinstance(
            node,
            ast.UnaryOp,
        ):
            operation = UNARY_OPERATORS.get(
                type(node.op)
            )

            if operation is None:
                raise ToolExecutionError(
                    "That unary operator is not allowed."
                )

            return operation(
                evaluate_node(node.operand)
            )

        if isinstance(
            node,
            ast.Name,
        ):
            if node.id in ALLOWED_CONSTANTS:
                return ALLOWED_CONSTANTS[
                    node.id
                ]

            raise ToolExecutionError(
                f"Unknown value '{node.id}'."
            )

        if isinstance(
            node,
            ast.Call,
        ):
            if not isinstance(
                node.func,
                ast.Name,
            ):
                raise ToolExecutionError(
                    "Only approved mathematical "
                    "functions are allowed."
                )

            function = ALLOWED_FUNCTIONS.get(
                node.func.id
            )

            if function is None:
                raise ToolExecutionError(
                    f"Function '{node.func.id}' is not allowed."
                )

            if node.keywords:
                raise ToolExecutionError(
                    "Named function arguments are not allowed."
                )

            arguments = [
                evaluate_node(argument)
                for argument in node.args
            ]

            return function(
                *arguments
            )

        raise ToolExecutionError(
            "The expression contains unsupported syntax."
        )

    return evaluate_node(tree)


def project_root_from_settings(
    settings: Settings,
) -> Path:
    return settings.chat_folder.parent.resolve()


def allowed_roots(
    settings: Settings,
) -> list[Path]:
    roots = {
        project_root_from_settings(
            settings
        ),
        settings.upload_folder.resolve(),
        settings.document_folder.resolve(),
        settings.report_folder.resolve(),
        settings.skills_folder.resolve(),
        settings.agent_run_folder.resolve(),
    }

    return sorted(
        roots,
        key=lambda path: str(path),
    )


def path_is_within(
    path: Path,
    root: Path,
) -> bool:
    try:
        path.relative_to(
            root
        )

        return True

    except ValueError:
        return False


def enforce_user_document_access(
    *,
    settings: Settings,
    file_service: FileService,
    path: Path,
) -> None:
    resolved = path.resolve()

    protected_roots = (
        (
            settings.upload_folder
            / "users"
        ).resolve(),
        (
            settings.document_folder
            / "users"
        ).resolve(),
    )

    if not any(
        path_is_within(
            resolved,
            root,
        )
        for root in protected_roots
    ):
        return

    private_roots = (
        file_service.upload_folder.resolve(),
        file_service.document_folder.resolve(),
    )

    if any(
        path_is_within(
            resolved,
            root,
        )
        for root in private_roots
    ):
        return

    raise ToolExecutionError(
        "Access to another user's document "
        "storage is not allowed."
    )


def resolve_safe_path(
    settings: Settings,
    requested_path: str,
    *,
    file_service: FileService | None = None,
) -> Path:
    root = project_root_from_settings(
        settings
    )

    cleaned = str(
        requested_path or "."
    ).strip()

    candidate = Path(cleaned)

    if not candidate.is_absolute():
        candidate = root / candidate

    try:
        resolved = candidate.resolve()

    except OSError as exc:
        raise ToolExecutionError(
            f"Could not resolve path: {exc}"
        ) from exc

    permitted = False

    for allowed_root in allowed_roots(
        settings
    ):
        try:
            resolved.relative_to(
                allowed_root
            )

            permitted = True
            break

        except ValueError:
            continue

    if not permitted:
        raise ToolExecutionError(
            "Access to that path is not allowed."
        )

    if file_service is not None:
        enforce_user_document_access(
            settings=settings,
            file_service=file_service,
            path=resolved,
        )

    return resolved


def build_local_tool_service(
    *,
    settings: Settings,
    file_service: FileService,
    rag_service: RAGService,
    skill_service: SkillService,
    ai_provider: AIProvider,
) -> ToolService:
    service = ToolService(
        settings=settings
    )

    def calculator_tool(
        arguments: dict[str, Any],
    ) -> ToolResult:
        expression = str(
            arguments.get(
                "expression",
                "",
            )
        )

        result = evaluate_expression(
            expression
        )

        return ToolResult(
            success=True,
            tool_name="calculator",
            content=(
                f"{expression} = {result}"
            ),
            data={
                "expression": expression,
                "result": result,
            },
        )

    service.register(
        ToolDefinition(
            name="calculator",
            description=(
                "Safely evaluate a mathematical expression."
            ),
            category="utility",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": (
                            "Mathematical expression to evaluate."
                        ),
                    }
                },
                "required": [
                    "expression"
                ],
            },
            handler=calculator_tool,
        )
    )

    def current_datetime_tool(
        arguments: dict[str, Any],
    ) -> ToolResult:
        timezone_name = str(
            arguments.get(
                "timezone",
                "",
            )
        ).strip()

        try:
            if timezone_name:
                timezone = ZoneInfo(
                    timezone_name
                )

                now = datetime.now(
                    timezone
                )

            else:
                now = datetime.now().astimezone()

        except ZoneInfoNotFoundError as exc:
            raise ToolExecutionError(
                f"Unknown timezone '{timezone_name}'."
            ) from exc

        formatted = now.strftime(
            "%A, %d %B %Y at %H:%M:%S %Z"
        )

        return ToolResult(
            success=True,
            tool_name="current_datetime",
            content=formatted,
            data={
                "iso": now.isoformat(),
                "timezone": str(
                    now.tzinfo
                ),
            },
        )

    service.register(
        ToolDefinition(
            name="current_datetime",
            description=(
                "Return the current local date and time, "
                "optionally for an IANA timezone."
            ),
            category="utility",
            parameters={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": (
                            "Optional timezone such as "
                            "Europe/London."
                        ),
                    }
                },
            },
            handler=current_datetime_tool,
        )
    )

    def list_files_tool(
        arguments: dict[str, Any],
    ) -> ToolResult:
        folder_value = str(
            arguments.get(
                "folder",
                ".",
            )
        )

        recursive = bool(
            arguments.get(
                "recursive",
                False,
            )
        )

        maximum_results = int(
            arguments.get(
                "max_results",
                100,
            )
        )

        maximum_results = max(
            1,
            min(
                maximum_results,
                500,
            ),
        )

        folder = resolve_safe_path(
            settings,
            folder_value,
            file_service=file_service,
        )

        if not folder.exists():
            raise ToolExecutionError(
                f"Folder does not exist: {folder_value}"
            )

        if not folder.is_dir():
            raise ToolExecutionError(
                f"Path is not a folder: {folder_value}"
            )

        iterator = (
            folder.rglob("*")
            if recursive
            else folder.iterdir()
        )

        project_root = (
            project_root_from_settings(
                settings
            )
        )

        entries: list[
            dict[str, Any]
        ] = []

        for path in iterator:
            try:
                enforce_user_document_access(
                    settings=settings,
                    file_service=file_service,
                    path=path,
                )

            except ToolExecutionError:
                continue

            try:
                relative_path = path.relative_to(
                    project_root
                )

            except ValueError:
                relative_path = path

            entries.append(
                {
                    "path": str(
                        relative_path
                    ),
                    "type": (
                        "directory"
                        if path.is_dir()
                        else "file"
                    ),
                    "size_bytes": (
                        path.stat().st_size
                        if path.is_file()
                        else None
                    ),
                }
            )

            if len(entries) >= maximum_results:
                break

        lines = [
            (
                f"{entry['type']}: "
                f"{entry['path']}"
                + (
                    f" ({entry['size_bytes']} bytes)"
                    if entry[
                        "size_bytes"
                    ] is not None
                    else ""
                )
            )
            for entry in entries
        ]

        return ToolResult(
            success=True,
            tool_name="list_files",
            content=(
                "\n".join(lines)
                if lines
                else "The folder is empty."
            ),
            data={
                "folder": str(folder),
                "entries": entries,
                "truncated": (
                    len(entries)
                    >= maximum_results
                ),
            },
        )

    service.register(
        ToolDefinition(
            name="list_files",
            description=(
                "List files and folders inside the local "
                "application project."
            ),
            category="filesystem",
            parameters={
                "type": "object",
                "properties": {
                    "folder": {
                        "type": "string",
                        "description": (
                            "Folder relative to the project root."
                        ),
                    },
                    "recursive": {
                        "type": "boolean",
                    },
                    "max_results": {
                        "type": "integer",
                    },
                },
            },
            handler=list_files_tool,
        )
    )

    def read_text_file_tool(
        arguments: dict[str, Any],
    ) -> ToolResult:
        requested_path = str(
            arguments.get(
                "path",
                "",
            )
        ).strip()

        if not requested_path:
            raise ToolExecutionError(
                "A file path is required."
            )

        maximum_characters = int(
            arguments.get(
                "max_characters",
                20_000,
            )
        )

        maximum_characters = max(
            100,
            min(
                maximum_characters,
                100_000,
            ),
        )

        path = resolve_safe_path(
            settings,
            requested_path,
            file_service=file_service,
        )

        if not path.exists():
            raise ToolExecutionError(
                f"File does not exist: {requested_path}"
            )

        if not path.is_file():
            raise ToolExecutionError(
                f"Path is not a file: {requested_path}"
            )

        if path.stat().st_size > (
            settings.max_upload_size_mb
            * 1024
            * 1024
        ):
            raise ToolExecutionError(
                "The file exceeds the configured size limit."
            )

        try:
            text = path.read_text(
                encoding="utf-8"
            )

        except UnicodeDecodeError:
            try:
                text = path.read_text(
                    encoding="cp1252"
                )

            except UnicodeDecodeError as exc:
                raise ToolExecutionError(
                    "The file is not readable as text."
                ) from exc

        except OSError as exc:
            raise ToolExecutionError(
                f"Could not read file: {exc}"
            ) from exc

        truncated = (
            len(text)
            > maximum_characters
        )

        output = text[
            :maximum_characters
        ]

        return ToolResult(
            success=True,
            tool_name="read_text_file",
            content=output,
            data={
                "path": str(path),
                "character_count": len(text),
                "truncated": truncated,
            },
        )

    service.register(
        ToolDefinition(
            name="read_text_file",
            description=(
                "Read a local text or source-code file "
                "inside the application project."
            ),
            category="filesystem",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                    },
                    "max_characters": {
                        "type": "integer",
                    },
                },
                "required": [
                    "path"
                ],
            },
            handler=read_text_file_tool,
        )
    )

    def search_documents_tool(
        arguments: dict[str, Any],
    ) -> ToolResult:
        query = str(
            arguments.get(
                "query",
                "",
            )
        ).strip()

        if not query:
            raise ToolExecutionError(
                "A search query is required."
            )

        top_k = int(
            arguments.get(
                "top_k",
                6,
            )
        )

        document_ids = arguments.get(
            "document_ids"
        )

        if not isinstance(
            document_ids,
            list,
        ):
            document_ids = None

        try:
            results = rag_service.search(
                query=query,
                document_ids=document_ids,
                top_k=max(
                    1,
                    min(top_k, 20),
                ),
            )

        except FileProcessingError as exc:
            raise ToolExecutionError(
                str(exc)
            ) from exc

        serialised = [
            result.to_dict()
            for result in results
        ]

        if not results:
            return ToolResult(
                success=True,
                tool_name="search_documents",
                content=(
                    "No relevant indexed document "
                    "passages were found."
                ),
                data={
                    "query": query,
                    "results": [],
                },
            )

        sections: list[str] = []

        for index, result in enumerate(
            results,
            start=1,
        ):
            score = (
                f"{result.relevance_score:.0%}"
                if result.relevance_score
                is not None
                else "unknown"
            )

            sections.append(
                f"[Result {index}]\n"
                f"Document: {result.document_title}\n"
                f"File: {result.original_name}\n"
                f"Relevance: {score}\n"
                f"{result.text}"
            )

        return ToolResult(
            success=True,
            tool_name="search_documents",
            content="\n\n---\n\n".join(
                sections
            ),
            data={
                "query": query,
                "results": serialised,
            },
        )

    service.register(
        ToolDefinition(
            name="search_documents",
            description=(
                "Search indexed local documents using "
                "Ollama embeddings and ChromaDB."
            ),
            category="knowledge",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                    },
                    "top_k": {
                        "type": "integer",
                    },
                    "document_ids": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                },
                "required": [
                    "query"
                ],
            },
            handler=search_documents_tool,
        )
    )

    def list_skills_tool(
        arguments: dict[str, Any],
    ) -> ToolResult:
        include_disabled = bool(
            arguments.get(
                "include_disabled",
                False,
            )
        )

        skills = skill_service.list_skills(
            include_disabled=include_disabled
        )

        records = [
            {
                "slug": skill.slug,
                "name": skill.name,
                "description": (
                    skill.description
                ),
                "enabled": skill.enabled,
                "built_in": skill.built_in,
                "keywords": skill.keywords,
            }
            for skill in skills
        ]

        content = "\n".join(
            (
                f"{skill.icon} {skill.name} "
                f"({skill.slug})"
                + (
                    ""
                    if skill.enabled
                    else " [disabled]"
                )
                + f"\n{skill.description}"
            )
            for skill in skills
        )

        return ToolResult(
            success=True,
            tool_name="list_skills",
            content=(
                content
                if content
                else "No local skills were found."
            ),
            data={
                "skills": records,
            },
        )

    service.register(
        ToolDefinition(
            name="list_skills",
            description=(
                "List installed local agent skills."
            ),
            category="agent",
            parameters={
                "type": "object",
                "properties": {
                    "include_disabled": {
                        "type": "boolean",
                    }
                },
            },
            handler=list_skills_tool,
        )
    )

    def save_report_tool(
        arguments: dict[str, Any],
    ) -> ToolResult:
        title = str(
            arguments.get(
                "title",
                "Local report",
            )
        ).strip()

        content = str(
            arguments.get(
                "content",
                "",
            )
        ).strip()

        if not content:
            raise ToolExecutionError(
                "Report content cannot be empty."
            )

        safe_title = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "_",
            title,
        ).strip("_")

        safe_title = (
            safe_title[:80]
            or "local_report"
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        filename = (
            f"{timestamp}_{safe_title}.md"
        )

        settings.report_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        path = (
            settings.report_folder
            / filename
        )

        report_text = (
            f"# {title}\n\n"
            f"{content.strip()}\n"
        )

        try:
            path.write_text(
                report_text,
                encoding="utf-8",
            )

        except OSError as exc:
            raise ToolExecutionError(
                f"Could not save report: {exc}"
            ) from exc

        return ToolResult(
            success=True,
            tool_name="save_report",
            content=(
                f"Report saved locally to: {path}"
            ),
            data={
                "path": str(path),
                "filename": filename,
                "title": title,
            },
        )

    service.register(
        ToolDefinition(
            name="save_report",
            description=(
                "Save Markdown content as a local report."
            ),
            category="output",
            parameters={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                    },
                    "content": {
                        "type": "string",
                    },
                },
                "required": [
                    "content"
                ],
            },
            handler=save_report_tool,
            requires_confirmation=False,
        )
    )


    def resolve_image_argument(
        arguments: dict[str, Any],
        key: str,
    ) -> Path:
        requested_path = str(
            arguments.get(
                key,
                "",
            )
        ).strip()

        if not requested_path:
            raise ToolExecutionError(
                f"Image path '{key}' is required."
            )

        path = resolve_safe_path(
            settings,
            requested_path,
            file_service=file_service,
        )

        if not path.exists():
            raise ToolExecutionError(
                f"Image does not exist: {requested_path}"
            )

        if not path.is_file():
            raise ToolExecutionError(
                f"Image path is not a file: {requested_path}"
            )

        supported_extensions = {
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".bmp",
            ".gif",
        }

        if path.suffix.lower() not in supported_extensions:
            raise ToolExecutionError(
                "Unsupported image format. "
                "Supported formats: PNG, JPG, JPEG, WEBP, BMP, GIF."
            )

        return path

    def image_analysis_tool(
        arguments: dict[str, Any],
    ) -> ToolResult:
        path = resolve_image_argument(
            arguments,
            "path",
        )

        question = str(
            arguments.get(
                "question",
                "Analyze this image",
            )
        ).strip()

        if not question:
            question = "Analyze this image"

        result = analyze_image(
            path,
            question,
            ai_provider=ai_provider,
        )

        return ToolResult(
            success=True,
            tool_name="image_analysis",
            content=str(result),
            data={
                "path": str(path),
                "question": question,
            },
        )

    service.register(
        ToolDefinition(
            name="image_analysis",
            description=(
                "Analyze a local image using the configured "
                "multimodal AI provider."
            ),
            category="vision",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Image path relative to the project root."
                        ),
                    },
                    "question": {
                        "type": "string",
                        "description": (
                            "Optional question about the image."
                        ),
                    },
                },
                "required": [
                    "path",
                ],
            },
            handler=image_analysis_tool,
        )
    )

    def chart_analysis_tool(
        arguments: dict[str, Any],
    ) -> ToolResult:
        path = resolve_image_argument(
            arguments,
            "path",
        )

        result = analyze_chart(
            path,
            ai_provider=ai_provider,
        )

        return ToolResult(
            success=True,
            tool_name="chart_analysis",
            content=str(result),
            data={
                "path": str(path),
            },
        )

    service.register(
        ToolDefinition(
            name="chart_analysis",
            description=(
                "Analyze a chart, graph, or plotted image using "
                "the configured multimodal AI provider."
            ),
            category="vision",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Chart image path relative to the project root."
                        ),
                    },
                },
                "required": [
                    "path",
                ],
            },
            handler=chart_analysis_tool,
        )
    )

    def image_compare_tool(
        arguments: dict[str, Any],
    ) -> ToolResult:
        image1 = resolve_image_argument(
            arguments,
            "image1",
        )

        image2 = resolve_image_argument(
            arguments,
            "image2",
        )

        result = compare_images(
            image1,
            image2,
            ai_provider=ai_provider,
        )

        return ToolResult(
            success=True,
            tool_name="image_compare",
            content=str(result),
            data={
                "image1": str(image1),
                "image2": str(image2),
            },
        )

    service.register(
        ToolDefinition(
            name="image_compare",
            description=(
                "Compare two local images and explain their "
                "similarities, differences, and important changes."
            ),
            category="vision",
            parameters={
                "type": "object",
                "properties": {
                    "image1": {
                        "type": "string",
                    },
                    "image2": {
                        "type": "string",
                    },
                },
                "required": [
                    "image1",
                    "image2",
                ],
            },
            handler=image_compare_tool,
        )
    )

    return service

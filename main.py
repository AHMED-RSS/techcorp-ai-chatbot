from __future__ import annotations

import base64
import json
import re

from pathlib import Path

from typing import Any

import streamlit as st

from sqlalchemy.exc import SQLAlchemyError

from agents.composer import ComposerSubmission
from agents.critic import (
    CriticReport,
    critic_report_from_dict,
)
from agents.executor import (
    PlanExecutionReport,
    execution_report_from_dict,
)
from agents.memory import MemoryItem
from agents.planner import (
    AgentPlan,
    agent_plan_from_dict,
)
from agents.router import RouteDecision
from core.bootstrap import bootstrap_application
from core.exceptions import (
    AgentExecutionError,
    ChatStorageError,
    CriticError,
    FileProcessingError,
    MemoryServiceError,
    OllamaConnectionError,
    OllamaModelError,
    PlanningError,
    SkillError,
    StudyError,
    ToolExecutionError,
    WebSearchError,
)
from core.session import (
    clear_rag_results,
    initialise_session_state,
    is_stop_requested,
    record_critic_report,
    record_execution,
    record_plan,
    record_route_decision,
    record_web_search,
    request_agent_stop,
    reset_agent_state,
)
from services.chat_service import ChatService
from services.database_chat_service import (
    DatabaseChatService,
)
from services.database_file_service import (
    DatabaseFileService,
    user_storage_key,
)
from services.database_memory_service import (
    DatabaseMemoryService,
)
from services.database_rag_service import (
    DatabaseRAGService,
)
from services.critic_service import CriticService
from services.executor_service import ExecutorService
from services.file_service import FileService
from services.memory_service import MemoryService
from services.planner_service import PlannerService
from services.rag_service import (
    RAGService,
    SearchResult,
)
from services.router_service import RouterService
from services.skill_service import (
    Skill,
    SkillService,
)
from services.study_service import StudyService
from services.tool_service import ToolService
from services.user_service import UserService
from services.web_search_service import (
    WebSearchReport,
    WebSearchService,
)
from tools.local_tools import (
    build_local_tool_service,
)
from tools.tool_models import ToolResult
from ui.auth_panel import (
    render_user_account,
    require_authenticated_user,
)
from ui.chat_sidebar import (
    create_chat,
    render_conversation_sidebar,
)
from ui.composer import render_prompt_composer
from ui.components import render_section_label
from ui.critic_panel import (
    render_critic_report,
    render_critic_sidebar,
    render_critic_workspace,
)
from ui.execution_panel import (
    render_execution_report,
    render_execution_sidebar,
    render_execution_workspace,
)
from ui.file_panel import (
    initialise_document_state,
    render_active_documents,
    render_file_sidebar,
)
from ui.layout import render_current_workspace
from ui.memory_panel import (
    render_memory_sidebar,
    render_memory_workspace,
)
from ui.plan_panel import (
    render_plan,
    render_plan_sidebar,
    render_planning_workspace,
)
from ui.sidebar import (
    render_sidebar_footer,
    render_sidebar_header,
    render_sidebar_status,
)
from ui.skills_panel import (
    render_skill_selector,
    render_skills_workspace,
    serialise_skill,
)
from ui.study_panel import render_study_workspace
from ui.styles import apply_app_styles
from ui.tool_panel import (
    render_tool_sidebar,
    render_tool_workspace,
)


st.set_page_config(
    page_title="TechCorp AI",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)


user_context = require_authenticated_user()


app = bootstrap_application()

settings = app.settings

user_service = UserService()

chat_service: ChatService = app.chats
file_service: FileService = app.files
rag_service: RAGService = app.rag
skill_service: SkillService = app.skills
tool_service: ToolService = app.tools
router_service: RouterService = app.router
planner_service: PlannerService = app.planner
executor_service: ExecutorService = app.executor
critic_service: CriticService = app.critic
memory_service: MemoryService = app.memory
study_service: StudyService = app.study
web_service: WebSearchService = app.web


initialise_session_state()

st.session_state.current_user = (
    user_context.to_dict()
)
st.session_state.current_user_id = (
    user_context.user_id
)

try:
    database_user = user_service.sync_user(
        user_context
    )

    storage_key = user_storage_key(
        database_user.user_id
    )

    user_runtime_settings = settings.model_copy(
        update={
            "task_folder": (
                settings.task_folder
                / "users"
                / storage_key
            ),
            "agent_run_folder": (
                settings.agent_run_folder
                / "users"
                / storage_key
            ),
            "report_folder": (
                settings.report_folder
                / "users"
                / storage_key
            ),
        }
    )

    user_runtime_settings.create_runtime_directories()

    chat_service = DatabaseChatService(
        user_id=database_user.user_id
    )

    memory_service = DatabaseMemoryService(
        user_id=database_user.user_id
    )

    file_service = DatabaseFileService(
        user_id=database_user.user_id,
        settings=user_runtime_settings,
    )

    rag_service = DatabaseRAGService(
        user_id=database_user.user_id,
        settings=user_runtime_settings,
        ollama_manager=app.ollama,
    )

    tool_service = build_local_tool_service(
        settings=user_runtime_settings,
        file_service=file_service,
        rag_service=rag_service,
        skill_service=skill_service,
    )

    router_service = RouterService(
        settings=user_runtime_settings,
        ollama_manager=app.ollama,
        skill_service=skill_service,
        tool_service=tool_service,
    )

    planner_service = PlannerService(
        settings=user_runtime_settings,
        ollama_manager=app.ollama,
        skill_service=skill_service,
        tool_service=tool_service,
    )

    executor_service = ExecutorService(
        settings=user_runtime_settings,
        ollama_manager=app.ollama,
        planner_service=planner_service,
        rag_service=rag_service,
        skill_service=skill_service,
        tool_service=tool_service,
    )

    study_service = StudyService(
        settings=user_runtime_settings,
        ollama_manager=app.ollama,
        rag_service=rag_service,
        file_service=file_service,
    )

    st.session_state.database_connected = True
    st.session_state.database_user_id = (
        database_user.user_id
    )
    st.session_state.database_error = None

except (SQLAlchemyError, RuntimeError) as exc:
    st.session_state.database_connected = False
    st.session_state.database_user_id = None
    st.session_state.database_error = str(exc)

    st.error(
        "TechCorp AI could not connect to "
        "the user database."
    )

    if settings.app_debug:
        st.exception(exc)
    else:
        st.caption(
            "Check PostgreSQL and the database "
            "configuration."
        )

    st.stop()


apply_app_styles()

if not st.session_state.selected_chat_model:
    st.session_state.selected_chat_model = (
        settings.ollama_chat_model
    )


SOURCE_FOLLOW_UP_PATTERNS = (
    "list the websites",
    "list of websites",
    "which websites",
    "what websites",
    "show the websites",
    "give me the websites",
    "give me website",
    "give me websites",
    "give me the list of website",
    "give me the list of websites",
    "list your sources",
    "show your sources",
    "which sources",
    "what sources",
    "give me your sources",
    "show the links",
    "give me the links",
    "list the links",
    "which links",
    "what links",
    "show the urls",
    "give me the urls",
    "where did you get",
    "where did this come from",
    "websites you looked at",
    "website you looked at",
    "websites you used",
    "website you used",
    "website you look",
    "sites you looked at",
    "sites you used",
    "sources you used",
    "links you used",
    "urls you used",
)


SIMPLE_REQUEST_PREFIXES = (
    "what is ",
    "what are ",
    "who is ",
    "who are ",
    "when is ",
    "where is ",
    "why is ",
    "how is ",
    "give me ",
    "list ",
    "show me ",
    "tell me ",
    "explain ",
    "summarise ",
    "summarize ",
    "define ",
    "translate ",
    "find ",
    "look for ",
)


MULTI_STEP_REQUEST_TERMS = (
    "create a plan",
    "build a plan",
    "make a plan",
    "step by step",
    "research and compare",
    "analyse and produce",
    "analyze and produce",
    "design and implement",
    "develop and test",
    "prepare a report",
    "write a report",
    "develop a strategy",
    "create a strategy",
    "compare multiple",
    "evaluate multiple",
    "investigate and",
    "research and",
    "plan and execute",
)


def refresh_ollama_status() -> None:
    try:
        connected = app.ollama.health_check()

        st.session_state.ollama_connected = connected

        st.session_state.ollama_models = (
            app.ollama.list_models()
            if connected
            else []
        )

    except Exception as exc:
        st.session_state.ollama_connected = False
        st.session_state.ollama_models = []
        st.session_state.last_error = str(exc)


def initialise_runtime() -> None:
    if st.session_state.startup_complete:
        return

    refresh_ollama_status()

    st.session_state.tool_runs = (
        tool_service.list_recent_runs()
    )

    st.session_state.startup_complete = True


initialise_runtime()

initialise_document_state(
    file_service=file_service,
    rag_service=rag_service,
)


def migrate_chats() -> None:
    if st.session_state.chat_migration_complete:
        return

    try:
        st.session_state.chat_migration_result = (
            chat_service.migrate_all_chats()
        )

    except ChatStorageError as exc:
        st.session_state.chat_error = str(exc)

    finally:
        st.session_state.chat_migration_complete = True


migrate_chats()


def restore_chat() -> None:
    chat_id = st.session_state.current_chat_id

    if not chat_id:
        return

    try:
        chat = chat_service.load_chat(
            chat_id
        )

    except ChatStorageError as exc:
        st.session_state.chat_error = str(exc)
        st.session_state.current_chat_id = None
        st.session_state.messages = []
        return

    if chat is None:
        st.session_state.current_chat_id = None
        st.session_state.messages = []
        return

    if not st.session_state.messages:
        st.session_state.messages = list(
            chat.get(
                "messages",
                [],
            )
        )


restore_chat()


def create_new_conversation() -> None:
    try:
        create_chat(
            chat_service
        )

        reset_agent_state()
        clear_rag_results()

        st.session_state.last_route_decision = None
        st.session_state.chat_error = None
        st.session_state.last_error = None

    except ChatStorageError as exc:
        st.session_state.chat_error = str(exc)


def append_message(
    role: str,
    content: str,
    *,
    metadata: dict[str, Any] | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> None:
    cleaned_content = str(
        content or ""
    ).strip()

    if not cleaned_content:
        return

    if not st.session_state.current_chat_id:
        chat = chat_service.create_chat()

        st.session_state.current_chat_id = chat["id"]
        st.session_state.messages = []

    message = chat_service.add_message(
        chat_id=st.session_state.current_chat_id,
        role=role,
        content=cleaned_content,
        metadata=metadata,
        attachments=attachments,
    )

    st.session_state.messages.append(
        message
    )


def model_messages() -> list[dict[str, str]]:
    prepared: list[dict[str, str]] = []

    for message in st.session_state.messages[-20:]:
        role = str(
            message.get(
                "role",
                "",
            )
        )

        content = str(
            message.get(
                "content",
                "",
            )
        ).strip()

        if (
            role
            in {
                "user",
                "assistant",
                "system",
                "tool",
            }
            and content
        ):
            prepared.append(
                {
                    "role": role,
                    "content": content,
                }
            )

    return prepared


def parse_memory_command(
    prompt: str,
) -> tuple[str, dict[str, Any]] | None:
    cleaned = prompt.strip()

    remember_match = re.match(
        r"^/remember(?:\s+(global|chat))?\s+(.+)$",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if remember_match:
        return (
            "remember",
            {
                "scope": (
                    remember_match.group(1)
                    or "global"
                ).lower(),
                "content": (
                    remember_match.group(2)
                    .strip()
                ),
            },
        )

    forget_match = re.match(
        r"^/forget\s+(.+)$",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if forget_match:
        return (
            "forget",
            {
                "query": (
                    forget_match.group(1)
                    .strip()
                )
            },
        )

    if cleaned.lower() == "/memories":
        return (
            "list",
            {},
        )

    return None


def execute_memory_command(
    command: tuple[str, dict[str, Any]],
) -> str:
    action, arguments = command

    if action == "remember":
        scope = str(
            arguments.get(
                "scope",
                "global",
            )
        )

        item = memory_service.create_memory(
            content=str(
                arguments.get(
                    "content",
                    "",
                )
            ),
            kind="note",
            source="chat_command",
            chat_id=(
                st.session_state.current_chat_id
                if scope == "chat"
                else None
            ),
        )

        return (
            "Saved as "
            + (
                "chat memory."
                if item.chat_id
                else "global memory."
            )
        )

    if action == "forget":
        query = str(
            arguments.get(
                "query",
                "",
            )
        )

        matches = memory_service.search_memories(
            query,
            chat_id=st.session_state.current_chat_id,
            limit=20,
        )

        if not matches:
            return "No matching memory was found."

        selected = [
            item
            for item in matches
            if query.lower() in item.content.lower()
        ] or matches[:1]

        deleted = sum(
            1
            for item in selected
            if memory_service.delete_memory(
                item.id
            )
        )

        return (
            f"Deleted {deleted} matching "
            "memory item(s)."
        )

    memories = memory_service.list_memories(
        include_disabled=False,
        chat_id=st.session_state.current_chat_id,
        limit=50,
    )

    if not memories:
        return "No active memories are stored."

    return (
        "Active memories:\n\n"
        + "\n".join(
            f"- [{item.kind}] {item.content}"
            for item in memories
        )
    )


def recall_memories(
    prompt: str,
) -> tuple[list[MemoryItem], str]:
    if not st.session_state.persistent_memory_enabled:
        st.session_state.last_recalled_memories = []
        return [], ""

    memories = memory_service.search_memories(
        prompt,
        chat_id=(
            st.session_state.current_chat_id
            if st.session_state.chat_memory_enabled
            else None
        ),
        limit=8,
    )

    st.session_state.last_recalled_memories = [
        item.to_dict()
        for item in memories
    ]

    return (
        memories,
        memory_service.build_memory_context(
            memories
        ),
    )


def parse_tool_command(
    prompt: str,
) -> tuple[str, dict[str, Any]] | None:
    if not prompt.strip().startswith(
        "/tool "
    ):
        return None

    remainder = prompt.strip()[
        len("/tool "):
    ].strip()

    if not remainder:
        raise ToolExecutionError(
            "Use: /tool tool_name "
            '{"argument": "value"}'
        )

    parts = remainder.split(
        maxsplit=1
    )

    arguments: dict[str, Any] = {}

    if len(parts) == 2:
        try:
            decoded = json.loads(
                parts[1]
            )

        except json.JSONDecodeError as exc:
            raise ToolExecutionError(
                f"Invalid tool JSON: {exc}"
            ) from exc

        if not isinstance(
            decoded,
            dict,
        ):
            raise ToolExecutionError(
                "Tool arguments must be a JSON object."
            )

        arguments = decoded

    return parts[0], arguments


def serialise_sources(
    results: list[SearchResult],
) -> list[dict[str, Any]]:
    return [
        result.to_dict()
        for result in results
    ]


def render_document_sources(
    sources: list[dict[str, Any]],
) -> None:
    if not sources:
        return

    with st.expander(
        f"Document sources ({len(sources)})",
        expanded=False,
    ):
        for index, source in enumerate(
            sources,
            start=1,
        ):
            st.markdown(
                f"**{index}. "
                f"{source.get('document_title', 'Untitled')}**"
            )

            score = source.get(
                "relevance_score"
            )

            st.caption(
                f"{source.get('original_name', '')} · "
                + (
                    f"Relevance {float(score):.0%}"
                    if score is not None
                    else "Relevance unavailable"
                )
            )

            text = str(
                source.get(
                    "text",
                    "",
                )
            )

            st.write(
                text[:900]
                + (
                    "…"
                    if len(text) > 900
                    else ""
                )
            )


def render_web_sources(
    results: list[dict[str, Any]],
) -> None:
    if not results:
        return

    with st.expander(
        f"Web sources ({len(results)})",
        expanded=False,
    ):
        for result in results:
            rank = int(
                result.get(
                    "rank",
                    1,
                )
            )

            title = str(
                result.get(
                    "title",
                    "Untitled result",
                )
            )

            url = str(
                result.get(
                    "url",
                    "",
                )
            )

            source = str(
                result.get(
                    "source",
                    "",
                )
            )

            if url:
                st.markdown(
                    f"**[Web {rank}] "
                    f"[{title}]({url})**"
                )

            else:
                st.markdown(
                    f"**[Web {rank}] {title}**"
                )

            if source:
                st.caption(
                    source
                )

            snippet = str(
                result.get(
                    "snippet",
                    "",
                )
            )

            if snippet:
                st.write(
                    snippet
                )


def normalise_request_text(
    prompt: str,
) -> str:
    return " ".join(
        str(
            prompt or ""
        )
        .casefold()
        .split()
    )


def is_source_follow_up(
    prompt: str,
) -> bool:
    cleaned = normalise_request_text(
        prompt
    )

    if not cleaned:
        return False

    if any(
        pattern in cleaned
        for pattern in SOURCE_FOLLOW_UP_PATTERNS
    ):
        return True

    asks_for_list = any(
        phrase in cleaned
        for phrase in (
            "list",
            "show",
            "give me",
            "which",
            "what",
        )
    )

    mentions_sources = any(
        word in cleaned
        for word in (
            "website",
            "websites",
            "site",
            "sites",
            "source",
            "sources",
            "link",
            "links",
            "url",
            "urls",
        )
    )

    refers_to_previous_use = any(
        phrase in cleaned
        for phrase in (
            "you used",
            "you look",
            "you looked",
            "previous answer",
            "previous search",
            "last answer",
            "last search",
        )
    )

    return (
        asks_for_list
        and mentions_sources
        and refers_to_previous_use
    )


def validate_web_result(
    result: Any,
) -> dict[str, Any] | None:
    if not isinstance(
        result,
        dict,
    ):
        return None

    url = str(
        result.get(
            "url",
            "",
        )
    ).strip()

    if not url.startswith(
        (
            "http://",
            "https://",
        )
    ):
        return None

    title = str(
        result.get(
            "title",
            "",
        )
    ).strip()

    source = str(
        result.get(
            "source",
            "",
        )
    ).strip()

    snippet = str(
        result.get(
            "snippet",
            "",
        )
    ).strip()

    try:
        rank = max(
            1,
            int(
                result.get(
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

    return {
        "title": title or source or url,
        "url": url,
        "source": source,
        "snippet": snippet,
        "rank": rank,
    }


def find_latest_web_results(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    for message in reversed(
        messages
    ):
        if not isinstance(
            message,
            dict,
        ):
            continue

        metadata = message.get(
            "metadata",
            {},
        )

        if not isinstance(
            metadata,
            dict,
        ):
            continue

        candidate_groups: list[Any] = [
            metadata.get(
                "web_results"
            )
        ]

        web_search = metadata.get(
            "web_search"
        )

        if isinstance(
            web_search,
            dict,
        ):
            candidate_groups.append(
                web_search.get(
                    "results"
                )
            )

        for candidate_group in candidate_groups:
            if not isinstance(
                candidate_group,
                list,
            ):
                continue

            verified_results: list[
                dict[str, Any]
            ] = []

            seen_urls: set[str] = set()

            for candidate in candidate_group:
                verified = validate_web_result(
                    candidate
                )

                if verified is None:
                    continue

                url = verified["url"]

                if url in seen_urls:
                    continue

                seen_urls.add(
                    url
                )

                verified_results.append(
                    verified
                )

            if verified_results:
                verified_results.sort(
                    key=lambda item: int(
                        item.get(
                            "rank",
                            1,
                        )
                    )
                )

                return verified_results

    return []


def build_web_source_list(
    results: list[dict[str, Any]],
) -> str:
    verified_results: list[
        dict[str, Any]
    ] = []

    seen_urls: set[str] = set()

    for item in results:
        result = validate_web_result(
            item
        )

        if result is None:
            continue

        url = result["url"]

        if url in seen_urls:
            continue

        seen_urls.add(
            url
        )

        verified_results.append(
            result
        )

    if not verified_results:
        return (
            "I do not have verified website results stored "
            "for the previous answer. Enable Web search and "
            "run the search again to collect exact source links."
        )

    lines = [
        "These are the verified websites used in the previous search:",
        "",
    ]

    for index, result in enumerate(
        verified_results,
        start=1,
    ):
        title = str(
            result.get(
                "title",
                "",
            )
        ).strip() or result["url"]

        url = result["url"]

        source = str(
            result.get(
                "source",
                "",
            )
        ).strip()

        lines.append(
            f"{index}. [{title}]({url})"
        )

        if source:
            lines.append(
                f"   Source: `{source}`"
            )

    lines.extend(
        [
            "",
            (
                "These links come directly from the stored "
                "search results. No URLs were generated or guessed."
            ),
        ]
    )

    return "\n".join(
        lines
    )


def should_create_plan_for_request(
    prompt: str,
    route: RouteDecision,
    *,
    deep_think: bool,
    force_plan: bool,
) -> bool:
    if deep_think or force_plan:
        return True

    cleaned = normalise_request_text(
        prompt
    )

    if not cleaned:
        return False

    if is_source_follow_up(
        cleaned
    ):
        return False

    if cleaned.startswith(
        (
            "/tool ",
            "/remember ",
            "/forget ",
        )
    ):
        return False

    if cleaned == "/memories":
        return False

    if route.route == "tool":
        return False

    if any(
        term in cleaned
        for term in MULTI_STEP_REQUEST_TERMS
    ):
        return True

    word_count = len(
        cleaned.split()
    )

    if (
        word_count <= 24
        and cleaned.startswith(
            SIMPLE_REQUEST_PREFIXES
        )
    ):
        return False

    if word_count <= 12:
        return False

    return word_count >= 40

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".gif",
}


IMAGE_REQUEST_TERMS = (
    "image",
    "photo",
    "picture",
    "screenshot",
    "photograph",
)


def looks_like_image_request(
    prompt: str,
) -> bool:
    cleaned = str(
        prompt or ""
    ).strip().lower()

    return any(
        term in cleaned
        for term in IMAGE_REQUEST_TERMS
    )


def is_image_attachment(
    attachment: dict[str, Any],
) -> bool:
    filename = str(
        attachment.get("original_name")
        or attachment.get("filename")
        or attachment.get("name")
        or ""
    )

    mime_type = str(
        attachment.get("mime_type")
        or attachment.get("content_type")
        or attachment.get("media_type")
        or attachment.get("type")
        or ""
    ).lower()

    suffix = Path(filename).suffix.lower()

    return (
        mime_type.startswith("image/")
        or mime_type == "image"
        or suffix in IMAGE_EXTENSIONS
    )


def decode_image_value(
    value: Any,
) -> bytes | None:
    if isinstance(value, bytes):
        return value

    if isinstance(value, bytearray):
        return bytes(value)

    if isinstance(value, memoryview):
        return value.tobytes()

    if not isinstance(value, str):
        return None

    text = value.strip()

    if not text:
        return None

    if text.startswith("data:image/") and "," in text:
        try:
            encoded = text.split(",", 1)[1]
            return base64.b64decode(encoded)
        except Exception:
            return None

    # Avoid interpreting a large Base64 value as a Windows path.
    if len(text) < 1000:
        try:
            path = Path(text).expanduser()

            if path.is_file():
                return path.read_bytes()

        except (OSError, ValueError):
            pass

    try:
        return base64.b64decode(
            text,
            validate=True,
        )
    except Exception:
        return None


def image_payload_from_attachment(
    attachment: dict[str, Any],
) -> bytes | None:
    data_keys = (
        "bytes",
        "file_bytes",
        "image_bytes",
        "data",
        "content",
        "base64",
        "base64_data",
    )

    path_keys = (
        "path",
        "file_path",
        "saved_path",
        "stored_path",
        "storage_path",
        "local_path",
        "upload_path",
    )

    for key in data_keys:
        payload = decode_image_value(
            attachment.get(key)
        )

        if payload:
            return payload

    for key in path_keys:
        payload = decode_image_value(
            attachment.get(key)
        )

        if payload:
            return payload

    # Check common nested metadata structures.
    for key in (
        "file",
        "metadata",
        "attachment",
        "document",
    ):
        nested = attachment.get(key)

        if isinstance(nested, dict):
            payload = image_payload_from_attachment(
                nested
            )

            if payload:
                return payload

    return None


def generate_vision_answer(
    prompt: str,
    attachments: list[dict[str, Any]],
) -> str | None:
    image_attachments = [
        attachment
        for attachment in attachments
        if is_image_attachment(attachment)
    ]

    if not image_attachments:
        return None

    image_payloads = [
        payload
        for attachment in image_attachments
        if (
            payload
            := image_payload_from_attachment(
                attachment
            )
        )
    ]

    if not image_payloads:
        metadata_keys = sorted(
            {
                str(key)
                for attachment in image_attachments
                for key in attachment
            }
        )

        raise RuntimeError(
            "An image was detected, but the composer did not "
            "preserve its file bytes or local path. "
            "Attachment fields found: "
            + ", ".join(metadata_keys)
        )

    ollama_images = [
        base64.b64encode(payload).decode("ascii")
        for payload in image_payloads
    ]

    question = prompt.strip() or (
        "Describe the attached image in detail."
    )

    vision_model = str(
        getattr(
            settings,
            "ollama_vision_model",
            "gemma3:4b",
        )
        or "gemma3:4b"
    )

    return app.ollama.chat(
        model=vision_model,
        temperature=0.1,
        system_prompt="""
You are TechCorp AI's visual-analysis agent.

You can see the images attached to the user message.

Analyse only details supported by the images. Describe:
- the overall scene and context,
- visible objects and animals,
- people and visible activities without identifying anyone,
- colours, shapes, patterns and textures,
- visible text,
- spatial relationships,
- uncertainty where details are unclear.

Never claim that you cannot access the attached images.
Do not invent details that are not visible.
""".strip(),
        messages=[
            {
                "role": "user",
                "content": question,
                "images": ollama_images,
            }
        ],
    )

def resolve_route(
    prompt: str,
) -> RouteDecision:
    if st.session_state.automatic_routing_enabled:
        decision = router_service.route(
            prompt,
            has_documents=bool(
                st.session_state.active_document_ids
            ),
            automatic_skill_selection=(
                st.session_state
                .automatic_skill_selection
            ),
            selected_skill=(
                st.session_state.selected_skill
            ),
            model=(
                st.session_state
                .selected_chat_model
            ),
        )

    else:
        skill = skill_service.resolve_skill(
            prompt=prompt,
            selected_slug=(
                st.session_state.selected_skill
            ),
            automatic=(
                st.session_state
                .automatic_skill_selection
            ),
            has_documents=bool(
                st.session_state.active_document_ids
            ),
        )

        route_name = "general"

        if skill.slug == "document_analyst":
            route_name = "document"

        elif skill.slug == "code_reviewer":
            route_name = "code"

        elif skill.slug == "study_coach":
            route_name = "study"

        decision = RouteDecision(
            route=route_name,
            confidence=1.0,
            reason=(
                "Automatic routing is disabled."
            ),
            recommended_skill=skill.slug,
            use_documents=(
                route_name
                in {
                    "document",
                    "study",
                }
                and bool(
                    st.session_state
                    .active_document_ids
                )
            ),
            source="manual",
        )

    record_route_decision(
        decision.to_dict()
    )

    return decision


def resolve_skill(
    prompt: str,
    route: RouteDecision,
) -> Skill:
    skill = skill_service.resolve_skill(
        prompt=prompt,
        selected_slug=(
            route.recommended_skill
            or st.session_state.selected_skill
        ),
        automatic=False,
        has_documents=bool(
            st.session_state.active_document_ids
        ),
    )

    st.session_state.current_skill = skill.slug

    st.session_state.resolved_skill = (
        serialise_skill(
            skill
        )
    )

    st.session_state.current_agent = skill.name

    return skill


def create_plan(
    prompt: str,
    route: RouteDecision,
    *,
    deep_think: bool,
) -> AgentPlan:
    st.session_state.planning_in_progress = True

    try:
        plan = planner_service.create_plan(
            prompt=prompt,
            route=route,
            has_documents=bool(
                st.session_state.active_document_ids
            ),
            model=(
                st.session_state
                .selected_chat_model
            ),
            force_plan=(
                bool(
                    st.session_state.force_planning
                )
                or deep_think
            ),
        )

        record_plan(
            plan.to_dict()
        )

        return plan

    finally:
        st.session_state.planning_in_progress = False


def execution_callback(
    report: PlanExecutionReport,
    step: Any,
    event: str,
) -> None:
    st.session_state.current_execution = (
        report.to_dict()
    )

    st.session_state.current_execution_id = (
        report.id
    )

    st.session_state.current_step_id = step.id

    st.session_state.current_step_title = (
        step.title
    )

    st.session_state.execution_progress = (
        report.progress
    )

    st.session_state.agent_status = "executing"


def execute_plan(
    plan: AgentPlan,
    *,
    web_context: str,
) -> PlanExecutionReport:
    messages = model_messages()

    if web_context:
        messages.insert(
            0,
            {
                "role": "system",
                "content": (
                    "WEB SEARCH RESULTS\n\n"
                    f"{web_context}"
                ),
            },
        )

    report = executor_service.execute_plan(
        plan=plan,
        model=(
            st.session_state.selected_chat_model
        ),
        document_ids=list(
            st.session_state.active_document_ids
        ),
        conversation_messages=messages,
        progress_callback=execution_callback,
        stop_callback=is_stop_requested,
        continue_on_error=bool(
            st.session_state
            .continue_execution_on_error
        ),
    )

    record_execution(
        report.to_dict()
    )

    return report


def reasoning_instructions(
    mode: str,
) -> tuple[str, float]:
    if mode == "deep":
        return (
            """
Use a deliberate, high-rigour approach.

Before producing the answer internally:
- identify all requirements,
- examine relevant alternatives,
- check assumptions,
- verify consistency with supplied evidence,
- consider edge cases,
- and produce a polished final answer.

Do not reveal private chain-of-thought. Present only the
useful conclusions, evidence and concise reasoning summary.
""".strip(),
            0.1,
        )

    if mode == "focused":
        return (
            """
Use a focused analytical approach. Prioritise the user's
main objective, avoid tangents and check the final answer
for completeness before returning it.
""".strip(),
            0.2,
        )

    return (
        """
Respond directly and clearly while following all supplied
evidence and application rules.
""".strip(),
        settings.agent_default_temperature,
    )


def generate_direct_answer(
    *,
    prompt: str,
    route: RouteDecision,
    skill: Skill,
    plan: AgentPlan | None,
    memory_context: str,
    web_context: str,
    reasoning_mode: str,
) -> tuple[str, list[dict[str, Any]]]:
    rag_results: list[SearchResult] = []

    last_submission = (
        st.session_state.last_composer_submission
        if isinstance(
            st.session_state.last_composer_submission,
            dict,
        )
        else {}
    )

    should_search_documents = (
        st.session_state.document_search_enabled
        and bool(
            st.session_state.active_document_ids
        )
        and (
            route.use_documents
            or route.route
            in {
                "document",
                "study",
            }
            or bool(
                last_submission.get(
                    "attachment_count",
                    0,
                )
            )
        )
    )

    if should_search_documents:
        rag_results = rag_service.search(
            query=prompt,
            document_ids=(
                st.session_state.active_document_ids
            ),
            top_k=8,
        )

    document_sources = serialise_sources(
        rag_results
    )

    document_context = (
        rag_service.build_context(
            rag_results,
            maximum_characters=20_000,
        )
        if rag_results
        else ""
    )

    plan_text = ""

    if plan is not None:
        plan_text = "\n".join(
            (
                f"{step.order}. "
                f"{step.title}: "
                f"{step.description}"
            )
            for step in plan.steps
        )

    (
        reasoning_prompt,
        temperature,
    ) = reasoning_instructions(
        reasoning_mode
    )

    system_prompt = f"""
You are TechCorp AI, a local-first assistant powered by Ollama.

ROUTE:
{route.route}

ACTIVE SKILL:
{skill_service.build_skill_prompt(skill)}

REASONING MODE:
{reasoning_mode}

{reasoning_prompt}

PLAN:
{plan_text or "No multi-step plan."}

EVIDENCE RULES:

- Local memories are user-provided context, not external evidence.
- Local document claims must be supported by supplied document sources.
- Cite local document passages with labels such as [Source 1].
- Web claims must be supported by supplied web-search results.
- Cite web claims with labels such as [Web 1].
- Use only URLs that appear exactly in the supplied web-search results.
- Never invent, reconstruct, repair, shorten or guess a URL.
- Never invent source titles, organisations or search results.
- When no verified web result is supplied, say that no verified web source is available.
- Distinguish source-derived content from inference.
- Search snippets can be incomplete; state uncertainty where appropriate.
- Do not claim that the AI model itself browsed the web.
- Do not claim a tool was run without an actual tool result.
- The user's newest instruction overrides older memory.
- Do not reveal private chain-of-thought.
- Do not output internal planning status such as STEP COMPLETE, PLAN GOAL UPDATE or NEXT STEP.
- Respond with a natural user-facing answer only.
""".strip()

    messages = model_messages()

    if memory_context:
        messages.insert(
            0,
            {
                "role": "system",
                "content": (
                    "RELEVANT LOCAL MEMORIES\n\n"
                    f"{memory_context}"
                ),
            },
        )

    if document_context:
        messages.insert(
            0,
            {
                "role": "system",
                "content": (
                    "LOCAL DOCUMENT SOURCES\n\n"
                    f"{document_context}"
                ),
            },
        )

    if web_context:
        messages.insert(
            0,
            {
                "role": "system",
                "content": (
                    "KEYLESS WEB SEARCH RESULTS\n\n"
                    f"{web_context}"
                ),
            },
        )

    output = app.ollama.chat(
        messages=messages,
        model=(
            st.session_state.selected_chat_model
        ),
        temperature=temperature,
        system_prompt=system_prompt,
    )

    return (
        output,
        document_sources,
    )


def run_critic(
    *,
    prompt: str,
    output: str,
    route: RouteDecision,
    plan: AgentPlan | None,
    execution: PlanExecutionReport | None,
    document_sources: list[dict[str, Any]],
    web_results: list[dict[str, Any]],
    skill: Skill,
) -> tuple[str, CriticReport | None]:
    if not st.session_state.automatic_critic_enabled:
        return output, None

    st.session_state.critic_in_progress = True
    st.session_state.agent_status = "reviewing"

    combined_sources = list(
        document_sources
    )

    combined_sources.extend(
        {
            "document_title": (
                f"[Web {result.get('rank', 1)}] "
                f"{result.get('title', 'Web result')}"
            ),
            "original_name": result.get(
                "source",
                "Web",
            ),
            "text": result.get(
                "snippet",
                "",
            ),
            "url": result.get(
                "url",
                "",
            ),
            "source_type": "web",
        }
        for result in web_results
    )

    try:
        report = critic_service.review_output(
            user_request=prompt,
            output=output,
            model=(
                st.session_state.selected_chat_model
            ),
            route=route,
            plan=plan,
            execution=execution,
            document_sources=combined_sources,
            tool_result=(
                st.session_state.last_tool_result
                if route.route == "tool"
                else None
            ),
            skill=serialise_skill(
                skill
            ),
        )

        record_critic_report(
            report.to_dict()
        )

        needs_revision = (
            report.requires_revision
            or report.score
            < float(
                st.session_state
                .critic_minimum_score
            )
        )

        if (
            needs_revision
            and st.session_state
            .automatic_critic_revision
        ):
            revised = critic_service.revise_output(
                report=report,
                model=(
                    st.session_state
                    .selected_chat_model
                ),
                document_sources=combined_sources,
                tool_result=(
                    st.session_state.last_tool_result
                    if route.route == "tool"
                    else None
                ),
            )

            record_critic_report(
                report.to_dict()
            )

            return revised, report

        return output, report

    finally:
        st.session_state.critic_in_progress = False


workspace = render_sidebar_header(
    settings=settings,
    create_chat_callback=create_new_conversation,
)

render_user_account(
    user_context
)

render_conversation_sidebar(
    chat_service
)

render_file_sidebar(
    file_service=file_service,
    rag_service=rag_service,
)

render_memory_sidebar(
    memory_service
)

render_tool_sidebar(
    tool_service
)

render_plan_sidebar(
    planner_service
)

render_execution_sidebar(
    executor_service
)

render_critic_sidebar(
    critic_service
)


with st.sidebar:
    render_section_label(
        "Agent routing"
    )

    st.toggle(
        "Automatic routing",
        key="automatic_routing_enabled",
    )

    st.toggle(
        "Automatic safe tools",
        key="automatic_tool_execution",
    )

    render_section_label(
        "Skills"
    )

    render_skill_selector(
        skill_service
    )

    render_section_label(
        "Local models"
    )

    installed_models = (
        st.session_state.ollama_models
    )

    if installed_models:
        selected = (
            st.session_state.selected_chat_model
        )

        if selected not in installed_models:
            selected = (
                settings.ollama_chat_model
                if settings.ollama_chat_model
                in installed_models
                else installed_models[0]
            )

        st.session_state.selected_chat_model = (
            st.selectbox(
                "Chat model",
                options=installed_models,
                index=installed_models.index(
                    selected
                ),
                key="local_model_selectbox",
            )
        )

    else:
        st.caption(
            f"Configured model: "
            f"{settings.ollama_chat_model}"
        )

    st.caption(
        f"Embedding model: "
        f"{settings.ollama_embed_model}"
    )

    if st.button(
        "↻ Refresh local status",
        use_container_width=True,
        key="refresh_local_status",
    ):
        refresh_ollama_status()
        st.rerun()


render_sidebar_status(
    settings
)

render_sidebar_footer()

render_current_workspace(
    workspace=workspace,
    settings=settings,
)


for error_key in (
    "chat_error",
    "rag_error",
    "memory_error",
    "tool_error",
    "router_error",
    "planner_error",
    "execution_error",
    "critic_error",
    "study_error",
    "web_search_error",
):
    error_value = st.session_state.get(
        error_key
    )

    if error_value:
        st.warning(
            error_value
        )


if workspace == "chat":
    render_active_documents(
        file_service
    )

    if isinstance(
        st.session_state.current_plan,
        dict,
    ):
        render_plan(
            agent_plan_from_dict(
                st.session_state.current_plan
            ),
            expanded=False,
        )

    if isinstance(
        st.session_state.current_execution,
        dict,
    ):
        render_execution_report(
            execution_report_from_dict(
                st.session_state.current_execution
            ),
            expanded=False,
        )

    if isinstance(
        st.session_state.current_critic_report,
        dict,
    ):
        render_critic_report(
            critic_report_from_dict(
                st.session_state.current_critic_report
            ),
            expanded=False,
        )

    for message in st.session_state.messages:
        content = str(
            message.get(
                "content",
                "",
            )
        )

        if not content:
            continue

        role = str(
            message.get(
                "role",
                "assistant",
            )
        )

        display_role = (
            role
            if role
            in {
                "user",
                "assistant",
            }
            else "assistant"
        )

        with st.chat_message(
            display_role
        ):
            st.markdown(
                content
            )

            attachments = message.get(
                "attachments",
                [],
            )

            if attachments:
                st.caption(
                    f"📎 {len(attachments)} attachment(s)"
                )

            metadata = message.get(
                "metadata",
                {},
            )

            if not isinstance(
                metadata,
                dict,
            ):
                continue

            composer_data = metadata.get(
                "composer"
            )

            if isinstance(
                composer_data,
                dict,
            ):
                labels = [
                    str(
                        composer_data.get(
                            "reasoning_mode",
                            "normal",
                        )
                    ).title()
                ]

                if composer_data.get(
                    "web_search_enabled"
                ):
                    labels.append(
                        "Web"
                    )

                if composer_data.get(
                    "document_search_enabled"
                ):
                    labels.append(
                        "Documents"
                    )

                st.caption(
                    "Composer: "
                    + " · ".join(
                        labels
                    )
                )

            route_data = metadata.get(
                "route"
            )

            if isinstance(
                route_data,
                dict,
            ):
                confidence = route_data.get(
                    "confidence",
                    0.5,
                )

                try:
                    confidence_value = float(
                        confidence
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    confidence_value = 0.5

                st.caption(
                    "Route: "
                    f"{route_data.get('route', 'general').title()} · "
                    f"{confidence_value:.0%}"
                )

            critic_data = metadata.get(
                "critic"
            )

            if isinstance(
                critic_data,
                dict,
            ):
                score = critic_data.get(
                    "score",
                    0,
                )

                try:
                    score_value = float(
                        score
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    score_value = 0.0

                st.caption(
                    "Quality score: "
                    f"{score_value:.0%}"
                )

            render_document_sources(
                metadata.get(
                    "document_sources",
                    [],
                )
            )

            render_web_sources(
                metadata.get(
                    "web_results",
                    [],
                )
            )

    if not st.session_state.ollama_connected:
        st.warning(
            "Ollama is offline. Start Ollama "
            "before sending an AI request."
        )

    if st.session_state.agent_running:
        st.info(
            f"Agent status: "
            f"{st.session_state.agent_status}"
        )

        if st.button(
            "Stop execution",
            type="primary",
            use_container_width=True,
            key="stop_execution_button",
        ):
            request_agent_stop()

    submission = render_prompt_composer(
        file_service=file_service,
        rag_service=rag_service,
        disabled=(
            st.session_state.agent_running
        ),
    )

    if submission is not None:
        prompt = submission.prompt

        st.session_state.last_composer_submission = (
            submission.to_dict()
        )

        st.session_state.reasoning_mode = (
            submission.reasoning_mode
        )

        st.session_state.web_search_enabled = (
            submission.web_search_enabled
        )

        st.session_state.document_search_enabled = (
            submission.document_search_enabled
        )

        attachment_metadata = [
            attachment
            for attachment in submission.attachments
            if isinstance(
                attachment,
                dict,
            )
        ]

        append_message(
            "user",
            prompt,
            metadata={
                "composer": submission.to_dict()
            },
            attachments=attachment_metadata,
        )

        if is_source_follow_up(
            prompt
        ):
            previous_results = (
                find_latest_web_results(
                    st.session_state.messages[:-1]
                )
            )

            source_answer = build_web_source_list(
                previous_results
            )

            route_metadata = {
                "route": "general",
                "confidence": 1.0,
                "reason": (
                    "Answered directly from stored "
                    "verified web results."
                ),
                "recommended_skill": (
                    "general_assistant"
                ),
                "use_documents": False,
                "source": (
                    "deterministic_follow_up"
                ),
            }

            append_message(
                "assistant",
                source_answer,
                metadata={
                    "agent": "Source Assistant",
                    "direct_response": True,
                    "response_type": (
                        "web_source_list"
                    ),
                    "web_results": previous_results,
                    "route": route_metadata,
                },
            )

            st.session_state.last_route_decision = (
                route_metadata
            )

            st.session_state.agent_status = "completed"

            st.rerun()

        memory_command = parse_memory_command(
            prompt
        )

        if memory_command is not None:
            try:
                response = execute_memory_command(
                    memory_command
                )

            except MemoryServiceError as exc:
                response = str(exc)

            append_message(
                "assistant",
                response,
                metadata={
                    "agent": "Memory Agent",
                    "memory_command": memory_command[0],
                },
            )

            st.rerun()

        explicit_tool = parse_tool_command(
            prompt
        )

        if explicit_tool is not None:
            tool_name, arguments = explicit_tool

            result: ToolResult = (
                tool_service.execute(
                    tool_name,
                    arguments,
                )
            )

            st.session_state.last_tool_result = (
                result.to_dict()
            )

            append_message(
                "assistant",
                result.content,
                metadata={
                    "agent": "Tool Agent",
                    "tool_result": result.to_dict(),
                    "composer": submission.to_dict(),
                },
            )

            st.rerun()

        if not st.session_state.ollama_connected:
            st.error(
                "Ollama must be running."
            )

            st.stop()

        image_attachments_present = any(
            is_image_attachment(attachment)
            for attachment in attachment_metadata
        )

        if image_attachments_present:
            st.session_state.agent_running = True
            st.session_state.agent_status = (
                "analysing_image"
            )
            st.session_state.current_agent = (
                "Vision Agent"
            )

            with st.chat_message("assistant"):
                try:
                    with st.spinner(
                        "Analysing the image with Gemma 3..."
                    ):
                        vision_output = (
                            generate_vision_answer(
                                prompt,
                                attachment_metadata,
                            )
                        )

                    if not vision_output:
                        raise RuntimeError(
                            "The vision model returned "
                            "an empty response."
                        )

                    st.markdown(vision_output)

                    append_message(
                        "assistant",
                        vision_output,
                        metadata={
                            "agent": "Vision Agent",
                            "composer": (
                                submission.to_dict()
                            ),
                            "route": {
                                "route": "vision",
                                "confidence": 1.0,
                                "reason": (
                                    "An image attachment "
                                    "was detected."
                                ),
                                "source": "attachment",
                            },
                            "vision_model": str(
                                getattr(
                                    settings,
                                    "ollama_vision_model",
                                    "gemma3:4b",
                                )
                            ),
                        },
                    )

                    st.session_state.agent_status = (
                        "completed"
                    )

                except Exception as exc:
                    error_message = (
                        f"Image analysis failed: {exc}"
                    )

                    st.error(error_message)

                    append_message(
                        "assistant",
                        error_message,
                        metadata={
                            "agent": "Vision Agent",
                            "vision_error": True,
                            "composer": submission.to_dict(),
                            "route": {
                                "route": "vision",
                                "confidence": 1.0,
                                "reason": (
                                    "Image processing failed."
                                ),
                                "source": "attachment",
                            },
                        },
                    )

                    st.session_state.last_error = (
                        error_message
                    )
                    st.session_state.agent_status = (
                        "failed"
                    )

                finally:
                    st.session_state.agent_running = (
                        False
                    )

            st.rerun()

        if looks_like_image_request(prompt):
            no_image_output = (
                "Please attach an image, photo or screenshot "
                "so I can analyse it."
            )

            with st.chat_message("assistant"):
                st.info(no_image_output)

            append_message(
                "assistant",
                no_image_output,
                metadata={
                    "agent": "Vision Agent",
                    "composer": submission.to_dict(),
                    "route": {
                        "route": "vision",
                        "confidence": 1.0,
                        "reason": (
                            "The request asks about an image, "
                            "but no image was attached."
                        ),
                        "source": "prompt",
                    },
                },
            )

            st.rerun()

        st.session_state.agent_running = True
        st.session_state.agent_status = "preparing"

        with st.chat_message(
            "assistant"
        ):
            output_placeholder = st.empty()

            task_state_id: str | None = None

            try:
                (
                    recalled_memories,
                    memory_context,
                ) = recall_memories(
                    prompt
                )

                web_report: WebSearchReport | None = None

                web_context = ""

                web_results: list[
                    dict[str, Any]
                ] = []

                if submission.web_search_enabled:
                    st.session_state.agent_status = (
                        "searching_web"
                    )

                    st.session_state.web_search_in_progress = (
                        True
                    )

                    with st.status(
                        "Searching the web without an API key...",
                        expanded=False,
                    ) as web_status:
                        web_report = web_service.search(
                            prompt,
                            max_results=6,
                        )

                        web_context = (
                            web_service.build_context(
                                web_report
                            )
                        )

                        web_results = [
                            result.to_dict()
                            for result
                            in web_report.results
                        ]

                        web_results = [
                            verified
                            for verified in (
                                validate_web_result(
                                    result
                                )
                                for result in web_results
                            )
                            if verified is not None
                        ]

                        record_web_search(
                            web_report.to_dict()
                        )

                        web_status.update(
                            label=(
                                f"Found "
                                f"{len(web_results)} "
                                "verified web result(s)"
                            ),
                            state="complete",
                        )

                    st.session_state.web_search_in_progress = (
                        False
                    )

                st.session_state.agent_status = "routing"

                route = resolve_route(
                    prompt
                )

                skill = resolve_skill(
                    prompt,
                    route,
                )

                task_state = (
                    memory_service.create_task_state(
                        chat_id=(
                            st.session_state.current_chat_id
                        ),
                        user_request=prompt,
                        goal=prompt,
                        status="routing",
                        route=route.to_dict(),
                        metadata={
                            "reasoning_mode": (
                                submission.reasoning_mode
                            ),
                            "web_search_id": (
                                web_report.id
                                if web_report is not None
                                else None
                            ),
                            "attachment_count": len(
                                attachment_metadata
                            ),
                            "memory_ids": [
                                item.id
                                for item in recalled_memories
                            ],
                        },
                    )
                )

                task_state_id = task_state.id

                plan: AgentPlan | None = None

                should_plan = (
                    st.session_state
                    .automatic_planning_enabled
                    and should_create_plan_for_request(
                        prompt,
                        route,
                        deep_think=(
                            submission.is_deep_think
                        ),
                        force_plan=bool(
                            st.session_state.force_planning
                        ),
                    )
                )

                if should_plan:
                    st.session_state.agent_status = "planning"

                    plan = create_plan(
                        prompt,
                        route,
                        deep_think=(
                            submission.is_deep_think
                        ),
                    )

                    task_state.goal = plan.goal
                    task_state.status = "planning"
                    task_state.plan = plan.to_dict()

                    memory_service.save_task_state(
                        task_state
                    )

                execution: PlanExecutionReport | None = None

                document_sources: list[
                    dict[str, Any]
                ] = []

                can_execute_plan = (
                    plan is not None
                    and st.session_state
                    .automatic_plan_execution
                    and not submission.web_search_enabled
                )

                if can_execute_plan:
                    st.session_state.agent_status = (
                        "executing"
                    )

                    execution = execute_plan(
                        plan,
                        web_context=web_context,
                    )

                    original_output = (
                        execution.final_output
                    )

                    document_sources = list(
                        execution.metadata.get(
                            "document_sources",
                            [],
                        )
                    )

                    task_state.execution = (
                        execution.to_dict()
                    )

                else:
                    st.session_state.agent_status = (
                        "generating"
                    )

                    (
                        original_output,
                        document_sources,
                    ) = generate_direct_answer(
                        prompt=prompt,
                        route=route,
                        skill=skill,
                        plan=plan,
                        memory_context=memory_context,
                        web_context=web_context,
                        reasoning_mode=(
                            submission.reasoning_mode
                        ),
                    )

                task_state.status = "reviewing"

                memory_service.save_task_state(
                    task_state
                )

                (
                    final_output,
                    critic_report,
                ) = run_critic(
                    prompt=prompt,
                    output=original_output,
                    route=route,
                    plan=plan,
                    execution=execution,
                    document_sources=document_sources,
                    web_results=web_results,
                    skill=skill,
                )

                task_state.status = "completed"
                task_state.final_output = final_output

                task_state.critic = (
                    critic_report.to_dict()
                    if critic_report is not None
                    else None
                )

                memory_service.save_task_state(
                    task_state
                )

                output_placeholder.markdown(
                    final_output
                )

                render_document_sources(
                    document_sources
                )

                render_web_sources(
                    web_results
                )

                if critic_report is not None:
                    render_critic_report(
                        critic_report,
                        expanded=False,
                    )

                append_message(
                    "assistant",
                    final_output,
                    metadata={
                        "agent": (
                            st.session_state.current_agent
                        ),
                        "composer": submission.to_dict(),
                        "route": route.to_dict(),
                        "plan": (
                            plan.to_dict()
                            if plan is not None
                            else None
                        ),
                        "execution": (
                            execution.to_dict()
                            if execution is not None
                            else None
                        ),
                        "skill": serialise_skill(
                            skill
                        ),
                        "critic": (
                            critic_report.to_dict()
                            if critic_report is not None
                            else None
                        ),
                        "original_output": (
                            original_output
                            if original_output != final_output
                            else None
                        ),
                        "document_sources": document_sources,
                        "web_search": (
                            web_report.to_dict()
                            if web_report is not None
                            else None
                        ),
                        "web_results": web_results,
                        "memories": [
                            item.to_dict()
                            for item in recalled_memories
                        ],
                        "task_state_id": task_state.id,
                    },
                )

                st.session_state.agent_status = "completed"

            except (
                AgentExecutionError,
                ChatStorageError,
                CriticError,
                FileProcessingError,
                MemoryServiceError,
                OllamaConnectionError,
                OllamaModelError,
                PlanningError,
                SkillError,
                StudyError,
                ToolExecutionError,
                WebSearchError,
            ) as exc:
                error_message = str(exc)

                output_placeholder.error(
                    error_message
                )

                st.session_state.last_error = (
                    error_message
                )

                st.session_state.agent_status = "failed"

                if isinstance(
                    exc,
                    WebSearchError,
                ):
                    st.session_state.web_search_error = (
                        error_message
                    )

                if task_state_id:
                    failed_state = (
                        memory_service.load_task_state(
                            task_state_id
                        )
                    )

                    if failed_state is not None:
                        failed_state.status = "failed"

                        failed_state.metadata[
                            "error"
                        ] = error_message

                        memory_service.save_task_state(
                            failed_state
                        )

            except Exception as exc:
                error_message = (
                    f"Unexpected error: {exc}"
                )

                output_placeholder.error(
                    error_message
                )

                st.session_state.last_error = (
                    error_message
                )

                st.session_state.agent_status = "failed"

            finally:
                st.session_state.agent_running = False
                st.session_state.execution_in_progress = False
                st.session_state.critic_in_progress = False
                st.session_state.web_search_in_progress = False

        st.rerun()


elif workspace == "study":
    if not st.session_state.ollama_connected:
        st.warning(
            "Ollama must be running to generate "
            "new study material."
        )

    render_study_workspace(
        study_service=study_service,
        file_service=file_service,
        model=(
            st.session_state.selected_chat_model
        ),
    )


elif workspace == "skills":
    render_skills_workspace(
        skill_service
    )


elif workspace == "tools":
    render_tool_workspace(
        tool_service
    )


elif workspace == "plans":
    render_planning_workspace(
        planner_service
    )


elif workspace == "executions":
    render_execution_workspace(
        executor_service
    )


elif workspace == "reviews":
    render_critic_workspace(
        critic_service
    )


elif workspace == "memory":
    render_memory_workspace(
        memory_service
    )


if settings.app_debug:
    with st.expander(
        "Development information",
        expanded=False,
    ):
        st.json(
            {
                "workspace": workspace,
                "ollama_connected": (
                    st.session_state
                    .ollama_connected
                ),
                "selected_model": (
                    st.session_state
                    .selected_chat_model
                ),
                "reasoning_mode": (
                    st.session_state
                    .reasoning_mode
                ),
                "web_search_enabled": (
                    st.session_state
                    .web_search_enabled
                ),
                "document_search_enabled": (
                    st.session_state
                    .document_search_enabled
                ),
                "pending_attachment_count": len(
                    st.session_state
                    .pending_attachments
                ),
                "last_web_result_count": len(
                    st.session_state
                    .last_web_results
                ),
                "agent_status": (
                    st.session_state.agent_status
                ),
                "current_skill": (
                    st.session_state.current_skill
                ),
                "current_task_id": (
                    st.session_state.current_task_id
                ),
                "current_execution_id": (
                    st.session_state
                    .current_execution_id
                ),
                "current_study_session_id": (
                    st.session_state
                    .current_study_session_id
                ),
                "last_error": (
                    st.session_state.last_error
                ),
            }
        )
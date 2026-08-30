from __future__ import annotations

from dataclasses import dataclass

from config.settings import (
    Settings,
    get_settings,
)
from core.logging_config import (
    configure_logging,
)
from core.ollama_client import (
    OllamaManager,
)
from core.providers import (
    AIProvider,
    OllamaProvider,
)
from services.chat_service import (
    ChatService,
)
from services.critic_service import (
    CriticService,
)
from services.executor_service import (
    ExecutorService,
)
from services.file_service import (
    FileService,
)
from services.memory_service import (
    MemoryService,
)
from services.planner_service import (
    PlannerService,
)
from services.rag_service import (
    RAGService,
)
from services.router_service import (
    RouterService,
)
from services.skill_service import (
    SkillService,
)
from services.study_service import (
    StudyService,
)
from services.tool_service import (
    ToolService,
)
from services.web_search_service import (
    WebSearchService,
)
from tools.local_tools import (
    build_local_tool_service,
)


@dataclass(slots=True)
class ApplicationContext:
    """
    Shared local application services.
    """

    settings: Settings
    ollama: OllamaManager
    ai: AIProvider
    chats: ChatService
    files: FileService
    rag: RAGService
    skills: SkillService
    tools: ToolService
    router: RouterService
    planner: PlannerService
    executor: ExecutorService
    critic: CriticService
    memory: MemoryService
    study: StudyService
    web: WebSearchService


_CONTEXT: ApplicationContext | None = None


def bootstrap_application(
) -> ApplicationContext:
    """
    Initialise and return all shared services.
    """

    global _CONTEXT

    if _CONTEXT is not None:
        return _CONTEXT

    settings = get_settings()

    configure_logging(
        log_folder=settings.log_folder,
        debug=settings.app_debug,
    )

    ollama_manager = OllamaManager(
        settings=settings,
    )

    ai_provider = OllamaProvider(
        ollama_manager=ollama_manager,
    )

    chat_service = ChatService(
        settings=settings,
    )

    file_service = FileService(
        settings=settings,
    )

    rag_service = RAGService(
        settings=settings,
        ai_provider=ai_provider,
    )

    skill_service = SkillService(
        settings=settings,
    )

    tool_service = build_local_tool_service(
        settings=settings,
        file_service=file_service,
        rag_service=rag_service,
        skill_service=skill_service,
    )

    router_service = RouterService(
        settings=settings,
        ollama_manager=ollama_manager,
        skill_service=skill_service,
        tool_service=tool_service,
    )

    planner_service = PlannerService(
        settings=settings,
        ai_provider=ai_provider,
        skill_service=skill_service,
        tool_service=tool_service,
    )

    executor_service = ExecutorService(
        settings=settings,
        ai_provider=ai_provider,
        planner_service=planner_service,
        rag_service=rag_service,
        skill_service=skill_service,
        tool_service=tool_service,
    )

    critic_service = CriticService(
        settings=settings,
        llm=ai_provider,
    )

    memory_service = MemoryService(
        settings=settings,
    )

    study_service = StudyService(
        settings=settings,
        ollama_manager=ollama_manager,
        rag_service=rag_service,
        file_service=file_service,
    )

    web_search_service = WebSearchService(
        settings=settings,
    )

    _CONTEXT = ApplicationContext(
        settings=settings,
        ollama=ollama_manager,
        ai=ai_provider,
        chats=chat_service,
        files=file_service,
        rag=rag_service,
        skills=skill_service,
        tools=tool_service,
        router=router_service,
        planner=planner_service,
        executor=executor_service,
        critic=critic_service,
        memory=memory_service,
        study=study_service,
        web=web_search_service,
    )

    return _CONTEXT


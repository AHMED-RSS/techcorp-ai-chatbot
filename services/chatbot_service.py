from __future__ import annotations

from services.chat_service import ChatService
from services.router_service import RouterService
from services.planner_service import PlannerService
from services.executor_service import ExecutorService


class ChatbotService:
    """
    Main application orchestration layer.

    Coordinates:
    - conversation handling
    - routing
    - planning
    - execution
    """

    def __init__(
        self,
        *,
        chat_service: ChatService,
        router_service: RouterService,
        planner_service: PlannerService,
        executor_service: ExecutorService,
    ) -> None:
        self.chats = chat_service
        self.router = router_service
        self.planner = planner_service
        self.executor = executor_service

    def process_message(
        self,
        *,
        message: str,
        model: str,
        document_ids: list[str] | None = None,
        conversation_messages: list[dict[str, str]] | None = None,
    ):
        document_ids = document_ids or []

        route = self.router.route(
            message,
            has_documents=bool(document_ids),
            model=model,
        )

        plan = self.planner.create_plan(
            prompt=message,
            route=route,
            has_documents=bool(document_ids),
            model=model,
        )

        execution = self.executor.execute_plan(
            plan=plan,
            model=model,
            document_ids=document_ids,
            conversation_messages=conversation_messages,
        )

        return execution

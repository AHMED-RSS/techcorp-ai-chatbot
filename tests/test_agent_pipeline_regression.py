from __future__ import annotations

from config.settings import get_settings
from services.router_service import RouterService
from services.planner_service import PlannerService
from services.skill_service import SkillService
from tools.local_tools import build_local_tool_service
from tests.fakes import FakeAIProvider


def test_router_to_planner_pipeline_uses_ai_provider(
    tmp_path,
):
    settings = get_settings()

    settings.skills_folder = tmp_path / "skills"
    settings.task_folder = tmp_path / "tasks"

    provider = FakeAIProvider()

    skill_service = SkillService(
        settings=settings,
    )

    skill_service.ensure_built_in_skills()

    tool_service = build_local_tool_service(
        settings=settings,
        file_service=None,
        rag_service=None,
        skill_service=skill_service,
        ai_provider=provider,
    )

    router = RouterService(
        settings=settings,
        llm=provider,
        skill_service=skill_service,
        tool_service=tool_service,
    )

    planner = PlannerService(
        settings=settings,
        ai_provider=provider,
        skill_service=skill_service,
        tool_service=tool_service,
    )

    prompt = "Explain Python functions"

    route = router.route(
        prompt=prompt,
    )

    plan = planner.create_plan(
        prompt=prompt,
        route=route,
        has_documents=False,
    )

    assert route.route in {
        "general",
        "code",
    }

    assert plan.user_request == prompt

    assert plan.steps



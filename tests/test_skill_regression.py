from __future__ import annotations

from config.settings import get_settings
from services.skill_service import SkillService


def test_skill_matching_selects_document_analyst(
    tmp_path,
):
    settings = get_settings()
    settings.skills_folder = tmp_path / "skills"

    service = SkillService(
        settings=settings,
    )

    service.ensure_built_in_skills()

    skill = service.match_skill(
        "Summarize this PDF document and extract key points",
        has_documents=True,
    )

    assert skill.slug == "document_analyst"


def test_resolve_skill_uses_selected_enabled_skill(
    tmp_path,
):
    settings = get_settings()
    settings.skills_folder = tmp_path / "skills"

    service = SkillService(
        settings=settings,
    )

    service.ensure_built_in_skills()

    skill = service.resolve_skill(
        prompt="help me write code",
        selected_slug="code_reviewer",
        automatic=False,
        has_documents=False,
    )

    assert skill.slug == "code_reviewer"


def test_resolve_skill_falls_back_when_selected_skill_disabled(
    tmp_path,
):
    settings = get_settings()
    settings.skills_folder = tmp_path / "skills"

    service = SkillService(
        settings=settings,
    )

    service.ensure_built_in_skills()

    disabled_skill = service.load_skill(
        "code_reviewer"
    )

    service.update_skill(
        "code_reviewer",
        name=disabled_skill.name,
        description=disabled_skill.description,
        instructions=disabled_skill.instructions,
        keywords=disabled_skill.keywords,
        icon=disabled_skill.icon,
        enabled=False,
    )

    skill = service.resolve_skill(
        prompt="write some code",
        selected_slug="code_reviewer",
        automatic=False,
        has_documents=False,
    )

    assert skill.slug != "code_reviewer"


def test_build_skill_prompt_contains_skill_information(
    tmp_path,
):
    settings = get_settings()
    settings.skills_folder = tmp_path / "skills"

    service = SkillService(
        settings=settings,
    )

    service.ensure_built_in_skills()

    skill = service.load_skill(
        "general_assistant"
    )

    prompt = service.build_skill_prompt(
        skill
    )

    assert "ACTIVE SKILL:" in prompt
    assert skill.name in prompt
    assert skill.instructions in prompt

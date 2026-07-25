from __future__ import annotations

import importlib

import pytest


MODULES = [
    "config.settings",
    "core.bootstrap",
    "core.exceptions",
    "core.logging_config",
    "core.ollama_client",
    "agents.composer",
    "agents.critic",
    "agents.executor",
    "agents.memory",
    "agents.planner",
    "agents.router",
    "agents.study",
    "parsers.models",
    "parsers.registry",
    "parsers.local_parsers",
    "services.chat_service",
    "services.critic_service",
    "services.executor_service",
    "services.file_service",
    "services.memory_service",
    "services.planner_service",
    "services.rag_service",
    "services.readiness_service",
    "services.router_service",
    "services.skill_service",
    "services.study_service",
    "services.tool_service",
    "services.web_search_service",
    "tools.local_tools",
    "tools.tool_models",
    "ui.chat_sidebar",
    "ui.composer",
    "ui.components",
    "ui.critic_panel",
    "ui.execution_panel",
    "ui.file_panel",
    "ui.layout",
    "ui.memory_panel",
    "ui.navigation",
    "ui.plan_panel",
    "ui.sidebar",
    "ui.skills_panel",
    "ui.study_panel",
    "ui.styles",
    "ui.tool_panel",
]


@pytest.mark.parametrize(
    "module_name",
    MODULES,
)
def test_module_imports(
    module_name: str,
) -> None:
    module = importlib.import_module(
        module_name
    )

    assert module is not None
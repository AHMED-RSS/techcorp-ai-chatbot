from __future__ import annotations

from copy import deepcopy
from typing import Any

import streamlit as st


DEFAULT_SESSION_STATE: dict[str, Any] = {
    # Authentication
    "current_user": None,
    "current_user_id": None,
    "database_connected": False,
    "database_user_id": None,
    "database_error": None,
    "preferences_loaded_user_id": None,
    "user_theme": "system",
    "preference_error": None,

    # Navigation
    "workspace": "chat",
    "sidebar_expanded": True,
    "show_settings": False,

    # Conversations
    "current_chat_id": None,
    "messages": [],
    "chat_search": "",
    "menu_chat_id": None,
    "pending_delete_chat_id": None,
    "chat_error": None,
    "chat_migration_complete": False,
    "chat_migration_result": {},

    # Advanced composer
    "reasoning_mode": "normal",
    "web_search_enabled": False,
    "document_search_enabled": True,
    "pending_attachments": [],
    "last_composer_submission": None,
    "composer_busy": False,
    "stop_requested": False,

    # Web search
    "last_web_search": None,
    "last_web_results": [],
    "web_search_history": [],
    "web_search_in_progress": False,
    "web_search_error": None,

    # Persistent memory
    "persistent_memory_enabled": True,
    "chat_memory_enabled": True,
    "last_recalled_memories": [],
    "last_saved_memory": None,
    "memory_error": None,
    "memory_workspace_search": "",
    "confirm_delete_all_memories": False,

    # Router
    "automatic_routing_enabled": True,
    "automatic_tool_execution": True,
    "last_route_decision": None,
    "route_history": [],
    "router_error": None,

    # Planning
    "automatic_planning_enabled": True,
    "force_planning": False,
    "current_goal": None,
    "current_plan": [],
    "current_task_id": None,
    "plan_history": [],
    "planner_error": None,
    "planning_in_progress": False,

    # Execution
    "automatic_plan_execution": True,
    "continue_execution_on_error": False,
    "current_execution": None,
    "current_execution_id": None,
    "execution_history": [],
    "execution_in_progress": False,
    "execution_error": None,
    "execution_progress": 0.0,
    "current_step_id": None,
    "current_step_title": None,

    # Critic
    "automatic_critic_enabled": True,
    "automatic_critic_revision": True,
    "critic_minimum_score": 0.80,
    "critic_score_slider": 0.80,
    "current_critic_report": None,
    "current_critic_report_id": None,
    "critic_history": [],
    "critic_in_progress": False,
    "critic_error": None,
    "last_original_output": None,
    "last_revised_output": None,

    # Agent
    "current_agent": "General Agent",
    "current_skill": None,
    "resolved_skill": None,
    "completed_steps": [],
    "failed_steps": [],
    "agent_events": [],
    "agent_running": False,
    "agent_status": "idle",

    # Documents
    "active_document_ids": [],
    "document_count": 0,
    "document_search_results": [],
    "last_processed_files": [],
    "last_upload_signature": None,

    # RAG
    "rag_chunk_count": 0,
    "rag_last_results": [],
    "rag_last_query": None,
    "rag_indexing": False,
    "rag_reindex_result": None,
    "rag_error": None,

    # Skills
    "selected_skill": "general_assistant",
    "automatic_skill_selection": True,
    "skill_editor_slug": None,
    "skill_editor_content": "",
    "skill_editor_dirty": False,
    "pending_delete_skill_slug": None,

    # Tools
    "tool_runs": [],
    "last_tool_result": None,
    "last_tool_name": None,
    "last_tool_arguments": {},
    "tool_error": None,
    "tool_workspace_enabled": True,

    # Study
    "study_type": "summary",
    "study_instruction": "",
    "study_result": None,
    "study_history": [],
    "study_error": None,
    "study_generation_in_progress": False,
    "current_study_session": None,
    "current_study_session_id": None,
    "study_generation_type": "summary",
    "study_library_filter": "all",
    "study_flashcard_index": 0,
    "study_flashcard_revealed": {},
    "study_quiz_answers": {},
    "study_quiz_submitted": False,

    # Runtime
    "ollama_connected": False,
    "ollama_models": [],
    "selected_chat_model": None,
    "startup_complete": False,
    "last_error": None,
}


def initialise_session_state() -> None:
    for key, default_value in (
        DEFAULT_SESSION_STATE.items()
    ):
        if key not in st.session_state:
            st.session_state[key] = (
                deepcopy(default_value)
            )


def bind_authenticated_user(
    user_id: str,
) -> bool:
    """
    Bind Streamlit state to one authenticated user.

    When the identity changes in the same browser session,
    all existing user and widget state is removed before
    defaults are restored.
    """

    cleaned_user_id = str(
        user_id or ""
    ).strip()

    if not cleaned_user_id:
        raise ValueError(
            "An authenticated user ID is required."
        )

    previous_user_id = str(
        st.session_state.get(
            "current_user_id",
            "",
        )
        or ""
    ).strip()

    user_changed = bool(
        previous_user_id
        and previous_user_id
        != cleaned_user_id
    )

    if user_changed:
        st.session_state.clear()

    initialise_session_state()

    st.session_state[
        "current_user_id"
    ] = cleaned_user_id

    return user_changed


def clear_user_session_state() -> None:
    """
    Remove all user-specific and widget state before logout.
    """

    st.session_state.clear()


def reset_agent_state() -> None:
    st.session_state.current_agent = (
        "General Agent"
    )

    st.session_state.current_skill = None
    st.session_state.resolved_skill = None
    st.session_state.current_goal = None
    st.session_state.current_plan = []
    st.session_state.current_task_id = None
    st.session_state.completed_steps = []
    st.session_state.failed_steps = []
    st.session_state.agent_events = []
    st.session_state.agent_running = False
    st.session_state.agent_status = "idle"
    st.session_state.stop_requested = False

    st.session_state.current_execution = None
    st.session_state.current_execution_id = None
    st.session_state.execution_in_progress = False
    st.session_state.execution_error = None
    st.session_state.execution_progress = 0.0
    st.session_state.current_step_id = None
    st.session_state.current_step_title = None

    st.session_state.current_critic_report = None
    st.session_state.current_critic_report_id = None
    st.session_state.critic_in_progress = False
    st.session_state.critic_error = None
    st.session_state.last_original_output = None
    st.session_state.last_revised_output = None

    st.session_state.last_recalled_memories = []
    st.session_state.memory_error = None

    st.session_state.last_web_search = None
    st.session_state.last_web_results = []
    st.session_state.web_search_error = None
    st.session_state.web_search_in_progress = False

    st.session_state.tool_error = None
    st.session_state.router_error = None
    st.session_state.planner_error = None
    st.session_state.planning_in_progress = False


def reset_composer_state() -> None:
    st.session_state.pending_attachments = []
    st.session_state.last_composer_submission = None
    st.session_state.composer_busy = False
    st.session_state.stop_requested = False


def clear_rag_results() -> None:
    st.session_state.rag_last_results = []
    st.session_state.rag_last_query = None
    st.session_state.rag_error = None


def record_route_decision(
    decision: dict[str, Any],
) -> None:
    st.session_state.last_route_decision = (
        deepcopy(decision)
    )

    history = list(
        st.session_state.route_history
    )

    history.append(
        deepcopy(decision)
    )

    st.session_state.route_history = (
        history[-50:]
    )


def record_plan(
    plan: dict[str, Any],
) -> None:
    st.session_state.current_plan = (
        deepcopy(plan)
    )

    st.session_state.current_goal = (
        plan.get(
            "goal"
        )
    )

    st.session_state.current_task_id = (
        plan.get(
            "id"
        )
    )

    history = list(
        st.session_state.plan_history
    )

    history.append(
        deepcopy(plan)
    )

    st.session_state.plan_history = (
        history[-50:]
    )


def record_execution(
    execution: dict[str, Any],
) -> None:
    st.session_state.current_execution = (
        deepcopy(execution)
    )

    st.session_state.current_execution_id = (
        execution.get(
            "id"
        )
    )

    steps = execution.get(
        "steps",
        [],
    )

    st.session_state.completed_steps = [
        step.get(
            "step_id"
        )
        for step in steps
        if (
            isinstance(
                step,
                dict,
            )
            and step.get(
                "status"
            )
            == "completed"
        )
    ]

    st.session_state.failed_steps = [
        step.get(
            "step_id"
        )
        for step in steps
        if (
            isinstance(
                step,
                dict,
            )
            and step.get(
                "status"
            )
            == "failed"
        )
    ]

    history = list(
        st.session_state.execution_history
    )

    history.append(
        deepcopy(execution)
    )

    st.session_state.execution_history = (
        history[-50:]
    )


def record_critic_report(
    report: dict[str, Any],
) -> None:
    st.session_state.current_critic_report = (
        deepcopy(report)
    )

    st.session_state.current_critic_report_id = (
        report.get(
            "id"
        )
    )

    history = list(
        st.session_state.critic_history
    )

    history.append(
        deepcopy(report)
    )

    st.session_state.critic_history = (
        history[-50:]
    )


def record_web_search(
    report: dict[str, Any],
) -> None:
    st.session_state.last_web_search = (
        deepcopy(report)
    )

    st.session_state.last_web_results = (
        deepcopy(
            report.get(
                "results",
                [],
            )
        )
    )

    history = list(
        st.session_state.web_search_history
    )

    history.append(
        deepcopy(report)
    )

    st.session_state.web_search_history = (
        history[-50:]
    )


def add_agent_event(
    event_type: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    st.session_state.agent_events.append(
        {
            "type": event_type,
            "message": message,
            "metadata": metadata or {},
        }
    )


def request_agent_stop() -> None:
    st.session_state.stop_requested = True
    st.session_state.agent_status = (
        "stopping"
    )


def is_stop_requested() -> bool:
    return bool(
        st.session_state.get(
            "stop_requested",
            False,
        )
    )
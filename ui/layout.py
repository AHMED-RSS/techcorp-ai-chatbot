from __future__ import annotations

import streamlit as st

from config.settings import Settings
from ui.components import (
    render_empty_chat,
    render_page_header,
)


WORKSPACE_HEADERS = {
    "chat": {
        "title": "TechCorp AI",
        "subtitle": (
            "Ask questions, analyse files, "
            "or give the agent a goal."
        ),
    },
    "study": {
        "title": "Study workspace",
        "subtitle": (
            "Create summaries, notes, flashcards, "
            "quizzes and revision material."
        ),
    },
    "skills": {
        "title": "Skills library",
        "subtitle": (
            "Manage reusable instructions for "
            "specialised agent workflows."
        ),
    },
    "tools": {
        "title": "Local tools",
        "subtitle": (
            "Inspect and run registered tools "
            "inside the local workspace."
        ),
    },
    "plans": {
        "title": "Agent plans",
        "subtitle": (
            "Review locally generated multi-step plans."
        ),
    },
    "executions": {
        "title": "Agent runs",
        "subtitle": (
            "Inspect saved plan executions and step results."
        ),
    },
    "reviews": {
        "title": "Quality reviews",
        "subtitle": (
            "Inspect critic reports, scores and revisions."
        ),
    },
    "memory": {
        "title": "Local memory",
        "subtitle": (
            "Manage persistent memories and task snapshots."
        ),
    },
}


def render_workspace_header(
    workspace: str,
) -> None:
    content = WORKSPACE_HEADERS.get(
        workspace,
        WORKSPACE_HEADERS["chat"],
    )

    render_page_header(
        title=content["title"],
        subtitle=content["subtitle"],
    )


def render_chat_placeholder() -> None:
    messages = st.session_state.get(
        "messages",
        [],
    )

    if not messages:
        render_empty_chat()


def render_current_workspace(
    workspace: str,
    settings: Settings,
) -> None:
    """
    Render the shared page heading.

    Individual workspaces are rendered by main.py.
    """

    del settings

    render_workspace_header(
        workspace
    )

    if workspace == "chat":
        render_chat_placeholder()
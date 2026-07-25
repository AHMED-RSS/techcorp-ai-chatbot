from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True, slots=True)
class NavigationItem:
    """
    One application workspace navigation item.
    """

    key: str
    label: str
    icon: str
    description: str


NAVIGATION_ITEMS: tuple[NavigationItem, ...] = (
    NavigationItem(
        key="chat",
        label="Chat",
        icon="◉",
        description="Talk to local agents.",
    ),
    NavigationItem(
        key="study",
        label="Study",
        icon="◇",
        description=(
            "Create summaries, notes, flashcards "
            "and quizzes from local documents."
        ),
    ),
    NavigationItem(
        key="skills",
        label="Skills",
        icon="✦",
        description="Manage local agent skills.",
    ),
    NavigationItem(
        key="tools",
        label="Tools",
        icon="⚙",
        description="Run registered local tools.",
    ),
    NavigationItem(
        key="plans",
        label="Plans",
        icon="☷",
        description="Review saved agent plans.",
    ),
    NavigationItem(
        key="executions",
        label="Runs",
        icon="▶",
        description="Review saved plan executions.",
    ),
    NavigationItem(
        key="reviews",
        label="Reviews",
        icon="✓",
        description="Review local critic reports.",
    ),
    NavigationItem(
        key="memory",
        label="Memory",
        icon="◫",
        description=(
            "Manage persistent memories and "
            "task-state snapshots."
        ),
    ),
)


VALID_WORKSPACES = {
    item.key
    for item in NAVIGATION_ITEMS
}


def _current_workspace() -> str:
    """
    Return a valid current workspace.
    """

    workspace = str(
        st.session_state.get(
            "workspace",
            "chat",
        )
    ).strip()

    if workspace not in VALID_WORKSPACES:
        workspace = "chat"
        st.session_state.workspace = workspace

    return workspace


def render_workspace_navigation() -> str:
    """
    Render sidebar workspace buttons and return the selected workspace.

    This is the function expected by ui/sidebar.py.
    """

    current_workspace = _current_workspace()

    for item in NAVIGATION_ITEMS:
        is_active = (
            current_workspace
            == item.key
        )

        if st.button(
            f"{item.icon}  {item.label}",
            key=(
                "navigation_button_"
                f"{item.key}"
            ),
            help=item.description,
            use_container_width=True,
            type=(
                "primary"
                if is_active
                else "secondary"
            ),
        ):
            st.session_state.workspace = item.key
            st.rerun()

    return _current_workspace()


def render_navigation() -> str:
    """
    Compatibility alias for older application code.
    """

    return render_workspace_navigation()
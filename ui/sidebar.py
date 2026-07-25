from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

from config.settings import Settings
from ui.components import (
    render_agent_panel,
    render_brand,
    render_html,
    render_section_label,
)
from ui.navigation import (
    render_workspace_navigation,
)


CreateChatCallback = Callable[
    [],
    Any,
]


def render_sidebar_header(
    settings: Settings,
    *,
    create_chat_callback: (
        CreateChatCallback
        | None
    ) = None,
) -> str:
    """
    Render the persistent sidebar header and workspace navigation.
    """

    with st.sidebar:
        render_brand(
            name=settings.app_name,
            subtitle=settings.app_subtitle,
        )

        if st.button(
            "＋ New conversation",
            key="create_new_conversation",
            use_container_width=True,
        ):
            if create_chat_callback is not None:
                create_chat_callback()

            else:
                st.session_state.current_chat_id = None
                st.session_state.messages = []

            st.rerun()

        render_html(
            """
            <div class="tc-sidebar-spacer"></div>
            """
        )

        workspace = (
            render_workspace_navigation()
        )

    return workspace


def render_sidebar_status(
    settings: Settings,
) -> None:
    with st.sidebar:
        render_section_label(
            "Workspace status"
        )

        selected_model = str(
            st.session_state.get(
                "selected_chat_model",
                settings.ollama_chat_model,
            )
            or settings.ollama_chat_model
        )

        render_agent_panel(
            agent_name=str(
                st.session_state.get(
                    "current_agent",
                    "General Agent",
                )
            ),
            model_name=selected_model,
            reasoning_mode=str(
                st.session_state.get(
                    "reasoning_mode",
                    "normal",
                )
            ),
            document_count=int(
                st.session_state.get(
                    "document_count",
                    0,
                )
                or 0
            ),
            ollama_connected=bool(
                st.session_state.get(
                    "ollama_connected",
                    False,
                )
            ),
        )


def render_sidebar_footer() -> None:
    with st.sidebar:
        render_html(
            """
            <div class="tc-sidebar-footer">
                Local-first AI workspace
                <br>
                Ollama · Skills · Agent Tools
            </div>
            """
        )
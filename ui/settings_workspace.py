from __future__ import annotations

import streamlit as st

from ui.components import render_section_label


SETTINGS_SECTIONS = [
    "AI Behavior",
    "Memory",
    "Planning",
    "Execution",
    "Quality",
    "Models",
]


def render_settings_workspace() -> None:
    """
    Render the settings workspace.
    """

    st.title("Settings")

    st.caption(
        "Configure your AI workspace, "
        "automation, memory and models."
    )

    status_left, status_right = st.columns(2)

    with status_left:
        with st.container(border=True):
            st.subheader("AI Workspace")

            st.write(
                "Model:",
                st.session_state.get(
                    "selected_chat_model",
                    "Not selected",
                ),
            )

    with status_right:
        with st.container(border=True):
            st.subheader("Runtime")

            st.write(
                "Ollama:",
                (
                    "Connected"
                    if st.session_state.get(
                        "ollama_connected",
                        False,
                    )
                    else "Offline"
                ),
            )

    st.divider()

    if "settings_section" not in st.session_state:
        st.session_state.settings_section = (
            "AI Behavior"
        )

    left, right = st.columns(
        [1, 3]
    )

    with left:
        render_section_label(
            "Categories"
        )

        for section in SETTINGS_SECTIONS:
            if st.button(
                section,
                key=f"settings_{section}",
                use_container_width=True,
                type=(
                    "primary"
                    if st.session_state.settings_section
                    == section
                    else "secondary"
                ),
            ):
                st.session_state.settings_section = section
                st.rerun()


    with right:

        section = (
            st.session_state.settings_section
        )

        render_section_label(
            section
        )


        if section == "AI Behavior":

            with st.container(border=True):
                st.subheader(
                    "Agent Control"
                )

                st.toggle(
                    "Automatic routing",
                    key="automatic_routing_enabled",
                )

                st.toggle(
                    "Automatic safe tools",
                    key="automatic_tool_execution",
                )

                st.toggle(
                    "Automatic skill selection",
                    key="automatic_skill_selection",
                )


        elif section == "Memory":

            with st.container(border=True):
                st.subheader(
                    "Memory Management"
                )

                st.toggle(
                    "Persistent memory",
                    key="persistent_memory_enabled",
                )

                st.toggle(
                    "Chat memory",
                    key="chat_memory_enabled",
                )


        elif section == "Planning":

            with st.container(border=True):
                st.subheader(
                    "Planning Automation"
                )

                st.toggle(
                    "Automatic planning",
                    key="automatic_planning_enabled",
                )

                st.toggle(
                    "Always create a plan",
                    key="force_planning",
                )


        elif section == "Execution":

            with st.container(border=True):
                st.subheader(
                    "Execution Control"
                )

                st.toggle(
                    "Execute plans automatically",
                    key="automatic_plan_execution",
                )

                st.toggle(
                    "Continue after step errors",
                    key="continue_execution_on_error",
                )


        elif section == "Quality":

            with st.container(border=True):
                st.subheader(
                    "Quality Critic"
                )

                st.toggle(
                    "Review answers automatically",
                    key="automatic_critic_enabled",
                )

                st.toggle(
                    "Automatically apply revisions",
                    key="automatic_critic_revision",
                )

                st.slider(
                    "Minimum quality score",
                    0.0,
                    1.0,
                    0.8,
                    0.05,
                    key="critic_score_slider",
                )


        elif section == "Models":

            with st.container(border=True):
                st.subheader(
                    "Local Models"
                )

                st.write(
                    "Chat model:",
                    st.session_state.get(
                        "selected_chat_model",
                        "Not selected",
                    ),
                )

                st.write(
                    "Embedding model:",
                    st.session_state.get(
                        "embedding_model",
                        "nomic-embed-text",
                    ),
                )

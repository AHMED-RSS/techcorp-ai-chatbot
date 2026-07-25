from __future__ import annotations

import streamlit as st

from agents.memory import (
    MemoryItem,
    TaskState,
)
from core.exceptions import (
    MemoryServiceError,
)
from services.memory_service import (
    MemoryService,
)
from ui.components import (
    render_section_label,
)


MEMORY_ICONS = {
    "preference": "🎛️",
    "fact": "🧾",
    "instruction": "📌",
    "project": "🗂️",
    "profile": "👤",
    "note": "📝",
}


TASK_STATUS_ICONS = {
    "pending": "○",
    "routing": "⇢",
    "planning": "☷",
    "executing": "▶",
    "reviewing": "✓",
    "completed": "✅",
    "failed": "❌",
    "stopped": "■",
}


def render_memory_item(
    memory_service: MemoryService,
    item: MemoryItem,
) -> None:
    icon = MEMORY_ICONS.get(
        item.kind,
        "📝",
    )

    with st.container(
        border=True
    ):
        columns = st.columns(
            [5, 1],
            gap="small",
        )

        with columns[0]:
            st.markdown(
                f"**{icon} "
                f"{item.kind.title()}**"
            )

            st.write(
                item.content
            )

            scope = (
                "Chat memory"
                if item.chat_id
                else "Global memory"
            )

            state = (
                "Enabled"
                if item.enabled
                else "Disabled"
            )

            st.caption(
                f"{scope} · {state} · "
                f"Used {item.access_count} time(s)"
            )

            if item.keywords:
                st.caption(
                    "Keywords: "
                    + ", ".join(
                        item.keywords
                    )
                )

        with columns[1]:
            if st.button(
                "Delete",
                key=(
                    "delete_memory_"
                    f"{item.id}"
                ),
                use_container_width=True,
            ):
                try:
                    memory_service.delete_memory(
                        item.id
                    )

                    st.toast(
                        "Memory deleted"
                    )

                    st.rerun()

                except MemoryServiceError as exc:
                    st.error(
                        str(exc)
                    )

        with st.expander(
            "Edit memory",
            expanded=False,
        ):
            with st.form(
                "edit_memory_form_"
                f"{item.id}"
            ):
                content = st.text_area(
                    "Content",
                    value=item.content,
                    height=120,
                )

                kind_options = [
                    "preference",
                    "fact",
                    "instruction",
                    "project",
                    "profile",
                    "note",
                ]

                kind = st.selectbox(
                    "Type",
                    options=kind_options,
                    index=(
                        kind_options.index(
                            item.kind
                        )
                        if item.kind
                        in kind_options
                        else len(
                            kind_options
                        )
                        - 1
                    ),
                )

                keywords = st.text_input(
                    "Keywords",
                    value=", ".join(
                        item.keywords
                    ),
                )

                enabled = st.checkbox(
                    "Enabled",
                    value=item.enabled,
                )

                submitted = (
                    st.form_submit_button(
                        "Save memory",
                        use_container_width=True,
                        type="primary",
                    )
                )

                if submitted:
                    try:
                        memory_service.update_memory(
                            item.id,
                            content=content,
                            kind=kind,
                            keywords=keywords,
                            enabled=enabled,
                        )

                        st.toast(
                            "Memory updated"
                        )

                        st.rerun()

                    except MemoryServiceError as exc:
                        st.error(
                            str(exc)
                        )


def render_task_state(
    state: TaskState,
) -> None:
    icon = TASK_STATUS_ICONS.get(
        state.status,
        "○",
    )

    with st.container(
        border=True
    ):
        st.markdown(
            f"**{icon} "
            f"{state.goal or state.user_request}**"
        )

        st.caption(
            f"Status: {state.status.title()} · "
            f"Updated: {state.updated_at}"
        )

        if state.final_output:
            with st.expander(
                "Final output",
                expanded=False,
            ):
                st.markdown(
                    state.final_output
                )

        with st.expander(
            "Task state data",
            expanded=False,
        ):
            st.json(
                state.to_dict()
            )


def render_memory_sidebar(
    memory_service: MemoryService,
) -> None:
    with st.sidebar:
        render_section_label(
            "Memory"
        )

        st.toggle(
            "Use persistent memory",
            key="persistent_memory_enabled",
            help=(
                "Retrieve relevant local memories "
                "and include them in agent context."
            ),
        )

        st.toggle(
            "Use chat-scoped memory",
            key="chat_memory_enabled",
            disabled=(
                not st.session_state
                .persistent_memory_enabled
            ),
            help=(
                "Allow memories that apply only to "
                "the current conversation."
            ),
        )

        memories = (
            memory_service.list_memories(
                include_disabled=False,
                limit=1_000,
            )
        )

        task_states = (
            memory_service.list_task_states(
                limit=1_000,
            )
        )

        st.caption(
            f"{len(memories)} active memories · "
            f"{len(task_states)} task snapshots"
        )

        last_memories = (
            st.session_state
            .last_recalled_memories
        )

        if last_memories:
            st.caption(
                f"Last prompt recalled "
                f"{len(last_memories)} memory item(s)"
            )

        with st.expander(
            "Quick memory",
            expanded=False,
        ):
            with st.form(
                "sidebar_quick_memory_form",
                clear_on_submit=True,
            ):
                content = st.text_area(
                    "Remember",
                    placeholder=(
                        "Example: I prefer complete "
                        "replacement files instead of patches."
                    ),
                    height=100,
                )

                kind = st.selectbox(
                    "Type",
                    options=[
                        "preference",
                        "fact",
                        "instruction",
                        "project",
                        "profile",
                        "note",
                    ],
                )

                chat_only = st.checkbox(
                    "Only for this chat",
                    value=False,
                )

                submitted = (
                    st.form_submit_button(
                        "Save memory",
                        use_container_width=True,
                    )
                )

                if submitted:
                    try:
                        item = (
                            memory_service
                            .create_memory(
                                content=content,
                                kind=kind,
                                source="sidebar",
                                chat_id=(
                                    st.session_state
                                    .current_chat_id
                                    if chat_only
                                    else None
                                ),
                            )
                        )

                        st.session_state.last_saved_memory = (
                            item.to_dict()
                        )

                        st.toast(
                            "Memory saved locally"
                        )

                        st.rerun()

                    except MemoryServiceError as exc:
                        st.error(
                            str(exc)
                        )


def render_memory_workspace(
    memory_service: MemoryService,
) -> None:
    st.markdown(
        "## Local memory"
    )

    st.caption(
        "Memories and task snapshots are stored "
        "only in the local project."
    )

    memory_tab, task_tab, create_tab = st.tabs(
        [
            "Memories",
            "Task state",
            "Create memory",
        ]
    )

    with memory_tab:
        search_text = st.text_input(
            "Search memories",
            key="memory_workspace_search",
            placeholder=(
                "Search preferences, facts or instructions"
            ),
        )

        include_disabled = st.checkbox(
            "Show disabled memories",
            value=True,
            key="show_disabled_memories",
        )

        if search_text.strip():
            memories = (
                memory_service
                .search_memories(
                    search_text,
                    chat_id=(
                        st.session_state
                        .current_chat_id
                    ),
                    limit=100,
                )
            )

        else:
            memories = (
                memory_service
                .list_memories(
                    include_disabled=(
                        include_disabled
                    ),
                    limit=500,
                )
            )

        metric_columns = st.columns(
            3,
            gap="small",
        )

        with metric_columns[0]:
            st.metric(
                "Memories",
                len(memories),
            )

        with metric_columns[1]:
            st.metric(
                "Global",
                sum(
                    1
                    for item in memories
                    if item.chat_id is None
                ),
            )

        with metric_columns[2]:
            st.metric(
                "Chat scoped",
                sum(
                    1
                    for item in memories
                    if item.chat_id is not None
                ),
            )

        if not memories:
            st.info(
                "No matching memories were found."
            )

        for item in memories:
            render_memory_item(
                memory_service,
                item,
            )

        st.divider()

        if st.button(
            "Delete all memories",
            key="delete_all_memories_button",
            use_container_width=True,
        ):
            st.session_state.confirm_delete_all_memories = (
                True
            )

        if st.session_state.get(
            "confirm_delete_all_memories",
            False,
        ):
            st.warning(
                "Delete every stored memory permanently?"
            )

            confirmation_columns = st.columns(
                2,
                gap="small",
            )

            with confirmation_columns[0]:
                if st.button(
                    "Confirm delete",
                    key="confirm_delete_all_memories_button",
                    type="primary",
                    use_container_width=True,
                ):
                    deleted = (
                        memory_service
                        .clear_memories()
                    )

                    st.session_state.confirm_delete_all_memories = (
                        False
                    )

                    st.toast(
                        f"Deleted {deleted} memories"
                    )

                    st.rerun()

            with confirmation_columns[1]:
                if st.button(
                    "Cancel",
                    key="cancel_delete_all_memories_button",
                    use_container_width=True,
                ):
                    st.session_state.confirm_delete_all_memories = (
                        False
                    )

                    st.rerun()

    with task_tab:
        current_chat_only = st.checkbox(
            "Current chat only",
            value=False,
            key="task_state_current_chat_only",
        )

        states = (
            memory_service
            .list_task_states(
                chat_id=(
                    st.session_state
                    .current_chat_id
                    if current_chat_only
                    else None
                ),
                limit=200,
            )
        )

        st.metric(
            "Task snapshots",
            len(states),
        )

        if not states:
            st.info(
                "No task snapshots are available."
            )

        for state in states:
            render_task_state(
                state
            )

    with create_tab:
        with st.form(
            "create_memory_workspace_form",
            clear_on_submit=True,
        ):
            content = st.text_area(
                "Memory content",
                height=180,
                placeholder=(
                    "Write a durable fact, preference "
                    "or instruction."
                ),
            )

            kind = st.selectbox(
                "Memory type",
                options=[
                    "preference",
                    "fact",
                    "instruction",
                    "project",
                    "profile",
                    "note",
                ],
                key="create_memory_kind",
            )

            keywords = st.text_input(
                "Keywords",
                placeholder=(
                    "streamlit, full files, local AI"
                ),
            )

            chat_only = st.checkbox(
                "Limit to current chat",
                value=False,
            )

            submitted = (
                st.form_submit_button(
                    "Create memory",
                    type="primary",
                    use_container_width=True,
                )
            )

            if submitted:
                try:
                    memory_service.create_memory(
                        content=content,
                        kind=kind,
                        keywords=keywords,
                        source="workspace",
                        chat_id=(
                            st.session_state
                            .current_chat_id
                            if chat_only
                            else None
                        ),
                    )

                    st.toast(
                        "Memory created"
                    )

                    st.rerun()

                except MemoryServiceError as exc:
                    st.error(
                        str(exc)
                    )
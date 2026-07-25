from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from core.exceptions import ChatStorageError
from services.chat_service import ChatService
from ui.components import render_section_label


def open_chat(
    chat_service: ChatService,
    chat_id: str,
) -> None:
    chat = chat_service.load_chat(
        chat_id
    )

    if chat is None:
        st.session_state.last_error = (
            "Conversation was not found."
        )
        return

    st.session_state.current_chat_id = (
        chat["id"]
    )

    st.session_state.messages = list(
        chat.get("messages", [])
    )

    st.session_state.menu_chat_id = None
    st.session_state.pending_delete_chat_id = None


def create_chat(
    chat_service: ChatService,
) -> None:
    chat = chat_service.create_chat()

    st.session_state.current_chat_id = (
        chat["id"]
    )

    st.session_state.messages = []
    st.session_state.menu_chat_id = None
    st.session_state.pending_delete_chat_id = None


def render_chat_item(
    chat_service: ChatService,
    chat: dict[str, Any],
) -> None:
    chat_id = str(chat["id"])
    title = str(
        chat.get(
            "title",
            "New conversation",
        )
    )

    is_active = (
        st.session_state.current_chat_id
        == chat_id
    )

    display_title = (
        f"📌 {title}"
        if chat.get("pinned", False)
        else title
    )

    columns = st.columns(
        [5.2, 0.8],
        gap="small",
    )

    with columns[0]:
        button_type = (
            "primary"
            if is_active
            else "secondary"
        )

        if st.button(
            display_title,
            key=f"open_chat_{chat_id}",
            use_container_width=True,
            type=button_type,
            help=title,
        ):
            open_chat(
                chat_service,
                chat_id,
            )

            st.rerun()

    with columns[1]:
        if st.button(
            "⋯",
            key=f"chat_menu_{chat_id}",
            help="Conversation options",
            use_container_width=True,
        ):
            if (
                st.session_state.menu_chat_id
                == chat_id
            ):
                st.session_state.menu_chat_id = (
                    None
                )
            else:
                st.session_state.menu_chat_id = (
                    chat_id
                )

            st.rerun()


def render_chat_manager(
    chat_service: ChatService,
) -> None:
    chat_id = st.session_state.get(
        "menu_chat_id"
    )

    if not chat_id:
        return

    chat = chat_service.load_chat(
        chat_id
    )

    if chat is None:
        st.session_state.menu_chat_id = None
        return

    with st.container(
        border=True,
    ):
        st.markdown(
            f"""
            <div style="
                font-size: 0.78rem;
                font-weight: 700;
                margin-bottom: 0.45rem;
            ">
                Manage conversation
            </div>

            <div style="
                color: #71717a;
                font-size: 0.72rem;
                margin-bottom: 0.6rem;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            ">
                {escape(chat["title"])}
            </div>
            """,
            unsafe_allow_html=True,
        )

        rename_value = st.text_input(
            "Conversation name",
            value=chat["title"],
            key=f"rename_input_{chat_id}",
            label_visibility="collapsed",
        )

        rename_column, pin_column = st.columns(
            2,
            gap="small",
        )

        with rename_column:
            if st.button(
                "Rename",
                key=f"rename_chat_{chat_id}",
                use_container_width=True,
            ):
                try:
                    chat_service.rename_chat(
                        chat_id,
                        rename_value,
                    )

                    st.session_state.menu_chat_id = (
                        None
                    )

                    st.toast(
                        "Conversation renamed"
                    )

                    st.rerun()

                except ChatStorageError as exc:
                    st.error(str(exc))

        with pin_column:
            pin_label = (
                "Unpin"
                if chat.get("pinned", False)
                else "Pin"
            )

            if st.button(
                pin_label,
                key=f"pin_chat_{chat_id}",
                use_container_width=True,
            ):
                try:
                    chat_service.toggle_pin(
                        chat_id
                    )

                    st.session_state.menu_chat_id = (
                        None
                    )

                    st.toast(
                        f"Conversation {pin_label.lower()}ned"
                    )

                    st.rerun()

                except ChatStorageError as exc:
                    st.error(str(exc))

        delete_requested = (
            st.session_state.pending_delete_chat_id
            == chat_id
        )

        if not delete_requested:
            if st.button(
                "Delete conversation",
                key=f"request_delete_{chat_id}",
                use_container_width=True,
            ):
                st.session_state.pending_delete_chat_id = (
                    chat_id
                )

                st.rerun()

        else:
            st.warning(
                "Delete this conversation permanently?"
            )

            confirm_column, cancel_column = (
                st.columns(
                    2,
                    gap="small",
                )
            )

            with confirm_column:
                if st.button(
                    "Delete",
                    key=f"confirm_delete_{chat_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    try:
                        chat_service.delete_chat(
                            chat_id
                        )

                        if (
                            st.session_state.current_chat_id
                            == chat_id
                        ):
                            st.session_state.current_chat_id = (
                                None
                            )

                            st.session_state.messages = []

                        st.session_state.menu_chat_id = (
                            None
                        )

                        st.session_state.pending_delete_chat_id = (
                            None
                        )

                        st.toast(
                            "Conversation deleted"
                        )

                        st.rerun()

                    except ChatStorageError as exc:
                        st.error(str(exc))

            with cancel_column:
                if st.button(
                    "Cancel",
                    key=f"cancel_delete_{chat_id}",
                    use_container_width=True,
                ):
                    st.session_state.pending_delete_chat_id = (
                        None
                    )

                    st.rerun()

        if st.button(
            "Close",
            key=f"close_chat_menu_{chat_id}",
            use_container_width=True,
        ):
            st.session_state.menu_chat_id = None
            st.session_state.pending_delete_chat_id = (
                None
            )

            st.rerun()


def render_conversation_sidebar(
    chat_service: ChatService,
) -> None:
    with st.sidebar:
        render_section_label(
            "Conversations"
        )

        search_query = st.text_input(
            "Search conversations",
            key="chat_search",
            placeholder="Search chats...",
            label_visibility="collapsed",
        )

        try:
            chats = chat_service.search_chats(
                search_query
            )

        except ChatStorageError as exc:
            st.error(str(exc))
            chats = []

        pinned_chats = [
            chat
            for chat in chats
            if chat.get("pinned", False)
        ]

        recent_chats = [
            chat
            for chat in chats
            if not chat.get("pinned", False)
        ]

        if pinned_chats:
            st.markdown(
                """
                <div class="tc-section-label">
                    Pinned
                </div>
                """,
                unsafe_allow_html=True,
            )

            for chat in pinned_chats:
                render_chat_item(
                    chat_service,
                    chat,
                )

        if recent_chats:
            st.markdown(
                """
                <div class="tc-section-label">
                    Recent
                </div>
                """,
                unsafe_allow_html=True,
            )

            for chat in recent_chats:
                render_chat_item(
                    chat_service,
                    chat,
                )

        if not chats:
            if search_query:
                st.caption(
                    "No conversations match your search."
                )
            else:
                st.caption(
                    "No saved conversations yet."
                )

        render_chat_manager(
            chat_service
        )
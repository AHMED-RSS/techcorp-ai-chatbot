from __future__ import annotations

from typing import Any

import streamlit as st

from agents.composer import (
    ComposerAttachment,
    ComposerSubmission,
)
from core.exceptions import (
    FileProcessingError,
)
from services.file_service import (
    FileService,
)
from services.rag_service import (
    RAGService,
)


SUPPORTED_FILE_TYPES = [
    "txt",
    "md",
    "rst",
    "log",
    "py",
    "js",
    "ts",
    "tsx",
    "jsx",
    "java",
    "c",
    "cpp",
    "h",
    "hpp",
    "cs",
    "go",
    "rs",
    "html",
    "css",
    "scss",
    "json",
    "xml",
    "yaml",
    "yml",
    "toml",
    "ini",
    "cfg",
    "csv",
    "pdf",
    "docx",
    "xlsx",
    "pptx",
    "zip",
    "png",
    "jpg",
    "jpeg",
    "webp",
]


REASONING_LABELS = {
    "normal": "Normal",
    "focused": "Focused",
    "deep": "Deep Think",
}


def _process_one_file(
    file_service: FileService,
    uploaded_file: Any,
) -> dict[str, Any]:
    """
    Process one uploaded file using the available FileService API.
    """

    candidate_methods = (
        "process_uploaded_file",
        "process_file",
        "process",
    )

    for method_name in candidate_methods:
        method = getattr(
            file_service,
            method_name,
            None,
        )

        if not callable(method):
            continue

        result = method(
            uploaded_file
        )

        if isinstance(
            result,
            dict,
        ):
            return result

        to_dict = getattr(
            result,
            "to_dict",
            None,
        )

        if callable(to_dict):
            converted = to_dict()

            if isinstance(
                converted,
                dict,
            ):
                return converted

        raise FileProcessingError(
            "The file service returned an unsupported result."
        )

    multiple_method = getattr(
        file_service,
        "process_uploaded_files",
        None,
    )

    if callable(multiple_method):
        results = multiple_method(
            [uploaded_file]
        )

        if results:
            result = results[0]

            if isinstance(
                result,
                dict,
            ):
                return result

            to_dict = getattr(
                result,
                "to_dict",
                None,
            )

            if callable(to_dict):
                converted = to_dict()

                if isinstance(
                    converted,
                    dict,
                ):
                    return converted

    raise FileProcessingError(
        "No compatible file-processing method is available."
    )


def process_composer_attachments(
    *,
    uploaded_files: list[Any],
    file_service: FileService,
    rag_service: RAGService,
) -> list[ComposerAttachment]:
    """
    Save, parse and index composer attachments locally.
    """

    attachments: list[ComposerAttachment] = []

    for uploaded_file in uploaded_files:
        attachment = ComposerAttachment(
            name=str(
                getattr(
                    uploaded_file,
                    "name",
                    "attachment",
                )
            ),
            size_bytes=int(
                getattr(
                    uploaded_file,
                    "size",
                    0,
                )
                or 0
            ),
            mime_type=str(
                getattr(
                    uploaded_file,
                    "type",
                    "application/octet-stream",
                )
                or "application/octet-stream"
            ),
        )

        try:
            document = _process_one_file(
                file_service,
                uploaded_file,
            )

            document_id = str(
                document.get(
                    "id",
                    "Search local documents",
                )
            ).strip()

            attachment.document_id = (
                document_id
                or None
            )

            attachment.title = str(
                document.get(
                    "title"
                )
                or document.get(
                    "original_name"
                )
                or attachment.name
            )

            attachment.stored_path = (
                str(
                    document.get(
                        "stored_path",
                        "Search local documents",
                    )
                ).strip()
                or None
            )

            if document_id:
                indexed_result = (
                    rag_service.index_document(
                        document
                    )
                )

                try:
                    attachment.indexed_chunks = int(
                        indexed_result
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    attachment.indexed_chunks = 0

                active_ids = list(
                    st.session_state.get(
                        "active_document_ids",
                        [],
                    )
                )

                if document_id not in active_ids:
                    active_ids.append(
                        document_id
                    )

                st.session_state.active_document_ids = (
                    active_ids
                )

        except Exception as exc:
            attachment.error = str(
                exc
            )

        attachments.append(
            attachment
        )

    return attachments


def _pending_attachments(
) -> list[dict[str, Any]]:
    return [
        item
        for item in st.session_state.get(
            "pending_attachments",
            [],
        )
        if isinstance(
            item,
            dict,
        )
    ]


def _render_attachment_list() -> None:
    attachments = _pending_attachments()

    if not attachments:
        return

    st.markdown(
        "#### Attached files"
    )

    for attachment in attachments:
        name = str(
            attachment.get(
                "name",
                "attachment",
            )
        )

        error = attachment.get(
            "error"
        )

        with st.container():
            if error:
                st.error(
                    f"{name}: {error}"
                )

            else:
                columns = st.columns(
                    [5, 1],
                    gap="small",
                )

                with columns[0]:
                    st.markdown(
                        f"**{name}**"
                    )

                    st.caption(
                        "Indexed chunks: "
                        f"{attachment.get('indexed_chunks', 0)}"
                    )

                with columns[1]:
                    document_id = attachment.get(
                        "document_id"
                    )

                    if st.button(
                        "Remove",
                        key=(
                            "remove_composer_attachment_"
                            f"{document_id or name}"
                        ),
                        use_container_width=True,
                    ):
                        remaining = [
                            item
                            for item in attachments
                            if item is not attachment
                        ]

                        st.session_state.pending_attachments = (
                            remaining
                        )

                        st.rerun()

def _render_add_prompt_menu(
    *,
    file_service: FileService,
    rag_service: RAGService,
    disabled: bool,
) -> None:
    """
    Render all composer options inside the single plus menu.
    """

    with st.popover(
        "+",
        disabled=disabled,
        use_container_width=False,
    ):
        st.markdown(
            "### Add to prompt"
        )

        st.caption(
            "Files and processing options remain local, "
            "except when Web search is enabled."
        )

        uploaded_files = st.file_uploader(
            "Files",
            type=SUPPORTED_FILE_TYPES,
            accept_multiple_files=True,
            key="composer_menu_files",
            disabled=disabled,
        )

        if uploaded_files:
            if st.button(
                "Add selected files",
                key="composer_menu_add_files",
                type="primary",
                use_container_width=True,
                disabled=disabled,
            ):
                processed = (
                    process_composer_attachments(
                        uploaded_files=list(
                            uploaded_files
                        ),
                        file_service=file_service,
                        rag_service=rag_service,
                    )
                )

                attachments = (
                    _pending_attachments()
                )

                attachments.extend(
                    attachment.to_dict()
                    for attachment in processed
                )

                st.session_state.pending_attachments = (
                    attachments
                )

                st.toast(
                    f"Added {len(processed)} file(s)"
                )

                st.rerun()

        st.divider()

        available_modes = [
            "normal",
            "focused",
            "deep",
        ]

        current_mode = str(
            st.session_state.get(
                "reasoning_mode",
                "normal",
            )
        )

        if current_mode not in available_modes:
            current_mode = "normal"

        selected_mode = st.selectbox(
            "Reasoning mode",
            options=available_modes,
            index=available_modes.index(
                current_mode
            ),
            format_func=lambda mode: (
                REASONING_LABELS[mode]
            ),
            key="composer_menu_reasoning",
            disabled=disabled,
        )

        st.session_state.reasoning_mode = (
            selected_mode
        )

        web_enabled = st.toggle(
            "Search the web",
            value=bool(
                st.session_state.get(
                    "web_search_enabled",
                    False,
                )
            ),
            key="composer_menu_web",
            disabled=disabled,
            help=(
                "Retrieve current search results through DDGS. "
                "The answer is still generated by local Ollama."
            ),
        )

        st.session_state.web_search_enabled = (
            web_enabled
        )

        document_enabled = st.toggle(
            "Search local documents",
            value=bool(
                st.session_state.get(
                    "document_search_enabled",
                    True,
                )
            ),
            key="composer_menu_documents",
            disabled=disabled,
            help=(
                "Search selected local documents using "
                "Ollama embeddings and ChromaDB."
            ),
        )

        st.session_state.document_search_enabled = (
            document_enabled
        )

        attachments = _pending_attachments()

        if attachments:
            st.divider()

            _render_attachment_list()

            if st.button(
                "Clear all attachments",
                key="composer_menu_clear_all",
                use_container_width=True,
                disabled=disabled,
            ):
                st.session_state.pending_attachments = []

                st.rerun()


def render_prompt_composer(
    *,
    file_service: FileService,
    rag_service: RAGService,
    disabled: bool = False,
) -> ComposerSubmission | None:
    """
    Render a ChatGPT-style prompt bar.

    The plus button is visually positioned inside the input bar.
    All additional options are contained within that plus menu.
    """

    with st.container(
        key="tc_prompt_composer"
    ):
        attachments_count = len(
            _pending_attachments()
        )

        reasoning_mode = str(
            st.session_state.get(
                "reasoning_mode",
                "normal",
            )
        )

        st.caption(
            "Attachments: "
            f"{attachments_count} | "
            "Reasoning: "
            f"{reasoning_mode.title()}"
        )

        _render_add_prompt_menu(
            file_service=file_service,
            rag_service=rag_service,
            disabled=disabled,
        )

        submitted_prompt = st.chat_input(
            "Ask anything...",
            key="advanced_chat_input",
            disabled=disabled,
            accept_file=False,
        )

    prompt = str(
        submitted_prompt
        or ""
    ).strip()

    if not prompt:
        return None

    attachments = (
        _pending_attachments()
    )

    submission = ComposerSubmission(
        prompt=prompt,
        reasoning_mode=str(
            st.session_state.get(
                "reasoning_mode",
                "normal",
            )
        ),
        web_search_enabled=bool(
            st.session_state.get(
                "web_search_enabled",
                False,
            )
        ),
        document_search_enabled=bool(
            st.session_state.get(
                "document_search_enabled",
                True,
            )
        ),
        attachments=attachments,
    )

    st.session_state.pending_attachments = []

    return submission

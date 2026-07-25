from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from core.exceptions import (
    FileProcessingError,
    OllamaConnectionError,
    OllamaModelError,
)
from services.file_service import (
    FileService,
)
from services.rag_service import (
    RAGService,
)
from ui.components import (
    render_section_label,
)


CATEGORY_ICONS = {
    "document": "📄",
    "text": "📝",
    "data": "📊",
    "code": "💻",
    "presentation": "📽️",
    "image": "🖼️",
    "archive": "🗜️",
    "unknown": "📎",
}


def initialise_document_state(
    file_service: FileService,
    rag_service: RAGService,
) -> None:
    documents = (
        file_service.list_documents()
    )

    st.session_state.document_count = (
        len(documents)
    )

    st.session_state.rag_chunk_count = (
        rag_service.count_chunks()
    )

    existing_ids = {
        str(document["id"])
        for document in documents
        if document.get("id")
    }

    st.session_state.active_document_ids = [
        document_id
        for document_id in (
            st.session_state
            .active_document_ids
        )
        if document_id in existing_ids
    ]


def process_sidebar_uploads(
    file_service: FileService,
    rag_service: RAGService,
    uploaded_files: list[Any],
) -> None:
    if not uploaded_files:
        return

    upload_signature = tuple(
        (
            uploaded_file.name,
            getattr(
                uploaded_file,
                "size",
                None,
            ),
        )
        for uploaded_file in uploaded_files
    )

    if (
        st.session_state.get(
            "last_upload_signature"
        )
        == upload_signature
    ):
        return

    st.session_state.rag_indexing = True
    processed: list[dict[str, Any]] = []
    errors: list[str] = []
    index_warnings: list[str] = []

    try:
        with st.spinner(
            "Reading and indexing files locally..."
        ):
            processed, errors = (
                file_service
                .process_uploaded_files(
                    uploaded_files
                )
            )

            for record in processed:
                try:
                    index_result = (
                        rag_service
                        .index_document(
                            record
                        )
                    )

                    if not index_result[
                        "indexed"
                    ]:
                        index_warnings.append(
                            f"{record['original_name']}: "
                            f"{index_result['reason']}"
                        )

                except (
                    OllamaConnectionError,
                    OllamaModelError,
                    FileProcessingError,
                ) as exc:
                    index_warnings.append(
                        f"{record['original_name']}: "
                        f"{exc}"
                    )

    finally:
        st.session_state.rag_indexing = (
            False
        )

    st.session_state.last_upload_signature = (
        upload_signature
    )

    if processed:
        new_ids = [
            str(record["id"])
            for record in processed
        ]

        active_ids = list(
            st.session_state
            .active_document_ids
        )

        for document_id in new_ids:
            if document_id not in active_ids:
                active_ids.append(
                    document_id
                )

        st.session_state.active_document_ids = (
            active_ids
        )

        st.session_state.last_processed_files = (
            processed
        )

        st.session_state.document_count = len(
            file_service.list_documents()
        )

        st.session_state.rag_chunk_count = (
            rag_service.count_chunks()
        )

        st.toast(
            f"{len(processed)} file(s) processed"
        )

    for error in errors:
        st.error(error)

    for warning in index_warnings:
        st.warning(warning)


def render_document_item(
    file_service: FileService,
    rag_service: RAGService,
    document: dict[str, Any],
) -> None:
    document_id = str(
        document["id"]
    )

    category = str(
        document.get(
            "category",
            "unknown",
        )
    )

    icon = CATEGORY_ICONS.get(
        category,
        "📎",
    )

    title = str(
        document.get(
            "title",
            document.get(
                "original_name",
                "Untitled",
            ),
        )
    )

    active = (
        document_id
        in st.session_state
        .active_document_ids
    )

    columns = st.columns(
        [0.8, 4.2, 0.8],
        gap="small",
    )

    with columns[0]:
        selected = st.checkbox(
            "Use document",
            value=active,
            key=(
                f"document_active_"
                f"{document_id}"
            ),
            label_visibility="collapsed",
        )

        active_ids = list(
            st.session_state
            .active_document_ids
        )

        if (
            selected
            and document_id
            not in active_ids
        ):
            active_ids.append(
                document_id
            )

            st.session_state.active_document_ids = (
                active_ids
            )

        elif (
            not selected
            and document_id
            in active_ids
        ):
            st.session_state.active_document_ids = [
                item
                for item in active_ids
                if item != document_id
            ]

    with columns[1]:
        st.markdown(
            f"**{icon} {escape(title)}**",
            unsafe_allow_html=True,
        )

        st.caption(
            f"{category.title()} · "
            f"{document.get('character_count', 0):,} "
            "characters"
        )

    with columns[2]:
        if st.button(
            "×",
            key=(
                f"delete_document_"
                f"{document_id}"
            ),
            help="Delete local file",
            use_container_width=True,
        ):
            try:
                rag_service.delete_document(
                    document_id
                )

                file_service.delete_document(
                    document_id
                )

                st.session_state.active_document_ids = [
                    item
                    for item in (
                        st.session_state
                        .active_document_ids
                    )
                    if item != document_id
                ]

                st.session_state.document_count = len(
                    file_service.list_documents()
                )

                st.session_state.rag_chunk_count = (
                    rag_service.count_chunks()
                )

                st.toast(
                    "Document deleted"
                )

                st.rerun()

            except (
                FileProcessingError,
                OllamaConnectionError,
                OllamaModelError,
            ) as exc:
                st.error(str(exc))

    warnings = document.get(
        "warnings",
        [],
    )

    if warnings:
        with st.expander(
            "File warnings",
            expanded=False,
        ):
            for warning in warnings:
                st.warning(warning)


def render_file_sidebar(
    file_service: FileService,
    rag_service: RAGService,
) -> None:
    with st.sidebar:
        render_section_label(
            "Local knowledge"
        )

        uploaded_files = st.file_uploader(
            "Add local files",
            accept_multiple_files=True,
            type=None,
            key="sidebar_file_uploader",
            help=(
                "Files and embeddings are stored "
                "locally on this computer."
            ),
            label_visibility="collapsed",
        )

        process_sidebar_uploads(
            file_service=file_service,
            rag_service=rag_service,
            uploaded_files=list(
                uploaded_files or []
            ),
        )

        documents = (
            file_service.list_documents()
        )

        st.session_state.document_count = (
            len(documents)
        )

        st.session_state.rag_chunk_count = (
            rag_service.count_chunks()
        )

        status_columns = st.columns(
            2,
            gap="small",
        )

        with status_columns[0]:
            st.caption(
                f"Files: "
                f"{len(documents)}"
            )

        with status_columns[1]:
            st.caption(
                "Chunks: "
                f"{st.session_state.rag_chunk_count}"
            )

        if not documents:
            st.caption(
                "No local files added."
            )

            return

        st.caption(
            f"{len(st.session_state.active_document_ids)} "
            f"of {len(documents)} selected"
        )

        with st.expander(
            "Manage files",
            expanded=False,
        ):
            for document in documents:
                render_document_item(
                    file_service=file_service,
                    rag_service=rag_service,
                    document=document,
                )

        if st.button(
            "↻ Rebuild document index",
            key="rebuild_rag_index_button",
            use_container_width=True,
            disabled=(
                st.session_state.rag_indexing
            ),
        ):
            st.session_state.rag_indexing = True

            try:
                with st.spinner(
                    "Rebuilding the local "
                    "semantic index..."
                ):
                    result = (
                        rag_service
                        .reindex_documents(
                            documents
                        )
                    )

                st.session_state.rag_reindex_result = (
                    result
                )

                st.session_state.rag_chunk_count = (
                    rag_service.count_chunks()
                )

                if result[
                    "failed_documents"
                ]:
                    st.warning(
                        "The index was rebuilt with "
                        "some file errors."
                    )

                else:
                    st.toast(
                        "Document index rebuilt"
                    )

            finally:
                st.session_state.rag_indexing = (
                    False
                )

            st.rerun()

        reindex_result = (
            st.session_state.get(
                "rag_reindex_result"
            )
        )

        if reindex_result:
            with st.expander(
                "Last indexing result",
                expanded=False,
            ):
                st.write(
                    "Indexed documents:",
                    reindex_result.get(
                        "indexed_documents",
                        0,
                    ),
                )

                st.write(
                    "Skipped documents:",
                    reindex_result.get(
                        "skipped_documents",
                        0,
                    ),
                )

                st.write(
                    "Total chunks:",
                    reindex_result.get(
                        "total_chunks",
                        0,
                    ),
                )

                failures = (
                    reindex_result.get(
                        "failed_documents",
                        [],
                    )
                )

                for failure in failures:
                    st.error(failure)


def render_active_documents(
    file_service: FileService,
) -> None:
    active_ids = (
        st.session_state
        .active_document_ids
    )

    if not active_ids:
        return

    documents = file_service.get_documents(
        active_ids
    )

    with st.expander(
        f"Selected local files "
        f"({len(documents)})",
        expanded=False,
    ):
        for document in documents:
            category = document.get(
                "category",
                "unknown",
            )

            icon = CATEGORY_ICONS.get(
                category,
                "📎",
            )

            st.markdown(
                f"**{icon} "
                f"{document.get('title', 'Untitled')}**"
            )

            st.caption(
                f"{document.get('original_name')} · "
                f"{document.get('character_count', 0):,} "
                "characters"
            )
from __future__ import annotations

import json
import re

import streamlit as st

from agents.study import StudySession
from core.exceptions import StudyError
from services.file_service import FileService
from services.study_service import StudyService


STUDY_TYPE_ICONS = {
    "summary": "📝",
    "notes": "📚",
    "flashcards": "🎴",
    "quiz": "❓",
}


def _safe_filename(
    value: str,
) -> str:
    cleaned = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        str(
            value or "study_session"
        ),
    ).strip("_")

    return (
        cleaned[:80]
        or "study_session"
    )


def render_study_sources(
    session: StudySession,
) -> None:
    if not session.sources:
        return

    with st.expander(
        f"Retrieved sources ({len(session.sources)})",
        expanded=False,
    ):
        for index, source in enumerate(
            session.sources,
            start=1,
        ):
            st.markdown(
                f"**{index}. "
                f"{source.get('document_title', 'Untitled')}**"
            )

            score = source.get(
                "relevance_score"
            )

            score_text = (
                f"{float(score):.0%}"
                if score is not None
                else "Unknown"
            )

            st.caption(
                f"{source.get('original_name', '')} · "
                f"Relevance {score_text}"
            )

            text = str(
                source.get(
                    "text",
                    "",
                )
            )

            st.write(
                text[:800]
                + (
                    "…"
                    if len(text) > 800
                    else ""
                )
            )


def render_study_downloads(
    study_service: StudyService,
    session: StudySession,
) -> None:
    filename = _safe_filename(
        session.title
    )

    markdown_data = (
        study_service.export_markdown(
            session
        )
    )

    json_data = json.dumps(
        session.to_dict(),
        ensure_ascii=False,
        indent=2,
    )

    columns = st.columns(
        2,
        gap="small",
    )

    with columns[0]:
        st.download_button(
            "Download Markdown",
            data=markdown_data,
            file_name=(
                f"{filename}.md"
            ),
            mime="text/markdown",
            use_container_width=True,
            key=(
                f"download_study_markdown_"
                f"{session.id}"
            ),
        )

    with columns[1]:
        st.download_button(
            "Download JSON",
            data=json_data,
            file_name=(
                f"{filename}.json"
            ),
            mime="application/json",
            use_container_width=True,
            key=(
                f"download_study_json_"
                f"{session.id}"
            ),
        )


def render_flashcards(
    session: StudySession,
) -> None:
    if not session.flashcards:
        st.info(
            "This session does not contain flashcards."
        )
        return

    reveal_state = dict(
        st.session_state.get(
            "study_flashcard_revealed",
            {},
        )
    )

    current_index = int(
        st.session_state.get(
            "study_flashcard_index",
            0,
        )
    )

    current_index = max(
        0,
        min(
            len(session.flashcards) - 1,
            current_index,
        ),
    )

    card = session.flashcards[
        current_index
    ]

    st.caption(
        f"Card {current_index + 1} "
        f"of {len(session.flashcards)}"
    )

    with st.container(
        border=True
    ):
        st.markdown(
            "### Front"
        )

        st.markdown(
            card.front
        )

        revealed = bool(
            reveal_state.get(
                card.id,
                False,
            )
        )

        if revealed:
            st.divider()

            st.markdown(
                "### Back"
            )

            st.markdown(
                card.back
            )

            if card.source_labels:
                st.caption(
                    "Sources: "
                    + ", ".join(
                        card.source_labels
                    )
                )

        else:
            if st.button(
                "Reveal answer",
                key=(
                    f"reveal_flashcard_"
                    f"{session.id}_"
                    f"{card.id}"
                ),
                type="primary",
                use_container_width=True,
            ):
                reveal_state[
                    card.id
                ] = True

                st.session_state.study_flashcard_revealed = (
                    reveal_state
                )

                st.rerun()

    navigation_columns = st.columns(
        3,
        gap="small",
    )

    with navigation_columns[0]:
        if st.button(
            "Previous",
            key=(
                f"previous_flashcard_"
                f"{session.id}"
            ),
            disabled=(
                current_index <= 0
            ),
            use_container_width=True,
        ):
            st.session_state.study_flashcard_index = (
                current_index - 1
            )

            st.rerun()

    with navigation_columns[1]:
        if st.button(
            "Hide answer",
            key=(
                f"hide_flashcard_"
                f"{session.id}"
            ),
            disabled=(
                not revealed
            ),
            use_container_width=True,
        ):
            reveal_state[
                card.id
            ] = False

            st.session_state.study_flashcard_revealed = (
                reveal_state
            )

            st.rerun()

    with navigation_columns[2]:
        if st.button(
            "Next",
            key=(
                f"next_flashcard_"
                f"{session.id}"
            ),
            disabled=(
                current_index
                >= len(session.flashcards) - 1
            ),
            use_container_width=True,
        ):
            st.session_state.study_flashcard_index = (
                current_index + 1
            )

            st.rerun()


def render_quiz(
    session: StudySession,
) -> None:
    if not session.quiz_questions:
        st.info(
            "This session does not contain quiz questions."
        )
        return

    answers = dict(
        st.session_state.get(
            "study_quiz_answers",
            {},
        )
    )

    submitted = bool(
        st.session_state.get(
            "study_quiz_submitted",
            False,
        )
    )

    for index, question in enumerate(
        session.quiz_questions,
        start=1,
    ):
        with st.container(
            border=True
        ):
            st.markdown(
                f"### {index}. {question.question}"
            )

            answer_key = (
                f"{session.id}:"
                f"{question.id}"
            )

            previous_answer = answers.get(
                answer_key
            )

            option_indices = list(
                range(
                    len(question.options)
                )
            )

            selected_index = (
                option_indices.index(
                    previous_answer
                )
                if previous_answer
                in option_indices
                else None
            )

            chosen = st.radio(
                "Choose one answer",
                options=option_indices,
                index=selected_index,
                format_func=(
                    lambda option_index: (
                        f"{chr(65 + option_index)}. "
                        f"{question.options[option_index]}"
                    )
                ),
                key=(
                    f"quiz_answer_"
                    f"{session.id}_"
                    f"{question.id}"
                ),
                disabled=submitted,
                label_visibility="collapsed",
            )

            if chosen is not None:
                answers[
                    answer_key
                ] = chosen

            if submitted:
                chosen_answer = answers.get(
                    answer_key
                )

                if (
                    chosen_answer
                    == question.correct_index
                ):
                    st.success(
                        "Correct"
                    )

                else:
                    correct_label = chr(
                        65
                        + question.correct_index
                    )

                    st.error(
                        "Incorrect. "
                        f"The correct answer is "
                        f"{correct_label}."
                    )

                if question.explanation:
                    st.write(
                        question.explanation
                    )

                if question.source_labels:
                    st.caption(
                        "Sources: "
                        + ", ".join(
                            question.source_labels
                        )
                    )

    st.session_state.study_quiz_answers = (
        answers
    )

    if not submitted:
        answered_count = sum(
            1
            for question in session.quiz_questions
            if (
                f"{session.id}:{question.id}"
                in answers
            )
        )

        st.caption(
            f"Answered {answered_count} "
            f"of {len(session.quiz_questions)}"
        )

        if st.button(
            "Submit quiz",
            key=(
                f"submit_quiz_"
                f"{session.id}"
            ),
            type="primary",
            use_container_width=True,
            disabled=(
                answered_count
                < len(session.quiz_questions)
            ),
        ):
            st.session_state.study_quiz_submitted = (
                True
            )

            st.rerun()

    else:
        score = sum(
            1
            for question in session.quiz_questions
            if (
                answers.get(
                    f"{session.id}:{question.id}"
                )
                == question.correct_index
            )
        )

        total = len(
            session.quiz_questions
        )

        percentage = (
            score / total
            if total
            else 0.0
        )

        st.metric(
            "Quiz score",
            f"{score}/{total}",
            f"{percentage:.0%}",
        )

        if st.button(
            "Retake quiz",
            key=(
                f"retake_quiz_"
                f"{session.id}"
            ),
            use_container_width=True,
        ):
            st.session_state.study_quiz_answers = {}
            st.session_state.study_quiz_submitted = (
                False
            )

            st.rerun()


def render_study_session(
    study_service: StudyService,
    session: StudySession,
) -> None:
    icon = STUDY_TYPE_ICONS.get(
        session.study_type,
        "📚",
    )

    st.markdown(
        f"## {icon} {session.title}"
    )

    st.caption(
        f"{session.study_type.title()} · "
        f"{len(session.document_titles)} document(s) · "
        f"{session.created_at}"
    )

    if session.document_titles:
        with st.expander(
            "Source documents",
            expanded=False,
        ):
            for title in (
                session.document_titles
            ):
                st.markdown(
                    f"- {title}"
                )

    if session.content:
        st.markdown(
            session.content
        )

    if session.study_type == "flashcards":
        render_flashcards(
            session
        )

    elif session.study_type == "quiz":
        render_quiz(
            session
        )

    render_study_sources(
        session
    )

    st.divider()

    render_study_downloads(
        study_service,
        session,
    )


def render_generation_controls(
    *,
    study_service: StudyService,
    file_service: FileService,
    model: str,
) -> None:
    active_document_ids = list(
        st.session_state
        .active_document_ids
    )

    active_documents = (
        file_service.get_documents(
            active_document_ids
        )
    )

    if not active_documents:
        st.info(
            "Upload and select at least one local "
            "document from the sidebar."
        )
        return

    st.success(
        f"{len(active_documents)} selected document(s)"
    )

    with st.expander(
        "Selected documents",
        expanded=False,
    ):
        for document in active_documents:
            st.markdown(
                "- "
                + str(
                    document.get(
                        "title"
                    )
                    or document.get(
                        "original_name"
                    )
                    or "Untitled document"
                )
            )

    material_type = st.selectbox(
        "Study material",
        options=[
            "summary",
            "notes",
            "flashcards",
            "quiz",
        ],
        format_func=lambda value: {
            "summary": "📝 Summary",
            "notes": "📚 Revision notes",
            "flashcards": "🎴 Flashcards",
            "quiz": "❓ Quiz",
        }[value],
        key="study_generation_type",
    )

    with st.form(
        "study_generation_form"
    ):
        instruction = st.text_area(
            "Focus or instruction",
            value=str(
                st.session_state.get(
                    "study_instruction",
                    "",
                )
            ),
            placeholder=(
                "Example: Focus on the main risks, "
                "recommendations and conclusions."
            ),
            height=120,
        )

        count = 12
        detail_level = "balanced"
        note_style = "outline"

        if material_type == "summary":
            detail_level = st.select_slider(
                "Detail level",
                options=[
                    "concise",
                    "balanced",
                    "detailed",
                ],
                value="balanced",
            )

        elif material_type == "notes":
            note_style = st.selectbox(
                "Notes style",
                options=[
                    "outline",
                    "cornell",
                    "exam",
                ],
                format_func=lambda value: {
                    "outline": "Structured outline",
                    "cornell": "Cornell notes",
                    "exam": "Exam revision",
                }[value],
            )

        elif material_type == "flashcards":
            count = st.slider(
                "Number of flashcards",
                min_value=3,
                max_value=30,
                value=12,
            )

        elif material_type == "quiz":
            count = st.slider(
                "Number of questions",
                min_value=3,
                max_value=20,
                value=8,
            )

        submitted = st.form_submit_button(
            "Generate locally",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    st.session_state.study_generation_in_progress = (
        True
    )

    st.session_state.study_error = None
    st.session_state.study_instruction = (
        instruction
    )

    try:
        with st.status(
            "Generating local study material...",
            expanded=True,
        ) as status:
            if material_type == "summary":
                session = (
                    study_service.create_summary(
                        document_ids=(
                            active_document_ids
                        ),
                        instruction=instruction,
                        model=model,
                        detail_level=(
                            detail_level
                        ),
                    )
                )

            elif material_type == "notes":
                session = (
                    study_service.create_notes(
                        document_ids=(
                            active_document_ids
                        ),
                        instruction=instruction,
                        model=model,
                        note_style=(
                            note_style
                        ),
                    )
                )

            elif material_type == "flashcards":
                session = (
                    study_service
                    .create_flashcards(
                        document_ids=(
                            active_document_ids
                        ),
                        instruction=instruction,
                        model=model,
                        count=count,
                    )
                )

            else:
                session = (
                    study_service.create_quiz(
                        document_ids=(
                            active_document_ids
                        ),
                        instruction=instruction,
                        model=model,
                        count=count,
                    )
                )

            status.update(
                label=(
                    "Study material generated"
                ),
                state="complete",
            )

        st.session_state.current_study_session = (
            session.to_dict()
        )

        st.session_state.current_study_session_id = (
            session.id
        )

        history = list(
            st.session_state.study_history
        )

        history.append(
            session.to_dict()
        )

        st.session_state.study_history = (
            history[-50:]
        )

        st.session_state.study_flashcard_index = 0
        st.session_state.study_flashcard_revealed = {}
        st.session_state.study_quiz_answers = {}
        st.session_state.study_quiz_submitted = False

        st.toast(
            "Study session saved locally"
        )

        st.rerun()

    except StudyError as exc:
        st.session_state.study_error = str(
            exc
        )

        st.error(
            str(exc)
        )

    finally:
        st.session_state.study_generation_in_progress = (
            False
        )


def render_study_library(
    study_service: StudyService,
) -> None:
    sessions = study_service.list_sessions(
        limit=100
    )

    if not sessions:
        st.info(
            "No saved study sessions."
        )
        return

    filter_type = st.selectbox(
        "Filter",
        options=[
            "all",
            "summary",
            "notes",
            "flashcards",
            "quiz",
        ],
        format_func=lambda value: (
            value.title()
        ),
        key="study_library_filter",
    )

    visible_sessions = [
        session
        for session in sessions
        if (
            filter_type == "all"
            or session.study_type
            == filter_type
        )
    ]

    st.metric(
        "Saved sessions",
        len(
            visible_sessions
        ),
    )

    for session in visible_sessions:
        icon = STUDY_TYPE_ICONS.get(
            session.study_type,
            "📚",
        )

        with st.container(
            border=True
        ):
            columns = st.columns(
                [5, 1, 1],
                gap="small",
            )

            with columns[0]:
                st.markdown(
                    f"**{icon} "
                    f"{session.title}**"
                )

                st.caption(
                    f"{session.study_type.title()} · "
                    f"{len(session.document_titles)} "
                    f"document(s) · "
                    f"{session.created_at}"
                )

            with columns[1]:
                if st.button(
                    "Open",
                    key=(
                        f"open_study_session_"
                        f"{session.id}"
                    ),
                    use_container_width=True,
                ):
                    st.session_state.current_study_session = (
                        session.to_dict()
                    )

                    st.session_state.current_study_session_id = (
                        session.id
                    )

                    st.session_state.study_flashcard_index = 0
                    st.session_state.study_flashcard_revealed = {}
                    st.session_state.study_quiz_answers = {}
                    st.session_state.study_quiz_submitted = False

                    st.rerun()

            with columns[2]:
                if st.button(
                    "Delete",
                    key=(
                        f"delete_study_session_"
                        f"{session.id}"
                    ),
                    use_container_width=True,
                ):
                    try:
                        study_service.delete_session(
                            session.id
                        )

                        if (
                            st.session_state
                            .current_study_session_id
                            == session.id
                        ):
                            st.session_state.current_study_session = (
                                None
                            )

                            st.session_state.current_study_session_id = (
                                None
                            )

                        st.toast(
                            "Study session deleted"
                        )

                        st.rerun()

                    except StudyError as exc:
                        st.error(
                            str(exc)
                        )


def render_study_workspace(
    *,
    study_service: StudyService,
    file_service: FileService,
    model: str,
) -> None:
    st.markdown(
        "# Study workspace"
    )

    st.caption(
        "Generate grounded learning material from "
        "selected local documents."
    )

    if st.session_state.study_error:
        st.warning(
            st.session_state.study_error
        )

    generate_tab, current_tab, library_tab = (
        st.tabs(
            [
                "Generate",
                "Current session",
                "Library",
            ]
        )
    )

    with generate_tab:
        render_generation_controls(
            study_service=study_service,
            file_service=file_service,
            model=model,
        )

    with current_tab:
        current_data = (
            st.session_state
            .current_study_session
        )

        if not isinstance(
            current_data,
            dict,
        ):
            st.info(
                "Generate or open a study session."
            )

        else:
            from agents.study import (
                study_session_from_dict,
            )

            render_study_session(
                study_service,
                study_session_from_dict(
                    current_data
                ),
            )

    with library_tab:
        render_study_library(
            study_service
        )
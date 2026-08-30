from __future__ import annotations

import json
import os
import re
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.study import (
    Flashcard,
    QuizQuestion,
    StudySession,
    study_session_from_dict,
)
from config.settings import Settings
from core.exceptions import StudyError
from core.logging_config import get_logger
from core.providers import (
    AIProvider,
)
from services.file_service import FileService
from services.rag_service import (
    RAGService,
    SearchResult,
)


logger = get_logger(__name__)


FLASHCARD_SYSTEM_PROMPT = """
You create flashcards only from supplied local document sources.

Return exactly one JSON object:

{
  "title": "short set title",
  "flashcards": [
    {
      "front": "one clear question or prompt",
      "back": "one concise answer",
      "source_labels": ["Source 1"]
    }
  ]
}

Rules:

- Return only valid JSON.
- Do not use Markdown around the JSON.
- Use only facts supported by the supplied sources.
- Preserve the terminology used by the sources.
- Keep one main concept per flashcard.
- Do not create duplicate cards.
- Use source labels that appear in the supplied context.
- Do not add outside knowledge.
""".strip()


QUIZ_SYSTEM_PROMPT = """
You create a multiple-choice quiz only from supplied local document sources.

Return exactly one JSON object:

{
  "title": "short quiz title",
  "questions": [
    {
      "question": "question text",
      "options": [
        "option one",
        "option two",
        "option three",
        "option four"
      ],
      "correct_index": 0,
      "explanation": "why the answer is correct",
      "source_labels": ["Source 1"]
    }
  ]
}

Rules:

- Return only valid JSON.
- Do not use Markdown around the JSON.
- Use only facts supported by the supplied sources.
- Each question must have exactly four options.
- Exactly one option must be correct.
- correct_index is zero-based and must be 0, 1, 2 or 3.
- Avoid trick questions and ambiguous wording.
- Use source labels from the supplied context.
- Do not add outside knowledge.
""".strip()


class StudyService:
    """
    Generates and stores local study material from indexed documents.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        ai_provider: AIProvider,
        rag_service: RAGService,
        file_service: FileService,
    ) -> None:
        self.settings = settings
        self.ai = ai_provider
        self.rag = rag_service
        self.files = file_service

        self.study_folder = (
            settings.report_folder
            / "study"
        )

        self.study_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

    def create_summary(
        self,
        *,
        document_ids: list[str],
        instruction: str,
        model: str,
        detail_level: str = "balanced",
    ) -> StudySession:
        documents = self._require_documents(
            document_ids
        )

        query = (
            instruction.strip()
            or (
                "Summarise the most important ideas, "
                "arguments, findings and conclusions."
            )
        )

        results = self._retrieve_sources(
            query=query,
            document_ids=document_ids,
            top_k=12,
        )

        context = self._require_context(
            results
        )

        detail_instruction = {
            "concise": (
                "Keep the summary concise and focus only "
                "on the highest-priority points."
            ),
            "balanced": (
                "Provide a balanced structured summary "
                "with enough detail for revision."
            ),
            "detailed": (
                "Provide a detailed structured summary "
                "while avoiding unsupported additions."
            ),
        }.get(
            detail_level,
            "Provide a balanced structured summary.",
        )

        system_prompt = f"""
You are creating a study summary from selected local documents.

{detail_instruction}

Requirements:

- Use only the supplied local document sources.
- Preserve the sources' terminology and distinctions.
- Organise the result with useful headings.
- Include key concepts, arguments, evidence and conclusions.
- Clearly distinguish sources when they disagree.
- Cite source labels such as [Source 1].
- Do not add outside knowledge.
- State when a requested point is not supported by the sources.
""".strip()

        output = self.ai.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "LOCAL DOCUMENT SOURCES\n\n"
                        f"{context}"
                    ),
                },
                {
                    "role": "user",
                    "content": query,
                },
            ],
            model=model,
            temperature=0.1,
            system_prompt=system_prompt,
        ).strip()

        if not output:
            raise StudyError(
                "The local model returned an empty summary."
            )

        session = self._new_session(
            study_type="summary",
            title=self._default_title(
                "Summary",
                documents,
            ),
            instruction=query,
            documents=documents,
            model=model,
            content=output,
            sources=results,
            metadata={
                "detail_level": detail_level,
            },
        )

        return self.save_session(
            session
        )

    def create_notes(
        self,
        *,
        document_ids: list[str],
        instruction: str,
        model: str,
        note_style: str = "outline",
    ) -> StudySession:
        documents = self._require_documents(
            document_ids
        )

        query = (
            instruction.strip()
            or (
                "Create revision notes covering the "
                "important concepts in the selected documents."
            )
        )

        results = self._retrieve_sources(
            query=query,
            document_ids=document_ids,
            top_k=14,
        )

        context = self._require_context(
            results
        )

        style_instruction = {
            "outline": (
                "Use hierarchical headings and concise bullet points."
            ),
            "cornell": (
                "Use sections for cues or questions, notes and "
                "a final summary."
            ),
            "exam": (
                "Focus on definitions, distinctions, processes, "
                "evidence and likely assessment points."
            ),
        }.get(
            note_style,
            "Use hierarchical headings and concise bullet points.",
        )

        system_prompt = f"""
You are creating revision notes from selected local documents.

{style_instruction}

Requirements:

- Use only the supplied sources.
- Preserve source terminology.
- Explain relationships between concepts.
- Include definitions only when the sources support them.
- Cite source labels such as [Source 1].
- Do not silently correct or expand the source material.
- Mark unsupported requested information as unavailable.
""".strip()

        output = self.ai.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "LOCAL DOCUMENT SOURCES\n\n"
                        f"{context}"
                    ),
                },
                {
                    "role": "user",
                    "content": query,
                },
            ],
            model=model,
            temperature=0.1,
            system_prompt=system_prompt,
        ).strip()

        if not output:
            raise StudyError(
                "The local model returned empty revision notes."
            )

        session = self._new_session(
            study_type="notes",
            title=self._default_title(
                "Revision notes",
                documents,
            ),
            instruction=query,
            documents=documents,
            model=model,
            content=output,
            sources=results,
            metadata={
                "note_style": note_style,
            },
        )

        return self.save_session(
            session
        )

    def create_flashcards(
        self,
        *,
        document_ids: list[str],
        instruction: str,
        model: str,
        count: int = 12,
    ) -> StudySession:
        documents = self._require_documents(
            document_ids
        )

        count = max(
            3,
            min(
                50,
                int(count),
            ),
        )

        query = (
            instruction.strip()
            or (
                "Create flashcards covering the most "
                "important concepts."
            )
        )

        results = self._retrieve_sources(
            query=query,
            document_ids=document_ids,
            top_k=16,
        )

        context = self._require_context(
            results
        )

        response = self.ai.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "LOCAL DOCUMENT SOURCES\n\n"
                        f"{context}"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"{query}\n\n"
                        f"Create {count} flashcards."
                    ),
                },
            ],
            model=model,
            temperature=0.1,
            system_prompt=(
                FLASHCARD_SYSTEM_PROMPT
            ),
            response_format="json",
        )

        parsed = self._parse_json(
            response
        )

        raw_cards = parsed.get(
            "flashcards",
            [],
        )

        if not isinstance(
            raw_cards,
            list,
        ):
            raw_cards = []

        cards: list[Flashcard] = []

        for index, raw_card in enumerate(
            raw_cards[:count],
            start=1,
        ):
            if not isinstance(
                raw_card,
                dict,
            ):
                continue

            card = Flashcard(
                id=f"card_{index}",
                front=str(
                    raw_card.get(
                        "front",
                        "",
                    )
                ),
                back=str(
                    raw_card.get(
                        "back",
                        "",
                    )
                ),
                source_labels=(
                    raw_card.get(
                        "source_labels",
                        [],
                    )
                ),
            )

            if (
                card.front
                and card.back
            ):
                cards.append(
                    card
                )

        if not cards:
            raise StudyError(
                "The local model did not return valid flashcards."
            )

        title = str(
            parsed.get(
                "title",
                "",
            )
        ).strip()

        session = self._new_session(
            study_type="flashcards",
            title=(
                title
                or self._default_title(
                    "Flashcards",
                    documents,
                )
            ),
            instruction=query,
            documents=documents,
            model=model,
            flashcards=cards,
            sources=results,
            metadata={
                "requested_count": count,
                "generated_count": len(
                    cards
                ),
            },
        )

        return self.save_session(
            session
        )

    def create_quiz(
        self,
        *,
        document_ids: list[str],
        instruction: str,
        model: str,
        count: int = 8,
    ) -> StudySession:
        documents = self._require_documents(
            document_ids
        )

        count = max(
            3,
            min(
                30,
                int(count),
            ),
        )

        query = (
            instruction.strip()
            or (
                "Create a quiz covering the most important "
                "material in the selected documents."
            )
        )

        results = self._retrieve_sources(
            query=query,
            document_ids=document_ids,
            top_k=16,
        )

        context = self._require_context(
            results
        )

        response = self.ai.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "LOCAL DOCUMENT SOURCES\n\n"
                        f"{context}"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"{query}\n\n"
                        f"Create {count} questions."
                    ),
                },
            ],
            model=model,
            temperature=0.1,
            system_prompt=QUIZ_SYSTEM_PROMPT,
            response_format="json",
        )

        parsed = self._parse_json(
            response
        )

        raw_questions = parsed.get(
            "questions",
            [],
        )

        if not isinstance(
            raw_questions,
            list,
        ):
            raw_questions = []

        questions: list[QuizQuestion] = []

        for index, raw_question in enumerate(
            raw_questions[:count],
            start=1,
        ):
            if not isinstance(
                raw_question,
                dict,
            ):
                continue

            options = raw_question.get(
                "options",
                [],
            )

            if (
                not isinstance(
                    options,
                    list,
                )
                or len(options) != 4
            ):
                continue

            question = QuizQuestion(
                id=f"question_{index}",
                question=str(
                    raw_question.get(
                        "question",
                        "",
                    )
                ),
                options=options,
                correct_index=(
                    raw_question.get(
                        "correct_index",
                        0,
                    )
                ),
                explanation=str(
                    raw_question.get(
                        "explanation",
                        "",
                    )
                ),
                source_labels=(
                    raw_question.get(
                        "source_labels",
                        [],
                    )
                ),
            )

            if question.question:
                questions.append(
                    question
                )

        if not questions:
            raise StudyError(
                "The local model did not return a valid quiz."
            )

        title = str(
            parsed.get(
                "title",
                "",
            )
        ).strip()

        session = self._new_session(
            study_type="quiz",
            title=(
                title
                or self._default_title(
                    "Quiz",
                    documents,
                )
            ),
            instruction=query,
            documents=documents,
            model=model,
            quiz_questions=questions,
            sources=results,
            metadata={
                "requested_count": count,
                "generated_count": len(
                    questions
                ),
            },
        )

        return self.save_session(
            session
        )

    def save_session(
        self,
        session: StudySession,
    ) -> StudySession:
        session.updated_at = (
            self._utc_now()
        )

        if not session.created_at:
            session.created_at = (
                session.updated_at
            )

        path = self.session_path(
            session.id
        )

        temporary_path = path.with_suffix(
            ".json.tmp"
        )

        try:
            temporary_path.write_text(
                json.dumps(
                    session.to_dict(),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            os.replace(
                temporary_path,
                path,
            )

        except OSError as exc:
            raise StudyError(
                f"Could not save study session: {exc}"
            ) from exc

        return session

    def load_session(
        self,
        session_id: str,
    ) -> StudySession | None:
        path = self.session_path(
            session_id
        )

        if not path.exists():
            return None

        try:
            raw = json.loads(
                path.read_text(
                    encoding="utf-8",
                )
            )

        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise StudyError(
                f"Could not load study session: {exc}"
            ) from exc

        if not isinstance(
            raw,
            dict,
        ):
            raise StudyError(
                "Stored study session is invalid."
            )

        return study_session_from_dict(
            raw
        )

    def list_sessions(
        self,
        *,
        study_type: str | None = None,
        limit: int = 100,
    ) -> list[StudySession]:
        sessions: list[StudySession] = []

        for path in self.study_folder.glob(
            "*.json"
        ):
            try:
                raw = json.loads(
                    path.read_text(
                        encoding="utf-8",
                    )
                )

                if not isinstance(
                    raw,
                    dict,
                ):
                    continue

                session = (
                    study_session_from_dict(
                        raw
                    )
                )

            except Exception:
                logger.warning(
                    "Skipping invalid study session: %s",
                    path.name,
                )
                continue

            if (
                study_type
                and session.study_type
                != study_type
            ):
                continue

            sessions.append(
                session
            )

        sessions.sort(
            key=lambda session: (
                session.updated_at
            ),
            reverse=True,
        )

        return sessions[
            :max(
                1,
                limit,
            )
        ]

    def delete_session(
        self,
        session_id: str,
    ) -> bool:
        path = self.session_path(
            session_id
        )

        if not path.exists():
            return False

        try:
            path.unlink()

        except OSError as exc:
            raise StudyError(
                f"Could not delete study session: {exc}"
            ) from exc

        return True

    def export_markdown(
        self,
        session: StudySession,
    ) -> str:
        lines = [
            f"# {session.title}",
            "",
            f"Type: {session.study_type}",
            f"Created: {session.created_at}",
            f"Model: {session.model}",
            "",
            "## Source documents",
            "",
        ]

        for title in session.document_titles:
            lines.append(
                f"- {title}"
            )

        lines.extend(
            [
                "",
                "## Instruction",
                "",
                session.instruction,
                "",
            ]
        )

        if session.content:
            lines.extend(
                [
                    "## Study material",
                    "",
                    session.content,
                    "",
                ]
            )

        if session.flashcards:
            lines.extend(
                [
                    "## Flashcards",
                    "",
                ]
            )

            for index, card in enumerate(
                session.flashcards,
                start=1,
            ):
                lines.extend(
                    [
                        f"### Card {index}",
                        "",
                        f"**Front:** {card.front}",
                        "",
                        f"**Back:** {card.back}",
                        "",
                    ]
                )

                if card.source_labels:
                    lines.append(
                        "Sources: "
                        + ", ".join(
                            card.source_labels
                        )
                    )
                    lines.append("")

        if session.quiz_questions:
            lines.extend(
                [
                    "## Quiz",
                    "",
                ]
            )

            for index, question in enumerate(
                session.quiz_questions,
                start=1,
            ):
                lines.append(
                    f"### Question {index}"
                )
                lines.append("")
                lines.append(
                    question.question
                )
                lines.append("")

                for option_index, option in enumerate(
                    question.options,
                ):
                    label = chr(
                        65 + option_index
                    )

                    lines.append(
                        f"- {label}. {option}"
                    )

                lines.extend(
                    [
                        "",
                        (
                            "**Correct answer:** "
                            f"{chr(65 + question.correct_index)}"
                        ),
                        "",
                        (
                            "**Explanation:** "
                            f"{question.explanation}"
                        ),
                        "",
                    ]
                )

        return "\n".join(
            lines
        ).strip() + "\n"

    def session_path(
        self,
        session_id: str,
    ) -> Path:
        safe_id = re.sub(
            r"[^a-zA-Z0-9_-]",
            "",
            str(
                session_id or ""
            ),
        )

        if not safe_id:
            raise StudyError(
                "Invalid study session identifier."
            )

        return (
            self.study_folder
            / f"{safe_id}.json"
        )

    def _require_documents(
        self,
        document_ids: list[str],
    ) -> list[dict[str, Any]]:
        cleaned_ids = [
            str(document_id).strip()
            for document_id in document_ids
            if str(document_id).strip()
        ]

        if not cleaned_ids:
            raise StudyError(
                "Select at least one local document first."
            )

        documents = self.files.get_documents(
            cleaned_ids
        )

        if not documents:
            raise StudyError(
                "The selected documents could not be loaded."
            )

        return documents

    def _retrieve_sources(
        self,
        *,
        query: str,
        document_ids: list[str],
        top_k: int,
    ) -> list[SearchResult]:
        results = self.rag.search(
            query=query,
            document_ids=document_ids,
            top_k=top_k,
        )

        if not results:
            raise StudyError(
                "No relevant indexed passages were found. "
                "Rebuild the document index and try again."
            )

        return results

    def _require_context(
        self,
        results: list[SearchResult],
    ) -> str:
        context = self.rag.build_context(
            results,
            maximum_characters=28_000,
        )

        if not context.strip():
            raise StudyError(
                "The retrieved documents did not contain usable text."
            )

        return context

    def _new_session(
        self,
        *,
        study_type: str,
        title: str,
        instruction: str,
        documents: list[dict[str, Any]],
        model: str,
        content: str = "",
        flashcards: list[Flashcard] | None = None,
        quiz_questions: list[QuizQuestion] | None = None,
        sources: list[SearchResult] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StudySession:
        timestamp = self._utc_now()

        return StudySession(
            id=str(
                uuid.uuid4()
            ),
            study_type=study_type,
            title=title,
            instruction=instruction,
            document_ids=[
                str(
                    document.get(
                        "id",
                        "",
                    )
                )
                for document in documents
                if document.get(
                    "id"
                )
            ],
            document_titles=[
                str(
                    document.get(
                        "title"
                    )
                    or document.get(
                        "original_name"
                    )
                    or "Untitled document"
                )
                for document in documents
            ],
            model=model,
            content=content,
            flashcards=(
                flashcards or []
            ),
            quiz_questions=(
                quiz_questions or []
            ),
            sources=[
                source.to_dict()
                for source in (
                    sources or []
                )
            ],
            created_at=timestamp,
            updated_at=timestamp,
            metadata=metadata or {},
        )

    @staticmethod
    def _default_title(
        prefix: str,
        documents: list[dict[str, Any]],
    ) -> str:
        first_title = str(
            documents[0].get(
                "title"
            )
            or documents[0].get(
                "original_name"
            )
            or "Selected documents"
        )

        if len(documents) == 1:
            return (
                f"{prefix}: {first_title}"
            )

        return (
            f"{prefix}: {first_title} "
            f"and {len(documents) - 1} more"
        )

    @staticmethod
    def _parse_json(
        response: str,
    ) -> dict[str, Any]:
        cleaned = str(
            response or ""
        ).strip()

        if cleaned.startswith(
            "```"
        ):
            cleaned = re.sub(
                r"^```(?:json)?",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )

            cleaned = re.sub(
                r"```$",
                "",
                cleaned,
            ).strip()

        try:
            parsed = json.loads(
                cleaned
            )

        except json.JSONDecodeError:
            match = re.search(
                r"\{.*\}",
                cleaned,
                flags=re.DOTALL,
            )

            if match is None:
                raise StudyError(
                    "The local model did not return valid JSON."
                )

            try:
                parsed = json.loads(
                    match.group(0)
                )

            except json.JSONDecodeError as exc:
                raise StudyError(
                    "The local model returned invalid structured output."
                ) from exc

        if not isinstance(
            parsed,
            dict,
        ):
            raise StudyError(
                "Structured study output must be a JSON object."
            )

        return parsed

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat(
            timespec="seconds"
        )


from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_STUDY_TYPES = {
    "summary",
    "notes",
    "flashcards",
    "quiz",
}


@dataclass(slots=True)
class Flashcard:
    """
    One local study flashcard.
    """

    id: str
    front: str
    back: str
    source_labels: list[str] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        self.id = str(
            self.id or ""
        ).strip()

        self.front = str(
            self.front or ""
        ).strip()[:1_000]

        self.back = str(
            self.back or ""
        ).strip()[:2_000]

        if not isinstance(
            self.source_labels,
            list,
        ):
            self.source_labels = []

        self.source_labels = [
            str(label).strip()
            for label in self.source_labels
            if str(label).strip()
        ][:20]

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "front": self.front,
            "back": self.back,
            "source_labels": self.source_labels,
        }


@dataclass(slots=True)
class QuizQuestion:
    """
    One multiple-choice study question.
    """

    id: str
    question: str
    options: list[str]
    correct_index: int
    explanation: str
    source_labels: list[str] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        self.id = str(
            self.id or ""
        ).strip()

        self.question = str(
            self.question or ""
        ).strip()[:1_500]

        if not isinstance(
            self.options,
            list,
        ):
            self.options = []

        self.options = [
            str(option).strip()[:1_000]
            for option in self.options
            if str(option).strip()
        ][:6]

        try:
            self.correct_index = int(
                self.correct_index
            )

        except (
            TypeError,
            ValueError,
        ):
            self.correct_index = 0

        if self.options:
            self.correct_index = max(
                0,
                min(
                    len(self.options) - 1,
                    self.correct_index,
                ),
            )
        else:
            self.correct_index = 0

        self.explanation = str(
            self.explanation or ""
        ).strip()[:2_000]

        if not isinstance(
            self.source_labels,
            list,
        ):
            self.source_labels = []

        self.source_labels = [
            str(label).strip()
            for label in self.source_labels
            if str(label).strip()
        ][:20]

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "options": self.options,
            "correct_index": self.correct_index,
            "explanation": self.explanation,
            "source_labels": self.source_labels,
        }


@dataclass(slots=True)
class StudySession:
    """
    Persistent output generated from selected local documents.
    """

    id: str
    study_type: str
    title: str
    instruction: str
    document_ids: list[str]
    document_titles: list[str]
    model: str
    content: str = ""
    flashcards: list[Flashcard] = field(
        default_factory=list
    )
    quiz_questions: list[QuizQuestion] = field(
        default_factory=list
    )
    sources: list[dict[str, Any]] = field(
        default_factory=list
    )
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        self.id = str(
            self.id or ""
        ).strip()

        cleaned_type = str(
            self.study_type or "summary"
        ).strip().lower()

        if cleaned_type not in VALID_STUDY_TYPES:
            cleaned_type = "summary"

        self.study_type = cleaned_type

        self.title = str(
            self.title or "Study session"
        ).strip()[:200]

        self.instruction = str(
            self.instruction or ""
        ).strip()[:3_000]

        if not isinstance(
            self.document_ids,
            list,
        ):
            self.document_ids = []

        self.document_ids = [
            str(document_id).strip()
            for document_id in self.document_ids
            if str(document_id).strip()
        ]

        if not isinstance(
            self.document_titles,
            list,
        ):
            self.document_titles = []

        self.document_titles = [
            str(title).strip()
            for title in self.document_titles
            if str(title).strip()
        ]

        self.model = str(
            self.model or ""
        ).strip()

        self.content = str(
            self.content or ""
        ).strip()

        self.flashcards = [
            card
            if isinstance(
                card,
                Flashcard,
            )
            else flashcard_from_dict(
                card
            )
            for card in self.flashcards
            if isinstance(
                card,
                (Flashcard, dict),
            )
        ]

        self.quiz_questions = [
            question
            if isinstance(
                question,
                QuizQuestion,
            )
            else quiz_question_from_dict(
                question
            )
            for question in self.quiz_questions
            if isinstance(
                question,
                (QuizQuestion, dict),
            )
        ]

        if not isinstance(
            self.sources,
            list,
        ):
            self.sources = []

        if not isinstance(
            self.metadata,
            dict,
        ):
            self.metadata = {}

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "study_type": self.study_type,
            "title": self.title,
            "instruction": self.instruction,
            "document_ids": self.document_ids,
            "document_titles": self.document_titles,
            "model": self.model,
            "content": self.content,
            "flashcards": [
                card.to_dict()
                for card in self.flashcards
            ],
            "quiz_questions": [
                question.to_dict()
                for question in self.quiz_questions
            ],
            "sources": self.sources,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


def flashcard_from_dict(
    data: dict[str, Any],
) -> Flashcard:
    return Flashcard(
        id=str(
            data.get(
                "id",
                "",
            )
        ),
        front=str(
            data.get(
                "front",
                "",
            )
        ),
        back=str(
            data.get(
                "back",
                "",
            )
        ),
        source_labels=(
            data.get(
                "source_labels",
                [],
            )
        ),
    )


def quiz_question_from_dict(
    data: dict[str, Any],
) -> QuizQuestion:
    return QuizQuestion(
        id=str(
            data.get(
                "id",
                "",
            )
        ),
        question=str(
            data.get(
                "question",
                "",
            )
        ),
        options=(
            data.get(
                "options",
                [],
            )
        ),
        correct_index=data.get(
            "correct_index",
            0,
        ),
        explanation=str(
            data.get(
                "explanation",
                "",
            )
        ),
        source_labels=(
            data.get(
                "source_labels",
                [],
            )
        ),
    )


def study_session_from_dict(
    data: dict[str, Any],
) -> StudySession:
    return StudySession(
        id=str(
            data.get(
                "id",
                "",
            )
        ),
        study_type=str(
            data.get(
                "study_type",
                "summary",
            )
        ),
        title=str(
            data.get(
                "title",
                "Study session",
            )
        ),
        instruction=str(
            data.get(
                "instruction",
                "",
            )
        ),
        document_ids=(
            data.get(
                "document_ids",
                [],
            )
        ),
        document_titles=(
            data.get(
                "document_titles",
                [],
            )
        ),
        model=str(
            data.get(
                "model",
                "",
            )
        ),
        content=str(
            data.get(
                "content",
                "",
            )
        ),
        flashcards=[
            flashcard_from_dict(
                card
            )
            for card in data.get(
                "flashcards",
                [],
            )
            if isinstance(
                card,
                dict,
            )
        ],
        quiz_questions=[
            quiz_question_from_dict(
                question
            )
            for question in data.get(
                "quiz_questions",
                [],
            )
            if isinstance(
                question,
                dict,
            )
        ],
        sources=(
            data.get(
                "sources",
                [],
            )
        ),
        created_at=str(
            data.get(
                "created_at",
                "",
            )
        ),
        updated_at=str(
            data.get(
                "updated_at",
                "",
            )
        ),
        metadata=(
            data.get(
                "metadata",
                {},
            )
        ),
    )
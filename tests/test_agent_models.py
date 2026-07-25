from __future__ import annotations

from agents.composer import (
    ComposerAttachment,
    ComposerSubmission,
)
from agents.critic import (
    CriticFinding,
    CriticReport,
)
from agents.executor import (
    PlanExecutionReport,
    StepExecution,
)
from agents.memory import (
    MemoryItem,
    TaskState,
)
from agents.planner import (
    AgentPlan,
    PlanStep,
)
from agents.study import (
    Flashcard,
    QuizQuestion,
    StudySession,
)


def test_composer_submission_normalises_mode() -> None:
    submission = ComposerSubmission(
        prompt="Hello",
        reasoning_mode="invalid",
        web_search_enabled=True,
        document_search_enabled=True,
    )

    assert submission.prompt == "Hello"
    assert submission.reasoning_mode == "normal"
    assert submission.web_search_enabled is True


def test_composer_attachment_normalises_values() -> None:
    attachment = ComposerAttachment(
        name=" notes.pdf ",
        size_bytes=-10,
        mime_type="application/pdf",
        indexed_chunks=-3,
    )

    assert attachment.name == "notes.pdf"
    assert attachment.size_bytes == 0
    assert attachment.indexed_chunks == 0


def test_plan_sorts_steps() -> None:
    plan = AgentPlan(
        id="plan-1",
        user_request="Build something",
        goal="Build something",
        summary="Test",
        requires_plan=True,
        confidence=0.8,
        route="general",
        recommended_skill=None,
        use_documents=False,
        steps=[
            PlanStep(
                id="step_2",
                order=2,
                title="Second",
                description="Second step",
            ),
            PlanStep(
                id="step_1",
                order=1,
                title="First",
                description="First step",
            ),
        ],
    )

    assert [
        step.id
        for step in plan.steps
    ] == [
        "step_1",
        "step_2",
    ]


def test_execution_report_progress() -> None:
    report = PlanExecutionReport(
        id="run-1",
        plan_id="plan-1",
        user_request="Test",
        goal="Test",
        status="running",
        started_at="2026-01-01T00:00:00+00:00",
        steps=[
            StepExecution(
                step_id="step_1",
                order=1,
                title="First",
                step_type="reason",
                status="completed",
                started_at=(
                    "2026-01-01T00:00:00+00:00"
                ),
            ),
            StepExecution(
                step_id="step_2",
                order=2,
                title="Second",
                step_type="write",
                status="running",
                started_at=(
                    "2026-01-01T00:00:01+00:00"
                ),
            ),
        ],
    )

    assert report.completed_step_count == 1
    assert report.progress == 0.5


def test_critic_counts_material_findings() -> None:
    report = CriticReport(
        id="critic-1",
        user_request="Test",
        original_output="Output",
        passed=False,
        requires_revision=True,
        score=0.5,
        summary="Needs work",
        findings=[
            CriticFinding(
                category="accuracy",
                severity="error",
                message="Incorrect claim",
            ),
            CriticFinding(
                category="clarity",
                severity="warning",
                message="Unclear wording",
            ),
        ],
    )

    assert report.error_count == 1
    assert report.warning_count == 1


def test_memory_item_deduplicates_keywords() -> None:
    item = MemoryItem(
        id="memory-1",
        content="Use complete files",
        keywords=[
            "Python",
            "python",
            "Full Files",
        ],
    )

    assert item.keywords == [
        "python",
        "full files",
    ]


def test_task_state_defaults_goal() -> None:
    state = TaskState(
        id="task-1",
        chat_id=None,
        user_request="Create a report",
        goal="",
        status="pending",
    )

    assert state.goal == "Create a report"


def test_flashcard_serialisation() -> None:
    card = Flashcard(
        id="card-1",
        front="Question",
        back="Answer",
        source_labels=[
            "Source 1",
        ],
    )

    assert card.to_dict()[
        "front"
    ] == "Question"


def test_quiz_correct_index_is_clamped() -> None:
    question = QuizQuestion(
        id="question-1",
        question="Choose",
        options=[
            "A",
            "B",
            "C",
            "D",
        ],
        correct_index=99,
        explanation="D is correct",
    )

    assert question.correct_index == 3


def test_study_session_normalises_type() -> None:
    session = StudySession(
        id="study-1",
        study_type="invalid",
        title="Session",
        instruction="Test",
        document_ids=[],
        document_titles=[],
        model="llama3.2",
    )

    assert session.study_type == "summary"
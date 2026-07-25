from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_EXECUTION_STATUSES = {
    "pending",
    "running",
    "completed",
    "failed",
    "stopped",
}


@dataclass(slots=True)
class StepExecution:
    """
    Execution result for one plan step.
    """

    step_id: str
    order: int
    title: str
    step_type: str
    status: str
    started_at: str
    completed_at: str | None = None
    output: str = ""
    error: str | None = None
    tool_result: dict[str, Any] | None = None
    document_sources: list[dict[str, Any]] = field(
        default_factory=list
    )
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        self.step_id = str(
            self.step_id or ""
        ).strip()

        try:
            self.order = int(
                self.order
            )

        except (
            TypeError,
            ValueError,
        ):
            self.order = 1

        self.title = str(
            self.title or "Untitled step"
        ).strip()

        self.step_type = str(
            self.step_type or "reason"
        ).strip().lower()

        cleaned_status = str(
            self.status or "pending"
        ).strip().lower()

        if (
            cleaned_status
            not in VALID_EXECUTION_STATUSES
        ):
            cleaned_status = "pending"

        self.status = cleaned_status

        self.started_at = str(
            self.started_at or ""
        )

        if self.completed_at is not None:
            self.completed_at = str(
                self.completed_at
            )

        self.output = str(
            self.output or ""
        )

        if self.error is not None:
            self.error = str(
                self.error
            )

        if not isinstance(
            self.document_sources,
            list,
        ):
            self.document_sources = []

        if not isinstance(
            self.metadata,
            dict,
        ):
            self.metadata = {}

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "order": self.order,
            "title": self.title,
            "step_type": self.step_type,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": (
                self.completed_at
            ),
            "output": self.output,
            "error": self.error,
            "tool_result": self.tool_result,
            "document_sources": (
                self.document_sources
            ),
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class PlanExecutionReport:
    """
    Persistent result of executing an AgentPlan.
    """

    id: str
    plan_id: str
    user_request: str
    goal: str
    status: str
    started_at: str
    completed_at: str | None = None
    steps: list[StepExecution] = field(
        default_factory=list
    )
    final_output: str = ""
    error: str | None = None
    model: str | None = None
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        self.id = str(
            self.id or ""
        ).strip()

        self.plan_id = str(
            self.plan_id or ""
        ).strip()

        self.user_request = str(
            self.user_request or ""
        ).strip()

        self.goal = str(
            self.goal or ""
        ).strip()

        cleaned_status = str(
            self.status or "pending"
        ).strip().lower()

        if (
            cleaned_status
            not in VALID_EXECUTION_STATUSES
        ):
            cleaned_status = "pending"

        self.status = cleaned_status

        self.started_at = str(
            self.started_at or ""
        )

        if self.completed_at is not None:
            self.completed_at = str(
                self.completed_at
            )

        self.steps = [
            step
            if isinstance(
                step,
                StepExecution,
            )
            else step_execution_from_dict(
                step
            )
            for step in self.steps
            if isinstance(
                step,
                (StepExecution, dict),
            )
        ]

        self.final_output = str(
            self.final_output or ""
        )

        if self.error is not None:
            self.error = str(
                self.error
            )

        if self.model is not None:
            self.model = str(
                self.model
            )

        if not isinstance(
            self.metadata,
            dict,
        ):
            self.metadata = {}

    @property
    def completed_step_count(
        self,
    ) -> int:
        return sum(
            1
            for step in self.steps
            if step.status == "completed"
        )

    @property
    def failed_step_count(
        self,
    ) -> int:
        return sum(
            1
            for step in self.steps
            if step.status == "failed"
        )

    @property
    def progress(
        self,
    ) -> float:
        if not self.steps:
            return 0.0

        finished = sum(
            1
            for step in self.steps
            if step.status
            in {
                "completed",
                "failed",
                "stopped",
            }
        )

        return finished / len(
            self.steps
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "user_request": (
                self.user_request
            ),
            "goal": self.goal,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": (
                self.completed_at
            ),
            "steps": [
                step.to_dict()
                for step in self.steps
            ],
            "final_output": (
                self.final_output
            ),
            "error": self.error,
            "model": self.model,
            "metadata": self.metadata,
        }


def step_execution_from_dict(
    data: dict[str, Any],
) -> StepExecution:
    return StepExecution(
        step_id=str(
            data.get(
                "step_id",
                "",
            )
        ),
        order=data.get(
            "order",
            1,
        ),
        title=str(
            data.get(
                "title",
                "Untitled step",
            )
        ),
        step_type=str(
            data.get(
                "step_type",
                "reason",
            )
        ),
        status=str(
            data.get(
                "status",
                "pending",
            )
        ),
        started_at=str(
            data.get(
                "started_at",
                "",
            )
        ),
        completed_at=(
            data.get(
                "completed_at"
            )
        ),
        output=str(
            data.get(
                "output",
                "",
            )
        ),
        error=(
            data.get(
                "error"
            )
        ),
        tool_result=(
            data.get(
                "tool_result"
            )
        ),
        document_sources=(
            data.get(
                "document_sources",
                [],
            )
        ),
        metadata=(
            data.get(
                "metadata",
                {},
            )
        ),
    )


def execution_report_from_dict(
    data: dict[str, Any],
) -> PlanExecutionReport:
    return PlanExecutionReport(
        id=str(
            data.get(
                "id",
                "",
            )
        ),
        plan_id=str(
            data.get(
                "plan_id",
                "",
            )
        ),
        user_request=str(
            data.get(
                "user_request",
                "",
            )
        ),
        goal=str(
            data.get(
                "goal",
                "",
            )
        ),
        status=str(
            data.get(
                "status",
                "pending",
            )
        ),
        started_at=str(
            data.get(
                "started_at",
                "",
            )
        ),
        completed_at=(
            data.get(
                "completed_at"
            )
        ),
        steps=[
            step_execution_from_dict(
                step
            )
            for step in data.get(
                "steps",
                [],
            )
            if isinstance(
                step,
                dict,
            )
        ],
        final_output=str(
            data.get(
                "final_output",
                "",
            )
        ),
        error=(
            data.get(
                "error"
            )
        ),
        model=(
            data.get(
                "model"
            )
        ),
        metadata=(
            data.get(
                "metadata",
                {},
            )
        ),
    )
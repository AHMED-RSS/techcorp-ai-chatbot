from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_STEP_TYPES = {
    "reason",
    "document_search",
    "tool",
    "write",
    "review",
}


VALID_STEP_STATUSES = {
    "pending",
    "running",
    "completed",
    "failed",
    "skipped",
}


@dataclass(slots=True)
class PlanStep:
    """
    One ordered step inside an agent plan.
    """

    id: str
    order: int
    title: str
    description: str
    step_type: str = "reason"
    route: str = "general"
    skill_slug: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] = field(
        default_factory=dict
    )
    use_documents: bool = False
    depends_on: list[str] = field(
        default_factory=list
    )
    status: str = "pending"
    result: str | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        self.id = str(
            self.id or ""
        ).strip()

        if not self.id:
            self.id = f"step_{self.order}"

        try:
            self.order = int(
                self.order
            )

        except (
            TypeError,
            ValueError,
        ):
            self.order = 1

        self.order = max(
            1,
            self.order,
        )

        self.title = str(
            self.title or "Untitled step"
        ).strip()[:120]

        self.description = str(
            self.description or ""
        ).strip()[:1000]

        cleaned_type = str(
            self.step_type or "reason"
        ).strip().lower()

        if cleaned_type not in VALID_STEP_TYPES:
            cleaned_type = "reason"

        self.step_type = cleaned_type

        self.route = str(
            self.route or "general"
        ).strip().lower()

        if self.skill_slug is not None:
            cleaned_skill = str(
                self.skill_slug
            ).strip()

            self.skill_slug = (
                cleaned_skill or None
            )

        if self.tool_name is not None:
            cleaned_tool = str(
                self.tool_name
            ).strip().lower()

            self.tool_name = (
                cleaned_tool or None
            )

        if not isinstance(
            self.tool_arguments,
            dict,
        ):
            self.tool_arguments = {}

        self.use_documents = bool(
            self.use_documents
        )

        if not isinstance(
            self.depends_on,
            list,
        ):
            self.depends_on = []

        self.depends_on = [
            str(step_id).strip()
            for step_id in self.depends_on
            if str(step_id).strip()
        ]

        cleaned_status = str(
            self.status or "pending"
        ).strip().lower()

        if cleaned_status not in VALID_STEP_STATUSES:
            cleaned_status = "pending"

        self.status = cleaned_status

        if self.result is not None:
            self.result = str(
                self.result
            )

        if self.error is not None:
            self.error = str(
                self.error
            )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "order": self.order,
            "title": self.title,
            "description": self.description,
            "step_type": self.step_type,
            "route": self.route,
            "skill_slug": self.skill_slug,
            "tool_name": self.tool_name,
            "tool_arguments": self.tool_arguments,
            "use_documents": self.use_documents,
            "depends_on": self.depends_on,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }


@dataclass(slots=True)
class AgentPlan:
    """
    Structured goal and ordered steps for a user request.
    """

    id: str
    user_request: str
    goal: str
    summary: str
    requires_plan: bool
    confidence: float
    route: str
    recommended_skill: str | None
    use_documents: bool
    steps: list[PlanStep] = field(
        default_factory=list
    )
    assumptions: list[str] = field(
        default_factory=list
    )
    success_criteria: list[str] = field(
        default_factory=list
    )
    status: str = "planned"
    created_at: str = ""
    updated_at: str = ""
    source: str = "fallback"

    def __post_init__(self) -> None:
        self.id = str(
            self.id or ""
        ).strip()

        self.user_request = str(
            self.user_request or ""
        ).strip()

        self.goal = str(
            self.goal or self.user_request
        ).strip()[:1000]

        self.summary = str(
            self.summary or ""
        ).strip()[:1500]

        self.requires_plan = bool(
            self.requires_plan
        )

        try:
            confidence = float(
                self.confidence
            )

        except (
            TypeError,
            ValueError,
        ):
            confidence = 0.0

        self.confidence = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

        self.route = str(
            self.route or "general"
        ).strip().lower()

        if self.recommended_skill is not None:
            cleaned_skill = str(
                self.recommended_skill
            ).strip()

            self.recommended_skill = (
                cleaned_skill or None
            )

        self.use_documents = bool(
            self.use_documents
        )

        self.steps = sorted(
            [
                step
                if isinstance(
                    step,
                    PlanStep,
                )
                else plan_step_from_dict(
                    step
                )
                for step in self.steps
                if isinstance(
                    step,
                    (PlanStep, dict),
                )
            ],
            key=lambda step: step.order,
        )

        if not isinstance(
            self.assumptions,
            list,
        ):
            self.assumptions = []

        self.assumptions = [
            str(item).strip()
            for item in self.assumptions
            if str(item).strip()
        ]

        if not isinstance(
            self.success_criteria,
            list,
        ):
            self.success_criteria = []

        self.success_criteria = [
            str(item).strip()
            for item in self.success_criteria
            if str(item).strip()
        ]

        self.status = str(
            self.status or "planned"
        ).strip().lower()

        self.source = str(
            self.source or "fallback"
        ).strip()

    @property
    def step_count(self) -> int:
        return len(
            self.steps
        )

    @property
    def completed_step_count(self) -> int:
        return sum(
            1
            for step in self.steps
            if step.status == "completed"
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_request": self.user_request,
            "goal": self.goal,
            "summary": self.summary,
            "requires_plan": self.requires_plan,
            "confidence": self.confidence,
            "route": self.route,
            "recommended_skill": (
                self.recommended_skill
            ),
            "use_documents": (
                self.use_documents
            ),
            "steps": [
                step.to_dict()
                for step in self.steps
            ],
            "assumptions": self.assumptions,
            "success_criteria": (
                self.success_criteria
            ),
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
        }


def plan_step_from_dict(
    data: dict[str, Any],
) -> PlanStep:
    return PlanStep(
        id=str(
            data.get(
                "id",
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
        description=str(
            data.get(
                "description",
                "",
            )
        ),
        step_type=str(
            data.get(
                "step_type",
                "reason",
            )
        ),
        route=str(
            data.get(
                "route",
                "general",
            )
        ),
        skill_slug=(
            data.get(
                "skill_slug"
            )
        ),
        tool_name=(
            data.get(
                "tool_name"
            )
        ),
        tool_arguments=(
            data.get(
                "tool_arguments",
                {},
            )
        ),
        use_documents=bool(
            data.get(
                "use_documents",
                False,
            )
        ),
        depends_on=(
            data.get(
                "depends_on",
                [],
            )
        ),
        status=str(
            data.get(
                "status",
                "pending",
            )
        ),
        result=(
            data.get(
                "result"
            )
        ),
        error=(
            data.get(
                "error"
            )
        ),
    )


def agent_plan_from_dict(
    data: dict[str, Any],
) -> AgentPlan:
    return AgentPlan(
        id=str(
            data.get(
                "id",
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
        summary=str(
            data.get(
                "summary",
                "",
            )
        ),
        requires_plan=bool(
            data.get(
                "requires_plan",
                False,
            )
        ),
        confidence=data.get(
            "confidence",
            0.0,
        ),
        route=str(
            data.get(
                "route",
                "general",
            )
        ),
        recommended_skill=(
            data.get(
                "recommended_skill"
            )
        ),
        use_documents=bool(
            data.get(
                "use_documents",
                False,
            )
        ),
        steps=[
            plan_step_from_dict(
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
        assumptions=(
            data.get(
                "assumptions",
                [],
            )
        ),
        success_criteria=(
            data.get(
                "success_criteria",
                [],
            )
        ),
        status=str(
            data.get(
                "status",
                "planned",
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
        source=str(
            data.get(
                "source",
                "fallback",
            )
        ),
    )
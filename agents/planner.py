from __future__ import annotations

import uuid

from dataclasses import dataclass, field
from datetime import datetime, timezone
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


def _utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def _normalise_string_list(
    value: Any,
) -> list[str]:
    if not isinstance(
        value,
        list,
    ):
        return []

    result: list[str] = []

    for item in value:
        cleaned = str(
            item or ""
        ).strip()

        if cleaned:
            result.append(
                cleaned
            )

    return result


@dataclass(slots=True)
class PlanStep:
    """
    One executable step inside an agent plan.
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

    def __post_init__(
        self,
    ) -> None:
        try:
            self.order = int(
                self.order
            )

        except (
            TypeError,
            ValueError,
        ):
            self.order = 1

        if self.order < 1:
            self.order = 1

        self.id = str(
            self.id
            or f"step_{self.order}"
        ).strip()

        self.title = str(
            self.title
            or "Untitled step"
        ).strip()

        self.description = str(
            self.description
            or ""
        ).strip()

        self.step_type = str(
            self.step_type
            or "reason"
        ).strip().lower()

        if self.step_type not in VALID_STEP_TYPES:
            self.step_type = "reason"

        self.route = str(
            self.route
            or "general"
        ).strip().lower()

        self.status = str(
            self.status
            or "pending"
        ).strip().lower()

        if self.status not in VALID_STEP_STATUSES:
            self.status = "pending"

        if self.skill_slug is not None:
            self.skill_slug = str(
                self.skill_slug
            ).strip() or None

        if self.tool_name is not None:
            self.tool_name = str(
                self.tool_name
            ).strip() or None

        if not isinstance(
            self.tool_arguments,
            dict,
        ):
            self.tool_arguments = {}

        self.use_documents = bool(
            self.use_documents
        )

        self.depends_on = (
            _normalise_string_list(
                self.depends_on
            )
        )

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
            "tool_arguments": dict(
                self.tool_arguments
            ),
            "use_documents": self.use_documents,
            "depends_on": list(
                self.depends_on
            ),
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }


@dataclass(slots=True)
class AgentPlan:
    """
    Autonomous execution plan.
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
    source: str = "planner"

    def __post_init__(
        self,
    ) -> None:
        self.id = str(
            self.id
            or f"plan_{uuid.uuid4().hex[:8]}"
        ).strip()

        self.user_request = str(
            self.user_request
            or ""
        ).strip()

        self.goal = str(
            self.goal
            or self.user_request
        ).strip()

        self.summary = str(
            self.summary
            or ""
        ).strip()

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
            confidence = 0.5

        if confidence > 1.0 and confidence <= 100:
            confidence /= 100

        self.confidence = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

        self.route = str(
            self.route
            or "general"
        ).strip().lower()

        if self.recommended_skill is not None:
            self.recommended_skill = str(
                self.recommended_skill
            ).strip() or None

        self.use_documents = bool(
            self.use_documents
        )

        normalised_steps: list[
            PlanStep
        ] = []

        for step in self.steps:
            if isinstance(
                step,
                PlanStep,
            ):
                normalised_steps.append(
                    step
                )

            elif isinstance(
                step,
                dict,
            ):
                normalised_steps.append(
                    plan_step_from_dict(
                        step
                    )
                )

        normalised_steps.sort(
            key=lambda step: (
                step.order,
                step.id,
            )
        )

        self.steps = normalised_steps

        self.assumptions = (
            _normalise_string_list(
                self.assumptions
            )
        )

        self.success_criteria = (
            _normalise_string_list(
                self.success_criteria
            )
        )

        self.status = str(
            self.status
            or "planned"
        ).strip().lower()

        now = _utc_now()

        self.created_at = str(
            self.created_at
            or now
        )

        self.updated_at = str(
            self.updated_at
            or self.created_at
        )

        self.source = str(
            self.source
            or "planner"
        ).strip()

    @property
    def step_count(
        self,
    ) -> int:
        return len(
            self.steps
        )

    @property
    def completed_step_count(
        self,
    ) -> int:
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
            "use_documents": self.use_documents,
            "steps": [
                step.to_dict()
                for step in self.steps
            ],
            "assumptions": list(
                self.assumptions
            ),
            "success_criteria": list(
                self.success_criteria
            ),
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
        }


def create_plan(
    user_request: str,
    route_decision: Any,
) -> AgentPlan:
    """
    Convert a route decision into a simple executable plan.
    """

    route = str(
        getattr(
            route_decision,
            "route",
            "general",
        )
        or "general"
    ).strip().lower()

    skill = getattr(
        route_decision,
        "recommended_skill",
        None,
    )

    use_documents = bool(
        getattr(
            route_decision,
            "use_documents",
            False,
        )
    )

    try:
        confidence = float(
            getattr(
                route_decision,
                "confidence",
                0.5,
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        confidence = 0.5

    if route == "document":
        steps = [
            PlanStep(
                id="retrieve_documents",
                order=1,
                title="Retrieve documents",
                description=(
                    "Search the indexed local documents for "
                    "information relevant to the request."
                ),
                step_type="document_search",
                route="document",
                use_documents=True,
            ),
            PlanStep(
                id="analyze_context",
                order=2,
                title="Analyse retrieved context",
                description=(
                    "Identify the relevant evidence and "
                    "organise the important findings."
                ),
                step_type="reason",
                route="document",
                use_documents=True,
                depends_on=[
                    "retrieve_documents"
                ],
            ),
            PlanStep(
                id="generate_answer",
                order=3,
                title="Generate response",
                description=(
                    "Answer the user using the retrieved "
                    "document evidence."
                ),
                step_type="write",
                route="general",
                use_documents=True,
                depends_on=[
                    "analyze_context"
                ],
            ),
            PlanStep(
                id="quality_check",
                order=4,
                title="Quality review",
                description=(
                    "Check that the final response is accurate, "
                    "relevant and supported by evidence."
                ),
                step_type="review",
                route="general",
                depends_on=[
                    "generate_answer"
                ],
            ),
        ]

    elif route == "vision":
        steps = [
            PlanStep(
                id="image_analysis",
                order=1,
                title="Analyse image",
                description=(
                    "Inspect the image and extract relevant "
                    "visual information."
                ),
                step_type="reason",
                route="vision",
            ),
            PlanStep(
                id="vision_response",
                order=2,
                title="Explain findings",
                description=(
                    "Provide a clear answer based on the "
                    "visual analysis."
                ),
                step_type="write",
                route="vision",
                depends_on=[
                    "image_analysis"
                ],
            ),
        ]

    elif route == "study":
        steps = [
            PlanStep(
                id="study_analysis",
                order=1,
                title="Understand topic",
                description=(
                    "Analyse the requested topic and identify "
                    "the learning objectives."
                ),
                step_type="reason",
                route="study",
            ),
            PlanStep(
                id="study_output",
                order=2,
                title="Create study material",
                description=(
                    "Generate the requested notes, quiz, "
                    "flashcards or explanation."
                ),
                step_type="write",
                route="study",
                depends_on=[
                    "study_analysis"
                ],
            ),
        ]

    else:
        steps = [
            PlanStep(
                id="understand_request",
                order=1,
                title="Understand request",
                description=(
                    "Identify the user's objective and "
                    "the required response."
                ),
                step_type="reason",
                route=route,
            ),
            PlanStep(
                id="final_answer",
                order=2,
                title="Answer user",
                description=(
                    "Produce a direct and complete response."
                ),
                step_type="write",
                route=route,
                depends_on=[
                    "understand_request"
                ],
            ),
        ]

    now = _utc_now()

    return AgentPlan(
        id=f"plan_{uuid.uuid4().hex[:8]}",
        user_request=user_request,
        goal=(
            f"Complete the request using the "
            f"{route} route."
        ),
        summary=(
            "Autonomous plan generated by the "
            "planner agent."
        ),
        requires_plan=(
            len(
                steps
            )
            > 1
        ),
        confidence=confidence,
        route=route,
        recommended_skill=skill,
        use_documents=use_documents,
        steps=steps,
        assumptions=[
            (
                "The user request has been routed "
                "correctly."
            )
        ],
        success_criteria=[
            "All required steps are completed.",
            (
                "The final response addresses the "
                "user's request."
            ),
        ],
        status="planned",
        created_at=now,
        updated_at=now,
        source="autonomous_planner",
    )


def plan_step_from_dict(
    data: dict[str, Any],
) -> PlanStep:
    return PlanStep(
        id=data.get(
            "id",
            "",
        ),
        order=data.get(
            "order",
            1,
        ),
        title=data.get(
            "title",
            "",
        ),
        description=data.get(
            "description",
            "",
        ),
        step_type=data.get(
            "step_type",
            "reason",
        ),
        route=data.get(
            "route",
            "general",
        ),
        skill_slug=data.get(
            "skill_slug"
        ),
        tool_name=data.get(
            "tool_name"
        ),
        tool_arguments=data.get(
            "tool_arguments",
            {},
        ),
        use_documents=data.get(
            "use_documents",
            False,
        ),
        depends_on=data.get(
            "depends_on",
            [],
        ),
        status=data.get(
            "status",
            "pending",
        ),
        result=data.get(
            "result"
        ),
        error=data.get(
            "error"
        ),
    )


def agent_plan_from_dict(
    data: dict[str, Any],
) -> AgentPlan:
    raw_steps = data.get(
        "steps",
        [],
    )

    steps = [
        plan_step_from_dict(
            item
        )
        for item in raw_steps
        if isinstance(
            item,
            dict,
        )
    ]

    return AgentPlan(
        id=data.get(
            "id",
            "",
        ),
        user_request=data.get(
            "user_request",
            "",
        ),
        goal=data.get(
            "goal",
            "",
        ),
        summary=data.get(
            "summary",
            "",
        ),
        requires_plan=data.get(
            "requires_plan",
            bool(
                steps
            ),
        ),
        confidence=data.get(
            "confidence",
            0.5,
        ),
        route=data.get(
            "route",
            "general",
        ),
        recommended_skill=data.get(
            "recommended_skill"
        ),
        use_documents=data.get(
            "use_documents",
            False,
        ),
        steps=steps,
        assumptions=data.get(
            "assumptions",
            [],
        ),
        success_criteria=data.get(
            "success_criteria",
            [],
        ),
        status=data.get(
            "status",
            "planned",
        ),
        created_at=data.get(
            "created_at",
            "",
        ),
        updated_at=data.get(
            "updated_at",
            "",
        ),
        source=data.get(
            "source",
            "planner",
        ),
    )
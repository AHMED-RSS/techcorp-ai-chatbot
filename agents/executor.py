from __future__ import annotations

import uuid

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.providers import AIProvider


VALID_EXECUTION_STATUSES = {
    "pending",
    "running",
    "completed",
    "completed_with_warnings",
    "failed",
    "skipped",
    "stopped",
}


def _utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


@dataclass(slots=True)
class StepExecution:
    step_id: str
    order: int
    title: str
    step_type: str
    status: str
    started_at: str

    completed_at: str | None = None
    output: str = ""
    error: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(
        self,
    ) -> None:
        self.step_id = str(
            self.step_id
            or ""
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
            self.title
            or "Untitled step"
        ).strip()

        self.step_type = str(
            self.step_type
            or "reason"
        ).strip().lower()

        self.status = str(
            self.status
            or "pending"
        ).strip().lower()

        if self.status not in VALID_EXECUTION_STATUSES:
            self.status = "pending"

        self.started_at = str(
            self.started_at
            or _utc_now()
        )

        if self.completed_at is not None:
            self.completed_at = str(
                self.completed_at
            )

        self.output = str(
            self.output
            or ""
        )

        if self.error is not None:
            self.error = str(
                self.error
            )

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
            "completed_at": self.completed_at,
            "output": self.output,
            "error": self.error,
            "metadata": dict(
                self.metadata
            ),
        }


@dataclass(slots=True)
class PlanExecutionReport:
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

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(
        self,
    ) -> None:
        self.id = str(
            self.id
            or f"exec_{uuid.uuid4().hex[:8]}"
        ).strip()

        self.plan_id = str(
            self.plan_id
            or ""
        ).strip()

        self.user_request = str(
            self.user_request
            or ""
        ).strip()

        self.goal = str(
            self.goal
            or self.user_request
        ).strip()

        self.status = str(
            self.status
            or "pending"
        ).strip().lower()

        if self.status not in VALID_EXECUTION_STATUSES:
            self.status = "pending"

        self.started_at = str(
            self.started_at
            or _utc_now()
        )

        if self.completed_at is not None:
            self.completed_at = str(
                self.completed_at
            )

        normalised_steps: list[
            StepExecution
        ] = []

        for step in self.steps:
            if isinstance(
                step,
                StepExecution,
            ):
                normalised_steps.append(
                    step
                )

            elif isinstance(
                step,
                dict,
            ):
                normalised_steps.append(
                    step_execution_from_dict(
                        step
                    )
                )

        normalised_steps.sort(
            key=lambda step: (
                step.order,
                step.step_id,
            )
        )

        self.steps = normalised_steps

        self.final_output = str(
            self.final_output
            or ""
        )

        if self.error is not None:
            self.error = str(
                self.error
            )

        if not isinstance(
            self.metadata,
            dict,
        ):
            self.metadata = {}

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
    def skipped_step_count(
        self,
    ) -> int:
        return sum(
            1
            for step in self.steps
            if step.status == "skipped"
        )

    @property
    def progress(
        self,
    ) -> float:
        if not self.steps:
            return 0.0

        return (
            self.completed_step_count
            / len(
                self.steps
            )
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "user_request": self.user_request,
            "goal": self.goal,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "steps": [
                step.to_dict()
                for step in self.steps
            ],
            "step_count": self.step_count,
            "completed_step_count": (
                self.completed_step_count
            ),
            "failed_step_count": (
                self.failed_step_count
            ),
            "skipped_step_count": (
                self.skipped_step_count
            ),
            "final_output": self.final_output,
            "progress": self.progress,
            "error": self.error,
            "metadata": dict(
                self.metadata
            ),
        }


def execute_plan(
    plan: Any,
    *,
    model: str | None = None,
    ai_provider: AIProvider | None = None,
) -> PlanExecutionReport:
    execution = PlanExecutionReport(
        id=f"exec_{uuid.uuid4().hex[:8]}",
        plan_id=plan.id,
        user_request=plan.user_request,
        goal=plan.goal,
        status="running",
        started_at=_utc_now(),
    )

    context: dict[str, Any] = {}

    ordered_steps = sorted(
        plan.steps,
        key=lambda step: (
            step.order,
            step.id,
        ),
    )

    for step in ordered_steps:
        started_at = _utc_now()

        try:
            output = execute_step(
                step,
                context=context,
                user_request=(
                    execution.user_request
                ),
                model=model,
                ai_provider=ai_provider,
            )

            context[
                step.id
            ] = output

            execution.steps.append(
                StepExecution(
                    step_id=step.id,
                    order=step.order,
                    title=step.title,
                    step_type=step.step_type,
                    status="completed",
                    started_at=started_at,
                    completed_at=_utc_now(),
                    output=str(
                        output
                        if output is not None
                        else ""
                    ),
                )
            )

        except Exception as exc:
            execution.steps.append(
                StepExecution(
                    step_id=step.id,
                    order=step.order,
                    title=step.title,
                    step_type=step.step_type,
                    status="failed",
                    started_at=started_at,
                    completed_at=_utc_now(),
                    error=str(
                        exc
                    ),
                )
            )

    if execution.failed_step_count:
        execution.status = "failed"
        execution.error = (
            "One or more execution steps failed."
        )

        successful_outputs = [
            step.output
            for step in execution.steps
            if (
                step.output
                and step.status == "completed"
                and step.step_type != "review"
            )
        ]

        execution.final_output = (
            successful_outputs[-1]
            if successful_outputs
            else "Execution failed."
        )

    else:
        execution.status = "completed"

        outputs = [
            step.output
            for step in execution.steps
            if (
                step.output
                and step.step_type != "review"
            )
        ]

        if outputs:
            execution.final_output = (
                outputs[-1]
            )

    execution.completed_at = _utc_now()

    execution.metadata.setdefault(
        "model",
        model,
    )

    return execution


def execute_step(
    step: Any,
    context: dict[str, Any] | None = None,
    user_request: str = "",
    model: str | None = None,
    ai_provider: AIProvider | None = None,
) -> Any:
    step_type = str(
        step.step_type
        or "reason"
    ).lower()

    context = context or {}

    if step_type == "document_search":
        from config.settings import Settings
        from core.ollama_client import OllamaManager
        from core.providers import OllamaProvider
        from services.rag_service import RAGService

        settings = Settings()

        if ai_provider is None:
            ai_provider = OllamaProvider(
                OllamaManager(settings)
            )

        rag = RAGService(
            settings,
            ai_provider,
        )

        results = rag.search(
            query=user_request,
            top_k=8,
        )

        return rag.build_context(
            results
        )

    if step_type == "tool":
        from services.tool_service import ToolService

        service = ToolService()

        return service.execute(
            step.tool_name,
            step.tool_arguments,
        )

    if step.skill_slug:
        from services.skill_service import SkillService

        service = SkillService()

        return service.execute(
            step.skill_slug
        )

    if step_type in {
        "reason",
        "write",
    }:
        from config.settings import Settings
        from core.ollama_client import OllamaManager
        from core.providers import OllamaProvider

        settings = Settings()

        if ai_provider is None:
            ai_provider = OllamaProvider(
                OllamaManager(settings)
            )

        client = ai_provider

        context_text = "\n\n".join(
            str(
                value
            )
            for value in context.values()
            if value
        )

        prompt = f"""
You are a local AI assistant completing one step of an
agent execution plan.

USER REQUEST:
{user_request}

PREVIOUS STEP CONTEXT:
{context_text or "No previous step context."}

CURRENT STEP:
{step.title}

INSTRUCTION:
{step.description}

RULES:
- Answer the user's request directly.
- Use supplied context when it is relevant.
- Do not output internal workflow messages.
- Do not output STEP COMPLETE, PLAN GOAL UPDATE or NEXT STEP.
- Do not invent sources, URLs or tool results.
- Return only useful natural-language content.
""".strip()

        selected_model = (
            model
            or getattr(
                settings,
                "ollama_chat_model",
                None,
            )
        )

        try:
            return client.chat(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=selected_model,
            )

        except TypeError:
            return client.chat(
                [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ]
            )

    if step_type == "review":
        from agents.critic import evaluate_response

        candidate_output = ""

        for value in reversed(
            list(
                context.values()
            )
        ):
            if value:
                candidate_output = str(
                    value
                )
                break

        report = evaluate_response(
            user_request,
            candidate_output,
        )

        return report.to_dict()

    return (
        f"Executed: {step.title}"
    )


def run_agent_cycle(
    user_request: str,
    plan: Any,
    max_retries: int = 2,
    ai_provider: AIProvider | None = None,
) -> PlanExecutionReport:
    from agents.critic import evaluate_response

    retry = 0
    execution: PlanExecutionReport | None = None

    while retry <= max_retries:
        execution = execute_plan(
            plan,
            ai_provider=ai_provider,
        )

        if execution.status == "failed":
            return execution

        review = evaluate_response(
            user_request,
            execution.final_output,
        )

        execution.metadata.update(
            {
                "critic_score": review.score,
                "critic_passed": review.passed,
                "retry": retry,
            }
        )

        if review.passed:
            return execution

        retry += 1

        if retry > max_retries:
            execution.status = (
                "completed_with_warnings"
            )

            return execution

        from agents.planner import create_plan
        from agents.router import detect_route

        new_route = detect_route(
            user_request
        )

        plan = create_plan(
            user_request,
            new_route,
        )

    if execution is None:
        raise RuntimeError(
            "The agent cycle did not create an execution report."
        )

    return execution


def step_execution_from_dict(
    data: dict[str, Any],
) -> StepExecution:
    return StepExecution(
        step_id=data.get(
            "step_id",
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
        step_type=data.get(
            "step_type",
            "reason",
        ),
        status=data.get(
            "status",
            "pending",
        ),
        started_at=data.get(
            "started_at",
            "",
        ),
        completed_at=data.get(
            "completed_at"
        ),
        output=data.get(
            "output",
            "",
        ),
        error=data.get(
            "error"
        ),
        metadata=data.get(
            "metadata",
            {},
        ),
    )


def execution_report_from_dict(
    data: dict[str, Any],
) -> PlanExecutionReport:
    raw_steps = data.get(
        "steps",
        [],
    )

    steps = [
        step_execution_from_dict(
            item
        )
        for item in raw_steps
        if isinstance(
            item,
            dict,
        )
    ]

    return PlanExecutionReport(
        id=data.get(
            "id",
            "",
        ),
        plan_id=data.get(
            "plan_id",
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
        status=data.get(
            "status",
            "pending",
        ),
        started_at=data.get(
            "started_at",
            "",
        ),
        completed_at=data.get(
            "completed_at"
        ),
        steps=steps,
        final_output=data.get(
            "final_output",
            "",
        ),
        error=data.get(
            "error"
        ),
        metadata=data.get(
            "metadata",
            {},
        ),
    )

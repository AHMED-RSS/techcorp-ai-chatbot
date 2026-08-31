from __future__ import annotations

import json
import os
import uuid

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.executor import (
    PlanExecutionReport,
    StepExecution,
    execution_report_from_dict,
)
from agents.planner import (
    AgentPlan,
    PlanStep,
)
from config.settings import Settings
from core.exceptions import (
    AgentExecutionError,
    FileProcessingError,
    SkillError,
    ToolExecutionError,
)
from core.logging_config import (
    get_logger,
)
from core.providers import (
    AIProvider,
)
from services.planner_service import (
    PlannerService,
)
from services.rag_service import (
    RAGService,
    SearchResult,
)
from services.skill_service import (
    Skill,
    SkillService,
)
from services.tool_service import (
    ToolService,
)


logger = get_logger(__name__)


ProgressCallback = Callable[
    [
        PlanExecutionReport,
        PlanStep,
        str,
    ],
    None,
]

StopCallback = Callable[
    [],
    bool,
]


class ExecutorService:
    """
    Executes AgentPlan steps sequentially.

    Step outputs are carried into later steps as local context.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        ai_provider: AIProvider,
        planner_service: PlannerService,
        rag_service: RAGService,
        skill_service: SkillService,
        tool_service: ToolService,
    ) -> None:
        self.settings = settings
        self.ai = ai_provider
        self.planner = planner_service
        self.rag = rag_service
        self.skills = skill_service
        self.tools = tool_service

        self.execution_folder = (
            settings.agent_run_folder
        )

        self.execution_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

    def execute_plan(
        self,
        *,
        plan: AgentPlan,
        model: str,
        document_ids: list[str],
        conversation_messages: (
            list[dict[str, str]]
            | None
        ) = None,
        progress_callback: (
            ProgressCallback
            | None
        ) = None,
        stop_callback: (
            StopCallback
            | None
        ) = None,
        continue_on_error: bool = False,
    ) -> PlanExecutionReport:
        timestamp = self._utc_now()

        report = PlanExecutionReport(
            id=str(
                uuid.uuid4()
            ),
            plan_id=plan.id,
            user_request=(
                plan.user_request
            ),
            goal=plan.goal,
            status="running",
            started_at=timestamp,
            completed_at=None,
            steps=[],
            final_output="",
            error=None,
            model=model,
            metadata={
                "document_ids": list(
                    document_ids
                ),
                "continue_on_error": (
                    continue_on_error
                ),
            },
        )

        plan.status = "running"

        self.planner.save_plan(
            plan
        )

        self.save_report(
            report
        )

        completed_outputs: dict[
            str,
            str,
        ] = {}

        all_sources: list[
            dict[str, Any]
        ] = []

        try:
            for step in plan.steps:
                if (
                    stop_callback is not None
                    and stop_callback()
                ):
                    self._mark_remaining_stopped(
                        plan=plan,
                        report=report,
                    )

                    report.status = "stopped"
                    report.error = (
                        "Execution was stopped "
                        "by the user."
                    )

                    plan.status = "stopped"

                    break

                unmet_dependencies = [
                    dependency
                    for dependency in (
                        step.depends_on
                    )
                    if dependency
                    not in completed_outputs
                ]

                if unmet_dependencies:
                    step.status = "skipped"
                    step.error = (
                        "Dependencies were not "
                        "completed: "
                        + ", ".join(
                            unmet_dependencies
                        )
                    )

                    report.steps.append(
                        StepExecution(
                            step_id=step.id,
                            order=step.order,
                            title=step.title,
                            step_type=(
                                step.step_type
                            ),
                            status="stopped",
                            started_at=(
                                self._utc_now()
                            ),
                            completed_at=(
                                self._utc_now()
                            ),
                            output="",
                            error=step.error,
                        )
                    )

                    self.planner.save_plan(
                        plan
                    )

                    self.save_report(
                        report
                    )

                    continue

                step.status = "running"
                step.error = None

                step_execution = (
                    StepExecution(
                        step_id=step.id,
                        order=step.order,
                        title=step.title,
                        step_type=(
                            step.step_type
                        ),
                        status="running",
                        started_at=(
                            self._utc_now()
                        ),
                    )
                )

                report.steps.append(
                    step_execution
                )

                self.planner.save_plan(
                    plan
                )

                self.save_report(
                    report
                )

                if progress_callback:
                    progress_callback(
                        report,
                        step,
                        "running",
                    )

                try:
                    output, metadata = (
                        self._execute_step(
                            plan=plan,
                            step=step,
                            model=model,
                            document_ids=(
                                document_ids
                            ),
                            completed_outputs=(
                                completed_outputs
                            ),
                            conversation_messages=(
                                conversation_messages
                                or []
                            ),
                        )
                    )

                    step.status = "completed"
                    step.result = output
                    step.error = None

                    step_execution.status = (
                        "completed"
                    )

                    step_execution.output = (
                        output
                    )

                    step_execution.completed_at = (
                        self._utc_now()
                    )

                    step_execution.metadata = (
                        metadata
                    )

                    tool_result = metadata.get(
                        "tool_result"
                    )

                    if isinstance(
                        tool_result,
                        dict,
                    ):
                        step_execution.tool_result = (
                            tool_result
                        )

                    document_sources = (
                        metadata.get(
                            "document_sources",
                            [],
                        )
                    )

                    if isinstance(
                        document_sources,
                        list,
                    ):
                        step_execution.document_sources = (
                            document_sources
                        )

                        all_sources.extend(
                            document_sources
                        )

                    completed_outputs[
                        step.id
                    ] = output

                    if progress_callback:
                        progress_callback(
                            report,
                            step,
                            "completed",
                        )

                except Exception as exc:
                    error_text = str(
                        exc
                    )

                    logger.exception(
                        "Plan step failed: %s",
                        step.id,
                    )

                    step.status = "failed"
                    step.error = error_text

                    step_execution.status = (
                        "failed"
                    )

                    step_execution.error = (
                        error_text
                    )

                    step_execution.completed_at = (
                        self._utc_now()
                    )

                    if progress_callback:
                        progress_callback(
                            report,
                            step,
                            "failed",
                        )

                    if not continue_on_error:
                        report.status = "failed"
                        report.error = (
                            f"Step {step.order} failed: "
                            f"{error_text}"
                        )

                        plan.status = "failed"

                        self._mark_pending_steps_skipped(
                            plan=plan,
                            failed_step=step,
                        )

                        break

                finally:
                    self.planner.save_plan(
                        plan
                    )

                    self.save_report(
                        report
                    )

            if report.status == "running":
                failed_steps = [
                    step
                    for step in report.steps
                    if step.status == "failed"
                ]

                if failed_steps:
                    report.status = "failed"
                    plan.status = "failed"

                else:
                    report.status = "completed"
                    plan.status = "completed"

            report.final_output = (
                self._select_final_output(
                    report
                )
            )

            report.completed_at = (
                self._utc_now()
            )

            report.metadata[
                "document_sources"
            ] = self._deduplicate_sources(
                all_sources
            )

            self.planner.save_plan(
                plan
            )

            self.save_report(
                report
            )

            return report

        except Exception as exc:
            report.status = "failed"
            report.error = str(
                exc
            )

            report.completed_at = (
                self._utc_now()
            )

            plan.status = "failed"

            self.planner.save_plan(
                plan
            )

            self.save_report(
                report
            )

            if isinstance(
                exc,
                AgentExecutionError,
            ):
                raise

            raise AgentExecutionError(
                f"Plan execution failed: {exc}"
            ) from exc

    def _execute_step(
        self,
        *,
        plan: AgentPlan,
        step: PlanStep,
        model: str,
        document_ids: list[str],
        completed_outputs: dict[str, str],
        conversation_messages: list[
            dict[str, str]
        ],
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
        if (
            step.step_type
            == "document_search"
        ):
            return self._execute_document_step(
                plan=plan,
                step=step,
                document_ids=document_ids,
            )

        if step.step_type == "tool":
            return self._execute_tool_step(
                step
            )

        if step.step_type in {
            "reason",
            "write",
            "review",
        }:
            return self._execute_model_step(
                plan=plan,
                step=step,
                model=model,
                document_ids=document_ids,
                completed_outputs=(
                    completed_outputs
                ),
                conversation_messages=(
                    conversation_messages
                ),
            )

        raise AgentExecutionError(
            f"Unsupported step type: "
            f"{step.step_type}"
        )

    def _execute_document_step(
        self,
        *,
        plan: AgentPlan,
        step: PlanStep,
        document_ids: list[str],
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
        if not document_ids:
            raise AgentExecutionError(
                "This step requires selected "
                "documents, but none are selected."
            )

        query = (
            step.description.strip()
            or step.title.strip()
            or plan.user_request
        )

        results = self.rag.search(
            query=query,
            document_ids=document_ids,
            top_k=6,
        )

        sources = [
            result.to_dict()
            for result in results
        ]

        if not results:
            output = (
                "No relevant passages were found "
                "in the selected documents."
            )

        else:
            output = self.rag.build_context(
                results,
                maximum_characters=18_000,
            )

        return (
            output,
            {
                "query": query,
                "result_count": len(
                    results
                ),
                "document_sources": (
                    sources
                ),
            },
        )

    def _execute_tool_step(
        self,
        step: PlanStep,
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
        if not step.tool_name:
            raise ToolExecutionError(
                "The tool step has no tool name."
            )

        result = self.tools.execute(
            step.tool_name,
            step.tool_arguments,
        )

        if not result.success:
            raise ToolExecutionError(
                result.error
                or result.content
                or (
                    f"Tool '{step.tool_name}' "
                    "failed."
                )
            )

        return (
            result.content,
            {
                "tool_result": (
                    result.to_dict()
                )
            },
        )

    def _execute_model_step(
        self,
        *,
        plan: AgentPlan,
        step: PlanStep,
        model: str,
        document_ids: list[str],
        completed_outputs: dict[str, str],
        conversation_messages: list[
            dict[str, str]
        ],
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
        skill = self._resolve_step_skill(
            plan=plan,
            step=step,
        )

        dependency_context = (
            self._build_dependency_context(
                step=step,
                completed_outputs=(
                    completed_outputs
                ),
            )
        )

        all_previous_context = (
            self._build_previous_context(
                completed_outputs
            )
        )

        document_sources: list[
            dict[str, Any]
        ] = []

        document_context = ""

        if (
            step.use_documents
            and document_ids
        ):
            search_query = (
                f"{plan.user_request}\n\n"
                f"Current step: "
                f"{step.description}"
            )

            search_results = (
                self.rag.search(
                    query=search_query,
                    document_ids=(
                        document_ids
                    ),
                    top_k=6,
                )
            )

            document_sources = [
                result.to_dict()
                for result in search_results
            ]

            document_context = (
                self.rag.build_context(
                    search_results,
                    maximum_characters=(
                        16_000
                    ),
                )
            )

        skill_prompt = (
            self.skills
            .build_skill_prompt(
                skill
            )
        )

        step_instruction = (
            self._step_instruction(
                step
            )
        )

        system_prompt = f"""
You are executing one step of a local multi-step
agent plan.

PLAN GOAL:
{plan.goal}

ORIGINAL USER REQUEST:
{plan.user_request}

CURRENT STEP:
- Number: {step.order}
- Title: {step.title}
- Type: {step.step_type}
- Route: {step.route}
- Description: {step.description}

{skill_prompt}

STEP-SPECIFIC INSTRUCTION:
{step_instruction}

RULES:
- Complete only the current step.
- Use completed-step outputs as working context.
- Do not claim that a tool was used unless tool output
  appears in the supplied completed-step context.
- Do not claim document retrieval unless document
  sources are supplied.
- Cite document source labels such as [Source 1] when
  making document-based claims.
- Do not claim internet access.
- Return a useful step result that later steps can use.
""".strip()

        messages: list[
            dict[str, str]
        ] = []

        messages.extend(
            conversation_messages[-8:]
        )

        if all_previous_context:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "COMPLETED PLAN STEP OUTPUTS\n\n"
                        f"{all_previous_context}"
                    ),
                }
            )

        if dependency_context:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "DIRECT DEPENDENCY OUTPUTS\n\n"
                        f"{dependency_context}"
                    ),
                }
            )

        if document_context:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "LOCAL DOCUMENT SOURCES\n\n"
                        f"{document_context}"
                    ),
                }
            )

        messages.append(
            {
                "role": "user",
                "content": (
                    "Execute the current plan step."
                ),
            }
        )

        output = self.ai.chat(
            messages=messages,
            model=model,
            temperature=(
                self.settings
                .agent_default_temperature
            ),
            system_prompt=system_prompt,
        )

        return (
            output,
            {
                "skill": {
                    "slug": skill.slug,
                    "name": skill.name,
                    "icon": skill.icon,
                },
                "document_sources": (
                    document_sources
                ),
            },
        )

    def _resolve_step_skill(
        self,
        *,
        plan: AgentPlan,
        step: PlanStep,
    ) -> Skill:
        selected_slug = (
            step.skill_slug
            or plan.recommended_skill
            or "general_assistant"
        )

        skill = self.skills.load_skill(
            selected_slug
        )

        if (
            skill is None
            or not skill.enabled
        ):
            skill = self.skills.load_skill(
                "general_assistant"
            )

        if skill is None:
            enabled_skills = (
                self.skills.enabled_skills()
            )

            if not enabled_skills:
                raise SkillError(
                    "No enabled skills are available."
                )

            skill = enabled_skills[0]

        return skill

    @staticmethod
    def _step_instruction(
        step: PlanStep,
    ) -> str:
        if step.step_type == "reason":
            return (
                "Analyse the problem and produce "
                "reasoned findings for later steps."
            )

        if step.step_type == "write":
            return (
                "Create the requested draft or final "
                "content using the available context."
            )

        if step.step_type == "review":
            return (
                "Review the existing output for correctness, "
                "completeness, clarity and unsupported claims. "
                "Return an improved final version rather than "
                "only listing criticisms."
            )

        return (
            "Complete the current step accurately."
        )

    @staticmethod
    def _build_dependency_context(
        *,
        step: PlanStep,
        completed_outputs: dict[str, str],
    ) -> str:
        sections: list[str] = []

        for dependency in step.depends_on:
            output = completed_outputs.get(
                dependency
            )

            if output:
                sections.append(
                    f"[{dependency}]\n{output}"
                )

        return "\n\n---\n\n".join(
            sections
        )

    @staticmethod
    def _build_previous_context(
        completed_outputs: dict[str, str],
    ) -> str:
        sections: list[str] = []

        for step_id, output in (
            completed_outputs.items()
        ):
            if output:
                sections.append(
                    f"[{step_id}]\n{output}"
                )

        context = "\n\n---\n\n".join(
            sections
        )

        return context[-30_000:]

    @staticmethod
    def _select_final_output(
        report: PlanExecutionReport,
    ) -> str:
        preferred_types = (
            "review",
            "write",
            "reason",
            "tool",
            "document_search",
        )

        for step_type in preferred_types:
            matching = [
                step
                for step in report.steps
                if (
                    step.status
                    == "completed"
                    and step.step_type
                    == step_type
                    and step.output.strip()
                )
            ]

            if matching:
                return matching[-1].output.strip()

        return ""

    def save_report(
        self,
        report: PlanExecutionReport,
    ) -> PlanExecutionReport:
        path = self.report_path(
            report.id
        )

        temporary_path = path.with_suffix(
            ".json.tmp"
        )

        try:
            temporary_path.write_text(
                json.dumps(
                    report.to_dict(),
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            os.replace(
                temporary_path,
                path,
            )

        except OSError as exc:
            raise AgentExecutionError(
                f"Could not save execution "
                f"report: {exc}"
            ) from exc

        return report

    def load_report(
        self,
        report_id: str,
    ) -> PlanExecutionReport | None:
        path = self.report_path(
            report_id
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
            raise AgentExecutionError(
                f"Could not load execution "
                f"report: {exc}"
            ) from exc

        if not isinstance(
            raw,
            dict,
        ):
            raise AgentExecutionError(
                "Execution report is invalid."
            )

        return execution_report_from_dict(
            raw
        )

    def list_reports(
        self,
        limit: int = 50,
    ) -> list[
        PlanExecutionReport
    ]:
        reports: list[
            PlanExecutionReport
        ] = []

        for path in (
            self.execution_folder.glob(
                "execution_*.json"
            )
        ):
            try:
                raw = json.loads(
                    path.read_text(
                        encoding="utf-8",
                    )
                )

                if isinstance(
                    raw,
                    dict,
                ):
                    reports.append(
                        execution_report_from_dict(
                            raw
                        )
                    )

            except Exception:
                logger.warning(
                    "Skipping invalid execution "
                    "report: %s",
                    path.name,
                )

        reports.sort(
            key=lambda report: (
                report.started_at
            ),
            reverse=True,
        )

        return reports[
            :max(1, limit)
        ]

    def delete_report(
        self,
        report_id: str,
    ) -> bool:
        path = self.report_path(
            report_id
        )

        if not path.exists():
            return False

        try:
            path.unlink()
            return True

        except OSError as exc:
            raise AgentExecutionError(
                f"Could not delete execution "
                f"report: {exc}"
            ) from exc

    def report_path(
        self,
        report_id: str,
    ) -> Path:
        safe_id = "".join(
            character
            for character in str(
                report_id
            )
            if (
                character.isalnum()
                or character
                in {
                    "-",
                    "_",
                }
            )
        )

        if not safe_id:
            raise AgentExecutionError(
                "Invalid execution report ID."
            )

        return (
            self.execution_folder
            / f"execution_{safe_id}.json"
        )

    @staticmethod
    def _mark_pending_steps_skipped(
        *,
        plan: AgentPlan,
        failed_step: PlanStep,
    ) -> None:
        for step in plan.steps:
            if (
                step.order
                > failed_step.order
                and step.status
                == "pending"
            ):
                step.status = "skipped"
                step.error = (
                    "Skipped because an earlier "
                    "step failed."
                )

    @staticmethod
    def _mark_remaining_stopped(
        *,
        plan: AgentPlan,
        report: PlanExecutionReport,
    ) -> None:
        completed_ids = {
            execution.step_id
            for execution in report.steps
        }

        for step in plan.steps:
            if step.id in completed_ids:
                continue

            if step.status == "pending":
                step.status = "skipped"
                step.error = (
                    "Skipped because execution "
                    "was stopped."
                )

    @staticmethod
    def _deduplicate_sources(
        sources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        result: list[
            dict[str, Any]
        ] = []

        seen_ids: set[str] = set()

        for source in sources:
            source_id = str(
                source.get(
                    "chunk_id",
                    "",
                )
            )

            if (
                source_id
                and source_id in seen_ids
            ):
                continue

            if source_id:
                seen_ids.add(
                    source_id
                )

            result.append(
                source
            )

        return result

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat(
            timespec="seconds"
        )

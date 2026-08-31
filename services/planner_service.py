from __future__ import annotations

import json
import os
import re
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.planner import (
    AgentPlan,
    PlanStep,
    agent_plan_from_dict,
)
from agents.router import (
    RouteDecision,
)
from config.settings import Settings
from core.exceptions import (
    PlanningError,
)
from core.logging_config import (
    get_logger,
)
from core.providers import (
    AIProvider,
)
from services.skill_service import (
    SkillService,
)
from services.tool_service import (
    ToolService,
)


logger = get_logger(__name__)


PLANNER_SYSTEM_PROMPT = """
You are the planning component of a local Agentic AI application.

Your task is to decide whether the user's request needs a multi-step plan.
When it does, produce a concise, practical and executable plan.

Return exactly one JSON object with these fields:

{
  "requires_plan": true,
  "goal": "clear final objective",
  "summary": "short explanation of the approach",
  "confidence": 0.0,
  "route": "general | document | code | study | tool",
  "recommended_skill": "skill slug or null",
  "use_documents": false,
  "assumptions": [],
  "success_criteria": [],
  "steps": [
    {
      "id": "step_1",
      "order": 1,
      "title": "short step title",
      "description": "what this step accomplishes",
      "step_type": "reason | document_search | tool | write | review",
      "route": "general | document | code | study | tool",
      "skill_slug": "skill slug or null",
      "tool_name": "available tool name or null",
      "tool_arguments": {},
      "use_documents": false,
      "depends_on": []
    }
  ]
}

Planning rules:

1. Return only JSON. Do not use Markdown.
2. Use between 2 and 8 steps for requests requiring a plan.
3. Do not create unnecessary plans for simple questions.
4. Set requires_plan to false for a request that can be answered directly.
5. Never invent tools or skills.
6. A tool step must use an available tool name.
7. Use document_search only when selected documents are available.
8. Steps must be ordered and have unique IDs.
9. Dependencies may only reference earlier step IDs.
10. Keep the plan concise and directly related to the user request.
11. Do not execute the plan.
12. Do not answer the user's request.
""".strip()


class PlannerService:
    """
    Creates and stores local agent plans.

    Planning uses the configured AI provider with deterministic
    fallback behaviour.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        ai_provider: AIProvider,
        skill_service: SkillService,
        tool_service: ToolService,
    ) -> None:
        self.settings = settings
        self.ai = ai_provider
        self.skills = skill_service
        self.tools = tool_service

        self.plan_folder = (
            settings.task_folder
        )

        self.plan_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

    def should_plan(
        self,
        prompt: str,
    ) -> bool:
        cleaned = str(
            prompt or ""
        ).strip().lower()

        if not cleaned:
            return False

        explicit_phrases = (
            "make a plan",
            "create a plan",
            "plan this",
            "step by step",
            "steps to",
            "roadmap",
            "strategy",
            "project plan",
            "implementation plan",
            "action plan",
            "research plan",
            "study plan",
            "migration plan",
            "build a",
            "develop a",
            "design a",
            "compare and recommend",
            "analyse and report",
            "analyze and report",
        )

        if any(
            phrase in cleaned
            for phrase in explicit_phrases
        ):
            return True

        conjunction_count = sum(
            cleaned.count(
                conjunction
            )
            for conjunction in (
                " and ",
                " then ",
                " after that ",
                " followed by ",
            )
        )

        if conjunction_count >= 2:
            return True

        if len(cleaned) >= 350:
            return True

        return False

    def create_plan(
        self,
        *,
        prompt: str,
        route: RouteDecision,
        has_documents: bool,
        model: str | None = None,
        force_plan: bool = False,
    ) -> AgentPlan:
        cleaned_prompt = str(
            prompt or ""
        ).strip()

        if not cleaned_prompt:
            raise PlanningError(
                "Cannot create a plan for an empty request."
            )

        plan_required = (
            force_plan
            or self.should_plan(
                cleaned_prompt
            )
        )

        if not plan_required:
            plan = self._direct_plan(
                prompt=cleaned_prompt,
                route=route,
            )

            self.save_plan(
                plan
            )

            return plan

        try:
            plan = self._model_plan(
                prompt=cleaned_prompt,
                route=route,
                has_documents=has_documents,
                model=model,
            )

        except Exception as exc:
            logger.warning(
                "Planner model failed; using fallback plan: %s",
                exc,
            )

            plan = self._fallback_plan(
                prompt=cleaned_prompt,
                route=route,
                has_documents=has_documents,
            )

        self.validate_plan(
            plan,
            has_documents=has_documents,
        )

        self.save_plan(
            plan
        )

        return plan

    def _model_plan(
        self,
        *,
        prompt: str,
        route: RouteDecision,
        has_documents: bool,
        model: str | None,
    ) -> AgentPlan:
        available_tools = (
            self.tools.public_schemas()
        )

        available_skills = [
            {
                "slug": skill.slug,
                "name": skill.name,
                "description": (
                    skill.description
                ),
            }
            for skill in (
                self.skills.enabled_skills()
            )
        ]

        context = {
            "user_request": prompt,
            "router_decision": (
                route.to_dict()
            ),
            "selected_documents_available": (
                has_documents
            ),
            "maximum_steps": (
                self.settings
                .agent_max_steps
            ),
            "available_tools": (
                available_tools
            ),
            "available_skills": (
                available_skills
            ),
        }

        response = self.ai.chat(
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(
                        context,
                        indent=2,
                        ensure_ascii=False,
                    ),
                }
            ],
            model=(
                model
                or self.settings
                .ollama_chat_model
            ),
            temperature=0.1,
            system_prompt=(
                PLANNER_SYSTEM_PROMPT
            ),
            response_format="json",
        )

        parsed = self._parse_json(
            response
        )

        timestamp = self._utc_now()

        parsed["id"] = str(
            uuid.uuid4()
        )

        parsed["user_request"] = (
            prompt
        )

        parsed["created_at"] = (
            timestamp
        )

        parsed["updated_at"] = (
            timestamp
        )

        parsed["status"] = "planned"
        parsed["source"] = "ai_provider"

        plan = agent_plan_from_dict(
            parsed
        )

        if (
            len(plan.steps)
            > self.settings.agent_max_steps
        ):
            plan.steps = plan.steps[
                : self.settings.agent_max_steps
            ]

        return plan

    def _direct_plan(
        self,
        *,
        prompt: str,
        route: RouteDecision,
    ) -> AgentPlan:
        timestamp = self._utc_now()

        step_type = "reason"

        if route.route == "tool":
            step_type = "tool"

        elif route.route == "document":
            step_type = "document_search"

        elif route.route in {
            "code",
            "study",
        }:
            step_type = "write"

        step = PlanStep(
            id="step_1",
            order=1,
            title="Complete the request",
            description=(
                "Respond directly using the selected "
                "route, skill and available context."
            ),
            step_type=step_type,
            route=route.route,
            skill_slug=(
                route.recommended_skill
            ),
            tool_name=route.tool_name,
            tool_arguments=(
                route.tool_arguments
            ),
            use_documents=(
                route.use_documents
            ),
        )

        return AgentPlan(
            id=str(
                uuid.uuid4()
            ),
            user_request=prompt,
            goal=prompt,
            summary=(
                "The request can be completed directly "
                "without a multi-step plan."
            ),
            requires_plan=False,
            confidence=1.0,
            route=route.route,
            recommended_skill=(
                route.recommended_skill
            ),
            use_documents=(
                route.use_documents
            ),
            steps=[step],
            assumptions=[],
            success_criteria=[
                "The response directly addresses the request.",
            ],
            status="planned",
            created_at=timestamp,
            updated_at=timestamp,
            source="direct",
        )

    def _fallback_plan(
        self,
        *,
        prompt: str,
        route: RouteDecision,
        has_documents: bool,
    ) -> AgentPlan:
        timestamp = self._utc_now()

        steps: list[PlanStep] = []

        current_order = 1

        if (
            has_documents
            and (
                route.use_documents
                or route.route
                in {
                    "document",
                    "study",
                }
            )
        ):
            steps.append(
                PlanStep(
                    id=(
                        f"step_{current_order}"
                    ),
                    order=current_order,
                    title=(
                        "Retrieve relevant document context"
                    ),
                    description=(
                        "Search the selected local documents "
                        "for information relevant to the request."
                    ),
                    step_type="document_search",
                    route="document",
                    skill_slug=(
                        "document_analyst"
                    ),
                    use_documents=True,
                )
            )

            current_order += 1

        if (
            route.route == "tool"
            and route.tool_name
        ):
            dependencies = (
                [
                    f"step_{current_order - 1}"
                ]
                if current_order > 1
                else []
            )

            steps.append(
                PlanStep(
                    id=(
                        f"step_{current_order}"
                    ),
                    order=current_order,
                    title=(
                        f"Run {route.tool_name}"
                    ),
                    description=(
                        "Execute the selected local tool "
                        "using the prepared arguments."
                    ),
                    step_type="tool",
                    route="tool",
                    skill_slug=(
                        route.recommended_skill
                    ),
                    tool_name=(
                        route.tool_name
                    ),
                    tool_arguments=(
                        route.tool_arguments
                    ),
                    use_documents=False,
                    depends_on=dependencies,
                )
            )

            current_order += 1

        dependencies = (
            [
                f"step_{current_order - 1}"
            ]
            if current_order > 1
            else []
        )

        steps.append(
            PlanStep(
                id=f"step_{current_order}",
                order=current_order,
                title="Produce the requested result",
                description=(
                    "Use the available evidence, active skill "
                    "and any tool output to create the response."
                ),
                step_type="write",
                route=route.route,
                skill_slug=(
                    route.recommended_skill
                ),
                use_documents=(
                    route.use_documents
                ),
                depends_on=dependencies,
            )
        )

        current_order += 1

        steps.append(
            PlanStep(
                id=f"step_{current_order}",
                order=current_order,
                title="Review the result",
                description=(
                    "Check that the response addresses the "
                    "goal, follows the selected skill and does "
                    "not claim unsupported tool or document use."
                ),
                step_type="review",
                route=route.route,
                skill_slug=(
                    route.recommended_skill
                ),
                use_documents=False,
                depends_on=[
                    f"step_{current_order - 1}"
                ],
            )
        )

        return AgentPlan(
            id=str(
                uuid.uuid4()
            ),
            user_request=prompt,
            goal=prompt,
            summary=(
                "Fallback plan generated from the "
                "router decision."
            ),
            requires_plan=True,
            confidence=0.65,
            route=route.route,
            recommended_skill=(
                route.recommended_skill
            ),
            use_documents=(
                route.use_documents
            ),
            steps=steps,
            assumptions=[
                (
                    "The available local tools and selected "
                    "documents are sufficient for the request."
                )
            ],
            success_criteria=[
                "The final result addresses the user request.",
                "Any document-based claims are grounded.",
                "Any tool result is represented accurately.",
            ],
            status="planned",
            created_at=timestamp,
            updated_at=timestamp,
            source="fallback",
        )

    def validate_plan(
        self,
        plan: AgentPlan,
        *,
        has_documents: bool,
    ) -> None:
        if not plan.id:
            raise PlanningError(
                "Plan does not have an identifier."
            )

        if not plan.goal:
            raise PlanningError(
                "Plan does not have a goal."
            )

        if not plan.steps:
            raise PlanningError(
                "Plan does not contain any steps."
            )

        if (
            len(plan.steps)
            > self.settings.agent_max_steps
        ):
            raise PlanningError(
                "Plan exceeds the configured "
                "maximum number of steps."
            )

        seen_ids: set[str] = set()
        previous_ids: set[str] = set()

        enabled_skill_slugs = {
            skill.slug
            for skill in (
                self.skills.enabled_skills()
            )
        }

        for expected_order, step in enumerate(
            plan.steps,
            start=1,
        ):
            step.order = expected_order

            if step.id in seen_ids:
                step.id = (
                    f"step_{expected_order}"
                )

            seen_ids.add(
                step.id
            )

            step.depends_on = [
                dependency
                for dependency in (
                    step.depends_on
                )
                if dependency in previous_ids
            ]

            previous_ids.add(
                step.id
            )

            if (
                step.use_documents
                and not has_documents
            ):
                step.use_documents = False

            if (
                step.step_type
                == "document_search"
                and not has_documents
            ):
                step.step_type = "reason"
                step.route = "general"
                step.description = (
                    "Proceed without document retrieval "
                    "because no selected documents are available."
                )

            if step.skill_slug:
                if (
                    step.skill_slug
                    not in enabled_skill_slugs
                ):
                    step.skill_slug = (
                        plan.recommended_skill
                    )

            if step.step_type == "tool":
                if (
                    not step.tool_name
                    or not self.tools.has_tool(
                        step.tool_name
                    )
                ):
                    step.step_type = "reason"
                    step.route = "general"
                    step.tool_name = None
                    step.tool_arguments = {}

    def save_plan(
        self,
        plan: AgentPlan,
    ) -> AgentPlan:
        plan.updated_at = (
            self._utc_now()
        )

        path = self.plan_path(
            plan.id
        )

        temporary_path = path.with_suffix(
            ".json.tmp"
        )

        try:
            temporary_path.write_text(
                json.dumps(
                    plan.to_dict(),
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
            raise PlanningError(
                f"Could not save plan: {exc}"
            ) from exc

        return plan

    def load_plan(
        self,
        plan_id: str,
    ) -> AgentPlan | None:
        path = self.plan_path(
            plan_id
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
            raise PlanningError(
                f"Could not load plan: {exc}"
            ) from exc

        if not isinstance(
            raw,
            dict,
        ):
            raise PlanningError(
                "Stored plan is invalid."
            )

        return agent_plan_from_dict(
            raw
        )

    def list_plans(
        self,
        limit: int = 50,
    ) -> list[AgentPlan]:
        plans: list[AgentPlan] = []

        for path in self.plan_folder.glob(
            "*.json"
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
                    plans.append(
                        agent_plan_from_dict(
                            raw
                        )
                    )

            except Exception:
                logger.warning(
                    "Skipping invalid plan file: %s",
                    path.name,
                )

        plans.sort(
            key=lambda plan: (
                plan.updated_at
            ),
            reverse=True,
        )

        return plans[
            : max(1, limit)
        ]

    def delete_plan(
        self,
        plan_id: str,
    ) -> bool:
        path = self.plan_path(
            plan_id
        )

        if not path.exists():
            return False

        try:
            path.unlink()
            return True

        except OSError as exc:
            raise PlanningError(
                f"Could not delete plan: {exc}"
            ) from exc

    def plan_path(
        self,
        plan_id: str,
    ) -> Path:
        safe_id = re.sub(
            r"[^a-zA-Z0-9_-]",
            "",
            str(plan_id),
        )

        if not safe_id:
            raise PlanningError(
                "Invalid plan identifier."
            )

        return (
            self.plan_folder
            / f"{safe_id}.json"
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
                raise PlanningError(
                    "Planner did not return valid JSON."
                )

            parsed = json.loads(
                match.group(0)
            )

        if not isinstance(
            parsed,
            dict,
        ):
            raise PlanningError(
                "Planner response must be a JSON object."
            )

        return parsed

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat(
            timespec="seconds"
        )


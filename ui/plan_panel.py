from __future__ import annotations

from typing import Any

import streamlit as st

from agents.planner import (
    AgentPlan,
)
from core.exceptions import (
    PlanningError,
)
from services.planner_service import (
    PlannerService,
)
from ui.components import (
    render_section_label,
)


STEP_ICONS = {
    "reason": "🧠",
    "document_search": "📚",
    "tool": "⚙️",
    "write": "✍️",
    "review": "🔎",
}


STATUS_ICONS = {
    "pending": "○",
    "running": "◉",
    "completed": "✓",
    "failed": "×",
    "skipped": "–",
}


def render_plan(
    plan: AgentPlan,
    *,
    expanded: bool = True,
) -> None:
    with st.expander(
        (
            f"Agent plan · "
            f"{plan.step_count} step(s)"
        ),
        expanded=expanded,
    ):
        st.markdown(
            f"### Goal\n{plan.goal}"
        )

        if plan.summary:
            st.caption(
                plan.summary
            )

        metrics = st.columns(
            4,
            gap="small",
        )

        with metrics[0]:
            st.metric(
                "Steps",
                plan.step_count,
            )

        with metrics[1]:
            st.metric(
                "Route",
                plan.route.title(),
            )

        with metrics[2]:
            st.metric(
                "Confidence",
                f"{plan.confidence:.0%}",
            )

        with metrics[3]:
            st.metric(
                "Source",
                plan.source.title(),
            )

        if not plan.requires_plan:
            st.info(
                "This request can be completed directly."
            )

        st.markdown(
            "#### Steps"
        )

        for step in plan.steps:
            icon = STEP_ICONS.get(
                step.step_type,
                "•",
            )

            status_icon = (
                STATUS_ICONS.get(
                    step.status,
                    "○",
                )
            )

            with st.container(
                border=True
            ):
                st.markdown(
                    f"**{status_icon} "
                    f"{step.order}. {icon} "
                    f"{step.title}**"
                )

                if step.description:
                    st.write(
                        step.description
                    )

                details: list[str] = [
                    f"Type: {step.step_type}",
                    f"Route: {step.route}",
                ]

                if step.skill_slug:
                    details.append(
                        f"Skill: {step.skill_slug}"
                    )

                if step.tool_name:
                    details.append(
                        f"Tool: {step.tool_name}"
                    )

                if step.use_documents:
                    details.append(
                        "Documents: yes"
                    )

                st.caption(
                    " · ".join(details)
                )

                if step.depends_on:
                    st.caption(
                        "Depends on: "
                        + ", ".join(
                            step.depends_on
                        )
                    )

                if step.tool_arguments:
                    with st.expander(
                        "Tool arguments",
                        expanded=False,
                    ):
                        st.json(
                            step.tool_arguments
                        )

                if step.result:
                    st.success(
                        step.result
                    )

                if step.error:
                    st.error(
                        step.error
                    )

        if plan.assumptions:
            st.markdown(
                "#### Assumptions"
            )

            for assumption in (
                plan.assumptions
            ):
                st.markdown(
                    f"- {assumption}"
                )

        if plan.success_criteria:
            st.markdown(
                "#### Success criteria"
            )

            for criterion in (
                plan.success_criteria
            ):
                st.markdown(
                    f"- {criterion}"
                )


def render_plan_sidebar(
    planner_service: PlannerService,
) -> None:
    with st.sidebar:
        render_section_label(
            "Planning"
        )

        st.toggle(
            "Automatic planning",
            key="automatic_planning_enabled",
            help=(
                "Create a local multi-step plan "
                "for complex requests."
            ),
        )

        st.toggle(
            "Always create a plan",
            key="force_planning",
            disabled=(
                not st.session_state
                .automatic_planning_enabled
            ),
            help=(
                "Force planning even for requests "
                "that appear simple."
            ),
        )

        current_plan = (
            st.session_state.current_plan
        )

        if isinstance(
            current_plan,
            dict,
        ):
            st.caption(
                "Current plan: "
                f"{len(current_plan.get('steps', []))} "
                "step(s)"
            )

        with st.expander(
            "Recent plans",
            expanded=False,
        ):
            try:
                plans = (
                    planner_service.list_plans(
                        limit=10
                    )
                )

            except PlanningError as exc:
                st.error(str(exc))
                plans = []

            if not plans:
                st.caption(
                    "No saved plans."
                )

            for plan in plans:
                st.markdown(
                    f"**{plan.goal[:70]}**"
                )

                st.caption(
                    f"{plan.step_count} steps · "
                    f"{plan.created_at}"
                )

                if st.button(
                    "Open",
                    key=(
                        f"open_plan_"
                        f"{plan.id}"
                    ),
                    use_container_width=True,
                ):
                    st.session_state.current_plan = (
                        plan.to_dict()
                    )

                    st.session_state.current_task_id = (
                        plan.id
                    )

                    st.rerun()


def render_planning_workspace(
    planner_service: PlannerService,
) -> None:
    st.markdown(
        "## Agent plans"
    )

    st.caption(
        "Plans are created and stored locally."
    )

    current_plan_data = (
        st.session_state.current_plan
    )

    plans = planner_service.list_plans(
        limit=50
    )

    if isinstance(
        current_plan_data,
        dict,
    ):
        from agents.planner import (
            agent_plan_from_dict,
        )

        current_plan = (
            agent_plan_from_dict(
                current_plan_data
            )
        )

        render_plan(
            current_plan,
            expanded=True,
        )

        st.divider()

    if not plans:
        st.info(
            "No saved agent plans are available."
        )

        return

    st.markdown(
        "### Saved plans"
    )

    for plan in plans:
        with st.container(
            border=True
        ):
            columns = st.columns(
                [5, 1, 1],
                gap="small",
            )

            with columns[0]:
                st.markdown(
                    f"**{plan.goal}**"
                )

                st.caption(
                    f"{plan.step_count} step(s) · "
                    f"{plan.route.title()} · "
                    f"{plan.source}"
                )

            with columns[1]:
                if st.button(
                    "Open",
                    key=(
                        f"workspace_open_plan_"
                        f"{plan.id}"
                    ),
                    use_container_width=True,
                ):
                    st.session_state.current_plan = (
                        plan.to_dict()
                    )

                    st.session_state.current_task_id = (
                        plan.id
                    )

                    st.rerun()

            with columns[2]:
                if st.button(
                    "Delete",
                    key=(
                        f"delete_plan_"
                        f"{plan.id}"
                    ),
                    use_container_width=True,
                ):
                    try:
                        planner_service.delete_plan(
                            plan.id
                        )

                        if (
                            st.session_state
                            .current_task_id
                            == plan.id
                        ):
                            st.session_state.current_plan = (
                                []
                            )

                            st.session_state.current_task_id = (
                                None
                            )

                        st.toast(
                            "Plan deleted"
                        )

                        st.rerun()

                    except PlanningError as exc:
                        st.error(str(exc))


def serialise_plan(
    plan: AgentPlan,
) -> dict[str, Any]:
    return plan.to_dict()
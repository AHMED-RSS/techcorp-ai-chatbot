from __future__ import annotations

import streamlit as st

from agents.executor import (
    PlanExecutionReport,
    execution_report_from_dict,
)
from core.exceptions import (
    AgentExecutionError,
)
from services.executor_service import (
    ExecutorService,
)
from ui.components import (
    render_section_label,
)


STATUS_ICONS = {
    "pending": "○",
    "running": "◉",
    "completed": "✓",
    "failed": "×",
    "stopped": "■",
}


STEP_ICONS = {
    "reason": "🧠",
    "document_search": "📚",
    "tool": "⚙️",
    "write": "✍️",
    "review": "🔎",
}


def render_execution_report(
    report: PlanExecutionReport,
    *,
    expanded: bool = True,
) -> None:
    status_icon = STATUS_ICONS.get(
        report.status,
        "○",
    )

    with st.expander(
        (
            f"{status_icon} Plan execution · "
            f"{report.status.title()}"
        ),
        expanded=expanded,
    ):
        st.markdown(
            f"### {report.goal}"
        )

        progress_value = max(
            0.0,
            min(
                1.0,
                report.progress,
            ),
        )

        st.progress(
            progress_value,
            text=(
                f"{report.completed_step_count} "
                f"of {len(report.steps)} "
                "recorded step(s) completed"
            ),
        )

        metrics = st.columns(
            4,
            gap="small",
        )

        with metrics[0]:
            st.metric(
                "Status",
                report.status.title(),
            )

        with metrics[1]:
            st.metric(
                "Completed",
                report.completed_step_count,
            )

        with metrics[2]:
            st.metric(
                "Failed",
                report.failed_step_count,
            )

        with metrics[3]:
            st.metric(
                "Model",
                report.model or "Unknown",
            )

        for step in report.steps:
            icon = STEP_ICONS.get(
                step.step_type,
                "•",
            )

            step_status_icon = (
                STATUS_ICONS.get(
                    step.status,
                    "○",
                )
            )

            with st.container(
                border=True
            ):
                st.markdown(
                    f"**{step_status_icon} "
                    f"{step.order}. {icon} "
                    f"{step.title}**"
                )

                st.caption(
                    f"Type: {step.step_type} · "
                    f"Status: {step.status}"
                )

                if step.output:
                    output = step.output

                    if len(output) > 2_500:
                        output = (
                            output[:2_500]
                            + "…"
                        )

                    st.markdown(
                        output
                    )

                if step.error:
                    st.error(
                        step.error
                    )

                if step.tool_result:
                    with st.expander(
                        "Tool result",
                        expanded=False,
                    ):
                        st.json(
                            step.tool_result
                        )

                if step.document_sources:
                    with st.expander(
                        (
                            "Document sources "
                            f"({len(step.document_sources)})"
                        ),
                        expanded=False,
                    ):
                        for source in (
                            step.document_sources
                        ):
                            st.markdown(
                                "**"
                                + str(
                                    source.get(
                                        "document_title",
                                        "Untitled",
                                    )
                                )
                                + "**"
                            )

                            st.caption(
                                str(
                                    source.get(
                                        "original_name",
                                        "",
                                    )
                                )
                            )

        if report.final_output:
            st.markdown(
                "### Final output"
            )

            st.markdown(
                report.final_output
            )

        if report.error:
            st.error(
                report.error
            )


def render_execution_sidebar(
    executor_service: ExecutorService,
) -> None:
    with st.sidebar:
        with st.expander(
            "Execution",
            expanded=False,
        ):

            st.toggle(
            "Execute plans automatically",
            key="automatic_plan_execution",
            help=(
                "Run generated plan steps sequentially "
                "and pass results between steps."
            ),
        )

        st.toggle(
            "Continue after step errors",
            key="continue_execution_on_error",
            disabled=(
                not st.session_state
                .automatic_plan_execution
            ),
            help=(
                "Continue later steps when one plan "
                "step fails."
            ),
        )

        current_execution = (
            st.session_state
            .current_execution
        )

        if isinstance(
            current_execution,
            dict,
        ):
            status = current_execution.get(
                "status",
                "unknown",
            )

            completed = sum(
                1
                for step in current_execution.get(
                    "steps",
                    [],
                )
                if step.get(
                    "status"
                )
                == "completed"
            )

            st.caption(
                f"Current execution: "
                f"{status.title()} · "
                f"{completed} completed step(s)"
            )

        with st.expander(
            "Recent executions",
            expanded=False,
        ):
            try:
                reports = (
                    executor_service
                    .list_reports(
                        limit=10
                    )
                )

            except AgentExecutionError as exc:
                st.error(
                    str(exc)
                )
                reports = []

            if not reports:
                st.caption(
                    "No execution reports."
                )

            for report in reports:
                status_icon = (
                    STATUS_ICONS.get(
                        report.status,
                        "○",
                    )
                )

                st.markdown(
                    f"**{status_icon} "
                    f"{report.goal[:65]}**"
                )

                st.caption(
                    f"{report.status.title()} · "
                    f"{report.completed_step_count} "
                    "completed"
                )

                if st.button(
                    "Open execution",
                    key=(
                        "open_execution_"
                        f"{report.id}"
                    ),
                    use_container_width=True,
                ):
                    st.session_state.current_execution = (
                        report.to_dict()
                    )

                    st.session_state.current_execution_id = (
                        report.id
                    )

                    st.rerun()


def render_execution_workspace(
    executor_service: ExecutorService,
) -> None:
    st.markdown(
        "## Agent executions"
    )

    st.caption(
        "Execution reports are stored locally."
    )

    current_data = (
        st.session_state
        .current_execution
    )

    if isinstance(
        current_data,
        dict,
    ):
        current_report = (
            execution_report_from_dict(
                current_data
            )
        )

        render_execution_report(
            current_report,
            expanded=True,
        )

        st.divider()

    reports = (
        executor_service.list_reports(
            limit=50
        )
    )

    if not reports:
        st.info(
            "No saved plan executions."
        )
        return

    st.markdown(
        "### Saved executions"
    )

    for report in reports:
        status_icon = STATUS_ICONS.get(
            report.status,
            "○",
        )

        with st.container(
            border=True
        ):
            columns = st.columns(
                [5, 1, 1],
                gap="small",
            )

            with columns[0]:
                st.markdown(
                    f"**{status_icon} "
                    f"{report.goal}**"
                )

                st.caption(
                    f"{report.status.title()} · "
                    f"{report.completed_step_count} "
                    "completed · "
                    f"{report.started_at}"
                )

            with columns[1]:
                if st.button(
                    "Open",
                    key=(
                        "workspace_open_execution_"
                        f"{report.id}"
                    ),
                    use_container_width=True,
                ):
                    st.session_state.current_execution = (
                        report.to_dict()
                    )

                    st.session_state.current_execution_id = (
                        report.id
                    )

                    st.rerun()

            with columns[2]:
                if st.button(
                    "Delete",
                    key=(
                        "delete_execution_"
                        f"{report.id}"
                    ),
                    use_container_width=True,
                ):
                    try:
                        executor_service.delete_report(
                            report.id
                        )

                        if (
                            st.session_state
                            .current_execution_id
                            == report.id
                        ):
                            st.session_state.current_execution = (
                                None
                            )

                            st.session_state.current_execution_id = (
                                None
                            )

                        st.toast(
                            "Execution deleted"
                        )

                        st.rerun()

                    except AgentExecutionError as exc:
                        st.error(
                            str(exc)
                        )
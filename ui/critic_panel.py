from __future__ import annotations

import streamlit as st

from agents.critic import (
    CriticReport,
    critic_report_from_dict,
)
from core.exceptions import (
    CriticError,
)
from services.critic_service import (
    CriticService,
)
from ui.components import (
    render_section_label,
)


SEVERITY_ICONS = {
    "info": "ℹ️",
    "warning": "⚠️",
    "error": "❌",
    "critical": "🚨",
}


def render_critic_report(
    report: CriticReport,
    *,
    expanded: bool = False,
) -> None:
    status_icon = (
        "✅"
        if report.passed
        else "⚠️"
    )

    with st.expander(
        (
            f"{status_icon} Quality review · "
            f"{report.score:.0%}"
        ),
        expanded=expanded,
    ):
        metric_columns = st.columns(
            4,
            gap="small",
        )

        with metric_columns[0]:
            st.metric(
                "Score",
                f"{report.score:.0%}",
            )

        with metric_columns[1]:
            st.metric(
                "Passed",
                (
                    "Yes"
                    if report.passed
                    else "No"
                ),
            )

        with metric_columns[2]:
            st.metric(
                "Errors",
                report.error_count,
            )

        with metric_columns[3]:
            st.metric(
                "Warnings",
                report.warning_count,
            )

        if report.summary:
            st.write(
                report.summary
            )

        if report.strengths:
            st.markdown(
                "#### Strengths"
            )

            for strength in (
                report.strengths
            ):
                st.markdown(
                    f"- {strength}"
                )

        if report.findings:
            st.markdown(
                "#### Findings"
            )

            for finding in (
                report.findings
            ):
                icon = SEVERITY_ICONS.get(
                    finding.severity,
                    "•",
                )

                with st.container(
                    border=True
                ):
                    st.markdown(
                        f"**{icon} "
                        f"{finding.category.title()} · "
                        f"{finding.severity.title()}**"
                    )

                    st.write(
                        finding.message
                    )

                    if finding.recommendation:
                        st.caption(
                            "Recommendation: "
                            f"{finding.recommendation}"
                        )

                    if finding.evidence:
                        st.caption(
                            "Evidence: "
                            f"{finding.evidence}"
                        )

        else:
            st.success(
                "No material issues were identified."
            )

        if report.revised_output:
            st.markdown(
                "#### Revised answer"
            )

            st.markdown(
                report.revised_output
            )

        st.caption(
            f"Review source: {report.source} · "
            f"Model: {report.model or 'Unknown'}"
        )


def render_critic_sidebar(
    critic_service: CriticService,
) -> None:
    with st.sidebar:
        render_section_label(
            "Quality critic"
        )

        st.toggle(
            "Review answers automatically",
            key="automatic_critic_enabled",
            help=(
                "Use the local Ollama critic to check "
                "the final answer before saving it."
            ),
        )

        st.toggle(
            "Automatically apply revisions",
            key="automatic_critic_revision",
            disabled=(
                not st.session_state
                .automatic_critic_enabled
            ),
            help=(
                "Replace a failed answer with the "
                "critic's improved version."
            ),
        )

        threshold = st.slider(
            "Minimum quality score",
            min_value=0.0,
            max_value=1.0,
            value=float(
                st.session_state
                .critic_minimum_score
            ),
            step=0.05,
            disabled=(
                not st.session_state
                .automatic_critic_enabled
            ),
            key="critic_score_slider",
        )

        st.session_state.critic_minimum_score = (
            threshold
        )

        current_report = (
            st.session_state.current_critic_report
        )

        if isinstance(
            current_report,
            dict,
        ):
            st.caption(
                "Last review: "
                f"{float(current_report.get('score', 0)):.0%} · "
                + (
                    "Passed"
                    if current_report.get(
                        "passed",
                        False,
                    )
                    else "Needs attention"
                )
            )

        with st.expander(
            "Recent reviews",
            expanded=False,
        ):
            try:
                reports = (
                    critic_service.list_reports(
                        limit=10
                    )
                )

            except CriticError as exc:
                st.error(
                    str(exc)
                )
                reports = []

            if not reports:
                st.caption(
                    "No critic reports."
                )

            for report in reports:
                icon = (
                    "✅"
                    if report.passed
                    else "⚠️"
                )

                st.markdown(
                    f"**{icon} "
                    f"{report.user_request[:60]}**"
                )

                st.caption(
                    f"{report.score:.0%} · "
                    f"{report.created_at}"
                )

                if st.button(
                    "Open review",
                    key=(
                        "sidebar_open_critic_"
                        f"{report.id}"
                    ),
                    use_container_width=True,
                ):
                    st.session_state.current_critic_report = (
                        report.to_dict()
                    )

                    st.session_state.current_critic_report_id = (
                        report.id
                    )

                    st.rerun()


def render_critic_workspace(
    critic_service: CriticService,
) -> None:
    st.markdown(
        "## Quality reviews"
    )

    st.caption(
        "Critic reports are generated and stored locally."
    )

    current_data = (
        st.session_state.current_critic_report
    )

    if isinstance(
        current_data,
        dict,
    ):
        current_report = (
            critic_report_from_dict(
                current_data
            )
        )

        render_critic_report(
            current_report,
            expanded=True,
        )

        st.divider()

    try:
        reports = (
            critic_service.list_reports(
                limit=50
            )
        )

    except CriticError as exc:
        st.error(
            str(exc)
        )
        return

    if not reports:
        st.info(
            "No saved quality reviews."
        )
        return

    st.markdown(
        "### Saved reviews"
    )

    for report in reports:
        icon = (
            "✅"
            if report.passed
            else "⚠️"
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
                    f"**{icon} "
                    f"{report.user_request}**"
                )

                st.caption(
                    f"Score {report.score:.0%} · "
                    f"{len(report.findings)} finding(s) · "
                    f"{report.created_at}"
                )

            with columns[1]:
                if st.button(
                    "Open",
                    key=(
                        "workspace_open_critic_"
                        f"{report.id}"
                    ),
                    use_container_width=True,
                ):
                    st.session_state.current_critic_report = (
                        report.to_dict()
                    )

                    st.session_state.current_critic_report_id = (
                        report.id
                    )

                    st.rerun()

            with columns[2]:
                if st.button(
                    "Delete",
                    key=(
                        "delete_critic_report_"
                        f"{report.id}"
                    ),
                    use_container_width=True,
                ):
                    try:
                        critic_service.delete_report(
                            report.id
                        )

                        if (
                            st.session_state
                            .current_critic_report_id
                            == report.id
                        ):
                            st.session_state.current_critic_report = (
                                None
                            )

                            st.session_state.current_critic_report_id = (
                                None
                            )

                        st.toast(
                            "Review deleted"
                        )

                        st.rerun()

                    except CriticError as exc:
                        st.error(
                            str(exc)
                        )
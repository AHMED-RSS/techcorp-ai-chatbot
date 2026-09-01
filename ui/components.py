from __future__ import annotations

from html import escape
from textwrap import dedent
from typing import Literal

import streamlit as st


BadgeStatus = Literal[
    "success",
    "warning",
    "error",
    "info",
]


def render_html(
    html: str,
) -> None:
    """
    Render a custom HTML fragment safely through Streamlit.

    Streamlit's Markdown parser can terminate HTML blocks when
    blank lines appear between nested elements. Compacting the
    fragment prevents the remaining tags from appearing as text.
    """

    compact_html = " ".join(
        line.strip()
        for line in dedent(
            html
        ).splitlines()
        if line.strip()
    )

    st.markdown(
        compact_html,
        unsafe_allow_html=True,
    )


def render_brand(
    name: str,
    subtitle: str,
) -> None:
    render_html(
        f"""
        <div class="tc-brand">
            <div class="tc-brand-logo">&#9673;</div>
            <div class="tc-brand-copy">
                <div class="tc-brand-title">{escape(name)}</div>
                <div class="tc-brand-subtitle">{escape(subtitle)}</div>
            </div>
        </div>
        """
    )


def render_page_header(
    title: str,
    subtitle: str,
) -> None:
    render_html(
        f"""
        <div class="tc-page-header">
            <h1 class="tc-page-title">{escape(title)}</h1>
            <div class="tc-page-subtitle">{escape(subtitle)}</div>
        </div>
        """
    )


def render_section_label(
    label: str,
) -> None:
    render_html(
        f"""
        <div class="tc-section-label">{escape(label)}</div>
        """
    )


def render_badge(
    text: str,
    status: BadgeStatus = "info",
) -> None:
    valid_statuses = {
        "success",
        "warning",
        "error",
        "info",
    }

    safe_status = (
        status
        if status in valid_statuses
        else "info"
    )

    render_html(
        f"""
        <span class="tc-badge tc-badge-{safe_status}">
            <span class="tc-badge-dot"></span>
            <span>{escape(text)}</span>
        </span>
        """
    )


def render_badge_row(
    badges: list[tuple[str, BadgeStatus]],
) -> None:
    html = """
    <div class="tc-badge-row">
    """

    for text, status in badges:
        html += f"""
        <span class="tc-badge tc-badge-{status}">
            <span class="tc-badge-dot"></span>
            <span>{escape(text)}</span>
        </span>&nbsp;
        """

    html += """
    </div>
    """

    render_html(html)


def render_agent_panel(
    agent_name: str,
    model_name: str,
    reasoning_mode: str,
    document_count: int,
    ollama_connected: bool,
) -> None:
    connection_text = (
        "Connected"
        if ollama_connected
        else "Offline"
    )

    connection_status = (
        "success"
        if ollama_connected
        else "error"
    )

    render_html(
        f"""
        <div class="tc-agent-panel">
            <div class="tc-agent-row">
                <span class="tc-agent-label">Active agent</span>
                <span class="tc-agent-value">{escape(agent_name)}</span>
            </div>
            <div class="tc-agent-row">
                <span class="tc-agent-label">Model</span>
                <span class="tc-agent-value">{escape(model_name)}</span>
            </div>
            <div class="tc-agent-row">
                <span class="tc-agent-label">Reasoning</span>
                <span class="tc-agent-value">
                    {escape(reasoning_mode.title())}
                </span>
            </div>
            <div class="tc-agent-row">
                <span class="tc-agent-label">Documents</span>
                <span class="tc-agent-value">{int(document_count)}</span>
            </div>
            <div class="tc-agent-status">
                <span class="tc-badge tc-badge-{connection_status}">
                    <span class="tc-badge-dot"></span>
                    <span>Ollama {connection_text}</span>
                </span>
            </div>
        </div>
        """
    )


def render_empty_chat() -> None:
    render_html(
        """
        <div class="tc-empty-state">
            <div class="tc-empty-icon">&#10022;</div>
            <h2 class="tc-empty-title">
                What would you like to accomplish?
            </h2>
            <div class="tc-empty-subtitle">
                Ask a question, analyse a document, prepare study
                materials, or let the agent build and execute a plan.
            </div>
            <div class="tc-feature-grid">
                <div class="tc-feature-card">


                    <div class="tc-feature-title">Deep reasoning</div>
                    <div class="tc-feature-text">
                        Break complex goals into structured,
                        executable steps.
                    </div>
                </div>
                <div class="tc-feature-card">


                    <div class="tc-feature-title">
                        Document intelligence
                    </div>
                    <div class="tc-feature-text">
                        Analyse local documents and answer using
                        relevant source content.
                    </div>
                </div>
                <div class="tc-feature-card">


                    <div class="tc-feature-title">Reusable skills</div>
                    <div class="tc-feature-text">
                        Apply specialised instructions for study,
                        research, writing and more.
                    </div>
                </div>
            </div>
        </div>
        """
    )


def render_information_card(
    title: str,
    description: str,
    icon: str = "&#8226;",
) -> None:
    render_html(
        f"""
        <div class="tc-card-soft">
            <div class="tc-card-title">
                <span class="tc-card-icon">{escape(icon)}</span>
                <span>{escape(title)}</span>
            </div>
            <div class="tc-card-description">
                {escape(description)}
            </div>
        </div>
        """
    )

def render_chat_message(
    role: str,
    content: str,
) -> None:
    safe_role = (
        "You"
        if role.lower() == "user"
        else "Assistant"
    )

    role_class = (
        "tc-message-user"
        if role.lower() == "user"
        else "tc-message-assistant"
    )

    render_html(
        f"""
        <div class="tc-message {role_class}">
            <div class="tc-message-header">
                {escape(safe_role)}
            </div>
            <div class="tc-message-body">
                {escape(content)}
            </div>
        </div>
        """
    )


def render_agent_timeline(
    steps: list[dict[str, str]],
) -> None:
    items = ""

    for step in steps:
        status = step.get(
            "status",
            "pending",
        )

        title = step.get(
            "title",
            "Step",
        )

        status_class = (
            f"tc-agent-step-{status}"
        )

        icon = (
            "✓"
            if status == "completed"
            else "●"
            if status == "active"
            else "○"
        )

        items += f"""
        <div class="tc-agent-step {status_class}">
            <span class="tc-agent-step-dot">
                {icon}
            </span>
            <span>{escape(title)}</span>
        </div>
        """

    render_html(
        f"""
        <div class="tc-agent-status-card">
            {items}
        </div>
        """
    )


def render_card(
    title: str,
    body: str,
) -> None:
    render_html(
        f"""
        <div class="tc-card">
            <div class="tc-card-title">
                {escape(title)}
            </div>
            <div class="tc-card-description">
                {escape(body)}
            </div>
        </div>
        """
    )

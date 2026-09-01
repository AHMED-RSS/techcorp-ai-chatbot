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

def _split_response_sections(
    content: str,
) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []

    current_title = "Overview"
    current_body: list[str] = []

    for line in content.splitlines():
        clean = line.strip()

        is_heading = (
            clean.startswith("##")
            or (
                len(clean) > 2
                and clean[0].isdigit()
                and clean[1] == "."
            )
            or (
                clean.startswith("**")
                and clean.endswith("**")
            )
        )

        if is_heading:
            if current_body:
                sections.append(
                    (
                        current_title,
                        "\n".join(current_body).strip(),
                    )
                )

            current_title = (
                clean
                .replace("#", "")
                .replace("*", "")
                .strip()
            )

            current_body = []

        else:
            current_body.append(line)

    if current_body:
        sections.append(
            (
                current_title,
                "\n".join(current_body).strip(),
            )
        )

    return sections



def render_response_summary(
    summary: str,
) -> None:
    render_html(
        f"""
        <div class="tc-response-summary">
            <div class="tc-response-summary-title">
                Summary
            </div>

            <div class="tc-response-summary-text">
                {escape(summary)}
            </div>
        </div>
        """
    )



def render_response_actions(
    metadata: dict,
    content: str = "",
) -> None:

    sources = True

    html = """
    <div class="tc-response-actions">
        <span>Quick actions</span>
    </div>
    """

    render_html(
        html
    )

    columns = st.columns(
        4,
        gap="small",
    )

    action_id = id(metadata)

    with columns[0]:
        if st.button(
            "[S] Sources",
            key=f"response_sources_{action_id}",
        ):
            st.session_state.show_sources = True

    with columns[1]:
        if st.button(
            "[M] Save Memory",
            key=f"response_save_memory_{action_id}",
        ):
            st.session_state.memory_capture_content = content
            st.session_state.memory_capture_requested = True

    with columns[2]:
        if st.button(
            "[P] Create Plan",
            key=f"response_create_plan_{action_id}",
        ):
            st.session_state.plan_response_content = content
            st.session_state.plan_from_response = True

    with columns[3]:
        if st.button(
            "[+] Explain More",
            key=f"response_explain_more_{action_id}",
        ):
            st.session_state.explain_response = True


def inject_citations(
    text: str,
    web_sources: list[dict],
    document_sources: list[dict],
) -> str:

    import re


    def replace(match):

        label = match.group(1)


        if label.startswith("Web"):

            try:
                index = int(
                    label.split()[1]
                ) - 1

                if index < len(web_sources):

                    source = web_sources[index]

                    url = str(
                        source.get(
                            "url",
                            "",
                        )
                    )

                    title = str(
                        source.get(
                            "title",
                            label,
                        )
                    )

                    if url:
                        return (
                            f'<a class="tc-citation-badge" '
                            f'href="{escape(url)}" '
                            'target="_blank" '
                            'rel="noopener noreferrer">'
                            f'🔗 Web {index + 1}'
                            '</a>'
                        )

            except Exception:
                pass


        if label.startswith("Source"):

            try:
                index = int(
                    label.split()[1]
                ) - 1

                if index < len(document_sources):

                    return str(
                        document_sources[index].get(
                            "document_title",
                            label,
                        )
                    )

            except Exception:
                pass


        return label


    return re.sub(
        r"\[(Web \d+|Source \d+)\]",
        replace,
        text,
    )



def render_chat_message(
    role: str,
    content: str,
    web_sources: list[dict] | None = None,
    document_sources: list[dict] | None = None,
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

    if role.lower() == "assistant":

        summary = (
            content
            .strip()
            .split("\n", 1)[0]
            .strip()
        )

        if not summary:
            summary = (
                "Assistant generated a structured response."
            )

        if len(summary) > 220:
            summary = (
                summary[:220]
                + "..."
            )

        render_response_summary(
            summary
        )

        sections = _split_response_sections(
            content
        )

        body = ""

        render_html(
            f"""
            <div class="tc-message {role_class}">
                <div class="tc-message-header">
                    {escape(safe_role)}
                </div>

                <div class="tc-response-card">
            """
        )


        for title, section_text in sections:

            section_text = inject_citations(
                section_text,
                web_sources or [],
                document_sources or [],
            )

            st.markdown(
                f"""
### {title}

{section_text}

---
                """
            )


        render_html(
            """
                </div>
            </div>
            """
        )

        return

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


def render_activity_panel(
    status: str,
) -> None:

    labels = {
        "preparing": (
            "Preparing request",
            "active",
        ),
        "searching_web": (
            "Searching web",
            "active",
        ),
        "routing": (
            "Selecting route",
            "active",
        ),
        "planning": (
            "Creating plan",
            "active",
        ),
        "executing": (
            "Executing tools",
            "active",
        ),
        "generating": (
            "Generating response",
            "active",
        ),
        "reviewing": (
            "Quality review",
            "active",
        ),
        "completed": (
            "Completed",
            "success",
        ),
        "failed": (
            "Failed",
            "error",
        ),
    }


    title, state = labels.get(
        status,
        (
            status.title(),
            "info",
        ),
    )


    render_html(
        f"""
        <div class="tc-activity-panel">

            <div class="tc-card-title">
                AI Activity
            </div>

            <div class="tc-activity-item">
                <span class="tc-activity-dot tc-{state}">
                </span>

                <span>
                    {escape(title)}
                </span>
            </div>

        </div>
        """
    )




def render_source_panel(
    document_sources: list[dict],
    web_sources: list[dict],
) -> None:

    if not document_sources and not web_sources:
        return

    html = """
    <div class="tc-source-panel">

        <div class="tc-card-title">
            Sources Used
        </div>
    """

    if document_sources:
        html += """
        <div class="tc-source-section">
            <div class="tc-source-label">
                Documents
            </div>
        """

        for source in document_sources[:5]:
            title = str(
                source.get(
                    "document_title",
                    "Untitled",
                )
            )

            score = source.get(
                "relevance_score"
            )

            relevance = (
                f"{float(score):.0%}"
                if score is not None
                else "N/A"
            )

            html += f"""
            <div class="tc-source-item">
                <strong>{escape(title)}</strong>
                <span>
                    Relevance {escape(relevance)}
                </span>
            </div>
            """

        html += "</div>"


    if web_sources:
        html += """
        <div class="tc-source-section">
            <div class="tc-source-label">
                Web Sources
            </div>
        """

        for source in web_sources[:5]:
            title = str(
                source.get(
                    "title",
                    "Untitled result",
                )
            )

            url = str(
                source.get(
                    "url",
                    "",
                )
            )

            link_html = (
                f'<a href="{escape(url)}" '
                'target="_blank">'
                'Open source'
                '</a>'
                if url
                else "Link unavailable"
            )

            html += f"""
            <div class="tc-source-item">
                <strong>{escape(title)}</strong>

                <span>
                    {link_html}
                </span>

                <small>
                    Verified web result
                </small>
            </div>
            """

        html += "</div>"


    html += "</div>"

    render_html(html)




def render_ai_workspace_dashboard(
    agent_status: str,
    model_name: str,
    reasoning_mode: str,
    documents: int,
    sources: int,
    memories: int,
) -> None:

    cards = [
        (
            "Agent",
            f"{agent_status.title()} · {model_name}",
        ),
        (
            "Reasoning",
            reasoning_mode.title(),
        ),
        (
            "Knowledge",
            f"{documents} Documents · {sources} Sources",
        ),
        (
            "Memory",
            f"{memories} Stored",
        ),
    ]


    html = """
    <div class="tc-dashboard-grid">
    """


    for title, value in cards:
        html += f"""
        <div class="tc-dashboard-card">
            <div class="tc-dashboard-title">
                {escape(title)}
            </div>

            <div class="tc-dashboard-value">
                {escape(value)}
            </div>
        </div>
        """


    html += """
    </div>
    """


    render_html(html)




def render_context_memory(
    memories: int,
    tasks: int,
    persistent: bool,
    chat_memory: bool,
) -> None:

    rows = [
        (
            "Stored Memories",
            str(memories),
        ),
        (
            "Task States",
            str(tasks),
        ),
        (
            "Persistent Memory",
            "Enabled"
            if persistent
            else "Off",
        ),
        (
            "Chat Memory",
            "Enabled"
            if chat_memory
            else "Off",
        ),
    ]


    html = """
    <div class="tc-memory-card">

        <div class="tc-card-title">
            Context Memory
        </div>

        <div class="tc-memory-body">
    """


    for label, value in rows:
        html += f"""
        <div class="tc-memory-row">
            <span>{escape(label)}</span>
            <strong>{escape(value)}</strong>
        </div>
        """


    html += """
        </div>

    </div>
    """


    render_html(html)




def render_learning_workspace(
    title: str,
    study_type: str,
    documents: int,
    sources: int,
    flashcards: int,
    questions: int,
) -> None:

    rows = [
        ("Goal", title),
        ("Mode", study_type.title()),
        ("Documents", str(documents)),
        ("Sources", str(sources)),
        ("Flashcards", str(flashcards)),
        ("Quiz Questions", str(questions)),
    ]

    html = """
    <div class="tc-learning-card">

        <div class="tc-card-title">
            Learning Workspace
        </div>

        <div class="tc-learning-body">
    """

    for label, value in rows:
        html += f"""
        <div class="tc-learning-row">
            <span>{escape(label)}</span>
            <strong>{escape(value)}</strong>
        </div>
        """

    html += """
        </div>

    </div>
    """

    render_html(html)




def render_response_intelligence(
    route: str,
    confidence: str,
    quality: str,
    sources: int,
    documents_enabled: bool,
    web_enabled: bool,
    reasoning: str,
) -> None:

    rows = [
        ("Task", route),
        ("Confidence", confidence),
        ("Quality", quality),
        ("Sources", str(sources)),
        (
            "Documents",
            "Enabled"
            if documents_enabled
            else "Off",
        ),
        (
            "Web Search",
            "Enabled"
            if web_enabled
            else "Off",
        ),
        ("Reasoning", reasoning.title()),
    ]

    html = """
    <div class="tc-result-card">

        <div class="tc-card-title">
            Response Intelligence
        </div>

        <div class="tc-result-body">
    """

    for label, value in rows:
        html += f"""
        <div class="tc-result-row">
            <span>{escape(label)}</span>
            <strong>{escape(value)}</strong>
        </div>
        """

    html += """
        </div>

    </div>
    """

    render_html(html)




def render_result_summary_card(
    route: str | None = None,
    confidence: str | None = None,
    quality: str | None = None,
) -> None:
    rows = ""

    if route:
        rows += f"""
        <div class="tc-result-row">
            <span>Route</span>
            <strong>{escape(route)}</strong>
        </div>
        """

    if confidence:
        rows += f"""
        <div class="tc-result-row">
            <span>Confidence</span>
            <strong>{escape(confidence)}</strong>
        </div>
        """

    if quality:
        rows += f"""
        <div class="tc-result-row">
            <span>Quality</span>
            <strong>{escape(quality)}</strong>
        </div>
        """

    render_html(
        f"""
        <div class="tc-result-card">
            <div class="tc-card-title">
                Agent Result
            </div>

            <div class="tc-result-body">
                {rows}
            </div>
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

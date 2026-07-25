from __future__ import annotations

import json
from typing import Any

import streamlit as st

from core.exceptions import ToolExecutionError
from services.tool_service import ToolService
from ui.components import render_section_label


TOOL_PRESENTATION: dict[str, dict[str, str]] = {
    "list_skills": {
        "title": "List skills",
        "icon": "✦",
        "category": "Skills",
        "summary": (
            "Browse the local skills available to the agent."
        ),
    },
    "list_files": {
        "title": "Browse project files",
        "icon": "📁",
        "category": "Files",
        "summary": (
            "Inspect files and folders inside the local project."
        ),
    },
    "read_text_file": {
        "title": "Read a text file",
        "icon": "📄",
        "category": "Files",
        "summary": (
            "Open a local text or source-code file safely."
        ),
    },
    "search_documents": {
        "title": "Search documents",
        "icon": "🔎",
        "category": "Knowledge",
        "summary": (
            "Search indexed documents with local embeddings."
        ),
    },
    "save_report": {
        "title": "Save a report",
        "icon": "📝",
        "category": "Output",
        "summary": (
            "Save Markdown content as a local report."
        ),
    },
    "calculator": {
        "title": "Calculator",
        "icon": "🧮",
        "category": "Utility",
        "summary": (
            "Evaluate a mathematical expression safely."
        ),
    },
    "current_datetime": {
        "title": "Date and time",
        "icon": "🕒",
        "category": "Utility",
        "summary": (
            "Get the current local date and time."
        ),
    },
}


TYPE_LABELS = {
    "string": "Text",
    "integer": "Whole number",
    "number": "Number",
    "boolean": "On / off",
    "array": "List",
    "object": "Object",
}


def _tool_to_dict(
    tool: Any,
) -> dict[str, Any]:
    if isinstance(
        tool,
        dict,
    ):
        return dict(
            tool
        )

    to_dict = getattr(
        tool,
        "to_dict",
        None,
    )

    if callable(
        to_dict
    ):
        converted = to_dict()

        if isinstance(
            converted,
            dict,
        ):
            return converted

    model_dump = getattr(
        tool,
        "model_dump",
        None,
    )

    if callable(
        model_dump
    ):
        converted = model_dump()

        if isinstance(
            converted,
            dict,
        ):
            return converted

    result: dict[str, Any] = {}

    for attribute in (
        "name",
        "description",
        "parameters",
        "input_schema",
        "requires_confirmation",
        "safe",
    ):
        if hasattr(
            tool,
            attribute,
        ):
            result[attribute] = getattr(
                tool,
                attribute,
            )

    return result


def _registered_tools(
    tool_service: ToolService,
) -> list[dict[str, Any]]:
    candidate_attributes = (
        "list_tools",
        "public_schemas",
        "get_tools",
        "tools",
    )

    for attribute_name in (
        candidate_attributes
    ):
        value = getattr(
            tool_service,
            attribute_name,
            None,
        )

        if callable(
            value
        ):
            try:
                value = value()

            except TypeError:
                continue

        if isinstance(
            value,
            dict,
        ):
            tools: list[
                dict[str, Any]
            ] = []

            for name, definition in (
                value.items()
            ):
                tool_data = (
                    _tool_to_dict(
                        definition
                    )
                )

                tool_data.setdefault(
                    "name",
                    str(
                        name
                    ),
                )

                tools.append(
                    tool_data
                )

            return tools

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                _tool_to_dict(
                    tool
                )
                for tool in value
            ]

    private_registry = getattr(
        tool_service,
        "_tools",
        None,
    )

    if isinstance(
        private_registry,
        dict,
    ):
        tools: list[
            dict[str, Any]
        ] = []

        for name, definition in (
            private_registry.items()
        ):
            tool_data = (
                _tool_to_dict(
                    definition
                )
            )

            tool_data.setdefault(
                "name",
                str(
                    name
                ),
            )

            tools.append(
                tool_data
            )

        return tools

    return []


def _tool_name(
    tool: dict[str, Any],
) -> str:
    return str(
        tool.get(
            "name",
            "unnamed_tool",
        )
    ).strip()


def _tool_description(
    tool: dict[str, Any],
) -> str:
    return str(
        tool.get(
            "description",
            "No description is available.",
        )
    ).strip()


def _tool_schema(
    tool: dict[str, Any],
) -> dict[str, Any]:
    schema = (
        tool.get(
            "parameters"
        )
        or tool.get(
            "input_schema"
        )
        or tool.get(
            "schema"
        )
        or {}
    )

    return (
        schema
        if isinstance(
            schema,
            dict,
        )
        else {}
    )


def _tool_presentation(
    tool: dict[str, Any],
) -> dict[str, str]:
    name = _tool_name(
        tool
    )

    configured = (
        TOOL_PRESENTATION.get(
            name,
            {},
        )
    )

    fallback_title = (
        name.replace(
            "_",
            " ",
        ).title()
    )

    return {
        "title": configured.get(
            "title",
            fallback_title,
        ),
        "icon": configured.get(
            "icon",
            "⚙",
        ),
        "category": configured.get(
            "category",
            "Local tool",
        ),
        "summary": configured.get(
            "summary",
            _tool_description(
                tool
            ),
        ),
    }


def _parameter_rows(
    schema: dict[str, Any],
) -> list[dict[str, Any]]:
    properties = schema.get(
        "properties",
        {},
    )

    required_values = schema.get(
        "required",
        [],
    )

    required = {
        str(
            value
        )
        for value in required_values
        if str(
            value
        ).strip()
    }

    if not isinstance(
        properties,
        dict,
    ):
        return []

    rows: list[
        dict[str, Any]
    ] = []

    for name, definition in (
        properties.items()
    ):
        if not isinstance(
            definition,
            dict,
        ):
            definition = {}

        parameter_type = str(
            definition.get(
                "type",
                "string",
            )
        )

        item_type = ""

        items = definition.get(
            "items"
        )

        if isinstance(
            items,
            dict,
        ):
            item_type = str(
                items.get(
                    "type",
                    "",
                )
            )

        rows.append(
            {
                "name": str(
                    name
                ),
                "type": parameter_type,
                "item_type": item_type,
                "description": str(
                    definition.get(
                        "description",
                        "",
                    )
                ).strip(),
                "required": (
                    str(
                        name
                    )
                    in required
                ),
                "default": definition.get(
                    "default"
                ),
            }
        )

    return rows


def _friendly_type(
    parameter: dict[str, Any],
) -> str:
    parameter_type = str(
        parameter.get(
            "type",
            "string",
        )
    )

    label = TYPE_LABELS.get(
        parameter_type,
        parameter_type.title(),
    )

    item_type = str(
        parameter.get(
            "item_type",
            "",
        )
    )

    if (
        parameter_type == "array"
        and item_type
    ):
        item_label = (
            TYPE_LABELS.get(
                item_type,
                item_type.title(),
            )
        )

        label = (
            f"List of {item_label.lower()}"
        )

    return label


def _example_arguments(
    tool: dict[str, Any],
) -> dict[str, Any]:
    example_values: dict[
        str,
        dict[str, Any],
    ] = {
        "list_skills": {
            "include_disabled": False,
        },
        "list_files": {
            "folder": ".",
            "recursive": False,
            "max_results": 50,
        },
        "read_text_file": {
            "path": "README.md",
            "max_characters": 12000,
        },
        "search_documents": {
            "query": (
                "Summarise the main findings"
            ),
            "top_k": 5,
            "document_ids": [],
        },
        "save_report": {
            "title": "Research notes",
            "content": (
                "# Research notes\n\n"
                "Local report content."
            ),
        },
        "calculator": {
            "expression": (
                "(125 * 4) + 30"
            ),
        },
        "current_datetime": {
            "timezone": (
                "Europe/London"
            ),
        },
    }

    name = _tool_name(
        tool
    )

    if name in example_values:
        return example_values[
            name
        ]

    arguments: dict[
        str,
        Any,
    ] = {}

    for parameter in _parameter_rows(
        _tool_schema(
            tool
        )
    ):
        parameter_name = str(
            parameter["name"]
        )

        parameter_type = str(
            parameter["type"]
        )

        default = parameter.get(
            "default"
        )

        if default is not None:
            arguments[
                parameter_name
            ] = default

        elif parameter_type == "string":
            arguments[
                parameter_name
            ] = ""

        elif parameter_type == "integer":
            arguments[
                parameter_name
            ] = 1

        elif parameter_type == "number":
            arguments[
                parameter_name
            ] = 1.0

        elif parameter_type == "boolean":
            arguments[
                parameter_name
            ] = False

        elif parameter_type == "array":
            arguments[
                parameter_name
            ] = []

        elif parameter_type == "object":
            arguments[
                parameter_name
            ] = {}

    return arguments


def _recent_runs(
    tool_service: ToolService,
    *,
    limit: int = 30,
) -> list[dict[str, Any]]:
    method = getattr(
        tool_service,
        "list_recent_runs",
        None,
    )

    if not callable(
        method
    ):
        return []

    try:
        runs = method(
            limit=limit
        )

    except TypeError:
        runs = method()

    if not isinstance(
        runs,
        list,
    ):
        return []

    result: list[
        dict[str, Any]
    ] = []

    for run in runs[:limit]:
        if isinstance(
            run,
            dict,
        ):
            result.append(
                run
            )

        elif hasattr(
            run,
            "to_dict",
        ):
            converted = run.to_dict()

            if isinstance(
                converted,
                dict,
            ):
                result.append(
                    converted
                )

    return result


def render_parameter_list(
    tool: dict[str, Any],
) -> None:
    parameters = _parameter_rows(
        _tool_schema(
            tool
        )
    )

    if not parameters:
        st.caption(
            "This tool does not require any input."
        )
        return

    st.markdown(
        "**Inputs**"
    )

    for parameter in parameters:
        required = bool(
            parameter.get(
                "required"
            )
        )

        type_text = _friendly_type(
            parameter
        )

        name = str(
            parameter.get(
                "name",
                "",
            )
        )

        description = str(
            parameter.get(
                "description",
                "",
            )
        ).strip()

        with st.container(
            border=True
        ):
            columns = st.columns(
                [3, 2, 2],
                gap="small",
                vertical_alignment="center",
            )

            with columns[0]:
                st.markdown(
                    f"`{name}`"
                )

            with columns[1]:
                st.caption(
                    type_text
                )

            with columns[2]:
                if required:
                    st.markdown(
                        "🔴 **Required**"
                    )

                else:
                    st.markdown(
                        "⚪ Optional"
                    )

            if description:
                st.caption(
                    description
                )


def render_tool_result(
    result: Any,
    *,
    expanded: bool = True,
) -> None:
    if result is None:
        return

    if isinstance(
        result,
        dict,
    ):
        data = result

    elif hasattr(
        result,
        "to_dict",
    ):
        converted = result.to_dict()

        data = (
            converted
            if isinstance(
                converted,
                dict,
            )
            else {
                "content": str(
                    result
                )
            }
        )

    else:
        data = {
            "content": str(
                result
            )
        }

    tool_name = str(
        data.get(
            "tool_name"
        )
        or data.get(
            "name"
        )
        or "Tool result"
    )

    success = bool(
        data.get(
            "success",
            not bool(
                data.get(
                    "error"
                )
            ),
        )
    )

    icon = (
        "✅"
        if success
        else "❌"
    )

    with st.expander(
        f"{icon} {tool_name}",
        expanded=expanded,
    ):
        content = str(
            data.get(
                "content"
            )
            or data.get(
                "output"
            )
            or data.get(
                "result"
            )
            or ""
        ).strip()

        if content:
            st.markdown(
                content
            )

        error = data.get(
            "error"
        )

        if error:
            st.error(
                str(
                    error
                )
            )

        metadata = data.get(
            "metadata"
        )

        if isinstance(
            metadata,
            dict,
        ) and metadata:
            with st.expander(
                "Technical details",
                expanded=False,
            ):
                st.json(
                    metadata
                )


def render_tool_sidebar(
    tool_service: ToolService,
) -> None:
    tools = _registered_tools(
        tool_service
    )

    with st.sidebar:
        render_section_label(
            "Local tools"
        )

        st.caption(
            f"{len(tools)} local capabilities"
        )

        if not tools:
            st.info(
                "No tools are registered."
            )
            return

        with st.expander(
            "Available tools",
            expanded=False,
        ):
            for tool in tools:
                presentation = (
                    _tool_presentation(
                        tool
                    )
                )

                st.markdown(
                    f"{presentation['icon']} "
                    f"**{presentation['title']}**"
                )

                st.caption(
                    presentation[
                        "summary"
                    ]
                )

        if st.button(
            "Open tools workspace",
            key=(
                "open_tools_workspace"
            ),
            use_container_width=True,
        ):
            st.session_state.workspace = (
                "tools"
            )

            st.rerun()


def render_available_tool_card(
    tool: dict[str, Any],
) -> None:
    presentation = (
        _tool_presentation(
            tool
        )
    )

    tool_name = _tool_name(
        tool
    )

    description = (
        _tool_description(
            tool
        )
    )

    requires_confirmation = bool(
        tool.get(
            "requires_confirmation",
            False,
        )
    )

    with st.container(
        border=True
    ):
        heading_columns = st.columns(
            [5, 2],
            gap="small",
            vertical_alignment="center",
        )

        with heading_columns[0]:
            st.markdown(
                f"### {presentation['icon']} "
                f"{presentation['title']}"
            )

            st.caption(
                presentation[
                    "category"
                ]
            )

        with heading_columns[1]:
            if requires_confirmation:
                st.warning(
                    "Confirmation required",
                    icon="⚠️",
                )

            else:
                st.success(
                    "Ready",
                    icon="✅",
                )

        st.write(
            presentation[
                "summary"
            ]
        )

        if (
            description
            and description
            != presentation[
                "summary"
            ]
        ):
            st.caption(
                description
            )

        render_parameter_list(
            tool
        )

        footer_columns = st.columns(
            [3, 2],
            gap="small",
            vertical_alignment="center",
        )

        with footer_columns[0]:
            st.caption(
                f"Internal name: `{tool_name}`"
            )

        with footer_columns[1]:
            if st.button(
                "Use this tool",
                key=(
                    "select_tool_"
                    f"{tool_name}"
                ),
                use_container_width=True,
            ):
                st.session_state[
                    "manual_tool_name"
                ] = tool_name

                st.rerun()

        with st.expander(
            "Advanced schema",
            expanded=False,
        ):
            st.json(
                _tool_schema(
                    tool
                )
            )


def render_manual_tool_runner(
    tool_service: ToolService,
    tools: list[dict[str, Any]],
) -> None:
    tool_names = [
        _tool_name(
            tool
        )
        for tool in tools
    ]

    stored_name = str(
        st.session_state.get(
            "manual_tool_name",
            tool_names[0],
        )
    )

    if stored_name not in tool_names:
        stored_name = tool_names[0]

    selected_name = st.selectbox(
        "Choose a tool",
        options=tool_names,
        index=tool_names.index(
            stored_name
        ),
        format_func=lambda name: (
            f"{_tool_presentation(next(tool for tool in tools if _tool_name(tool) == name))['icon']} "
            f"{_tool_presentation(next(tool for tool in tools if _tool_name(tool) == name))['title']}"
        ),
        key="manual_tool_name",
    )

    selected_tool = next(
        tool
        for tool in tools
        if _tool_name(
            tool
        )
        == selected_name
    )

    presentation = (
        _tool_presentation(
            selected_tool
        )
    )

    with st.container(
        border=True
    ):
        st.markdown(
            f"### {presentation['icon']} "
            f"{presentation['title']}"
        )

        st.write(
            presentation[
                "summary"
            ]
        )

        render_parameter_list(
            selected_tool
        )

    example = _example_arguments(
        selected_tool
    )

    editor_key = (
        "manual_tool_arguments_"
        f"{selected_name}"
    )

    if editor_key not in (
        st.session_state
    ):
        st.session_state[
            editor_key
        ] = json.dumps(
            example,
            ensure_ascii=False,
            indent=2,
        )

    argument_text = st.text_area(
        "Tool inputs",
        key=editor_key,
        height=220,
        help=(
            "Enter the inputs as one JSON object. "
            "An editable example is provided."
        ),
    )

    action_columns = st.columns(
        [2, 1],
        gap="small",
    )

    with action_columns[1]:
        if st.button(
            "Reset example",
            key=(
                "reset_tool_example_"
                f"{selected_name}"
            ),
            use_container_width=True,
        ):
            st.session_state[
                editor_key
            ] = json.dumps(
                example,
                ensure_ascii=False,
                indent=2,
            )

            st.rerun()

    requires_confirmation = bool(
        selected_tool.get(
            "requires_confirmation",
            False,
        )
    )

    confirmed = True

    if requires_confirmation:
        confirmed = st.checkbox(
            "I confirm this local action",
            value=False,
            key=(
                "confirm_manual_tool_"
                f"{selected_name}"
            ),
        )

    with action_columns[0]:
        run_clicked = st.button(
            "Run tool",
            key=(
                "run_manual_tool_"
                f"{selected_name}"
            ),
            type="primary",
            use_container_width=True,
            disabled=(
                requires_confirmation
                and not confirmed
            ),
        )

    if not run_clicked:
        return

    try:
        arguments = json.loads(
            argument_text
            or "{}"
        )

        if not isinstance(
            arguments,
            dict,
        ):
            raise ToolExecutionError(
                "Tool inputs must be a JSON object."
            )

        with st.status(
            f"Running {presentation['title']}...",
            expanded=True,
        ) as status:
            result = (
                tool_service.execute(
                    selected_name,
                    arguments,
                )
            )

            status.update(
                label=(
                    f"{presentation['title']} completed"
                ),
                state="complete",
            )

        result_data = (
            result.to_dict()
            if hasattr(
                result,
                "to_dict",
            )
            else {
                "tool_name": (
                    selected_name
                ),
                "content": str(
                    result
                ),
                "success": True,
            }
        )

        st.session_state.last_tool_name = (
            selected_name
        )

        st.session_state.last_tool_arguments = (
            arguments
        )

        st.session_state.last_tool_result = (
            result_data
        )

        history = list(
            st.session_state.get(
                "tool_runs",
                [],
            )
        )

        history.append(
            result_data
        )

        st.session_state.tool_runs = (
            history[-50:]
        )

        st.session_state.tool_error = None

        render_tool_result(
            result_data,
            expanded=True,
        )

    except json.JSONDecodeError as exc:
        st.error(
            f"The tool inputs are not valid JSON: {exc}"
        )

    except (
        ToolExecutionError,
        ValueError,
        TypeError,
    ) as exc:
        st.session_state.tool_error = (
            str(
                exc
            )
        )

        st.error(
            str(
                exc
            )
        )

    except Exception as exc:
        st.session_state.tool_error = (
            str(
                exc
            )
        )

        st.error(
            f"Tool execution failed: {exc}"
        )


def render_tool_history(
    tool_service: ToolService,
) -> None:
    runs = _recent_runs(
        tool_service,
        limit=30,
    )

    if not runs:
        runs = [
            run
            for run in st.session_state.get(
                "tool_runs",
                [],
            )
            if isinstance(
                run,
                dict,
            )
        ][-30:]

    if not runs:
        st.info(
            "No tool runs have been recorded."
        )
        return

    st.metric(
        "Recorded runs",
        len(
            runs
        ),
    )

    for run in reversed(
        runs
    ):
        render_tool_result(
            run,
            expanded=False,
        )


def render_tool_workspace(
    tool_service: ToolService,
) -> None:
    st.markdown(
        "## Local tools"
    )

    st.caption(
        "Use focused local capabilities without sending "
        "your project data to a cloud AI service."
    )

    tools = _registered_tools(
        tool_service
    )

    if not tools:
        st.info(
            "No local tools are currently registered."
        )
        return

    category_count = len(
        {
            _tool_presentation(
                tool
            )["category"]
            for tool in tools
        }
    )

    metric_columns = st.columns(
        3,
        gap="small",
    )

    with metric_columns[0]:
        st.metric(
            "Tools",
            len(
                tools
            ),
        )

    with metric_columns[1]:
        st.metric(
            "Categories",
            category_count,
        )

    with metric_columns[2]:
        st.metric(
            "Local execution",
            "Enabled",
        )

    available_tab, run_tab, history_tab = (
        st.tabs(
            [
                "Browse",
                "Run a tool",
                "History",
            ]
        )
    )

    with available_tab:
        category_options = [
            "All",
            *sorted(
                {
                    _tool_presentation(
                        tool
                    )["category"]
                    for tool in tools
                }
            ),
        ]

        selected_category = (
            st.selectbox(
                "Category",
                options=category_options,
                key=(
                    "tool_category_filter"
                ),
            )
        )

        filtered_tools = [
            tool
            for tool in tools
            if (
                selected_category
                == "All"
                or _tool_presentation(
                    tool
                )["category"]
                == selected_category
            )
        ]

        st.caption(
            f"Showing {len(filtered_tools)} "
            f"of {len(tools)} tools"
        )

        for tool in filtered_tools:
            render_available_tool_card(
                tool
            )

    with run_tab:
        render_manual_tool_runner(
            tool_service,
            tools,
        )

    with history_tab:
        render_tool_history(
            tool_service
        )
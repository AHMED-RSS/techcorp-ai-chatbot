from __future__ import annotations

from typing import Any

import streamlit as st

from core.exceptions import SkillError
from services.skill_service import (
    Skill,
    SkillService,
)


def skill_label(
    skill: Skill,
) -> str:
    status = (
        ""
        if skill.enabled
        else " · Disabled"
    )

    return (
        f"{skill.icon} "
        f"{skill.name}"
        f"{status}"
    )


def render_skill_selector(
    skill_service: SkillService,
) -> None:
    skills = skill_service.enabled_skills()

    if not skills:
        st.warning(
            "No enabled skills are available."
        )
        return

    options = [
        skill.slug
        for skill in skills
    ]

    skill_map = {
        skill.slug: skill
        for skill in skills
    }

    selected_slug = (
        st.session_state
        .selected_skill
    )

    if selected_slug not in options:
        selected_slug = (
            "general_assistant"
            if "general_assistant"
            in options
            else options[0]
        )

    st.toggle(
        "Automatic skill selection",
        key="automatic_skill_selection",
        help=(
            "Select the best local skill based "
            "on the prompt and selected files."
        ),
    )

    if (
        st.session_state
        .automatic_skill_selection
    ):
        st.caption(
            "The application will select a skill "
            "for each request."
        )

    else:
        selected_index = options.index(
            selected_slug
        )

        chosen_slug = st.selectbox(
            "Active skill",
            options=options,
            index=selected_index,
            format_func=lambda slug: (
                skill_label(
                    skill_map[slug]
                )
            ),
            key="manual_skill_selector",
        )

        st.session_state.selected_skill = (
            chosen_slug
        )


def render_skill_card(
    skill: Skill,
) -> None:
    with st.container(
        border=True
    ):
        title_columns = st.columns(
            [5, 1],
            gap="small",
        )

        with title_columns[0]:
            st.markdown(
                f"### {skill.icon} "
                f"{skill.name}"
            )

            st.caption(
                skill.description
            )

        with title_columns[1]:
            if skill.built_in:
                st.markdown(
                    "`Built-in`"
                )
            else:
                st.markdown(
                    "`Custom`"
                )

        keyword_text = (
            ", ".join(skill.keywords)
            if skill.keywords
            else "No keywords"
        )

        st.caption(
            f"Keywords: {keyword_text}"
        )

        if not skill.enabled:
            st.warning(
                "This skill is currently disabled."
            )


def render_create_skill_form(
    skill_service: SkillService,
) -> None:
    with st.form(
        "create_skill_form",
        clear_on_submit=True,
    ):
        st.markdown(
            "### Create custom skill"
        )

        name = st.text_input(
            "Name",
            placeholder="Research Assistant",
        )

        description = st.text_area(
            "Description",
            placeholder=(
                "Explains what this skill should "
                "help the agent accomplish."
            ),
            height=90,
        )

        icon = st.text_input(
            "Icon",
            value="✨",
            max_chars=4,
        )

        keywords = st.text_input(
            "Keywords",
            placeholder=(
                "research, compare, investigate"
            ),
            help=(
                "Separate keywords with commas."
            ),
        )

        instructions = st.text_area(
            "Skill instructions",
            placeholder=(
                "Describe the behaviour, priorities "
                "and constraints for this skill."
            ),
            height=260,
        )

        submitted = st.form_submit_button(
            "Create skill",
            use_container_width=True,
            type="primary",
        )

        if submitted:
            try:
                created = (
                    skill_service.create_skill(
                        name=name,
                        description=description,
                        instructions=instructions,
                        keywords=keywords,
                        icon=icon,
                        enabled=True,
                    )
                )

                st.session_state.selected_skill = (
                    created.slug
                )

                st.session_state.skill_editor_slug = (
                    created.slug
                )

                st.toast(
                    "Skill created"
                )

                st.rerun()

            except SkillError as exc:
                st.error(str(exc))


def render_skill_editor(
    skill_service: SkillService,
    skill: Skill,
) -> None:
    with st.form(
        f"edit_skill_form_{skill.slug}"
    ):
        st.markdown(
            f"### Edit {skill.name}"
        )

        if skill.built_in:
            st.info(
                "Built-in skills can be edited and "
                "enabled or disabled, but they cannot "
                "be deleted."
            )

        name = st.text_input(
            "Name",
            value=skill.name,
        )

        description = st.text_area(
            "Description",
            value=skill.description,
            height=90,
        )

        icon = st.text_input(
            "Icon",
            value=skill.icon,
            max_chars=4,
        )

        keywords = st.text_input(
            "Keywords",
            value=", ".join(
                skill.keywords
            ),
        )

        enabled = st.checkbox(
            "Enabled",
            value=skill.enabled,
        )

        instructions = st.text_area(
            "Skill instructions",
            value=skill.instructions,
            height=320,
        )

        save_submitted = (
            st.form_submit_button(
                "Save changes",
                use_container_width=True,
                type="primary",
            )
        )

        if save_submitted:
            try:
                skill_service.update_skill(
                    skill.slug,
                    name=name,
                    description=description,
                    instructions=instructions,
                    keywords=keywords,
                    icon=icon,
                    enabled=enabled,
                )

                st.toast(
                    "Skill updated"
                )

                st.rerun()

            except SkillError as exc:
                st.error(str(exc))

    if not skill.built_in:
        st.divider()

        delete_requested = (
            st.session_state
            .pending_delete_skill_slug
            == skill.slug
        )

        if not delete_requested:
            if st.button(
                "Delete custom skill",
                key=(
                    f"request_delete_skill_"
                    f"{skill.slug}"
                ),
                use_container_width=True,
            ):
                st.session_state.pending_delete_skill_slug = (
                    skill.slug
                )

                st.rerun()

        else:
            st.warning(
                "Delete this custom skill permanently?"
            )

            delete_columns = st.columns(
                2,
                gap="small",
            )

            with delete_columns[0]:
                if st.button(
                    "Delete",
                    key=(
                        f"confirm_delete_skill_"
                        f"{skill.slug}"
                    ),
                    type="primary",
                    use_container_width=True,
                ):
                    try:
                        skill_service.delete_skill(
                            skill.slug
                        )

                        st.session_state.pending_delete_skill_slug = (
                            None
                        )

                        st.session_state.skill_editor_slug = (
                            None
                        )

                        st.session_state.selected_skill = (
                            "general_assistant"
                        )

                        st.toast(
                            "Skill deleted"
                        )

                        st.rerun()

                    except SkillError as exc:
                        st.error(str(exc))

            with delete_columns[1]:
                if st.button(
                    "Cancel",
                    key=(
                        f"cancel_delete_skill_"
                        f"{skill.slug}"
                    ),
                    use_container_width=True,
                ):
                    st.session_state.pending_delete_skill_slug = (
                        None
                    )

                    st.rerun()


def render_skills_workspace(
    skill_service: SkillService,
) -> None:
    st.markdown(
        "## Local skills"
    )

    st.caption(
        "Skills are local instruction packages "
        "used to guide the Ollama assistant."
    )

    skills = skill_service.list_skills()

    if not skills:
        st.error(
            "No skills were found."
        )
        return

    tab_library, tab_editor, tab_create = st.tabs(
        [
            "Skill library",
            "Edit skill",
            "Create skill",
        ]
    )

    with tab_library:
        st.metric(
            "Installed skills",
            len(skills),
        )

        for skill in skills:
            render_skill_card(skill)

            if st.button(
                f"Open {skill.name}",
                key=(
                    f"open_skill_"
                    f"{skill.slug}"
                ),
                use_container_width=True,
            ):
                st.session_state.skill_editor_slug = (
                    skill.slug
                )

                st.session_state.selected_skill = (
                    skill.slug
                )

                st.rerun()

    with tab_editor:
        skill_slugs = [
            skill.slug
            for skill in skills
        ]

        skill_map = {
            skill.slug: skill
            for skill in skills
        }

        editor_slug = (
            st.session_state
            .skill_editor_slug
        )

        if editor_slug not in skill_slugs:
            editor_slug = (
                st.session_state
                .selected_skill
            )

        if editor_slug not in skill_slugs:
            editor_slug = skill_slugs[0]

        selected_index = (
            skill_slugs.index(
                editor_slug
            )
        )

        chosen_slug = st.selectbox(
            "Choose a skill to edit",
            options=skill_slugs,
            index=selected_index,
            format_func=lambda slug: (
                skill_label(
                    skill_map[slug]
                )
            ),
            key="workspace_skill_editor_select",
        )

        st.session_state.skill_editor_slug = (
            chosen_slug
        )

        render_skill_editor(
            skill_service,
            skill_map[chosen_slug],
        )

    with tab_create:
        render_create_skill_form(
            skill_service
        )


def serialise_skill(
    skill: Skill,
) -> dict[str, Any]:
    return {
        "slug": skill.slug,
        "name": skill.name,
        "description": (
            skill.description
        ),
        "icon": skill.icon,
        "keywords": skill.keywords,
        "built_in": skill.built_in,
        "enabled": skill.enabled,
    }
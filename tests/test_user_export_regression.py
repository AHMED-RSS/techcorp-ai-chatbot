from __future__ import annotations

import json

from tests.test_user_data_controls import user_data_environment


def test_export_contains_expected_sections(
    user_data_environment,
):
    service = user_data_environment[
        "service"
    ]

    export = service.export_data()

    expected_sections = {
        "schema_version",
        "exported_at",
        "scope",
        "account",
        "preferences",
        "chats",
        "messages",
        "memories",
        "tasks",
        "documents",
        "skills",
        "study_sessions",
        "counts",
    }

    assert expected_sections.issubset(
        export.keys()
    )


def test_export_json_is_valid_json(
    user_data_environment,
):
    service = user_data_environment[
        "service"
    ]

    payload = service.export_json()

    decoded = json.loads(
        payload.decode("utf-8")
    )

    assert decoded["account"]["user_id"] == (
        "auth0|user-a"
    )


def test_export_contains_preferences_and_skills(
    user_data_environment,
):
    service = user_data_environment[
        "service"
    ]

    export = service.export_data()

    assert export["preferences"] is not None

    assert (
        export["preferences"]
        ["preferred_chat_model"]
        == "model-a"
    )

    assert len(
        export["skills"]
    ) == 1

    skill = export["skills"][0]

    assert skill["name"] == (
        "Private Skill A"
    )

    assert skill["enabled"] is True

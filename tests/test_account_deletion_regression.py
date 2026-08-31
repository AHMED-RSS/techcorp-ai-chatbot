from __future__ import annotations

from tests.test_user_data_controls import user_data_environment


def test_delete_account_returns_expected_contract(
    user_data_environment,
):
    service = user_data_environment[
        "service"
    ]

    result = service.delete_local_account()

    assert result["deleted"] is True

    assert result["user_id"] == (
        "auth0|user-a"
    )

    assert "database" in result
    assert "rag" in result
    assert "document_storage" in result
    assert "runtime_storage" in result

    assert (
        result["auth0_identity_deleted"]
        is False
    )


def test_delete_account_reports_missing_user(
    user_data_environment,
):
    service = user_data_environment[
        "service"
    ]

    service.user_id = (
        "auth0|missing-user"
    )

    result = service.delete_local_account()

    assert result["deleted"] is False

    assert result["user_id"] == (
        "auth0|missing-user"
    )

    assert (
        result["reason"]
        == "Local account not found"
    )


def test_delete_account_reports_cleanup_results(
    user_data_environment,
):
    service = user_data_environment[
        "service"
    ]

    result = service.delete_local_account()

    assert result["rag"]["deleted"] is True

    assert (
        result["document_storage"]
        ["deleted_folders"]
        == 2
    )

    assert (
        result["runtime_storage"]["deleted_folders"] == 3
    )

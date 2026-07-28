from __future__ import annotations

import pytest

from core.user_context import UserContext


def test_user_context_uses_auth0_subject() -> None:
    context = UserContext.from_claims(
        {
            "sub": "auth0|user-123",
            "email": "user@example.com",
            "name": "Example User",
            "picture": "https://example.com/avatar.png",
            "email_verified": True,
            "roles": ["member", "tester"],
        }
    )

    assert context.user_id == "auth0|user-123"
    assert context.email == "user@example.com"
    assert context.name == "Example User"
    assert context.avatar_url == (
        "https://example.com/avatar.png"
    )
    assert context.email_verified is True
    assert context.roles == (
        "member",
        "tester",
    )


def test_user_context_uses_email_as_name_fallback() -> None:
    context = UserContext.from_claims(
        {
            "sub": "google-oauth2|456",
            "email": "fallback@example.com",
        }
    )

    assert context.name == "fallback@example.com"


def test_user_context_requires_subject() -> None:
    with pytest.raises(
        ValueError,
        match="stable 'sub'",
    ):
        UserContext.from_claims(
            {
                "email": "missing-sub@example.com",
            }
        )


def test_user_context_serialises_safely() -> None:
    context = UserContext(
        user_id="auth0|789",
        email="person@example.com",
        name="Person",
        roles=("member",),
    )

    result = context.to_dict()

    assert result["user_id"] == "auth0|789"
    assert result["roles"] == ["member"]

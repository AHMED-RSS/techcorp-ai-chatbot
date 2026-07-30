from __future__ import annotations

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

from core.user_context import UserContext
from database.base import Base
from services.user_service import UserService


def build_service() -> UserService:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(
        engine
    )

    factory = sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )

    return UserService(
        factory
    )


def create_users(
    service: UserService,
) -> None:
    service.sync_user(
        UserContext(
            user_id="auth0|user-a",
            email="a@example.com",
            name="User A",
        )
    )

    service.sync_user(
        UserContext(
            user_id="auth0|user-b",
            email="b@example.com",
            name="User B",
        )
    )


def test_default_preferences_are_created() -> None:
    service = build_service()

    service.sync_user(
        UserContext(
            user_id="auth0|user-a",
            email="a@example.com",
            name="User A",
        )
    )

    preferences = service.get_preferences(
        "auth0|user-a"
    )

    assert preferences is not None

    assert (
        preferences.preferred_chat_model
        is None
    )

    assert preferences.theme == "system"


def test_model_preferences_are_user_isolated() -> None:
    service = build_service()

    create_users(
        service
    )

    service.set_preferred_chat_model(
        user_id="auth0|user-a",
        model="llama3.2",
    )

    service.set_preferred_chat_model(
        user_id="auth0|user-b",
        model="qwen2.5",
    )

    preferences_a = service.get_preferences(
        "auth0|user-a"
    )

    preferences_b = service.get_preferences(
        "auth0|user-b"
    )

    assert preferences_a is not None
    assert preferences_b is not None

    assert (
        preferences_a.preferred_chat_model
        == "llama3.2"
    )

    assert (
        preferences_b.preferred_chat_model
        == "qwen2.5"
    )

    service.set_preferred_chat_model(
        user_id="auth0|user-a",
        model=None,
    )

    preferences_a = service.get_preferences(
        "auth0|user-a"
    )

    preferences_b = service.get_preferences(
        "auth0|user-b"
    )

    assert preferences_a is not None
    assert preferences_b is not None

    assert (
        preferences_a.preferred_chat_model
        is None
    )

    assert (
        preferences_b.preferred_chat_model
        == "qwen2.5"
    )


def test_theme_preferences_are_user_isolated() -> None:
    service = build_service()

    create_users(
        service
    )

    service.set_theme(
        user_id="auth0|user-a",
        theme="dark",
    )

    service.set_theme(
        user_id="auth0|user-b",
        theme="light",
    )

    preferences_a = service.get_preferences(
        "auth0|user-a"
    )

    preferences_b = service.get_preferences(
        "auth0|user-b"
    )

    assert preferences_a is not None
    assert preferences_b is not None

    assert preferences_a.theme == "dark"
    assert preferences_b.theme == "light"

    with pytest.raises(
        ValueError,
        match="system, light or dark",
    ):
        service.set_theme(
            user_id="auth0|user-a",
            theme="purple",
        )



def test_user_switch_clears_session_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core import session as session_module
    from core.session import (
        bind_authenticated_user,
    )

    fake_state = {
        "current_user_id": "auth0|user-a",
        "messages": [
            {
                "role": "user",
                "content": "Private message",
            }
        ],
        "active_document_ids": [
            "document-a"
        ],
        "current_plan": {
            "id": "plan-a"
        },
        "last_tool_result": {
            "content": "private"
        },
        "selected_chat_model": "model-a",
        "preferences_loaded_user_id": (
            "auth0|user-a"
        ),
    }

    monkeypatch.setattr(
        session_module.st,
        "session_state",
        fake_state,
    )

    changed = bind_authenticated_user(
        "auth0|user-b"
    )

    assert changed is True

    assert fake_state[
        "current_user_id"
    ] == "auth0|user-b"

    assert fake_state["messages"] == []

    assert fake_state[
        "active_document_ids"
    ] == []

    assert fake_state[
        "current_plan"
    ] == []

    assert fake_state[
        "last_tool_result"
    ] is None

    assert fake_state[
        "selected_chat_model"
    ] is None

    assert fake_state[
        "preferences_loaded_user_id"
    ] is None

    fake_state["messages"] = [
        {
            "role": "user",
            "content": "User B message",
        }
    ]

    changed = bind_authenticated_user(
        "auth0|user-b"
    )

    assert changed is False

    assert fake_state["messages"] == [
        {
            "role": "user",
            "content": "User B message",
        }
    ]

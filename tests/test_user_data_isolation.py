from __future__ import annotations

import pytest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from core.exceptions import (
    ChatStorageError,
    MemoryServiceError,
)
from database.base import Base
from database.models import (
    Chat,
    ChatMessage,
    MemoryRecord,
    TaskSnapshot,
    User,
)
from services.database_chat_service import (
    DatabaseChatService,
)
from services.database_memory_service import (
    DatabaseMemoryService,
)


@pytest.fixture()
def isolated_services():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:"
    )

    Base.metadata.create_all(engine)

    factory = sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
    )

    with factory() as session:
        session.add_all(
            [
                User(
                    user_id="auth0|user-a",
                    email="a@example.com",
                    name="User A",
                ),
                User(
                    user_id="auth0|user-b",
                    email="b@example.com",
                    name="User B",
                ),
            ]
        )

        session.commit()

    return {
        "factory": factory,
        "chats_a": DatabaseChatService(
            user_id="auth0|user-a",
            session_factory=factory,
        ),
        "chats_b": DatabaseChatService(
            user_id="auth0|user-b",
            session_factory=factory,
        ),
        "memory_a": DatabaseMemoryService(
            user_id="auth0|user-a",
            session_factory=factory,
        ),
        "memory_b": DatabaseMemoryService(
            user_id="auth0|user-b",
            session_factory=factory,
        ),
    }


def test_chat_is_hidden_from_other_user(
    isolated_services,
) -> None:
    chats_a = isolated_services["chats_a"]
    chats_b = isolated_services["chats_b"]

    chat = chats_a.create_chat(
        "User A private chat"
    )

    chats_a.add_message(
        chat["id"],
        "user",
        "User A private message",
    )

    assert chats_b.load_chat(
        chat["id"]
    ) is None

    assert chats_b.list_chats() == []

    assert chats_b.delete_chat(
        chat["id"]
    ) is False

    with pytest.raises(
        ChatStorageError,
        match="Conversation was not found",
    ):
        chats_b.rename_chat(
            chat["id"],
            "Stolen chat",
        )

    stored = chats_a.load_chat(
        chat["id"]
    )

    assert stored is not None

    assert stored["messages"][0][
        "content"
    ] == "User A private message"


def test_users_only_search_their_chats(
    isolated_services,
) -> None:
    chats_a = isolated_services["chats_a"]
    chats_b = isolated_services["chats_b"]

    chat_a = chats_a.create_chat(
        "Alpha project"
    )

    chat_b = chats_b.create_chat(
        "Beta project"
    )

    chats_a.add_message(
        chat_a["id"],
        "assistant",
        "Private alpha information",
    )

    chats_b.add_message(
        chat_b["id"],
        "assistant",
        "Private beta information",
    )

    assert len(
        chats_a.search_chats("alpha")
    ) == 1

    assert chats_a.search_chats(
        "beta"
    ) == []

    assert len(
        chats_b.search_chats("beta")
    ) == 1

    assert chats_b.search_chats(
        "alpha"
    ) == []


def test_memory_is_hidden_from_other_user(
    isolated_services,
) -> None:
    memory_a = isolated_services["memory_a"]
    memory_b = isolated_services["memory_b"]

    item = memory_a.create_memory(
        content=(
            "User A prefers concise answers."
        ),
        kind="preference",
    )

    assert memory_b.load_memory(
        item.id
    ) is None

    assert memory_b.list_memories() == []

    assert memory_b.delete_memory(
        item.id
    ) is False

    assert memory_a.load_memory(
        item.id
    ) is not None


def test_task_is_hidden_from_other_user(
    isolated_services,
) -> None:
    memory_a = isolated_services["memory_a"]
    memory_b = isolated_services["memory_b"]

    task = memory_a.create_task_state(
        chat_id=None,
        user_request="Prepare private work",
        goal="Complete private task",
        status="planned",
    )

    assert memory_b.load_task_state(
        task.id
    ) is None

    assert (
        memory_b.list_task_states()
        == []
    )

    assert memory_b.delete_task_state(
        task.id
    ) is False


def test_user_cannot_attach_data_to_other_chat(
    isolated_services,
) -> None:
    chats_a = isolated_services["chats_a"]
    memory_b = isolated_services["memory_b"]

    chat = chats_a.create_chat()

    with pytest.raises(
        MemoryServiceError,
        match="Conversation was not found",
    ):
        memory_b.create_memory(
            content="Cross-user memory",
            chat_id=chat["id"],
        )

    with pytest.raises(
        MemoryServiceError,
        match="Conversation was not found",
    ):
        memory_b.create_task_state(
            chat_id=chat["id"],
            user_request="Cross-user task",
            goal="This must fail",
            status="pending",
        )


def test_every_record_contains_owner_id(
    isolated_services,
) -> None:
    factory = isolated_services["factory"]
    chats_a = isolated_services["chats_a"]
    memory_a = isolated_services["memory_a"]

    chat = chats_a.create_chat()

    chats_a.add_message(
        chat["id"],
        "user",
        "Verify owner",
    )

    memory_a.create_memory(
        content="Owner-scoped memory",
        chat_id=chat["id"],
    )

    memory_a.create_task_state(
        chat_id=chat["id"],
        user_request="Verify ownership",
        goal="Check owner IDs",
        status="completed",
    )

    with factory() as session:
        assert {
            record.user_id
            for record in session.scalars(
                select(Chat)
            )
        } == {"auth0|user-a"}

        assert {
            record.user_id
            for record in session.scalars(
                select(ChatMessage)
            )
        } == {"auth0|user-a"}

        assert {
            record.user_id
            for record in session.scalars(
                select(MemoryRecord)
            )
        } == {"auth0|user-a"}

        assert {
            record.user_id
            for record in session.scalars(
                select(TaskSnapshot)
            )
        } == {"auth0|user-a"}

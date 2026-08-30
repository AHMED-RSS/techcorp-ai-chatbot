from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base
from database.models import User
from services.database_chat_service import DatabaseChatService


def create_test_session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    
    # Pre-populate required user records in the sqlite database
    session = session_factory()
    try:
        session.add(User(user_id="user_1", name="Test User 1", email="chat1@example.com"))
        session.add(User(user_id="user_2", name="Test User 2", email="chat2@example.com"))
        session.commit()
    finally:
        session.close()

    return session_factory


def test_chat_creation_and_message_flow():
    factory = create_test_session_factory()
    service = DatabaseChatService(user_id="user_1", session_factory=factory)

    chat_dict = service.create_chat(title="Test UI Chat")
    assert chat_dict is not None
    assert chat_dict["title"] == "Test UI Chat"
    chat_id = chat_dict["id"]

    msg_dict = service.add_message(
        chat_id=chat_id,
        role="user",
        content="Hello world",
    )
    assert msg_dict is not None
    assert msg_dict["content"] == "Hello world"

    loaded_chat = service.load_chat(chat_id=chat_id)
    assert loaded_chat is not None
    assert len(loaded_chat["messages"]) == 1
    assert loaded_chat["messages"][0]["content"] == "Hello world"


def test_conversation_persistence_and_retrieval():
    factory = create_test_session_factory()
    service = DatabaseChatService(user_id="user_2", session_factory=factory)

    chat1 = service.create_chat(title="Chat 1")
    chat2 = service.create_chat(title="Chat 2")

    service.add_message(chat_id=chat1["id"], role="user", content="Msg 1")
    service.add_message(chat_id=chat2["id"], role="user", content="Msg 2")

    user_chats = service.list_chats()
    assert len(user_chats) == 2
    titles = [c["title"] for c in user_chats]
    assert "Chat 1" in titles
    assert "Chat 2" in titles

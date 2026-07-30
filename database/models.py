from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    false,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from database.base import Base, utc_now


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    avatar_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )

    settings_record: Mapped[
        UserSettings | None
    ] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    preferred_chat_model: Mapped[
        str | None
    ] = mapped_column(
        String(255),
        nullable=True,
    )

    theme: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="system",
        server_default="system",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(
        back_populates="settings_record",
    )

class Chat(Base):
    __tablename__ = "chats"
    __table_args__ = (
        Index(
            "ix_chats_user_updated",
            "user_id",
            "updated_at",
        ),
    )

    chat_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="New conversation",
    )

    pinned: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )

    archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )

    metadata_json: Mapped[
        dict[str, Any]
    ] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )

    messages: Mapped[
        list["ChatMessage"]
    ] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index(
            "ix_chat_messages_chat_created",
            "chat_id",
            "created_at",
        ),
        Index(
            "ix_chat_messages_user",
            "user_id",
        ),
    )

    message_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    chat_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "chats.chat_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    attachments_json: Mapped[
        list[dict[str, Any]]
    ] = mapped_column(
        "attachments",
        JSON,
        nullable=False,
        default=list,
    )

    metadata_json: Mapped[
        dict[str, Any]
    ] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    chat: Mapped[Chat] = relationship(
        back_populates="messages",
    )


class MemoryRecord(Base):
    __tablename__ = "memories"
    __table_args__ = (
        Index(
            "ix_memories_user_updated",
            "user_id",
            "updated_at",
        ),
        Index(
            "ix_memories_user_chat",
            "user_id",
            "chat_id",
        ),
    )

    memory_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    chat_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "chats.chat_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    kind: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="note",
    )

    keywords_json: Mapped[
        list[str]
    ] = mapped_column(
        "keywords",
        JSON,
        nullable=False,
        default=list,
    )

    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="explicit",
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    access_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    last_accessed_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    metadata_json: Mapped[
        dict[str, Any]
    ] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )


class TaskSnapshot(Base):
    __tablename__ = "task_snapshots"
    __table_args__ = (
        Index(
            "ix_task_snapshots_user_updated",
            "user_id",
            "updated_at",
        ),
        Index(
            "ix_task_snapshots_user_chat",
            "user_id",
            "chat_id",
        ),
    )

    task_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    chat_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "chats.chat_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    user_request: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    goal: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    route_json: Mapped[
        dict[str, Any] | None
    ] = mapped_column(
        "route",
        JSON,
        nullable=True,
    )

    plan_json: Mapped[
        dict[str, Any] | None
    ] = mapped_column(
        "plan",
        JSON,
        nullable=True,
    )

    execution_json: Mapped[
        dict[str, Any] | None
    ] = mapped_column(
        "execution",
        JSON,
        nullable=True,
    )

    critic_json: Mapped[
        dict[str, Any] | None
    ] = mapped_column(
        "critic",
        JSON,
        nullable=True,
    )

    final_output: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    metadata_json: Mapped[
        dict[str, Any]
    ] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )

class DocumentRecord(Base):
    """
    Parsed document metadata and extracted text owned by one user.
    """

    __tablename__ = "documents"

    __table_args__ = (
        Index(
            "ix_documents_user_updated",
            "user_id",
            "updated_at",
        ),
        Index(
            "ix_documents_user_sha256",
            "user_id",
            "sha256",
        ),
    )

    document_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    original_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    stored_filename: Mapped[str] = mapped_column(
        String(600),
        nullable=False,
    )

    stored_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    extension: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="",
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unknown",
    )

    size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    extracted_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    character_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    text_truncated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )

    metadata_json: Mapped[
        dict[str, Any]
    ] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )

    warnings_json: Mapped[
        list[str]
    ] = mapped_column(
        "warnings",
        JSON,
        nullable=False,
        default=list,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )


class StudySessionRecord(Base):
    """
    User-owned study material generated from local documents.
    """

    __tablename__ = "study_sessions"

    __table_args__ = (
        Index(
            "ix_study_sessions_user_updated",
            "user_id",
            "updated_at",
        ),
        Index(
            "ix_study_sessions_user_type_updated",
            "user_id",
            "study_type",
            "updated_at",
        ),
    )

    session_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    study_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    instruction: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    document_ids_json: Mapped[
        list[str]
    ] = mapped_column(
        "document_ids",
        JSON,
        nullable=False,
        default=list,
    )

    document_titles_json: Mapped[
        list[str]
    ] = mapped_column(
        "document_titles",
        JSON,
        nullable=False,
        default=list,
    )

    model: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    flashcards_json: Mapped[
        list[dict[str, Any]]
    ] = mapped_column(
        "flashcards",
        JSON,
        nullable=False,
        default=list,
    )

    quiz_questions_json: Mapped[
        list[dict[str, Any]]
    ] = mapped_column(
        "quiz_questions",
        JSON,
        nullable=False,
        default=list,
    )

    sources_json: Mapped[
        list[dict[str, Any]]
    ] = mapped_column(
        "sources",
        JSON,
        nullable=False,
        default=list,
    )

    metadata_json: Mapped[
        dict[str, Any]
    ] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )


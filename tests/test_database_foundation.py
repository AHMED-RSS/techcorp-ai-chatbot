from __future__ import annotations

import pytest

from sqlalchemy import (
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)

from config.settings import Settings
from core.user_context import UserContext
from database.base import Base
from database.connection import (
    DatabaseConfigurationError,
    build_database_url,
)
from database.models import (
    User,
    UserSettings,
)
from services.user_service import UserService


def test_build_database_url() -> None:
    settings = Settings(
        _env_file=None,
        DATABASE_HOST="database.local",
        DATABASE_PORT=5433,
        DATABASE_NAME="techcorp_test",
        DATABASE_USER="test_user",
        DATABASE_PASSWORD="test-password",
    )

    url = build_database_url(settings)

    assert url.drivername == (
        "postgresql+psycopg"
    )
    assert url.host == "database.local"
    assert url.port == 5433
    assert url.database == "techcorp_test"
    assert url.username == "test_user"
    assert url.password == "test-password"


def test_database_password_is_required() -> None:
    settings = Settings(
        _env_file=None,
        DATABASE_PASSWORD="",
    )

    with pytest.raises(
        DatabaseConfigurationError,
        match="DATABASE_PASSWORD",
    ):
        build_database_url(settings)


def build_user_service() -> tuple[
    UserService,
    sessionmaker[Session],
]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:"
    )

    Base.metadata.create_all(engine)

    factory = sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
    )

    return UserService(factory), factory


def test_sync_user_creates_database_records() -> None:
    service, factory = (
        build_user_service()
    )

    context = UserContext(
        user_id="auth0|123",
        email="user@example.com",
        name="Example User",
        avatar_url=(
            "https://example.com/avatar.png"
        ),
        email_verified=True,
    )

    record = service.sync_user(context)

    assert record.user_id == "auth0|123"
    assert record.email == (
        "user@example.com"
    )

    with factory() as session:
        user = session.get(
            User,
            "auth0|123",
        )

        settings_record = session.get(
            UserSettings,
            "auth0|123",
        )

        assert user is not None
        assert settings_record is not None
        assert settings_record.theme == (
            "system"
        )


def test_sync_user_updates_without_duplicates() -> None:
    service, factory = (
        build_user_service()
    )

    service.sync_user(
        UserContext(
            user_id="google-oauth2|456",
            email="old@example.com",
            name="Old Name",
        )
    )

    updated = service.sync_user(
        UserContext(
            user_id="google-oauth2|456",
            email="new@example.com",
            name="New Name",
            email_verified=True,
        )
    )

    assert updated.email == (
        "new@example.com"
    )
    assert updated.name == "New Name"
    assert updated.email_verified is True

    with factory() as session:
        user_count = session.scalar(
            select(func.count()).select_from(
                User
            )
        )

        settings_count = session.scalar(
            select(func.count()).select_from(
                UserSettings
            )
        )

    assert user_count == 1
    assert settings_count == 1

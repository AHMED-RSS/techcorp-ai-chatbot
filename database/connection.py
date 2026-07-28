from __future__ import annotations

from functools import lru_cache
from typing import Any

from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import Settings, get_settings


class DatabaseConfigurationError(
    RuntimeError
):
    """Required database settings are missing."""


DatabaseSessionFactory = sessionmaker[Session]


def build_database_url(
    settings: Settings,
) -> URL:
    required = {
        "DATABASE_HOST": settings.database_host,
        "DATABASE_NAME": settings.database_name,
        "DATABASE_USER": settings.database_user,
        "DATABASE_PASSWORD": (
            settings.database_password
        ),
    }

    missing = [
        key
        for key, value in required.items()
        if not str(value or "").strip()
    ]

    if missing:
        raise DatabaseConfigurationError(
            "Missing database settings: "
            + ", ".join(missing)
        )

    return URL.create(
        drivername="postgresql+psycopg",
        username=settings.database_user,
        password=settings.database_password,
        host=settings.database_host,
        port=settings.database_port,
        database=settings.database_name,
    )


@lru_cache(maxsize=1)
def get_database_engine() -> Engine:
    settings = get_settings()

    return create_engine(
        build_database_url(settings),
        echo=settings.database_echo,
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=(
            settings.database_max_overflow
        ),
        pool_timeout=(
            settings.database_pool_timeout
        ),
    )


@lru_cache(maxsize=1)
def get_session_factory(
) -> DatabaseSessionFactory:
    return sessionmaker(
        bind=get_database_engine(),
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


def database_health_check(
    engine: Engine | None = None,
) -> dict[str, Any]:
    selected_engine = (
        engine or get_database_engine()
    )

    with selected_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT "
                "current_user, "
                "current_database(), "
                "version(), "
                "to_regclass('public.users'), "
                "to_regclass('public.user_settings')"
            )
        ).one()

    return {
        "connected": True,
        "user": row[0],
        "database": row[1],
        "server": str(row[2]).split(",")[0],
        "users_table": row[3],
        "settings_table": row[4],
    }

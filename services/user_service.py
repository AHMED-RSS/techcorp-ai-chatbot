from __future__ import annotations

from dataclasses import dataclass

from core.user_context import UserContext
from database.connection import (
    DatabaseSessionFactory,
    get_session_factory,
)
from database.models import User, UserSettings


@dataclass(
    frozen=True,
    slots=True,
)
class UserRecord:
    user_id: str
    email: str | None
    name: str
    avatar_url: str | None
    email_verified: bool


class UserService:
    """Synchronise Auth0 users with PostgreSQL."""

    def __init__(
        self,
        session_factory: (
            DatabaseSessionFactory | None
        ) = None,
    ) -> None:
        self._session_factory = (
            session_factory
            or get_session_factory()
        )

    @staticmethod
    def _to_record(
        user: User,
    ) -> UserRecord:
        return UserRecord(
            user_id=user.user_id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            email_verified=(
                user.email_verified
            ),
        )

    def sync_user(
        self,
        context: UserContext,
    ) -> UserRecord:
        with self._session_factory() as session:
            user = session.get(
                User,
                context.user_id,
            )

            if user is None:
                user = User(
                    user_id=context.user_id,
                    email=(
                        context.email or None
                    ),
                    name=context.name,
                    avatar_url=(
                        context.avatar_url
                    ),
                    email_verified=(
                        context.email_verified
                    ),
                )

                session.add(user)

            else:
                user.email = (
                    context.email or None
                )
                user.name = context.name
                user.avatar_url = (
                    context.avatar_url
                )
                user.email_verified = (
                    context.email_verified
                )

            settings_record = session.get(
                UserSettings,
                context.user_id,
            )

            if settings_record is None:
                session.add(
                    UserSettings(
                        user_id=(
                            context.user_id
                        ),
                    )
                )

            session.commit()
            session.refresh(user)

            return self._to_record(user)

    def get_user(
        self,
        user_id: str,
    ) -> UserRecord | None:
        with self._session_factory() as session:
            user = session.get(
                User,
                user_id,
            )

            if user is None:
                return None

            return self._to_record(user)

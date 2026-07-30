from __future__ import annotations

from dataclasses import dataclass

from core.user_context import UserContext
from database.connection import (
    DatabaseSessionFactory,
    get_session_factory,
)
from database.models import User, UserSettings


VALID_THEMES = {
    "system",
    "light",
    "dark",
}


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


@dataclass(
    frozen=True,
    slots=True,
)
class UserPreferencesRecord:
    user_id: str
    preferred_chat_model: str | None
    theme: str


class UserService:
    """
    Synchronise Auth0 users and manage user preferences
    in PostgreSQL.
    """

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

    @staticmethod
    def _to_preferences(
        settings_record: UserSettings,
    ) -> UserPreferencesRecord:
        return UserPreferencesRecord(
            user_id=settings_record.user_id,
            preferred_chat_model=(
                settings_record
                .preferred_chat_model
            ),
            theme=settings_record.theme,
        )

    @staticmethod
    def _clean_user_id(
        user_id: str,
    ) -> str:
        cleaned = str(
            user_id or ""
        ).strip()

        if not cleaned:
            raise ValueError(
                "A user ID is required."
            )

        return cleaned

    def _get_or_create_settings(
        self,
        *,
        session,
        user_id: str,
    ) -> UserSettings:
        settings_record = session.get(
            UserSettings,
            user_id,
        )

        if settings_record is not None:
            return settings_record

        user = session.get(
            User,
            user_id,
        )

        if user is None:
            raise ValueError(
                "The user does not exist."
            )

        settings_record = UserSettings(
            user_id=user_id
        )

        session.add(
            settings_record
        )

        return settings_record

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
                session.flush()

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

            self._get_or_create_settings(
                session=session,
                user_id=context.user_id,
            )

            session.commit()
            session.refresh(user)

            return self._to_record(user)

    def get_user(
        self,
        user_id: str,
    ) -> UserRecord | None:
        cleaned_user_id = (
            self._clean_user_id(
                user_id
            )
        )

        with self._session_factory() as session:
            user = session.get(
                User,
                cleaned_user_id,
            )

            if user is None:
                return None

            return self._to_record(user)

    def get_preferences(
        self,
        user_id: str,
    ) -> UserPreferencesRecord | None:
        cleaned_user_id = (
            self._clean_user_id(
                user_id
            )
        )

        with self._session_factory() as session:
            settings_record = session.get(
                UserSettings,
                cleaned_user_id,
            )

            if settings_record is None:
                return None

            return self._to_preferences(
                settings_record
            )

    def set_preferred_chat_model(
        self,
        *,
        user_id: str,
        model: str | None,
    ) -> UserPreferencesRecord:
        cleaned_user_id = (
            self._clean_user_id(
                user_id
            )
        )

        cleaned_model = str(
            model or ""
        ).strip()

        preferred_model = (
            cleaned_model or None
        )

        if (
            preferred_model is not None
            and len(preferred_model) > 255
        ):
            raise ValueError(
                "The preferred model name "
                "is too long."
            )

        with self._session_factory() as session:
            settings_record = (
                self._get_or_create_settings(
                    session=session,
                    user_id=cleaned_user_id,
                )
            )

            settings_record.preferred_chat_model = (
                preferred_model
            )

            session.commit()
            session.refresh(
                settings_record
            )

            return self._to_preferences(
                settings_record
            )

    def set_theme(
        self,
        *,
        user_id: str,
        theme: str,
    ) -> UserPreferencesRecord:
        cleaned_user_id = (
            self._clean_user_id(
                user_id
            )
        )

        cleaned_theme = str(
            theme or ""
        ).strip().lower()

        if cleaned_theme not in VALID_THEMES:
            raise ValueError(
                "Theme must be system, "
                "light or dark."
            )

        with self._session_factory() as session:
            settings_record = (
                self._get_or_create_settings(
                    session=session,
                    user_id=cleaned_user_id,
                )
            )

            settings_record.theme = (
                cleaned_theme
            )

            session.commit()
            session.refresh(
                settings_record
            )

            return self._to_preferences(
                settings_record
            )

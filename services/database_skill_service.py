from __future__ import annotations

import uuid

from typing import Any

from sqlalchemy import select

from config.settings import Settings
from core.exceptions import SkillError
from database.connection import (
    DatabaseSessionFactory,
    get_session_factory,
)
from database.models import UserSkillRecord
from services.skill_service import (
    BUILT_IN_SKILLS,
    Skill,
    SkillService,
    clean_slug,
)


class DatabaseSkillService(SkillService):
    """
    User-isolated skill storage backed by PostgreSQL.

    Built-in skill definitions remain shared in application code.
    User edits to built-ins and user-created custom skills are stored
    separately for the authenticated user.
    """

    def __init__(
        self,
        *,
        user_id: str,
        settings: Settings,
        session_factory: (
            DatabaseSessionFactory | None
        ) = None,
    ) -> None:
        cleaned_user_id = str(
            user_id or ""
        ).strip()

        if not cleaned_user_id:
            raise ValueError(
                "A user ID is required."
            )

        self.user_id = cleaned_user_id
        self.settings = settings
        self.skills_folder = (
            settings.skills_folder
        )
        self._session_factory = (
            session_factory
            or get_session_factory()
        )

    @staticmethod
    def _datetime_text(
        value: Any,
    ) -> str:
        if value is None:
            return ""

        isoformat = getattr(
            value,
            "isoformat",
            None,
        )

        if callable(isoformat):
            return str(isoformat())

        return str(value)

    @staticmethod
    def _built_in_definition(
        slug: str,
    ) -> dict[str, Any] | None:
        for definition in BUILT_IN_SKILLS:
            if definition["slug"] == slug:
                return definition

        return None

    def _find_record(
        self,
        session,
        slug: str,
    ) -> UserSkillRecord | None:
        return session.scalar(
            select(
                UserSkillRecord
            ).where(
                UserSkillRecord.user_id
                == self.user_id,
                UserSkillRecord.slug
                == slug,
            )
        )

    def _record_to_skill(
        self,
        record: UserSkillRecord,
    ) -> Skill:
        return Skill(
            slug=record.slug,
            name=record.name,
            description=record.description,
            instructions=record.instructions,
            icon=record.icon,
            keywords=list(
                record.keywords_json or []
            ),
            built_in=record.built_in,
            enabled=record.enabled,
            created_at=self._datetime_text(
                record.created_at
            ),
            updated_at=self._datetime_text(
                record.updated_at
            ),
            folder=self.skill_folder(
                record.slug
            ),
        )

    def _default_built_in_skill(
        self,
        definition: dict[str, Any],
    ) -> Skill:
        slug = str(
            definition["slug"]
        )

        return Skill(
            slug=slug,
            name=str(
                definition["name"]
            ),
            description=str(
                definition["description"]
            ),
            instructions=str(
                definition["instructions"]
            ),
            icon=str(
                definition.get(
                    "icon",
                    "\u2728",
                )
            ),
            keywords=list(
                definition.get(
                    "keywords",
                    [],
                )
            ),
            built_in=True,
            enabled=True,
            created_at="",
            updated_at="",
            folder=self.skill_folder(
                slug
            ),
        )

    def load_skill(
        self,
        slug: str,
    ) -> Skill | None:
        safe_slug = clean_slug(slug)

        definition = (
            self._built_in_definition(
                safe_slug
            )
        )

        with self._session_factory() as session:
            record = self._find_record(
                session,
                safe_slug,
            )

            if record is not None:
                return self._record_to_skill(
                    record
                )

        if definition is not None:
            return self._default_built_in_skill(
                definition
            )

        return None

    def list_skills(
        self,
        *,
        include_disabled: bool = True,
    ) -> list[Skill]:
        with self._session_factory() as session:
            records = list(
                session.scalars(
                    select(
                        UserSkillRecord
                    ).where(
                        UserSkillRecord.user_id
                        == self.user_id
                    )
                ).all()
            )

            record_map = {
                record.slug: record
                for record in records
            }

            skills: list[Skill] = []

            for definition in BUILT_IN_SKILLS:
                slug = str(
                    definition["slug"]
                )

                record = record_map.pop(
                    slug,
                    None,
                )

                if record is None:
                    skill = (
                        self._default_built_in_skill(
                            definition
                        )
                    )
                else:
                    skill = self._record_to_skill(
                        record
                    )

                if (
                    include_disabled
                    or skill.enabled
                ):
                    skills.append(skill)

            for record in record_map.values():
                if record.built_in:
                    continue

                skill = self._record_to_skill(
                    record
                )

                if (
                    include_disabled
                    or skill.enabled
                ):
                    skills.append(skill)

        skills.sort(
            key=lambda skill: (
                not skill.built_in,
                skill.name.lower(),
            )
        )

        return skills

    def create_skill(
        self,
        *,
        name: str,
        description: str,
        instructions: str,
        keywords: list[str] | str,
        icon: str = "\u2728",
        enabled: bool = True,
    ) -> Skill:
        validated = self.validate_skill_data(
            name=name,
            description=description,
            instructions=instructions,
            keywords=keywords,
        )

        slug = clean_slug(
            validated["name"]
        )
        original_slug = slug
        counter = 2

        existing_slugs = {
            skill.slug
            for skill in self.list_skills()
        }

        while slug in existing_slugs:
            slug = (
                f"{original_slug}_{counter}"
            )
            counter += 1

        with self._session_factory() as session:
            record = UserSkillRecord(
                skill_id=str(
                    uuid.uuid4()
                ),
                user_id=self.user_id,
                slug=slug,
                name=validated["name"],
                description=(
                    validated["description"]
                ),
                instructions=(
                    validated["instructions"]
                ),
                icon=str(
                    icon or "\u2728"
                )[:4],
                keywords_json=(
                    validated["keywords"]
                ),
                built_in=False,
                enabled=bool(enabled),
            )

            session.add(record)
            session.commit()
            session.refresh(record)

            return self._record_to_skill(
                record
            )

    def update_skill(
        self,
        slug: str,
        *,
        name: str,
        description: str,
        instructions: str,
        keywords: list[str] | str,
        icon: str,
        enabled: bool,
    ) -> Skill:
        safe_slug = clean_slug(slug)

        existing = self.load_skill(
            safe_slug
        )

        if existing is None:
            raise SkillError(
                "Skill was not found."
            )

        validated = self.validate_skill_data(
            name=name,
            description=description,
            instructions=instructions,
            keywords=keywords,
        )

        with self._session_factory() as session:
            record = self._find_record(
                session,
                safe_slug,
            )

            if record is None:
                if not existing.built_in:
                    raise SkillError(
                        "Skill was not found."
                    )

                record = UserSkillRecord(
                    skill_id=str(
                        uuid.uuid4()
                    ),
                    user_id=self.user_id,
                    slug=safe_slug,
                    name=validated["name"],
                    description=(
                        validated[
                            "description"
                        ]
                    ),
                    instructions=(
                        validated[
                            "instructions"
                        ]
                    ),
                    icon=str(
                        icon or "\u2728"
                    )[:4],
                    keywords_json=(
                        validated[
                            "keywords"
                        ]
                    ),
                    built_in=True,
                    enabled=bool(enabled),
                )

                session.add(record)

            else:
                record.name = (
                    validated["name"]
                )
                record.description = (
                    validated[
                        "description"
                    ]
                )
                record.instructions = (
                    validated[
                        "instructions"
                    ]
                )
                record.icon = str(
                    icon or "\u2728"
                )[:4]
                record.keywords_json = (
                    validated["keywords"]
                )
                record.built_in = (
                    existing.built_in
                )
                record.enabled = bool(
                    enabled
                )

            session.commit()
            session.refresh(record)

            return self._record_to_skill(
                record
            )

    def delete_skill(
        self,
        slug: str,
    ) -> bool:
        safe_slug = clean_slug(slug)

        existing = self.load_skill(
            safe_slug
        )

        if existing is None:
            return False

        if existing.built_in:
            raise SkillError(
                "Built-in skills cannot be deleted."
            )

        with self._session_factory() as session:
            record = self._find_record(
                session,
                safe_slug,
            )

            if record is None:
                return False

            session.delete(record)
            session.commit()

        return True

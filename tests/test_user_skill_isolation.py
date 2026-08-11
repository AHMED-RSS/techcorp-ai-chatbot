from __future__ import annotations

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

from config.settings import get_settings
from core.exceptions import SkillError
from database.base import Base
from database.models import User
from services.database_skill_service import (
    DatabaseSkillService,
)


@pytest.fixture()
def skill_environment(
    tmp_path,
) -> dict[str, DatabaseSkillService]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    factory = sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
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

    settings = get_settings().model_copy(
        update={
            "skills_folder": (
                tmp_path / "skills"
            ),
        }
    )

    return {
        "a": DatabaseSkillService(
            user_id="auth0|user-a",
            settings=settings,
            session_factory=factory,
        ),
        "b": DatabaseSkillService(
            user_id="auth0|user-b",
            settings=settings,
            session_factory=factory,
        ),
    }


def create_private_skill(
    service: DatabaseSkillService,
):
    return service.create_skill(
        name="Private Research",
        description=(
            "A private research skill for one user."
        ),
        instructions=(
            "Research the requested topic carefully, "
            "compare the evidence, and produce a "
            "clear structured answer."
        ),
        keywords="research, compare",
        icon="\u2728",
    )


def test_custom_skill_is_visible_only_to_owner(
    skill_environment,
) -> None:
    service_a = skill_environment["a"]
    service_b = skill_environment["b"]

    created = create_private_skill(
        service_a
    )

    assert (
        service_a.load_skill(
            created.slug
        )
        is not None
    )

    assert (
        service_b.load_skill(
            created.slug
        )
        is None
    )

    assert created.slug not in {
        skill.slug
        for skill in service_b.list_skills()
    }


def test_users_can_use_same_custom_slug(
    skill_environment,
) -> None:
    service_a = skill_environment["a"]
    service_b = skill_environment["b"]

    skill_a = create_private_skill(
        service_a
    )
    skill_b = create_private_skill(
        service_b
    )

    assert skill_a.slug == "private_research"
    assert skill_b.slug == "private_research"


def test_user_cannot_modify_other_users_custom_skill(
    skill_environment,
) -> None:
    service_a = skill_environment["a"]
    service_b = skill_environment["b"]

    created = create_private_skill(
        service_a
    )

    with pytest.raises(
        SkillError,
        match="not found",
    ):
        service_b.update_skill(
            created.slug,
            name="Changed Skill",
            description=(
                "This change must not be allowed."
            ),
            instructions=(
                "These instructions must never replace "
                "another user's private skill content."
            ),
            keywords="changed",
            icon="\u2728",
            enabled=True,
        )

    assert (
        service_b.delete_skill(
            created.slug
        )
        is False
    )

    owner_skill = service_a.load_skill(
        created.slug
    )

    assert owner_skill is not None
    assert owner_skill.name == "Private Research"


def test_built_in_edit_is_private_to_user(
    skill_environment,
) -> None:
    service_a = skill_environment["a"]
    service_b = skill_environment["b"]

    original_b = service_b.load_skill(
        "general_assistant"
    )

    assert original_b is not None

    service_a.update_skill(
        "general_assistant",
        name="My General Assistant",
        description=(
            "A private customised general assistant."
        ),
        instructions=(
            "Answer clearly and use the private "
            "preferences configured only by this user."
        ),
        keywords="general, private",
        icon="\u2728",
        enabled=False,
    )

    edited_a = service_a.load_skill(
        "general_assistant"
    )
    unchanged_b = service_b.load_skill(
        "general_assistant"
    )

    assert edited_a is not None
    assert unchanged_b is not None

    assert edited_a.name == "My General Assistant"
    assert edited_a.enabled is False

    assert unchanged_b.name == original_b.name
    assert (
        unchanged_b.description
        == original_b.description
    )
    assert (
        unchanged_b.instructions
        == original_b.instructions
    )
    assert unchanged_b.enabled is True


def test_built_in_skill_cannot_be_deleted(
    skill_environment,
) -> None:
    service_a = skill_environment["a"]

    with pytest.raises(
        SkillError,
        match="cannot be deleted",
    ):
        service_a.delete_skill(
            "general_assistant"
        )
"""Add user-owned skills.

Revision ID: 20260808_0005
Revises: 20260730_0004
Create Date: 2026-08-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260808_0005"

down_revision: Union[
    str,
    None,
] = "20260730_0004"

branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None

depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    op.create_table(
        "user_skills",
        sa.Column(
            "skill_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "slug",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "instructions",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "icon",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "keywords",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "built_in",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "skill_id"
        ),
        sa.UniqueConstraint(
            "user_id",
            "slug",
            name="uq_user_skills_user_slug",
        ),
    )

    op.create_index(
        "ix_user_skills_user_id",
        "user_skills",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        "ix_user_skills_user_updated",
        "user_skills",
        [
            "user_id",
            "updated_at",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_skills_user_updated",
        table_name="user_skills",
    )

    op.drop_index(
        "ix_user_skills_user_id",
        table_name="user_skills",
    )

    op.drop_table(
        "user_skills"
    )

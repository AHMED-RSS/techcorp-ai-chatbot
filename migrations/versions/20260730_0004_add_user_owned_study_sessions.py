"""Add user-owned study sessions.

Revision ID: 20260730_0004
Revises: 20260729_0003
Create Date: 2026-07-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260730_0004"

down_revision: Union[
    str,
    None,
] = "20260729_0003"

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
        "study_sessions",
        sa.Column(
            "session_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "study_type",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "instruction",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "document_ids",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "document_titles",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "model",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "flashcards",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "quiz_questions",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "sources",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            sa.JSON(),
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
            "session_id"
        ),
    )

    op.create_index(
        "ix_study_sessions_user_id",
        "study_sessions",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        "ix_study_sessions_user_updated",
        "study_sessions",
        [
            "user_id",
            "updated_at",
        ],
        unique=False,
    )

    op.create_index(
        "ix_study_sessions_user_type_updated",
        "study_sessions",
        [
            "user_id",
            "study_type",
            "updated_at",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_study_sessions_user_type_updated",
        table_name="study_sessions",
    )

    op.drop_index(
        "ix_study_sessions_user_updated",
        table_name="study_sessions",
    )

    op.drop_index(
        "ix_study_sessions_user_id",
        table_name="study_sessions",
    )

    op.drop_table(
        "study_sessions"
    )

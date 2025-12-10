"""add feedback_submissions table

Revision ID: c3d4e5f6a7b8
Revises: b7d8e9f01234
Create Date: 2025-01-15 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b7d8e9f01234"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feedback_submissions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("user_role", sa.String(length=50), nullable=True),
        sa.Column("page_route", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_feedback_submissions_created_at",
        "feedback_submissions",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_feedback_submissions_created_at", table_name="feedback_submissions")
    op.drop_table("feedback_submissions")

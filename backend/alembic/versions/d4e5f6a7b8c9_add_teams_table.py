"""add teams table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2025-01-15 13:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("home_ground", sa.String(length=255), nullable=True),
        sa.Column("season", sa.String(length=50), nullable=True),
        sa.Column("owner_user_id", sa.String(), nullable=False),
        sa.Column("coach_user_id", sa.String(), nullable=True),
        sa.Column("coach_name", sa.String(length=255), nullable=True),
        sa.Column("players", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("competitions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["coach_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teams_name", "teams", ["name"], unique=False)
    op.create_index("ix_teams_owner", "teams", ["owner_user_id"], unique=False)
    op.create_index("ix_teams_coach", "teams", ["coach_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_teams_coach", table_name="teams")
    op.drop_index("ix_teams_owner", table_name="teams")
    op.drop_index("ix_teams_name", table_name="teams")
    op.drop_table("teams")

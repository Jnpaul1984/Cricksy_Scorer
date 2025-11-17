"""add_coach_pro_tables

Revision ID: a6d4c2f1b7e8
Revises: f7c1d9b2a4e5
Create Date: 2025-11-17 01:15:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a6d4c2f1b7e8"
down_revision = "f7c1d9b2a4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coach_player_assignments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("coach_user_id", sa.String(), nullable=False),
        sa.Column("player_profile_id", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
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
        sa.ForeignKeyConstraint(["coach_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["player_profile_id"], ["player_profiles.player_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_coach_player_assignments_coach_user_id",
        "coach_player_assignments",
        ["coach_user_id"],
    )
    op.create_index(
        "ix_coach_player_assignments_player_profile_id",
        "coach_player_assignments",
        ["player_profile_id"],
    )
    op.create_index(
        "ix_coach_assignments_unique",
        "coach_player_assignments",
        ["coach_user_id", "player_profile_id"],
        unique=True,
    )

    op.create_table(
        "coaching_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("coach_user_id", sa.String(), nullable=False),
        sa.Column("player_profile_id", sa.String(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("focus_area", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["coach_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["player_profile_id"], ["player_profiles.player_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_coaching_sessions_coach_time",
        "coaching_sessions",
        ["coach_user_id", "scheduled_at"],
    )
    op.create_index(
        "ix_coaching_sessions_player_time",
        "coaching_sessions",
        ["player_profile_id", "scheduled_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_coaching_sessions_player_time", table_name="coaching_sessions")
    op.drop_index("ix_coaching_sessions_coach_time", table_name="coaching_sessions")
    op.drop_table("coaching_sessions")

    op.drop_index("ix_coach_assignments_unique", table_name="coach_player_assignments")
    op.drop_index(
        "ix_coach_player_assignments_player_profile_id",
        table_name="coach_player_assignments",
    )
    op.drop_index(
        "ix_coach_player_assignments_coach_user_id",
        table_name="coach_player_assignments",
    )
    op.drop_table("coach_player_assignments")

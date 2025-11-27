"""add_player_pro_tables

Revision ID: f7c1d9b2a4e5
Revises: e4a3c6f1d5ab
Create Date: 2025-11-17 00:30:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f7c1d9b2a4e5"
down_revision = "e4a3c6f1d5ab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    visibility_enum = postgresql.ENUM(
        "private_to_coach",
        "org_only",
        name="coaching_note_visibility",
    )
    bind = op.get_bind()
    visibility_enum.create(bind, checkfirst=True)
    column_visibility_enum = postgresql.ENUM(
        "private_to_coach",
        "org_only",
        name="coaching_note_visibility",
        create_type=False,
    )

    op.create_table(
        "player_forms",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("matches_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("runs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wickets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("batting_average", sa.Float(), nullable=True),
        sa.Column("strike_rate", sa.Float(), nullable=True),
        sa.Column("economy", sa.Float(), nullable=True),
        sa.Column("form_score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["player_id"], ["player_profiles.player_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_player_forms_player_id",
        "player_forms",
        ["player_id"],
    )
    op.create_index(
        "ix_player_forms_period",
        "player_forms",
        ["player_id", "period_start", "period_end"],
    )

    op.create_table(
        "player_coaching_notes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("coach_user_id", sa.String(), nullable=False),
        sa.Column("strengths", sa.Text(), nullable=False),
        sa.Column("weaknesses", sa.Text(), nullable=False),
        sa.Column("action_plan", sa.Text(), nullable=True),
        sa.Column(
            "visibility",
            column_visibility_enum,
            nullable=False,
            server_default="private_to_coach",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["coach_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["player_profiles.player_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_player_coaching_notes_player_id",
        "player_coaching_notes",
        ["player_id"],
    )
    op.create_index(
        "ix_player_coaching_notes_coach_user_id",
        "player_coaching_notes",
        ["coach_user_id"],
    )
    op.create_index(
        "ix_player_coaching_notes_visibility",
        "player_coaching_notes",
        ["visibility"],
    )

    op.create_table(
        "player_summaries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("total_matches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_runs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_wickets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("batting_average", sa.Float(), nullable=True),
        sa.Column("bowling_average", sa.Float(), nullable=True),
        sa.Column("strike_rate", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["player_id"], ["player_profiles.player_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id"),
    )
    op.create_index(
        "ix_player_summaries_player_id",
        "player_summaries",
        ["player_id"],
    )
    op.create_index(
        "ix_player_summaries_totals",
        "player_summaries",
        ["total_runs", "total_wickets"],
    )


def downgrade() -> None:
    op.drop_index("ix_player_summaries_totals", table_name="player_summaries")
    op.drop_index("ix_player_summaries_player_id", table_name="player_summaries")
    op.drop_table("player_summaries")

    op.drop_index(
        "ix_player_coaching_notes_visibility",
        table_name="player_coaching_notes",
    )
    op.drop_index(
        "ix_player_coaching_notes_coach_user_id",
        table_name="player_coaching_notes",
    )
    op.drop_index(
        "ix_player_coaching_notes_player_id",
        table_name="player_coaching_notes",
    )
    op.drop_table("player_coaching_notes")

    op.drop_index("ix_player_forms_period", table_name="player_forms")
    op.drop_index("ix_player_forms_player_id", table_name="player_forms")
    op.drop_table("player_forms")

    visibility_enum = postgresql.ENUM(name="coaching_note_visibility")
    bind = op.get_bind()
    visibility_enum.drop(bind, checkfirst=True)

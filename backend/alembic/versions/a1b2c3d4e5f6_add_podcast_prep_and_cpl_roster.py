"""Phase 10T — Add podcast_prep_reports, cpl_current_season_teams, cpl_current_season_players tables.

Revision ID: a1b2c3d4e5f6
Revises: z1a2b3c4d5e6
Create Date: 2026-06-02
"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "z1a2b3c4d5e6"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # --- podcast_prep_report_status enum ---
    podcast_topic_type = sa.Enum(
        "match",
        "tournament",
        "team",
        "archive",
        "custom",
        name="podcast_prep_topic_type",
    )
    podcast_report_status = sa.Enum(
        "draft",
        "reviewed",
        "approved",
        "archived",
        name="podcast_prep_report_status",
    )
    podcast_topic_type.create(op.get_bind(), checkfirst=True)
    podcast_report_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "podcast_prep_reports",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column(
            "topic_type",
            podcast_topic_type,
            nullable=False,
        ),
        sa.Column("source_match_id", sa.String(), nullable=True),
        sa.Column("source_competition_code", sa.String(64), nullable=True),
        sa.Column("source_season", sa.String(64), nullable=True),
        sa.Column("source_team_name", sa.String(255), nullable=True),
        sa.Column("generated_markdown", sa.Text(), nullable=True),
        sa.Column("generated_plain_text", sa.Text(), nullable=True),
        sa.Column("trust_summary", sa.Text(), nullable=True),
        sa.Column(
            "status",
            podcast_report_status,
            nullable=False,
            server_default="draft",
        ),
        sa.Column("created_by_id", sa.String(), nullable=True),
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
            ["created_by_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_podcast_prep_report_topic", "podcast_prep_reports", ["topic_type"])
    op.create_index("ix_podcast_prep_report_status", "podcast_prep_reports", ["status"])
    op.create_index(
        "ix_podcast_prep_report_match", "podcast_prep_reports", ["source_match_id"]
    )
    op.create_index(
        "ix_podcast_prep_report_created_by", "podcast_prep_reports", ["created_by_id"]
    )

    # --- cpl_roster_player_status enum ---
    roster_status_enum = sa.Enum(
        "active",
        "inactive",
        "unknown",
        name="cpl_roster_player_status",
    )
    roster_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "cpl_current_season_teams",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("competition_code", sa.String(64), nullable=False),
        sa.Column("season", sa.String(64), nullable=False),
        sa.Column("team_name", sa.String(255), nullable=False),
        sa.Column("normalized_team_name", sa.String(255), nullable=False),
        sa.Column("team_short_name", sa.String(64), nullable=True),
        sa.Column("home_ground", sa.String(255), nullable=True),
        sa.Column("source_note", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cpl_current_team_comp_code", "cpl_current_season_teams", ["competition_code"]
    )
    op.create_index(
        "ix_cpl_current_team_season", "cpl_current_season_teams", ["season"]
    )
    op.create_index(
        "ix_cpl_current_team_normalized", "cpl_current_season_teams", ["normalized_team_name"]
    )
    op.create_index(
        "ix_cpl_current_team_unique",
        "cpl_current_season_teams",
        ["competition_code", "season", "normalized_team_name"],
        unique=True,
    )

    op.create_table(
        "cpl_current_season_players",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("competition_code", sa.String(64), nullable=False),
        sa.Column("season", sa.String(64), nullable=False),
        sa.Column("player_name", sa.String(255), nullable=False),
        sa.Column("normalized_player_name", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("team_name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(64), nullable=True),
        sa.Column("batting_style", sa.String(64), nullable=True),
        sa.Column("bowling_style", sa.String(64), nullable=True),
        sa.Column(
            "status",
            roster_status_enum,
            nullable=False,
            server_default="active",
        ),
        sa.Column("is_returning", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("prior_season", sa.String(64), nullable=True),
        sa.Column("source_note", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cpl_current_player_comp_code",
        "cpl_current_season_players",
        ["competition_code"],
    )
    op.create_index(
        "ix_cpl_current_player_season", "cpl_current_season_players", ["season"]
    )
    op.create_index(
        "ix_cpl_current_player_normalized",
        "cpl_current_season_players",
        ["normalized_player_name"],
    )
    op.create_index(
        "ix_cpl_current_player_team", "cpl_current_season_players", ["team_name"]
    )
    op.create_index(
        "ix_cpl_current_player_status", "cpl_current_season_players", ["status"]
    )
    op.create_index(
        "ix_cpl_current_player_unique",
        "cpl_current_season_players",
        ["competition_code", "season", "normalized_player_name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("cpl_current_season_players")
    op.drop_table("cpl_current_season_teams")
    op.drop_table("podcast_prep_reports")

    # Drop enums (PostgreSQL specific; safe to catch errors on SQLite)
    try:
        sa.Enum(name="podcast_prep_topic_type").drop(op.get_bind(), checkfirst=True)
        sa.Enum(name="podcast_prep_report_status").drop(op.get_bind(), checkfirst=True)
        sa.Enum(name="cpl_roster_player_status").drop(op.get_bind(), checkfirst=True)
    except Exception:
        pass

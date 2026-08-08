"""Extend current-season roster fields for management workflows.

Revision ID: ab12cd34ef56
Revises: f0a1b2c3d4e5
Create Date: 2026-08-08
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "ab12cd34ef56"
down_revision: str | None = "f0a1b2c3d4e5"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Extend existing player status enum safely.
        op.execute(sa.text("ALTER TYPE cpl_roster_player_status ADD VALUE IF NOT EXISTS 'retired'"))
        op.execute(
            sa.text("ALTER TYPE cpl_roster_player_status ADD VALUE IF NOT EXISTS 'disabled'")
        )
        team_status = postgresql.ENUM(
            "active",
            "inactive",
            name="cpl_roster_team_status",
            create_type=False,
        )
        team_status.create(bind, checkfirst=True)

    op.add_column(
        "cpl_current_season_teams",
        sa.Column("country", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "cpl_current_season_teams",
        sa.Column("coach_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "cpl_current_season_teams",
        sa.Column("captain_name", sa.String(length=255), nullable=True),
    )
    if bind.dialect.name == "postgresql":
        op.add_column(
            "cpl_current_season_teams",
            sa.Column(
                "status",
                postgresql.ENUM(
                    "active",
                    "inactive",
                    name="cpl_roster_team_status",
                    create_type=False,
                ),
                nullable=False,
                server_default="active",
            ),
        )
    else:
        op.add_column(
            "cpl_current_season_teams",
            sa.Column(
                "status",
                sa.Enum("active", "inactive", name="cpl_roster_team_status"),
                nullable=False,
                server_default="active",
            ),
        )
    op.create_index(
        "ix_cpl_current_team_status", "cpl_current_season_teams", ["status"], unique=False
    )

    op.add_column(
        "cpl_current_season_players",
        sa.Column("nationality", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "cpl_current_season_players",
        sa.Column("date_of_birth", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cpl_current_season_players", "date_of_birth")
    op.drop_column("cpl_current_season_players", "nationality")

    op.drop_index("ix_cpl_current_team_status", table_name="cpl_current_season_teams")
    op.drop_column("cpl_current_season_teams", "status")
    op.drop_column("cpl_current_season_teams", "captain_name")
    op.drop_column("cpl_current_season_teams", "coach_name")
    op.drop_column("cpl_current_season_teams", "country")

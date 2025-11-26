"""add tournament tables

Revision ID: e1f7a8b2c9d3
Revises: d2bd42f8d9e8
Create Date: 2025-11-01 23:42:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e1f7a8b2c9d3"
down_revision = "d2bd42f8d9e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tournaments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tournament_type", sa.String(), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tournaments_status", "tournaments", ["status"])

    op.create_table(
        "tournament_teams",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tournament_id", sa.String(), nullable=False),
        sa.Column("team_name", sa.String(), nullable=False),
        sa.Column("team_data", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("matches_played", sa.Integer(), nullable=False),
        sa.Column("matches_won", sa.Integer(), nullable=False),
        sa.Column("matches_lost", sa.Integer(), nullable=False),
        sa.Column("matches_drawn", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("net_run_rate", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tournament_id"], ["tournaments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tournament_teams_tournament_id", "tournament_teams", ["tournament_id"]
    )
    op.create_index("ix_tournament_teams_points", "tournament_teams", ["points"])

    op.create_table(
        "fixtures",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tournament_id", sa.String(), nullable=False),
        sa.Column("match_number", sa.Integer(), nullable=True),
        sa.Column("team_a_name", sa.String(), nullable=False),
        sa.Column("team_b_name", sa.String(), nullable=False),
        sa.Column("venue", sa.String(), nullable=True),
        sa.Column("scheduled_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("game_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["tournament_id"], ["tournaments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fixtures_tournament_id", "fixtures", ["tournament_id"])
    op.create_index("ix_fixtures_status", "fixtures", ["status"])
    op.create_index("ix_fixtures_scheduled_date", "fixtures", ["scheduled_date"])


def downgrade() -> None:
    op.drop_index("ix_fixtures_scheduled_date", table_name="fixtures")
    op.drop_index("ix_fixtures_status", table_name="fixtures")
    op.drop_index("ix_fixtures_tournament_id", table_name="fixtures")
    op.drop_table("fixtures")

    op.drop_index("ix_tournament_teams_points", table_name="tournament_teams")
    op.drop_index("ix_tournament_teams_tournament_id", table_name="tournament_teams")
    op.drop_table("tournament_teams")

    op.drop_index("ix_tournaments_status", table_name="tournaments")
    op.drop_table("tournaments")

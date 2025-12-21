"""Add Player, BattingScorecard, BowlingScorecard, and Delivery models.

Revision ID: m3h4i5j6k7l8
Revises: l2g3h4i5j6k7
Create Date: 2025-12-20 23:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m3h4i5j6k7l8"
down_revision: str | None = "l2g3h4i5j6k7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create Player, BattingScorecard, BowlingScorecard, and Delivery tables."""
    # Create players table
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("jersey_number", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_players_id"), "players", ["id"], unique=False)
    op.create_index(op.f("ix_players_name"), "players", ["name"], unique=False)

    # Create batting_scorecards table
    op.create_table(
        "batting_scorecards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("runs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("balls_faced", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fours", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sixes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("minutes_at_crease", sa.Integer(), nullable=True),
        sa.Column("is_out", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dismissal_type", sa.String(length=50), nullable=True),
        sa.Column("bowler_id", sa.Integer(), nullable=True),
        sa.Column("fielder_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bowler_id"], ["players.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["fielder_id"], ["players.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_batting_scorecards_game_id"),
        "batting_scorecards",
        ["game_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_batting_scorecards_player_id"),
        "batting_scorecards",
        ["player_id"],
        unique=False,
    )

    # Create bowling_scorecards table
    op.create_table(
        "bowling_scorecards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("overs_bowled", sa.Float(), nullable=False, server_default="0"),
        sa.Column("balls_bowled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("runs_conceded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wickets_taken", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("maiden_overs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wides", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("no_balls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_bowling_scorecards_game_id"),
        "bowling_scorecards",
        ["game_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_bowling_scorecards_player_id"),
        "bowling_scorecards",
        ["player_id"],
        unique=False,
    )

    # Create deliveries table
    op.create_table(
        "deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("inning_number", sa.Integer(), nullable=False),
        sa.Column("over_number", sa.Integer(), nullable=False),
        sa.Column("ball_number", sa.Integer(), nullable=False),
        sa.Column("bowler_id", sa.Integer(), nullable=False),
        sa.Column("batter_id", sa.Integer(), nullable=False),
        sa.Column("non_striker_id", sa.Integer(), nullable=False),
        sa.Column("runs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("runs_off_bat", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extra_type", sa.String(length=10), nullable=True),
        sa.Column("extra_runs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_wicket", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("wicket_type", sa.String(length=50), nullable=True),
        sa.Column("wicket_fielder_id", sa.Integer(), nullable=True),
        sa.Column("is_legal", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batter_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bowler_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["non_striker_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["wicket_fielder_id"], ["players.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_deliveries_game_id"),
        "deliveries",
        ["game_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_deliveries_batter_id"),
        "deliveries",
        ["batter_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_deliveries_bowler_id"),
        "deliveries",
        ["bowler_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop Player, BattingScorecard, BowlingScorecard, and Delivery tables."""
    op.drop_index(op.f("ix_deliveries_bowler_id"), table_name="deliveries")
    op.drop_index(op.f("ix_deliveries_batter_id"), table_name="deliveries")
    op.drop_index(op.f("ix_deliveries_game_id"), table_name="deliveries")
    op.drop_table("deliveries")

    op.drop_index(op.f("ix_bowling_scorecards_player_id"), table_name="bowling_scorecards")
    op.drop_index(op.f("ix_bowling_scorecards_game_id"), table_name="bowling_scorecards")
    op.drop_table("bowling_scorecards")

    op.drop_index(op.f("ix_batting_scorecards_player_id"), table_name="batting_scorecards")
    op.drop_index(op.f("ix_batting_scorecards_game_id"), table_name="batting_scorecards")
    op.drop_table("batting_scorecards")

    op.drop_index(op.f("ix_players_name"), table_name="players")
    op.drop_index(op.f("ix_players_id"), table_name="players")
    op.drop_table("players")

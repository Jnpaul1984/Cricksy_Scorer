"""add_player_profiles_and_achievements

Revision ID: e1a2b3c4d5e6
Revises: d2bd42f8d9e8
Create Date: 2025-11-01 23:42:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e1a2b3c4d5e6"
down_revision = "d2bd42f8d9e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create achievement_type enum
    achievement_type_enum = postgresql.ENUM(
        "century",
        "half_century",
        "five_wickets",
        "best_scorer",
        "best_bowler",
        "hat_trick",
        "golden_duck",
        "maiden_over",
        "six_sixes",
        "perfect_catch",
        name="achievement_type",
        create_type=False,
    )
    achievement_type_enum.create(op.get_bind(), checkfirst=True)

    # Create player_profiles table
    op.create_table(
        "player_profiles",
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("player_name", sa.String(), nullable=False),
        sa.Column("total_matches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "total_innings_batted", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "total_runs_scored", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "total_balls_faced", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("total_fours", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_sixes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("times_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("highest_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("centuries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("half_centuries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "total_innings_bowled", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "total_overs_bowled", sa.Float(), nullable=False, server_default="0.0"
        ),
        sa.Column(
            "total_runs_conceded", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("total_wickets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best_bowling_figures", sa.String(), nullable=True),
        sa.Column(
            "five_wicket_hauls", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("maidens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("catches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stumpings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("run_outs", sa.Integer(), nullable=False, server_default="0"),
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
        sa.PrimaryKeyConstraint("player_id"),
    )
    op.create_index(
        "ix_player_profiles_batting_avg",
        "player_profiles",
        ["total_runs_scored", "times_out"],
    )
    op.create_index("ix_player_profiles_player_id", "player_profiles", ["player_id"])
    op.create_index(
        "ix_player_profiles_total_runs", "player_profiles", ["total_runs_scored"]
    )
    op.create_index(
        "ix_player_profiles_total_wickets", "player_profiles", ["total_wickets"]
    )

    # Create player_achievements table
    op.create_table(
        "player_achievements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=True),
        sa.Column(
            "achievement_type",
            sa.Enum(
                "century",
                "half_century",
                "five_wickets",
                "best_scorer",
                "best_bowler",
                "hat_trick",
                "golden_duck",
                "maiden_over",
                "six_sixes",
                "perfect_catch",
                name="achievement_type",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("badge_icon", sa.String(), nullable=True),
        sa.Column(
            "earned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "achievement_metadata", sa.JSON(), nullable=False, server_default="{}"
        ),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["player_id"], ["player_profiles.player_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_player_achievements_earned_at", "player_achievements", ["earned_at"]
    )
    op.create_index(
        "ix_player_achievements_player_id", "player_achievements", ["player_id"]
    )
    op.create_index(
        "ix_player_achievements_type", "player_achievements", ["achievement_type"]
    )


def downgrade() -> None:
    # Drop indexes and tables
    op.drop_index("ix_player_achievements_type", table_name="player_achievements")
    op.drop_index("ix_player_achievements_player_id", table_name="player_achievements")
    op.drop_index("ix_player_achievements_earned_at", table_name="player_achievements")
    op.drop_table("player_achievements")

    op.drop_index("ix_player_profiles_total_wickets", table_name="player_profiles")
    op.drop_index("ix_player_profiles_total_runs", table_name="player_profiles")
    op.drop_index("ix_player_profiles_player_id", table_name="player_profiles")
    op.drop_index("ix_player_profiles_batting_avg", table_name="player_profiles")
    op.drop_table("player_profiles")

    # Drop enum type
    sa.Enum(name="achievement_type").drop(op.get_bind(), checkfirst=True)

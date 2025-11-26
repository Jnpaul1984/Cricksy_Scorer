"""add_fan_mode_features

Revision ID: b7d8e9f01234
Revises: a6d4c2f1b7e8
Create Date: 2025-11-17 05:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers, used by Alembic.
revision = "b7d8e9f01234"
down_revision = "a6d4c2f1b7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("games", sa.Column("created_by_user_id", sa.String(), nullable=True))
    op.add_column(
        "games",
        sa.Column(
            "is_fan_match",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_index("ix_games_is_fan_match", "games", ["is_fan_match"])
    op.create_index("ix_games_created_by_user_id", "games", ["created_by_user_id"])
    op.create_foreign_key(
        "fk_games_created_by_user_id_users",
        "games",
        "users",
        ["created_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    fan_favorite_type = postgresql.ENUM("player", "team", name="fan_favorite_type")
    fan_favorite_type.create(op.get_bind(), checkfirst=True)
    column_fan_favorite_type = postgresql.ENUM(
        "player",
        "team",
        name="fan_favorite_type",
        create_type=False,
    )

    op.create_table(
        "fan_favorites",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("favorite_type", column_fan_favorite_type, nullable=False),
        sa.Column("player_profile_id", sa.String(), nullable=True),
        sa.Column("team_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["player_profile_id"], ["player_profiles.player_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "(player_profile_id IS NOT NULL AND team_id IS NULL) OR "
            "(player_profile_id IS NULL AND team_id IS NOT NULL)",
            name="ck_fan_favorites_target",
        ),
    )
    op.create_index(
        "ix_fan_favorites_user_type", "fan_favorites", ["user_id", "favorite_type"]
    )
    op.create_index(
        "ix_fan_favorites_user_player",
        "fan_favorites",
        ["user_id", "player_profile_id"],
    )
    op.create_index(
        "ix_fan_favorites_user_team", "fan_favorites", ["user_id", "team_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_fan_favorites_user_team", table_name="fan_favorites")
    op.drop_index("ix_fan_favorites_user_player", table_name="fan_favorites")
    op.drop_index("ix_fan_favorites_user_type", table_name="fan_favorites")
    op.drop_table("fan_favorites")
    fan_favorite_type = postgresql.ENUM(name="fan_favorite_type")
    fan_favorite_type.drop(op.get_bind(), checkfirst=True)

    op.drop_constraint("fk_games_created_by_user_id_users", "games", type_="foreignkey")
    op.drop_index("ix_games_created_by_user_id", table_name="games")
    op.drop_index("ix_games_is_fan_match", table_name="games")
    op.drop_column("games", "is_fan_match")
    op.drop_column("games", "created_by_user_id")

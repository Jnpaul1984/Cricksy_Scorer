"""add phase10g competition roster intelligence

Revision ID: b6c7d8e9f0a1
Revises: a4b5c6d7e8f9
Create Date: 2026-05-17 19:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b6c7d8e9f0a1"
down_revision: str | None = "a4b5c6d7e8f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    roster_status_enum = sa.Enum(
        "named_squad",
        "playing_xi",
        "substitute",
        "unresolved",
        "unavailable_unknown",
        name="historical_competition_roster_status",
    )
    roster_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "historical_competition_roster_entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("competition_type", sa.String(length=64), nullable=False),
        sa.Column("competition_name", sa.String(length=255), nullable=True),
        sa.Column("season", sa.String(length=64), nullable=True),
        sa.Column("team_name", sa.String(length=255), nullable=True),
        sa.Column(
            "roster_status",
            roster_status_enum,
            nullable=False,
            server_default="unavailable_unknown",
        ),
        sa.Column("canonical_player_id", sa.Integer(), nullable=True),
        sa.Column("source_player_id", sa.String(), nullable=True),
        sa.Column("source_player_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_source_player_name", sa.String(length=255), nullable=False),
        sa.Column("source_schema", sa.String(length=64), nullable=False),
        sa.Column("source_system", sa.String(length=64), nullable=False),
        sa.Column("batch_id", sa.String(), nullable=True),
        sa.Column("game_id", sa.String(), nullable=True),
        sa.Column(
            "provenance_references",
            json_type,
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "conflict_references",
            json_type,
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "review_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["batch_id"], ["historical_import_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["canonical_player_id"], ["players.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["source_player_id"],
            ["historical_source_player_registry.source_player_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hist_comp_roster_unique_context",
        "historical_competition_roster_entries",
        [
            "source_system",
            "source_schema",
            "game_id",
            "team_name",
            "roster_status",
            "normalized_source_player_name",
        ],
        unique=True,
    )
    op.create_index(
        "ix_hist_comp_roster_comp_season_team",
        "historical_competition_roster_entries",
        ["competition_type", "competition_name", "season", "team_name"],
    )
    op.create_index(
        op.f("ix_historical_competition_roster_entries_competition_type"),
        "historical_competition_roster_entries",
        ["competition_type"],
    )
    op.create_index(
        op.f("ix_historical_competition_roster_entries_competition_name"),
        "historical_competition_roster_entries",
        ["competition_name"],
    )
    op.create_index(
        op.f("ix_historical_competition_roster_entries_season"),
        "historical_competition_roster_entries",
        ["season"],
    )
    op.create_index(
        op.f("ix_historical_competition_roster_entries_team_name"),
        "historical_competition_roster_entries",
        ["team_name"],
    )
    op.create_index(
        op.f("ix_historical_competition_roster_entries_roster_status"),
        "historical_competition_roster_entries",
        ["roster_status"],
    )
    op.create_index(
        op.f("ix_historical_competition_roster_entries_canonical_player_id"),
        "historical_competition_roster_entries",
        ["canonical_player_id"],
    )
    op.create_index(
        op.f("ix_historical_competition_roster_entries_source_player_id"),
        "historical_competition_roster_entries",
        ["source_player_id"],
    )
    op.create_index(
        op.f("ix_historical_competition_roster_entries_normalized_source_player_name"),
        "historical_competition_roster_entries",
        ["normalized_source_player_name"],
    )
    op.create_index(
        op.f("ix_historical_competition_roster_entries_source_schema"),
        "historical_competition_roster_entries",
        ["source_schema"],
    )
    op.create_index(
        op.f("ix_historical_competition_roster_entries_source_system"),
        "historical_competition_roster_entries",
        ["source_system"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_historical_competition_roster_entries_source_system"),
        table_name="historical_competition_roster_entries",
    )
    op.drop_index(
        op.f("ix_historical_competition_roster_entries_source_schema"),
        table_name="historical_competition_roster_entries",
    )
    op.drop_index(
        op.f("ix_historical_competition_roster_entries_normalized_source_player_name"),
        table_name="historical_competition_roster_entries",
    )
    op.drop_index(
        op.f("ix_historical_competition_roster_entries_source_player_id"),
        table_name="historical_competition_roster_entries",
    )
    op.drop_index(
        op.f("ix_historical_competition_roster_entries_canonical_player_id"),
        table_name="historical_competition_roster_entries",
    )
    op.drop_index(
        op.f("ix_historical_competition_roster_entries_roster_status"),
        table_name="historical_competition_roster_entries",
    )
    op.drop_index(
        op.f("ix_historical_competition_roster_entries_team_name"),
        table_name="historical_competition_roster_entries",
    )
    op.drop_index(
        op.f("ix_historical_competition_roster_entries_season"),
        table_name="historical_competition_roster_entries",
    )
    op.drop_index(
        op.f("ix_historical_competition_roster_entries_competition_name"),
        table_name="historical_competition_roster_entries",
    )
    op.drop_index(
        op.f("ix_historical_competition_roster_entries_competition_type"),
        table_name="historical_competition_roster_entries",
    )
    op.drop_index(
        "ix_hist_comp_roster_comp_season_team",
        table_name="historical_competition_roster_entries",
    )
    op.drop_index(
        "ix_hist_comp_roster_unique_context",
        table_name="historical_competition_roster_entries",
    )
    op.drop_table("historical_competition_roster_entries")
    sa.Enum(name="historical_competition_roster_status").drop(op.get_bind(), checkfirst=True)

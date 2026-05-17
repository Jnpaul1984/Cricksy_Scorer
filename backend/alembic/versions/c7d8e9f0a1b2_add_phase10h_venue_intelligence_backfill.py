"""add phase10h venue intelligence backfill

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-05-17 21:25:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d8e9f0a1b2"
down_revision: str | None = "b6c7d8e9f0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    verification_enum = postgresql.ENUM(
        "unverified",
        "verified",
        "review_required",
        name="historical_venue_verification_status",
        create_type=False,
    )
    verification_enum.create(op.get_bind(), checkfirst=True)
    resolution_enum = postgresql.ENUM(
        "resolved",
        "unresolved",
        "review_required",
        name="historical_venue_resolution_state",
        create_type=False,
    )
    resolution_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "historical_venue_intelligence",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_canonical_name", sa.String(length=255), nullable=False),
        sa.Column("short_name", sa.String(length=128), nullable=True),
        sa.Column("normalized_short_name", sa.String(length=128), nullable=True),
        sa.Column("alternate_names", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("country", sa.String(length=128), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("timezone", sa.String(length=128), nullable=True),
        sa.Column("venue_type", sa.String(length=64), nullable=True),
        sa.Column("indoor_outdoor", sa.String(length=32), nullable=True),
        sa.Column(
            "verification_status",
            verification_enum,
            nullable=False,
            server_default="unverified",
        ),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("created_from_import", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("provenance_references", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_historical_venue_intelligence_normalized_canonical_name"),
        "historical_venue_intelligence",
        ["normalized_canonical_name"],
    )
    op.create_index(
        op.f("ix_historical_venue_intelligence_normalized_short_name"),
        "historical_venue_intelligence",
        ["normalized_short_name"],
    )
    op.create_index(
        op.f("ix_historical_venue_intelligence_city"),
        "historical_venue_intelligence",
        ["city"],
    )
    op.create_index(
        op.f("ix_historical_venue_intelligence_country"),
        "historical_venue_intelligence",
        ["country"],
    )
    op.create_index(
        op.f("ix_historical_venue_intelligence_verification_status"),
        "historical_venue_intelligence",
        ["verification_status"],
    )

    op.create_table(
        "historical_venue_aliases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("venue_id", sa.String(), nullable=False),
        sa.Column("alias_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_alias", sa.String(length=255), nullable=False),
        sa.Column("source_schema", sa.String(length=64), nullable=True),
        sa.Column("source_system", sa.String(length=64), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("provenance_reference", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(["venue_id"], ["historical_venue_intelligence.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hist_venue_alias_unique",
        "historical_venue_aliases",
        ["venue_id", "normalized_alias"],
        unique=True,
    )
    op.create_index(
        op.f("ix_historical_venue_aliases_venue_id"),
        "historical_venue_aliases",
        ["venue_id"],
    )
    op.create_index(
        op.f("ix_historical_venue_aliases_normalized_alias"),
        "historical_venue_aliases",
        ["normalized_alias"],
    )

    op.create_table(
        "historical_venue_resolution_decisions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("batch_id", sa.String(), nullable=True),
        sa.Column("game_id", sa.String(), nullable=True),
        sa.Column("raw_imported_value", sa.String(length=255), nullable=False),
        sa.Column("normalized_raw_value", sa.String(length=255), nullable=False),
        sa.Column("canonical_venue_id", sa.String(), nullable=True),
        sa.Column(
            "resolution_state",
            resolution_enum,
            nullable=False,
            server_default="unresolved",
        ),
        sa.Column("matched_by", sa.String(length=64), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("unresolved_reason", sa.String(length=128), nullable=True),
        sa.Column("source_schema", sa.String(length=64), nullable=True),
        sa.Column("source_system", sa.String(length=64), nullable=True),
        sa.Column("competition_name", sa.String(length=255), nullable=True),
        sa.Column("season", sa.String(length=64), nullable=True),
        sa.Column("review_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("provenance_references", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("resolution_snapshot", json_type, nullable=False, server_default=sa.text("'{}'")),
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
        sa.ForeignKeyConstraint(["canonical_venue_id"], ["historical_venue_intelligence.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hist_venue_resolution_unique_context",
        "historical_venue_resolution_decisions",
        ["game_id", "normalized_raw_value", "source_schema", "source_system"],
        unique=True,
    )
    op.create_index(
        op.f("ix_historical_venue_resolution_decisions_batch_id"),
        "historical_venue_resolution_decisions",
        ["batch_id"],
    )
    op.create_index(
        op.f("ix_historical_venue_resolution_decisions_game_id"),
        "historical_venue_resolution_decisions",
        ["game_id"],
    )
    op.create_index(
        op.f("ix_historical_venue_resolution_decisions_normalized_raw_value"),
        "historical_venue_resolution_decisions",
        ["normalized_raw_value"],
    )
    op.create_index(
        op.f("ix_historical_venue_resolution_decisions_canonical_venue_id"),
        "historical_venue_resolution_decisions",
        ["canonical_venue_id"],
    )
    op.create_index(
        op.f("ix_historical_venue_resolution_decisions_resolution_state"),
        "historical_venue_resolution_decisions",
        ["resolution_state"],
    )
    op.create_index(
        op.f("ix_historical_venue_resolution_decisions_competition_name"),
        "historical_venue_resolution_decisions",
        ["competition_name"],
    )
    op.create_index(
        op.f("ix_historical_venue_resolution_decisions_season"),
        "historical_venue_resolution_decisions",
        ["season"],
    )

    op.create_table(
        "historical_venue_resolution_queue",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("decision_id", sa.String(), nullable=True),
        sa.Column("raw_imported_value", sa.String(length=255), nullable=False),
        sa.Column("normalized_raw_value", sa.String(length=255), nullable=False),
        sa.Column("source_schema", sa.String(length=64), nullable=True),
        sa.Column("source_system", sa.String(length=64), nullable=True),
        sa.Column("queue_state", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=128), nullable=False),
        sa.Column("review_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("provenance_references", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["historical_venue_resolution_decisions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hist_venue_queue_unique_context",
        "historical_venue_resolution_queue",
        ["normalized_raw_value", "source_schema", "source_system", "reason"],
        unique=True,
    )
    op.create_index(
        op.f("ix_historical_venue_resolution_queue_decision_id"),
        "historical_venue_resolution_queue",
        ["decision_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_historical_venue_resolution_queue_normalized_raw_value"),
        "historical_venue_resolution_queue",
        ["normalized_raw_value"],
    )

    op.create_table(
        "historical_competition_venue_usage",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("canonical_venue_id", sa.String(), nullable=False),
        sa.Column("competition_name", sa.String(length=255), nullable=True),
        sa.Column("season", sa.String(length=64), nullable=True),
        sa.Column("source_schema", sa.String(length=64), nullable=True),
        sa.Column("source_system", sa.String(length=64), nullable=True),
        sa.Column("matches_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("game_references", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("provenance_references", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("review_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
        sa.ForeignKeyConstraint(
            ["canonical_venue_id"], ["historical_venue_intelligence.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hist_comp_venue_usage_unique_context",
        "historical_competition_venue_usage",
        ["canonical_venue_id", "competition_name", "season", "source_schema", "source_system"],
        unique=True,
    )
    op.create_index(
        op.f("ix_historical_competition_venue_usage_canonical_venue_id"),
        "historical_competition_venue_usage",
        ["canonical_venue_id"],
    )
    op.create_index(
        op.f("ix_historical_competition_venue_usage_competition_name"),
        "historical_competition_venue_usage",
        ["competition_name"],
    )
    op.create_index(
        op.f("ix_historical_competition_venue_usage_season"),
        "historical_competition_venue_usage",
        ["season"],
    )


def downgrade() -> None:
    verification_enum = postgresql.ENUM(
        "unverified",
        "verified",
        "review_required",
        name="historical_venue_verification_status",
        create_type=False,
    )
    resolution_enum = postgresql.ENUM(
        "resolved",
        "unresolved",
        "review_required",
        name="historical_venue_resolution_state",
        create_type=False,
    )

    op.drop_index(
        op.f("ix_historical_competition_venue_usage_season"),
        table_name="historical_competition_venue_usage",
    )
    op.drop_index(
        op.f("ix_historical_competition_venue_usage_competition_name"),
        table_name="historical_competition_venue_usage",
    )
    op.drop_index(
        op.f("ix_historical_competition_venue_usage_canonical_venue_id"),
        table_name="historical_competition_venue_usage",
    )
    op.drop_index(
        "ix_hist_comp_venue_usage_unique_context",
        table_name="historical_competition_venue_usage",
    )
    op.drop_table("historical_competition_venue_usage")

    op.drop_index(
        op.f("ix_historical_venue_resolution_queue_normalized_raw_value"),
        table_name="historical_venue_resolution_queue",
    )
    op.drop_index(
        op.f("ix_historical_venue_resolution_queue_decision_id"),
        table_name="historical_venue_resolution_queue",
    )
    op.drop_index("ix_hist_venue_queue_unique_context", table_name="historical_venue_resolution_queue")
    op.drop_table("historical_venue_resolution_queue")

    op.drop_index(
        op.f("ix_historical_venue_resolution_decisions_season"),
        table_name="historical_venue_resolution_decisions",
    )
    op.drop_index(
        op.f("ix_historical_venue_resolution_decisions_competition_name"),
        table_name="historical_venue_resolution_decisions",
    )
    op.drop_index(
        op.f("ix_historical_venue_resolution_decisions_resolution_state"),
        table_name="historical_venue_resolution_decisions",
    )
    op.drop_index(
        op.f("ix_historical_venue_resolution_decisions_canonical_venue_id"),
        table_name="historical_venue_resolution_decisions",
    )
    op.drop_index(
        op.f("ix_historical_venue_resolution_decisions_normalized_raw_value"),
        table_name="historical_venue_resolution_decisions",
    )
    op.drop_index(
        op.f("ix_historical_venue_resolution_decisions_game_id"),
        table_name="historical_venue_resolution_decisions",
    )
    op.drop_index(
        op.f("ix_historical_venue_resolution_decisions_batch_id"),
        table_name="historical_venue_resolution_decisions",
    )
    op.drop_index(
        "ix_hist_venue_resolution_unique_context",
        table_name="historical_venue_resolution_decisions",
    )
    op.drop_table("historical_venue_resolution_decisions")

    op.drop_index(
        op.f("ix_historical_venue_aliases_normalized_alias"),
        table_name="historical_venue_aliases",
    )
    op.drop_index(
        op.f("ix_historical_venue_aliases_venue_id"),
        table_name="historical_venue_aliases",
    )
    op.drop_index("ix_hist_venue_alias_unique", table_name="historical_venue_aliases")
    op.drop_table("historical_venue_aliases")

    op.drop_index(
        op.f("ix_historical_venue_intelligence_verification_status"),
        table_name="historical_venue_intelligence",
    )
    op.drop_index(
        op.f("ix_historical_venue_intelligence_country"),
        table_name="historical_venue_intelligence",
    )
    op.drop_index(
        op.f("ix_historical_venue_intelligence_city"),
        table_name="historical_venue_intelligence",
    )
    op.drop_index(
        op.f("ix_historical_venue_intelligence_normalized_short_name"),
        table_name="historical_venue_intelligence",
    )
    op.drop_index(
        op.f("ix_historical_venue_intelligence_normalized_canonical_name"),
        table_name="historical_venue_intelligence",
    )
    op.drop_table("historical_venue_intelligence")

    resolution_enum.drop(op.get_bind(), checkfirst=True)
    verification_enum.drop(op.get_bind(), checkfirst=True)

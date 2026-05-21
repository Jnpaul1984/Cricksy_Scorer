"""add historical player identity registry

Revision ID: f2e3d4c5b6a7
Revises: d7e9a4b6c1f2
Create Date: 2026-05-17 17:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2e3d4c5b6a7"
down_revision: str | None = "d7e9a4b6c1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

historical_player_resolution_state = postgresql.ENUM(
    "unresolved",
    "auto_resolved",
    "manually_resolved",
    "ambiguous",
    "blocked",
    "duplicate",
    name="historical_player_resolution_state",
    create_type=False,
)
json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    bind = op.get_bind()
    use_postgres_enum = bind.dialect.name == "postgresql"
    if use_postgres_enum:
        historical_player_resolution_state.create(bind, checkfirst=True)
    resolution_state_type = (
        historical_player_resolution_state if use_postgres_enum else sa.String(length=32)
    )

    op.create_table(
        "historical_source_player_registry",
        sa.Column("source_player_id", sa.String(), nullable=False),
        sa.Column("source_player_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("source_schema", sa.String(length=64), nullable=False),
        sa.Column("source_system", sa.String(length=64), nullable=False),
        sa.Column(
            "resolution_state",
            resolution_state_type,
            nullable=False,
            server_default="unresolved",
        ),
        sa.Column("canonical_player_id", sa.Integer(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("mapping_method", sa.String(length=64), nullable=True),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("manual_override", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("match_references", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "competition_references", json_type, nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column(
            "provenance_references", json_type, nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("alias_references", json_type, nullable=False, server_default=sa.text("'[]'")),
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
        sa.ForeignKeyConstraint(["canonical_player_id"], ["players.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("source_player_id"),
    )
    op.create_index(
        "ix_hist_source_player_unique_key",
        "historical_source_player_registry",
        ["source_system", "source_schema", "normalized_name"],
        unique=True,
    )
    op.create_index(
        "ix_historical_source_player_registry_normalized_name",
        "historical_source_player_registry",
        ["normalized_name"],
    )
    op.create_index(
        "ix_historical_source_player_registry_resolution_state",
        "historical_source_player_registry",
        ["resolution_state"],
    )
    op.create_index(
        "ix_historical_source_player_registry_canonical_player_id",
        "historical_source_player_registry",
        ["canonical_player_id"],
    )

    op.create_table(
        "historical_source_player_aliases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_player_id", sa.String(), nullable=False),
        sa.Column("alias_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_alias", sa.String(length=255), nullable=False),
        sa.Column("source_schema", sa.String(length=64), nullable=False),
        sa.Column("source_system", sa.String(length=64), nullable=False),
        sa.Column(
            "provenance_reference", json_type, nullable=False, server_default=sa.text("'{}'")
        ),
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
        sa.ForeignKeyConstraint(
            ["source_player_id"],
            ["historical_source_player_registry.source_player_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_historical_source_player_aliases_source_player_id",
        "historical_source_player_aliases",
        ["source_player_id"],
    )
    op.create_index(
        "ix_historical_source_player_aliases_normalized_alias",
        "historical_source_player_aliases",
        ["normalized_alias"],
    )
    op.create_index(
        "ix_hist_source_player_alias_unique",
        "historical_source_player_aliases",
        ["source_player_id", "normalized_alias", "source_schema", "source_system"],
        unique=True,
    )

    op.create_table(
        "historical_player_resolution_queue",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_player_id", sa.String(), nullable=False),
        sa.Column("queue_state", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("reason", sa.String(length=128), nullable=False, server_default="unresolved"),
        sa.Column("resolution_snapshot", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_player_id"],
            ["historical_source_player_registry.source_player_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_player_id"),
    )
    op.create_index(
        "ix_historical_player_resolution_queue_source_player_id",
        "historical_player_resolution_queue",
        ["source_player_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_historical_player_resolution_queue_source_player_id",
        table_name="historical_player_resolution_queue",
    )
    op.drop_table("historical_player_resolution_queue")

    op.drop_index(
        "ix_hist_source_player_alias_unique", table_name="historical_source_player_aliases"
    )
    op.drop_index(
        "ix_historical_source_player_aliases_normalized_alias",
        table_name="historical_source_player_aliases",
    )
    op.drop_index(
        "ix_historical_source_player_aliases_source_player_id",
        table_name="historical_source_player_aliases",
    )
    op.drop_table("historical_source_player_aliases")

    op.drop_index(
        "ix_historical_source_player_registry_canonical_player_id",
        table_name="historical_source_player_registry",
    )
    op.drop_index(
        "ix_historical_source_player_registry_resolution_state",
        table_name="historical_source_player_registry",
    )
    op.drop_index(
        "ix_historical_source_player_registry_normalized_name",
        table_name="historical_source_player_registry",
    )
    op.drop_index(
        "ix_hist_source_player_unique_key", table_name="historical_source_player_registry"
    )
    op.drop_table("historical_source_player_registry")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        historical_player_resolution_state.drop(bind, checkfirst=True)

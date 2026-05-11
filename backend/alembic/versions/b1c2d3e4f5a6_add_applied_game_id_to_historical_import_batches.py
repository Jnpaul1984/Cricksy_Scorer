"""add_applied_game_id_to_historical_import_batches

Revision ID: b1c2d3e4f5a6
Revises: a9b8c7d6e5f4
Create Date: 2026-05-11 00:00:00.000000

Phase 5D: Historical JSON Import Apply MVP.

Adds a single nullable ``applied_game_id`` column to
``historical_import_batches`` so that the apply path can record which Game
row was created when a batch is finalized.  This enables reliable rollback
and audit without mutating the original dry-run audit data in
``dry_run_summary``.

No Game/Delivery/Player/Team structure is altered by this migration.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: str | Sequence[str] | None = "a9b8c7d6e5f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add applied_game_id to historical_import_batches."""
    op.add_column(
        "historical_import_batches",
        sa.Column("applied_game_id", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Remove applied_game_id from historical_import_batches."""
    op.drop_column("historical_import_batches", "applied_game_id")

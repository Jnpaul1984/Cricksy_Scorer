"""add_historical_import_batch_table

Revision ID: a9b8c7d6e5f4
Revises: r5s6t7u8v9w0
Create Date: 2026-05-10 22:00:00.000000

Phase 5C: Historical Import Batch Tracking + Duplicate Detection Schema.

Adds the `historical_import_batches` table for persisting import metadata
and duplicate detection state.  No Game/Delivery/Player/Team rows are
created by this migration.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, Sequence[str], None] = "r5s6t7u8v9w0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create historical_import_batches table."""
    conn = op.get_bind()
    is_postgres = conn.dialect.name == "postgresql"

    dry_run_summary_col = (
        sa.Column("dry_run_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
        if is_postgres
        else sa.Column("dry_run_summary", sa.JSON(), nullable=True)
    )

    op.create_table(
        "historical_import_batches",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner_user_id", sa.String(), nullable=True),
        sa.Column("owner_org_id", sa.String(), nullable=True),
        sa.Column("source_filename", sa.String(512), nullable=True),
        sa.Column("source_format", sa.String(64), nullable=False),
        sa.Column("source_hash_sha256", sa.String(64), nullable=False),
        sa.Column("semantic_key", sa.String(512), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("innings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delivery_count", sa.Integer(), nullable=False, server_default="0"),
        dry_run_summary_col,
        sa.Column("is_finalized", sa.Boolean(), nullable=False, server_default="false"),
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

    # Indexes for fast duplicate detection lookups
    op.create_index(
        "ix_hist_import_batches_owner_user_id",
        "historical_import_batches",
        ["owner_user_id"],
    )
    op.create_index(
        "ix_hist_import_batches_owner_org_id",
        "historical_import_batches",
        ["owner_org_id"],
    )
    op.create_index(
        "ix_hist_import_batches_source_hash_sha256",
        "historical_import_batches",
        ["source_hash_sha256"],
    )
    op.create_index(
        "ix_hist_import_batches_semantic_key",
        "historical_import_batches",
        ["semantic_key"],
    )
    op.create_index(
        "ix_hist_import_hash_user",
        "historical_import_batches",
        ["source_hash_sha256", "owner_user_id"],
    )
    op.create_index(
        "ix_hist_import_hash_org",
        "historical_import_batches",
        ["source_hash_sha256", "owner_org_id"],
    )
    op.create_index(
        "ix_hist_import_semantic_user",
        "historical_import_batches",
        ["semantic_key", "owner_user_id"],
    )
    op.create_index(
        "ix_hist_import_semantic_org",
        "historical_import_batches",
        ["semantic_key", "owner_org_id"],
    )


def downgrade() -> None:
    """Drop historical_import_batches table."""
    op.drop_index("ix_hist_import_semantic_org", table_name="historical_import_batches")
    op.drop_index("ix_hist_import_semantic_user", table_name="historical_import_batches")
    op.drop_index("ix_hist_import_hash_org", table_name="historical_import_batches")
    op.drop_index("ix_hist_import_hash_user", table_name="historical_import_batches")
    op.drop_index("ix_hist_import_batches_semantic_key", table_name="historical_import_batches")
    op.drop_index(
        "ix_hist_import_batches_source_hash_sha256", table_name="historical_import_batches"
    )
    op.drop_index("ix_hist_import_batches_owner_org_id", table_name="historical_import_batches")
    op.drop_index("ix_hist_import_batches_owner_user_id", table_name="historical_import_batches")
    op.drop_table("historical_import_batches")

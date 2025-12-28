"""Add staged video analysis fields and statuses.

Revision ID: p2q3r4s5t6u7
Revises: abc753bb4d7c
Create Date: 2025-12-28

Adds:
- New enum values for video_analysis_job_status (quick_running/quick_done/deep_running/done)
- progress_pct, stage, deep_enabled
- quick_results, deep_results
- per-stage timestamps

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "p2q3r4s5t6u7"
down_revision: str | Sequence[str] | None = "abc753bb4d7c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    # Extend enum in Postgres
    if dialect_name == "postgresql":
        op.execute(
            "ALTER TYPE video_analysis_job_status ADD VALUE IF NOT EXISTS 'quick_running'"
        )
        op.execute("ALTER TYPE video_analysis_job_status ADD VALUE IF NOT EXISTS 'quick_done'")
        op.execute(
            "ALTER TYPE video_analysis_job_status ADD VALUE IF NOT EXISTS 'deep_running'"
        )
        op.execute("ALTER TYPE video_analysis_job_status ADD VALUE IF NOT EXISTS 'done'")

    # Add progress/stage columns
    op.add_column(
        "video_analysis_jobs",
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "video_analysis_jobs",
        sa.Column("stage", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "video_analysis_jobs",
        sa.Column("deep_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # Add staged results
    op.add_column("video_analysis_jobs", sa.Column("quick_results", sa.JSON(), nullable=True))
    op.add_column("video_analysis_jobs", sa.Column("deep_results", sa.JSON(), nullable=True))

    # Per-stage timestamps
    op.add_column(
        "video_analysis_jobs",
        sa.Column("quick_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "video_analysis_jobs",
        sa.Column("quick_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "video_analysis_jobs",
        sa.Column("deep_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "video_analysis_jobs",
        sa.Column("deep_completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Remove server_default now that existing rows are backfilled
    op.alter_column("video_analysis_jobs", "progress_pct", server_default=None)
    op.alter_column("video_analysis_jobs", "deep_enabled", server_default=None)


def downgrade() -> None:
    # Note: PostgreSQL enums cannot easily have values removed; we leave enum values in place.

    op.drop_column("video_analysis_jobs", "deep_completed_at")
    op.drop_column("video_analysis_jobs", "deep_started_at")
    op.drop_column("video_analysis_jobs", "quick_completed_at")
    op.drop_column("video_analysis_jobs", "quick_started_at")

    op.drop_column("video_analysis_jobs", "deep_results")
    op.drop_column("video_analysis_jobs", "quick_results")

    op.drop_column("video_analysis_jobs", "deep_enabled")
    op.drop_column("video_analysis_jobs", "stage")
    op.drop_column("video_analysis_jobs", "progress_pct")

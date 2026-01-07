"""add findings and report fields to VideoAnalysisJob

Revision ID: h3i4j5k6l7m8
Revises: g2h3i4j5k6l7
Create Date: 2026-01-06 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "h3i4j5k6l7m8"
down_revision: str | Sequence[str] | None = "g2h3i4j5k6l7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add extracted findings and report fields for frontend consumption.

    These fields store the critical artifacts (findings, report) extracted from
    quick_results and deep_results for direct frontend access without parsing.
    """
    # Add extracted artifact fields for quick pass
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "quick_findings",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="Quick pass findings extracted from quick_results",
        ),
    )
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "quick_report",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="Quick pass report extracted from quick_results",
        ),
    )

    # Add extracted artifact fields for deep pass
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "deep_findings",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="Deep pass findings extracted from deep_results",
        ),
    )
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "deep_report",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="Deep pass report extracted from deep_results",
        ),
    )

    # Add S3 keys for result artifacts
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "quick_results_s3_key",
            sa.String(length=500),
            nullable=True,
            comment="S3 key for quick results JSON",
        ),
    )
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "deep_results_s3_key",
            sa.String(length=500),
            nullable=True,
            comment="S3 key for deep results JSON",
        ),
    )


def downgrade() -> None:
    """Remove findings and report fields."""
    op.drop_column("video_analysis_jobs", "deep_results_s3_key")
    op.drop_column("video_analysis_jobs", "quick_results_s3_key")
    op.drop_column("video_analysis_jobs", "deep_report")
    op.drop_column("video_analysis_jobs", "deep_findings")
    op.drop_column("video_analysis_jobs", "quick_report")
    op.drop_column("video_analysis_jobs", "quick_findings")

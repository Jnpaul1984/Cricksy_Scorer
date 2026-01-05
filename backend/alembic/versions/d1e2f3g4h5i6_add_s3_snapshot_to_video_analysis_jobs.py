"""Add s3_bucket and s3_key snapshot to video_analysis_jobs

Revision ID: d1e2f3g4h5i6
Revises: a1b2c3d4e5f6
Create Date: 2026-01-05 14:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d1e2f3g4h5i6"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    """Add S3 location snapshot columns to video_analysis_jobs.
    
    These columns store an immutable snapshot of the S3 bucket/key at job creation time,
    preventing intermittent 404s caused by session.s3_key mutations during retries or
    re-uploads.
    """
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "s3_bucket",
            sa.String(length=255),
            nullable=True,
            comment="S3 bucket snapshot at job creation",
        ),
    )
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "s3_key",
            sa.String(length=500),
            nullable=True,
            comment="S3 key snapshot at job creation",
        ),
    )


def downgrade():
    """Remove S3 snapshot columns from video_analysis_jobs."""
    op.drop_column("video_analysis_jobs", "s3_key")
    op.drop_column("video_analysis_jobs", "s3_bucket")

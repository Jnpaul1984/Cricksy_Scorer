"""add video analysis chunk model and chunking fields

Revision ID: g2h3i4j5k6l7
Revises: f1a2b3c4d5e6
Create Date: 2026-01-05 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "g2h3i4j5k6l7"
down_revision: str | Sequence[str] | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add VideoAnalysisChunk model and chunking fields to VideoAnalysisJob.

    Enables GPU-accelerated parallel video processing:
    - Chunks allow concurrent GPU workers to process video segments
    - Progress tracking via completed_chunks/total_chunks
    - Resumable jobs via chunk checkpoints
    """
    # Create chunk status enum using PostgreSQL ENUM with checkfirst for idempotency
    chunk_status_enum = postgresql.ENUM(
        'queued', 'processing', 'completed', 'failed',
        name='video_analysis_chunk_status',
        create_type=False  # We'll create it separately
    )
    chunk_status_enum.create(op.get_bind(), checkfirst=True)

    # Add chunking fields to video_analysis_jobs
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "deep_mode",
            sa.String(length=50),
            nullable=True,
            comment="Deep processing mode: cpu (monolithic) or gpu (chunked)",
        ),
    )
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "total_chunks",
            sa.Integer(),
            nullable=True,
            comment="Total number of chunks for GPU processing",
        ),
    )
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "completed_chunks",
            sa.Integer(),
            nullable=True,
            comment="Number of completed chunks",
        ),
    )
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "video_duration_seconds",
            sa.Float(),
            nullable=True,
            comment="Video duration in seconds",
        ),
    )

    # Set default deep_mode=cpu for existing jobs
    op.execute("UPDATE video_analysis_jobs SET deep_mode = 'cpu' WHERE deep_mode IS NULL")

    # Create video_analysis_chunks table
    op.create_table(
        "video_analysis_chunks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "job_id",
            sa.String(),
            nullable=False,
            comment="Reference to parent job",
        ),
        sa.Column(
            "chunk_index",
            sa.Integer(),
            nullable=False,
            comment="0-based chunk index for ordering",
        ),
        sa.Column(
            "start_sec",
            sa.Float(),
            nullable=False,
            comment="Start time in seconds",
        ),
        sa.Column(
            "end_sec",
            sa.Float(),
            nullable=False,
            comment="End time in seconds",
        ),
        sa.Column(
            "status",
            chunk_status_enum,
            nullable=False,
            server_default="queued",
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of processing attempts",
        ),
        sa.Column(
            "artifact_s3_key",
            sa.String(length=500),
            nullable=True,
            comment="S3 key for chunk JSON output: jobs/{job_id}/chunks/chunk_{index:04d}.json",
        ),
        sa.Column(
            "runtime_ms",
            sa.Integer(),
            nullable=True,
            comment="Processing time in milliseconds",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Error details if chunk failed",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When processing started",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When processing completed",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["video_analysis_jobs.id"],
            ondelete="CASCADE",
        ),
    )

    # Create indexes for efficient chunk claiming and querying
    op.create_index(
        "ix_analysis_chunks_job_id",
        "video_analysis_chunks",
        ["job_id"],
    )
    op.create_index(
        "ix_analysis_chunks_status",
        "video_analysis_chunks",
        ["status"],
    )
    op.create_index(
        "ix_analysis_chunks_job_chunk_idx",
        "video_analysis_chunks",
        ["job_id", "chunk_index"],
        unique=True,
    )


def downgrade() -> None:
    """Remove VideoAnalysisChunk model and chunking fields."""
    # Drop indexes
    op.drop_index("ix_analysis_chunks_job_chunk_idx", table_name="video_analysis_chunks")
    op.drop_index("ix_analysis_chunks_status", table_name="video_analysis_chunks")
    op.drop_index("ix_analysis_chunks_job_id", table_name="video_analysis_chunks")

    # Drop table
    op.drop_table("video_analysis_chunks")

    # Drop enum
    op.execute("DROP TYPE video_analysis_chunk_status")

    # Drop columns from video_analysis_jobs
    op.drop_column("video_analysis_jobs", "video_duration_seconds")
    op.drop_column("video_analysis_jobs", "completed_chunks")
    op.drop_column("video_analysis_jobs", "total_chunks")
    op.drop_column("video_analysis_jobs", "deep_mode")

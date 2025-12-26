"""Add video_sessions and video_analysis_jobs tables for Coach Pro Plus.

Revision ID: n4i5j6k7l8m9
Revises: m3h4i5j6k7l8
Create Date: 2025-12-23 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "n4i5j6k7l8m9"
down_revision: str | None = "m3h4i5j6k7l8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enums with checkfirst=True to avoid duplicate creation
    owner_type_enum = sa.Enum("coach", "org", name="owner_type", create_type=False)

    video_session_status_enum = sa.Enum(
        "pending",
        "uploaded",
        "processing",
        "ready",
        "failed",
        name="video_session_status",
        create_type=False,
    )

    video_analysis_job_status_enum = sa.Enum(
        "queued",
        "processing",
        "completed",
        "failed",
        name="video_analysis_job_status",
        create_type=False,
    )

    # Create video_sessions table
    op.create_table(
        "video_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner_type", owner_type_enum, nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("player_ids", sa.JSON(), nullable=False),
        sa.Column("s3_bucket", sa.String(length=255), nullable=True),
        sa.Column("s3_key", sa.String(length=500), nullable=True),
        sa.Column(
            "status",
            video_session_status_enum,
            nullable=False,
        ),
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
    op.create_index("ix_video_sessions_owner", "video_sessions", ["owner_type", "owner_id"])
    op.create_index("ix_video_sessions_status", "video_sessions", ["status"])
    op.create_index("ix_video_sessions_created_at", "video_sessions", ["created_at"])

    # Create video_analysis_jobs table
    op.create_table(
        "video_analysis_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("sample_fps", sa.Integer(), nullable=False),
        sa.Column("include_frames", sa.Boolean(), nullable=False),
        sa.Column(
            "status",
            video_analysis_job_status_enum,
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sqs_message_id", sa.String(length=255), nullable=True),
        sa.Column("results", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["video_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_jobs_session_id", "video_analysis_jobs", ["session_id"])
    op.create_index("ix_analysis_jobs_status", "video_analysis_jobs", ["status"])
    op.create_index("ix_analysis_jobs_created_at", "video_analysis_jobs", ["created_at"])
    op.create_index("ix_analysis_jobs_sqs_message_id", "video_analysis_jobs", ["sqs_message_id"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_analysis_jobs_sqs_message_id", table_name="video_analysis_jobs")
    op.drop_index("ix_analysis_jobs_created_at", table_name="video_analysis_jobs")
    op.drop_index("ix_analysis_jobs_status", table_name="video_analysis_jobs")
    op.drop_index("ix_analysis_jobs_session_id", table_name="video_analysis_jobs")

    # Drop tables
    op.drop_table("video_analysis_jobs")

    op.drop_index("ix_video_sessions_created_at", table_name="video_sessions")
    op.drop_index("ix_video_sessions_status", table_name="video_sessions")
    op.drop_index("ix_video_sessions_owner", table_name="video_sessions")

    op.drop_table("video_sessions")

    # Drop enums
    sa.Enum(name="video_analysis_job_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="video_session_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="owner_type").drop(op.get_bind(), checkfirst=True)

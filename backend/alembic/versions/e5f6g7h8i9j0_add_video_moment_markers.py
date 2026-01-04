"""Add video_moment_markers table for fielding/wicketkeeping analysis

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-01-04 11:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "e5f6g7h8i9j0"
down_revision = "d4e5f6g7h8i9"
branch_labels = None
depends_on = None


def upgrade():
    """Create video_moment_markers table for timestamped moments in videos."""
    # Create enum for moment types (skip if exists)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE video_moment_type AS ENUM (
                'setup', 'catch', 'throw', 'dive', 'stumping', 'other'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.create_table(
        "video_moment_markers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("video_session_id", sa.String(), nullable=False),
        sa.Column(
            "timestamp_ms",
            sa.BigInteger(),
            nullable=False,
            comment="Timestamp in milliseconds from video start",
        ),
        sa.Column(
            "moment_type",
            postgresql.ENUM(
                "setup",
                "catch",
                "throw",
                "dive",
                "stumping",
                "other",
                name="video_moment_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_by", sa.String(), nullable=False, comment="Coach user_id who created marker"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["video_session_id"], ["video_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
    )

    # Create indexes
    op.create_index(
        "ix_video_moment_markers_video_session_id",
        "video_moment_markers",
        ["video_session_id"],
        unique=False,
    )
    op.create_index(
        "ix_video_moment_markers_moment_type", "video_moment_markers", ["moment_type"], unique=False
    )
    op.create_index(
        "ix_video_moment_markers_timestamp_ms",
        "video_moment_markers",
        ["timestamp_ms"],
        unique=False,
    )

    # Add moment_marker_id to coach_notes (optional link)
    op.add_column(
        "coach_notes",
        sa.Column(
            "moment_marker_id",
            sa.String(),
            sa.ForeignKey("video_moment_markers.id", ondelete="SET NULL"),
            nullable=True,
            comment="Optional link to specific moment in video",
        ),
    )
    op.create_index(
        "ix_coach_notes_moment_marker_id", "coach_notes", ["moment_marker_id"], unique=False
    )


def downgrade():
    """Drop video_moment_markers table and related fields."""
    op.drop_index("ix_coach_notes_moment_marker_id", table_name="coach_notes")
    op.drop_column("coach_notes", "moment_marker_id")

    op.drop_index("ix_video_moment_markers_timestamp_ms", table_name="video_moment_markers")
    op.drop_index("ix_video_moment_markers_moment_type", table_name="video_moment_markers")
    op.drop_index("ix_video_moment_markers_video_session_id", table_name="video_moment_markers")
    op.drop_table("video_moment_markers")

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS video_moment_type")

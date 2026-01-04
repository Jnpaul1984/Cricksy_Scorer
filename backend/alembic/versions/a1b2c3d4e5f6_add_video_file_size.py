"""Add file_size_bytes to video_sessions

Revision ID: a1b2c3d4e5f6
Revises: j0e1f2g3h4i5
Create Date: 2026-01-03 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "3f8b9d2a1e4c"
branch_labels = None
depends_on = None


def upgrade():
    """Add file_size_bytes column to track video storage usage."""
    op.add_column(
        "video_sessions",
        sa.Column(
            "file_size_bytes",
            sa.BigInteger(),
            nullable=True,
            comment="File size in bytes for quota tracking",
        ),
    )

    # Create index for efficient quota queries
    op.create_index(
        "ix_video_sessions_owner_size",
        "video_sessions",
        ["owner_id", "status", "file_size_bytes"],
        unique=False,
    )


def downgrade():
    """Remove file_size_bytes column."""
    op.drop_index("ix_video_sessions_owner_size", table_name="video_sessions")
    op.drop_column("video_sessions", "file_size_bytes")

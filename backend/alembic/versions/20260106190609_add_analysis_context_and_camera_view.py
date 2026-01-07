"""add_analysis_context_and_camera_view

Revision ID: 20260106190609
Revises: 8fad14d07603
Create Date: 2026-01-06 19:06:09

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260106190609"
down_revision = "8fad14d07603"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get database connection to detect dialect
    conn = op.get_bind()
    is_postgres = conn.dialect.name == "postgresql"

    if is_postgres:
        # PostgreSQL: Create enums
        analysis_context_enum = postgresql.ENUM(
            "batting",
            "bowling",
            "wicketkeeping",
            "fielding",
            "mixed",
            name="analysis_context",
            create_type=False,
        )
        camera_view_enum = postgresql.ENUM(
            "side", "front", "behind", "other", name="camera_view", create_type=False
        )

        # Create enum types
        analysis_context_enum.create(conn, checkfirst=True)
        camera_view_enum.create(conn, checkfirst=True)

        # Add columns with enum types
        op.add_column(
            "video_sessions",
            sa.Column(
                "analysis_context",
                sa.Enum(
                    "batting",
                    "bowling",
                    "wicketkeeping",
                    "fielding",
                    "mixed",
                    name="analysis_context",
                ),
                nullable=True,
                comment="What is being analyzed",
            ),
        )
        op.add_column(
            "video_sessions",
            sa.Column(
                "camera_view",
                sa.Enum("side", "front", "behind", "other", name="camera_view"),
                nullable=True,
                comment="Camera angle",
            ),
        )
    else:
        # SQLite: Use VARCHAR instead of ENUM
        op.add_column("video_sessions", sa.Column("analysis_context", sa.String(20), nullable=True))
        op.add_column("video_sessions", sa.Column("camera_view", sa.String(20), nullable=True))

    # Create index on analysis_context
    op.create_index(
        op.f("ix_video_sessions_analysis_context"),
        "video_sessions",
        ["analysis_context"],
        unique=False,
    )


def downgrade() -> None:
    # Get database connection to detect dialect
    conn = op.get_bind()
    is_postgres = conn.dialect.name == "postgresql"

    # Drop index
    op.drop_index(op.f("ix_video_sessions_analysis_context"), table_name="video_sessions")

    # Drop columns
    op.drop_column("video_sessions", "camera_view")
    op.drop_column("video_sessions", "analysis_context")

    if is_postgres:
        # Drop enums only for PostgreSQL
        sa.Enum(name="camera_view").drop(conn, checkfirst=True)
        sa.Enum(name="analysis_context").drop(conn, checkfirst=True)

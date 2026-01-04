"""Add coach_notes table for player feedback

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-01-04 10:30:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "d4e5f6g7h8i9"
down_revision = "c3d4e5f6g7h8"
branch_labels = None
depends_on = None


def upgrade():
    """Create coach_notes table for storing coach feedback on players."""
    # Create enum for severity (skip if exists)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE coach_note_severity AS ENUM ('info', 'improvement', 'critical');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.create_table(
        "coach_notes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("coach_id", sa.String(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("video_session_id", sa.String(), nullable=True),
        sa.Column("note_text", sa.Text(), nullable=False),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String()),
            nullable=True,
            comment='Tags like ["footwork", "timing", "technique"]',
        ),
        sa.Column(
            "severity",
            postgresql.ENUM(
                "info", "improvement", "critical", name="coach_note_severity", create_type=False
            ),
            nullable=False,
            server_default="info",
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
        sa.ForeignKeyConstraint(["coach_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_session_id"], ["video_sessions.id"], ondelete="SET NULL"),
    )

    # Create indexes
    op.create_index("ix_coach_notes_coach_id", "coach_notes", ["coach_id"], unique=False)
    op.create_index("ix_coach_notes_player_id", "coach_notes", ["player_id"], unique=False)
    op.create_index(
        "ix_coach_notes_video_session_id", "coach_notes", ["video_session_id"], unique=False
    )
    op.create_index("ix_coach_notes_severity", "coach_notes", ["severity"], unique=False)
    op.create_index("ix_coach_notes_created_at", "coach_notes", ["created_at"], unique=False)


def downgrade():
    """Drop coach_notes table."""
    op.drop_index("ix_coach_notes_created_at", table_name="coach_notes")
    op.drop_index("ix_coach_notes_severity", table_name="coach_notes")
    op.drop_index("ix_coach_notes_video_session_id", table_name="coach_notes")
    op.drop_index("ix_coach_notes_player_id", table_name="coach_notes")
    op.drop_index("ix_coach_notes_coach_id", table_name="coach_notes")
    op.drop_table("coach_notes")

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS coach_note_severity")

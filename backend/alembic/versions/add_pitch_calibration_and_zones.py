"""add pitch calibration and target zones

Revision ID: pitch_calibration_001
Revises: z1a2b3c4d5e6
Create Date: 2026-01-14

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "pitch_calibration_001"
down_revision = "z1a2b3c4d5e6"  # Revises: add analysis_mode to video_analysis_job
branch_labels = None
depends_on = None


def upgrade():
    # Add pitch_corners column to video_sessions
    op.add_column(
        "video_sessions",
        sa.Column(
            "pitch_corners",
            sa.JSON(),
            nullable=True,
            comment=("4 corner points for pitch homography: " "[{x, y}, {x, y}, {x, y}, {x, y}]"),
        ),
    )

    # Create target_zones table (indexes created automatically via SQLAlchemy)
    op.create_table(
        "target_zones",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column(
            "owner_id",
            sa.String(),
            nullable=False,
            comment="Coach user_id who created the zone",
        ),
        sa.Column(
            "session_id",
            sa.String(),
            nullable=True,
            comment="Optional link to specific session",
        ),
        sa.Column(
            "name",
            sa.String(length=100),
            nullable=False,
            comment="Zone name (e.g., 'Yorker Line', 'Off Stump')",
        ),
        sa.Column(
            "shape",
            sa.String(length=20),
            nullable=False,
            server_default="rect",
            comment="Shape type: rect, circle, polygon",
        ),
        sa.Column(
            "definition_json",
            sa.JSON(),
            nullable=False,
            comment=(
                "Shape definition: {x, y, width, height} for rect, " "{cx, cy, r} for circle, etc."
            ),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["video_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes explicitly (not auto-created in migrations)
    op.create_index(
        op.f("ix_target_zones_owner_id"),
        "target_zones",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_target_zones_session_id"), "target_zones", ["session_id"], unique=False
    )


def downgrade():
    # Drop indexes
    op.drop_index(op.f("ix_target_zones_session_id"), table_name="target_zones")
    op.drop_index(op.f("ix_target_zones_owner_id"), table_name="target_zones")

    # Drop target_zones table
    op.drop_table("target_zones")

    # Remove pitch_corners column
    op.drop_column("video_sessions", "pitch_corners")

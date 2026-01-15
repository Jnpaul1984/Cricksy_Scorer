"""add coach suggestions and player summary

Revision ID: p3q4r5s6t7u8
Revises: c4daa06ced6b
Create Date: 2026-01-15 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "p3q4r5s6t7u8"
down_revision: Union[str, Sequence[str], None] = "c4daa06ced6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add Phase 3 coaching suggestions and player summary."""

    # Add coach suggestions to video_analysis_jobs
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "coach_suggestions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment=(
                "AI-generated coaching suggestions: "
                "{primary_focus, secondary_focus, coaching_cues, drills, "
                "proposed_next_goal, rationale}"
            ),
        ),
    )

    # Add player summary to video_analysis_jobs
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "player_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment=(
                "Player-facing simplified summary: "
                "{focus, what_to_practice, encouragement}"
            ),
        ),
    )


def downgrade() -> None:
    """Downgrade schema - remove Phase 3 columns."""
    op.drop_column("video_analysis_jobs", "player_summary")
    op.drop_column("video_analysis_jobs", "coach_suggestions")

"""add coach goals and outcomes tracking

Revision ID: j4k5l6m7n8o9
Revises: 8fad14d07603
Create Date: 2026-01-15 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "j4k5l6m7n8o9"
down_revision: Union[str, Sequence[str], None] = "8fad14d07603"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add Phase 2 coach goals and outcomes tracking."""
    
    # Add coach goals and outcomes to video_analysis_jobs
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "coach_goals",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Coach-defined goals: {zones: [{zone_id, target_accuracy}], metrics: [{code, target_score}]}",
        ),
    )
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "outcomes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Calculated outcomes vs goals: {zones: [...], metrics: [...], overall_compliance_pct}",
        ),
    )
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "goal_compliance_pct",
            sa.Float(),
            nullable=True,
            comment="Overall goal compliance percentage (0-100)",
        ),
    )
    
    # Add target accuracy and active flag to target_zones
    op.add_column(
        "target_zones",
        sa.Column(
            "target_accuracy",
            sa.Float(),
            nullable=True,
            comment="Target accuracy percentage (0.0-1.0) for goal compliance",
        ),
    )
    op.add_column(
        "target_zones",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Whether zone is active for analysis",
        ),
    )


def downgrade() -> None:
    """Downgrade schema - remove Phase 2 columns."""
    
    # Remove from target_zones
    op.drop_column("target_zones", "is_active")
    op.drop_column("target_zones", "target_accuracy")
    
    # Remove from video_analysis_jobs
    op.drop_column("video_analysis_jobs", "goal_compliance_pct")
    op.drop_column("video_analysis_jobs", "outcomes")
    op.drop_column("video_analysis_jobs", "coach_goals")

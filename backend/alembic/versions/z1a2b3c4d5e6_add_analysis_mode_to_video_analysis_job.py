"""add analysis_mode to video_analysis_job

Revision ID: z1a2b3c4d5e6
Revises: h3i4j5k6l7m8
Create Date: 2026-01-07 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z1a2b3c4d5e6"
down_revision: Union[str, None] = "h3i4j5k6l7m8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add analysis_mode field to video_analysis_jobs."""
    op.add_column(
        "video_analysis_jobs",
        sa.Column(
            "analysis_mode",
            sa.String(50),
            nullable=True,
            comment="Analysis mode: batting, bowling, or wicketkeeping",
        ),
    )


def downgrade() -> None:
    """Remove analysis_mode field from video_analysis_jobs."""
    op.drop_column("video_analysis_jobs", "analysis_mode")

"""add pdf export fields to video_analysis_jobs

Revision ID: 8fad14d07603
Revises: h3i4j5k6l7m8
Create Date: 2026-01-06 17:09:14.437475

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8fad14d07603'
down_revision: Union[str, Sequence[str], None] = 'h3i4j5k6l7m8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add PDF export fields to video_analysis_jobs
    op.add_column(
        'video_analysis_jobs',
        sa.Column('pdf_s3_key', sa.String(length=500), nullable=True, comment='S3 key for exported PDF report')
    )
    op.add_column(
        'video_analysis_jobs',
        sa.Column('pdf_generated_at', sa.DateTime(timezone=True), nullable=True, comment='When PDF was generated')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove PDF export fields
    op.drop_column('video_analysis_jobs', 'pdf_generated_at')
    op.drop_column('video_analysis_jobs', 'pdf_s3_key')

"""add awaiting_upload job status

Revision ID: f1a2b3c4d5e6
Revises: 290600375fa0
Create Date: 2026-01-05 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "290600375fa0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add awaiting_upload status to VideoAnalysisJobStatus enum.

    This prevents workers from claiming jobs before upload completion,
    fixing intermittent S3 HeadObject 404 errors.
    """
    # Add new enum value to video_analysis_job_status type
    op.execute(
        """
        ALTER TYPE video_analysis_job_status
        ADD VALUE IF NOT EXISTS 'awaiting_upload' BEFORE 'queued';
        """
    )


def downgrade() -> None:
    """Remove awaiting_upload status from VideoAnalysisJobStatus enum.

    Note: PostgreSQL doesn't support removing enum values directly.
    This would require recreating the enum type and updating all references.
    For safety, we keep the value in the enum but document it as deprecated.
    """
    # Cannot remove enum values in PostgreSQL without recreating the type
    # This is a forward-only migration for safety

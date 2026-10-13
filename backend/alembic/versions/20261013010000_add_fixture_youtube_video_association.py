"""add optional YouTube association to linked organization fixtures

Revision ID: 20261013010000
Revises: 20261001040000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261013010000"
down_revision: str | Sequence[str] | None = "20261001040000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("fixtures", sa.Column("youtube_video_id", sa.String(length=11), nullable=True))
    op.add_column(
        "fixtures",
        sa.Column(
            "youtube_video_updated_by_user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "fixtures",
        sa.Column("youtube_video_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("fixtures", "youtube_video_updated_at")
    op.drop_column("fixtures", "youtube_video_updated_by_user_id")
    op.drop_column("fixtures", "youtube_video_id")

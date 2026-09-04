"""add_player_centered_fields_to_video_sessions

Revision ID: 20260904163500
Revises: 20260106190609, ab12cd34ef56
Create Date: 2026-09-04 16:35:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260904163500"
down_revision = ("20260106190609", "ab12cd34ef56")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "video_sessions",
        sa.Column(
            "primary_player_id",
            sa.String(),
            nullable=True,
            comment="Primary player anchor for player-centered sessions",
        ),
    )
    op.add_column(
        "video_sessions",
        sa.Column(
            "discipline",
            sa.String(length=32),
            nullable=True,
            comment=(
                "V2 discipline context (batting, pace_bowling, spin_bowling, "
                "wicketkeeping, fielding)"
            ),
        ),
    )
    op.add_column(
        "video_sessions",
        sa.Column(
            "coaching_focus",
            sa.String(length=160),
            nullable=True,
            comment="Optional coaching focus entered when creating a session",
        ),
    )
    op.create_index(
        op.f("ix_video_sessions_primary_player_id"),
        "video_sessions",
        ["primary_player_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_video_sessions_primary_player_id"), table_name="video_sessions")
    op.drop_column("video_sessions", "coaching_focus")
    op.drop_column("video_sessions", "discipline")
    op.drop_column("video_sessions", "primary_player_id")

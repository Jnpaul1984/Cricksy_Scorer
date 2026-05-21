"""add coaching_skill_audit_logs table

Phase 9H.6 — Audit Log + Safety Controls.

Creates the ``coaching_skill_audit_logs`` table used to store governed,
sanitized audit events for Coach Pro Plus / Org Pro review decisions on
player-development recommendations. The table stores only safe metadata
summaries and must never contain raw video payloads, raw prompts, or other
unsafe evidence blobs.

Revision ID: d7e9a4b6c1f2
Revises: d9b1c2e3f4a5
Create Date: 2026-05-17 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7e9a4b6c1f2"
down_revision: str | None = "d9b1c2e3f4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create coaching_skill_audit_logs table."""
    op.create_table(
        "coaching_skill_audit_logs",
        sa.Column("id", sa.String(), nullable=False, primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("skill_id", sa.String(length=128), nullable=False),
        sa.Column("skill_version", sa.String(length=32), nullable=False),
        sa.Column("triggered_by_user_id", sa.String(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.String(), nullable=True),
        sa.Column("player_profile_id", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("video_session_id", sa.String(), nullable=True),
        sa.Column("video_analysis_job_id", sa.String(), nullable=True),
        sa.Column("approval_decision", sa.String(length=64), nullable=True),
        sa.Column("approval_state_after", sa.String(length=64), nullable=True),
        sa.Column("coach_approved_after", sa.Boolean(), nullable=True),
        sa.Column("organization_id", sa.String(), nullable=True),
        sa.Column("input_summary", sa.JSON(), nullable=False),
        sa.Column("output_summary", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_coaching_skill_audit_logs_event_type",
        "coaching_skill_audit_logs",
        ["event_type"],
    )
    op.create_index(
        "ix_coaching_skill_audit_logs_triggered_by_user_id",
        "coaching_skill_audit_logs",
        ["triggered_by_user_id"],
    )
    op.create_index(
        "ix_coaching_skill_audit_logs_player_profile_id",
        "coaching_skill_audit_logs",
        ["player_profile_id"],
    )
    op.create_index(
        "ix_coaching_skill_audit_logs_plan_id", "coaching_skill_audit_logs", ["plan_id"]
    )
    op.create_index(
        "ix_coaching_skill_audit_logs_video_session_id",
        "coaching_skill_audit_logs",
        ["video_session_id"],
    )
    op.create_index(
        "ix_coaching_skill_audit_logs_video_analysis_job_id",
        "coaching_skill_audit_logs",
        ["video_analysis_job_id"],
    )
    op.create_index(
        "ix_coaching_skill_audit_logs_created_at",
        "coaching_skill_audit_logs",
        ["created_at"],
    )


def downgrade() -> None:
    """Drop coaching_skill_audit_logs table."""
    op.drop_index("ix_coaching_skill_audit_logs_created_at", table_name="coaching_skill_audit_logs")
    op.drop_index(
        "ix_coaching_skill_audit_logs_video_analysis_job_id",
        table_name="coaching_skill_audit_logs",
    )
    op.drop_index(
        "ix_coaching_skill_audit_logs_video_session_id", table_name="coaching_skill_audit_logs"
    )
    op.drop_index("ix_coaching_skill_audit_logs_plan_id", table_name="coaching_skill_audit_logs")
    op.drop_index(
        "ix_coaching_skill_audit_logs_player_profile_id",
        table_name="coaching_skill_audit_logs",
    )
    op.drop_index(
        "ix_coaching_skill_audit_logs_triggered_by_user_id",
        table_name="coaching_skill_audit_logs",
    )
    op.drop_index("ix_coaching_skill_audit_logs_event_type", table_name="coaching_skill_audit_logs")
    op.drop_table("coaching_skill_audit_logs")

"""add anonymous aggregate sponsor reporting

Revision ID: 20261001010000
Revises: 20260930030000
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision = "20261001010000"
down_revision: str | Sequence[str] | None = "20260930030000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sponsor_placement_daily_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("placement_id", sa.String(), sa.ForeignKey("organization_sponsor_placements.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("display_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("display_count >= 0 AND click_count >= 0", name="ck_sponsor_daily_metric_nonnegative"),
        sa.UniqueConstraint("organization_id", "placement_id", "metric_date", name="uq_sponsor_placement_daily_metric"),
    )
    op.create_index("ix_sponsor_placement_daily_metrics_organization_id", "sponsor_placement_daily_metrics", ["organization_id"])
    op.create_index("ix_sponsor_placement_daily_metrics_placement_id", "sponsor_placement_daily_metrics", ["placement_id"])
    op.create_index("ix_sponsor_placement_daily_metrics_metric_date", "sponsor_placement_daily_metrics", ["metric_date"])
    op.create_table(
        "sponsor_placement_report_dedup",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column("received_date", sa.Date(), nullable=False),
    )
    op.create_index("ix_sponsor_placement_report_dedup_received_date", "sponsor_placement_report_dedup", ["received_date"])


def downgrade() -> None:
    op.drop_table("sponsor_placement_report_dedup")
    op.drop_table("sponsor_placement_daily_metrics")

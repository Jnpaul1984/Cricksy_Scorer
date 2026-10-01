"""add one-time sponsor reporting capability and shared rate bucket

Revision ID: 20261001010001
Revises: 20261001010000
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision = "20261001010001"
down_revision: str | Sequence[str] | None = "20261001010000"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("sponsor_placement_reporting_capabilities", sa.Column("nonce", sa.String(36), primary_key=True), sa.Column("placement_id", sa.String(), sa.ForeignKey("organization_sponsor_placements.id", ondelete="RESTRICT"), nullable=False), sa.Column("event_type", sa.String(8), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("consumed_at", sa.DateTime(timezone=True)), sa.CheckConstraint("event_type IN ('display', 'click')", name="ck_sponsor_reporting_capability_event_type"))
    op.create_index("ix_sponsor_placement_reporting_capabilities_placement_id", "sponsor_placement_reporting_capabilities", ["placement_id"])
    op.create_index("ix_sponsor_placement_reporting_capabilities_expires_at", "sponsor_placement_reporting_capabilities", ["expires_at"])
    op.create_table("sponsor_placement_report_rate_buckets", sa.Column("placement_id", sa.String(), sa.ForeignKey("organization_sponsor_placements.id", ondelete="RESTRICT"), primary_key=True), sa.Column("bucket_start", sa.DateTime(timezone=True), primary_key=True), sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"), sa.CheckConstraint("event_count >= 0", name="ck_sponsor_report_rate_bucket_nonnegative"))

def downgrade() -> None:
    op.drop_table("sponsor_placement_report_rate_buckets")
    op.drop_table("sponsor_placement_reporting_capabilities")

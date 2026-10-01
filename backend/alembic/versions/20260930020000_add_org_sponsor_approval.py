"""add governed organization sponsor placement lifecycle

Revision ID: 20260930020000
Revises: 20260930010000
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision = "20260930020000"
down_revision: str | Sequence[str] | None = "20260930010000"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "organization_sponsor_placements",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("organization_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sponsor_name", sa.String(160), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("sponsor_url", sa.String(2048)),
        sa.Column("placement_surface", sa.String(64), nullable=False, server_default="public_organization_homepage"),
        sa.Column("state", sa.String(16), nullable=False, server_default="proposed"),
        sa.Column("proposed_by_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approved_by_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("taken_down_by_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("approved_at", sa.DateTime(timezone=True)), sa.Column("taken_down_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("placement_surface = 'public_organization_homepage'", name="ck_org_sponsor_placement_surface"),
        sa.CheckConstraint("state IN ('proposed', 'approved', 'taken_down')", name="ck_org_sponsor_placement_state"),
        sa.CheckConstraint("length(category) BETWEEN 1 AND 64", name="ck_org_sponsor_placement_category"),
    )
    op.create_index("ix_org_sponsor_placement_public", "organization_sponsor_placements", ["organization_id", "state", "placement_surface"])
    op.create_index("uq_org_sponsor_one_approved", "organization_sponsor_placements", ["organization_id", "placement_surface"], unique=True, postgresql_where=sa.text("state = 'approved'"), sqlite_where=sa.text("state = 'approved'"))
    op.create_table("organization_sponsor_placement_audit", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("placement_id", sa.String(), sa.ForeignKey("organization_sponsor_placements.id", ondelete="RESTRICT"), nullable=False), sa.Column("organization_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False), sa.Column("action", sa.String(16), nullable=False), sa.Column("actor_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_organization_sponsor_placement_audit_placement_id", "organization_sponsor_placement_audit", ["placement_id"])
    op.create_index("ix_organization_sponsor_placement_audit_organization_id", "organization_sponsor_placement_audit", ["organization_id"])

def downgrade() -> None:
    op.drop_table("organization_sponsor_placement_audit")
    op.drop_index("ix_org_sponsor_placement_public", table_name="organization_sponsor_placements")
    op.drop_index("uq_org_sponsor_one_approved", table_name="organization_sponsor_placements")
    op.drop_table("organization_sponsor_placements")

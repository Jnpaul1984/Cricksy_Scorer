"""add persisted sponsor visibility controls

Revision ID: 20260930030000
Revises: 20260930020000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260930030000"
down_revision: str | Sequence[str] | None = "20260930020000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organization_sponsor_placements",
        sa.Column("visibility_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_table(
        "sponsor_visibility_global_settings",
        sa.Column("key", sa.String(32), primary_key=True),
        sa.Column("visibility_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "organization_sponsor_visibility_settings",
        sa.Column("organization_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("visibility_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "sponsor_visibility_audit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("organization_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="RESTRICT")),
        sa.Column("placement_id", sa.String(), sa.ForeignKey("organization_sponsor_placements.id", ondelete="RESTRICT")),
        sa.Column("visibility_enabled", sa.Boolean(), nullable=False),
        sa.Column("actor_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sponsor_visibility_audit_organization_id", "sponsor_visibility_audit", ["organization_id"])
    op.create_index("ix_sponsor_visibility_audit_placement_id", "sponsor_visibility_audit", ["placement_id"])


def downgrade() -> None:
    op.drop_table("sponsor_visibility_audit")
    op.drop_table("organization_sponsor_visibility_settings")
    op.drop_table("sponsor_visibility_global_settings")
    op.drop_column("organization_sponsor_placements", "visibility_enabled")

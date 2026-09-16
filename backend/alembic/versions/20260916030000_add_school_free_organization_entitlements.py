"""add_school_free_organization_entitlements

Revision ID: 20260916030000
Revises: 20260916020000
Create Date: 2026-09-16 03:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260916030000"
down_revision = "20260916020000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_entitlements",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("plan_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column(
            "effective_from",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "plan_key IN ('school_free')",
            name="ck_organization_entitlements_plan_key",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_organization_entitlements_status",
        ),
        sa.CheckConstraint(
            "source IN ('system', 'admin', 'billing')",
            name="ck_organization_entitlements_source",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_organization_entitlements_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_entitlements"),
        sa.UniqueConstraint(
            "organization_id",
            "plan_key",
            name="uq_organization_entitlements_organization_plan",
        ),
    )
    op.create_index(
        "ix_organization_entitlements_organization_id",
        "organization_entitlements",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_organization_entitlements_organization_status",
        "organization_entitlements",
        ["organization_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_entitlements_organization_status",
        table_name="organization_entitlements",
    )
    op.drop_index(
        "ix_organization_entitlements_organization_id",
        table_name="organization_entitlements",
    )
    op.drop_table("organization_entitlements")

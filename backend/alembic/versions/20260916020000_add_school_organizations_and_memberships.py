"""add_school_organizations_and_memberships

Revision ID: 20260916020000
Revises: 20260905103000
Create Date: 2026-09-16 02:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260916020000"
down_revision = "20260905103000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "organization_type",
            sa.String(length=32),
            server_default="school",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="active",
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
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
            "organization_type IN ('school')",
            name="ck_organizations_type",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'archived')",
            name="ck_organizations_status",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_organizations_created_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
    )

    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="active",
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
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
            "role IN ('owner', 'admin', 'coach', 'scorer', 'viewer')",
            name="ck_organization_memberships_role",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_organization_memberships_status",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_organization_memberships_created_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_organization_memberships_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_organization_memberships_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_memberships"),
        sa.UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_organization_memberships_organization_user",
        ),
    )
    op.create_index(
        "ix_organization_memberships_organization_id",
        "organization_memberships",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_organization_memberships_user_id",
        "organization_memberships",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_organization_memberships_user_status",
        "organization_memberships",
        ["user_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_memberships_user_status",
        table_name="organization_memberships",
    )
    op.drop_index(
        "ix_organization_memberships_user_id",
        table_name="organization_memberships",
    )
    op.drop_index(
        "ix_organization_memberships_organization_id",
        table_name="organization_memberships",
    )
    op.drop_table("organization_memberships")
    op.drop_table("organizations")

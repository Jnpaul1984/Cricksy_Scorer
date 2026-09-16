"""add_organization_owned_teams

Revision ID: 20260916040000
Revises: 20260916030000
Create Date: 2026-09-16 04:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260916040000"
down_revision = "20260916030000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "teams_owner_user_id_fkey",
        "teams",
        type_="foreignkey",
    )
    op.alter_column(
        "teams",
        "owner_user_id",
        existing_type=sa.String(),
        nullable=True,
    )
    op.create_foreign_key(
        "fk_teams_owner_user_id_users",
        "teams",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("teams", sa.Column("organization_id", sa.String(), nullable=True))
    op.add_column(
        "teams",
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="active",
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_teams_organization_id_organizations",
        "teams",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_teams_status",
        "teams",
        "status IN ('active', 'archived')",
    )
    op.create_index(
        "ix_teams_organization_id",
        "teams",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_teams_organization_status",
        "teams",
        ["organization_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    orphaned_owner_count = bind.scalar(
        sa.text("SELECT count(*) FROM teams WHERE owner_user_id IS NULL")
    )
    if orphaned_owner_count:
        raise RuntimeError(
            "Cannot downgrade Phase 7D while teams have no owner_user_id; "
            "reassign or explicitly remove those retained teams first"
        )

    op.drop_index("ix_teams_organization_status", table_name="teams")
    op.drop_index("ix_teams_organization_id", table_name="teams")
    op.drop_constraint("ck_teams_status", "teams", type_="check")
    op.drop_constraint(
        "fk_teams_organization_id_organizations",
        "teams",
        type_="foreignkey",
    )
    op.drop_column("teams", "status")
    op.drop_column("teams", "organization_id")
    op.drop_constraint(
        "fk_teams_owner_user_id_users",
        "teams",
        type_="foreignkey",
    )
    op.alter_column(
        "teams",
        "owner_user_id",
        existing_type=sa.String(),
        nullable=False,
    )
    op.create_foreign_key(
        "teams_owner_user_id_fkey",
        "teams",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="CASCADE",
    )

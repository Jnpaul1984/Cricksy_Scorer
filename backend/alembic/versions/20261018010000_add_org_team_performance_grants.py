"""add default-off organization Team Performance grants

Revision ID: 20261018010000
Revises: 20261016020000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "20261018010000"
down_revision: str | Sequence[str] | None = "20261016020000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_team_performance_grants",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column(
            "effective_from",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("granted_by_user_id", sa.String(), nullable=False),
        sa.Column("grant_reason", sa.Text(), nullable=False),
        sa.Column(
            "granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("revoked_by_user_id", sa.String(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('active', 'expired', 'revoked')",
            name="ck_org_team_performance_grant_status",
        ),
        sa.CheckConstraint(
            "length(trim(grant_reason)) > 0",
            name="ck_org_team_performance_grant_reason",
        ),
        sa.CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="ck_org_team_performance_grant_validity",
        ),
        sa.CheckConstraint(
            "(status = 'revoked' AND revoked_by_user_id IS NOT NULL "
            "AND revoked_at IS NOT NULL AND revocation_reason IS NOT NULL "
            "AND length(trim(revocation_reason)) > 0) "
            "OR (status != 'revoked' AND revoked_by_user_id IS NULL "
            "AND revoked_at IS NULL AND revocation_reason IS NULL)",
            name="ck_org_team_performance_grant_revocation_audit",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_org_team_performance_grant_org_status",
        "organization_team_performance_grants",
        ["organization_id", "status"],
    )
    op.create_index(
        "uq_org_team_performance_one_active_grant",
        "organization_team_performance_grants",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_org_team_performance_one_active_grant",
        table_name="organization_team_performance_grants",
    )
    op.drop_index(
        "ix_org_team_performance_grant_org_status",
        table_name="organization_team_performance_grants",
    )
    op.drop_table("organization_team_performance_grants")

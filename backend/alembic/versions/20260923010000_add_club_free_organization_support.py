"""add_club_free_organization_support

Revision ID: 20260923010000
Revises: 20260918010000
Create Date: 2026-09-23 01:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260923010000"
down_revision: str | Sequence[str] | None = "20260918010000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_organizations_type",
        "organizations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_organizations_type",
        "organizations",
        "organization_type IN ('school', 'club')",
    )
    op.drop_constraint(
        "ck_organization_entitlements_plan_key",
        "organization_entitlements",
        type_="check",
    )
    op.create_check_constraint(
        "ck_organization_entitlements_plan_key",
        "organization_entitlements",
        "plan_key IN ('school_free', 'club_free')",
    )


def downgrade() -> None:
    bind = op.get_bind()
    club_organization_count = int(
        bind.scalar(
            sa.text("SELECT count(*) FROM organizations " "WHERE organization_type = 'club'")
        )
        or 0
    )
    club_entitlement_count = int(
        bind.scalar(
            sa.text(
                "SELECT count(*) FROM organization_entitlements " "WHERE plan_key = 'club_free'"
            )
        )
        or 0
    )
    if club_organization_count or club_entitlement_count:
        raise RuntimeError(
            "Cannot downgrade Club Free support while Club organizations or "
            "club_free entitlements exist"
        )

    op.drop_constraint(
        "ck_organization_entitlements_plan_key",
        "organization_entitlements",
        type_="check",
    )
    op.create_check_constraint(
        "ck_organization_entitlements_plan_key",
        "organization_entitlements",
        "plan_key IN ('school_free')",
    )
    op.drop_constraint(
        "ck_organizations_type",
        "organizations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_organizations_type",
        "organizations",
        "organization_type IN ('school')",
    )

"""Add beta user fields to users table.

Revision ID: j0e1f2g3h4i5
Revises: i9d0e1f2g3h4
Create Date: 2025-12-12 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j0e1f2g3h4i5"
down_revision: str | None = "i9d0e1f2g3h4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add subscription_plan, org_id, and beta_tag columns to users table."""
    # subscription_plan reuses the existing user_role enum
    op.add_column(
        "users",
        sa.Column(
            "subscription_plan",
            sa.Enum(
                "free",
                "player_pro",
                "coach_pro",
                "analyst_pro",
                "org_pro",
                name="user_role",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column("org_id", sa.String(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("beta_tag", sa.String(), nullable=True),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])


def downgrade() -> None:
    """Remove beta user fields from users table."""
    op.drop_index("ix_users_org_id", table_name="users")
    op.drop_column("users", "beta_tag")
    op.drop_column("users", "org_id")
    op.drop_column("users", "subscription_plan")

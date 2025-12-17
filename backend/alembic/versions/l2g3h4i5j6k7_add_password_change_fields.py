"""Add password change tracking fields to users table.

Revision ID: l2g3h4i5j6k7
Revises: k1f2g3h4i5j6
Create Date: 2025-12-16 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "l2g3h4i5j6k7"
down_revision: str | None = "k1f2g3h4i5j6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add requires_password_change and password_changed_at columns to users table."""
    op.add_column(
        "users",
        sa.Column(
            "requires_password_change",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "password_changed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove password change tracking fields from users table."""
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "requires_password_change")

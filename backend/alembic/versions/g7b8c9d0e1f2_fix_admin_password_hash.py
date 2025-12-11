"""Fix admin password hash.

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2025-12-11 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g7b8c9d0e1f2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Update admin password hash."""
    admin_email = "jasonnpaul@hotmail.com"
    # Hash for password: S\XY._61)~TCs\fGdnH4
    new_hash = "$2b$12$OXUzpHS9gb.llYjJOrtrgeIid1/IXELo5L7nY1R484niDCizLa5/W"

    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE users SET hashed_password = :hash WHERE email = :email"),
        {"hash": new_hash, "email": admin_email},
    )
    print(f"[MIGRATION] Updated password hash for: {admin_email}")


def downgrade() -> None:
    """Revert to old password hash."""
    admin_email = "jasonnpaul@hotmail.com"
    old_hash = "$2b$12$KNlNUJmqa4zik6.LCJbx/uxQUvyDH6z3Z.fm4g2isAYVjZ8UNjijq"

    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE users SET hashed_password = :hash WHERE email = :email"),
        {"hash": old_hash, "email": admin_email},
    )

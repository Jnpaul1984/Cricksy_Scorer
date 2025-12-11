"""Fix admin password hash to use PBKDF2 format.

Revision ID: i9d0e1f2g3h4
Revises: h8c9d0e1f2g3
Create Date: 2025-12-11 03:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i9d0e1f2g3h4"
down_revision: str | None = "h8c9d0e1f2g3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Update admin password hash to PBKDF2 format.

    The app uses PBKDF2-SHA256 for password hashing (not bcrypt).
    Format: base64url(salt):base64url(hash)
    """
    admin_email = "jasonnpaul@hotmail.com"
    # PBKDF2-SHA256 hash for password: Cricksy2025!
    # Generated with: backend.security.get_password_hash('Cricksy2025!')
    new_hash = "929K1lfoqJAoReuzNqIanA:mb4Sgb6tG88hgnpv-uxzHmNwb3PApHXzTlgBhR-mcik"

    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE users SET hashed_password = :hash WHERE email = :email"),
        {"hash": new_hash, "email": admin_email},
    )
    print(f"[MIGRATION] Updated password hash to PBKDF2 for: {admin_email}")


def downgrade() -> None:
    """Revert to bcrypt password hash."""
    pass

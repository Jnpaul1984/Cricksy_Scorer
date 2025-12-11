"""Update admin password to simpler one.

Revision ID: h8c9d0e1f2g3
Revises: g7b8c9d0e1f2
Create Date: 2025-12-11 01:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h8c9d0e1f2g3"
down_revision: str | None = "g7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Update admin password hash to simpler password."""
    admin_email = "jasonnpaul@hotmail.com"
    # PBKDF2-SHA256 hash for password: Cricksy2025!
    # Format: base64url(salt):base64url(hash)
    # Generated with: backend.security.get_password_hash('Cricksy2025!')
    new_hash = "929K1lfoqJAoReuzNqIanA:mb4Sgb6tG88hgnpv-uxzHmNwb3PApHXzTlgBhR-mcik"

    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE users SET hashed_password = :hash WHERE email = :email"),
        {"hash": new_hash, "email": admin_email},
    )
    print(f"[MIGRATION] Updated password hash for: {admin_email}")


def downgrade() -> None:
    """Revert to previous password hash."""
    pass

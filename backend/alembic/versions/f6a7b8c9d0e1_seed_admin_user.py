"""Seed admin user for production.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2025-12-10 20:00:00.000000

"""

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Insert admin user if not exists."""
    # Read from environment variables for security
    admin_email = os.getenv("ADMIN_EMAIL", "jasonnpaul@hotmail.com")
    admin_password_hash = os.getenv(
        "ADMIN_PASSWORD_HASH",
        "$2b$12$KNlNUJmqa4zik6.LCJbx/uxQUvyDH6z3Z.fm4g2isAYVjZ8UNjijq",
    )
    admin_id = os.getenv("ADMIN_USER_ID", "788fdd50-9f01-44d1-8043-b4de01701267")

    # Check if user already exists
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT id FROM users WHERE email = :email"), {"email": admin_email}
    )
    if result.fetchone() is None:
        conn.execute(
            sa.text("""
                INSERT INTO users (
                    id, email, hashed_password, is_active,
                    is_superuser, role, created_at, updated_at
                )
                VALUES (
                    :id, :email, :hashed_password, true,
                    true, 'org_pro', NOW(), NOW()
                )
            """),
            {
                "id": admin_id,
                "email": admin_email,
                "hashed_password": admin_password_hash,
            },
        )
        print(f"[MIGRATION] Created admin user: {admin_email}")
    else:
        print(f"[MIGRATION] Admin user already exists: {admin_email}")


def downgrade() -> None:
    """Remove admin user."""
    admin_email = os.getenv("ADMIN_EMAIL", "jasonnpaul@hotmail.com")
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM users WHERE email = :email"), {"email": admin_email})

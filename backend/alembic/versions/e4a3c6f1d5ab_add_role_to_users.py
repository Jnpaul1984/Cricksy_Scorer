"""add role column to users

Revision ID: e4a3c6f1d5ab
Revises: c8f6d3f7c2aa
Create Date: 2025-11-16 23:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4a3c6f1d5ab"
down_revision: str | Sequence[str] | None = "c8f6d3f7c2aa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    role_enum = sa.Enum(
        "free",
        "player_pro",
        "coach_pro",
        "analyst_pro",
        "org_pro",
        name="user_role",
    )
    role_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column(
            "role",
            role_enum,
            nullable=False,
            server_default="free",
        ),
    )
    op.execute(sa.text("UPDATE users SET role = 'free' WHERE role IS NULL"))
    op.alter_column("users", "role", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    role_enum = sa.Enum(
        "free",
        "player_pro",
        "coach_pro",
        "analyst_pro",
        "org_pro",
        name="user_role",
    )
    op.drop_column("users", "role")
    role_enum.drop(op.get_bind(), checkfirst=False)

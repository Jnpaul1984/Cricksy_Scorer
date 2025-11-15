"""merge heads

Revision ID: ff8ee3e387c0
Revises: 4d3b902edbe8, e1a2b3c4d5e6, e1f7a8b2c9d3
Create Date: 2025-11-13 22:17:49.273797

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "ff8ee3e387c0"
down_revision: str | Sequence[str] | None = (
    "4d3b902edbe8",
    "e1a2b3c4d5e6",
    "e1f7a8b2c9d3",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""

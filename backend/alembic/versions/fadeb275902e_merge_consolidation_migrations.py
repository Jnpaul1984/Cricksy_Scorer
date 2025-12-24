"""Merge consolidation migrations

Revision ID: fadeb275902e
Revises: 4c991d30e532, abc753bb4d7c
Create Date: 2025-12-23 20:32:12.758553

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'fadeb275902e'
down_revision: str | Sequence[str] | None = ('4c991d30e532', 'abc753bb4d7c')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

"""Merge consolidation migrations

Revision ID: fadeb275902e
Revises: 4c991d30e532, abc753bb4d7c
Create Date: 2025-12-23 20:32:12.758553

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fadeb275902e'
down_revision: Union[str, Sequence[str], None] = ('4c991d30e532', 'abc753bb4d7c')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

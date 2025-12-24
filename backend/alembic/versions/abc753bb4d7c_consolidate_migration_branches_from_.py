"""Consolidate migration branches from main and feature branches

Revision ID: abc753bb4d7c
Revises: a7e5f6b9c0d1, n4i5j6k7l8m9, k1f2g3h4i5j6
Create Date: 2025-12-23 20:31:09.003514

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abc753bb4d7c'
down_revision: Union[str, Sequence[str], None] = ('a7e5f6b9c0d1', 'n4i5j6k7l8m9', 'k1f2g3h4i5j6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

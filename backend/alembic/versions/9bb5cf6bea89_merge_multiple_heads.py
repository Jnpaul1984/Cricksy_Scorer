"""merge_multiple_heads

Revision ID: 9bb5cf6bea89
Revises: 4d3b902edbe8, e1a2b3c4d5e6, e1f7a8b2c9d3
Create Date: 2025-11-10 01:04:39.475022

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9bb5cf6bea89'
down_revision: Union[str, Sequence[str], None] = ('4d3b902edbe8', 'e1a2b3c4d5e6', 'e1f7a8b2c9d3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

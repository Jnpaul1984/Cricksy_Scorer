"""merge heads

Revision ID: c4daa06ced6b
Revises: j4k5l6m7n8o9, pitch_calibration_001
Create Date: 2026-01-15 01:35:24.219050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4daa06ced6b'
down_revision: Union[str, Sequence[str], None] = ('j4k5l6m7n8o9', 'pitch_calibration_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

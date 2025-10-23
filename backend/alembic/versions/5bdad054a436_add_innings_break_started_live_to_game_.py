"""add innings_break/started/live to game_status

Revision ID: 5bdad054a436
Revises: 991718358b86
Create Date: 2025-09-17 09:46:37.930681

"""
from typing import Sequence, Union

from alembic import op



# revision identifiers, used by Alembic.
revision: str = '5bdad054a436'
down_revision: Union[str, Sequence[str], None] = '991718358b86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add values to existing enum. IF NOT EXISTS is safe to re-run.
    op.execute("ALTER TYPE game_status ADD VALUE IF NOT EXISTS 'innings_break'")
    op.execute("ALTER TYPE game_status ADD VALUE IF NOT EXISTS 'started'")
    op.execute("ALTER TYPE game_status ADD VALUE IF NOT EXISTS 'live'")


def downgrade():
    # Postgres cannot easily drop enum values.
    # If you must truly downgrade, you'd need to recreate the enum/type.
    # Leaving as a no-op is standard for enum extensions.
    pass



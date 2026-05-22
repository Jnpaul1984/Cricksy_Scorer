"""add players country column

Revision ID: 7a606e3d5b82
Revises: c7d8e9f0a1b2
Create Date: 2026-05-21 18:29:32.619031

"""

import sqlalchemy as sa
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "7a606e3d5b82"
down_revision: Union[str, Sequence[str], None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("players")}
    if "country" not in existing_columns:
        op.add_column("players", sa.Column("country", sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("players")}
    if "country" in existing_columns:
        op.drop_column("players", "country")

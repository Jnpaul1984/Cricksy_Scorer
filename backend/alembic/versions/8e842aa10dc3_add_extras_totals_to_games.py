"""add extras_totals to games

Revision ID: 8e842aa10dc3
Revises: 9ceb65587e9a
Create Date: 2025-08-21 18:13:11.587394

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '8e842aa10dc3'
down_revision: Union[str, Sequence[str], None] = '9ceb65587e9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "games",
        sa.Column(
            "extras_totals",
            JSONB(astext_type=sa.Text()),              # <-- use JSONB
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

def downgrade():
    op.drop_column("games", "extras_totals")
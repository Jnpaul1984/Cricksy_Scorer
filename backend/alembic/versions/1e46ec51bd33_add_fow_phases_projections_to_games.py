"""add FOW, phases, projections to games

Revision ID: 1e46ec51bd33
Revises: 8e842aa10dc3
Create Date: 2025-08-21 18:19:42.405728

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql 

# revision identifiers, used by Alembic.
revision: str = '1e46ec51bd33'
down_revision: Union[str, Sequence[str], None] = '8e842aa10dc3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "games",
        sa.Column(
            "fall_of_wickets",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "games",
        sa.Column(
            "phases",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "games",
        sa.Column(
            "projections",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("games", "projections")
    op.drop_column("games", "phases")
    op.drop_column("games", "fall_of_wickets")



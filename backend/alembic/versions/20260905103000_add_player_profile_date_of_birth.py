"""add_player_profile_date_of_birth

Revision ID: 20260905103000
Revises: 20260904163500
Create Date: 2026-09-05 10:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260905103000"
down_revision = "20260904163500"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("player_profiles", sa.Column("date_of_birth", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("player_profiles", "date_of_birth")

"""add bowling context columns to games

Revision ID: 9ceb65587e9a
Revises: a1f75f7dd6d4
Create Date: 2025-08-21 18:08:57.408541

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ceb65587e9a'
down_revision: Union[str, Sequence[str], None] = 'a1f75f7dd6d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("games", sa.Column("current_bowler_id", sa.String(length=64), nullable=True))
    op.add_column("games", sa.Column("last_ball_bowler_id", sa.String(length=64), nullable=True))
    # If you also persist these (your code reads them from snapshot, but safe to add if you plan to store):
    op.add_column("games", sa.Column("current_over_balls", sa.Integer(), nullable=True))
    op.add_column("games", sa.Column("mid_over_change_used", sa.Boolean(), nullable=True))
    op.add_column("games", sa.Column("balls_bowled_total", sa.Integer(), nullable=True))

def downgrade() -> None:
    op.drop_column("games", "balls_bowled_total")
    op.drop_column("games", "mid_over_change_used")
    op.drop_column("games", "current_over_balls")
    op.drop_column("games", "last_ball_bowler_id")
    op.drop_column("games", "current_bowler_id")




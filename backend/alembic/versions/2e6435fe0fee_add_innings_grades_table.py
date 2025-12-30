"""add_innings_grades_table

Revision ID: 2e6435fe0fee
Revises: q8r9s0t1u2v3
Create Date: 2025-12-29 21:44:57.065407

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e6435fe0fee'
down_revision: Union[str, Sequence[str], None] = 'q8r9s0t1u2v3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'innings_grades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('game_id', sa.String(), nullable=False),
        sa.Column('inning_num', sa.Integer(), nullable=False),
        sa.Column('grade', sa.String(3), nullable=False),
        sa.Column('score_percentage', sa.Float(), nullable=False),
        sa.Column('par_score', sa.Integer(), nullable=False),
        sa.Column('total_runs', sa.Integer(), nullable=False),
        sa.Column('run_rate', sa.Float(), nullable=False),
        sa.Column('wickets_lost', sa.Integer(), nullable=False),
        sa.Column('wicket_efficiency', sa.Float(), nullable=False),
        sa.Column('boundary_count', sa.Integer(), nullable=False),
        sa.Column('boundary_percentage', sa.Float(), nullable=False),
        sa.Column('dot_ball_ratio', sa.Float(), nullable=False),
        sa.Column('overs_played', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
    )
    # Create index for faster lookups
    op.create_index('ix_innings_grades_game_id', 'innings_grades', ['game_id'])
    op.create_index('ix_innings_grades_game_inning', 'innings_grades', ['game_id', 'inning_num'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_innings_grades_game_inning', table_name='innings_grades')
    op.drop_index('ix_innings_grades_game_id', table_name='innings_grades')
    op.drop_table('innings_grades')

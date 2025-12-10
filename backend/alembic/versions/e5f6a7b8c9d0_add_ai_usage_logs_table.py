"""add ai_usage_logs table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2025-01-15 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_usage_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=True),
        sa.Column('feature', sa.String(length=100), nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=False, default=0),
        sa.Column('context_id', sa.String(), nullable=True),
        sa.Column('model_name', sa.String(length=100), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ai_usage_logs_user_id', 'ai_usage_logs', ['user_id'])
    op.create_index('ix_ai_usage_logs_org_id', 'ai_usage_logs', ['org_id'])
    op.create_index('ix_ai_usage_logs_feature', 'ai_usage_logs', ['feature'])
    op.create_index('ix_ai_usage_logs_timestamp', 'ai_usage_logs', ['timestamp'])
    op.create_index('ix_ai_usage_user_feature', 'ai_usage_logs', ['user_id', 'feature'])
    op.create_index('ix_ai_usage_org_timestamp', 'ai_usage_logs', ['org_id', 'timestamp'])


def downgrade() -> None:
    op.drop_index('ix_ai_usage_org_timestamp', 'ai_usage_logs')
    op.drop_index('ix_ai_usage_user_feature', 'ai_usage_logs')
    op.drop_index('ix_ai_usage_logs_timestamp', 'ai_usage_logs')
    op.drop_index('ix_ai_usage_logs_feature', 'ai_usage_logs')
    op.drop_index('ix_ai_usage_logs_org_id', 'ai_usage_logs')
    op.drop_index('ix_ai_usage_logs_user_id', 'ai_usage_logs')
    op.drop_table('ai_usage_logs')

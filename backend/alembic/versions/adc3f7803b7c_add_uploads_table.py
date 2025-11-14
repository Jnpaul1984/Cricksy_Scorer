"""add_uploads_table

Revision ID: adc3f7803b7c
Revises: 2b47aa34f669
Create Date: 2025-11-10 01:52:48.958541

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'adc3f7803b7c'
down_revision: Union[str, Sequence[str], None] = '2b47aa34f669'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'uploads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('upload_id', sa.String(length=100), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('s3_key', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('upload_url', sa.Text(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.Column('parsed_preview', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_uploads_id'), 'uploads', ['id'], unique=False)
    op.create_index(op.f('ix_uploads_upload_id'), 'uploads', ['upload_id'], unique=True)
    op.create_index(op.f('ix_uploads_status'), 'uploads', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_uploads_status'), table_name='uploads')
    op.drop_index(op.f('ix_uploads_upload_id'), table_name='uploads')
    op.drop_index(op.f('ix_uploads_id'), table_name='uploads')
    op.drop_table('uploads')

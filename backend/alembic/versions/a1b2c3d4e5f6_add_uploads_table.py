"""Add uploads table

Revision ID: a1b2c3d4e5f6
Revises: existing_head
Create Date: 2025-11-10 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = None  # Will be updated to actual head
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add uploads table for scorecard file uploads."""
    op.create_table(
        'uploads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uploader_id', sa.String(length=255), nullable=False),
        sa.Column('game_id', sa.Integer(), nullable=True),
        sa.Column('filename', sa.String(length=512), nullable=False),
        sa.Column('file_type', sa.String(length=100), nullable=False),
        sa.Column('s3_key', sa.String(length=1024), nullable=False),
        sa.Column('status', sa.Enum('pending', 'processing', 'ready', 'failed', name='uploadstatus', native_enum=False, length=50), nullable=False),
        sa.Column('parsed_preview', sa.JSON(), nullable=True),
        sa.Column('upload_metadata', sa.JSON(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_uploads_id'), 'uploads', ['id'], unique=False)
    op.create_index(op.f('ix_uploads_uploader_id'), 'uploads', ['uploader_id'], unique=False)
    op.create_index(op.f('ix_uploads_game_id'), 'uploads', ['game_id'], unique=False)
    op.create_index(op.f('ix_uploads_s3_key'), 'uploads', ['s3_key'], unique=True)
    op.create_index(op.f('ix_uploads_status'), 'uploads', ['status'], unique=False)


def downgrade() -> None:
    """Remove uploads table."""
    op.drop_index(op.f('ix_uploads_status'), table_name='uploads')
    op.drop_index(op.f('ix_uploads_s3_key'), table_name='uploads')
    op.drop_index(op.f('ix_uploads_game_id'), table_name='uploads')
    op.drop_index(op.f('ix_uploads_uploader_id'), table_name='uploads')
    op.drop_index(op.f('ix_uploads_id'), table_name='uploads')
    op.drop_table('uploads')
    
    # Drop the enum type if using PostgreSQL
    # Note: SQLAlchemy's Enum with native_enum=False doesn't create a native enum in PostgreSQL
    # so this is only needed if native_enum=True was used

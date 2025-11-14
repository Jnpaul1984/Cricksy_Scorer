"""add uploads table

Revision ID: f4a9c8e7b6d5
Revises: e1f7a8b2c9d3
Create Date: 2025-11-10 00:54:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f4a9c8e7b6d5'
down_revision: Union[str, None] = 'e1f7a8b2c9d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create upload_status enum
    upload_status_enum = sa.Enum(
        'pending', 'processing', 'ready', 'failed',
        name='upload_status'
    )
    upload_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create uploads table
    op.create_table(
        'uploads',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('uploader_id', sa.String(), nullable=False),
        sa.Column('game_id', sa.String(), nullable=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False),
        sa.Column('s3_key', sa.String(), nullable=False),
        sa.Column('status', upload_status_enum, nullable=False),
        sa.Column('parsed_preview', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('upload_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='SET NULL'),
    )
    
    # Create indexes
    op.create_index('ix_uploads_uploader_id', 'uploads', ['uploader_id'], unique=False)
    op.create_index('ix_uploads_game_id', 'uploads', ['game_id'], unique=False)
    op.create_index('ix_uploads_status', 'uploads', ['status'], unique=False)
    op.create_index('ix_uploads_created_at', 'uploads', ['created_at'], unique=False)
    op.create_index('ix_uploads_s3_key', 'uploads', ['s3_key'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_uploads_s3_key', table_name='uploads')
    op.drop_index('ix_uploads_created_at', table_name='uploads')
    op.drop_index('ix_uploads_status', table_name='uploads')
    op.drop_index('ix_uploads_game_id', table_name='uploads')
    op.drop_index('ix_uploads_uploader_id', table_name='uploads')
    
    # Drop table
    op.drop_table('uploads')
    
    # Drop enum
    sa.Enum(name='upload_status').drop(op.get_bind(), checkfirst=True)

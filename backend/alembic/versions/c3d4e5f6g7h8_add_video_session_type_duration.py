"""Add session_type and min_duration_seconds to video_sessions

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-01-04 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6g7h8'
down_revision = 'b2c3d4e5f6g7'
branch_labels = None
depends_on = None


def upgrade():
    """Add session_type enum and min_duration_seconds to video_sessions."""
    # Create enum type for session_type (skip if exists)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE video_session_type AS ENUM ('batting', 'bowling', 'fielding', 'wicketkeeping');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Add session_type column (nullable initially for existing rows)
    op.add_column(
        'video_sessions',
        sa.Column(
            'session_type',
            postgresql.ENUM('batting', 'bowling', 'fielding', 'wicketkeeping', name='video_session_type', create_type=False),
            nullable=True,
            comment='Type of cricket session (batting, bowling, fielding, wicketkeeping)'
        )
    )
    
    # Add min_duration_seconds with default 300 (5 minutes)
    op.add_column(
        'video_sessions',
        sa.Column(
            'min_duration_seconds',
            sa.Integer(),
            nullable=False,
            server_default='300',
            comment='Minimum video duration required (default 5 minutes)'
        )
    )
    
    # Create index on session_type for filtering
    op.create_index(
        'ix_video_sessions_session_type',
        'video_sessions',
        ['session_type'],
        unique=False
    )


def downgrade():
    """Remove session_type and min_duration_seconds from video_sessions."""
    op.drop_index('ix_video_sessions_session_type', table_name='video_sessions')
    op.drop_column('video_sessions', 'min_duration_seconds')
    op.drop_column('video_sessions', 'session_type')
    
    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS video_session_type")

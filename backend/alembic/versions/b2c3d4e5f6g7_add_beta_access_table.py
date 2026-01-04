"""Add beta_access table for dynamic entitlements

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-03 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    """Add beta_access table for flexible entitlements."""
    op.create_table(
        'beta_access',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('is_super_beta', sa.Boolean(), nullable=False, server_default='false',
                  comment='Grants all features (beta super user)'),
        sa.Column('entitlements', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Custom feature list: ["video_upload", "advanced_analytics"]'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True,
                  comment='Beta access expiration (NULL = permanent)'),
        sa.Column('granted_by', sa.String(), nullable=True, comment='Admin who granted access'),
        sa.Column('notes', sa.Text(), nullable=True, comment='Admin notes about beta access'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    op.create_index('ix_beta_access_user_id', 'beta_access', ['user_id'], unique=True)
    op.create_index('ix_beta_access_expires_at', 'beta_access', ['expires_at'], unique=False)


def downgrade():
    """Remove beta_access table."""
    op.drop_index('ix_beta_access_expires_at', table_name='beta_access')
    op.drop_index('ix_beta_access_user_id', table_name='beta_access')
    op.drop_table('beta_access')

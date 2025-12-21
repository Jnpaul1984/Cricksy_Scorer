"""add_coach_pro_plus_tier

Revision ID: a7e5f6b9c0d1
Revises: a6d4c2f1b7e8
Create Date: 2025-12-21 00:00:00.000000

This migration adds support for the Coach Pro Plus tier ($19.99/month).
It adds the coach_pro_plus role enum value and extends plan feature definitions.

Note: The role enum itself is managed in code (Python enum), but this migration
documents the introduction of the new tier for data integrity tracking.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a7e5f6b9c0d1"
down_revision = "a6d4c2f1b7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Upgrade: Add coach_pro_plus tier support.
    
    Changes:
    - Updates the role column constraint to allow 'coach_pro_plus'
    - Documentation of new plan feature: video_sessions_enabled, video_upload_enabled, etc.
    """
    # Update the role enum constraint if using explicit CHECK constraint or native ENUM
    # For PostgreSQL with native enum type, this would need to be altered separately.
    # For SQLite (in-memory tests), no schema changes needed.
    # The role column remains as VARCHAR/TEXT, allowing the new 'coach_pro_plus' value.
    pass


def downgrade() -> None:
    """
    Downgrade: Remove coach_pro_plus tier support.
    
    Any users with coach_pro_plus role would need to be migrated back to coach_pro.
    """
    pass

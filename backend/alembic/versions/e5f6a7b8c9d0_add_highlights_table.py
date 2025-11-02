"""add highlights table

Revision ID: e5f6a7b8c9d0
Revises: 1b13e5e48c1e
Create Date: 2025-11-01 23:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "1b13e5e48c1e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create highlight_event_type enum
    op.execute(
        "CREATE TYPE highlight_event_type AS ENUM ("
        "'boundary', 'six', 'wicket', 'milestone', 'partnership', 'hat_trick', 'maiden_over'"
        ")"
    )
    
    # Create highlights table
    op.create_table(
        "highlights",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.Enum(
            "boundary", "six", "wicket", "milestone", "partnership", "hat_trick", "maiden_over",
            name="highlight_event_type"
        ), nullable=False),
        sa.Column("over_number", sa.Integer(), nullable=False),
        sa.Column("ball_number", sa.Integer(), nullable=False),
        sa.Column("inning", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("player_id", sa.String(), nullable=True),
        sa.Column("player_name", sa.String(), nullable=True),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("video_url", sa.Text(), nullable=True),
        sa.Column("video_generated", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_highlights_game_id", "highlights", ["game_id"], unique=False)
    op.create_index("ix_highlights_event_type", "highlights", ["event_type"], unique=False)
    op.create_index("ix_highlights_created_at", "highlights", ["created_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_highlights_created_at", table_name="highlights")
    op.drop_index("ix_highlights_event_type", table_name="highlights")
    op.drop_index("ix_highlights_game_id", table_name="highlights")
    op.drop_table("highlights")
    op.execute("DROP TYPE highlight_event_type")

"""merge heads

Revision ID: f5c9d6e3b2a1
Revises: 4d3b902edbe8, e1a2b3c4d5e6, e1f7a8b2c9d3
Create Date: 2025-11-13 11:12:38.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5c9d6e3b2a1"
down_revision: str | Sequence[str] | None = ("4d3b902edbe8", "e1a2b3c4d5e6", "e1f7a8b2c9d3")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge multiple heads into a single head.

    This migration intentionally contains no schema changes; it records
    the merge of parallel heads so alembic can run `upgrade head` without
    ambiguity.
    """
    pass


def downgrade() -> None:
    """No-op downgrade for merge revision."""
    pass

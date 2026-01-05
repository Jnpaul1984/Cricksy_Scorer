"""merge migration heads

Revision ID: 290600375fa0
Revises: d1e2f3g4h5i6, e5f6g7h8i9j0
Create Date: 2026-01-05 07:31:06.246661

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "290600375fa0"
down_revision: Union[str, Sequence[str], None] = ("d1e2f3g4h5i6", "e5f6g7h8i9j0")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

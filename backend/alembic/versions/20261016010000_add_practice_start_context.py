"""Add immutable private-practice start context.

Revision ID: 20261016010000
Revises: 20261015010000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261016010000"
down_revision: str | Sequence[str] | None = "20261015010000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable context without changing existing official or draft rows."""

    with op.batch_alter_table("games") as batch_op:
        batch_op.add_column(sa.Column("practice_start_context", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Refuse to discard persisted private-practice start decisions."""

    bind = op.get_bind()
    has_start_context = bind.execute(
        sa.text("SELECT 1 FROM games WHERE practice_start_context IS NOT NULL LIMIT 1")
    ).first()
    if has_start_context is not None:
        raise RuntimeError(
            "Cannot downgrade practice start context migration while start context data exists"
        )
    with op.batch_alter_table("games") as batch_op:
        batch_op.drop_column("practice_start_context")

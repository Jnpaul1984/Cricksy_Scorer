"""Add private-practice workflow revision.

Revision ID: 20261016020000
Revises: 20261016010000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261016020000"
down_revision: str | Sequence[str] | None = "20261016010000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Give existing rows a safe initial token without changing their rules."""

    with op.batch_alter_table("games") as batch_op:
        batch_op.add_column(
            sa.Column("practice_workflow_revision", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.add_column(sa.Column("practice_innings_history", sa.JSON(), nullable=True))


def downgrade() -> None:
    connection = op.get_bind()
    has_live_workflow_data = connection.execute(
        sa.text(
            "SELECT 1 FROM games "
            "WHERE practice_workflow_revision <> 1 "
            "OR practice_innings_history IS NOT NULL LIMIT 1"
        )
    ).scalar()
    if has_live_workflow_data:
        raise RuntimeError(
            "Cannot downgrade practice workflow revision while games contain workflow data"
        )
    with op.batch_alter_table("games") as batch_op:
        batch_op.drop_column("practice_innings_history")
        batch_op.drop_column("practice_workflow_revision")

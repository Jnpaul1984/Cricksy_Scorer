"""Add dormant match purpose and versioned rules storage.

Revision ID: 20261015010000
Revises: 20261013010000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261015010000"
down_revision: str | Sequence[str] | None = "20261013010000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Batch mode keeps this additive migration executable against disposable
    # SQLite test databases while producing ordinary ALTERs on PostgreSQL.
    with op.batch_alter_table("games") as batch_op:
        batch_op.add_column(
            sa.Column(
                "match_purpose",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'official'"),
            )
        )
        batch_op.add_column(sa.Column("match_rules", sa.JSON(), nullable=True))
        batch_op.create_check_constraint(
            "ck_games_match_purpose",
            "match_purpose IN ('official', 'practice')",
        )


def downgrade() -> None:
    bind = op.get_bind()
    practice_or_rules_row = bind.execute(
        sa.text(
            "SELECT 1 FROM games "
            "WHERE match_purpose <> 'official' OR match_rules IS NOT NULL LIMIT 1"
        )
    ).first()
    if practice_or_rules_row is not None:
        raise RuntimeError(
            "Cannot downgrade match rules migration while practice purpose or match_rules data exists"
        )
    with op.batch_alter_table("games") as batch_op:
        batch_op.drop_constraint("ck_games_match_purpose", type_="check")
        batch_op.drop_column("match_rules")
        batch_op.drop_column("match_purpose")

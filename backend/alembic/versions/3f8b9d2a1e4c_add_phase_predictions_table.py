"""add_phase_predictions_table

Revision ID: 3f8b9d2a1e4c
Revises: 89c9c0a2cf2f
Create Date: 2025-12-30 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3f8b9d2a1e4c"
down_revision: Union[str, Sequence[str], None] = "89c9c0a2cf2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create phase_predictions table
    op.create_table(
        "phase_predictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("inning_num", sa.Integer(), nullable=False),
        sa.Column("delivery_num", sa.Integer(), nullable=False),
        sa.Column("current_over", sa.Float(), nullable=False),
        sa.Column("current_phase", sa.String(length=20), nullable=False),
        sa.Column("projected_total", sa.Integer(), nullable=False),
        sa.Column("next_over_predicted_runs", sa.Integer(), nullable=False),
        sa.Column("next_over_range_min", sa.Integer(), nullable=False),
        sa.Column("next_over_range_max", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("phase_stats", sa.JSON(), nullable=False),
        sa.Column("win_probability", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(
        "ix_phase_predictions_game_id",
        "phase_predictions",
        ["game_id"],
    )
    op.create_index(
        "ix_phase_predictions_game_inning",
        "phase_predictions",
        ["game_id", "inning_num"],
    )
    op.create_index(
        "ix_phase_predictions_game_inning_delivery",
        "phase_predictions",
        ["game_id", "inning_num", "delivery_num"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_phase_predictions_game_inning_delivery", table_name="phase_predictions")
    op.drop_index("ix_phase_predictions_game_inning", table_name="phase_predictions")
    op.drop_index("ix_phase_predictions_game_id", table_name="phase_predictions")
    op.drop_table("phase_predictions")

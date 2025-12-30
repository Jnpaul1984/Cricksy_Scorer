"""add_pressure_points_table

Revision ID: 89c9c0a2cf2f
Revises: 2e6435fe0fee
Create Date: 2025-12-30 13:18:07.559223

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "89c9c0a2cf2f"
down_revision: Union[str, Sequence[str], None] = "2e6435fe0fee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "pressure_points",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("inning_num", sa.Integer(), nullable=False),
        sa.Column("delivery_num", sa.Integer(), nullable=False),
        sa.Column("over_num", sa.Float(), nullable=False),
        sa.Column("pressure_score", sa.Float(), nullable=False),
        sa.Column("pressure_level", sa.String(20), nullable=False),
        sa.Column("factors", sa.JSON(), nullable=False),
        sa.Column("rates", sa.JSON(), nullable=False),
        sa.Column("cumulative_stats", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
    )

    # Create indexes
    op.create_index("ix_pressure_points_game_id", "pressure_points", ["game_id"])
    op.create_index("ix_pressure_points_game_inning", "pressure_points", ["game_id", "inning_num"])
    op.create_index(
        "ix_pressure_points_game_inning_delivery",
        "pressure_points",
        ["game_id", "inning_num", "delivery_num"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_pressure_points_game_inning_delivery", table_name="pressure_points")
    op.drop_index("ix_pressure_points_game_inning", table_name="pressure_points")
    op.drop_index("ix_pressure_points_game_id", table_name="pressure_points")
    op.drop_table("pressure_points")

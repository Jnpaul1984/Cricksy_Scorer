"""add phase10f player metadata career foundation

Revision ID: a4b5c6d7e8f9
Revises: f2e3d4c5b6a7
Create Date: 2026-05-17 19:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4b5c6d7e8f9"
down_revision: str | None = "f2e3d4c5b6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.add_column(
        "historical_source_player_registry",
        sa.Column(
            "metadata_field_history",
            json_type,
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column(
        "historical_source_player_registry",
        sa.Column(
            "metadata_conflicts",
            json_type,
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column(
        "historical_source_player_registry",
        sa.Column(
            "career_profile_foundation",
            json_type,
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column(
        "historical_source_player_registry",
        sa.Column(
            "review_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("historical_source_player_registry", "review_required")
    op.drop_column("historical_source_player_registry", "career_profile_foundation")
    op.drop_column("historical_source_player_registry", "metadata_conflicts")
    op.drop_column("historical_source_player_registry", "metadata_field_history")

"""Add shot_map key to deliveries ledger entries.

Revision ID: d2bd42f8d9e8
Revises: 5bdad054a436
Create Date: 2025-10-18 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa  # noqa: F401 (kept for Alembic convention)


# revision identifiers, used by Alembic.
revision: str = "d2bd42f8d9e8"
down_revision: str | Sequence[str] | None = "5bdad054a436"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ensure each delivery JSON blob exposes a nullable shot_map key."""
    op.execute(
        """
        UPDATE games
        SET deliveries = COALESCE((
            SELECT jsonb_agg(
                CASE
                    WHEN elem ? 'shot_map' THEN elem
                    ELSE elem || jsonb_build_object('shot_map', NULL)
                END
            )
            FROM jsonb_array_elements(COALESCE(deliveries::jsonb, '[]'::jsonb)) AS elem
        ), '[]'::jsonb)
        """
    )


def downgrade() -> None:
    """Drop the shot_map key from delivery JSON blobs."""
    op.execute(
        """
        UPDATE games
        SET deliveries = COALESCE((
            SELECT jsonb_agg(elem - 'shot_map')
            FROM jsonb_array_elements(COALESCE(deliveries::jsonb, '[]'::jsonb)) AS elem
        ), '[]'::jsonb)
        """
    )

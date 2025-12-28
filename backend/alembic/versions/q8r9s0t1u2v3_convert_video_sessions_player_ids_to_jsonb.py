"""Convert video_sessions.player_ids to JSONB.

Some environments ended up with video_sessions.player_ids as a Postgres ARRAY
(e.g., character varying[]) while the application binds it as JSONB.

This migration normalizes the column type to JSONB in Postgres, while no-oping
for SQLite/other dialects.

Revision ID: q8r9s0t1u2v3
Revises: p2q3r4s5t6u7
Create Date: 2025-12-28

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "q8r9s0t1u2v3"
down_revision: str | None = "p2q3r4s5t6u7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _postgres_column_type(table: str, column: str) -> str | None:
    """Return the Postgres data_type for a column (e.g., 'jsonb', 'ARRAY')."""
    bind = op.get_bind()
    row = bind.execute(
        sa.text(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table
              AND column_name = :column
            """
        ),
        {"table": table, "column": column},
    ).fetchone()
    if row is None:
        return None
    return str(row[0])


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    col_type = _postgres_column_type("video_sessions", "player_ids")
    if col_type is None:
        return

    # Normalize to JSONB.
    # - If already jsonb: no-op
    # - If json: cast to jsonb
    # - If ARRAY (e.g., varchar[]): convert to jsonb array via to_jsonb
    if col_type == "jsonb":
        return

    if col_type == "json":
        op.execute(
            sa.text(
                """
                ALTER TABLE video_sessions
                ALTER COLUMN player_ids
                TYPE jsonb
                USING player_ids::jsonb
                """
            )
        )
        return

    if col_type == "ARRAY":
        op.execute(
            sa.text(
                """
                ALTER TABLE video_sessions
                ALTER COLUMN player_ids
                TYPE jsonb
                USING to_jsonb(player_ids)
                """
            )
        )
        return

    # Unexpected type: be conservative and do nothing.


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    col_type = _postgres_column_type("video_sessions", "player_ids")
    if col_type != "jsonb":
        return

    # Convert JSONB array -> varchar[]
    op.execute(
        sa.text(
            """
            ALTER TABLE video_sessions
            ALTER COLUMN player_ids
            TYPE varchar[]
            USING COALESCE(
                ARRAY(SELECT jsonb_array_elements_text(player_ids)),
                ARRAY[]::varchar[]
            )
            """
        )
    )

"""jsonb_and_required_run_rate

Revision ID: a1f75f7dd6d4
Revises: 2d0c3e4d3a75
Create Date: 2025-08-21 10:48:50.299658
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as psql

# revision identifiers, used by Alembic.
revision: str = "a1f75f7dd6d4"
down_revision: Union[str, Sequence[str], None] = "2d0c3e4d3a75"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _fill_null(table: str, column: str, json_literal: str) -> None:
    """
    Set NULLs to a JSON literal string BEFORE type change.
    json_literal must be a valid JSON string like '{}' or '[]' (no casts here).
    Works regardless of column's current type (json/text/jsonb).
    """
    op.execute(
        sa.text(f"UPDATE {table} SET {column} = {json_literal} WHERE {column} IS NULL")
    )


def _to_jsonb(table: str, column: str) -> None:
    """
    Convert a column to JSONB using a direct cast. This assumes all rows
    are valid JSON (or already json/jsonb/text containing valid JSON).
    """
    op.alter_column(
        table,
        column,
        type_=psql.JSONB(),
        postgresql_using=f"{column}::jsonb",
    )


def upgrade():
    # 1) team_a / team_b: keep NULLs as NULL; just cast to jsonb
    _to_jsonb("games", "team_a")
    _to_jsonb("games", "team_b")

    # 2) scorecards: ensure NOT NULL rows exist as objects; set NULL -> {}
    _fill_null("games", "batting_scorecard", "'{}'")
    _fill_null("games", "bowling_scorecard", "'{}'")
    _to_jsonb("games", "batting_scorecard")
    _to_jsonb("games", "bowling_scorecard")

    # 3) deliveries: set NULL -> [] then cast
    _fill_null("games", "deliveries", "'[]'")
    _to_jsonb("games", "deliveries")

    # 4) Add required_run_rate if missing
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("games")}
    if "required_run_rate" not in cols:
        op.add_column(
            "games", sa.Column("required_run_rate", sa.Float(), nullable=True)
        )


def downgrade():
    # Drop required_run_rate if present
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("games")}
    if "required_run_rate" in cols:
        op.drop_column("games", "required_run_rate")

    # Leaving JSONB types in place is safest. If you truly need to revert:
    # op.alter_column("games", "team_a", type_=psql.JSON(), postgresql_using="team_a::json")
    # op.alter_column("games", "team_b", type_=psql.JSON(), postgresql_using="team_b::json")
    # op.alter_column("games", "batting_scorecard", type_=psql.JSON(), postgresql_using="batting_scorecard::json")
    # op.alter_column("games", "bowling_scorecard", type_=psql.JSON(), postgresql_using="bowling_scorecard::json")
    # op.alter_column("games", "deliveries", type_=psql.JSON(), postgresql_using="deliveries::json")

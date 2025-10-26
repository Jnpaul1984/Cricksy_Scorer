"""sync games columns

Revision ID: 991718358b86
Revises: 1e46ec51bd33
Create Date: 2025-08-21 18:27:58.283241
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "991718358b86"
down_revision: str | Sequence[str] | None = "1e46ec51bd33"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Define the enum so we can create/drop explicitly.
game_status = postgresql.ENUM(
    "not_started",
    "in_progress",
    "completed",
    "abandoned",
    name="game_status",
    create_type=False,  # we'll create it ourselves with checkfirst=True
)


def _has_column(insp: sa.Inspector, table: str, column: str) -> bool:
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # 1) Ensure the enum type exists
    game_status.create(bind, checkfirst=True)

    # 2) Cast games.status -> game_status (robust USING with fallback)
    if _has_column(insp, "games", "status"):
        # Normalize any out-of-range or NULL values so the cast won't fail
        op.execute(
            sa.text(
                """
            UPDATE games
            SET status = 'not_started'
            WHERE status IS NULL
               OR status NOT IN ('not_started','in_progress','completed','abandoned')
        """
            )
        )

        # Only alter type if it isn't already the enum
        current_type = bind.execute(
            sa.text(
                """
                SELECT t.typname
                FROM pg_attribute a
                JOIN pg_class c ON a.attrelid = c.oid
                JOIN pg_type  t ON a.atttypid = t.oid
                WHERE c.relname = 'games' AND a.attname = 'status'
            """
            )
        ).scalar()

        if current_type != "game_status":
            op.alter_column(
                "games",
                "status",
                type_=game_status,
                existing_type=sa.VARCHAR(),
                nullable=False,
                postgresql_using=(
                    "CASE "
                    "WHEN status IN ('not_started','in_progress','completed','abandoned') "
                    "THEN status::game_status "
                    "ELSE 'not_started'::game_status "
                    "END"
                ),
            )

    # 3) Add columns your code expects, only if missing
    if not _has_column(insp, "games", "par_score"):
        op.add_column("games", sa.Column("par_score", sa.Integer(), nullable=True))

    def create_jsonb() -> postgresql.JSONB:
        return postgresql.JSONB(astext_type=sa.Text())

    def _add_jsonb_notnull(table: str, col: str, default_literal: str):
        if not _has_column(insp, table, col):
            op.add_column(
                table,
                sa.Column(
                    col,
                    create_jsonb(),
                    nullable=False,
                    server_default=sa.text(default_literal),
                ),
            )
            # remove the default once existing rows are backfilled
            op.alter_column(table, col, server_default=None)

    _add_jsonb_notnull("games", "extras_totals", "'{}'::jsonb")
    _add_jsonb_notnull("games", "fall_of_wickets", "'[]'::jsonb")
    _add_jsonb_notnull("games", "phases", "'{}'::jsonb")
    _add_jsonb_notnull("games", "projections", "'{}'::jsonb")
    _add_jsonb_notnull("games", "deliveries", "'[]'::jsonb")
    _add_jsonb_notnull("games", "batting_scorecard", "'{}'::jsonb")
    _add_jsonb_notnull("games", "bowling_scorecard", "'{}'::jsonb")

    # 4) Drop legacy columns if present
    for legacy in ("current_over_balls", "mid_over_change_used", "balls_bowled_total"):
        if _has_column(insp, "games", legacy):
            op.drop_column("games", legacy)

    # 5) Sponsors.surfaces -> NOT NULL (if present)
    if _has_column(insp, "sponsors", "surfaces"):
        op.alter_column(
            "sponsors",
            "surfaces",
            existing_type=postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Sponsors.surfaces back to nullable
    if _has_column(insp, "sponsors", "surfaces"):
        op.alter_column(
            "sponsors",
            "surfaces",
            existing_type=postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        )

    # Recreate legacy columns (nullable)
    for legacy, coltype in (
        ("balls_bowled_total", sa.Integer()),
        ("mid_over_change_used", sa.Boolean()),
        ("current_over_balls", sa.Integer()),
    ):
        if not _has_column(insp, "games", legacy):
            op.add_column("games", sa.Column(legacy, coltype, nullable=True))

    # Drop JSONB columns we added
    for col in (
        "bowling_scorecard",
        "batting_scorecard",
        "deliveries",
        "projections",
        "phases",
        "fall_of_wickets",
        "extras_totals",
    ):
        if _has_column(insp, "games", col):
            op.drop_column("games", col)

    # Drop par_score
    if _has_column(insp, "games", "par_score"):
        op.drop_column("games", "par_score")

    # Cast status back to VARCHAR, then drop enum type
    if _has_column(insp, "games", "status"):
        op.alter_column(
            "games",
            "status",
            existing_type=game_status,
            type_=sa.VARCHAR(),
            nullable=True,
        )

    game_status.drop(bind, checkfirst=True)

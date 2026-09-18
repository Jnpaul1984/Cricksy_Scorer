"""Add School competition tenancy, stable Team references, and publication state.

Revision ID: 20260918010000
Revises: 20260916070000
Create Date: 2026-09-18 01:00:00

Legacy tournaments and fixtures intentionally remain unscoped. Existing School
Games remain NULL and are interpreted as private by the application.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260918010000"
down_revision = "20260916070000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tournaments", sa.Column("organization_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_tournaments_organization",
        "tournaments",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_tournaments_organization_id", "tournaments", ["organization_id"], unique=False
    )
    op.create_index(
        "ix_tournaments_organization_status",
        "tournaments",
        ["organization_id", "status"],
        unique=False,
    )

    op.add_column("tournament_teams", sa.Column("team_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_tournament_teams_team",
        "tournament_teams",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_tournament_teams_team_id", "tournament_teams", ["team_id"])
    op.create_unique_constraint(
        "uq_tournament_teams_tournament_team",
        "tournament_teams",
        ["tournament_id", "team_id"],
    )

    op.add_column("fixtures", sa.Column("team_a_id", sa.String(), nullable=True))
    op.add_column("fixtures", sa.Column("team_b_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_fixtures_team_a",
        "fixtures",
        "teams",
        ["team_a_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_fixtures_team_b",
        "fixtures",
        "teams",
        ["team_b_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_fixtures_team_a_id", "fixtures", ["team_a_id"])
    op.create_index("ix_fixtures_team_b_id", "fixtures", ["team_b_id"])
    op.create_index(
        "uq_school_fixtures_game_id",
        "fixtures",
        ["game_id"],
        unique=True,
        postgresql_where=sa.text(
            "game_id IS NOT NULL AND team_a_id IS NOT NULL AND team_b_id IS NOT NULL"
        ),
    )

    op.add_column("games", sa.Column("publication_state", sa.String(length=24), nullable=True))
    op.create_check_constraint(
        "ck_games_publication_state",
        "games",
        "publication_state IS NULL OR publication_state IN "
        "('private', 'published_live', 'published_final')",
    )
    op.create_index("ix_games_publication_state", "games", ["publication_state"])


def downgrade() -> None:
    op.drop_index("ix_games_publication_state", table_name="games")
    op.drop_constraint("ck_games_publication_state", "games", type_="check")
    op.drop_column("games", "publication_state")

    op.drop_index("uq_school_fixtures_game_id", table_name="fixtures")
    op.drop_index("ix_fixtures_team_b_id", table_name="fixtures")
    op.drop_index("ix_fixtures_team_a_id", table_name="fixtures")
    op.drop_constraint("fk_fixtures_team_b", "fixtures", type_="foreignkey")
    op.drop_constraint("fk_fixtures_team_a", "fixtures", type_="foreignkey")
    op.drop_column("fixtures", "team_b_id")
    op.drop_column("fixtures", "team_a_id")

    op.drop_constraint(
        "uq_tournament_teams_tournament_team", "tournament_teams", type_="unique"
    )
    op.drop_index("ix_tournament_teams_team_id", table_name="tournament_teams")
    op.drop_constraint("fk_tournament_teams_team", "tournament_teams", type_="foreignkey")
    op.drop_column("tournament_teams", "team_id")

    op.drop_index("ix_tournaments_organization_status", table_name="tournaments")
    op.drop_index("ix_tournaments_organization_id", table_name="tournaments")
    op.drop_constraint("fk_tournaments_organization", "tournaments", type_="foreignkey")
    op.drop_column("tournaments", "organization_id")

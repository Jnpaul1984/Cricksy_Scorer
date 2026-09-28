"""add_selection_match_preparation

Revision ID: 20260928010000
Revises: 20260927010000
Create Date: 2026-09-28 01:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260928010000"
down_revision: str | Sequence[str] | None = "20260927010000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organization_selection_plan_players",
        sa.Column("batting_position", sa.Integer(), nullable=True),
    )
    op.add_column(
        "organization_selection_plan_players",
        sa.Column("bowling_priority", sa.Integer(), nullable=True),
    )
    op.add_column(
        "organization_selection_plan_players",
        sa.Column("bowling_role", sa.String(length=16), nullable=True),
    )
    op.create_check_constraint(
        "ck_organization_selection_plan_players_batting_position",
        "organization_selection_plan_players",
        "batting_position IS NULL OR batting_position > 0",
    )
    op.create_check_constraint(
        "ck_organization_selection_plan_players_bowling_priority",
        "organization_selection_plan_players",
        "bowling_priority IS NULL OR bowling_priority > 0",
    )
    op.create_check_constraint(
        "ck_organization_selection_plan_players_bowling_role",
        "organization_selection_plan_players",
        "bowling_role IS NULL OR bowling_role IN ('primary', 'secondary')",
    )
    op.create_check_constraint(
        "ck_organization_selection_plan_players_bowling_pair",
        "organization_selection_plan_players",
        "(bowling_priority IS NULL) = (bowling_role IS NULL)",
    )
    op.create_check_constraint(
        "ck_organization_selection_plan_players_xi_planning",
        "organization_selection_plan_players",
        "selection_role = 'xi' OR (batting_position IS NULL AND bowling_priority IS NULL "
        "AND bowling_role IS NULL)",
    )
    op.create_unique_constraint(
        "uq_organization_selection_plan_players_batting_position",
        "organization_selection_plan_players",
        ["selection_plan_id", "batting_position"],
    )
    op.create_unique_constraint(
        "uq_organization_selection_plan_players_bowling_priority",
        "organization_selection_plan_players",
        ["selection_plan_id", "bowling_priority"],
    )

    op.create_table(
        "organization_selection_publications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("selection_plan_id", sa.String(), nullable=False),
        sa.Column("team_id", sa.String(), nullable=False),
        sa.Column("fixture_id", sa.String(), nullable=False),
        sa.Column("fixture_tournament_id", sa.String(), nullable=False),
        sa.Column("plan_revision", sa.Integer(), nullable=False),
        sa.Column("publication_version", sa.Integer(), nullable=False),
        sa.Column("captain_roster_membership_id", sa.String(), nullable=False),
        sa.Column("wicketkeeper_roster_membership_id", sa.String(), nullable=False),
        sa.Column("published_by_user_id", sa.String(), nullable=False),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "publication_version >= 1", name="ck_organization_selection_publications_version"
        ),
        sa.CheckConstraint(
            "plan_revision >= 1", name="ck_organization_selection_publications_revision"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_organization_selection_publications_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["selection_plan_id", "organization_id"],
            ["organization_selection_plans.id", "organization_selection_plans.organization_id"],
            name="fk_organization_selection_publications_plan_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["team_id", "organization_id"],
            ["teams.id", "teams.organization_id"],
            name="fk_organization_selection_publications_team_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["fixture_id", "fixture_tournament_id"],
            ["fixtures.id", "fixtures.tournament_id"],
            name="fk_organization_selection_publications_fixture_tournament",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["fixture_tournament_id", "organization_id"],
            ["tournaments.id", "tournaments.organization_id"],
            name="fk_organization_selection_publications_tournament_org",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_selection_publications"),
        sa.UniqueConstraint(
            "id", "organization_id", name="uq_organization_selection_publications_id_org"
        ),
        sa.UniqueConstraint(
            "selection_plan_id",
            "publication_version",
            name="uq_organization_selection_publications_plan_version",
        ),
        sa.UniqueConstraint(
            "selection_plan_id",
            "plan_revision",
            name="uq_organization_selection_publications_plan_revision",
        ),
    )
    op.create_index(
        "ix_organization_selection_publications_organization_id",
        "organization_selection_publications",
        ["organization_id"],
    )
    op.create_index(
        "ix_organization_selection_publications_plan_version",
        "organization_selection_publications",
        ["organization_id", "selection_plan_id", "publication_version"],
    )

    op.create_table(
        "organization_selection_publication_players",
        sa.Column("publication_id", sa.String(), nullable=False),
        sa.Column("school_player_membership_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("player_profile_id", sa.String(), nullable=False),
        sa.Column("player_name", sa.String(), nullable=False),
        sa.Column("selection_role", sa.String(length=16), nullable=False),
        sa.Column("batting_position", sa.Integer(), nullable=True),
        sa.Column("bowling_priority", sa.Integer(), nullable=True),
        sa.Column("bowling_role", sa.String(length=16), nullable=True),
        sa.CheckConstraint(
            "selection_role IN ('xi', 'reserve')",
            name="ck_organization_selection_publication_players_role",
        ),
        sa.CheckConstraint(
            "batting_position IS NULL OR batting_position > 0",
            name="ck_organization_selection_publication_players_batting_position",
        ),
        sa.CheckConstraint(
            "bowling_priority IS NULL OR bowling_priority > 0",
            name="ck_organization_selection_publication_players_bowling_priority",
        ),
        sa.CheckConstraint(
            "bowling_role IS NULL OR bowling_role IN ('primary', 'secondary')",
            name="ck_organization_selection_publication_players_bowling_role",
        ),
        sa.CheckConstraint(
            "(bowling_priority IS NULL) = (bowling_role IS NULL)",
            name="ck_organization_selection_publication_players_bowling_pair",
        ),
        sa.CheckConstraint(
            "selection_role = 'xi' OR (batting_position IS NULL AND bowling_priority IS NULL "
            "AND bowling_role IS NULL)",
            name="ck_organization_selection_publication_players_xi_planning",
        ),
        sa.ForeignKeyConstraint(
            ["publication_id", "organization_id"],
            [
                "organization_selection_publications.id",
                "organization_selection_publications.organization_id",
            ],
            name="fk_organization_selection_publication_players_publication_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["school_player_membership_id", "organization_id"],
            ["school_player_memberships.id", "school_player_memberships.organization_id"],
            name="fk_organization_selection_publication_players_roster_org",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "publication_id",
            "school_player_membership_id",
            name="pk_organization_selection_publication_players",
        ),
        sa.UniqueConstraint(
            "publication_id",
            "batting_position",
            name="uq_organization_selection_publication_players_batting_position",
        ),
        sa.UniqueConstraint(
            "publication_id",
            "bowling_priority",
            name="uq_organization_selection_publication_players_bowling_priority",
        ),
    )
    op.create_index(
        "ix_organization_selection_publication_players_role",
        "organization_selection_publication_players",
        ["organization_id", "publication_id", "selection_role"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_selection_publication_players_role",
        table_name="organization_selection_publication_players",
    )
    op.drop_table("organization_selection_publication_players")
    op.drop_index(
        "ix_organization_selection_publications_plan_version",
        table_name="organization_selection_publications",
    )
    op.drop_index(
        "ix_organization_selection_publications_organization_id",
        table_name="organization_selection_publications",
    )
    op.drop_table("organization_selection_publications")
    op.drop_constraint(
        "uq_organization_selection_plan_players_bowling_priority",
        "organization_selection_plan_players",
        type_="unique",
    )
    op.drop_constraint(
        "uq_organization_selection_plan_players_batting_position",
        "organization_selection_plan_players",
        type_="unique",
    )
    for name in (
        "ck_organization_selection_plan_players_xi_planning",
        "ck_organization_selection_plan_players_bowling_pair",
        "ck_organization_selection_plan_players_bowling_role",
        "ck_organization_selection_plan_players_bowling_priority",
        "ck_organization_selection_plan_players_batting_position",
    ):
        op.drop_constraint(name, "organization_selection_plan_players", type_="check")
    op.drop_column("organization_selection_plan_players", "bowling_role")
    op.drop_column("organization_selection_plan_players", "bowling_priority")
    op.drop_column("organization_selection_plan_players", "batting_position")

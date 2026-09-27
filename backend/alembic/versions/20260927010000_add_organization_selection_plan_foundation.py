"""add_organization_selection_plan_foundation

Revision ID: 20260927010000
Revises: 20260925030000
Create Date: 2026-09-27 01:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260927010000"
down_revision: str | Sequence[str] | None = "20260925030000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization_selection_plans",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("team_id", sa.String(), nullable=False),
        sa.Column("fixture_id", sa.String(), nullable=False),
        sa.Column("fixture_tournament_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("captain_roster_membership_id", sa.String(), nullable=True),
        sa.Column("wicketkeeper_roster_membership_id", sa.String(), nullable=True),
        sa.Column("created_by_user_id", sa.String(), nullable=False),
        sa.Column("updated_by_user_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published')",
            name="ck_organization_selection_plans_status",
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name="ck_organization_selection_plans_revision",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_organization_selection_plans_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id", "organization_id"],
            ["teams.id", "teams.organization_id"],
            name="fk_organization_selection_plans_team_organization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["fixture_id", "fixture_tournament_id"],
            ["fixtures.id", "fixtures.tournament_id"],
            name="fk_organization_selection_plans_fixture_tournament",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["fixture_tournament_id", "organization_id"],
            ["tournaments.id", "tournaments.organization_id"],
            name="fk_organization_selection_plans_tournament_organization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["captain_roster_membership_id", "organization_id"],
            ["school_player_memberships.id", "school_player_memberships.organization_id"],
            name="fk_organization_selection_plans_captain_organization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["wicketkeeper_roster_membership_id", "organization_id"],
            ["school_player_memberships.id", "school_player_memberships.organization_id"],
            name="fk_organization_selection_plans_wicketkeeper_organization",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_selection_plans"),
        sa.UniqueConstraint(
            "id",
            "organization_id",
            name="uq_organization_selection_plans_id_organization",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "team_id",
            "fixture_id",
            name="uq_organization_selection_plans_context",
        ),
    )
    op.create_index(
        "ix_organization_selection_plans_organization_id",
        "organization_selection_plans",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_organization_selection_plans_fixture",
        "organization_selection_plans",
        ["organization_id", "fixture_id"],
        unique=False,
    )
    op.create_index(
        "ix_organization_selection_plans_team_status",
        "organization_selection_plans",
        ["organization_id", "team_id", "status"],
        unique=False,
    )

    op.create_table(
        "organization_selection_plan_players",
        sa.Column("selection_plan_id", sa.String(), nullable=False),
        sa.Column("school_player_membership_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("selection_role", sa.String(length=16), nullable=False),
        sa.CheckConstraint(
            "selection_role IN ('xi', 'reserve')",
            name="ck_organization_selection_plan_players_role",
        ),
        sa.ForeignKeyConstraint(
            ["selection_plan_id", "organization_id"],
            ["organization_selection_plans.id", "organization_selection_plans.organization_id"],
            name="fk_organization_selection_plan_players_plan_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["school_player_membership_id", "organization_id"],
            ["school_player_memberships.id", "school_player_memberships.organization_id"],
            name="fk_organization_selection_plan_players_roster_organization",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "selection_plan_id",
            "school_player_membership_id",
            name="pk_organization_selection_plan_players",
        ),
    )
    op.create_index(
        "ix_organization_selection_plan_players_plan_role",
        "organization_selection_plan_players",
        ["organization_id", "selection_plan_id", "selection_role"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_selection_plan_players_plan_role",
        table_name="organization_selection_plan_players",
    )
    op.drop_table("organization_selection_plan_players")
    op.drop_index(
        "ix_organization_selection_plans_team_status",
        table_name="organization_selection_plans",
    )
    op.drop_index(
        "ix_organization_selection_plans_fixture",
        table_name="organization_selection_plans",
    )
    op.drop_index(
        "ix_organization_selection_plans_organization_id",
        table_name="organization_selection_plans",
    )
    op.drop_table("organization_selection_plans")

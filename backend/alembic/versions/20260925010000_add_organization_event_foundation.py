"""add_organization_event_foundation

Revision ID: 20260925010000
Revises: 20260923010000
Create Date: 2026-09-25 01:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260925010000"
down_revision: str | Sequence[str] | None = "20260923010000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_teams_id_organization",
        "teams",
        ["id", "organization_id"],
    )
    op.create_unique_constraint(
        "uq_school_player_memberships_id_organization",
        "school_player_memberships",
        ["id", "organization_id"],
    )

    op.create_table(
        "organization_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("participant_scope", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="scheduled", nullable=False),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
        sa.Column("updated_by_user_id", sa.String(), nullable=True),
        sa.Column("cancelled_by_user_id", sa.String(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
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
            "participant_scope IN ('organization', 'teams', 'selected_players')",
            name="ck_organization_events_participant_scope",
        ),
        sa.CheckConstraint(
            "status IN ('scheduled', 'cancelled')",
            name="ck_organization_events_status",
        ),
        sa.CheckConstraint(
            "end_at IS NULL OR end_at > start_at",
            name="ck_organization_events_time_range",
        ),
        sa.CheckConstraint(
            "(status = 'scheduled' AND cancelled_at IS NULL) OR "
            "(status = 'cancelled' AND cancelled_at IS NOT NULL)",
            name="ck_organization_events_cancellation_state",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_organization_events_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_organization_events_created_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["users.id"],
            name="fk_organization_events_updated_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["cancelled_by_user_id"],
            ["users.id"],
            name="fk_organization_events_cancelled_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_events"),
        sa.UniqueConstraint(
            "id",
            "organization_id",
            name="uq_organization_events_id_organization",
        ),
    )
    op.create_index(
        "ix_organization_events_organization_id",
        "organization_events",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_organization_events_organization_start",
        "organization_events",
        ["organization_id", "start_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_organization_events_organization_status_start",
        "organization_events",
        ["organization_id", "status", "start_at", "id"],
        unique=False,
    )

    op.create_table(
        "organization_event_teams",
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("team_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id", "organization_id"],
            ["organization_events.id", "organization_events.organization_id"],
            name="fk_organization_event_teams_event_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id", "organization_id"],
            ["teams.id", "teams.organization_id"],
            name="fk_organization_event_teams_team_organization",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("event_id", "team_id", name="pk_organization_event_teams"),
    )
    op.create_index(
        "ix_organization_event_teams_organization_team",
        "organization_event_teams",
        ["organization_id", "team_id"],
        unique=False,
    )

    op.create_table(
        "organization_event_roster_players",
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("school_player_membership_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id", "organization_id"],
            ["organization_events.id", "organization_events.organization_id"],
            name="fk_organization_event_players_event_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["school_player_membership_id", "organization_id"],
            ["school_player_memberships.id", "school_player_memberships.organization_id"],
            name="fk_organization_event_players_roster_organization",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "event_id",
            "school_player_membership_id",
            name="pk_organization_event_roster_players",
        ),
    )
    op.create_index(
        "ix_organization_event_players_organization_player",
        "organization_event_roster_players",
        ["organization_id", "school_player_membership_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_event_players_organization_player",
        table_name="organization_event_roster_players",
    )
    op.drop_table("organization_event_roster_players")
    op.drop_index(
        "ix_organization_event_teams_organization_team",
        table_name="organization_event_teams",
    )
    op.drop_table("organization_event_teams")
    op.drop_index(
        "ix_organization_events_organization_status_start",
        table_name="organization_events",
    )
    op.drop_index(
        "ix_organization_events_organization_start",
        table_name="organization_events",
    )
    op.drop_index("ix_organization_events_organization_id", table_name="organization_events")
    op.drop_table("organization_events")
    op.drop_constraint(
        "uq_school_player_memberships_id_organization",
        "school_player_memberships",
        type_="unique",
    )
    op.drop_constraint(
        "uq_teams_id_organization",
        "teams",
        type_="unique",
    )

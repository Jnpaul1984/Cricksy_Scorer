"""add_organization_player_availability

Revision ID: 20260925020000
Revises: 20260925010000
Create Date: 2026-09-25 02:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260925020000"
down_revision: str | Sequence[str] | None = "20260925010000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_tournaments_id_organization",
        "tournaments",
        ["id", "organization_id"],
    )
    op.create_unique_constraint(
        "uq_fixtures_id_tournament",
        "fixtures",
        ["id", "tournament_id"],
    )

    op.create_table(
        "organization_availability_targets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("organization_event_id", sa.String(), nullable=True),
        sa.Column("fixture_id", sa.String(), nullable=True),
        sa.Column("fixture_tournament_id", sa.String(), nullable=True),
        sa.Column("response_deadline", sa.DateTime(timezone=True), nullable=True),
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
            "target_type IN ('event', 'fixture')",
            name="ck_organization_availability_targets_type",
        ),
        sa.CheckConstraint(
            "(target_type = 'event' AND organization_event_id IS NOT NULL "
            "AND fixture_id IS NULL AND fixture_tournament_id IS NULL) OR "
            "(target_type = 'fixture' AND organization_event_id IS NULL "
            "AND fixture_id IS NOT NULL AND fixture_tournament_id IS NOT NULL)",
            name="ck_organization_availability_targets_reference",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_organization_availability_targets_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_event_id", "organization_id"],
            ["organization_events.id", "organization_events.organization_id"],
            name="fk_organization_availability_targets_event_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["fixture_id", "fixture_tournament_id"],
            ["fixtures.id", "fixtures.tournament_id"],
            name="fk_organization_availability_targets_fixture_tournament",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["fixture_tournament_id", "organization_id"],
            ["tournaments.id", "tournaments.organization_id"],
            name="fk_organization_availability_targets_tournament_organization",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_availability_targets"),
        sa.UniqueConstraint(
            "id",
            "organization_id",
            name="uq_organization_availability_targets_id_organization",
        ),
        sa.UniqueConstraint(
            "organization_event_id",
            name="uq_organization_availability_targets_event",
        ),
        sa.UniqueConstraint(
            "fixture_id",
            name="uq_organization_availability_targets_fixture",
        ),
    )
    op.create_index(
        "ix_organization_availability_targets_organization_id",
        "organization_availability_targets",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_organization_availability_targets_organization_type",
        "organization_availability_targets",
        ["organization_id", "target_type"],
        unique=False,
    )
    op.create_index(
        "ix_organization_availability_targets_deadline",
        "organization_availability_targets",
        ["organization_id", "response_deadline"],
        unique=False,
    )

    op.create_table(
        "organization_player_availability",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("school_player_membership_id", sa.String(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("recorded_by_user_id", sa.String(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "recorded_after_deadline",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('available', 'unavailable', 'maybe')",
            name="ck_organization_player_availability_state",
        ),
        sa.ForeignKeyConstraint(
            ["target_id", "organization_id"],
            [
                "organization_availability_targets.id",
                "organization_availability_targets.organization_id",
            ],
            name="fk_organization_player_availability_target_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["school_player_membership_id", "organization_id"],
            ["school_player_memberships.id", "school_player_memberships.organization_id"],
            name="fk_organization_player_availability_roster_organization",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_player_availability"),
        sa.UniqueConstraint(
            "target_id",
            "school_player_membership_id",
            name="uq_organization_player_availability_target_player",
        ),
    )
    op.create_index(
        "ix_organization_player_availability_target_state",
        "organization_player_availability",
        ["organization_id", "target_id", "state"],
        unique=False,
    )

    op.create_table(
        "organization_player_availability_history",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("school_player_membership_id", sa.String(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("recorded_by_user_id", sa.String(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "recorded_after_deadline",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "state IN ('available', 'unavailable', 'maybe')",
            name="ck_organization_player_availability_history_state",
        ),
        sa.ForeignKeyConstraint(
            ["target_id", "organization_id"],
            [
                "organization_availability_targets.id",
                "organization_availability_targets.organization_id",
            ],
            name="fk_organization_player_availability_history_target_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["school_player_membership_id", "organization_id"],
            ["school_player_memberships.id", "school_player_memberships.organization_id"],
            name="fk_organization_player_availability_history_roster_organization",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_player_availability_history"),
    )
    op.create_index(
        "ix_organization_player_availability_history_target_player_time",
        "organization_player_availability_history",
        [
            "organization_id",
            "target_id",
            "school_player_membership_id",
            "recorded_at",
            "id",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_player_availability_history_target_player_time",
        table_name="organization_player_availability_history",
    )
    op.drop_table("organization_player_availability_history")
    op.drop_index(
        "ix_organization_player_availability_target_state",
        table_name="organization_player_availability",
    )
    op.drop_table("organization_player_availability")
    op.drop_index(
        "ix_organization_availability_targets_deadline",
        table_name="organization_availability_targets",
    )
    op.drop_index(
        "ix_organization_availability_targets_organization_type",
        table_name="organization_availability_targets",
    )
    op.drop_index(
        "ix_organization_availability_targets_organization_id",
        table_name="organization_availability_targets",
    )
    op.drop_table("organization_availability_targets")
    op.drop_constraint(
        "uq_fixtures_id_tournament",
        "fixtures",
        type_="unique",
    )
    op.drop_constraint(
        "uq_tournaments_id_organization",
        "tournaments",
        type_="unique",
    )

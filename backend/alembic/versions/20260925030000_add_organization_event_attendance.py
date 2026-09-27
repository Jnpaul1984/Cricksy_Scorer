"""add_organization_event_attendance

Revision ID: 20260925030000
Revises: 20260925020000
Create Date: 2026-09-25 03:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260925030000"
down_revision: str | Sequence[str] | None = "20260925020000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Event deletion must not cascade through an availability target and erase its audit history.
    op.drop_constraint(
        "fk_organization_availability_targets_event_organization",
        "organization_availability_targets",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_organization_availability_targets_event_organization",
        "organization_availability_targets",
        "organization_events",
        ["organization_event_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "organization_player_attendance",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("organization_event_id", sa.String(), nullable=False),
        sa.Column("school_player_membership_id", sa.String(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("recorded_by_user_id", sa.String(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('present', 'absent', 'excused')",
            name="ck_organization_player_attendance_state",
        ),
        sa.ForeignKeyConstraint(
            ["organization_event_id", "organization_id"],
            ["organization_events.id", "organization_events.organization_id"],
            name="fk_organization_player_attendance_event_organization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["school_player_membership_id", "organization_id"],
            ["school_player_memberships.id", "school_player_memberships.organization_id"],
            name="fk_organization_player_attendance_roster_organization",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_player_attendance"),
        sa.UniqueConstraint(
            "organization_event_id",
            "school_player_membership_id",
            name="uq_organization_player_attendance_event_player",
        ),
    )
    op.create_index(
        "ix_organization_player_attendance_event_state",
        "organization_player_attendance",
        ["organization_id", "organization_event_id", "state"],
        unique=False,
    )

    op.create_table(
        "organization_player_attendance_history",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("organization_event_id", sa.String(), nullable=False),
        sa.Column("school_player_membership_id", sa.String(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("recorded_by_user_id", sa.String(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('present', 'absent', 'excused')",
            name="ck_organization_player_attendance_history_state",
        ),
        sa.ForeignKeyConstraint(
            ["organization_event_id", "organization_id"],
            ["organization_events.id", "organization_events.organization_id"],
            name="fk_organization_player_attendance_history_event_organization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["school_player_membership_id", "organization_id"],
            ["school_player_memberships.id", "school_player_memberships.organization_id"],
            name="fk_organization_player_attendance_history_roster_organization",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_player_attendance_history"),
    )
    op.create_index(
        "ix_organization_player_attendance_history_event_player_time",
        "organization_player_attendance_history",
        [
            "organization_id",
            "organization_event_id",
            "school_player_membership_id",
            "recorded_at",
            "id",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_player_attendance_history_event_player_time",
        table_name="organization_player_attendance_history",
    )
    op.drop_table("organization_player_attendance_history")
    op.drop_index(
        "ix_organization_player_attendance_event_state",
        table_name="organization_player_attendance",
    )
    op.drop_table("organization_player_attendance")

    op.drop_constraint(
        "fk_organization_availability_targets_event_organization",
        "organization_availability_targets",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_organization_availability_targets_event_organization",
        "organization_availability_targets",
        "organization_events",
        ["organization_event_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="CASCADE",
    )

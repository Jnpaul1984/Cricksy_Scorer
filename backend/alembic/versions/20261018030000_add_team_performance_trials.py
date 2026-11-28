"""Add default-off Team Performance trial state and immutable evidence history.

Revision ID: 20261018030000
Revises: 20261018020000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261018030000"
down_revision: str | Sequence[str] | None = "20261018020000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id() -> sa.Column:
    return sa.Column("id", sa.String(), primary_key=True)


def _org() -> sa.Column:
    return sa.Column(
        "organization_id",
        sa.String(),
        sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )


def _user(name: str) -> sa.Column:
    return sa.Column(
        name, sa.String(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


def _time(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False)


def upgrade() -> None:
    op.create_table(
        "team_performance_trial_availability",
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        _user("changed_by_user_id"),
        _time("changed_at"),
        sa.CheckConstraint(
            "status IN ('enabled', 'revoked')", name="ck_team_trial_availability_status"
        ),
    )
    op.create_table(
        "team_performance_trial_availability_events",
        _id(),
        _org(),
        sa.Column("status", sa.String(16), nullable=False),
        _user("actor_user_id"),
        sa.Column("reason", sa.Text(), nullable=False),
        _time("recorded_at"),
        sa.CheckConstraint(
            "status IN ('enabled', 'revoked')", name="ck_team_trial_availability_event_status"
        ),
        sa.CheckConstraint(
            "length(trim(reason)) > 0", name="ck_team_trial_availability_event_reason"
        ),
    )
    op.create_index(
        "ix_team_performance_trial_availability_events_organization_id",
        "team_performance_trial_availability_events",
        ["organization_id"],
    )
    op.create_table(
        "team_performance_trials",
        _id(),
        _org(),
        sa.Column(
            "team_id", sa.String(), sa.ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        _user("activated_by_user_id"),
        _time("activated_at"),
        sa.Column("venue_timezone", sa.String(64), nullable=False),
        sa.Column("activation_local_date", sa.Date(), nullable=False),
        _time("expires_at"),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("report_access_until", sa.DateTime(timezone=True)),
        sa.Column("prerequisite_sources", sa.JSON(), nullable=False),
        sa.UniqueConstraint("organization_id", "team_id", name="uq_team_trial_organization_team"),
        sa.CheckConstraint(
            "state IN ('active', 'exhausted', 'expired', 'revoked', 'review_required')",
            name="ck_team_trial_state",
        ),
        sa.CheckConstraint("policy_version > 0", name="ck_team_trial_policy_version"),
    )
    op.create_index(
        "ix_team_performance_trials_organization_id", "team_performance_trials", ["organization_id"]
    )
    op.create_table(
        "team_performance_trial_completions",
        _id(),
        sa.Column(
            "trial_id",
            sa.String(),
            sa.ForeignKey("team_performance_trials.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "game_id", sa.String(), sa.ForeignKey("games.id", ondelete="RESTRICT"), nullable=False
        ),
        _time("completed_at"),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.UniqueConstraint("trial_id", "game_id", name="uq_team_trial_completion_game"),
    )
    op.create_index(
        "ix_team_trial_completion_order",
        "team_performance_trial_completions",
        ["trial_id", "completed_at"],
    )
    op.create_table(
        "team_performance_trial_events",
        _id(),
        sa.Column(
            "trial_id",
            sa.String(),
            sa.ForeignKey("team_performance_trials.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("event_key", sa.String(160), nullable=False),
        sa.Column("game_id", sa.String(), sa.ForeignKey("games.id", ondelete="RESTRICT")),
        sa.Column("actor_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON()),
        _time("recorded_at"),
        sa.UniqueConstraint("trial_id", "event_key", name="uq_team_trial_event_key"),
        sa.CheckConstraint("length(trim(reason)) > 0", name="ck_team_trial_event_reason"),
    )
    op.create_index(
        "ix_team_trial_events_trial_time",
        "team_performance_trial_events",
        ["trial_id", "recorded_at"],
    )
    op.create_table(
        "team_performance_trial_consumptions",
        _id(),
        sa.Column(
            "trial_id",
            sa.String(),
            sa.ForeignKey("team_performance_trials.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "game_id", sa.String(), sa.ForeignKey("games.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "completion_event_id",
            sa.String(),
            sa.ForeignKey("team_performance_trial_completions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("played_date", sa.Date(), nullable=False),
        sa.Column("metadata_revision", sa.Integer(), nullable=False),
        sa.Column("ledger_digest", sa.String(64), nullable=False),
        _time("recorded_at"),
        sa.UniqueConstraint("trial_id", "game_id", name="uq_team_trial_consumed_game"),
        sa.UniqueConstraint(
            "trial_id", "completion_event_id", name="uq_team_trial_completion_event"
        ),
        sa.CheckConstraint("metadata_revision >= 1", name="ck_team_trial_consumption_revision"),
    )
    op.create_index(
        "ix_team_performance_trial_consumptions_trial_id",
        "team_performance_trial_consumptions",
        ["trial_id"],
    )
    op.create_table(
        "team_performance_trial_snapshots",
        _id(),
        sa.Column(
            "trial_id",
            sa.String(),
            sa.ForeignKey("team_performance_trials.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        _time("created_at"),
        sa.CheckConstraint("ordinal BETWEEN 1 AND 3", name="ck_team_trial_snapshot_ordinal"),
    )
    op.create_index(
        "ix_team_trial_snapshot_trial_ordinal",
        "team_performance_trial_snapshots",
        ["trial_id", "ordinal"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        "team_performance_trial_snapshots",
        "team_performance_trial_consumptions",
        "team_performance_trial_events",
        "team_performance_trial_completions",
        "team_performance_trials",
        "team_performance_trial_availability_events",
        "team_performance_trial_availability",
    ):
        if bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first() is not None:
            raise RuntimeError(
                "Cannot downgrade Team Performance trial with availability or audit history"
            )
    op.drop_index(
        "ix_team_trial_snapshot_trial_ordinal", table_name="team_performance_trial_snapshots"
    )
    op.drop_table("team_performance_trial_snapshots")
    op.drop_index(
        "ix_team_performance_trial_consumptions_trial_id",
        table_name="team_performance_trial_consumptions",
    )
    op.drop_table("team_performance_trial_consumptions")
    op.drop_index("ix_team_trial_events_trial_time", table_name="team_performance_trial_events")
    op.drop_table("team_performance_trial_events")
    op.drop_index("ix_team_trial_completion_order", table_name="team_performance_trial_completions")
    op.drop_table("team_performance_trial_completions")
    op.drop_index(
        "ix_team_performance_trials_organization_id", table_name="team_performance_trials"
    )
    op.drop_table("team_performance_trials")
    op.drop_index(
        "ix_team_performance_trial_availability_events_organization_id",
        table_name="team_performance_trial_availability_events",
    )
    op.drop_table("team_performance_trial_availability_events")
    op.drop_table("team_performance_trial_availability")

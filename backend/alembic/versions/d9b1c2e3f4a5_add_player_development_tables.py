"""add player development tables

Revision ID: d9b1c2e3f4a5
Revises: c9d8e7f6a5b4
Create Date: 2026-05-16 00:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9b1c2e3f4a5"
down_revision: str | None = "c9d8e7f6a5b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

player_development_plan_status = sa.Enum(
    "draft",
    "active",
    "paused",
    "completed",
    "archived",
    name="player_development_plan_status",
)
player_development_source_type = sa.Enum(
    "match_data",
    "video_analysis",
    "coach_note",
    "ai_insight",
    "manual",
    name="player_development_source_type",
)
player_development_severity = sa.Enum(
    "low",
    "medium",
    "high",
    name="player_development_severity",
)
player_development_approval_state = sa.Enum(
    "not_required",
    "pending_review",
    "approved",
    "rejected",
    "changes_requested",
    name="player_development_approval_state",
)
json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    """Create Phase 9B player development tables."""
    bind = op.get_bind()
    player_development_plan_status.create(bind, checkfirst=True)
    player_development_source_type.create(bind, checkfirst=True)
    player_development_severity.create(bind, checkfirst=True)
    player_development_approval_state.create(bind, checkfirst=True)

    op.create_table(
        "player_development_plans",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("player_profile_id", sa.String(), nullable=False),
        sa.Column("coach_user_id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "status",
            player_development_plan_status,
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "source_type",
            player_development_source_type,
            nullable=False,
            server_default="manual",
        ),
        sa.Column("coach_approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "approval_state",
            player_development_approval_state,
            nullable=False,
            server_default="not_required",
        ),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("evidence_refs", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("ai_metadata", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_player_development_plans_confidence_range",
        ),
        sa.ForeignKeyConstraint(["coach_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["player_profile_id"], ["player_profiles.player_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_player_development_plans_player_profile_id",
        "player_development_plans",
        ["player_profile_id"],
    )
    op.create_index(
        "ix_player_development_plans_coach_user_id",
        "player_development_plans",
        ["coach_user_id"],
    )
    op.create_index("ix_player_development_plans_org_id", "player_development_plans", ["org_id"])
    op.create_index("ix_player_development_plans_status", "player_development_plans", ["status"])
    op.create_index(
        "ix_player_development_plans_source_type",
        "player_development_plans",
        ["source_type"],
    )
    op.create_index(
        "ix_player_development_plans_owner_status",
        "player_development_plans",
        ["player_profile_id", "coach_user_id", "org_id", "status"],
    )

    op.create_table(
        "player_development_goals",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_metric", sa.String(length=100), nullable=True),
        sa.Column("baseline_value", sa.Float(), nullable=True),
        sa.Column("target_value", sa.Float(), nullable=True),
        sa.Column("current_value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column(
            "status",
            player_development_plan_status,
            nullable=False,
            server_default="draft",
        ),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("evidence_refs", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["player_development_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_development_goals_plan_id", "player_development_goals", ["plan_id"])
    op.create_index("ix_player_development_goals_status", "player_development_goals", ["status"])

    op.create_table(
        "player_weakness_tags",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("player_profile_id", sa.String(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("safe_display_label", sa.String(length=255), nullable=False),
        sa.Column(
            "severity",
            player_development_severity,
            nullable=False,
            server_default="medium",
        ),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column(
            "source_type",
            player_development_source_type,
            nullable=False,
            server_default="manual",
        ),
        sa.Column("evidence_refs", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("ai_metadata", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_player_weakness_tags_confidence_range",
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["player_development_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["player_profile_id"], ["player_profiles.player_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_weakness_tags_plan_id", "player_weakness_tags", ["plan_id"])
    op.create_index(
        "ix_player_weakness_tags_player_profile_id",
        "player_weakness_tags",
        ["player_profile_id"],
    )
    op.create_index("ix_player_weakness_tags_category", "player_weakness_tags", ["category"])
    op.create_index(
        "ix_player_weakness_tags_source_type",
        "player_weakness_tags",
        ["source_type"],
    )

    op.create_table(
        "player_strength_tags",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("player_profile_id", sa.String(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column(
            "source_type",
            player_development_source_type,
            nullable=False,
            server_default="manual",
        ),
        sa.Column("evidence_refs", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("ai_metadata", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_player_strength_tags_confidence_range",
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["player_development_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["player_profile_id"], ["player_profiles.player_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_strength_tags_plan_id", "player_strength_tags", ["plan_id"])
    op.create_index(
        "ix_player_strength_tags_player_profile_id",
        "player_strength_tags",
        ["player_profile_id"],
    )
    op.create_index("ix_player_strength_tags_category", "player_strength_tags", ["category"])
    op.create_index(
        "ix_player_strength_tags_source_type",
        "player_strength_tags",
        ["source_type"],
    )

    op.create_table(
        "player_development_interventions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("coach_user_id", sa.String(), nullable=False),
        sa.Column(
            "source_type",
            player_development_source_type,
            nullable=False,
            server_default="manual",
        ),
        sa.Column("intervention_type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_refs", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["coach_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["player_development_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_player_development_interventions_plan_id",
        "player_development_interventions",
        ["plan_id"],
    )
    op.create_index(
        "ix_player_development_interventions_coach_user_id",
        "player_development_interventions",
        ["coach_user_id"],
    )
    op.create_index(
        "ix_player_development_interventions_source_type",
        "player_development_interventions",
        ["source_type"],
    )

    op.create_table(
        "player_drill_assignments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("player_profile_id", sa.String(), nullable=False),
        sa.Column("coach_user_id", sa.String(), nullable=False),
        sa.Column("drill_category", sa.String(length=100), nullable=False),
        sa.Column("drill_name", sa.String(length=255), nullable=False),
        sa.Column("drill_description", sa.Text(), nullable=True),
        sa.Column("frequency", sa.String(length=100), nullable=True),
        sa.Column(
            "status",
            player_development_plan_status,
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_refs", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["coach_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["player_development_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["player_profile_id"], ["player_profiles.player_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_player_drill_assignments_plan_id",
        "player_drill_assignments",
        ["plan_id"],
    )
    op.create_index(
        "ix_player_drill_assignments_player_profile_id",
        "player_drill_assignments",
        ["player_profile_id"],
    )
    op.create_index(
        "ix_player_drill_assignments_coach_user_id",
        "player_drill_assignments",
        ["coach_user_id"],
    )
    op.create_index("ix_player_drill_assignments_status", "player_drill_assignments", ["status"])

    op.create_table(
        "player_progress_checkpoints",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("player_profile_id", sa.String(), nullable=False),
        sa.Column("coach_user_id", sa.String(), nullable=False),
        sa.Column("checkpoint_date", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("progress_status", sa.String(length=100), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("evidence_refs", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("ai_metadata", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("coach_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_player_progress_checkpoints_confidence_range",
        ),
        sa.ForeignKeyConstraint(["coach_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["player_development_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["player_profile_id"], ["player_profiles.player_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_player_progress_checkpoints_plan_id",
        "player_progress_checkpoints",
        ["plan_id"],
    )
    op.create_index(
        "ix_player_progress_checkpoints_player_profile_id",
        "player_progress_checkpoints",
        ["player_profile_id"],
    )
    op.create_index(
        "ix_player_progress_checkpoints_coach_user_id",
        "player_progress_checkpoints",
        ["coach_user_id"],
    )
    op.create_index(
        "ix_player_progress_checkpoints_progress_status",
        "player_progress_checkpoints",
        ["progress_status"],
    )
    op.create_index(
        "ix_player_progress_checkpoints_player_date",
        "player_progress_checkpoints",
        ["player_profile_id", "checkpoint_date"],
    )


def downgrade() -> None:
    """Drop Phase 9B player development tables."""
    op.drop_index(
        "ix_player_progress_checkpoints_player_date",
        table_name="player_progress_checkpoints",
    )
    op.drop_index(
        "ix_player_progress_checkpoints_progress_status",
        table_name="player_progress_checkpoints",
    )
    op.drop_index(
        "ix_player_progress_checkpoints_coach_user_id",
        table_name="player_progress_checkpoints",
    )
    op.drop_index(
        "ix_player_progress_checkpoints_player_profile_id",
        table_name="player_progress_checkpoints",
    )
    op.drop_index("ix_player_progress_checkpoints_plan_id", table_name="player_progress_checkpoints")
    op.drop_table("player_progress_checkpoints")

    op.drop_index("ix_player_drill_assignments_status", table_name="player_drill_assignments")
    op.drop_index(
        "ix_player_drill_assignments_coach_user_id",
        table_name="player_drill_assignments",
    )
    op.drop_index(
        "ix_player_drill_assignments_player_profile_id",
        table_name="player_drill_assignments",
    )
    op.drop_index("ix_player_drill_assignments_plan_id", table_name="player_drill_assignments")
    op.drop_table("player_drill_assignments")

    op.drop_index(
        "ix_player_development_interventions_source_type",
        table_name="player_development_interventions",
    )
    op.drop_index(
        "ix_player_development_interventions_coach_user_id",
        table_name="player_development_interventions",
    )
    op.drop_index(
        "ix_player_development_interventions_plan_id",
        table_name="player_development_interventions",
    )
    op.drop_table("player_development_interventions")

    op.drop_index("ix_player_strength_tags_source_type", table_name="player_strength_tags")
    op.drop_index("ix_player_strength_tags_category", table_name="player_strength_tags")
    op.drop_index(
        "ix_player_strength_tags_player_profile_id",
        table_name="player_strength_tags",
    )
    op.drop_index("ix_player_strength_tags_plan_id", table_name="player_strength_tags")
    op.drop_table("player_strength_tags")

    op.drop_index("ix_player_weakness_tags_source_type", table_name="player_weakness_tags")
    op.drop_index("ix_player_weakness_tags_category", table_name="player_weakness_tags")
    op.drop_index(
        "ix_player_weakness_tags_player_profile_id",
        table_name="player_weakness_tags",
    )
    op.drop_index("ix_player_weakness_tags_plan_id", table_name="player_weakness_tags")
    op.drop_table("player_weakness_tags")

    op.drop_index("ix_player_development_goals_status", table_name="player_development_goals")
    op.drop_index("ix_player_development_goals_plan_id", table_name="player_development_goals")
    op.drop_table("player_development_goals")

    op.drop_index(
        "ix_player_development_plans_owner_status",
        table_name="player_development_plans",
    )
    op.drop_index(
        "ix_player_development_plans_source_type",
        table_name="player_development_plans",
    )
    op.drop_index("ix_player_development_plans_status", table_name="player_development_plans")
    op.drop_index("ix_player_development_plans_org_id", table_name="player_development_plans")
    op.drop_index(
        "ix_player_development_plans_coach_user_id",
        table_name="player_development_plans",
    )
    op.drop_index(
        "ix_player_development_plans_player_profile_id",
        table_name="player_development_plans",
    )
    op.drop_table("player_development_plans")

    bind = op.get_bind()
    player_development_approval_state.drop(bind, checkfirst=True)
    player_development_severity.drop(bind, checkfirst=True)
    player_development_source_type.drop(bind, checkfirst=True)
    player_development_plan_status.drop(bind, checkfirst=True)

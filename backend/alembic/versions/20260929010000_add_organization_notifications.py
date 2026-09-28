"""add_organization_notifications

Revision ID: 20260929010000
Revises: 20260928010000
Create Date: 2026-09-29 01:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260929010000"
down_revision: str | Sequence[str] | None = "20260928010000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_CATEGORIES = (
    "'organization_announcement', 'team_announcement', 'event', "
    "'selection', 'availability_reminder'"
)


def upgrade() -> None:
    op.create_table(
        "organization_notifications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("recipient_user_id", sa.String(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("source_version", sa.String(length=128), nullable=True),
        sa.Column("source_key", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("actor_user_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            f"category IN ({_CATEGORIES})",
            name="ck_organization_notifications_category",
        ),
        sa.CheckConstraint(
            "source_type IN ('organization_announcement', 'team_announcement', "
            "'organization_event', 'selection_publication', 'availability_target')",
            name="ck_organization_notifications_source_type",
        ),
        sa.CheckConstraint(
            "(category = 'organization_announcement' AND source_type = "
            "'organization_announcement') OR "
            "(category = 'team_announcement' AND source_type = 'team_announcement') OR "
            "(category = 'event' AND source_type = 'organization_event') OR "
            "(category = 'selection' AND source_type = 'selection_publication') OR "
            "(category = 'availability_reminder' AND source_type = 'availability_target')",
            name="ck_organization_notifications_category_source",
        ),
        sa.CheckConstraint(
            "source_id IS NOT NULL OR source_key IS NOT NULL",
            name="ck_organization_notifications_source_identity",
        ),
        sa.CheckConstraint(
            "(origin = 'actor' AND actor_user_id IS NOT NULL) OR "
            "(origin = 'system' AND actor_user_id IS NULL)",
            name="ck_organization_notifications_origin_actor",
        ),
        sa.CheckConstraint(
            "read_at IS NULL OR read_at >= created_at",
            name="ck_organization_notifications_read_time",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_organization_notifications_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.id"],
            name="fk_organization_notifications_recipient_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_organization_notifications_actor_user",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "recipient_user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
            name="fk_organization_notifications_recipient_membership",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_notifications"),
        sa.UniqueConstraint(
            "organization_id",
            "recipient_user_id",
            "idempotency_key",
            name="uq_organization_notifications_logical_delivery",
        ),
    )
    op.create_index(
        "ix_organization_notifications_inbox",
        "organization_notifications",
        ["organization_id", "recipient_user_id", "created_at", "id"],
    )
    op.create_index(
        "ix_organization_notifications_unread",
        "organization_notifications",
        ["organization_id", "recipient_user_id", "created_at", "id"],
        postgresql_where=sa.text("read_at IS NULL"),
    )
    op.create_index(
        "ix_organization_notifications_category",
        "organization_notifications",
        ["organization_id", "recipient_user_id", "category", "created_at", "id"],
    )

    op.create_table(
        "organization_notification_preferences",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
            f"category IN ({_CATEGORIES})",
            name="ck_organization_notification_preferences_category",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_organization_notification_preferences_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_organization_notification_preferences_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["organization_memberships.organization_id", "organization_memberships.user_id"],
            name="fk_organization_notification_preferences_membership",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_notification_preferences"),
        sa.UniqueConstraint(
            "organization_id",
            "user_id",
            "category",
            name="uq_organization_notification_preferences_user_category",
        ),
    )
    op.create_index(
        "ix_organization_notification_preferences_user",
        "organization_notification_preferences",
        ["organization_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_notification_preferences_user",
        table_name="organization_notification_preferences",
    )
    op.drop_table("organization_notification_preferences")
    op.drop_index(
        "ix_organization_notifications_category",
        table_name="organization_notifications",
    )
    op.drop_index(
        "ix_organization_notifications_unread",
        table_name="organization_notifications",
    )
    op.drop_index(
        "ix_organization_notifications_inbox",
        table_name="organization_notifications",
    )
    op.drop_table("organization_notifications")

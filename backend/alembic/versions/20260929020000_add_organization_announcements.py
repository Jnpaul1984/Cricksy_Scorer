"""add_organization_announcements

Revision ID: 20260929020000
Revises: 20260929010000
Create Date: 2026-09-29 02:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260929020000"
down_revision: str | Sequence[str] | None = "20260929010000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization_announcements",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("audience_type", sa.String(length=24), nullable=False),
        sa.Column("team_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("last_published_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
        sa.Column("updated_by_user_id", sa.String(), nullable=True),
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
            "audience_type IN ('organization', 'team', 'staff')",
            name="ck_organization_announcements_audience",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published')",
            name="ck_organization_announcements_status",
        ),
        sa.CheckConstraint(
            "(audience_type = 'team' AND team_id IS NOT NULL) OR "
            "(audience_type <> 'team' AND team_id IS NULL)",
            name="ck_organization_announcements_team_audience",
        ),
        sa.CheckConstraint(
            "revision >= 1 AND last_published_version >= 0",
            name="ck_organization_announcements_versions",
        ),
        sa.CheckConstraint(
            "status <> 'published' OR last_published_version >= 1",
            name="ck_organization_announcements_published_version",
        ),
        sa.CheckConstraint(
            "length(title) BETWEEN 1 AND 255",
            name="ck_organization_announcements_title_length",
        ),
        sa.CheckConstraint(
            "length(body) BETWEEN 1 AND 6000",
            name="ck_organization_announcements_body_length",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_organization_announcements_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id", "organization_id"],
            ["teams.id", "teams.organization_id"],
            name="fk_organization_announcements_team_organization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_organization_announcements_created_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["users.id"],
            name="fk_organization_announcements_updated_by",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_announcements"),
        sa.UniqueConstraint(
            "id",
            "organization_id",
            name="uq_organization_announcements_id_organization",
        ),
    )
    op.create_index(
        "ix_organization_announcements_feed",
        "organization_announcements",
        ["organization_id", "status", "updated_at", "id"],
    )
    op.create_index(
        "ix_organization_announcements_team",
        "organization_announcements",
        ["organization_id", "team_id", "status"],
    )

    op.create_table(
        "organization_announcement_publications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("announcement_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("publication_version", sa.Integer(), nullable=False),
        sa.Column("announcement_revision", sa.Integer(), nullable=False),
        sa.Column("audience_type", sa.String(length=24), nullable=False),
        sa.Column("team_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("published_by_user_id", sa.String(), nullable=True),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("eligible_recipient_count", sa.Integer(), nullable=False),
        sa.Column("delivered_count", sa.Integer(), nullable=False),
        sa.Column("suppressed_by_preference_count", sa.Integer(), nullable=False),
        sa.Column("unresolved_recipient_count", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint(
            "publication_version >= 1",
            name="ck_organization_announcement_publications_version",
        ),
        sa.CheckConstraint(
            "audience_type IN ('organization', 'team', 'staff')",
            name="ck_organization_announcement_publications_audience",
        ),
        sa.CheckConstraint(
            "(audience_type = 'team' AND team_id IS NOT NULL) OR "
            "(audience_type <> 'team' AND team_id IS NULL)",
            name="ck_organization_announcement_publications_team_audience",
        ),
        sa.CheckConstraint(
            "length(title) BETWEEN 1 AND 255",
            name="ck_organization_announcement_publications_title_length",
        ),
        sa.CheckConstraint(
            "length(body) BETWEEN 1 AND 6000",
            name="ck_organization_announcement_publications_body_length",
        ),
        sa.CheckConstraint(
            "eligible_recipient_count >= 0 AND delivered_count >= 0 AND "
            "suppressed_by_preference_count >= 0 AND unresolved_recipient_count >= 0",
            name="ck_organization_announcement_publications_counts_nonnegative",
        ),
        sa.CheckConstraint(
            "eligible_recipient_count = delivered_count + "
            "suppressed_by_preference_count + unresolved_recipient_count",
            name="ck_organization_announcement_publications_counts_total",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_organization_announcement_publications_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["announcement_id", "organization_id"],
            ["organization_announcements.id", "organization_announcements.organization_id"],
            name="fk_organization_announcement_publications_announcement",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["team_id", "organization_id"],
            ["teams.id", "teams.organization_id"],
            name="fk_organization_announcement_publications_team_organization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["published_by_user_id"],
            ["users.id"],
            name="fk_organization_announcement_publications_published_by",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organization_announcement_publications"),
        sa.UniqueConstraint(
            "announcement_id",
            "publication_version",
            name="uq_organization_announcement_publication_version",
        ),
    )
    op.create_index(
        "ix_organization_announcement_publications_feed",
        "organization_announcement_publications",
        ["organization_id", "published_at", "id"],
    )
    op.create_index(
        "ix_organization_announcement_publications_team",
        "organization_announcement_publications",
        ["organization_id", "team_id", "published_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_announcement_publications_team",
        table_name="organization_announcement_publications",
    )
    op.drop_index(
        "ix_organization_announcement_publications_feed",
        table_name="organization_announcement_publications",
    )
    op.drop_table("organization_announcement_publications")
    op.drop_index(
        "ix_organization_announcements_team",
        table_name="organization_announcements",
    )
    op.drop_index(
        "ix_organization_announcements_feed",
        table_name="organization_announcements",
    )
    op.drop_table("organization_announcements")

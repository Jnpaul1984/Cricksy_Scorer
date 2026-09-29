"""add organization public publication settings

Revision ID: 20260929030000
Revises: 20260929020000
Create Date: 2026-09-29 03:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260929030000"
down_revision: str | Sequence[str] | None = "20260929020000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization_public_settings",
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("public_identifier", sa.String(length=28), nullable=False),
        sa.Column(
            "publication_state",
            sa.String(length=16),
            server_default="unpublished",
            nullable=False,
        ),
        sa.Column("publication_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unpublished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by_user_id", sa.String(), nullable=True),
        sa.Column("unpublished_by_user_id", sa.String(), nullable=True),
        sa.Column("updated_by_user_id", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "publication_state IN ('unpublished', 'published')",
            name="ck_organization_public_settings_state",
        ),
        sa.CheckConstraint(
            "public_identifier ~ '^org_[0-9a-f]{24}$'",
            name="ck_organization_public_settings_identifier",
        ),
        sa.CheckConstraint(
            "publication_version >= 1", name="ck_organization_public_settings_version"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["published_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["unpublished_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("organization_id"),
        sa.UniqueConstraint(
            "public_identifier", name="uq_organization_public_settings_public_identifier"
        ),
    )
    op.create_index(
        "ix_organization_public_settings_public_lookup",
        "organization_public_settings",
        ["public_identifier", "publication_state"],
        unique=False,
    )
    op.execute(
        """
        INSERT INTO organization_public_settings (organization_id, public_identifier)
        SELECT id, 'org_' || substring(md5(id) from 1 for 24)
        FROM organizations
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_public_settings_public_lookup",
        table_name="organization_public_settings",
    )
    op.drop_table("organization_public_settings")

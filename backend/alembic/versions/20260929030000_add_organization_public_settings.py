"""add organization public publication settings

Revision ID: 20260929030000
Revises: 20260929020000
Create Date: 2026-09-29 03:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260929030000"
down_revision: str | Sequence[str] | None = "20260929020000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ORGANIZATION_PUBLIC_SETTINGS_BACKFILL_SQL = """
DO $$
DECLARE
    organization_record RECORD;
    collision_attempt INTEGER;
    candidate TEXT;
BEGIN
    FOR organization_record IN SELECT id FROM organizations ORDER BY id LOOP
        collision_attempt := 0;
        LOOP
            IF collision_attempt >= 100 THEN
                RAISE EXCEPTION
                    'Unable to allocate public identifier for organization %',
                    organization_record.id;
            END IF;
            candidate := 'org_' || substring(
                md5(
                    organization_record.id ||
                    CASE
                        WHEN collision_attempt = 0 THEN ''
                        ELSE ':' || collision_attempt::text
                    END
                )
                from 1 for 24
            );
            BEGIN
                INSERT INTO organization_public_settings (
                    organization_id,
                    public_identifier
                )
                VALUES (organization_record.id, candidate);
                EXIT;
            EXCEPTION WHEN unique_violation THEN
                collision_attempt := collision_attempt + 1;
            END;
        END LOOP;
    END LOOP;
END
$$;
"""


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
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["published_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unpublished_by_user_id"], ["users.id"], ondelete="SET NULL"),
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
    op.execute(ORGANIZATION_PUBLIC_SETTINGS_BACKFILL_SQL)


def downgrade() -> None:
    op.drop_index(
        "ix_organization_public_settings_public_lookup",
        table_name="organization_public_settings",
    )
    op.drop_table("organization_public_settings")

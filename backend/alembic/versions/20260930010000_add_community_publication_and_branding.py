"""add community competition publication and durable basic branding

Revision ID: 20260930010000
Revises: 20260929030000
Create Date: 2026-09-30 01:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260930010000"
down_revision: str | Sequence[str] | None = "20260929030000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COMPETITION_PUBLICATION_BACKFILL_SQL = """
INSERT INTO organization_competition_publications (competition_id, organization_id)
SELECT id, organization_id
FROM tournaments
WHERE organization_id IS NOT NULL
ON CONFLICT (competition_id) DO NOTHING
"""


def upgrade() -> None:
    op.add_column(
        "organization_public_settings",
        sa.Column("logo_url", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "organization_public_settings",
        sa.Column("logo_alt_text", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "organization_public_settings",
        sa.Column("branding_version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "organization_public_settings",
        sa.Column("branding_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organization_public_settings",
        sa.Column("branding_updated_by_user_id", sa.String(), nullable=True),
    )
    op.create_foreign_key(
        "fk_org_public_settings_branding_user",
        "organization_public_settings",
        "users",
        ["branding_updated_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_organization_public_settings_branding_version",
        "organization_public_settings",
        "branding_version >= 1",
    )
    op.create_check_constraint(
        "ck_organization_public_settings_logo_url",
        "organization_public_settings",
        "logo_url IS NULL OR (length(logo_url) <= 2048 AND "
        "logo_url LIKE 'https://%' AND logo_url NOT LIKE '%<%' AND logo_url NOT LIKE '%>%')",
    )
    op.create_check_constraint(
        "ck_organization_public_settings_logo_alt_text",
        "organization_public_settings",
        "logo_alt_text IS NULL OR (length(logo_alt_text) <= 120 AND "
        "logo_alt_text NOT LIKE '%<%' AND logo_alt_text NOT LIKE '%>%')",
    )
    op.create_check_constraint(
        "ck_organization_public_settings_logo_pair",
        "organization_public_settings",
        "(logo_url IS NULL AND logo_alt_text IS NULL) OR "
        "(logo_url IS NOT NULL AND logo_alt_text IS NOT NULL)",
    )

    op.create_table(
        "organization_competition_publications",
        sa.Column("competition_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
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
            name="ck_organization_competition_publications_state",
        ),
        sa.CheckConstraint(
            "publication_version >= 1",
            name="ck_organization_competition_publications_version",
        ),
        sa.ForeignKeyConstraint(
            ["competition_id", "organization_id"],
            ["tournaments.id", "tournaments.organization_id"],
            ondelete="CASCADE",
            name="fk_org_comp_publication_tournament_org",
        ),
        sa.ForeignKeyConstraint(["published_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unpublished_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("competition_id"),
    )
    op.create_index(
        "ix_organization_competition_publications_public_lookup",
        "organization_competition_publications",
        ["organization_id", "publication_state"],
        unique=False,
    )
    op.execute(COMPETITION_PUBLICATION_BACKFILL_SQL)


def downgrade() -> None:
    op.drop_index(
        "ix_organization_competition_publications_public_lookup",
        table_name="organization_competition_publications",
    )
    op.drop_table("organization_competition_publications")
    op.drop_constraint(
        "ck_organization_public_settings_logo_pair",
        "organization_public_settings",
        type_="check",
    )
    op.drop_constraint(
        "ck_organization_public_settings_logo_alt_text",
        "organization_public_settings",
        type_="check",
    )
    op.drop_constraint(
        "ck_organization_public_settings_logo_url",
        "organization_public_settings",
        type_="check",
    )
    op.drop_constraint(
        "ck_organization_public_settings_branding_version",
        "organization_public_settings",
        type_="check",
    )
    op.drop_constraint(
        "fk_org_public_settings_branding_user",
        "organization_public_settings",
        type_="foreignkey",
    )
    op.drop_column("organization_public_settings", "branding_updated_by_user_id")
    op.drop_column("organization_public_settings", "branding_updated_at")
    op.drop_column("organization_public_settings", "branding_version")
    op.drop_column("organization_public_settings", "logo_alt_text")
    op.drop_column("organization_public_settings", "logo_url")

"""add opaque competition keys and staff public entity favorites

Revision ID: 20261001030000
Revises: 20261001020000
Create Date: 2026-10-01 03:00:00.000000

This local patch deliberately stacks after the unmerged Team-publication migration.
Do not apply independently or merge it as a second Alembic head.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261001030000"
down_revision: str | Sequence[str] | None = "20261001020000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organization_competition_publications", sa.Column("public_key", sa.String(28), nullable=True))
    # Deterministic opaque backfill. It does not expose tournament IDs and the API only accepts cmp_ keys.
    op.execute("UPDATE organization_competition_publications SET public_key = 'cmp_' || substr(md5('cricksy-public-competition:' || competition_id), 1, 24) WHERE public_key IS NULL")
    op.alter_column("organization_competition_publications", "public_key", nullable=False)
    op.create_unique_constraint("uq_organization_competition_publications_public_key", "organization_competition_publications", ["public_key"])
    op.create_table(
        "public_entity_favorites",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("subject_kind", sa.String(16), nullable=False),
        sa.Column("subject_public_key", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("subject_kind IN ('organization', 'team', 'competition')", name="ck_public_entity_favorites_subject_kind"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "subject_kind", "subject_public_key", name="uq_public_entity_favorites_user_subject"),
    )
    op.create_index("ix_public_entity_favorites_user_created", "public_entity_favorites", ["user_id", "created_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_public_entity_favorites_user_created", table_name="public_entity_favorites")
    op.drop_table("public_entity_favorites")
    op.drop_constraint("uq_organization_competition_publications_public_key", "organization_competition_publications", type_="unique")
    op.drop_column("organization_competition_publications", "public_key")

"""add default-private organization team publication

Revision ID: 20261001020000
Revises: 20261001010001
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision = "20261001020000"
down_revision: str | Sequence[str] | None = "20261001010001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("organization_team_publications", sa.Column("team_id", sa.String(), primary_key=True), sa.Column("organization_id", sa.String(), nullable=False), sa.Column("public_identifier", sa.String(29), nullable=False), sa.Column("publication_state", sa.String(16), nullable=False, server_default="unpublished"), sa.Column("publication_version", sa.Integer(), nullable=False, server_default="1"), sa.Column("published_at", sa.DateTime(timezone=True)), sa.Column("unpublished_at", sa.DateTime(timezone=True)), sa.Column("published_by_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("unpublished_by_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("updated_by_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.ForeignKeyConstraint(["team_id", "organization_id"], ["teams.id", "teams.organization_id"], ondelete="CASCADE", name="fk_org_team_publication_team_org"), sa.UniqueConstraint("public_identifier", name="uq_org_team_publication_public_identifier"), sa.CheckConstraint("publication_state IN ('unpublished', 'published')", name="ck_org_team_publication_state"), sa.CheckConstraint("publication_version >= 1", name="ck_org_team_publication_version"))
    op.create_index("ix_org_team_publication_public_lookup", "organization_team_publications", ["organization_id", "publication_state"])
    op.create_table("organization_team_publication_audit", sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True), sa.Column("team_id", sa.String(), nullable=False), sa.Column("organization_id", sa.String(), nullable=False), sa.Column("action", sa.String(16), nullable=False), sa.Column("actor_user_id", sa.String(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False), sa.Column("publication_version", sa.Integer(), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.ForeignKeyConstraint(["team_id", "organization_id"], ["teams.id", "teams.organization_id"], ondelete="RESTRICT", name="fk_org_team_publication_audit_team_org"), sa.CheckConstraint("action IN ('published', 'unpublished')", name="ck_org_team_publication_audit_action"), sa.CheckConstraint("publication_version >= 1", name="ck_org_team_publication_audit_version"))
    op.create_index("ix_org_team_publication_audit_team_time", "organization_team_publication_audit", ["team_id", "occurred_at"])


def downgrade() -> None:
    op.drop_table("organization_team_publication_audit")
    op.drop_table("organization_team_publications")

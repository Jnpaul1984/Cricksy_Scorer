"""add_school_master_player_roster

Revision ID: 20260916050000
Revises: 20260916040000
Create Date: 2026-09-16 05:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260916050000"
down_revision = "20260916040000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "school_player_memberships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("player_profile_id", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="active",
            nullable=False,
        ),
        sa.Column("student_identifier", sa.String(length=128), nullable=True),
        sa.Column("year_group", sa.String(length=64), nullable=True),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_school_player_memberships_status",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_school_player_memberships_created_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_school_player_memberships_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["player_profile_id"],
            ["player_profiles.player_id"],
            name="fk_school_player_memberships_player_profile_id_player_profiles",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_school_player_memberships"),
        sa.UniqueConstraint(
            "organization_id",
            "player_profile_id",
            name="uq_school_player_memberships_organization_player",
        ),
    )
    op.create_index(
        "ix_school_player_memberships_organization_id",
        "school_player_memberships",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_school_player_memberships_player_profile_id",
        "school_player_memberships",
        ["player_profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_school_player_memberships_organization_status",
        "school_player_memberships",
        ["organization_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_school_player_memberships_organization_status",
        table_name="school_player_memberships",
    )
    op.drop_index(
        "ix_school_player_memberships_player_profile_id",
        table_name="school_player_memberships",
    )
    op.drop_index(
        "ix_school_player_memberships_organization_id",
        table_name="school_player_memberships",
    )
    op.drop_table("school_player_memberships")

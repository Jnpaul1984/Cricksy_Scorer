"""add_school_team_player_memberships

Revision ID: 20260916060000
Revises: 20260916050000
Create Date: 2026-09-16 06:00:00

The association stores authoritative Team and School master-roster identifiers.
Same-organization equality is enforced by the service because adding composite
parent keys solely for this revision would broaden the Phase 7D/7E schemas.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260916060000"
down_revision = "20260916050000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "school_team_player_memberships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("team_id", sa.String(), nullable=False),
        sa.Column("school_player_membership_id", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="active",
            nullable=False,
        ),
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
            name="ck_school_team_player_memberships_status",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_school_team_players_creator",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_school_team_players_organization",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["school_player_membership_id"],
            ["school_player_memberships.id"],
            name="fk_school_team_players_school_player",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name="fk_school_team_players_team",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_school_team_player_memberships"),
        sa.UniqueConstraint(
            "team_id",
            "school_player_membership_id",
            name="uq_school_team_player_memberships_team_player",
        ),
    )
    op.create_index(
        "ix_school_team_player_memberships_organization_id",
        "school_team_player_memberships",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_school_team_player_memberships_team_id",
        "school_team_player_memberships",
        ["team_id"],
        unique=False,
    )
    op.create_index(
        "ix_school_team_player_memberships_school_player_membership_id",
        "school_team_player_memberships",
        ["school_player_membership_id"],
        unique=False,
    )
    op.create_index(
        "ix_school_team_player_memberships_organization_team_status",
        "school_team_player_memberships",
        ["organization_id", "team_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_school_team_player_memberships_organization_team_status",
        table_name="school_team_player_memberships",
    )
    op.drop_index(
        "ix_school_team_player_memberships_school_player_membership_id",
        table_name="school_team_player_memberships",
    )
    op.drop_index(
        "ix_school_team_player_memberships_team_id",
        table_name="school_team_player_memberships",
    )
    op.drop_index(
        "ix_school_team_player_memberships_organization_id",
        table_name="school_team_player_memberships",
    )
    op.drop_table("school_team_player_memberships")

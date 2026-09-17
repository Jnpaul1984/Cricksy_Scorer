"""add_school_player_import_sessions

Revision ID: 20260916070000
Revises: 20260916060000
Create Date: 2026-09-16 07:00:00

Stores immutable normalized preview state and the apply result. Raw uploaded files
are parsed in memory and are never persisted.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260916070000"
down_revision = "20260916060000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "school_player_imports",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("actor_user_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="previewed", nullable=False),
        sa.Column("file_type", sa.String(length=8), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("column_mapping", sa.JSON(), nullable=False),
        sa.Column("preview_rows", sa.JSON(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('previewed', 'applied')",
            name="ck_school_player_imports_status",
        ),
        sa.CheckConstraint(
            "file_type IN ('csv', 'xlsx')",
            name="ck_school_player_imports_file_type",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_school_player_imports_actor",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_school_player_imports_organization",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_school_player_imports"),
    )
    op.create_index(
        "ix_school_player_imports_organization_id",
        "school_player_imports",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_school_player_imports_actor_user_id",
        "school_player_imports",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_school_player_imports_organization_actor_status",
        "school_player_imports",
        ["organization_id", "actor_user_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_school_player_imports_organization_actor_status",
        table_name="school_player_imports",
    )
    op.drop_index(
        "ix_school_player_imports_actor_user_id",
        table_name="school_player_imports",
    )
    op.drop_index(
        "ix_school_player_imports_organization_id",
        table_name="school_player_imports",
    )
    op.drop_table("school_player_imports")

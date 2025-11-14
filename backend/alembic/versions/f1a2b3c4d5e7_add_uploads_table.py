"""add uploads table

Revision ID: f1a2b3c4d5e7
Revises: 9ceb65587e9a
Create Date: 2025-11-10 01:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e7"
down_revision: str | Sequence[str] | None = "9ceb65587e9a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum type for upload status
    op.execute(
        """
        CREATE TYPE upload_status AS ENUM (
            'initiated', 'uploaded', 'processing', 
            'parsed', 'applied', 'failed', 'cancelled'
        )
        """
    )

    # Create uploads table
    op.create_table(
        "uploads",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("s3_bucket", sa.String(), nullable=False),
        sa.Column("s3_key", sa.String(), nullable=False),
        sa.Column("presigned_url", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "initiated",
                "uploaded",
                "processing",
                "parsed",
                "applied",
                "failed",
                "cancelled",
                name="upload_status",
            ),
            nullable=False,
            server_default="initiated",
        ),
        sa.Column("parsed_preview", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(op.f("ix_uploads_id"), "uploads", ["id"], unique=False)
    op.create_index(op.f("ix_uploads_game_id"), "uploads", ["game_id"], unique=False)
    op.create_index(op.f("ix_uploads_status"), "uploads", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_uploads_status"), table_name="uploads")
    op.drop_index(op.f("ix_uploads_game_id"), table_name="uploads")
    op.drop_index(op.f("ix_uploads_id"), table_name="uploads")
    op.drop_table("uploads")
    op.execute("DROP TYPE upload_status")

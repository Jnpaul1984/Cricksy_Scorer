"""add ai_insight_reviews table

Phase 8C — AI Insight Feedback + Review Workflow.

Creates the ``ai_insight_reviews`` table used to store reviewer decisions
on AI-generated insights.  This table holds advisory metadata only and
must never be used to mutate official cricket truth.

Revision ID: c9d8e7f6a5b4
Revises: b1c2d3e4f5a6
Create Date: 2026-05-15 04:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d8e7f6a5b4"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create ai_insight_reviews table and associated enums."""
    op.create_table(
        "ai_insight_reviews",
        sa.Column("id", sa.String(), nullable=False, primary_key=True),
        sa.Column(
            "insight_type",
            sa.String(64),
            nullable=False,
            comment="AI output type: summary, insight, commentary, recommendation, report, draft",
        ),
        sa.Column(
            "insight_id",
            sa.String(256),
            nullable=False,
            comment="Logical ID for the insight (e.g. match_id, player_id)",
        ),
        sa.Column(
            "reviewer_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column(
            "reviewer_org_id",
            sa.String(),
            nullable=True,
            comment="Org at time of review (snapshot)",
        ),
        sa.Column(
            "review_state",
            sa.String(64),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "feedback_type",
            sa.String(64),
            nullable=True,
        ),
        sa.Column(
            "note",
            sa.Text(),
            nullable=True,
            comment="Optional reviewer note or change request text",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_ai_insight_reviews_insight_type",
        "ai_insight_reviews",
        ["insight_type"],
    )
    op.create_index(
        "ix_ai_insight_reviews_insight_id",
        "ai_insight_reviews",
        ["insight_id"],
    )
    op.create_index(
        "ix_ai_insight_reviews_reviewer_id",
        "ai_insight_reviews",
        ["reviewer_id"],
    )
    op.create_index(
        "ix_ai_insight_review_type_id",
        "ai_insight_reviews",
        ["insight_type", "insight_id"],
    )
    op.create_index(
        "ix_ai_insight_reviews_review_state",
        "ai_insight_reviews",
        ["review_state"],
    )


def downgrade() -> None:
    """Drop ai_insight_reviews table."""
    op.drop_index("ix_ai_insight_reviews_review_state", table_name="ai_insight_reviews")
    op.drop_index("ix_ai_insight_review_type_id", table_name="ai_insight_reviews")
    op.drop_index("ix_ai_insight_reviews_reviewer_id", table_name="ai_insight_reviews")
    op.drop_index("ix_ai_insight_reviews_insight_id", table_name="ai_insight_reviews")
    op.drop_index("ix_ai_insight_reviews_insight_type", table_name="ai_insight_reviews")
    op.drop_table("ai_insight_reviews")

"""add mental questionnaire MVP tables

Revision ID: r5s6t7u8v9w0
Revises: p3q4r5s6t7u8
Create Date: 2026-05-10 05:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "r5s6t7u8v9w0"
down_revision: Union[str, Sequence[str], None] = "p3q4r5s6t7u8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


mental_questionnaire_category = sa.Enum(
    "Mental Toughness",
    "Pressure Handling",
    "Game Awareness / Cricket IQ",
    "Training Habits & Discipline",
    name="mental_questionnaire_category",
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "mental_questionnaire_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category", mental_questionnaire_category, nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mental_questionnaire_question_category_order",
        "mental_questionnaire_questions",
        ["category", "display_order"],
        unique=True,
    )
    op.create_index(
        "ix_mental_questionnaire_questions_category",
        "mental_questionnaire_questions",
        ["category"],
        unique=False,
    )

    questions = sa.table(
        "mental_questionnaire_questions",
        sa.column("category", sa.String()),
        sa.column("question_text", sa.Text()),
        sa.column("display_order", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        questions,
        [
            {
                "category": "Mental Toughness",
                "question_text": "I stay focused and bounce back quickly after setbacks in training or matches.",
                "display_order": 1,
                "is_active": True,
            },
            {
                "category": "Mental Toughness",
                "question_text": "I keep my effort level strong even when situations become difficult.",
                "display_order": 2,
                "is_active": True,
            },
            {
                "category": "Pressure Handling",
                "question_text": "I stay calm and execute my skills when the game pressure rises.",
                "display_order": 1,
                "is_active": True,
            },
            {
                "category": "Pressure Handling",
                "question_text": "I can improve under pressure by sticking to my process and routines.",
                "display_order": 2,
                "is_active": True,
            },
            {
                "category": "Game Awareness / Cricket IQ",
                "question_text": "I read match situations well and adjust decisions for the team.",
                "display_order": 1,
                "is_active": True,
            },
            {
                "category": "Game Awareness / Cricket IQ",
                "question_text": "I understand field settings, bowler plans, and scoring options clearly.",
                "display_order": 2,
                "is_active": True,
            },
            {
                "category": "Training Habits & Discipline",
                "question_text": "I follow training plans with discipline and complete key practice tasks.",
                "display_order": 1,
                "is_active": True,
            },
            {
                "category": "Training Habits & Discipline",
                "question_text": "I prepare consistently with recovery, reflection, and game-readiness habits.",
                "display_order": 2,
                "is_active": True,
            },
        ],
    )

    op.create_table(
        "mental_questionnaire_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("submitted_by_user_id", sa.String(), nullable=False),
        sa.Column("overall_average_score", sa.Float(), nullable=False),
        sa.Column("overall_summary", sa.Text(), nullable=False),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("development_areas", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["player_id"], ["player_profiles.player_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mental_questionnaire_sessions_player_created",
        "mental_questionnaire_sessions",
        ["player_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_mental_questionnaire_sessions_player_id",
        "mental_questionnaire_sessions",
        ["player_id"],
        unique=False,
    )
    op.create_index(
        "ix_mental_questionnaire_sessions_submitted_by_user_id",
        "mental_questionnaire_sessions",
        ["submitted_by_user_id"],
        unique=False,
    )

    op.create_table(
        "mental_questionnaire_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.CheckConstraint("score >= 1 AND score <= 5", name="ck_mental_questionnaire_score_range"),
        sa.ForeignKeyConstraint(["question_id"], ["mental_questionnaire_questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["mental_questionnaire_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mental_questionnaire_answers_question_id",
        "mental_questionnaire_answers",
        ["question_id"],
        unique=False,
    )
    op.create_index(
        "ix_mental_questionnaire_answers_session_id",
        "mental_questionnaire_answers",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_mental_questionnaire_answers_session_question",
        "mental_questionnaire_answers",
        ["session_id", "question_id"],
        unique=True,
    )

    op.create_table(
        "mental_questionnaire_category_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("category", mental_questionnaire_category, nullable=False),
        sa.Column("average_score", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["mental_questionnaire_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mental_questionnaire_category_scores_category",
        "mental_questionnaire_category_scores",
        ["category"],
        unique=False,
    )
    op.create_index(
        "ix_mental_questionnaire_category_scores_session_category",
        "mental_questionnaire_category_scores",
        ["session_id", "category"],
        unique=True,
    )
    op.create_index(
        "ix_mental_questionnaire_category_scores_session_id",
        "mental_questionnaire_category_scores",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_mental_questionnaire_category_scores_session_id",
        table_name="mental_questionnaire_category_scores",
    )
    op.drop_index(
        "ix_mental_questionnaire_category_scores_session_category",
        table_name="mental_questionnaire_category_scores",
    )
    op.drop_index(
        "ix_mental_questionnaire_category_scores_category",
        table_name="mental_questionnaire_category_scores",
    )
    op.drop_table("mental_questionnaire_category_scores")

    op.drop_index("ix_mental_questionnaire_answers_session_question", table_name="mental_questionnaire_answers")
    op.drop_index("ix_mental_questionnaire_answers_session_id", table_name="mental_questionnaire_answers")
    op.drop_index("ix_mental_questionnaire_answers_question_id", table_name="mental_questionnaire_answers")
    op.drop_table("mental_questionnaire_answers")

    op.drop_index(
        "ix_mental_questionnaire_sessions_submitted_by_user_id",
        table_name="mental_questionnaire_sessions",
    )
    op.drop_index("ix_mental_questionnaire_sessions_player_id", table_name="mental_questionnaire_sessions")
    op.drop_index(
        "ix_mental_questionnaire_sessions_player_created",
        table_name="mental_questionnaire_sessions",
    )
    op.drop_table("mental_questionnaire_sessions")

    op.drop_index(
        "ix_mental_questionnaire_questions_category",
        table_name="mental_questionnaire_questions",
    )
    op.drop_index(
        "ix_mental_questionnaire_question_category_order",
        table_name="mental_questionnaire_questions",
    )
    op.drop_table("mental_questionnaire_questions")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS mental_questionnaire_category")

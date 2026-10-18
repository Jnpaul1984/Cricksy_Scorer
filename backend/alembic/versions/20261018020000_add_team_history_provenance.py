"""Add trustworthy Team Performance match-history metadata.

Revision ID: 20261018020000
Revises: 20261018010000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261018020000"
down_revision: str | Sequence[str] | None = "20261018010000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("games") as batch_op:
        batch_op.add_column(sa.Column("actual_played_date", sa.Date(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "played_date_trust_state",
                sa.String(length=16),
                server_default="unknown",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("played_date_source", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("original_overs_limit", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "original_format_trust_state",
                sa.String(length=24),
                server_default="unknown",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("original_format_source", sa.String(length=32), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "team_performance_metadata_revision",
                sa.Integer(),
                server_default="1",
                nullable=False,
            )
        )
        batch_op.create_check_constraint(
            "ck_games_played_date_provenance",
            "(played_date_trust_state IS NOT NULL AND "
            "((played_date_trust_state = 'unknown' AND actual_played_date IS NULL "
            "AND played_date_source IS NULL) OR "
            "(played_date_trust_state = 'confirmed' AND actual_played_date IS NOT NULL "
            "AND played_date_source IS NOT NULL AND played_date_source = 'staff_confirmed')))",
        )
        batch_op.create_check_constraint(
            "ck_games_original_format_provenance",
            "(original_format_trust_state IS NOT NULL AND "
            "((original_format_trust_state = 'unknown' AND original_overs_limit IS NULL "
            "AND original_format_source IS NULL) OR "
            "(original_format_trust_state = 'setup_capture' "
            "AND original_overs_limit IS NOT NULL AND original_overs_limit BETWEEN 1 AND 120 "
            "AND original_format_source IS NOT NULL "
            "AND original_format_source = 'school_match_setup') OR "
            "(original_format_trust_state = 'staff_corrected' "
            "AND original_overs_limit IS NOT NULL AND original_overs_limit BETWEEN 1 AND 120 "
            "AND original_format_source IS NOT NULL "
            "AND original_format_source = 'staff_correction')))",
        )
        batch_op.create_check_constraint(
            "ck_games_team_performance_metadata_revision",
            "team_performance_metadata_revision >= 1",
        )

    op.create_index(
        "ix_games_original_overs_played_date",
        "games",
        ["original_overs_limit", "actual_played_date"],
    )
    op.create_table(
        "game_performance_metadata_audit",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("metadata_revision", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(length=32), nullable=False),
        sa.Column("old_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.String(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "field_name IN ('actual_played_date', 'original_overs_limit')",
            name="ck_game_performance_metadata_audit_field",
        ),
        sa.CheckConstraint(
            "length(trim(reason)) > 0",
            name="ck_game_performance_metadata_audit_reason",
        ),
        sa.CheckConstraint(
            "metadata_revision >= 1",
            name="ck_game_performance_metadata_audit_revision",
        ),
        sa.CheckConstraint(
            "length(trim(source)) > 0",
            name="ck_game_performance_metadata_audit_source",
        ),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "game_id",
            "metadata_revision",
            "field_name",
            name="uq_game_performance_metadata_audit_revision_field",
        ),
    )
    op.create_index(
        "ix_game_performance_metadata_audit_game_revision",
        "game_performance_metadata_audit",
        ["game_id", "metadata_revision"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    non_default_metadata = bind.execute(
        sa.text(
            "SELECT 1 FROM games WHERE actual_played_date IS NOT NULL "
            "OR played_date_trust_state <> 'unknown' "
            "OR original_overs_limit IS NOT NULL "
            "OR original_format_trust_state <> 'unknown' "
            "OR team_performance_metadata_revision <> 1 LIMIT 1"
        )
    ).first()
    audit_history = bind.execute(
        sa.text("SELECT 1 FROM game_performance_metadata_audit LIMIT 1")
    ).first()
    if non_default_metadata is not None or audit_history is not None:
        raise RuntimeError(
            "Cannot downgrade Team Performance history while confirmed metadata or audit history exists"
        )

    op.drop_index(
        "ix_game_performance_metadata_audit_game_revision",
        table_name="game_performance_metadata_audit",
    )
    op.drop_table("game_performance_metadata_audit")
    op.drop_index("ix_games_original_overs_played_date", table_name="games")
    with op.batch_alter_table("games") as batch_op:
        batch_op.drop_constraint("ck_games_team_performance_metadata_revision", type_="check")
        batch_op.drop_constraint("ck_games_original_format_provenance", type_="check")
        batch_op.drop_constraint("ck_games_played_date_provenance", type_="check")
        batch_op.drop_column("team_performance_metadata_revision")
        batch_op.drop_column("original_format_source")
        batch_op.drop_column("original_format_trust_state")
        batch_op.drop_column("original_overs_limit")
        batch_op.drop_column("played_date_source")
        batch_op.drop_column("played_date_trust_state")
        batch_op.drop_column("actual_played_date")

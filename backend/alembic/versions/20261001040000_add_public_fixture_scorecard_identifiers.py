"""add opaque fixture and scorecard identifiers for public share routes

Revision ID: 20261001040000
Revises: 20261001030000
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20261001040000"
down_revision: str | Sequence[str] | None = "20261001030000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column("fixtures", sa.Column("public_identifier", sa.String(28), nullable=True))
    op.execute("UPDATE fixtures SET public_identifier = 'fix_' || substr(md5('cricksy-public-fixture:' || id), 1, 24) WHERE public_identifier IS NULL")
    op.alter_column("fixtures", "public_identifier", nullable=False)
    op.create_unique_constraint("uq_fixtures_public_identifier", "fixtures", ["public_identifier"])
    op.add_column("games", sa.Column("public_scorecard_identifier", sa.String(28), nullable=True))
    op.execute("UPDATE games SET public_scorecard_identifier = 'sc_' || substr(md5('cricksy-public-scorecard:' || id), 1, 24) WHERE public_scorecard_identifier IS NULL")
    op.alter_column("games", "public_scorecard_identifier", nullable=False)
    op.create_unique_constraint("uq_games_public_scorecard_identifier", "games", ["public_scorecard_identifier"])

def downgrade() -> None:
    op.execute("ALTER TABLE games DROP CONSTRAINT IF EXISTS uq_games_public_scorecard_identifier")
    op.execute("ALTER TABLE games DROP CONSTRAINT IF EXISTS games_public_scorecard_identifier_key")
    op.drop_column("games", "public_scorecard_identifier")
    op.execute("ALTER TABLE fixtures DROP CONSTRAINT IF EXISTS uq_fixtures_public_identifier")
    op.execute("ALTER TABLE fixtures DROP CONSTRAINT IF EXISTS fixtures_public_identifier_key")
    op.drop_column("fixtures", "public_identifier")

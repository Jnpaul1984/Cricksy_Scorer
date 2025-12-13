"""
Add security logging tables: request_logs, auth_events, rate_limit_events
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "k1f2g3h4i5j6_add_security_logging_tables"
down_revision = "j0e1f2g3h4i5_add_beta_user_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "request_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ts", sa.Integer, nullable=False, index=True),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.String(200), nullable=False),
        sa.Column("status", sa.Integer, nullable=False),
        sa.Column("ip", sa.String(64), nullable=True, index=True),
        sa.Column("userAgent", sa.String(200), nullable=True),
        sa.Column("userId", sa.String(64), nullable=True, index=True),
        sa.Column("latencyMs", sa.Integer, nullable=True),
    )
    op.create_table(
        "auth_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ts", sa.Integer, nullable=False, index=True),
        sa.Column("email", sa.String(128), nullable=True, index=True),
        sa.Column("userId", sa.String(64), nullable=True, index=True),
        sa.Column("ip", sa.String(64), nullable=True, index=True),
        sa.Column("userAgent", sa.String(200), nullable=True),
        sa.Column("eventType", sa.String(32), nullable=False),
        sa.Column("success", sa.Boolean, nullable=False),
    )
    op.create_table(
        "rate_limit_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ts", sa.Integer, nullable=False, index=True),
        sa.Column("ip", sa.String(64), nullable=True, index=True),
        sa.Column("userId", sa.String(64), nullable=True, index=True),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("limitName", sa.String(64), nullable=False),
    )


def downgrade():
    op.drop_table("rate_limit_events")
    op.drop_table("auth_events")
    op.drop_table("request_logs")

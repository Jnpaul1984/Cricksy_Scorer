"""
Add security logging tables: request_logs, auth_events, rate_limit_events
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "k1f2g3h4i5j6"
down_revision = "j0e1f2g3h4i5"
branch_labels = None
depends_on = None


def upgrade():
    # Create tables safely (if they already exist, do nothing)
    op.execute("""
    CREATE TABLE IF NOT EXISTS request_logs (
        id SERIAL PRIMARY KEY,
        ts INTEGER NOT NULL,
        method VARCHAR(10) NOT NULL,
        path VARCHAR(200) NOT NULL,
        status INTEGER NOT NULL,
        ip VARCHAR(64),
        "userAgent" VARCHAR(200),
        "userId" VARCHAR(64),
        "latencyMs" INTEGER
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS auth_events (
        id SERIAL PRIMARY KEY,
        ts INTEGER NOT NULL,
        event VARCHAR(64) NOT NULL,
        success BOOLEAN NOT NULL,
        ip VARCHAR(64),
        "userAgent" VARCHAR(200),
        "userId" VARCHAR(64),
        detail VARCHAR(500)
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS rate_limit_events (
        id SERIAL PRIMARY KEY,
        ts INTEGER NOT NULL,
        key VARCHAR(200) NOT NULL,
        limit_name VARCHAR(100),
        allowed BOOLEAN NOT NULL,
        ip VARCHAR(64),
        "userAgent" VARCHAR(200),
        "userId" VARCHAR(64)
    );
    """)


def downgrade():
    op.execute('DROP TABLE IF EXISTS rate_limit_events;')
    op.execute('DROP TABLE IF EXISTS auth_events;')
    op.execute('DROP TABLE IF EXISTS request_logs;')

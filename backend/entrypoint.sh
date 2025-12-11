#!/bin/sh
# Don't use set -e so we can handle errors gracefully

echo "=== Entrypoint starting ==="
echo "Working directory: $(pwd)"
echo "Contents of /app:"
ls -la /app
echo ""

echo "Python version:"
python --version
echo "Python path:"
which python
echo ""

echo "DATABASE_URL set: $(if [ -n "$DATABASE_URL" ]; then echo 'yes (redacted)'; else echo 'NO - MISSING!'; fi)"
echo ""

export PYTHONPATH=/app
echo "PYTHONPATH set to: $PYTHONPATH"

# Extract database name from DATABASE_URL and create it if it doesn't exist
# DATABASE_URL format: postgresql+asyncpg://user:pass@host:port/dbname
echo "=== Checking/Creating database ==="
python << 'PYEOF'
import os
import sys
from urllib.parse import urlparse

db_url = os.getenv("DATABASE_URL", "")
if not db_url:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

# Parse the URL
parsed = urlparse(db_url)
db_name = parsed.path.lstrip("/")
host = parsed.hostname
port = parsed.port or 5432
user = parsed.username
password = parsed.password

print(f"Target database: {db_name}")
print(f"Host: {host}:{port}")

# Connect to 'postgres' database to create our target database
import asyncio
try:
    import asyncpg
except ImportError:
    print("asyncpg not installed, skipping database creation check")
    sys.exit(0)

async def ensure_database():
    try:
        # Connect to default postgres database
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database="postgres"
        )

        # Check if database exists
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            db_name
        )

        if not exists:
            print(f"Database '{db_name}' does not exist. Creating...")
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Database '{db_name}' created successfully!")
        else:
            print(f"Database '{db_name}' already exists.")

        await conn.close()
    except Exception as e:
        print(f"Error checking/creating database: {e}")
        # Don't fail - let the app try to start anyway
        sys.exit(0)

asyncio.run(ensure_database())
PYEOF

echo "=== Running Alembic migrations ==="
cd /app
if python -m alembic -c backend/alembic.ini upgrade head; then
    echo "Migrations completed successfully"
else
    echo "ERROR: Alembic migration failed with exit code $?"
    echo "Continuing anyway to allow the server to start for debugging..."
fi

echo "=== Starting FastAPI server ==="
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000

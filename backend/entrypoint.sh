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

echo "DATABASE_URL set: $(if [ -n \"$DATABASE_URL\" ]; then echo 'yes (redacted)'; else echo 'NO - MISSING!'; fi)"
echo ""

export PYTHONPATH=/app
echo "PYTHONPATH set to: $PYTHONPATH"

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

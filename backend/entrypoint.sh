#!/bin/sh
set -eu

echo "=== Entrypoint starting ==="
echo "Python: $(python --version)"
echo "Working dir: $(pwd)"
echo "PYTHONPATH=/app"
export PYTHONPATH=/app

# Print presence only (don’t leak)
if [ -n "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL set: yes (redacted)"
else
  echo "DATABASE_URL set: NO - MISSING!"
fi

# Mode flags
RUN_MIGRATIONS="${RUN_MIGRATIONS:-false}"
MIGRATE_ONLY="${MIGRATE_ONLY:-false}"

echo "RUN_MIGRATIONS: $RUN_MIGRATIONS"
echo "MIGRATE_ONLY: $MIGRATE_ONLY"
echo ""

run_migrations() {
  echo "=== Running Alembic migrations ==="
  cd /app
  python -m alembic -c backend/alembic.ini upgrade head
  echo "Migrations completed successfully"
}

# One-off migration mode (ECS run-task should use this)
if [ "$MIGRATE_ONLY" = "true" ]; then
  run_migrations
  echo "Exiting (MIGRATE_ONLY=true)."
  exit 0
fi

# Optional: allow web task to run migrations (you should keep this false in ECS service)
if [ "$RUN_MIGRATIONS" = "true" ]; then
  run_migrations
fi

echo "=== Starting API ==="
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000

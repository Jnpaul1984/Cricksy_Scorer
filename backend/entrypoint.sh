#!/bin/sh
set -e

echo "Running Alembic migrations..."
cd /app
alembic -c backend/alembic.ini upgrade head

echo "Starting FastAPI server..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000

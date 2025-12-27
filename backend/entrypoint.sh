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

# --- MediaPipe model bootstrap (S3 -> local) ---
MEDIAPIPE_MODEL_S3_URI="${MEDIAPIPE_MODEL_S3_URI:-}"
MEDIAPIPE_MODEL_LOCAL_PATH="${MEDIAPIPE_MODEL_LOCAL_PATH:-/app/mediapipe_models/pose_landmarker_full.task}"

if [ -n "$MEDIAPIPE_MODEL_LOCAL_PATH" ]; then
  mkdir -p "$(dirname "$MEDIAPIPE_MODEL_LOCAL_PATH")"
fi

if [ -f "$MEDIAPIPE_MODEL_LOCAL_PATH" ]; then
  echo "MediaPipe model already present at: $MEDIAPIPE_MODEL_LOCAL_PATH"
else
  if [ -z "$MEDIAPIPE_MODEL_S3_URI" ]; then
    echo "MediaPipe model missing and MEDIAPIPE_MODEL_S3_URI not set. Coach Pro Plus video analysis disabled."
  else
    echo "MediaPipe model missing. Attempting download from: $MEDIAPIPE_MODEL_S3_URI"
    python - <<'PY'
import os, sys
import boto3

s3_uri = os.environ.get("MEDIAPIPE_MODEL_S3_URI")
dst = os.environ.get("MEDIAPIPE_MODEL_LOCAL_PATH", "/app/mediapipe_models/pose_landmarker_full.task")

if not s3_uri or not s3_uri.startswith("s3://"):
    print("Invalid MEDIAPIPE_MODEL_S3_URI:", s3_uri)
    sys.exit(1)

# Parse s3://bucket/key
without = s3_uri[len("s3://"):]
bucket, _, key = without.partition("/")
if not bucket or not key:
    print("Invalid S3 URI (missing bucket/key):", s3_uri)
    sys.exit(1)

s3 = boto3.client("s3")
try:
    s3.download_file(bucket, key, dst)
    size = os.path.getsize(dst)
    print(f"Downloaded MediaPipe model to {dst} ({size} bytes)")
except Exception as e:
    print("Failed to download MediaPipe model:", repr(e))
    sys.exit(1)
PY
  fi
fi
# --- end MediaPipe bootstrap ---

echo "=== Starting API ==="

# If a command was provided (e.g., worker), run it instead of the API.
# This allows the same image to be used for both the web API and background workers.
if [ "$#" -gt 0 ]; then
  echo "=== Running command === $*"
  exec "$@"
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port 8000

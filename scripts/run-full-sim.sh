#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export CRICKSY_IN_MEMORY_DB=1
export PYTHONPATH="$ROOT/backend:${PYTHONPATH:-}"

echo "==> Running backend test suite (unit tests only)"
(
  cd "$ROOT/backend"
  pytest -q tests/test_health.py tests/test_results_endpoint.py tests/test_simulated_t20_match.py
)

echo "==> Starting backend API (in-memory mode)"
if [ ! -f "$ROOT/backend/main.py" ]; then
  echo "Error: $ROOT/backend/main.py not found. Cannot start backend API."
  exit 1
fi
UVICORN_LOG="warning"
# Set PYTHONPATH to include backend directory for module imports
export PYTHONPATH="$ROOT/backend:${PYTHONPATH:-}"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level "${UVICORN_LOG}" &
BACKEND_PID=$!

cleanup() {
  if ps -p "${BACKEND_PID}" >/dev/null 2>&1; then
    kill "${BACKEND_PID}" >/dev/null 2>&1 || true
    wait "${BACKEND_PID}" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

"$ROOT/scripts/wait_for_http.sh" "http://127.0.0.1:8000/health" 40

echo "==> Running frontend E2E suite"
(
  cd "$ROOT/frontend"
  API_BASE="http://localhost:8000" VITE_API_BASE="http://localhost:8000" npm run test:e2e
)

echo "==> CI match simulation completed successfully."

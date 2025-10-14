#!/usr/bin/env bash
set -euo pipefail
URL="${1:-http://localhost:8000/health}"
TIMEOUT="${2:-180}"

while [ "$TIMEOUT" -gt 0 ]; do
  if curl -fsS "$URL" >/dev/null 2>&1; then
    echo "Healthy: $URL"
    exit 0
  fi
  sleep 2
  TIMEOUT=$((TIMEOUT-2))
done

echo "Service not healthy: $URL"
exit 1

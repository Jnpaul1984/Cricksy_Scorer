#!/usr/bin/env bash
set -euo pipefail

# Wait for a URL to become available
wait_for_url() {
  local url="$1"
  local timeout="${2:-30}"
  local elapsed=0
  
  while [ $elapsed -lt $timeout ]; do
    if curl -sf "$url" -m 2 >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.3
    elapsed=$((elapsed + 1))
  done
  return 1
}

# Set API base URL from environment or use default
API_BASE="${API_BASE:-http://localhost:8000}"
export API_BASE
export VITE_API_BASE="${VITE_API_BASE:-$API_BASE}"

echo "Using API base: $API_BASE"

# Build the app
echo "Building app..."
npm run build

# Start preview server in background
echo "Starting preview on port 3000..."
npm run preview -- --port 3000 &
PREVIEW_PID=$!

# Cleanup function
cleanup() {
  if [ -n "${PREVIEW_PID:-}" ] && ps -p "$PREVIEW_PID" >/dev/null 2>&1; then
    echo "Stopping preview server..."
    kill "$PREVIEW_PID" 2>/dev/null || true
    wait "$PREVIEW_PID" 2>/dev/null || true
  fi
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Wait for preview server to be ready
if ! wait_for_url "http://localhost:3000" 40; then
  echo "ERROR: Preview server did not start in time."
  exit 1
fi

# Check if Cypress is installed
if ! npx cypress verify >/dev/null 2>&1; then
  echo "WARNING: Cypress binary is not installed."
  echo "To install Cypress, run: npx cypress install"
  echo "Or ensure Cypress can download from: https://download.cypress.io"
  echo ""
  echo "Note: In environments with network restrictions, you may need to:"
  echo "  1. Download Cypress manually from https://github.com/cypress-io/cypress/releases"
  echo "  2. Set CYPRESS_INSTALL_BINARY=/path/to/cypress.zip before npm install"
  echo "  3. Or use CYPRESS_CACHE_FOLDER to specify a pre-installed location"
  echo ""
  echo "Skipping E2E tests due to missing Cypress installation."
  exit 0
fi

# Run Cypress E2E tests
echo "Running Cypress E2E tests..."
npx cypress run

echo "E2E tests completed successfully."

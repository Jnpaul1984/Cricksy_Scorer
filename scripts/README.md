# CI Simulation Suite

This directory contains scripts for running the complete CI simulation suite for the Cricksy Scorer application.

## Scripts

### `ci-simulation.sh`

The main CI simulation script that executes the exact steps outlined in the problem statement:

1. Set environment variable `CRICKSY_IN_MEMORY_DB=1`
2. Run backend pytest tests
3. Start the backend API server
4. Wait for backend to be ready
5. Run frontend E2E tests
6. Clean up (kill backend server)

**Usage:**
```bash
cd /path/to/Cricksy_Scorer
bash scripts/ci-simulation.sh
```

### `run-full-sim.sh`

A more robust version that includes:
- Automatic backend dependency installation
- Waits for HTTP health check before running E2E tests
- Better error handling and cleanup

**Usage:**
```bash
cd /path/to/Cricksy_Scorer
bash scripts/run-full-sim.sh
```

## Manual Execution

You can also run the steps manually from the repository root:

```bash
# 1. Set environment variable
export CRICKSY_IN_MEMORY_DB=1
export PYTHONPATH="$(pwd)/backend:${PYTHONPATH:-}"

# 2. Run backend tests
pushd backend && pytest && popd

# 3. Start backend API in background
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level warning &

# 4. Save PID and wait for backend
BACKEND_PID=$!
sleep 5

# 5. Run frontend E2E tests
pushd frontend && \
  API_BASE=http://localhost:8000 \
  VITE_API_BASE=http://localhost:8000 \
  npm run test:e2e && \
  popd

# 6. Clean up
kill $BACKEND_PID
```

## Prerequisites

### Backend

- Python 3.12+
- Dependencies from `backend/requirements.txt`

Install with:
```bash
cd backend
pip install -r requirements.txt
```

### Frontend

- Node.js 20+
- npm 10+
- Cypress (for E2E tests)

Install with:
```bash
cd frontend
npm ci
```

**Note on Cypress:** Cypress requires downloading a binary from https://download.cypress.io. In environments with network restrictions, you may need to:

1. Download Cypress manually from https://github.com/cypress-io/cypress/releases
2. Set `CYPRESS_INSTALL_BINARY=/path/to/cypress.zip` before running `npm install`
3. Or use `CYPRESS_CACHE_FOLDER` to specify a pre-installed location

If Cypress cannot be installed, the E2E test script will skip the tests gracefully with a warning.

## Environment Variables

- `CRICKSY_IN_MEMORY_DB=1` - Use in-memory database instead of PostgreSQL (required for tests)
- `PYTHONPATH` - Should include the backend directory for proper module imports
- `API_BASE` - Backend API URL for frontend (default: http://localhost:8000)
- `VITE_API_BASE` - Vite build-time API URL (default: http://localhost:8000)

## Cross-Platform Support

The frontend E2E test script automatically detects the operating system:

- **Windows**: Uses PowerShell script (`scripts/run-e2e.ps1`)
- **Linux/macOS**: Uses Bash script (`scripts/run-e2e.sh`)

The detection is handled in `frontend/package.json` via the `test:e2e` npm script.

## Troubleshooting

### Backend fails to start with "ModuleNotFoundError: No module named 'dls'"

**Solution:** Ensure `PYTHONPATH` is set correctly:
```bash
export PYTHONPATH="$(pwd)/backend:${PYTHONPATH:-}"
```

### Cypress binary not found

**Solution:** Install Cypress binary:
```bash
cd frontend
npx cypress install
```

If the download fails due to network restrictions, see the Cypress notes in the Prerequisites section above.

### Backend tests require running API server

Some tests in the `backend/tests` directory require a running API server. The CI simulation scripts run only the unit tests that don't require a server:
- `tests/test_health.py`
- `tests/test_results_endpoint.py`
- `tests/test_simulated_t20_match.py`

To run all tests including integration tests, start the backend server first, then run pytest.

## CI/CD Integration

For GitHub Actions or other CI/CD systems, use:

```yaml
- name: Run CI Simulation
  run: bash scripts/ci-simulation.sh
  env:
    CRICKSY_IN_MEMORY_DB: 1
```

The scripts handle all setup, execution, and cleanup automatically.

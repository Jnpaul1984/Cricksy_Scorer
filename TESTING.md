# Testing Guide - Cricksy Scorer

This document provides comprehensive instructions for running tests in the Cricksy Scorer project.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Backend Tests](#backend-tests)
- [Frontend Tests](#frontend-tests)
- [End-to-End Tests](#end-to-end-tests)
- [Test Organization](#test-organization)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Backend Requirements

- **Python:** 3.11+
- **pip:** Latest version
- **Dependencies:** Install from `backend/requirements.txt`

```bash
cd backend
pip install -r requirements.txt
```

### Frontend Requirements

- **Node.js:** 18+ (22.13.0 recommended)
- **npm/pnpm:** Latest version
- **Dependencies:** Install from `frontend/package.json`

```bash
cd frontend
npm install
# or
pnpm install
```

---

## Environment Setup

### Required Environment Variables

#### PYTHONPATH (Critical for Backend Tests)

The backend uses absolute imports with the `backend.` prefix. You **must** set `PYTHONPATH` to include the repository root:

```bash
export PYTHONPATH=/path/to/Cricksy_Scorer:$PYTHONPATH
```

**Example:**
```bash
# If your repo is at /home/user/Cricksy_Scorer
export PYTHONPATH=/home/user/Cricksy_Scorer:$PYTHONPATH
```

**Why is this needed?**
- Backend modules use imports like `from backend.sql_app import models`
- Without PYTHONPATH, Python cannot resolve these imports
- This is required for both running tests and starting the server

**Permanent Setup (Optional):**

Add to your `~/.bashrc` or `~/.zshrc`:
```bash
export PYTHONPATH="/path/to/Cricksy_Scorer:$PYTHONPATH"
```

#### CRICKSY_IN_MEMORY_DB (For Testing)

Enables in-memory database mode (no PostgreSQL required):

```bash
export CRICKSY_IN_MEMORY_DB=1
```

**When to use:**
- Running unit tests
- Running integration tests locally
- CI/CD pipelines
- Quick development testing

**When NOT to use:**
- Production environments
- Testing database migrations
- Testing PostgreSQL-specific features

#### API_BASE and VITE_API_BASE (For Frontend Tests)

Specify the backend API URL for frontend tests:

```bash
export API_BASE=http://localhost:8000
export VITE_API_BASE=http://localhost:8000
```

---

## Backend Tests

### Test Organization

Backend tests are organized into different categories:

```
backend/tests/
├── unit/                    # Unit tests (fast, no external dependencies)
├── integration/             # Integration tests (require running services)
├── smoke/                   # Smoke tests (basic functionality checks)
├── contract/                # API contract tests
├── ci_match/                # Full match simulation tests
└── ci_smoke/                # CI smoke tests
```

### Running All Backend Tests

```bash
cd backend
export PYTHONPATH=/path/to/Cricksy_Scorer:$PYTHONPATH
export CRICKSY_IN_MEMORY_DB=1
pytest
```

### Running Specific Test Categories

**Unit Tests Only:**
```bash
pytest tests/unit/
```

**Integration Tests Only:**
```bash
# Requires backend server running
pytest tests/integration/
```

**Smoke Tests:**
```bash
pytest tests/smoke/
pytest tests/ci_smoke/
```

**Contract Tests:**
```bash
pytest tests/contract/
```

**Full Match Simulation:**
```bash
pytest tests/ci_match/
```

### Running Specific Test Files

```bash
pytest tests/test_health.py
pytest tests/smoke/test_smoke_create_and_one_ball.py -v
```

### Running with Coverage

```bash
pytest --cov=backend --cov-report=html
# Open htmlcov/index.html to view coverage report
```

### Common Test Failures and Solutions

**ImportError: No module named 'backend'**
- **Solution:** Set PYTHONPATH (see Environment Setup above)

**Connection Refused Errors**
- **Cause:** Tests requiring API server, but server not running
- **Solution:** These are expected for integration tests when run standalone
- **Recommendation:** Separate unit tests from integration tests (see Test Organization section)

**Database Errors**
- **Solution:** Ensure `CRICKSY_IN_MEMORY_DB=1` is set

---

## Frontend Tests

### Test Types

The frontend includes several types of tests:

1. **Unit Tests** (Vitest) - Component and utility testing
2. **E2E Tests** (Cypress) - Full application flow testing

### Running Unit Tests

```bash
cd frontend
npm run test:unit
# or
npm run test:unit:watch  # Watch mode
```

### Type Checking

```bash
npm run type-check
```

### Linting

```bash
npm run lint
npm run format  # Auto-fix formatting issues
```

---

## End-to-End Tests

### Prerequisites for E2E Tests

1. **Backend server running** on port 8000
2. **Frontend preview server** running on port 3000
3. **Environment variables** set

### Full E2E Test Suite

#### Automated Script (Recommended)

```bash
# From repository root
./scripts/run-full-sim.sh
```

#### Manual Execution

**Step 1: Set Environment Variables**
```bash
export CRICKSY_IN_MEMORY_DB=1
export PYTHONPATH=/path/to/Cricksy_Scorer:$PYTHONPATH
export API_BASE=http://localhost:8000
export VITE_API_BASE=http://localhost:8000
```

**Step 2: Run Backend Tests**
```bash
cd backend
pytest
```

**Step 3: Start Backend Server**
```bash
# In a new terminal
cd backend
export CRICKSY_IN_MEMORY_DB=1
export PYTHONPATH=/path/to/Cricksy_Scorer:$PYTHONPATH
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level warning
```

**Step 4: Build Frontend**
```bash
# In another terminal
cd frontend
export API_BASE=http://localhost:8000
export VITE_API_BASE=http://localhost:8000
npm run build
```

**Step 5: Start Preview Server**
```bash
npm run preview -- --port 3000
```

**Step 6: Run Cypress Tests**
```bash
# In another terminal
cd frontend
npx cypress run
# or for interactive mode:
npx cypress open
```

**Step 7: Cleanup**
```bash
# Kill backend and preview servers
pkill -f "uvicorn backend.main:app"
pkill -f "vite preview"
```

### E2E Test Configuration

Cypress configuration is in `frontend/cypress.config.js` (JavaScript ES module).

**Key settings:**
- Base URL: `http://localhost:3000`
- API Base: `http://localhost:8000` (configurable via env)
- Support files: `cypress/support/`
- Test specs: `cypress/e2e/**/*.cy.{js,ts,jsx,tsx}`

### E2E Test Specs

```
frontend/cypress/e2e/
├── ci_match_simulator.cy.ts    # Full match simulation test
└── simulated_t20_match.cy.ts   # T20 match replay test
```

---

## Test Organization

### Current Structure

Currently, backend tests are mixed together, which can cause issues:

- **Unit tests** don't require external services
- **Integration tests** require backend server running
- **E2E tests** require both backend and frontend running

### Recommended Separation

#### Backend Test Reorganization

**Create separate test suites:**

```
backend/tests/
├── unit/                        # Fast, isolated tests
│   ├── test_models.py
│   ├── test_schemas.py
│   └── test_utils.py
├── integration/                 # Tests requiring services
│   ├── test_api_endpoints.py
│   ├── test_database.py
│   └── test_websockets.py
└── e2e/                        # Full system tests
    └── test_full_match_flow.py
```

**Update pytest.ini:**

```ini
[pytest]
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (require services)
    e2e: End-to-end tests (require full system)
    slow: Slow-running tests
```

**Mark tests appropriately:**

```python
import pytest

@pytest.mark.unit
def test_player_model():
    # Fast unit test
    pass

@pytest.mark.integration
def test_create_game_api():
    # Requires backend server
    pass

@pytest.mark.e2e
def test_full_match_simulation():
    # Requires backend + frontend
    pass
```

**Run specific test types:**

```bash
# Run only unit tests (fast)
pytest -m unit

# Run integration tests
pytest -m integration

# Run everything except slow tests
pytest -m "not slow"

# Run unit and integration tests
pytest -m "unit or integration"
```

#### Frontend Test Reorganization

**Separate Vitest and Cypress:**

```
frontend/
├── tests/                      # Vitest unit tests
│   └── unit/
│       ├── components/
│       └── utils/
└── cypress/
    ├── e2e/                   # E2E test specs
    ├── fixtures/              # Test data
    └── support/               # Helper functions
```

**Update package.json scripts:**

```json
{
  "scripts": {
    "test:unit": "vitest",
    "test:unit:watch": "vitest --watch",
    "test:e2e": "cypress run",
    "test:e2e:open": "cypress open",
    "test:all": "npm run test:unit && npm run test:e2e"
  }
}
```

### Benefits of Separation

1. **Faster feedback** - Run unit tests quickly during development
2. **Clear dependencies** - Know which tests require which services
3. **Better CI/CD** - Run unit tests in parallel, integration tests sequentially
4. **Easier debugging** - Isolate failures to specific layers
5. **Better documentation** - Test organization reflects system architecture

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: CI Tests

on: [push, pull_request]

jobs:
  backend-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run unit tests
        run: |
          cd backend
          export PYTHONPATH=$GITHUB_WORKSPACE:$PYTHONPATH
          export CRICKSY_IN_MEMORY_DB=1
          pytest -m unit

  backend-integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Start backend server
        run: |
          cd backend
          export PYTHONPATH=$GITHUB_WORKSPACE:$PYTHONPATH
          export CRICKSY_IN_MEMORY_DB=1
          python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
          sleep 5
      - name: Run integration tests
        run: |
          cd backend
          export PYTHONPATH=$GITHUB_WORKSPACE:$PYTHONPATH
          export CRICKSY_IN_MEMORY_DB=1
          pytest -m integration

  frontend-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run unit tests
        run: |
          cd frontend
          npm run test:unit

  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd backend && pip install -r requirements.txt
          cd ../frontend && npm ci
      - name: Start backend
        run: |
          cd backend
          export PYTHONPATH=$GITHUB_WORKSPACE:$PYTHONPATH
          export CRICKSY_IN_MEMORY_DB=1
          python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
          sleep 5
      - name: Build and start frontend
        run: |
          cd frontend
          export API_BASE=http://localhost:8000
          export VITE_API_BASE=http://localhost:8000
          npm run build
          npm run preview -- --port 3000 &
          sleep 5
      - name: Run E2E tests
        run: |
          cd frontend
          npx cypress run
```

---

## Troubleshooting

### Common Issues

#### 1. ModuleNotFoundError: No module named 'backend'

**Error:**
```
ImportError: No module named 'backend.sql_app'
```

**Solution:**
```bash
export PYTHONPATH=/path/to/Cricksy_Scorer:$PYTHONPATH
```

#### 2. Connection Refused (Backend Tests)

**Error:**
```
httpx.ConnectError: [Errno 111] Connection refused
```

**Cause:** Integration tests trying to connect to backend server that isn't running

**Solutions:**
- Run only unit tests: `pytest -m unit`
- Start backend server before running integration tests
- Use test markers to separate test types

#### 3. Cypress Configuration Error

**Error:**
```
Your configFile is invalid: cypress.config.ts
```

**Solution:**
- Ensure using `cypress.config.js` (JavaScript ES module)
- Check that `cypress/support/matchSimulator.js` exists
- Verify `"type": "module"` in package.json

#### 4. Preview Server Timeout

**Error:**
```
cy.visit() failed trying to load: http://localhost:3000
```

**Solutions:**
- Ensure preview server is running: `npm run preview`
- Check port 3000 is not in use: `lsof -i :3000`
- Increase Cypress timeout in config
- Use `vite dev` instead of `vite preview` for faster startup

#### 5. TypeScript Type Check Failures

**Error:**
```
File 'cypress/support/matchSimulator.ts' is not listed within the file list
```

**Solution:**
- Update `tsconfig.node.json` to include `"cypress/support/**/*.ts"`
- Or use JavaScript versions of Cypress files

---

## Quick Reference

### Environment Variables Cheat Sheet

```bash
# Required for backend tests and server
export PYTHONPATH=/path/to/Cricksy_Scorer:$PYTHONPATH
export CRICKSY_IN_MEMORY_DB=1

# Required for frontend E2E tests
export API_BASE=http://localhost:8000
export VITE_API_BASE=http://localhost:8000
```

### Common Commands

```bash
# Backend unit tests (fast)
cd backend && pytest -m unit

# Backend all tests
cd backend && pytest

# Frontend unit tests
cd frontend && npm run test:unit

# Frontend E2E tests (requires servers running)
cd frontend && npx cypress run

# Type checking
cd frontend && npm run type-check

# Linting
cd frontend && npm run lint
```

### Port Usage

- **8000** - Backend API server
- **3000** - Frontend preview/dev server
- **5432** - PostgreSQL (if not using in-memory DB)

---

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Cypress Documentation](https://docs.cypress.io/)
- [Vitest Documentation](https://vitest.dev/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

---

## Contributing

When adding new tests:

1. **Mark tests appropriately** with `@pytest.mark.unit`, `@pytest.mark.integration`, etc.
2. **Document dependencies** - What services must be running?
3. **Keep tests isolated** - Don't rely on test execution order
4. **Use fixtures** - Share setup code via pytest fixtures
5. **Test edge cases** - Not just happy paths
6. **Update this document** - If you add new test requirements

---

**Last Updated:** October 20, 2025
**Cypress Version:** 13.17.0
**Python Version:** 3.11+
**Node Version:** 22.13.0


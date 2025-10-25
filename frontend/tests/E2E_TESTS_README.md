# E2E Tests Documentation

This document describes the end-to-end (E2E) tests for the Cricksy Scorer frontend using Cypress.

## Overview

- **Framework**: Cypress 13.15.2
- **Test Count**: 2 tests
- **Location**: `cypress/e2e/`

## Test Files

### 1. `ci_match_simulator.cy.ts`

**Purpose**: Comprehensive test of the scoreboard, scoring, and analytics views for a seeded match.

**Test Flow**:
1. Seeds a complete T20 match using the `seed:match` Cypress task
2. Visits the scoreboard view and verifies:
   - Result banner shows "Team Alpha won by 15 runs"
   - First innings score shows "157/6 in 20 ov"
   - Batting and bowling tables are populated
   - Target information is displayed
   - Bowler figures are shown
   - Ball-by-ball display has at least 6 balls
3. Visits the scoring view and verifies:
   - Delivery table has over 100 rows
   - Extras card shows wides and leg-byes
   - DLS card is present
   - Batting and bowling scorecards are visible
4. Visits the analytics view and verifies:
   - Can search for and select the match
   - Run rate chart is displayed
   - Manhattan and Worm charts are rendered
   - Extras/Dot/Boundary statistics are shown
   - Batting and bowling tables are populated
   - DLS panel is present
   - Phase splits show powerplay information

**Dependencies**:
- Backend API running on `http://localhost:8000`
- Frontend app running on `http://localhost:3000`
- `matchSimulator.js` helper for seeding match data

### 2. `simulated_t20_match.cy.ts`

**Purpose**: Test using a simulated T20 match fixture.

**Test Flow**:
- Uses `simulated_t20_match.json` fixture
- Tests basic match simulation functionality

## Running E2E Tests

### Prerequisites

1. **Start the backend server**:
   ```bash
   cd backend
   CRICKSY_IN_MEMORY_DB=1 uvicorn main:_fastapi --host 0.0.0.0 --port 8000
   ```

2. **Start the frontend dev server**:
   ```bash
   cd frontend
   npm run dev
   ```

3. **Run the E2E tests**:
   ```bash
   cd frontend
   npx cypress run
   ```

   Or open Cypress in interactive mode:
   ```bash
   npx cypress open
   ```

### Environment Variables

- `API_BASE`: Backend API URL (default: `http://localhost:8000`)
- `baseUrl`: Frontend URL (default: `http://localhost:3000`)

## CI/CD Integration

To run E2E tests in GitHub Actions, add the following job to `.github/workflows/ci.yml`:

\`\`\`yaml
frontend-e2e-tests:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-node@v3
      with:
        node-version: '20'
    - uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install backend dependencies
      run: cd backend && pip install -r requirements.txt

    - name: Start backend server
      run: |
        cd backend
        CRICKSY_IN_MEMORY_DB=1 uvicorn main:_fastapi --host 0.0.0.0 --port 8000 &
        sleep 5

    - name: Install frontend dependencies
      run: cd frontend && npm ci

    - name: Build frontend
      run: cd frontend && npm run build

    - name: Start frontend server
      run: |
        cd frontend
        npm run preview -- --port 3000 &
        sleep 5

    - name: Run Cypress tests
      run: cd frontend && npx cypress run
\`\`\`

## Test Expansion Recommendations

### Additional E2E Scenarios to Add

1. **Complete Match Flow**
   - Create a new game
   - Set openers
   - Post deliveries for a full match
   - Verify final result

2. **DLS Rain Interruption**
   - Start a match
   - Simulate rain interruption
   - Verify revised target calculation

3. **Multi-Day Match**
   - Create a Test match
   - Play multiple innings
   - Verify state persistence across days

4. **Error Handling**
   - Test invalid API responses
   - Test network failures
   - Test user input validation

5. **Live Updates**
   - Test WebSocket live scoring
   - Verify real-time score updates
   - Test multiple concurrent viewers

## Known Issues

- E2E tests use PowerShell scripts (`run-e2e.ps1`) which are Windows-specific
- Need cross-platform alternatives for Linux/macOS
- Tests require manual server startup (not automated)

## Future Improvements

- Add visual regression testing with Cypress plugins
- Implement test data factories for easier test setup
- Add performance testing with Cypress
- Create reusable Cypress commands for common operations

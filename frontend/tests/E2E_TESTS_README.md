# E2E Tests Documentation

This document describes the end-to-end (E2E) tests for the Cricksy Scorer frontend using Cypress.

## Overview

- **Framework**: Cypress 15.x
- **Primary CI gate**: `npm run test:e2e`
- **Location**: `cypress/e2e/`
- **Coverage Matrix**: `frontend/tests/E2E_COVERAGE_MATRIX.md`

## Test Files

### CI-safe specs (use intercepts only — no live backend required)

#### 1. `analyst_workspace_data_library.cy.ts`

**Purpose**: Browser-level validation gate for the Analyst Workspace Data Library from Phase 5O.

**Test Flow**:
1. Loads `/analyst/workspace`
2. Opens the **Data Library** tab
3. Verifies controlled historical/imported rows render
4. Verifies search, source filter, format filter, and sort behavior
5. Verifies opening a match triggers the analyst detail flow
6. Verifies empty and error states

**Data strategy**:
- Uses Cypress intercepts only inside the test file
- Uses contract-shaped responses for `/auth/me`, `/analytics/matches`, `/analytics/matches/:id/case-study`, and `/analytics/matches/:id/registry`
- Does **not** add fake data to production runtime code paths

#### 2. `coach_workspace_smoke.cy.ts`

**Purpose**: Smoke gate for the Coaches Dashboard (`/coaches`).

**Test Flow**:
1. Loads `/coaches` with stubbed auth
2. Verifies "Coaches Dashboard" heading and subtitle
3. Verifies "No active match" empty state renders correctly
4. Verifies header action buttons (Open Scoring Console, Analyst Workspace)
5. Verifies Season Overview, Coach Notes, and Quick Links sections
6. Verifies navigation from "Open Scoring Console" goes to `/setup` when no game is active
7. Verifies Save Note button is disabled when the textarea is empty
8. Verifies unauthenticated users are redirected to `/login`

**Data strategy**:
- Uses Cypress intercepts only (stubs `/auth/me`)
- No live backend required

### Specs requiring a live backend

These specs use `cy.task('seed:match')` or similar to seed real backend state. They should be run in a full-stack environment only.

#### 3. `match_creation_flow.cy.ts`

**Purpose**: Covers the full match setup → XI selection → scoring console flow.

#### 4. `scoring_gate_smoke.cy.ts`

**Purpose**: Validates the scoring console state (read-only when game is over, delivery submission when live).

#### 5. `ci_match_simulator.cy.ts`

**Purpose**: Full smoke across viewer, scoring, and analytics views for a seeded completed match.

#### 6. `next_over_flow.cy.ts`, `wicket_new_batter_flow.cy.ts`, `innings_flip_flow.cy.ts`, `weather_interruption_flow.cy.ts`

**Purpose**: Targeted scoring-console gate checks for specific game-state transitions.

#### 7. `simulated_t20_match.cy.ts`

**Purpose**: Replay-style test using a simulated T20 match fixture.

---

## Running E2E Tests

### Install dependencies

```bash
cd frontend
npm ci
```

If you are in a restricted environment where `download.cypress.io` is blocked during `npm ci`, use:

```bash
cd frontend
CYPRESS_INSTALL_BINARY=0 npm ci
```

The `npm run test:e2e` command installs the Cypress binary explicitly before running the gate.

### Run the default CI gate (Analyst Workspace)

```bash
cd frontend
npm run test:e2e
```

This command:
- installs the Cypress binary if needed
- builds the frontend
- starts `vite preview` on port 3000
- runs `cypress/e2e/analyst_workspace_data_library.cy.ts`

### Run targeted suite gates

Each suite can be run independently:

```bash
# Analyst Workspace only
npm run test:e2e:analyst

# Coach Dashboard only
npm run test:e2e:coach

# Both CI-safe smoke suites (analyst + coach)
npm run test:e2e:smoke

# Scoring flows (requires live seeded backend)
npm run test:e2e:scoring
```

The `run-e2e.mjs` script also supports `--suite` directly:

```bash
node ./scripts/run-e2e.mjs --suite analyst
node ./scripts/run-e2e.mjs --suite coach
node ./scripts/run-e2e.mjs --suite smoke
```

### Optional: run all Cypress specs directly

```bash
cd frontend
npx cypress run --config-file cypress.config.mjs
```

---

## Environment Variables

- `API_BASE`: Backend API URL passed through to Cypress/the preview build (default: `http://localhost:8000`)
- `baseUrl`: Frontend URL (default: `http://localhost:3000`)
- `CYPRESS_SPEC`: Override the spec file path (legacy; prefer `--suite` flag)

---

## CI/CD Integration

The main CI workflow includes:

- **`frontend-analyst-e2e`**: Runs `npm run test:e2e` (Analyst Workspace gate — intercepts only, no backend)
- **`frontend-coach-e2e`**: Runs `npm run test:e2e:coach` (Coach Dashboard gate — intercepts only, no backend)

Reliability details:
- CI installs frontend packages with `CYPRESS_INSTALL_BINARY=0 npm ci`
- the validation command then runs `npx cypress install` explicitly
- the Cypress binary cache is stored at `~/.cache/Cypress`

This keeps the binary install step explicit and avoids coupling `npm ci` success to the Cypress download step in restricted environments.

---

## Adding a New E2E Gate

When you add or significantly change a major frontend workspace, follow these steps:

1. Create (or update) `cypress/e2e/<workspace>_smoke.cy.ts` with intercept-only stubs.
2. Add a `test:e2e:<workspace>` script to `package.json`.
3. Add the suite entry to `SUITES` in `scripts/run-e2e.mjs`.
4. Update the coverage matrix in `frontend/tests/E2E_COVERAGE_MATRIX.md`.
5. Add a CI job to `.github/workflows/ci.yml` if the spec is CI-safe (intercepts only).

If E2E coverage is intentionally deferred, document the reason in the PR and reference a follow-up issue.

---

## Known Issues

- Some restricted sandboxes block `download.cypress.io`, so agents may need `CYPRESS_INSTALL_BINARY=0 npm ci` before running `npm run test:e2e`
- Scoring, viewer, and import specs require a live backend. See `E2E_COVERAGE_MATRIX.md` for the full status of each workspace.


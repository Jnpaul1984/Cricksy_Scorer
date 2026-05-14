# E2E Tests Documentation

This document describes the end-to-end (E2E) tests for the Cricksy Scorer frontend using Cypress.

## Overview

- **Framework**: Cypress 15.x
- **Primary CI gate**: `npm run test:e2e`
- **Location**: `cypress/e2e/`

## Test Files

### 1. `analyst_workspace_data_library.cy.ts`

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

### 2. `ci_match_simulator.cy.ts`

**Purpose**: Comprehensive test of the scoreboard, scoring, and analytics views for a seeded match.

### 3. `simulated_t20_match.cy.ts`

**Purpose**: Test using a simulated T20 match fixture.

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

### Run the Analyst Workspace validation gate

```bash
cd frontend
npm run test:e2e
```

This command:
- installs the Cypress binary if needed
- builds the frontend
- starts `vite preview` on port 3000
- runs `cypress/e2e/analyst_workspace_data_library.cy.ts`

### Optional: run all Cypress specs directly

```bash
cd frontend
npx cypress run --config-file cypress.config.mjs
```

## Environment Variables

- `API_BASE`: Backend API URL passed through to Cypress/the preview build (default: `http://localhost:8000`)
- `baseUrl`: Frontend URL (default: `http://localhost:3000`)

## CI/CD Integration

The main CI workflow includes a dedicated **Frontend (analyst workspace E2E)** job.

Reliability details:
- CI installs frontend packages with `CYPRESS_INSTALL_BINARY=0 npm ci`
- the validation command then runs `npx cypress install` explicitly
- the Cypress binary cache is stored at `~/.cache/Cypress`

This keeps the binary install step explicit and avoids coupling `npm ci` success to the Cypress download step in restricted environments.

## Known Issues

- Some restricted sandboxes block `download.cypress.io`, so agents may need `CYPRESS_INSTALL_BINARY=0 npm ci` before running `npm run test:e2e`

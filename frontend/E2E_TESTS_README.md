# End-to-End (E2E) Testing Guide

This document provides an overview of the End-to-End (E2E) tests for the Cricksy Scorer frontend application, powered by Cypress. It explains the purpose of each test file and the necessary steps to run them successfully.

## Overview

Our E2E tests are designed to simulate real user scenarios and verify the application's functionality from the user's perspective. We have two primary E2E test suites:

1.  `ci_match_simulator.cy.ts`: A comprehensive test that simulates a full match and verifies all major views of the application.
2.  `simulated_t20_match.cy.ts`: A focused test that verifies the display of a completed T20 match from a fixture file.

## Prerequisites

Before running the E2E tests, ensure you have the following installed and configured:

*   Node.js and pnpm
*   A running instance of the Cricksy Scorer backend API.

## Test Suites

### 1. CI Match Simulator (`ci_match_simulator.cy.ts`)

This test provides a full end-to-end journey through the application, verifying the scoreboard, scoring, and analytics views.

#### What it Tests:

*   **Match Seeding**: It starts by seeding a complete match into the database via a Cypress task that calls the backend API.
*   **Public Scoreboard (`/view/:gameId`)**: It verifies that the public scoreboard view correctly displays the match result, innings summaries, batting and bowling tables, and other key information.
*   **Detailed Scoring View (`/game/:gameId/scoring`)**: It checks the internal scoring view for detailed delivery-by-delivery data, extras, and scorecards.
*   **Analytics View (`/analytics`)**: It simulates a user searching for the match and verifies that the analytics dashboards (Run Rate, Manhattan, Worm, etc.) are rendered correctly.

#### How to Run:

1.  **Start the Backend Server**:

    The backend API must be running and accessible. By default, the tests expect the API to be at `http://localhost:8000`. You can start the backend server with the following command from the `backend` directory:

    ```bash
    CRICKSY_IN_MEMORY_DB=1 PYTHONPATH=. uvicorn main:app --host 0.0.0.0 --port 8000
    ```

2.  **Start the Frontend Development Server**:

    From the `frontend` directory, start the Vite development server:

    ```bash
    pnpm dev
    ```

3.  **Run the Cypress Test**:

    Once both servers are running, you can run the Cypress tests. You can do this in either headed or headless mode.

    *   **Headed Mode (for debugging):**

        ```bash
        pnpm cypress open --e2e --browser chrome
        ```

        Then, select `ci_match_simulator.cy.ts` from the list of tests.

    *   **Headless Mode (for CI or automated runs):**

        ```bash
        pnpm cypress run --e2e --spec "cypress/e2e/ci_match_simulator.cy.ts"
        ```

### 2. Simulated T20 Match (`simulated_t20_match.cy.ts`)

This test is a more lightweight E2E test that focuses on the rendering of a pre-canned match result. It uses a dedicated view (`/e2e`) to load a fixture file and display the result.

#### What it Tests:

*   **Fixture Loading**: It loads a JSON fixture (`simulated_t20_match.json`) containing the data for a completed T20 match.
*   **Component Rendering**: It verifies that the `E2EView` component correctly renders the winner and summary of the match based on the loaded fixture data.

#### How to Run:

1.  **Start the Frontend Development Server**:

    This test does *not* require the backend server to be running. You only need the frontend development server.

    ```bash
    pnpm dev
    ```

2.  **Run the Cypress Test**:

    *   **Headed Mode:**

        ```bash
        pnpm cypress open --e2e --browser chrome
        ```

        Then, select `simulated_t20_match.cy.ts` from the list of tests.

    *   **Headless Mode:**

        ```bash
        pnpm cypress run --e2e --spec "cypress/e2e/simulated_t20_match.cy.ts"
        ```

## Conclusion

These E2E tests provide a safety net to ensure that the core functionality of the Cricksy Scorer application remains intact. The `ci_match_simulator` is particularly important as it covers a wide range of features and user interactions. It is recommended to run these tests as part of your regular development and CI/CD pipeline.


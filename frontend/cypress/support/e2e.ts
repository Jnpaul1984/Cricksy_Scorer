// Cypress E2E Support File
// This file is processed and loaded automatically before test files

/// <reference types="cypress" />

// Import custom commands
import './commands'

beforeEach(() => {
  // Intercept API calls to the backend snapshot endpoint
  // Match both /games/{id}/snapshot and /games/{id} patterns for snapshot requests
  cy.intercept('GET', '**/games/*/snapshot').as('snapshot')
})

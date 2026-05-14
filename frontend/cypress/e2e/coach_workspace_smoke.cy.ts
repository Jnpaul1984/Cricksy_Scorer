// Coach Workspace smoke gate
//
// Validates that the Coaches Dashboard page loads correctly and renders its key
// structural elements without requiring a live backend.  All API calls are
// intercepted via cy.intercept() – no production data paths are touched.

const authMe = {
  id: 'cypress-user',
  email: 'cypress@example.com',
  name: 'Cypress Coach',
  role: 'org_pro',
  is_superuser: false,
}

function stubCoachWorkspace(role = 'org_pro') {
  cy.intercept('GET', '**/auth/me', { ...authMe, role }).as('authMe')
}

describe('Coach Workspace smoke gate', () => {
  beforeEach(() => {
    cy.viewport(1600, 1200)
  })

  it('loads the Coaches Dashboard and renders all structural sections', () => {
    stubCoachWorkspace()

    cy.visitWithAuth('/coaches')

    cy.contains('h1', 'Coaches Dashboard').should('be.visible')
    cy.contains('p', 'Quick view of team performance and current match state.').should('be.visible')

    // Header action buttons are present
    cy.contains('button', 'Open Scoring Console').should('be.visible')
    cy.contains('button', 'Analyst Workspace').should('be.visible')

    // No active match → shows the empty state
    cy.contains('h2', 'Current Match').should('be.visible')
    cy.contains('No active match.').should('be.visible')
    cy.contains('button', 'Go to Setup').should('be.visible')

    // Season Overview section
    cy.contains('h3', 'Season Overview').should('be.visible')

    // Coach Notes section
    cy.contains('h3', 'Coach Notes').should('be.visible')
    cy.get('textarea[placeholder*="Add notes"]').should('be.visible')
    cy.contains('button', 'Save Note').should('be.visible').and('be.disabled')

    // Quick Links section
    cy.contains('h3', 'Quick Links').should('be.visible')
    cy.contains('button', 'View Leaderboard').should('be.visible')
    cy.contains('button', 'Team Analytics').should('be.visible')
    cy.contains('button', 'Video Sessions (Plus)').should('be.visible')
  })

  it('navigates to setup when "Open Scoring Console" is clicked with no active match', () => {
    stubCoachWorkspace()

    cy.visitWithAuth('/coaches')
    cy.contains('button', 'Open Scoring Console').click()

    cy.location('pathname').should('eq', '/setup')
  })

  it('navigates to Analyst Workspace when the shortcut button is clicked', () => {
    stubCoachWorkspace()

    cy.visitWithAuth('/coaches')
    cy.contains('button', 'Analyst Workspace').click()

    // Both /analyst and /analyst/workspace map to AnalystWorkspaceView
    cy.location('pathname').should('match', /^\/analyst/)
  })

  it('enables Save Note button only when text is entered', () => {
    stubCoachWorkspace()

    cy.visitWithAuth('/coaches')

    const noteArea = cy.get('textarea[placeholder*="Add notes"]')
    cy.contains('button', 'Save Note').should('be.disabled')

    noteArea.type('Test coaching note')
    cy.contains('button', 'Save Note').should('not.be.disabled')
  })

  it('redirects unauthenticated users to /login', () => {
    // Do NOT use visitWithAuth — visit without setting a token
    cy.visit('/coaches')
    cy.location('pathname').should('eq', '/login')
  })
})

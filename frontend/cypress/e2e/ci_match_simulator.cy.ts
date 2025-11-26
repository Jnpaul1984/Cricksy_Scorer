const API_BASE: string = (Cypress.env('API_BASE') as string) || 'http://127.0.0.1:8000'

describe('CI match simulator smoke', () => {
  let gameId = ''
  let expectedResultText = ''
  let teamAName = 'Team Alpha'
  let teamBName = 'Team Beta'

  before(() => {
    cy.fixture('simulated_t20_match.json').then((fixture) => {
      if (Array.isArray(fixture?.teams)) {
        teamAName = fixture.teams[0] || teamAName
        teamBName = fixture.teams[1] || teamBName
      }
    })

    cy.task('seed:match').then((result: any) => {
      expect(result?.gameId, 'seeded game id').to.be.a('string').and.not.be.empty
      gameId = String(result.gameId)
      return cy.request(`${API_BASE}/games/${gameId}/results`).then((resp) => {
        expectedResultText = String(resp.body?.result_text || '')
      })
    })
  })

  beforeEach(() => {
    cy.viewport(1600, 1200)
  })

  it('renders viewer, scoring, and analytics views for the seeded match', () => {
    const viewerUrl = `/view/${gameId}?apiBase=${encodeURIComponent(API_BASE)}`
    cy.visitWithSnapshot(viewerUrl)
      .its('response.body')
      .then((snap) => {
        expect(Boolean(snap?.is_game_over), 'viewer snapshot is_game_over').to.be.true
      })
    cy.get('[data-testid="scoreboard-result-banner"]').should('contain.text', expectedResultText || 'won')
    cy.get('[data-testid="scoreboard-score"]').should('exist')
    cy.get('[data-testid="scoreboard-overs"]').should('contain.text', 'ov')

    cy.visitWithSnapshot(`/game/${gameId}/scoring`)
      .its('response.body')
      .then((snap) => {
        expect(Boolean(snap?.is_game_over), 'scoring snapshot is_game_over').to.be.true
      })

    cy.get('[data-testid="scoreboard-result-banner"]').should('contain.text', expectedResultText || 'won')
    cy.get('[data-testid="submit-delivery"]').should('be.disabled')

    cy.visitWithAuth(`/analytics?apiBase=${encodeURIComponent(API_BASE)}`)
    cy.get('input[placeholder="Team A name"]').clear().type(teamAName)
    cy.get('input[placeholder="Team B name"]').clear().type(teamBName)
    cy.contains('button', 'Search').click()
    cy.contains('.result-list button', `${teamAName} vs ${teamBName}`, { timeout: 20000 }).click()

    cy.get('[data-testid="analytics-runrate-card"]').should('contain.text', 'Run Rate')
    cy.get('[data-testid="analytics-manhattan-card"]').scrollIntoView().find('canvas').should('exist')
    cy.get('[data-testid="analytics-worm-card"]').scrollIntoView().find('canvas').should('exist')
    cy.get('[data-testid="analytics-extras-card"]').should('contain.text', 'Legal balls')
    cy.get('[data-testid="analytics-batting-card"]').find('tbody tr').its('length').should('be.greaterThan', 5)
    cy.get('[data-testid="analytics-bowling-card"]').find('tbody tr').its('length').should('be.greaterThan', 5)
    cy.get('[data-testid="analytics-phase-card"]').should('contain.text', 'Powerplay')
  })
})

const API_BASE: string = (Cypress.env('API_BASE') as string) || 'http://127.0.0.1:8000'

describe('Simulated T20 embed scoreboard', () => {
  let gameId = ''
  let expectedResultText = ''

  before(() => {
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

  it('shows the seeded winner banner and score on the embeddable view', () => {
    const embedUrl = `/embed/${gameId}?apiBase=${encodeURIComponent(API_BASE)}&theme=dark`
    cy.visitWithSnapshot(embedUrl)
      .its('response.body')
      .then((snap) => {
        expect(Boolean(snap?.is_game_over), 'embed snapshot is_game_over').to.be.true
        expect(Number(snap?.total_runs ?? 0), 'total runs populated').to.be.greaterThan(0)
      })

    cy.get('[data-testid="scoreboard-score"]').should('exist')
    cy.get('[data-testid="scoreboard-overs"]').should('contain.text', 'ov')
    cy.get('[data-testid="scoreboard-result-banner"]').should('contain.text', expectedResultText || 'won')
  })
})

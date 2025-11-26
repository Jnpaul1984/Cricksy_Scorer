describe('Scoring gate smoke checks', () => {
  beforeEach(() => {
    cy.viewport(1600, 1200)
  })

  it('keeps the scoring console read-only once the match is completed', () => {
    cy.task('seed:match').then((result: any) => {
      const gameId = String(result.gameId)
      cy.visitWithSnapshot(`/game/${gameId}/scoring`)
        .its('response.body')
        .then((snap) => {
          expect(Boolean(snap?.is_game_over), 'is_game_over flag').to.be.true
        })

      cy.get('[data-testid="scoreboard-result-banner"]').should('exist')
      cy.get('[data-testid="submit-delivery"]').should('be.disabled')
    })
  })

  it('submits a legal delivery when no gates are raised', () => {
    cy.task('seed:live-game').then((res: any) => {
      const gameId = String(res.gameId)
      cy.intercept('POST', `**/games/${gameId}/deliveries`).as('scoreDelivery')

      let startingRuns = 0
      cy.visitWithSnapshot(`/game/${gameId}/scoring`)
        .its('response.body')
        .then((snap) => {
          startingRuns = Number(snap?.total_runs ?? 0)
          expect(Boolean(snap?.needs_new_innings), 'needs_new_innings flag').to.be.false
          expect(Boolean(snap?.needs_new_over), 'needs_new_over flag').to.be.false
          expect(Boolean(snap?.needs_new_batter), 'needs_new_batter flag').to.be.false
        })

      cy.get('[data-testid="submit-delivery"]').should('not.be.disabled')
      cy.get('[data-testid="delivery-run-4"]').click()
      cy.get('[data-testid="submit-delivery"]').click()

      cy.wait('@scoreDelivery').its('response.statusCode').should('be.oneOf', [200, 201, 204])
      cy.waitForSnapshotWhere((body) => Number(body?.total_runs ?? 0) >= startingRuns + 4)
      cy.get('[data-testid="scoreboard-runs"]')
        .invoke('text')
        .then((text) => {
          expect(Number(text.trim()), 'updated total runs').to.be.at.least(startingRuns + 4)
        })
    })
  })
})

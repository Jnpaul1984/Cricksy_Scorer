describe('Weather interruption start/resume flow', () => {
  let matchCtx: { gameId: string }

  before(() => {
    cy.task('seed:live-game').then((res: any) => {
      expect(res?.gameId, 'seeded game id').to.be.a('string').and.not.be.empty
      matchCtx = res
    })
  })

  beforeEach(() => {
    cy.viewport(1600, 1200)
  })

  it('shows a pause banner and disables scoring until play resumes', () => {
    cy.visitWithSnapshot(`/game/${matchCtx.gameId}/scoring`)
    cy.get('[data-testid="submit-delivery"]').should('not.be.disabled')

    cy.get('[data-testid="btn-open-weather"]').click()
    cy.get('[data-testid="btn-weather-start"]').click()

    // Wait for the banner to appear first to ensure the API call completed
    cy.get('[data-testid="interrupt-banner"]').should('be.visible')

    // Force reload to ensure the banner persists (tests backend persistence)
    cy.reload()

    cy.get('[data-testid="interrupt-banner"]').should('be.visible')
    cy.get('[data-testid="submit-delivery"]').should('be.disabled')

    // Resume via the weather modal
    cy.get('[data-testid="btn-open-weather"]').click()
    cy.get('[data-testid="btn-weather-resume"]').should('be.visible').click()

    cy.get('[data-testid="interrupt-banner"]').should('not.exist')
    cy.get('[data-testid="submit-delivery"]').should('not.be.disabled')
  })
})

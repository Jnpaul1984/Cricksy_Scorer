describe('Simulated T20 Match', () => {
  it('should display the correct winner and match summary', () => {
    cy.visit('/e2e')
    cy.fixture('simulated_t20_match.json').then((match) => {
      cy.window().should('have.property', 'loadMatch')
      cy.window().then((win: any) => {
        win.loadMatch(match)
      })
      cy.contains(match.result.winner, { timeout: 10000 }).should('exist')
      cy.contains(match.result.summary, { timeout: 10000 }).should('exist')
    })
  })
})

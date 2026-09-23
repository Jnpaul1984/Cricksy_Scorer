const ensureDialogOpen = (dialogTestId: string, triggerTestId: string) => {
  cy.get('body').then(($body) => {
    const isOpen = $body.find(`[data-testid="${dialogTestId}"]`).length > 0
    if (!isOpen) {
      cy.get(`[data-testid="${triggerTestId}"]`).should('be.visible').click({ force: true })
    }
  })
  cy.get(`[data-testid="${dialogTestId}"]`).should('be.visible').and('have.attr', 'role', 'dialog')
}

describe('End of innings → start next innings gate', () => {
  let matchCtx: {
    gameId: string
    teamAPlayers: Array<{ id: string; name: string }>
    teamBPlayers: Array<{ id: string; name: string }>
  }

  before(() => {
    cy.task('seed:innings-break').then((res: any) => {
      expect(res?.gameId, 'seeded game id').to.be.a('string').and.not.be.empty
      matchCtx = res
    })
  })

  beforeEach(() => {
    cy.viewport(1600, 1200)
  })

  it('clears the innings gate and shows chase targets', () => {
    cy.visitWithSnapshot(`/game/${matchCtx.gameId}/scoring`)
      .its('response.body')
      .then((snap) => {
        expect(Boolean(snap?.needs_new_innings), 'initial needs_new_innings flag').to.be.true
      })

    cy.get('[data-testid="gate-innings"]').should('be.visible')
    cy.get('[data-testid="submit-delivery"]').should('be.disabled')

    const striker = matchCtx.teamBPlayers[0]
    const nonStriker = matchCtx.teamBPlayers[1]
    const openingBowler = matchCtx.teamAPlayers[0]
    ensureDialogOpen('modal-start-innings', 'btn-open-start-innings')
    cy.get('[data-testid="select-next-striker"]').select(striker.id)
    cy.get('[data-testid="select-next-nonstriker"]').select(nonStriker.id)
    cy.get('[data-testid="select-opening-bowler"]').select(openingBowler.id)
    cy.get('[data-testid="confirm-start-innings"]').click()

    cy.waitForSnapshotFlag('needs_new_innings', false).then((snap) => {
      expect(Boolean(snap?.needs_new_over), 'needs_new_over reset').to.be.false
    })

    cy.get('[data-testid="submit-delivery"]').should('not.be.disabled')
    cy.get('[data-testid="scorer-striker-select"]').should('have.value', striker.id)
    cy.get('[data-testid="scorer-nonstriker-select"]').should('have.value', nonStriker.id)
    cy.get('[data-testid="scorer-bowler-select"]').should('have.value', openingBowler.id)
    cy.get('[data-testid="scoreboard-target"]')
      .should('contain.text', 'Target')
      .invoke('text')
      .should('match', /Target:\s*\d+/)
    cy.contains('.rate-item', 'RRR').should('exist')
  })
})

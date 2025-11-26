const API_BASE: string = (Cypress.env('API_BASE') as string) || 'http://127.0.0.1:8000'

const ensureDialogOpen = (dialogTestId: string, triggerTestId: string) => {
  cy.get('body').then(($body) => {
    const isOpen = $body.find(`[data-testid="${dialogTestId}"][open]`).length > 0
    if (!isOpen) {
      cy.get(`[data-testid="${triggerTestId}"]`).should('be.visible').click()
    }
  })
  cy.get(`[data-testid="${dialogTestId}"]`).should('have.attr', 'open')
}

describe('Wicket → needs_new_batter gate clears after selecting replacement', () => {
  let matchCtx: {
    gameId: string
    strikerId: string
    nonStrikerId: string
    bowlerId: string
    teamAPlayers: Array<{ id: string; name: string }>
  }

  before(() => {
    cy.task('seed:live-game').then((res: any) => {
      expect(res?.gameId, 'seeded game id').to.be.a('string').and.not.be.empty
      matchCtx = res
    })
  })

  beforeEach(() => {
    cy.viewport(1600, 1200)
  })

  it('blocks scoring until a new batter is chosen', () => {
    cy.visitWithSnapshot(`/game/${matchCtx.gameId}/scoring`)
      .its('response.body')
      .then((snap) => {
        expect(Boolean(snap?.needs_new_batter), 'initial needs_new_batter flag').to.be.false
      })

    cy.get('[data-testid="submit-delivery"]').should('not.be.disabled')

    const wicketPayload = {
      striker_id: matchCtx.strikerId,
      non_striker_id: matchCtx.nonStrikerId,
      bowler_id: matchCtx.bowlerId,
      is_wicket: true,
      dismissal_type: 'bowled',
    }
    cy.request('POST', `${API_BASE}/games/${matchCtx.gameId}/deliveries`, wicketPayload).its('status').should('be.oneOf', [200, 201, 204])

    // Reload to ensure state is fresh if sockets are flaky
    cy.reload()
    cy.waitForSnapshotFlag('needs_new_batter', true)
    cy.get('[data-testid="gate-new-batter"]').should('be.visible')
    cy.get('[data-testid="submit-delivery"]').should('be.disabled')

    const replacement = matchCtx.teamAPlayers?.[2]
    expect(replacement?.id, 'replacement batter id').to.be.a('string').and.not.be.empty

    ensureDialogOpen('modal-select-batter', 'btn-open-select-batter')
    cy.get('[data-testid="select-next-batter"]').select(replacement.id)
    cy.get('[data-testid="confirm-select-batter"]').click()

    // UI updates immediately via store, no need to wait for socket snapshot
    cy.get('[data-testid="gate-new-batter"]').should('not.exist')
    cy.get('[data-testid="submit-delivery"]').should('not.be.disabled')
  })
})

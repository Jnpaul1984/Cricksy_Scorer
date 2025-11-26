const API_BASE: string = (Cypress.env('API_BASE') as string) || 'http://127.0.0.1:8000'

const ensureDialogOpen = (dialogTestId: string, triggerTestId: string) => {
  cy.get('body').then(($body) => {
    const isOpen = $body.find(`[data-testid="${dialogTestId}"][open]`).length > 0
    if (!isOpen) {
      cy.get(`[data-testid="${triggerTestId}"]`).scrollIntoView().should('be.visible').click({ force: true })
    }
  })
  cy.get(`[data-testid="${dialogTestId}"]`).should('have.attr', 'open')
}

const addPlayers = (editorIndex: number, names: string[]) => {
  const joined = names.join(', ')
  cy.get('[data-testid^="players-editor-"]')
    .eq(editorIndex)
    .within(() => {
      cy.get('[data-testid="players-quick-input"]').clear().type(joined)
      cy.get('[data-testid="players-add-btn"]').click()
      cy.get('.list .row').should('have.length.at.least', names.length)
    })
}

describe('Match creation → XI selection → scoring console', () => {
  beforeEach(() => {
    cy.viewport(1600, 1200)
  })

  it('creates a match, locks the XI, and enables scoring with correct labels', () => {
    const stamp = Date.now()
    const teamAName = `Cypress Alpha ${stamp}`
    const teamBName = `Cypress Beta ${stamp}`
    const playersA = Array.from({ length: 11 }, (_, i) => `Alpha Player ${i + 1}`)
    const playersB = Array.from({ length: 11 }, (_, i) => `Beta Player ${i + 1}`)

    let createdGameId = ''
    let teamAPlayers: Array<{ id: string; name: string }> = []
    let teamBPlayers: Array<{ id: string; name: string }> = []

    cy.intercept('POST', '**/games').as('createGame')

    cy.visitWithAuth('/setup')
    cy.get('[data-testid="input-team-a"]').type(teamAName)
    cy.get('[data-testid="input-team-b"]').type(teamBName)

    addPlayers(0, playersA)
    addPlayers(1, playersB)

    cy.get('[data-testid="select-toss-winner"]').select(teamAName)
    cy.get('[data-testid="radio-bat"]').check({ force: true })
    cy.get('[data-testid="btn-create-match"]').should('not.be.disabled').click()

    cy.wait('@createGame').then((interception) => {
      expect(interception?.response?.statusCode).to.be.oneOf([200, 201])
      if (interception?.response?.body?.id) {
        createdGameId = String(interception.response.body.id)
        teamAPlayers =
          (interception.response.body?.team_a?.players as Array<{ id: string; name: string }>) || []
        teamBPlayers =
          (interception.response.body?.team_b?.players as Array<{ id: string; name: string }>) || []
      }
    })

    cy.location('pathname', { timeout: 30000 })
      .should('match', /\/game\/[^/]+\/select-xi/)
      .then((pathname) => {
        if (!createdGameId) {
          const match = pathname.match(/\/game\/([^/]+)\/select-xi/)
          createdGameId = match?.[1] || ''
        }
        expect(createdGameId).to.match(/^[-a-zA-Z0-9]+$/)
      })
      .then(() => {
        return cy.request(`${API_BASE}/games/${encodeURIComponent(createdGameId)}`)
      })
      .then((resp) => {
        teamAPlayers =
          (resp.body?.team_a?.players as Array<{ id: string; name: string }>) || []
        teamBPlayers =
          (resp.body?.team_b?.players as Array<{ id: string; name: string }>) || []

        const [capA, keepA] = teamAPlayers
        const [capB, keepB] = teamBPlayers

        cy.get('[data-testid="team-a-player"]').should('have.length.at.least', 11)
        cy.get('[data-testid="team-b-player"]').should('have.length.at.least', 11)

        cy.get('[data-testid="select-captain-a"]').select(capA.id)
        cy.get('[data-testid="select-keeper-a"]').select(keepA.id)
        cy.get('[data-testid="select-captain-b"]').select(capB.id)
        cy.get('[data-testid="select-keeper-b"]').select(keepB.id)

        cy.get('[data-testid="btn-save-xi"]').should('not.be.disabled').click()
      })

    cy.then(() => {
      return cy
        .visitWithSnapshot(`/game/${createdGameId}/scoring`)
        .its('response.body')
        .then((snap) => {
          expect(Boolean(snap?.needs_new_innings)).to.be.true
        })
    })

    cy.then(() => {
      const striker = teamAPlayers[0]
      const nonStriker = teamAPlayers[1]
      const openingBowler = teamBPlayers[0]

      ensureDialogOpen('modal-start-innings', 'btn-open-start-innings')

      cy.get('[data-testid="select-next-striker"]').select(striker.id)
      cy.get('[data-testid="select-next-nonstriker"]').select(nonStriker.id)
      cy.get('[data-testid="select-opening-bowler"]').select(openingBowler.id)

      cy.get('[data-testid="confirm-start-innings"]').click()
    })

    cy.waitForSnapshotFlag('needs_new_innings', false).then((snap) => {
      expect(Boolean(snap?.needs_new_batter)).to.be.false
      expect(Boolean(snap?.needs_new_over)).to.be.false
    })

    cy.get('[data-testid="submit-delivery"]').should('not.be.disabled')
  })
})

/* eslint-disable @typescript-eslint/no-unused-expressions */
const API_BASE: string = (Cypress.env('API_BASE') as string) || 'http://localhost:8000'

describe('CI Match Simulator', () => {
  let gameId: string

  before(() => {
    // Wider viewport helps avoid sticky header overlap
    cy.viewport(1600, 1200)

    cy.task('seed:match').then((result: any) => {
      expect(result?.gameId, 'seeded game id').to.be.a('string').and.not.be.empty
      gameId = result.gameId
    })
  })

  it('renders scoreboard, scoring, and analytics views for the seeded match', () => {
    const scoreboardUrl = `/view/${gameId}?apiBase=${encodeURIComponent(API_BASE)}`
    cy.visit(scoreboardUrl)

    // Assert result-banner against actual API result to avoid brittle exact string
    cy.request(`${API_BASE}/games/${gameId}/results`).then((resp) => {
      const body: any = resp.body || {}
      const winner = String(body?.winner_team_name || body?.winner || '')
      const expectedText = String(body?.result_text || '').replace(/\.$/, '') // trim trailing period

      cy.get('.result-banner', { timeout: 15000 })
        .should('exist')
        .invoke('text')
        .then((txt) => {
          const norm = String(txt).trim().replace(/\s+/g, ' ').replace(/\.$/, '')
          if (expectedText) {
            expect(norm).to.contain(expectedText)
          } else {
            // Fallback: generic signal that a result is shown
            expect(norm.toLowerCase()).to.contain('won by')
          }
          if (winner) {
            expect(norm).to.contain(winner)
          }
        })
    })

    // First-innings summary: tolerant to format like "20 ov" vs "20.0 ov"
    cy.get('.first-inn', { timeout: 15000 })
      .should('exist')
      .within(() => {
        cy.get('strong')
          .invoke('text')
          .should((txt) => {
            expect(txt).to.match(/\b\d{2,3}\/\d{1,2}\b/)        // e.g., 157/6
            expect(txt).to.match(/\(\s*\d+(?:\.\d+)?\s*ov\)/i)  // e.g., (20 ov) or (20.0 ov)
          })
      })

    // Scoring view
    cy.visit(`/game/${gameId}/scoring`)
    cy.contains('DeliveryTable', { timeout: 15000 }).should('not.exist')
    cy.get('.left table tbody tr', { timeout: 15000 }).its('length').should('be.greaterThan', 50)
    cy.get('.extras-card').should('contain', 'Wides').and('contain', 'Leg-byes')
    cy.get('.extras-card .dls-card').should('exist')
    cy.get('.scorecards-grid').within(() => {
      cy.contains('Batting').should('exist')
      cy.contains('Bowling').should('exist')
    })

    // Analytics
    cy.visit('/analytics')
    cy.get('input[placeholder="Team A name"]').clear().type('Team Alpha')
    cy.get('input[placeholder="Team B name"]').clear().type('Team Beta')
    cy.contains('button', 'Search').click()
    cy.contains('.result-list button', 'Team Alpha vs Team Beta', { timeout: 10000 }).click()

    // Scroll to avoid sticky headers occluding headings
    cy.contains('h3', 'Run Rate', { timeout: 15000 })
      .scrollIntoView({ ensureScrollable: false })
      .should('exist')
      .and('contain', 'Current')

    cy.contains('h3', 'Manhattan', { timeout: 15000 })
      .scrollIntoView({ ensureScrollable: false })
      .parent()
      .find('canvas')
      .should('exist')

    cy.contains('h3', 'Worm', { timeout: 15000 })
      .scrollIntoView({ ensureScrollable: false })
      .parent()
      .find('canvas')
      .should('exist')

    cy.contains('h3', 'Extras / Dot & Boundary %', { timeout: 15000 })
      .scrollIntoView({ ensureScrollable: false })
      .parent()
      .should('contain', 'Legal balls: 240')

    cy.contains('h3', 'Batting', { timeout: 15000 })
      .scrollIntoView({ ensureScrollable: false })
      .parent()
      .find('tbody tr')
      .its('length')
      .should('be.greaterThan', 5)

    cy.contains('h3', 'Bowling', { timeout: 15000 })
      .scrollIntoView({ ensureScrollable: false })
      .parent()
      .find('tbody tr')
      .its('length')
      .should('be.greaterThan', 5)

    cy.contains('h3', 'DLS Panel', { timeout: 15000 })
      .scrollIntoView({ ensureScrollable: false })
      .parent()
      .should('exist')

    cy.contains('h3', 'Phase Splits', { timeout: 15000 })
      .scrollIntoView({ ensureScrollable: false })
      .parent()
      .should('contain', 'Powerplay')
  })
})

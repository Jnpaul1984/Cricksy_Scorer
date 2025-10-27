/* eslint-disable @typescript-eslint/no-unused-expressions */
const API_BASE: string =
  (Cypress.env('API_BASE') as string) || 'http://localhost:8000'

describe('CI Match Simulator', () => {
  let gameId: string

  before(() => {
    cy.viewport(1600, 1200)
    cy.task('seed:match').then((result: any) => {
      expect(result?.gameId, 'seeded game id')
        .to.be.a('string')
        .and.not.be.empty
      gameId = result.gameId
    })
  })

  it('renders scoreboard, scoring, and analytics views for the seeded match', () => {
    const url = `/view/${gameId}?apiBase=${encodeURIComponent(API_BASE)}`
    cy.visit(url)

    cy.get('.result-banner', { timeout: 20000 })
      .should('exist')
      .invoke('text')
      .then((txt) => {
        const t = String(txt).trim()
        let ok = false
        if (t.startsWith('{') && t.endsWith('}')) {
          try {
            const j = JSON.parse(t)
            const a = Number(j?.team_a_score || 0)
            const b = Number(j?.team_b_score || 0)
            const winner = String(
              j?.winner_team_name || j?.winner || ''
            ).toLowerCase()
            const isTie = a === b
            const phrase = isTie ? 'match tied' : 'won by'
            ok = t.toLowerCase().includes(phrase) || Boolean(winner)
          } catch {
            ok = false
          }
        } else {
          const low = t.toLowerCase()
          ok = low.includes('won by') || low.includes('match tied')
        }
        expect(ok, `banner text: ${t}`).to.be.true
      })

    // Scoring view
    cy.visit(`/game/${gameId}/scoring`)
    cy.contains('DeliveryTable', { timeout: 15000 }).should('not.exist')
    cy.get('.left table tbody tr', { timeout: 15000 })
      .its('length')
      .should('be.greaterThan', 50)
    cy.get('.extras-card')
      .should('contain', 'Wides')
      .and('contain', 'Leg-byes')
    cy.get('.extras-card .dls-card').should('exist')
    cy.get('.scorecards-grid').within(() => {
      cy.contains('Batting').should('exist')
      cy.contains('Bowling').should('exist')
    })

    // Analytics — pass apiBase so search hits the backend
    cy.visit(`/analytics?apiBase=${encodeURIComponent(API_BASE)}`)
    cy.get('input[placeholder="Team A name"]').clear().type('Team Alpha')
    cy.get('input[placeholder="Team B name"]').clear().type('Team Beta')
    cy.contains('button', 'Search').click()
    cy.contains('.result-list button', 'Team Alpha vs Team Beta', {
      timeout: 15000,
    }).click()

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

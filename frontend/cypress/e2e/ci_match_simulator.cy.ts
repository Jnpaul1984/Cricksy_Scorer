/* eslint-disable @typescript-eslint/no-unused-expressions */
const API_BASE: string = (Cypress.env('API_BASE') as string) || 'http://localhost:8000'

describe('CI Match Simulator', () => {
  let gameId: string

  before(() => {
    cy.task('seed:match').then((result: any) => {
      expect(result?.gameId, 'seeded game id').to.be.a('string').and.not.be.empty
      gameId = result.gameId
    })
  })

  it('renders scoreboard, scoring, and analytics views for the seeded match', () => {
    const scoreboardUrl = `/view/${gameId}?apiBase=${encodeURIComponent(API_BASE)}`

    cy.visit(scoreboardUrl)

    // Result banner proves the page bootstrapped with a completed match
    cy.contains('.result-banner', 'Team Alpha won by 15 runs', { timeout: 15000 }).should('be.visible')

    // Be tolerant to format differences like "20 ov" vs "20.0 ov"
    cy.get('.first-inn', { timeout: 15000 })
      .should('be.visible')
      .within(() => {
        cy.get('strong')
          .invoke('text')
          .should((txt) => {
            // e.g., "157/6 (20 ov)" or "157/6 (20.0 ov)"
            expect(txt).to.match(/\b\d{2,3}\/\d{1,2}\b/)        // scoreline like 157/6
            expect(txt).to.match(/\(\s*\d+(?:\.\d+)?\s*ov\)/i)  // overs like (20 ov) or (20.0 ov)
          })
      })

    cy.get('.mini.batting-table tbody tr').its('length').should('be.greaterThan', 5)
    cy.get('.mini.bowling-table tbody tr').its('length').should('be.greaterThan', 4)
    cy.get('.info-strip').should('contain', 'Target').and('contain', '158')

    cy.contains('.pane-title', 'Bowler')
      .parent()
      .should('contain', 'Figures')
      .and('contain', '(')

    cy.get('.balls .ball').its('length').should('be.at.least', 6)

    cy.visit(`/game/${gameId}/scoring`)
    cy.contains('DeliveryTable', { timeout: 15000 }).should('not.exist')
    cy.get('.left table tbody tr', { timeout: 15000 }).its('length').should('be.greaterThan', 100)
    cy.get('.extras-card').should('contain', 'Wides').and('contain', 'Leg-byes')
    cy.get('.extras-card .dls-card').should('exist')
    cy.get('.scorecards-grid').within(() => {
      cy.contains('Batting').should('be.visible')
      cy.contains('Bowling').should('be.visible')
    })

    cy.visit('/analytics')
    cy.get('input[placeholder="Team A name"]').clear().type('Team Alpha')
    cy.get('input[placeholder="Team B name"]').clear().type('Team Beta')
    cy.contains('button', 'Search').click()
    cy.contains('.result-list button', 'Team Alpha vs Team Beta', { timeout: 10000 }).click()

    cy.contains('h3', 'Run Rate').should('contain', 'Current')
    cy.contains('h3', 'Manhattan').parent().find('canvas').should('exist')
    cy.contains('h3', 'Worm').parent().find('canvas').should('exist')
    cy.contains('h3', 'Extras / Dot & Boundary %').parent().should('contain', 'Legal balls: 240')
    cy.contains('h3', 'Batting').parent().find('tbody tr').its('length').should('be.greaterThan', 5)
    cy.contains('h3', 'Bowling').parent().find('tbody tr').its('length').should('be.greaterThan', 5)
    cy.contains('h3', 'DLS Panel').parent().should('exist')
    cy.contains('h3', 'Phase Splits').parent().should('contain', 'Powerplay')
  })
})

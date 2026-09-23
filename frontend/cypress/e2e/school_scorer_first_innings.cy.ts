const API_BASE: string = (Cypress.env('API_BASE') as string) || 'http://127.0.0.1:8000'

type SchoolMatchMode = 'school-v-school' | 'school-team-a-external' | 'school-team-b-external'

const createPreMatch = (mode: SchoolMatchMode) => {
  const stamp = `${mode}-${Date.now()}`
  return cy.request('POST', `${API_BASE}/games`, {
    team_a_name: mode === 'school-team-b-external' ? 'External Team A' : 'School Team A',
    team_b_name: mode === 'school-team-a-external' ? 'External Team B' : 'School Team B',
    players_a: Array.from({ length: 11 }, (_, index) => `A Player ${index + 1} ${stamp}`),
    players_b: Array.from({ length: 11 }, (_, index) => `B Player ${index + 1} ${stamp}`),
    match_type: 'limited',
    overs_limit: 2,
    toss_winner_team: mode === 'school-team-b-external' ? 'External Team A' : 'School Team A',
    decision: 'bat',
  }).its('body')
}

const exerciseSchoolFirstInnings = (mode: SchoolMatchMode) => {
  createPreMatch(mode).then((game: any) => {
    const gameId = String(game.id)
    const strikerId = String(game.team_a.players[0].id)
    const nonStrikerId = String(game.team_a.players[1].id)
    const bowlerId = String(game.team_b.players[0].id)
    let openerRequests = 0
    let startRequests = 0
    let deliveryRequests = 0

    cy.intercept('GET', `**/games/${gameId}`, req => {
      req.continue(response => {
        if (mode === 'school-v-school' || mode === 'school-team-a-external') {
          response.body.team_a.school_source = {
            organization_id: 'school-context',
            team_id: 'school-team-a',
          }
        }
        if (mode === 'school-v-school' || mode === 'school-team-b-external') {
          response.body.team_b.school_source = {
            organization_id: 'school-context',
            team_id: 'school-team-b',
          }
        }
      })
    }).as('schoolGame')
    cy.intercept('GET', `**/games/${gameId}/snapshot`, req => {
      req.continue(response => {
        response.body.school_organization_id = 'school-context'
        response.body.can_score = true
      })
    }).as('schoolSnapshot')
    cy.intercept('POST', `**/games/${gameId}/openers`, req => {
      openerRequests += 1
      req.continue()
    }).as('setSchoolOpeners')
    cy.intercept('POST', `**/games/${gameId}/innings/start`, req => {
      startRequests += 1
      expect(req.body).to.deep.equal({
        striker_id: strikerId,
        non_striker_id: nonStrikerId,
        opening_bowler_id: bowlerId,
      })
      req.continue()
    }).as('startSchoolInnings')
    cy.intercept('POST', `**/games/${gameId}/deliveries`, req => {
      deliveryRequests += 1
      req.continue()
    }).as('schoolDelivery')

    cy.visitWithAuth(`/game/${gameId}/scoring`, 'free')
    cy.wait('@schoolSnapshot')
    cy.get('[data-testid="gate-innings"]')
      .should('be.visible')
      .and('contain.text', 'Ready to Start')
    cy.get('[data-testid="school-first-innings-guidance"]')
      .should('contain.text', 'Select striker, non-striker and opening bowler to begin.')
    cy.get('[data-testid="btn-open-start-innings"]').should('not.exist')

    cy.get('[data-testid="scorer-striker-select"]').select(strikerId)
    cy.get('[data-testid="scorer-nonstriker-select"]').select(nonStrikerId)
    cy.then(() => {
      expect(startRequests, 'start requests before all selections').to.equal(0)
      expect(deliveryRequests, 'delivery requests before start').to.equal(0)
    })
    cy.get('[data-testid="scorer-bowler-select"]').select(bowlerId)

    cy.wait('@setSchoolOpeners').its('response.statusCode').should('eq', 200)
    cy.wait('@startSchoolInnings').its('response.statusCode').should('eq', 200)
    cy.get('[data-testid="gate-innings"]').should('not.exist')
    cy.get('[data-testid="scorer-controls"]')
      .should('be.visible')
      .and('have.attr', 'aria-disabled', 'false')
    cy.get('[data-testid="submit-delivery"]').should('not.be.disabled')
    cy.then(() => {
      expect(openerRequests, 'opening-selection requests').to.equal(1)
      expect(startRequests, 'first-innings start requests').to.equal(1)
      expect(deliveryRequests, 'automatic delivery requests').to.equal(0)
    })

    cy.get('[data-testid="delivery-run-1"]').click()
    cy.get('[data-testid="submit-delivery"]').click()
    cy.wait('@schoolDelivery').its('response.statusCode').should('eq', 200)
    cy.get('[data-testid="scoreboard-runs"]').should('contain.text', '1')
    cy.then(() => {
      expect(startRequests, 'start remains exactly once after scoring').to.equal(1)
      expect(deliveryRequests, 'explicit delivery requests').to.equal(1)
    })
  })
}

describe('School contextual scorer first-innings flow', () => {
  beforeEach(() => {
    cy.viewport(1440, 1000)
  })

  it('starts School vs School only after valid opening selections', () => {
    exerciseSchoolFirstInnings('school-v-school')
  })

  it('starts School Team A vs external only after valid opening selections', () => {
    exerciseSchoolFirstInnings('school-team-a-external')
  })

  it('starts external vs School Team B only after valid opening selections', () => {
    exerciseSchoolFirstInnings('school-team-b-external')
  })

  it('keeps a School viewer read-only and never issues a start request', () => {
    createPreMatch('school-v-school').then((game: any) => {
      const gameId = String(game.id)
      let startRequests = 0
      cy.intercept('GET', `**/games/${gameId}/snapshot`, req => {
        req.continue(response => {
          response.body.school_organization_id = 'school-context'
          response.body.can_score = false
        })
      }).as('viewerSnapshot')
      cy.intercept('POST', `**/games/${gameId}/innings/start`, req => {
        startRequests += 1
        req.continue()
      })

      cy.visitWithAuth(`/game/${gameId}/scoring`, 'superuser')
      cy.wait('@viewerSnapshot')
      cy.get('[data-testid="scorer-striker-select"]').should('be.disabled')
      cy.get('[data-testid="scorer-nonstriker-select"]').should('be.disabled')
      cy.get('[data-testid="scorer-bowler-select"]').should('be.disabled')
      cy.get('[data-testid="scorer-controls"]').should('have.attr', 'aria-disabled', 'true')
      cy.then(() => expect(startRequests).to.equal(0))
    })
  })
})

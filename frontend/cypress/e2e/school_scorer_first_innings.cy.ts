type SchoolMatchMode = 'school-v-school' | 'school-team-a-external' | 'school-team-b-external'

const players = (side: 'a' | 'b') => Array.from({ length: 11 }, (_, index) => ({
  id: `00000000-0000-4000-8000-${side === 'a' ? '1' : '2'}${String(index + 1).padStart(11, '0')}`,
  name: `${side.toUpperCase()} Player ${index + 1}`,
}))

const installSchoolMatchFixture = (mode: SchoolMatchMode, canScore = true) => {
  const gameId = `00000000-0000-4000-8000-${mode === 'school-v-school' ? '300000000001' : mode === 'school-team-a-external' ? '300000000002' : '300000000003'}`
  const teamAPlayers = players('a')
  const teamBPlayers = players('b')
  const strikerId = teamAPlayers[0].id
  const nonStrikerId = teamAPlayers[1].id
  const bowlerId = teamBPlayers[0].id
  const requests = { openers: 0, start: 0, delivery: 0 }
  let started = false
  let runs = 0

  const teamA = {
    name: mode === 'school-team-b-external' ? 'External Team A' : 'School Team A',
    players: teamAPlayers,
    ...(mode === 'school-v-school' || mode === 'school-team-a-external'
      ? { school_source: { organization_id: 'school-context', team_id: 'school-team-a' } }
      : {}),
  }
  const teamB = {
    name: mode === 'school-team-a-external' ? 'External Team B' : 'School Team B',
    players: teamBPlayers,
    ...(mode === 'school-v-school' || mode === 'school-team-b-external'
      ? { school_source: { organization_id: 'school-context', team_id: 'school-team-b' } }
      : {}),
  }

  const game = () => ({
    id: gameId,
    team_a: teamA,
    team_b: teamB,
    match_type: 'limited',
    overs_limit: 2,
    toss_winner_team: teamA.name,
    decision: 'bat',
    batting_team_name: teamA.name,
    bowling_team_name: teamB.name,
    status: started ? 'IN_PROGRESS' : 'INNINGS_BREAK',
    current_inning: started ? 1 : 0,
    total_runs: runs,
    total_wickets: 0,
    overs_completed: 0,
    balls_this_over: runs,
    current_striker_id: started ? strikerId : null,
    current_non_striker_id: started ? nonStrikerId : null,
    current_bowler_id: started ? bowlerId : null,
    target: null,
    result: null,
    is_game_over: false,
    needs_new_innings: !started,
    interruptions: [],
    deliveries: [],
    batting_scorecard: {},
    bowling_scorecard: {},
  })

  const snapshot = () => ({
    id: gameId,
    status: started ? 'IN_PROGRESS' : 'INNINGS_BREAK',
    score: { runs, wickets: 0, overs: runs ? 0.1 : 0 },
    total_runs: runs,
    total_wickets: 0,
    overs_completed: 0,
    balls_this_over: runs,
    current_run_rate: runs ? 6 : 0,
    required_run_rate: null,
    overs: runs ? '0.1' : '0.0',
    balls_bowled_total: runs,
    current_bowler_id: started ? bowlerId : null,
    current_striker_id: started ? strikerId : null,
    current_non_striker_id: started ? nonStrikerId : null,
    batting_team_name: teamA.name,
    bowling_team_name: teamB.name,
    current_inning: started ? 1 : 0,
    target: null,
    needs_new_over: false,
    needs_new_batter: false,
    needs_new_innings: !started,
    is_game_over: false,
    interruptions: [],
    school_organization_id: 'school-context',
    can_score: canScore,
    players: { batting: teamAPlayers, bowling: teamBPlayers },
    teams: { batting: { name: teamA.name }, bowling: { name: teamB.name } },
  })

  cy.intercept('GET', `**/games/${gameId}`, req => req.reply(game())).as('schoolGame')
  cy.intercept('GET', `**/games/${gameId}/snapshot`, req => req.reply(snapshot())).as('schoolSnapshot')
  cy.intercept('GET', `**/games/${gameId}/deliveries*`, {
    game_id: gameId,
    count: 0,
    deliveries: [],
  })
  cy.intercept('GET', `**/games/${gameId}/recent_deliveries*`, {
    game_id: gameId,
    count: 0,
    deliveries: [],
  })
  cy.intercept('GET', `**/games/${gameId}/interruptions*`, [])
  cy.intercept('GET', `**/api/analytics/games/${gameId}/phase-predictions*`, {})
  cy.intercept('POST', `**/games/${gameId}/openers`, req => {
    requests.openers += 1
    expect(req.body).to.deep.equal({ striker_id: strikerId, non_striker_id: nonStrikerId })
    req.reply(snapshot())
  }).as('setSchoolOpeners')
  cy.intercept('POST', `**/games/${gameId}/innings/start`, req => {
    requests.start += 1
    expect(req.body).to.deep.equal({
      striker_id: strikerId,
      non_striker_id: nonStrikerId,
      opening_bowler_id: bowlerId,
    })
    if (!canScore) {
      req.reply({ statusCode: 403, body: { detail: 'Insufficient organization role' } })
      return
    }
    started = true
    req.reply(snapshot())
  }).as('startSchoolInnings')
  cy.intercept('POST', `**/games/${gameId}/overs/start`, req => {
    expect(req.body).to.deep.equal({ bowler_id: bowlerId })
    req.reply({ ok: true, current_bowler_id: bowlerId })
  })
  cy.intercept('POST', `**/games/${gameId}/deliveries`, req => {
    requests.delivery += 1
    expect(started, 'delivery follows successful first-innings start').to.be.true
    runs += Number(req.body?.runs_scored ?? req.body?.runs_off_bat ?? 0)
    req.reply(snapshot())
  }).as('schoolDelivery')

  return { gameId, strikerId, nonStrikerId, bowlerId, requests }
}

const exerciseSchoolFirstInnings = (mode: SchoolMatchMode) => {
  const fixture = installSchoolMatchFixture(mode)

  cy.visitWithAuth(`/game/${fixture.gameId}/scoring`, 'free')
  cy.wait('@schoolSnapshot')
  cy.get('[data-testid="gate-innings"]')
    .should('be.visible')
    .and('contain.text', 'Ready to Start')
  cy.get('[data-testid="school-first-innings-guidance"]')
    .should('contain.text', 'Select striker, non-striker and opening bowler to begin.')
  cy.get('[data-testid="btn-open-start-innings"]').should('not.exist')

  cy.get('[data-testid="scorer-striker-select"]').select(fixture.strikerId)
  cy.get('[data-testid="scorer-nonstriker-select"]').select(fixture.nonStrikerId)
  cy.then(() => {
    expect(fixture.requests.start, 'start requests before all selections').to.equal(0)
    expect(fixture.requests.delivery, 'delivery requests before start').to.equal(0)
  })
  cy.get('[data-testid="scorer-bowler-select"]').select(fixture.bowlerId)

  cy.wait('@setSchoolOpeners').its('response.statusCode').should('eq', 200)
  cy.wait('@startSchoolInnings').its('response.statusCode').should('eq', 200)
  cy.get('[data-testid="gate-innings"]').should('not.exist')
  cy.get('[data-testid="scorer-controls"]')
    .should('be.visible')
    .and('have.attr', 'aria-disabled', 'false')
  cy.get('[data-testid="submit-delivery"]').should('not.be.disabled')
  cy.then(() => {
    expect(fixture.requests.openers, 'opening-selection requests').to.equal(1)
    expect(fixture.requests.start, 'first-innings start requests').to.equal(1)
    expect(fixture.requests.delivery, 'automatic delivery requests').to.equal(0)
  })

  cy.get('[data-testid="delivery-run-1"]').click()
  cy.get('[data-testid="submit-delivery"]').click()
  cy.wait('@schoolDelivery').its('response.statusCode').should('eq', 200)
  cy.get('[data-testid="scoreboard-runs"]').should('contain.text', '1')
  cy.then(() => {
    expect(fixture.requests.start, 'start remains exactly once after scoring').to.equal(1)
    expect(fixture.requests.delivery, 'explicit delivery requests').to.equal(1)
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
    const fixture = installSchoolMatchFixture('school-v-school', false)

    cy.visitWithAuth(`/game/${fixture.gameId}/scoring`, 'superuser')
    cy.wait('@schoolSnapshot')
    cy.get('[data-testid="scorer-striker-select"]').should('be.disabled')
    cy.get('[data-testid="scorer-nonstriker-select"]').should('be.disabled')
    cy.get('[data-testid="scorer-bowler-select"]').should('be.disabled')
    cy.get('[data-testid="scorer-controls"]').should('have.attr', 'aria-disabled', 'true')
    cy.then(() => expect(fixture.requests.start).to.equal(0))
  })
})

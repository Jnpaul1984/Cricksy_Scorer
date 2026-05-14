const analystMatches = {
  items: [
    {
      id: 'match-001',
      date: '2025-01-10',
      format: 'T20',
      teams: 'Lions vs Falcons',
      result: 'Lions won by 18 runs',
      run_rate: 8.4,
      phase_swing: '+18 in death',
      status: 'completed',
      venue: 'Generic Cricket Ground',
      event_name: 'Premier League 2025',
      season: '2025',
      match_number: 3,
      source_dates: ['2025-01-10'],
      match_datetime: null,
      is_historical: true,
      source: 'historical_import',
      historical_batch_id: 'batch-001',
    },
    {
      id: 'match-002',
      date: '2025-01-15',
      format: 'ODI',
      teams: 'Tigers vs Eagles',
      result: 'Tigers won by 5 wickets',
      run_rate: 5.2,
      phase_swing: '-12 in powerplay',
      status: 'completed',
      venue: 'Riverside Oval',
      event_name: 'City Cup',
      season: '2025',
      match_number: 7,
      source_dates: ['2025-01-15'],
      match_datetime: null,
      is_historical: false,
      source: 'live',
      historical_batch_id: null,
    },
    {
      id: 'match-003',
      date: '2024-12-22',
      format: 'T20',
      teams: 'Sharks vs Panthers',
      result: 'Sharks won by 11 runs',
      run_rate: 7.6,
      phase_swing: '+9 in middle overs',
      status: 'completed',
      venue: 'Harbor Stadium',
      event_name: 'Coastal Cup',
      season: '2024',
      match_number: 2,
      source_dates: ['2024-12-22'],
      match_datetime: null,
      is_historical: true,
      source: 'historical_import',
      historical_batch_id: 'batch-003',
    },
  ],
  total: 3,
}

const matchDetails = {
  'match-001': {
    match: {
      id: 'match-001',
      date: '2025-01-10',
      format: 'T20',
      teams_label: 'Lions vs Falcons',
      result: 'Lions won by 18 runs',
      home_team: 'Lions',
      away_team: 'Falcons',
      venue: 'Generic Cricket Ground',
      overs_per_side: 20,
      innings: [
        { team: 'Lions', runs: 178, wickets: 6, overs: 20, run_rate: 8.9 },
        { team: 'Falcons', runs: 160, wickets: 10, overs: 19.4, run_rate: 8.2 },
      ],
    },
    momentum_summary: {
      title: 'Lions dominated from ball one',
      subtitle: 'Consistent batting throughout all phases',
      winning_side: 'Lions',
      swing_metric: null,
    },
    key_phase: {
      title: 'Death overs surge',
      detail: 'Lions scored 45 runs in the last 4 overs to pull clear',
      overs_range: { start_over: 16, end_over: 20 },
      reason_codes: [],
    },
    phases: [
      {
        id: 'powerplay',
        label: 'Powerplay',
        start_over: 1,
        end_over: 6,
        runs: 52,
        wickets: 1,
        run_rate: 8.67,
        net_swing_vs_par: 10,
        impact: 'positive',
        impact_label: 'Strong start',
      },
      {
        id: 'middle',
        label: 'Middle overs',
        start_over: 7,
        end_over: 15,
        runs: 81,
        wickets: 3,
        run_rate: 9,
        net_swing_vs_par: 5,
        impact: 'neutral',
        impact_label: 'On par',
      },
      {
        id: 'death',
        label: 'Death overs',
        start_over: 16,
        end_over: 20,
        runs: 45,
        wickets: 2,
        run_rate: 9,
        net_swing_vs_par: 3,
        impact: 'positive',
        impact_label: 'Good finish',
      },
    ],
    key_players: [
      {
        id: 'player-001',
        name: 'J. Anderson',
        team: 'Lions',
        role: 'Batsman',
        impact: 'high',
        impact_label: 'Match winner',
        impact_score: 8.5,
        batting: {
          innings: 1,
          runs: 72,
          balls: 48,
          strike_rate: 150,
          boundaries: { fours: 6, sixes: 3 },
        },
        bowling: null,
        fielding: null,
      },
    ],
    dismissal_patterns: null,
    ai: null,
  },
}

const matchRegistries = {
  'match-001': {
    match_id: 'match-001',
    is_historical: true,
    competition: 'Premier League 2025',
    season: '2025',
    venue: 'Generic Cricket Ground',
    teams: 'Lions vs Falcons',
    match_number: 3,
    player_count: 22,
    innings_count: 2,
    has_deliveries: true,
    import_batch_id: 'batch-001',
    source_filename: 'match_001.json',
    source_format: 'cricsheet_json',
    source_type: 'json',
    imported_at: '2025-01-10T12:00:00Z',
    validation_status: 'valid',
    registration_status: 'registered',
    training_eligible: true,
    blocking_reason: null,
  },
}

const authMe = {
  id: 'cypress-user',
  email: 'cypress@example.com',
  name: 'Cypress Analyst',
  role: 'org_pro',
  is_superuser: false,
}

function stubSuccessfulLibrary() {
  cy.intercept('GET', '**/auth/me', authMe).as('authMe')
  cy.intercept('GET', '**/analytics/matches', analystMatches).as('getAnalystMatches')
  cy.intercept('GET', '**/analytics/matches/*/case-study', (req) => {
    const matchId = req.url.split('/').slice(-2, -1)[0]
    req.reply(matchDetails[matchId as keyof typeof matchDetails] ?? matchDetails['match-001'])
  }).as('getMatchCaseStudy')
  cy.intercept('GET', '**/analytics/matches/*/registry', (req) => {
    const matchId = req.url.split('/').slice(-2, -1)[0]
    req.reply(matchRegistries[matchId as keyof typeof matchRegistries] ?? {
      match_id: matchId,
      is_historical: false,
      competition: null,
      season: null,
      venue: null,
      teams: null,
      match_number: null,
      player_count: 0,
      innings_count: 0,
      has_deliveries: false,
      import_batch_id: null,
      source_filename: null,
      source_format: null,
      source_type: 'live',
      imported_at: null,
      validation_status: 'not_applicable',
      registration_status: 'not_registered',
      training_eligible: false,
      blocking_reason: 'not_a_historical_import',
    })
  }).as('getMatchRegistry')
}

describe('Analyst Workspace data library gate', () => {
  beforeEach(() => {
    cy.viewport(1600, 1200)
  })

  it('loads the analyst workspace and validates data library search, filters, sort, and detail flow', () => {
    stubSuccessfulLibrary()

    cy.visitWithAuth('/analyst/workspace')
    cy.wait('@getAnalystMatches')

    cy.contains('h1', 'Analyst Workspace').should('be.visible')
    cy.contains('button', 'Data Library').should('be.visible').click()

    cy.contains('h3', 'Data Library').should('be.visible')
    cy.get('.aw-dl-row').should('have.length', 3)
    cy.get('.aw-dl-row').first().should('contain.text', 'Tigers vs Eagles')
    cy.get('.aw-dl-badge--imported').should('exist')
    cy.contains('.aw-dl-row', 'Lions vs Falcons').should('contain.text', 'Historical import')

    cy.get('input[placeholder="Search by team, competition, venue, season…"]').type('Premier League')
    cy.get('.aw-dl-row').should('have.length', 1).first().should('contain.text', 'Lions vs Falcons')

    cy.get('input[placeholder="Search by team, competition, venue, season…"]').clear()
    cy.get('.aw-dl-filter-row .aw-chip-row').eq(0).contains('button', 'Imported').click()
    cy.get('.aw-dl-row').should('have.length', 2)
    cy.contains('.aw-dl-table', 'Tigers vs Eagles').should('not.exist')

    cy.get('.aw-dl-filter-row .aw-chip-row').eq(0).contains('button', 'All').click()
    cy.get('.aw-dl-filter-row .aw-chip-row').eq(1).contains('button', 'ODI').click()
    cy.get('.aw-dl-row').should('have.length', 1).first().should('contain.text', 'Tigers vs Eagles')

    cy.get('.aw-dl-filter-row .aw-chip-row').eq(1).contains('button', 'All').click()
    cy.get('.aw-dl-row').should('have.length', 3)
    cy.get('.aw-dl-filter-row .aw-chip-row').eq(2).contains('button', 'Oldest first').click()
    cy.get('.aw-dl-row').first().should('contain.text', 'Sharks vs Panthers')

    cy.contains('.aw-dl-row', 'Lions vs Falcons').within(() => {
      cy.contains('button', 'View').click()
    })

    cy.wait('@getMatchCaseStudy')
    cy.wait('@getMatchRegistry')

    cy.get('#aw-match-detail').should('be.visible').and('contain.text', 'Lions vs Falcons')
    cy.get('.aw-detail-registry').should('contain.text', 'Premier League 2025')
  })

  it('shows an empty state when the matches API returns no analyst data', () => {
    cy.intercept('GET', '**/auth/me', authMe).as('authMe')
    cy.intercept('GET', '**/analytics/matches', { items: [], total: 0 }).as('getAnalystMatches')

    cy.visitWithAuth('/analyst/workspace')
    cy.wait('@getAnalystMatches')
    cy.contains('button', 'Data Library').click()

    cy.contains('No analyst-ready match data is available yet.').should('be.visible')
  })

  it('shows an error state when the matches API fails', () => {
    cy.intercept('GET', '**/auth/me', authMe).as('authMe')
    cy.intercept('GET', '**/analytics/matches', {
      statusCode: 500,
      body: { detail: 'Data library unavailable' },
    }).as('getAnalystMatches')

    cy.visitWithAuth('/analyst/workspace')
    cy.wait('@getAnalystMatches')
    cy.contains('button', 'Data Library').click()

    cy.contains('Unable to load match data right now.').should('be.visible')
  })
})

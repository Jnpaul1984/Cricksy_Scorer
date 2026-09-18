const school = {
  id: 'school-a',
  name: 'Central School',
  organization_type: 'school',
  status: 'active',
  membership_role: 'owner',
  created_by_user_id: 'owner-a',
  created_at: '',
  updated_at: '',
};
const membership = {
  id: 'member-a',
  organization_id: 'school-a',
  user_id: 'owner-a',
  role: 'owner',
  status: 'active',
  created_by_user_id: null,
  created_at: '',
  updated_at: '',
};
const entitlement = {
  id: 'ent-a',
  organization_id: 'school-a',
  plan_key: 'school_free',
  status: 'active',
  source: 'system',
  effective_from: '',
  effective_until: null,
  capabilities: [
    'school_basic_statistics',
    'school_fixtures_results',
    'school_live_scorecards',
    'school_competitions',
    'school_persistent_teams',
    'school_team_rosters',
    'school_match_playing_xi',
  ],
  excluded_capabilities: ['advanced_ai'],
  created_at: '',
  updated_at: '',
};
const competition = {
  id: 'cup-a',
  organization_id: 'school-a',
  name: 'School Cup',
  description: null,
  tournament_type: 'league',
  start_date: null,
  end_date: null,
  status: 'ongoing',
  created_at: '',
  updated_at: '',
};

function stubContext() {
  cy.intercept('GET', '**/api/organizations/school-a/me', membership);
  cy.intercept('GET', '**/api/organizations/school-a/entitlements', entitlement);
  cy.intercept('GET', '**/api/organizations/school-a', school);
  cy.intercept('GET', '**/api/organizations/school-a/teams', []);
}

describe('Phase 7J School statistics and competition journey', () => {
  it('moves from canonical statistics to competition fixture, result, and explicit publication', () => {
    stubContext();
    cy.intercept('GET', '**/statistics/players', [
      {
        player_profile_id: 'player-a',
        player_name: 'Asha',
        roster_status: 'active',
        matches: 1,
        innings: 1,
        runs: 40,
        highest_score: 40,
        batting_average: null,
        balls_faced: 30,
        strike_rate: 133.33,
        fours: 4,
        sixes: 1,
        bowling_innings: 0,
        balls_bowled: 0,
        overs: '0.0',
        runs_conceded: 0,
        wickets: 0,
        bowling_average: null,
        economy: null,
        best_bowling: null,
      },
    ]);
    cy.intercept('GET', '**/statistics/teams', [
      {
        team_id: 'team-a',
        team_name: 'First XI',
        team_status: 'active',
        matches: 1,
        wins: 1,
        losses: 0,
        ties: 0,
        draws: 0,
        no_results: 0,
        runs_scored: 100,
        runs_conceded: 90,
        wickets_taken: 10,
        wickets_lost: 5,
      },
    ]);
    cy.intercept('GET', '**/competitions', [competition]);
    cy.intercept('GET', '**/competitions/cup-a/teams', []);
    cy.intercept('GET', '**/competitions/cup-a/fixtures', []);
    cy.intercept('GET', '**/competitions/cup-a/standings', {
      competition_id: 'cup-a',
      entries: [],
      unresolved_completed_games: 0,
    });
    cy.intercept('GET', '**/api/organizations/school-a/fixtures', []);
    cy.intercept('GET', '**/api/organizations/school-a/results', [
      {
        game_id: 'game-a',
        team_a_id: 'team-a',
        team_a_name: 'First XI',
        team_b_id: 'team-b',
        team_b_name: 'Second XI',
        status: 'completed',
        result: 'First XI won by 10 runs',
        publication_state: 'private',
        current_inning: 2,
        team_a_runs: 100,
        team_a_wickets: 5,
        team_b_runs: 90,
        team_b_wickets: 10,
        public_scorecard_available: false,
      },
    ]);
    cy.intercept('PATCH', '**/matches/game-a/publication', (req) => {
      expect(req.body).to.deep.equal({ publication_state: 'published_final' });
      req.reply({
        game_id: 'game-a',
        organization_id: 'school-a',
        publication_state: 'published_final',
      });
    }).as('publish');

    cy.visitWithAuth('/schools/school-a/statistics');
    cy.contains('Asha').should('be.visible');
    cy.contains('First XI').should('be.visible');
    cy.contains('fielder identity').should('be.visible');
    cy.contains('a', 'Competitions').click();
    cy.contains('h3', 'School Cup').should('be.visible');
    cy.contains('a', 'Fixtures / Results').click();
    cy.contains('First XI won by 10 runs').should('be.visible');
    cy.on('window:confirm', () => true);
    cy.contains('button', 'Publish final').click();
    cy.wait('@publish');
  });

  it('renders a published scorecard without authentication or School metadata', () => {
    cy.intercept('GET', '**/public/school-scorecards/game-a', {
      game_id: 'game-a',
      publication_state: 'published_final',
      status: 'completed',
      team_a: { name: 'First XI', players: [{ name: 'Asha' }] },
      team_b: { name: 'Second XI', players: [{ name: 'Ben' }] },
      match_type: 'limited',
      overs_limit: 20,
      days_limit: null,
      overs_per_day: null,
      toss_winner_team: 'First XI',
      decision: 'bat',
      batting_team_name: 'Second XI',
      bowling_team_name: 'First XI',
      total_runs: 90,
      total_wickets: 10,
      overs_completed: 18,
      balls_this_over: 2,
      current_inning: 2,
      result: 'First XI won by 10 runs',
      batting_scorecard: [{ player_name: 'Ben', runs: 20 }],
      bowling_scorecard: [{ player_name: 'Asha', wickets_taken: 2 }],
    });
    cy.visit('/school-scorecards/game-a');
    cy.contains('First XI won by 10 runs').should('be.visible');
    cy.contains('student metadata are not displayed').should('be.visible');
  });
});

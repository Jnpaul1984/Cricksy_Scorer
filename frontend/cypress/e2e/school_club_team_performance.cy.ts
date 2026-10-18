const timestamp = '2026-01-01T00:00:00Z';

const performance = (organizationId: string, teamId: string) => ({
  organization_id: organizationId,
  team_id: teamId,
  overs_limit: 20,
  completeness: 'unknown',
  batting: {
    team_runs: 19,
    bat_runs: 19,
    wides: 0,
    no_ball_penalties: 0,
    byes: 0,
    leg_byes: 0,
    wickets_lost: 0,
    legal_balls: 11,
    legal_dots: 1,
    fours: 1,
    sixes: 0,
    run_rate: 10.36,
    legal_dot_percentage: 9.09,
    runs_per_wicket: null,
  },
  bowling: {
    opposition_team_runs: 13,
    bowler_charged_runs: 9,
    wides: 0,
    no_ball_penalties: 0,
    byes: 0,
    leg_byes: 0,
    team_wickets: 1,
    bowler_credited_wickets: 1,
    legal_balls: 6,
    legal_dots: 1,
    team_concession_rate: 13,
    bowling_economy: 9,
    legal_dot_percentage: 16.67,
  },
  coverage: {
    status: 'usable_recorded_data',
    eligible_games: 1,
    included_games: 1,
    usable_batting_innings: 1,
    usable_bowling_innings: 1,
    used_delivery_rows: 17,
    observed_delivery_rows: 17,
    excluded_games: 0,
    excluded_innings: 0,
    cohort_excluded_games: 0,
    cohort_exclusion_counts: {},
    no_ledger_games: 0,
    invalid_data_games: 0,
    invalid_data_innings: 0,
    warning_counts: {},
  },
});

function stubOrganization(kind: 'school' | 'club', id: string) {
  const base = kind === 'school' ? 'schools' : 'clubs';
  const organization = {
    id,
    name: kind === 'school' ? 'Central School' : 'Central Cricket Club',
    organization_type: kind,
    status: 'active',
    membership_role: 'coach',
    created_by_user_id: 'coach-a',
    created_at: timestamp,
    updated_at: timestamp,
  };
  cy.intercept('GET', `**/api/organizations/${id}`, organization);
  cy.intercept('GET', `**/api/organizations/${id}/me`, {
    id: `membership-${id}`,
    organization_id: id,
    user_id: 'coach-a',
    role: 'coach',
    status: 'active',
    created_by_user_id: null,
    created_at: timestamp,
    updated_at: timestamp,
  });
  cy.intercept('GET', `**/api/organizations/${id}/entitlements`, {
    id: `entitlement-${id}`,
    organization_id: id,
    plan_key: kind === 'school' ? 'school_free' : 'club_free',
    status: 'active',
    source: 'system',
    effective_from: timestamp,
    effective_until: null,
    capabilities: [],
    excluded_capabilities: [],
    created_at: timestamp,
    updated_at: timestamp,
  });
  cy.intercept('GET', `**/api/organizations/${id}/team-performance/teams`, [
    {
      id: 'team-active',
      name: 'First XI',
      status: 'active',
    },
    {
      id: 'team-archived',
      name: 'Archive XI',
      status: 'archived',
    },
  ]);
  cy.intercept('GET', `**/api/organizations/${id}/team-performance/teams/**`, (req) => {
    const teamId = req.url.includes('team-archived') ? 'team-archived' : 'team-active';
    req.reply(performance(id, teamId));
  }).as(`teamPerformance-${id}`);
  cy.visitWithAuth(`/${base}/${id}/team-performance`, 'free');
}

describe('School/Club Team Performance staff pilot', () => {
  for (const [kind, id, title] of [
    ['school', 'school-pilot', 'Central School'],
    ['club', 'club-pilot', 'Central Cricket Club'],
  ] as const) {
    it(`renders the private ${kind} aggregate workspace and exact selected scope`, () => {
      stubOrganization(kind, id);
      cy.contains('h1', title).should('be.visible');
      cy.contains('h2', 'Team Performance').should('be.visible');
      cy.contains(
        'Based on recorded delivery data. Historical completeness has not been verified.',
      ).should('be.visible');
      cy.contains('Team runs').parent().should('contain', '19');
      cy.contains('Legal balls (overs)').parent().should('contain', '11 (1.5)');
      cy.contains('Player average').should('not.exist');
      cy.wait(`@teamPerformance-${id}`);

      cy.get('select[aria-label="Team"]').select('team-archived');
      cy.contains('Archive XI (archived)').should('be.visible');
      cy.wait(`@teamPerformance-${id}`)
        .its('request.url')
        .should('include', '/team-performance/teams/team-archived?overs_limit=20');
    });

    it(`shows unavailable access when the ${kind} pilot team listing is denied`, () => {
      cy.intercept('GET', `**/api/organizations/${id}`, {
        id,
        name: title,
        organization_type: kind,
        status: 'active',
        membership_role: 'coach',
        created_by_user_id: 'coach-a',
        created_at: timestamp,
        updated_at: timestamp,
      });
      const base = kind === 'school' ? 'schools' : 'clubs';
      cy.intercept('GET', `**/api/organizations/${id}/me`, {
        id: `membership-${id}`,
        organization_id: id,
        user_id: 'coach-a',
        role: 'coach',
        status: 'active',
        created_by_user_id: null,
        created_at: timestamp,
        updated_at: timestamp,
      });
      cy.intercept('GET', `**/api/organizations/${id}/entitlements`, {
        id: `entitlement-${id}`,
        organization_id: id,
        plan_key: `${kind}_free`,
        status: 'active',
        source: 'system',
        effective_from: timestamp,
        effective_until: null,
        capabilities: [],
        excluded_capabilities: [],
        created_at: timestamp,
        updated_at: timestamp,
      });
      cy.intercept('GET', `**/api/organizations/${id}/team-performance/teams`, {
        statusCode: 403,
        body: { detail: 'Team Performance is unavailable' },
      }).as(`deniedTeams-${id}`);
      cy.intercept('GET', `**/api/organizations/${id}/teams`, [
        {
          id: 'team-active',
          organization_id: id,
          name: 'First XI',
          status: 'active',
          home_ground: null,
          season: null,
          owner_user_id: null,
          coach_user_id: null,
          coach_name: null,
          created_at: timestamp,
          updated_at: timestamp,
        },
      ]);
      cy.visitWithAuth(`/${base}/${id}/team-performance`, 'free');
      cy.wait(`@deniedTeams-${id}`);
      cy.contains(
        'Team Performance is unavailable for this organization or your current access.',
      ).should('be.visible');
      cy.contains('Team batting').should('not.exist');
      cy.contains('Team runs').should('not.exist');
    });

    it(`clears displayed ${kind} aggregates after a later denied request`, () => {
      stubOrganization(kind, id);
      cy.wait(`@teamPerformance-${id}`);
      cy.contains('Team runs').parent().should('contain', '19');
      cy.contains('Team batting').should('be.visible');

      cy.intercept('GET', `**/api/organizations/${id}/team-performance/teams/**`, {
        statusCode: 403,
        body: { detail: 'Team Performance is unavailable' },
      }).as(`deniedPerformanceAfterDisplay-${id}`);
      cy.get('input[aria-label="Overs limit"]').clear().type('21');
      cy.wait(`@deniedPerformanceAfterDisplay-${id}`);
      cy.contains(
        'Team Performance is unavailable for this organization or your current access.',
      ).should('be.visible');
      cy.contains('Team batting').should('not.exist');
      cy.contains('Team runs').should('not.exist');
    });
  }
});

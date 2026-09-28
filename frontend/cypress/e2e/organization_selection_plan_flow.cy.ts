type OrganizationKind = 'school' | 'club';

function stubSelectionJourney(kind: OrganizationKind) {
  const organizationId = `${kind}-selection`;
  const basePath = kind === 'school' ? '/schools' : '/clubs';
  const kindLabel = kind === 'school' ? 'School' : 'Club';
  const team = {
    id: 'team-a',
    organization_id: organizationId,
    name: 'First XI',
    status: 'active',
    home_ground: null,
    season: '2026',
    owner_user_id: 'owner-a',
    coach_user_id: null,
    coach_name: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };
  const fixture = {
    fixture_id: 'fixture-a',
    competition_id: 'cup-a',
    competition_name: `${kindLabel} Cup`,
    team_a_id: 'team-a',
    team_a_name: 'First XI',
    team_b_id: 'team-b',
    team_b_name: 'Second XI',
    match_number: 1,
    venue: 'Main Ground',
    scheduled_date: '2099-04-01T14:00:00Z',
    fixture_status: 'scheduled',
    game_id: null,
    game_status: null,
    result: null,
    publication_state: null,
    public_scorecard_available: false,
  };
  let created = false;
  let revision = 1;
  let availabilityWrites = 0;
  const plan = () => ({
    id: 'plan-a',
    organization_id: organizationId,
    team_id: 'team-a',
    fixture_id: 'fixture-a',
    status: 'draft',
    revision,
    xi_roster_membership_ids: revision > 1 ? ['player-unavailable', 'player-maybe'] : [],
    reserve_roster_membership_ids: revision > 1 ? ['player-none'] : [],
    captain_roster_membership_id: revision > 1 ? 'player-unavailable' : null,
    wicketkeeper_roster_membership_id: revision > 1 ? 'player-maybe' : null,
    created_by_user_id: 'owner-a',
    updated_by_user_id: 'owner-a',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  });

  cy.intercept('GET', '**/auth/me', {
    id: 'owner-a',
    email: `${kind}@example.test`,
    role: 'free',
    is_active: true,
  });
  cy.intercept('GET', `**/api/organizations/${organizationId}`, {
    id: organizationId,
    name: `${kindLabel} Selection`,
    organization_type: kind,
    status: 'active',
    membership_role: 'owner',
    created_by_user_id: 'owner-a',
    created_at: '',
    updated_at: '',
  });
  cy.intercept('GET', `**/api/organizations/${organizationId}/me`, {
    id: 'membership-a',
    organization_id: organizationId,
    user_id: 'owner-a',
    role: 'owner',
    status: 'active',
    created_by_user_id: null,
    created_at: '',
    updated_at: '',
  });
  cy.intercept('GET', `**/api/organizations/${organizationId}/entitlements`, {
    id: 'entitlement-a',
    organization_id: organizationId,
    plan_key: `${kind}_free`,
    status: 'active',
    source: 'system',
    effective_from: '',
    effective_until: null,
    capabilities: [
      'school_fixtures_results',
      'school_live_scorecards',
      'organization_selection_plans',
    ],
    excluded_capabilities: [],
    created_at: '',
    updated_at: '',
  });
  cy.intercept('GET', `**/api/organizations/${organizationId}/teams`, [team]);
  cy.intercept('GET', `**/api/organizations/${organizationId}/fixtures`, [fixture]);
  cy.intercept('GET', `**/api/organizations/${organizationId}/results`, []);
  cy.intercept('GET', `**/api/organizations/${organizationId}/selection-plans?*`, (req) => {
    req.reply(created ? { statusCode: 200, body: plan() } : { statusCode: 404, body: { detail: 'Selection plan not found' } });
  }).as(`${kind}LookupSelection`);
  cy.intercept('POST', `**/api/organizations/${organizationId}/selection-plans`, (req) => {
    expect(req.body).to.deep.equal({ team_id: 'team-a', fixture_id: 'fixture-a' });
    created = true;
    req.reply({ statusCode: 201, body: plan() });
  }).as(`${kind}CreateSelection`);
  cy.intercept('GET', `**/api/organizations/${organizationId}/selection-plans/plan-a/candidates`, {
    organization_id: organizationId,
    team_id: 'team-a',
    fixture_id: 'fixture-a',
    candidates: [
      ['player-available', 'Available Player', 'available'],
      ['player-unavailable', 'Unavailable Player', 'unavailable'],
      ['player-maybe', 'Maybe Player', 'maybe'],
      ['player-none', 'No Response Player', null],
    ].map(([id, player_name, availability_state]) => ({
      roster_membership_id: id,
      player_profile_id: `profile-${id}`,
      player_name,
      eligible: true,
      availability_state,
    })),
  });
  cy.intercept('PATCH', `**/api/organizations/${organizationId}/selection-plans/plan-a`, (req) => {
    expect(req.body.expected_revision).to.equal(1);
    expect(req.body.xi_roster_membership_ids).to.deep.equal([
      'player-unavailable',
      'player-maybe',
    ]);
    expect(req.body.reserve_roster_membership_ids).to.deep.equal(['player-none']);
    revision = 2;
    req.reply({ statusCode: 200, body: plan() });
  }).as(`${kind}SaveSelection`);
  cy.intercept('PUT', '**/availability/**', (req) => {
    availabilityWrites += 1;
    req.reply({ statusCode: 500, body: { detail: 'Selection must not write Availability' } });
  });

  return { organizationId, basePath, getAvailabilityWrites: () => availabilityWrites };
}

describe('shared School and Club draft-selection journey', () => {
  (['school', 'club'] as const).forEach((kind) => {
    it(`${kind} explicitly creates and saves an availability-aware draft`, () => {
      const { organizationId, basePath, getAvailabilityWrites } = stubSelectionJourney(kind);
      if (kind === 'club') cy.viewport(390, 844);

      cy.visitWithAuth(`${basePath}/${organizationId}/fixtures-results`);
      cy.contains('a', 'Plan First XI').click();
      cy.location('pathname').should(
        'eq',
        `${basePath}/${organizationId}/selection/fixture-a/team-a`,
      );
      cy.wait(`@${kind}LookupSelection`);
      cy.contains('No draft selection has been created').should('be.visible');
      cy.contains('button', 'Create draft selection').click();
      cy.wait(`@${kind}CreateSelection`);

      cy.contains('Available Player').should('be.visible');
      cy.contains('Unavailable Player').should('be.visible');
      cy.contains('Maybe Player').should('be.visible');
      cy.contains('No Response Player').should('be.visible');
      cy.get('[data-test=add-xi-player-unavailable]').click();
      cy.get('[data-test=add-xi-player-maybe]').click();
      cy.get('[data-test=add-reserve-player-none]').click();
      cy.get('[data-test=selection-captain]').select('player-unavailable');
      cy.get('[data-test=selection-wicketkeeper]').select('player-maybe');
      cy.get('[data-test=save-selection-plan]').click();
      cy.wait(`@${kind}SaveSelection`);
      cy.contains('Draft saved at revision 2').should('be.visible');
      cy.then(() => expect(getAvailabilityWrites()).to.equal(0));
    });
  });
});

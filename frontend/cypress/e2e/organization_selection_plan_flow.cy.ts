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
  let status: 'draft' | 'published' = 'draft';
  let latestPublicationVersion: number | null = null;
  let xiIds: string[] = [];
  let reserveIds: string[] = [];
  let captainId: string | null = null;
  let wicketkeeperId: string | null = null;
  let battingOrderIds: string[] = [];
  let bowlingPlan: Array<{ roster_membership_id: string; role: 'primary' | 'secondary' }> = [];
  let publications: Record<string, unknown>[] = [];
  let availabilityWrites = 0;
  const plan = () => ({
    id: 'plan-a',
    organization_id: organizationId,
    team_id: 'team-a',
    fixture_id: 'fixture-a',
    status,
    revision,
    xi_roster_membership_ids: xiIds,
    reserve_roster_membership_ids: reserveIds,
    captain_roster_membership_id: captainId,
    wicketkeeper_roster_membership_id: wicketkeeperId,
    batting_order_roster_membership_ids: battingOrderIds,
    bowling_plan: bowlingPlan,
    latest_publication_version: latestPublicationVersion,
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
      ...Array.from({ length: 7 }, (_, index) => [
        `player-extra-${index + 1}`,
        `Extra Player ${index + 1}`,
        null,
      ]),
    ].map(([id, player_name, availability_state]) => ({
      roster_membership_id: id,
      player_profile_id: `profile-${id}`,
      player_name,
      eligible: true,
      availability_state,
    })),
  });
  cy.intercept('GET', `**/api/organizations/${organizationId}/selection-plans/plan-a/publications`, (req) => {
    req.reply(publications);
  });
  cy.intercept('PATCH', `**/api/organizations/${organizationId}/selection-plans/plan-a`, (req) => {
    expect(req.body.expected_revision).to.equal(1);
    xiIds = req.body.xi_roster_membership_ids;
    reserveIds = req.body.reserve_roster_membership_ids;
    captainId = req.body.captain_roster_membership_id;
    wicketkeeperId = req.body.wicketkeeper_roster_membership_id;
    battingOrderIds = req.body.batting_order_roster_membership_ids;
    bowlingPlan = req.body.bowling_plan;
    revision = 2;
    req.reply({ statusCode: 200, body: plan() });
  }).as(`${kind}SaveSelection`);
  cy.intercept('POST', `**/api/organizations/${organizationId}/selection-plans/plan-a/publish`, (req) => {
    expect(req.body).to.deep.equal({ expected_revision: 2 });
    status = 'published';
    latestPublicationVersion = 1;
    const publication = {
      id: 'publication-a', organization_id: organizationId, selection_plan_id: 'plan-a',
      team_id: 'team-a', fixture_id: 'fixture-a', plan_revision: 2, publication_version: 1,
      status: 'published', captain_roster_membership_id: captainId,
      wicketkeeper_roster_membership_id: wicketkeeperId,
      players: xiIds.map((id, index) => ({
        roster_membership_id: id, player_profile_id: `profile-${id}`,
        player_name: id, selection_role: 'xi', batting_position: index + 1,
        bowling_priority: null, bowling_role: null,
      })),
      published_by_user_id: 'owner-a', published_at: '2026-09-28T00:00:00Z',
    };
    publications = [publication];
    req.reply({ statusCode: 201, body: publication });
  }).as(`${kind}PublishSelection`);
  cy.intercept('POST', `**/api/organizations/${organizationId}/selection-plans/plan-a/draft`, (req) => {
    status = 'draft';
    revision = 3;
    req.reply({ statusCode: 200, body: plan() });
  }).as(`${kind}BeginDraft`);
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

    it(`${kind} publishes private match preparation and explicitly begins the next draft`, () => {
      const { organizationId, basePath } = stubSelectionJourney(kind);
      const ids = [
        'player-available',
        'player-unavailable',
        'player-maybe',
        'player-none',
        ...Array.from({ length: 7 }, (_, index) => `player-extra-${index + 1}`),
      ];
      cy.visitWithAuth(`${basePath}/${organizationId}/selection/fixture-a/team-a`);
      cy.contains('button', 'Create draft selection').click();
      cy.wait(`@${kind}CreateSelection`);
      ids.forEach((id) => cy.get(`[data-test=add-xi-${id}]`).click());
      cy.get('[data-test=selection-captain]').select(ids[0]);
      cy.get('[data-test=selection-wicketkeeper]').select(ids[1]);
      ids.forEach((id) => cy.get(`[data-test=add-batting-${id}]`).click());
      cy.get(`[data-test=add-bowler-${ids[2]}]`).click();
      cy.get('[data-test=save-selection-plan]').click();
      cy.wait(`@${kind}SaveSelection`);
      cy.get('[data-test=publish-selection-plan]').click();
      cy.wait(`@${kind}PublishSelection`);
      cy.contains('Published private selection version 1').should('be.visible');
      cy.contains('Published selection history').should('be.visible');
      cy.contains('button', 'Version 1').click();
      cy.get('[data-test=published-selection-snapshot]').should('be.visible');
      cy.get('[data-test=begin-selection-draft]').click();
      cy.wait(`@${kind}BeginDraft`);
      cy.contains('New draft started at revision 3').should('be.visible');
    });
  });
});

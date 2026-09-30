type OrganizationType = 'school' | 'club';

const publicIdentifier = 'org_0123456789abcdef01234567';

function publicCommunity(organizationType: OrganizationType) {
  const label = organizationType === 'school' ? 'School' : 'Club';
  return {
    public_identifier: publicIdentifier,
    display_name: `North ${label}`,
    organization_type: organizationType,
    branding: {
      logo_url: null,
      logo_alt_text: `North ${label} logo`,
      fallback_text: 'N',
    },
    competitions: [
      {
        name: 'Community Cup',
        tournament_type: 'league',
        start_date: '2026-09-30T12:00:00Z',
        end_date: null,
        status: 'ongoing',
        team_names: ['First XI', 'Second XI'],
        fixtures: [
          {
            team_a_name: 'First XI',
            team_b_name: 'Second XI',
            match_number: 1,
            venue: 'Main Ground',
            scheduled_date: '2026-10-01T12:00:00Z',
            fixture_status: 'completed',
            game_status: 'completed',
            result: 'First XI won by 8 runs',
            public_scorecard_path: '/school-scorecards/public-game',
          },
        ],
        standings: [
          {
            team_name: 'First XI',
            matches_played: 1,
            matches_won: 1,
            matches_lost: 0,
            matches_drawn: 0,
            points: 2,
          },
        ],
      },
    ],
  };
}

describe('Shared organization community homepage', () => {
  for (const organizationType of ['school', 'club'] as const) {
    it(`renders the anonymous ${organizationType} page on mobile without private sections`, () => {
      cy.viewport(375, 667);
      cy.intercept(
        'GET',
        `**/api/public/organizations/${publicIdentifier}/community`,
        publicCommunity(organizationType),
      ).as('community');
      cy.visit(`/community/${publicIdentifier}`);
      cy.wait('@community');
      cy.contains('h1', organizationType === 'school' ? 'North School' : 'North Club');
      cy.contains(`${organizationType === 'school' ? 'School' : 'Club'} cricket community`);
      cy.contains('Community Cup');
      cy.contains('First XI won by 8 runs');
      cy.contains('View published scorecard').focus().should('have.focus');
      cy.contains(/roster|member directory|player profile/i).should('not.exist');
      cy.get('body').then($body => {
        expect($body[0].scrollWidth).to.be.at.most($body[0].clientWidth + 1);
      });
    });
  }

  it('provides shared Owner controls while preserving explicit competition publication', () => {
    const organizationId = 'school-community';
    const timestamp = '2026-09-30T00:00:00Z';
    cy.intercept('GET', '**/auth/me', {
      id: 'owner-a',
      email: 'owner@example.test',
      role: 'free',
      is_active: true,
    });
    cy.intercept('GET', `**/api/organizations/${organizationId}`, {
      id: organizationId,
      name: 'Community School',
      organization_type: 'school',
      status: 'active',
      membership_role: 'owner',
      created_by_user_id: 'owner-a',
      created_at: timestamp,
      updated_at: timestamp,
    });
    cy.intercept('GET', `**/api/organizations/${organizationId}/me`, {
      id: 'membership-a',
      organization_id: organizationId,
      user_id: 'owner-a',
      role: 'owner',
      status: 'active',
      created_by_user_id: 'owner-a',
      created_at: timestamp,
      updated_at: timestamp,
    });
    cy.intercept('GET', `**/api/organizations/${organizationId}/entitlements`, {
      id: 'entitlement-a',
      organization_id: organizationId,
      plan_key: 'school_free',
      status: 'active',
      source: 'system',
      effective_from: timestamp,
      effective_until: null,
      capabilities: ['school_competitions', 'school_fixtures_results'],
      excluded_capabilities: [],
      created_at: timestamp,
      updated_at: timestamp,
    });
    cy.intercept('GET', `**/api/organizations/${organizationId}/notifications/unread-count`, {
      unread_count: 0,
    });
    cy.intercept('GET', `**/api/organizations/${organizationId}/community-settings`, {
      organization_id: organizationId,
      public_identifier: publicIdentifier,
      publication_state: 'unpublished',
      logo_url: null,
      logo_alt_text: null,
      branding_version: 1,
      branding_updated_at: null,
      competitions: [
        {
          competition_id: 'competition-a',
          competition_name: 'Private until selected',
          publication_state: 'unpublished',
          publication_version: 1,
          published_at: null,
          unpublished_at: null,
          updated_by_user_id: null,
        },
      ],
    }).as('settings');
    cy.intercept('PUT', `**/api/organizations/${organizationId}/public-settings/publish`, {
      statusCode: 200,
      body: {},
    }).as('publishHomepage');
    cy.intercept(
      'PUT',
      `**/api/organizations/${organizationId}/competitions/competition-a/community-publication/publish`,
      {
        statusCode: 200,
        body: {
          competition_id: 'competition-a',
          competition_name: 'Private until selected',
          publication_state: 'published',
          publication_version: 2,
          published_at: timestamp,
          unpublished_at: null,
          updated_by_user_id: 'owner-a',
        },
      },
    ).as('publishCompetition');

    cy.visit(`/schools/${organizationId}/community`, {
      onBeforeLoad(win) {
        win.localStorage.setItem('cricksy_token', 'community-token');
      },
    });
    cy.wait('@settings');
    cy.get('[data-test="community-publication-panel"]')
      .should('contain.text', 'Status:')
      .and('contain.text', 'Private');
    cy.contains('Private until selected').parent().should('contain.text', 'Private');
    cy.contains('button', 'Publish homepage').click();
    cy.wait('@publishHomepage');
    cy.contains('Community page published.');
    cy.contains('li', 'Private until selected').within(() => {
      cy.contains('button', 'Publish').click();
    });
    cy.wait('@publishCompetition');
    cy.contains('Competition published to the community page.');
  });
});

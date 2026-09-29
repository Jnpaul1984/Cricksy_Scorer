type OrganizationKind = 'school' | 'club';

const createdAt = '2026-09-29T15:00:00Z';

function stubAnnouncements(kind: OrganizationKind) {
  const organizationId = `${kind}-announcements`;
  const basePath = kind === 'school' ? '/schools' : '/clubs';
  const kindLabel = kind === 'school' ? 'School' : 'Club';
  const audienceType = kind === 'school' ? 'organization' : 'team';
  let draft: Record<string, unknown> | null = null;
  let published: Record<string, unknown> | null = null;

  cy.intercept('GET', `**/api/organizations/${organizationId}`, {
    id: organizationId,
    name: `${kindLabel} Announcements`,
    organization_type: kind,
    status: 'active',
    membership_role: 'owner',
    created_by_user_id: 'owner-a',
    created_at: createdAt,
    updated_at: createdAt,
  });
  cy.intercept('GET', `**/api/organizations/${organizationId}/me`, {
    id: 'membership-a',
    organization_id: organizationId,
    user_id: 'owner-a',
    role: 'owner',
    status: 'active',
    created_by_user_id: null,
    created_at: createdAt,
    updated_at: createdAt,
  });
  cy.intercept('GET', `**/api/organizations/${organizationId}/entitlements`, {
    id: 'entitlement-a',
    organization_id: organizationId,
    plan_key: kind === 'school' ? 'school_free' : 'club_free',
    status: 'active',
    source: 'system',
    effective_from: createdAt,
    effective_until: null,
    capabilities: ['organization_notifications', 'school_persistent_teams'],
    excluded_capabilities: [],
    created_at: createdAt,
    updated_at: createdAt,
  });
  cy.intercept('GET', `**/api/organizations/${organizationId}/notifications/unread-count`, {
    unread_count: 0,
  });
  cy.intercept('GET', `**/api/organizations/${organizationId}/teams`, [
    {
      id: 'team-a',
      organization_id: organizationId,
      name: 'First XI',
      status: 'active',
      home_ground: null,
      season: '2026',
      owner_user_id: 'owner-a',
      coach_user_id: 'coach-a',
      coach_name: 'Coach A',
      created_at: createdAt,
      updated_at: createdAt,
    },
  ]);
  cy.intercept('GET', `**/api/organizations/${organizationId}/announcements*`, (req) => {
    const items = [draft, published].filter(Boolean);
    req.reply({ items, total: items.length, limit: 100, offset: 0 });
  });
  cy.intercept('POST', `**/api/organizations/${organizationId}/announcements`, (req) => {
    draft = {
      id: 'announcement-a',
      announcement_id: 'announcement-a',
      organization_id: organizationId,
      ...req.body,
      status: 'draft',
      revision: 1,
      last_published_version: 0,
      publication_version: null,
      published_by_user_id: null,
      published_at: null,
      eligible_recipient_count: null,
      delivered_count: null,
      suppressed_by_preference_count: null,
      unresolved_recipient_count: null,
      created_by_user_id: 'owner-a',
      updated_by_user_id: 'owner-a',
      created_at: createdAt,
      updated_at: createdAt,
    };
    req.reply({ statusCode: 201, body: draft });
  }).as(`${kind}CreateAnnouncement`);
  cy.intercept(
    'POST',
    `**/api/organizations/${organizationId}/announcements/announcement-a/publish`,
    (req) => {
      const currentDraft = draft!;
      published = {
        ...currentDraft,
        announcement_id: 'announcement-a',
        status: 'published',
        publication_version: 1,
        published_by_user_id: 'owner-a',
        published_at: createdAt,
        eligible_recipient_count: 3,
        delivered_count: 2,
        suppressed_by_preference_count: 1,
        unresolved_recipient_count: 0,
      };
      draft = null;
      req.reply({
        statusCode: 201,
        body: {
          id: 'publication-a',
          announcement_id: 'announcement-a',
          organization_id: organizationId,
          publication_version: 1,
          announcement_revision: 1,
          title: published.title,
          body: published.body,
          audience_type: published.audience_type,
          team_id: published.team_id,
          published_by_user_id: 'owner-a',
          published_at: createdAt,
          eligible_recipient_count: 3,
          delivered_count: 2,
          suppressed_by_preference_count: 1,
          unresolved_recipient_count: 0,
        },
      });
    },
  ).as(`${kind}PublishAnnouncement`);

  return { organizationId, basePath, audienceType };
}

describe('Block 3B shared organization announcements', () => {
  (['school', 'club'] as const).forEach((kind) => {
    it(`creates and explicitly publishes a ${kind} announcement`, () => {
      const { organizationId, basePath, audienceType } = stubAnnouncements(kind);
      cy.viewport(kind === 'school' ? 1280 : 390, kind === 'school' ? 900 : 844);
      cy.visitWithAuth(`${basePath}/${organizationId}/announcements`);
      cy.get('[data-test=announcement-title]').type(`${kind} training update`);
      cy.get('[data-test=announcement-body]').type('Meet at the main ground at 17:00.');
      if (audienceType === 'team') {
        cy.get('[data-test=announcement-audience]').select('team');
        cy.get('[data-test=announcement-team]').select('team-a');
        cy.get('[aria-label="Announcement preview"]').should('contain.text', 'First XI');
      } else {
        cy.get('[aria-label="Announcement preview"]').should('contain.text', `Whole ${kind}`);
      }
      cy.get('[data-test=save-announcement]').click();
      cy.wait(`@${kind}CreateAnnouncement`);
      cy.contains('No notifications were sent').should('be.visible');
      cy.contains(`${kind} training update`).should('be.visible');
      cy.window().then((win) => cy.stub(win, 'confirm').returns(true));
      cy.get('[data-test=publish-announcement]').click();
      cy.wait(`@${kind}PublishAnnouncement`);
      cy.contains('Published version 1: 2 delivered, 1 suppressed.').should('be.visible');
      cy.contains('Version 1').should('be.visible');
      cy.contains('Delivered').parent().should('contain.text', '2');
      cy.contains('Suppressed').parent().should('contain.text', '1');
      cy.contains('Reply').should('not.exist');
    });
  });
});

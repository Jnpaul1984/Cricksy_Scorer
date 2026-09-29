type OrganizationKind = 'school' | 'club';

const createdAt = '2026-09-29T15:00:00Z';
const categories = [
  'organization_announcement',
  'team_announcement',
  'event',
  'selection',
  'availability_reminder',
] as const;

function stubNotificationInbox(kind: OrganizationKind) {
  const organizationId = `${kind}-notifications`;
  const basePath = kind === 'school' ? '/schools' : '/clubs';
  const kindLabel = kind === 'school' ? 'School' : 'Club';
  let revoked = false;
  let readAt: string | null = null;
  const preferences = Object.fromEntries(categories.map((category) => [category, true]));

  cy.intercept('GET', `**/api/organizations/${organizationId}`, {
    id: organizationId,
    name: `${kindLabel} Communications`,
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
    capabilities: ['organization_notifications'],
    excluded_capabilities: [],
    created_at: createdAt,
    updated_at: createdAt,
  });
  cy.intercept('GET', `**/api/organizations/${organizationId}/notifications?*`, (req) => {
    if (revoked) {
      req.reply({ statusCode: 403, body: { detail: 'membership revoked' } });
      return;
    }
    const category = req.query.category;
    const unreadOnly = req.query.unread_only === 'true';
    const matches = (!category || category === 'event') && (!unreadOnly || readAt === null);
    const items = matches
      ? [
          {
            id: 'notification-a',
            organization_id: organizationId,
            recipient_user_id: 'owner-a',
            category: 'event',
            source_type: 'organization_event',
            source_id: 'event-a',
            source_version: '1',
            source_key: 'event:event-a:update',
            idempotency_key: 'event:event-a:update:owner-a',
            title: `${kindLabel} training updated`,
            summary: 'Training starts at 17:00 at the main ground.',
            origin: 'actor',
            actor_user_id: 'coach-a',
            created_at: createdAt,
            read_at: readAt,
          },
        ]
      : [];
    req.reply({ items, total: items.length, limit: 20, offset: 0 });
  }).as(`${kind}Inbox`);
  cy.intercept(
    'GET',
    `**/api/organizations/${organizationId}/notifications/unread-count`,
    (req) => {
      if (revoked) {
        req.reply({ statusCode: 403, body: { detail: 'membership revoked' } });
        return;
      }
      req.reply({ unread_count: readAt ? 0 : 1 });
    },
  ).as(`${kind}UnreadCount`);
  cy.intercept('GET', `**/api/organizations/${organizationId}/notifications/preferences`, (req) => {
    if (revoked) {
      req.reply({ statusCode: 403, body: { detail: 'membership revoked' } });
      return;
    }
    req.reply({
      items: categories.map((category) => ({
        organization_id: organizationId,
        user_id: 'owner-a',
        category,
        enabled: preferences[category],
        created_at: null,
        updated_at: null,
      })),
    });
  }).as(`${kind}Preferences`);
  cy.intercept(
    'POST',
    `**/api/organizations/${organizationId}/notifications/notification-a/read`,
    (req) => {
      readAt = '2026-09-29T16:00:00Z';
      req.reply({
        id: 'notification-a',
        organization_id: organizationId,
        recipient_user_id: 'owner-a',
        category: 'event',
        source_type: 'organization_event',
        source_id: 'event-a',
        source_version: '1',
        source_key: 'event:event-a:update',
        idempotency_key: 'event:event-a:update:owner-a',
        title: `${kindLabel} training updated`,
        summary: 'Training starts at 17:00 at the main ground.',
        origin: 'actor',
        actor_user_id: 'coach-a',
        created_at: createdAt,
        read_at: readAt,
      });
    },
  ).as(`${kind}MarkRead`);
  cy.intercept(
    'PATCH',
    `**/api/organizations/${organizationId}/notifications/preferences/event`,
    (req) => {
      preferences.event = Boolean(req.body.enabled);
      req.reply({
        organization_id: organizationId,
        user_id: 'owner-a',
        category: 'event',
        enabled: preferences.event,
        created_at: createdAt,
        updated_at: createdAt,
      });
    },
  ).as(`${kind}UpdatePreference`);

  return {
    organizationId,
    basePath,
    revoke: () => {
      revoked = true;
    },
  };
}

describe('Block 3D shared organization notification inbox', () => {
  (['school', 'club'] as const).forEach((kind) => {
    it(`uses the recipient-owned ${kind} inbox on a mobile viewport`, () => {
      const { organizationId, basePath, revoke } = stubNotificationInbox(kind);
      cy.viewport(390, 844);
      cy.visitWithAuth(`${basePath}/${organizationId}/notifications`);
      cy.wait(`@${kind}UnreadCount`).then((interception) => {
        expect(interception.response?.body).to.deep.equal({ unread_count: 1 });
      });

      cy.get('[data-test=organization-notifications-link]').should('contain.text', 'Notifications');
      cy.get('[data-test=notification-unread-count]')
        .should('contain.text', '1')
        .and('have.attr', 'aria-label', '1 unread notifications');
      cy.get('[data-test=notification-notification-a]')
        .should('contain.text', `${kind === 'school' ? 'School' : 'Club'} training updated`)
        .and('have.attr', 'aria-label')
        .and('contain', 'Unread notification');
      cy.contains('Announcements remain authored').should('be.visible');

      cy.get('[data-test=notification-status-filter]').select('true');
      cy.get('[data-test=notification-category-filter]').select('event');
      cy.get('[data-test=notification-notification-a]').should('be.visible');
      cy.get('[data-test=notification-status-filter]').select('false');
      cy.get('[data-test=mark-read-notification-a]').click();
      cy.wait(`@${kind}MarkRead`);
      cy.get('[data-test=notification-read-state]').should('contain.text', 'Read');
      cy.get('[data-test=notification-unread-count]').should('not.exist');

      cy.get('[data-test=preference-event]').uncheck();
      cy.wait(`@${kind}UpdatePreference`);
      cy.contains('preference updated for future deliveries').should('be.visible');
      cy.contains('does not restore notifications that were previously suppressed').should(
        'be.visible',
      );
      cy.document().then((document) => {
        expect(document.documentElement.scrollWidth).to.be.at.most(
          document.documentElement.clientWidth,
        );
      });

      cy.then(() => revoke());
      cy.get('[data-test=refresh-notifications]').click();
      cy.wait(`@${kind}Inbox`);
      cy.wait(`@${kind}Preferences`);
      cy.get('[data-test=notification-notification-a]').should('not.exist');
      cy.get('[data-test=notification-unread-count]').should('not.exist');
      cy.get('[data-test=preference-event]').should('not.exist');
      cy.contains('Loading notifications…').should('not.exist');
      cy.contains('Loading notification preferences…').should('not.exist');
      cy.contains('Notification inbox refreshed.').should('not.exist');
      cy.contains('membership revoked').should('not.exist');
      cy.get('[role=alert]').should('contain.text', 'do not have permission');
    });
  });
});

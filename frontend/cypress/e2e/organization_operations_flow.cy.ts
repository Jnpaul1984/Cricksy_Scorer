type OrganizationKind = 'school' | 'club';
type AvailabilityState = 'available' | 'unavailable' | 'maybe';
type AttendanceState = 'present' | 'absent' | 'excused';

const startedAt = '2020-06-01T10:00:00Z';
const createdAt = '2020-01-01T00:00:00Z';

function stubOperations(
  kind: OrganizationKind,
  role = 'owner',
  suffix = 'operations',
  eventInitiallyCreated = false,
) {
  const organizationId = `${kind}-${suffix}`;
  const basePath = kind === 'school' ? '/schools' : '/clubs';
  const kindLabel = kind === 'school' ? 'School' : 'Club';
  const event = {
    id: 'event-training',
    organization_id: organizationId,
    event_type: 'training',
    title: `${kindLabel} training`,
    description: null,
    start_at: startedAt,
    end_at: null,
    location: 'Main Ground',
    participant_scope: 'organization',
    team_ids: [],
    roster_membership_ids: [],
    status: 'scheduled',
    created_by_user_id: 'actor-a',
    updated_by_user_id: 'actor-a',
    cancelled_by_user_id: null,
    cancelled_at: null,
    created_at: createdAt,
    updated_at: createdAt,
  };
  const players = ['Asha Able', 'Ben Baker', 'Cara Cole', 'Dev Das'].map((player_name, index) => ({
    id: `player-${index + 1}`,
    organization_id: organizationId,
    player_profile_id: `profile-${index + 1}`,
    player_name,
    status: 'active',
    student_identifier: null,
    year_group: null,
    created_by_user_id: 'actor-a',
    created_at: createdAt,
    updated_at: createdAt,
  }));
  const team = {
    id: 'team-a',
    organization_id: organizationId,
    name: 'First XI',
    status: 'active',
    home_ground: null,
    season: '2026',
    owner_user_id: 'actor-a',
    coach_user_id: null,
    coach_name: null,
    created_at: createdAt,
    updated_at: createdAt,
  };
  let eventCreated = eventInitiallyCreated;
  const availability: Record<string, AvailabilityState> = {};
  const attendance: Record<string, AttendanceState> = {};

  cy.intercept('GET', `**/api/organizations/${organizationId}`, {
    id: organizationId,
    name: `${kindLabel} Operations`,
    organization_type: kind,
    status: 'active',
    membership_role: role,
    created_by_user_id: 'actor-a',
    created_at: createdAt,
    updated_at: createdAt,
  });
  cy.intercept('GET', `**/api/organizations/${organizationId}/me`, {
    id: 'membership-a',
    organization_id: organizationId,
    user_id: 'actor-a',
    role,
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
    capabilities: [
      'organization_events',
      'organization_availability',
      'organization_attendance',
      'organization_notifications',
    ],
    excluded_capabilities: [],
    created_at: createdAt,
    updated_at: createdAt,
  });
  cy.intercept('GET', `**/api/organizations/${organizationId}/notifications/unread-count`, {
    unread_count: 0,
  });
  cy.intercept('GET', `**/api/organizations/${organizationId}/teams`, [team]);
  cy.intercept('GET', `**/api/organizations/${organizationId}/players?status=active`, players);
  cy.intercept('GET', `**/api/organizations/${organizationId}/events*`, (req) => {
    req.reply({
      items: eventCreated ? [event] : [],
      total: eventCreated ? 1 : 0,
      limit: 100,
      offset: 0,
    });
  });
  cy.intercept('GET', `**/api/organizations/${organizationId}/calendar*`, (req) => {
    req.reply({
      items: eventCreated
        ? [
            {
              source_type: 'organization_event',
              source_id: event.id,
              title: event.title,
              start_at: event.start_at,
              end_at: null,
              location: event.location,
              status: event.status,
              event_type: 'training',
              participant_scope: 'organization',
              team_ids: [],
              game_id: null,
              competition_id: null,
            },
          ]
        : [],
      total: eventCreated ? 1 : 0,
      limit: 100,
      offset: 0,
    });
  });
  cy.intercept('POST', `**/api/organizations/${organizationId}/events`, (req) => {
    eventCreated = true;
    event.title = req.body.title;
    req.reply({ statusCode: 201, body: event });
  }).as(`${kind}CreateEvent`);
  cy.intercept(
    'POST',
    `**/api/organizations/${organizationId}/events/${event.id}/cancel`,
    (req) => {
      event.status = 'cancelled';
      event.cancelled_at = new Date().toISOString();
      req.reply(event);
    },
  ).as(`${kind}CancelEvent`);
  cy.intercept(
    'POST',
    `**/api/organizations/${organizationId}/events/${event.id}/notifications`,
    (req) => {
      req.reply({
        source_type: 'organization_event',
        source_id: event.id,
        source_version: event.updated_at,
        notification_type: req.body.notification_type,
        safe_user_recipient_count: 2,
        delivered_count: 1,
        suppressed_by_preference_count: 1,
        unresolved_roster_recipient_count: players.length,
      });
    },
  ).as(`${kind}NotifyEvent`);
  cy.intercept('DELETE', `**/api/organizations/${organizationId}/events/${event.id}`, {
    statusCode: 409,
    body: { detail: 'Event cannot be deleted while retained operational history exists' },
  });
  cy.intercept(
    'GET',
    `**/api/organizations/${organizationId}/availability/event/${event.id}*`,
    (req) => {
      const rows = players.map((player) => ({
        roster_membership_id: player.id,
        player_profile_id: player.player_profile_id,
        player_name: player.player_name,
        team_ids: ['team-a'],
        eligible: true,
        state: availability[player.id] || null,
        recorded_by_user_id: availability[player.id] ? 'actor-a' : null,
        recorded_at: availability[player.id] ? createdAt : null,
        recorded_after_deadline: false,
      }));
      const counts = {
        available: rows.filter((row) => row.state === 'available').length,
        unavailable: rows.filter((row) => row.state === 'unavailable').length,
        maybe: rows.filter((row) => row.state === 'maybe').length,
        no_response: rows.filter((row) => row.state === null).length,
        total: rows.length,
      };
      req.reply({
        target: {
          target_type: 'event',
          target_id: event.id,
          title: event.title,
          starts_at: event.start_at,
          response_deadline: null,
          deadline_passed: false,
        },
        counts,
        players: rows,
        total: rows.length,
        limit: 500,
        offset: 0,
      });
    },
  );
  cy.intercept(
    'PUT',
    `**/api/organizations/${organizationId}/availability/event/${event.id}/players/*`,
    (req) => {
      const playerId = req.url.split('/').pop()!;
      availability[playerId] = req.body.state;
      req.reply({ statusCode: 200, body: {} });
    },
  );
  cy.intercept(
    'POST',
    `**/api/organizations/${organizationId}/availability/event/${event.id}/reminders`,
    {
      source_type: 'availability_target',
      source_id: 'availability-target-a',
      source_version: 'availability-version-a',
      target_type: 'event',
      no_response_count: 1,
      safe_user_recipient_count: 2,
      delivered_count: 1,
      suppressed_by_preference_count: 1,
      unresolved_roster_recipient_count: 1,
    },
  ).as(`${kind}AvailabilityReminder`);
  cy.intercept(
    'GET',
    `**/api/organizations/${organizationId}/attendance/events/${event.id}*`,
    (req) => {
      const rows = players.map((player) => ({
        roster_membership_id: player.id,
        player_profile_id: player.player_profile_id,
        player_name: player.player_name,
        team_ids: ['team-a'],
        eligible: true,
        state: attendance[player.id] || null,
        recorded_by_user_id: attendance[player.id] ? 'actor-a' : null,
        recorded_at: attendance[player.id] ? createdAt : null,
      }));
      const present = rows.filter((row) => row.state === 'present').length;
      const absent = rows.filter((row) => row.state === 'absent').length;
      req.reply({
        organization_id: organizationId,
        event_id: event.id,
        event_title: event.title,
        event_status: event.status,
        start_at: event.start_at,
        counts: {
          present,
          absent,
          excused: rows.filter((row) => row.state === 'excused').length,
          unmarked: rows.filter((row) => row.state === null).length,
          total: rows.length,
          attendance_percentage: present + absent ? (present / (present + absent)) * 100 : null,
        },
        players: rows,
        total: rows.length,
        limit: 500,
        offset: 0,
      });
    },
  );
  cy.intercept(
    'PUT',
    `**/api/organizations/${organizationId}/attendance/events/${event.id}/players/*`,
    (req) => {
      const playerId = req.url.split('/').pop()!;
      attendance[playerId] = req.body.state;
      req.reply({ statusCode: 200, body: {} });
    },
  );

  return { organizationId, basePath, event };
}

describe('Block 1 shared organization operations', () => {
  (['school', 'club'] as const).forEach((kind) => {
    it(`completes the ${kind} Event to Availability to Attendance journey`, () => {
      const { organizationId, basePath } = stubOperations(kind);
      cy.viewport(kind === 'school' ? 1280 : 390, kind === 'school' ? 900 : 844);
      cy.visitWithAuth(`${basePath}/${organizationId}/events`);
      cy.get('[data-test=event-title]').scrollIntoView().type('Started training');
      cy.get('[data-test=event-location]').type('Main Ground');
      cy.get('[data-test=event-start]').type('2020-06-01T10:00');
      cy.get('[data-test=save-event]').click();
      cy.wait(`@${kind}CreateEvent`);
      cy.contains('h4', 'Started training').should('be.visible');
      cy.contains('Participants').should('be.visible');
      cy.get('[data-test=notify-event-update-event-training]').click();
      cy.wait(`@${kind}NotifyEvent`)
        .its('request.body')
        .should('deep.equal', { notification_type: 'update' });
      cy.get('[data-test=event-notification-result-event-training]')
        .should('contain.text', 'Sent to 1 safe in-app User')
        .and('contain.text', '1 suppressed by preference')
        .and('contain.text', '4 roster participants are not directly reachable in-app');
      cy.contains('a', 'Availability').click();
      cy.get('[data-test=set-available-player-1]').click();
      cy.get('[data-test=set-unavailable-player-2]').click();
      cy.get('[data-test=set-maybe-player-3]').click();
      cy.get('[aria-label="Availability summary"]').within(() => {
        cy.contains('Available').parent().should('contain.text', '1');
        cy.contains('Unavailable').parent().should('contain.text', '1');
        cy.contains('Maybe').parent().should('contain.text', '1');
        cy.contains('No response').parent().should('contain.text', '1');
      });
      cy.get('[data-test=send-availability-reminder]').click();
      cy.wait(`@${kind}AvailabilityReminder`);
      cy.contains('Reminder sent to 1 staff User').should('be.visible');
      cy.contains('1 roster response is still outstanding').should('be.visible');
      cy.contains('a', 'Calendar').click();
      cy.contains('a', 'Attendance').click();
      cy.get('[data-test=set-present-player-1]').click();
      cy.get('[data-test=set-absent-player-2]').click();
      cy.get('[data-test=set-excused-player-3]').click();
      cy.get('[aria-label="Attendance summary"]').within(() => {
        cy.contains('Present').parent().should('contain.text', '1');
        cy.contains('Absent').parent().should('contain.text', '1');
        cy.contains('Excused').parent().should('contain.text', '1');
        cy.contains('Unmarked').parent().should('contain.text', '1');
      });
      cy.contains('Attendance:').parent().should('contain.text', '50%');
      cy.contains('a', 'Calendar').click();
      cy.window().then((win) => cy.stub(win, 'confirm').returns(true));
      cy.contains('button', 'Cancel').click();
      cy.wait(`@${kind}CancelEvent`);
      cy.get('[data-test=notify-event-cancellation-event-training]').click();
      cy.wait(`@${kind}NotifyEvent`)
        .its('request.body')
        .should('deep.equal', { notification_type: 'cancellation' });
      cy.contains('a', 'Attendance').click();
      cy.contains('Existing attendance remains visible').should('be.visible');
      cy.get('[data-test^=set-present]').should('not.exist');
    });
  });

  (['scorer', 'viewer'] as const).forEach((role) => {
    it(`keeps ${role} read-only and denies Attendance`, () => {
      const { organizationId } = stubOperations('school', role, `role-${role}`, true);
      cy.visitWithAuth(`/schools/${organizationId}/events`);
      cy.get('[data-test=event-form]').should('not.exist');
      cy.contains('button', 'Edit').should('not.exist');
      cy.contains('a', 'Attendance').should('not.exist');
      cy.contains('a', 'Availability').click();
      cy.contains('No response').should('be.visible');
      cy.get('[data-test^=set-available]').should('not.exist');
      cy.get('[data-test=availability-deadline]').should('not.exist');
      cy.visit(`/schools/${organizationId}/attendance/event-training`);
      cy.contains('Attendance is available only to organization Owners, Admins and Coaches.').should(
        'be.visible',
      );
      cy.get('[data-test^=set-present]').should('not.exist');
    });
  });

  it('does not let stale frontend authority bypass a backend denial', () => {
    const { organizationId } = stubOperations('school', 'owner');
    cy.intercept('POST', `**/api/organizations/${organizationId}/events`, {
      statusCode: 403,
      body: { detail: 'Membership role cannot manage organization events' },
    });
    cy.visitWithAuth(`/schools/${organizationId}/events`);
    cy.get('[data-test=event-title]').type('Denied training');
    cy.get('[data-test=event-location]').type('Main Ground');
    cy.get('[data-test=event-start]').type('2020-06-01T10:00');
    cy.get('[data-test=save-event]').click();
    cy.get('[role=alert]').should('contain.text', 'do not have permission');
    cy.contains('h4', 'Denied training').should('not.exist');
  });

  (
    [
      ['school', 'school'],
      ['club', 'club'],
      ['school', 'club'],
      ['club', 'school'],
    ] as const
  ).forEach(([fromKind, toKind]) => {
    it(`clears old data during a ${fromKind}-to-${toKind} organization switch`, () => {
      const first = stubOperations(fromKind, 'owner', 'switch-from');
      const second = stubOperations(toKind, 'owner', 'switch-to');
      cy.visitWithAuth(`${first.basePath}/${first.organizationId}/events`);
      cy.get('[data-test=event-title]').type('Old organization draft');
      cy.visit(`${second.basePath}/${second.organizationId}/events`);
      cy.contains(`${toKind === 'school' ? 'School' : 'Club'} Operations`).should('be.visible');
      cy.contains('Old organization draft').should('not.exist');
      cy.contains('No calendar entries yet.').should('be.visible');
    });
  });
});

import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref, type Ref } from 'vue';

import {
  organizationBasePath,
  organizationTerminology,
} from '@/composables/useOrganizationTerminology';
import { schoolContextKey, type SchoolContext } from '@/composables/useSchoolContext';
import * as schoolApi from '@/services/schoolAdminApi';
import type { FreeOrganizationType, SchoolMembershipRole } from '@/types/schoolAdmin';
import OrganizationEventsView from '@/views/school/OrganizationEventsView.vue';

vi.mock('@/services/schoolAdminApi');

function context(
  organizationType: FreeOrganizationType | Ref<FreeOrganizationType>,
  role: SchoolMembershipRole,
  organizationId: Ref<string> = ref(
    `${typeof organizationType === 'string' ? organizationType : organizationType.value}-a`,
  ),
): SchoolContext {
  const organizationTypeRef =
    typeof organizationType === 'string' ? ref(organizationType) : organizationType;
  const canManage = computed(() => ['owner', 'admin', 'coach'].includes(role));
  return {
    organizationId: computed(() => organizationId.value),
    organizationType: computed(() => organizationTypeRef.value),
    organizationBasePath: computed(() => organizationBasePath(organizationTypeRef.value)),
    terminology: computed(() => organizationTerminology(organizationTypeRef.value)),
    organization: ref(null),
    membership: ref({
      id: 'membership-a',
      organization_id: organizationId.value,
      user_id: role === 'coach' ? 'coach-a' : 'owner-a',
      role,
      status: 'active',
      created_by_user_id: null,
      created_at: '',
      updated_at: '',
    }),
    entitlement: ref(null),
    canManageTeams: canManage,
    canManageRosterMetadata: canManage,
    canManageRosterLifecycle: computed(() => ['owner', 'admin'].includes(role)),
    canManageTeamRoster: canManage,
    canImport: canManage,
    canCreateSchoolMatch: computed(() => role !== 'viewer'),
    canViewStatistics: computed(() => true),
    canViewFixturesResults: computed(() => true),
    canViewCompetitions: computed(() => true),
    canManageCompetitions: canManage,
    canDeleteCompetitions: computed(() => ['owner', 'admin'].includes(role)),
    canLinkFixtures: computed(() => role !== 'viewer'),
    canPublishScorecards: computed(() => role !== 'viewer'),
    canViewEvents: computed(() => true),
    canManageEvents: canManage,
    canViewAnnouncements: computed(() => true),
    canManageAnnouncements: canManage,
    canManageCommunity: canManage,
  };
}

function mountView(
  organizationType: FreeOrganizationType | Ref<FreeOrganizationType>,
  role: SchoolMembershipRole,
  organizationId: Ref<string> = ref(
    `${typeof organizationType === 'string' ? organizationType : organizationType.value}-a`,
  ),
) {
  const providedContext = context(organizationType, role, organizationId);
  const currentOrganizationType =
    typeof organizationType === 'string' ? organizationType : organizationType.value;
  providedContext.entitlement.value = {
    id: 'entitlement-a',
    organization_id: organizationId.value,
    plan_key: currentOrganizationType === 'club' ? 'club_free' : 'school_free',
    status: 'active',
    source: 'system',
    effective_from: '',
    effective_until: null,
    capabilities: ['organization_events', 'organization_availability', 'organization_attendance'],
    excluded_capabilities: [],
    created_at: '',
    updated_at: '',
  };
  return mount(OrganizationEventsView, {
    global: {
      provide: { [schoolContextKey as symbol]: providedContext },
      stubs: {
        RouterLink: { props: ['to'], template: '<a :href="String(to)"><slot /></a>' },
      },
    },
  });
}

describe('shared organization events view', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(schoolApi.listOrganizationEvents).mockResolvedValue({
      items: [],
      total: 0,
      limit: 100,
      offset: 0,
    });
    vi.mocked(schoolApi.getOrganizationCalendar).mockResolvedValue({
      items: [
        {
          source_type: 'fixture',
          source_id: 'fixture-a',
          title: 'First XI vs Second XI',
          start_at: '2099-04-01T14:00:00Z',
          end_at: null,
          location: 'Main Ground',
          status: 'scheduled',
          event_type: null,
          participant_scope: null,
          team_ids: ['team-a', 'team-b'],
          game_id: null,
          competition_id: 'competition-a',
        },
      ],
      total: 1,
      limit: 100,
      offset: 0,
    });
    vi.mocked(schoolApi.listSchoolTeams).mockResolvedValue([]);
    vi.mocked(schoolApi.listSchoolPlayers).mockResolvedValue([]);
  });

  it('creates a Club event through the shared organization API and keeps fixtures read-only', async () => {
    vi.mocked(schoolApi.createOrganizationEvent).mockResolvedValue({} as never);
    const wrapper = mountView('club', 'owner');
    await flushPromises();

    expect(wrapper.text()).toContain('Shared Club calendar');
    expect(wrapper.text()).toContain('First XI vs Second XI');
    expect(wrapper.text()).toContain('Cricket fixture');
    expect(wrapper.get('a').attributes('href')).toBe(
      '/clubs/club-a/availability/fixture/fixture-a',
    );
    expect(wrapper.findAll('button').map((button) => button.text())).not.toContain('Edit');

    await wrapper.get('[data-test="event-title"]').setValue('Club training');
    await wrapper.get('[data-test="event-location"]').setValue('Practice Nets');
    await wrapper.get('[data-test="event-start"]').setValue('2099-05-01T10:30');
    await wrapper.get('[data-test="save-event"]').trigger('submit');
    await flushPromises();

    expect(schoolApi.createOrganizationEvent).toHaveBeenCalledWith(
      'club-a',
      expect.objectContaining({
        event_type: 'training',
        title: 'Club training',
        location: 'Practice Nets',
        participant_scope: 'organization',
        team_ids: [],
        roster_membership_ids: [],
      }),
    );
  });

  it.each(['scorer', 'viewer'] as const)('keeps %s event access read-only', async (role) => {
    const wrapper = mountView('school', role);
    await flushPromises();
    expect(wrapper.text()).toContain('Shared School calendar');
    expect(wrapper.find('[data-test="event-form"]').exists()).toBe(false);
    expect(schoolApi.getOrganizationCalendar).toHaveBeenCalledWith('school-a', {
      includeCancelled: true,
      limit: 100,
    });
  });

  it('links an organization event to its private attendance register for staff', async () => {
    vi.mocked(schoolApi.getOrganizationCalendar).mockResolvedValue({
      items: [
        {
          source_type: 'organization_event',
          source_id: 'event-a',
          title: 'Training',
          start_at: '2020-04-01T14:00:00Z',
          end_at: null,
          location: 'Main Ground',
          status: 'scheduled',
          event_type: 'training',
          participant_scope: 'organization',
          team_ids: [],
          game_id: null,
          competition_id: null,
        },
      ],
      total: 1,
      limit: 100,
      offset: 0,
    });
    const wrapper = mountView('school', 'coach');
    await flushPromises();

    const attendanceLink = wrapper.get('.attendance-link');
    expect(attendanceLink.text()).toBe('Attendance');
    expect(attendanceLink.attributes('href')).toBe('/schools/school-a/attendance/event-a');
  });

  it('renders audiences and reports a retained-history delete conflict safely', async () => {
    const event = {
      id: 'event-a',
      organization_id: 'school-a',
      event_type: 'training' as const,
      title: 'First XI training',
      description: null,
      start_at: '2020-04-01T14:00:00Z',
      end_at: null,
      location: 'Main Ground',
      participant_scope: 'teams' as const,
      team_ids: ['team-a'],
      roster_membership_ids: [],
      status: 'scheduled' as const,
      created_by_user_id: 'owner-a',
      updated_by_user_id: 'owner-a',
      cancelled_by_user_id: null,
      cancelled_at: null,
      created_at: '2020-01-01T00:00:00Z',
      updated_at: '2020-01-01T00:00:00Z',
    };
    vi.mocked(schoolApi.listOrganizationEvents).mockResolvedValue({
      items: [event],
      total: 1,
      limit: 100,
      offset: 0,
    });
    vi.mocked(schoolApi.getOrganizationCalendar).mockResolvedValue({
      items: [
        {
          source_type: 'organization_event',
          source_id: event.id,
          title: event.title,
          start_at: event.start_at,
          end_at: null,
          location: event.location,
          status: 'scheduled',
          event_type: 'training',
          participant_scope: 'teams',
          team_ids: ['team-a'],
          game_id: null,
          competition_id: null,
        },
      ],
      total: 1,
      limit: 100,
      offset: 0,
    });
    vi.mocked(schoolApi.listSchoolTeams).mockResolvedValue([
      {
        id: 'team-a',
        organization_id: 'school-a',
        name: 'First XI',
        status: 'active',
        home_ground: null,
        season: null,
        owner_user_id: null,
        coach_user_id: null,
        coach_name: null,
        created_at: '',
        updated_at: '',
      },
    ]);
    vi.mocked(schoolApi.deleteOrganizationEvent).mockRejectedValue(
      Object.assign(new Error('Event cannot be deleted while retained attendance history exists'), {
        status: 409,
      }),
    );
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const wrapper = mountView('school', 'owner');
    await flushPromises();

    expect(wrapper.text()).toContain('Audience');
    expect(wrapper.text()).toContain('First XI');
    await wrapper.get('[data-test="delete-event-event-a"]').trigger('click');
    await flushPromises();
    expect(wrapper.get('[role="alert"]').text()).toContain('retained attendance history');
  });

  it('deletes a history-free event through the scoped backend contract', async () => {
    const event = {
      id: 'empty-event',
      organization_id: 'school-a',
      event_type: 'other' as const,
      title: 'One-off meeting',
      description: null,
      start_at: '2099-04-01T14:00:00Z',
      end_at: null,
      location: 'Library',
      participant_scope: 'organization' as const,
      team_ids: [],
      roster_membership_ids: [],
      status: 'scheduled' as const,
      created_by_user_id: 'owner-a',
      updated_by_user_id: 'owner-a',
      cancelled_by_user_id: null,
      cancelled_at: null,
      created_at: '',
      updated_at: '',
    };
    vi.mocked(schoolApi.listOrganizationEvents).mockResolvedValue({
      items: [event],
      total: 1,
      limit: 100,
      offset: 0,
    });
    vi.mocked(schoolApi.getOrganizationCalendar).mockResolvedValue({
      items: [
        {
          source_type: 'organization_event',
          source_id: event.id,
          title: event.title,
          start_at: event.start_at,
          end_at: null,
          location: event.location,
          status: 'scheduled',
          event_type: 'other',
          participant_scope: 'organization',
          team_ids: [],
          game_id: null,
          competition_id: null,
        },
      ],
      total: 1,
      limit: 100,
      offset: 0,
    });
    vi.mocked(schoolApi.deleteOrganizationEvent).mockResolvedValue(undefined);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const wrapper = mountView('school', 'owner');
    await flushPromises();
    await wrapper.get('[data-test="delete-event-empty-event"]').trigger('click');
    await flushPromises();
    expect(schoolApi.deleteOrganizationEvent).toHaveBeenCalledWith('school-a', 'empty-event');
    expect(wrapper.get('[role="status"]').text()).toContain('Event deleted.');
  });

  it('reports safe User delivery and unresolved roster recipients honestly', async () => {
    const event = {
      id: 'notify-event',
      organization_id: 'school-a',
      event_type: 'training' as const,
      title: 'Selection training',
      description: null,
      start_at: '2099-04-01T14:00:00Z',
      end_at: null,
      location: 'Main Ground',
      participant_scope: 'selected_players' as const,
      team_ids: [],
      roster_membership_ids: ['roster-a'],
      status: 'scheduled' as const,
      created_by_user_id: 'owner-a',
      updated_by_user_id: 'owner-a',
      cancelled_by_user_id: null,
      cancelled_at: null,
      created_at: '',
      updated_at: '2099-01-01T00:00:00Z',
    };
    vi.mocked(schoolApi.listOrganizationEvents).mockResolvedValue({
      items: [event],
      total: 1,
      limit: 100,
      offset: 0,
    });
    vi.mocked(schoolApi.getOrganizationCalendar).mockResolvedValue({
      items: [
        {
          source_type: 'organization_event',
          source_id: event.id,
          title: event.title,
          start_at: event.start_at,
          end_at: null,
          location: event.location,
          status: 'scheduled',
          event_type: 'training',
          participant_scope: 'selected_players',
          team_ids: [],
          game_id: null,
          competition_id: null,
        },
      ],
      total: 1,
      limit: 100,
      offset: 0,
    });
    let resolveNotification: (
      value: Awaited<ReturnType<typeof schoolApi.notifyOrganizationEvent>>,
    ) => void = () => undefined;
    vi.mocked(schoolApi.notifyOrganizationEvent).mockReturnValue(
      new Promise((resolve) => {
        resolveNotification = resolve;
      }),
    );
    const result = {
      source_type: 'organization_event',
      source_id: event.id,
      source_version: event.updated_at,
      notification_type: 'update',
      safe_user_recipient_count: 0,
      delivered_count: 0,
      suppressed_by_preference_count: 0,
      unresolved_roster_recipient_count: 1,
    } as const;
    const wrapper = mountView('school', 'coach');
    await flushPromises();
    const trigger = wrapper.get('[data-test="notify-event-update-notify-event"]');
    await trigger.trigger('click');
    await trigger.trigger('click');
    expect(schoolApi.notifyOrganizationEvent).toHaveBeenCalledTimes(1);
    resolveNotification(result);
    await flushPromises();

    expect(schoolApi.notifyOrganizationEvent).toHaveBeenCalledWith(
      'school-a',
      'notify-event',
      'update',
    );
    expect(wrapper.text()).toContain('Sent to 0 safe in-app Users');
    expect(wrapper.text()).toContain('1 roster participant');
    expect(wrapper.text()).toContain('not directly reachable in-app');
    expect(wrapper.text()).not.toContain('1 player notified');
  });

  it('does not show a Team workflow trigger to a Coach after Team reassignment', async () => {
    const event = {
      id: 'team-event',
      organization_id: 'school-a',
      event_type: 'training' as const,
      title: 'Team training',
      description: null,
      start_at: '2099-04-01T14:00:00Z',
      end_at: null,
      location: 'Main Ground',
      participant_scope: 'teams' as const,
      team_ids: ['team-a'],
      roster_membership_ids: [],
      status: 'scheduled' as const,
      created_by_user_id: 'owner-a',
      updated_by_user_id: 'owner-a',
      cancelled_by_user_id: null,
      cancelled_at: null,
      created_at: '',
      updated_at: '2099-01-01T00:00:00Z',
    };
    vi.mocked(schoolApi.listOrganizationEvents).mockResolvedValue({
      items: [event],
      total: 1,
      limit: 100,
      offset: 0,
    });
    vi.mocked(schoolApi.getOrganizationCalendar).mockResolvedValue({
      items: [
        {
          source_type: 'organization_event',
          source_id: event.id,
          title: event.title,
          start_at: event.start_at,
          end_at: null,
          location: event.location,
          status: 'scheduled',
          event_type: 'training',
          participant_scope: 'teams',
          team_ids: ['team-a'],
          game_id: null,
          competition_id: null,
        },
      ],
      total: 1,
      limit: 100,
      offset: 0,
    });
    vi.mocked(schoolApi.listSchoolTeams).mockResolvedValue([
      {
        id: 'team-a',
        organization_id: 'school-a',
        name: 'Reassigned XI',
        status: 'active',
        home_ground: null,
        season: null,
        owner_user_id: null,
        coach_user_id: 'coach-b',
        coach_name: 'Coach B',
        created_at: '',
        updated_at: '',
      },
    ]);
    const wrapper = mountView('school', 'coach');
    await flushPromises();
    expect(wrapper.find('[data-test="notify-event-update-team-event"]').exists()).toBe(false);
  });

  it('suppresses a stale calendar response after an organization switch', async () => {
    let resolveOld: (
      value: Awaited<ReturnType<typeof schoolApi.getOrganizationCalendar>>,
    ) => void = () => undefined;
    const oldRequest = new Promise<Awaited<ReturnType<typeof schoolApi.getOrganizationCalendar>>>(
      (resolve) => {
        resolveOld = resolve;
      },
    );
    vi.mocked(schoolApi.getOrganizationCalendar)
      .mockReturnValueOnce(oldRequest)
      .mockResolvedValueOnce({
        items: [
          {
            source_type: 'fixture',
            source_id: 'club-fixture',
            title: 'Club Fixture',
            start_at: '2099-04-01T14:00:00Z',
            end_at: null,
            location: 'Club Ground',
            status: 'scheduled',
            event_type: null,
            participant_scope: null,
            team_ids: [],
            game_id: null,
            competition_id: 'club-competition',
          },
        ],
        total: 1,
        limit: 100,
        offset: 0,
      });
    const organizationId = ref('school-a');
    const wrapper = mountView('school', 'viewer', organizationId);
    await wrapper.vm.$nextTick();
    organizationId.value = 'school-b';
    await flushPromises();
    expect(wrapper.text()).toContain('Club Fixture');
    resolveOld({ items: [], total: 0, limit: 100, offset: 0 });
    await flushPromises();
    expect(wrapper.text()).toContain('Club Fixture');
    expect(schoolApi.getOrganizationCalendar).toHaveBeenLastCalledWith('school-b', {
      includeCancelled: true,
      limit: 100,
    });
  });

  it.each([
    ['school', 'school'],
    ['club', 'club'],
  ] as const)(
    'suppresses a late notification result across a %s to %s organization switch',
    async (fromType, toType) => {
      const event = {
        id: 'notify-event',
        organization_id: `${fromType}-a`,
        event_type: 'training' as const,
        title: 'Training',
        description: null,
        start_at: '2099-04-01T14:00:00Z',
        end_at: null,
        location: 'Main Ground',
        participant_scope: 'organization' as const,
        team_ids: [],
        roster_membership_ids: [],
        status: 'scheduled' as const,
        created_by_user_id: 'owner-a',
        updated_by_user_id: 'owner-a',
        cancelled_by_user_id: null,
        cancelled_at: null,
        created_at: '',
        updated_at: '2099-01-01T00:00:00Z',
      };
      vi.mocked(schoolApi.listOrganizationEvents).mockResolvedValue({
        items: [event],
        total: 1,
        limit: 100,
        offset: 0,
      });
      vi.mocked(schoolApi.getOrganizationCalendar).mockResolvedValue({
        items: [
          {
            source_type: 'organization_event',
            source_id: event.id,
            title: event.title,
            start_at: event.start_at,
            end_at: null,
            location: event.location,
            status: 'scheduled',
            event_type: 'training',
            participant_scope: 'organization',
            team_ids: [],
            game_id: null,
            competition_id: null,
          },
        ],
        total: 1,
        limit: 100,
        offset: 0,
      });
      let resolveNotification: (
        value: Awaited<ReturnType<typeof schoolApi.notifyOrganizationEvent>>,
      ) => void = () => undefined;
      vi.mocked(schoolApi.notifyOrganizationEvent).mockReturnValue(
        new Promise((resolve) => {
          resolveNotification = resolve;
        }),
      );
      const organizationId = ref(`${fromType}-a`);
      const organizationType = ref<FreeOrganizationType>(fromType);
      const wrapper = mountView(organizationType, 'owner', organizationId);
      await flushPromises();
      await wrapper.get('[data-test="notify-event-update-notify-event"]').trigger('click');
      organizationId.value = `${toType}-b`;
      organizationType.value = toType;
      await flushPromises();
      resolveNotification({
        source_type: 'organization_event',
        source_id: event.id,
        source_version: event.updated_at,
        notification_type: 'update',
        safe_user_recipient_count: 1,
        delivered_count: 1,
        suppressed_by_preference_count: 0,
        unresolved_roster_recipient_count: 0,
      });
      await flushPromises();

      expect(wrapper.find('[data-test="event-notification-result-notify-event"]').exists()).toBe(
        false,
      );
    },
  );
});

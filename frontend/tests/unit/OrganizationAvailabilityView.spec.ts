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
import OrganizationAvailabilityView from '@/views/school/OrganizationAvailabilityView.vue';

const mocks = vi.hoisted(() => ({
  route: { params: { targetType: 'event', targetId: 'event-a' } },
}));

vi.mock('@/services/schoolAdminApi');
vi.mock('vue-router', () => ({
  useRoute: () => mocks.route,
  RouterLink: { props: ['to'], template: '<a :href="String(to)"><slot /></a>' },
}));

function context(
  role: SchoolMembershipRole,
  organizationId: Ref<string> = ref('school-a'),
  organizationType: Ref<FreeOrganizationType> = ref('school'),
): SchoolContext {
  const writable = computed(() => ['owner', 'admin', 'coach'].includes(role));
  return {
    organizationId: computed(() => organizationId.value),
    organizationType: computed(() => organizationType.value),
    organizationBasePath: computed(() => organizationBasePath(organizationType.value)),
    terminology: computed(() => organizationTerminology(organizationType.value)),
    organization: ref(null),
    membership: ref({
      id: 'membership-a',
      organization_id: 'school-a',
      user_id: 'actor-a',
      role,
      status: 'active',
      created_by_user_id: null,
      created_at: '',
      updated_at: '',
    }),
    entitlement: ref({
      id: 'entitlement-a',
      organization_id: 'school-a',
      plan_key: 'school_free',
      status: 'active',
      source: 'system',
      effective_from: '',
      effective_until: null,
      capabilities: ['organization_availability'],
      excluded_capabilities: [],
      created_at: '',
      updated_at: '',
    }),
    canManageTeams: writable,
    canManageRosterMetadata: writable,
    canManageRosterLifecycle: computed(() => ['owner', 'admin'].includes(role)),
    canManageTeamRoster: writable,
    canImport: writable,
    canCreateSchoolMatch: computed(() => role !== 'viewer'),
    canViewStatistics: computed(() => true),
    canViewFixturesResults: computed(() => true),
    canViewCompetitions: computed(() => true),
    canManageCompetitions: writable,
    canDeleteCompetitions: computed(() => ['owner', 'admin'].includes(role)),
    canLinkFixtures: computed(() => role !== 'viewer'),
    canPublishScorecards: computed(() => role !== 'viewer'),
    canViewEvents: computed(() => true),
    canManageEvents: writable,
    canViewAnnouncements: computed(() => true),
    canManageAnnouncements: writable,
    canManageCommunity: writable,
  };
}

const summary = {
  target: {
    target_type: 'event' as const,
    target_id: 'event-a',
    title: 'Training',
    starts_at: '2099-01-10T13:00:00Z',
    response_deadline: '2099-01-09T13:00:00Z',
    deadline_passed: false,
  },
  counts: { available: 1, unavailable: 0, maybe: 0, no_response: 1, total: 2 },
  players: [
    {
      roster_membership_id: 'player-a',
      player_profile_id: 'profile-a',
      player_name: 'Alice Able',
      team_ids: ['team-a'],
      eligible: true,
      state: 'available' as const,
      recorded_by_user_id: 'actor-a',
      recorded_at: '2099-01-01T10:00:00Z',
      recorded_after_deadline: false,
    },
    {
      roster_membership_id: 'player-b',
      player_profile_id: 'profile-b',
      player_name: 'Bob Baker',
      team_ids: [],
      eligible: true,
      state: null,
      recorded_by_user_id: null,
      recorded_at: null,
      recorded_after_deadline: false,
    },
  ],
  total: 2,
  limit: 500,
  offset: 0,
};

function mountView(
  role: SchoolMembershipRole,
  organizationId: Ref<string> = ref('school-a'),
  organizationType: Ref<FreeOrganizationType> = ref('school'),
) {
  return mount(OrganizationAvailabilityView, {
    global: {
      provide: { [schoolContextKey as symbol]: context(role, organizationId, organizationType) },
    },
  });
}

describe('shared organization availability view', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(schoolApi.getOrganizationAvailability).mockResolvedValue(summary);
    vi.mocked(schoolApi.listSchoolTeams).mockResolvedValue([
      {
        id: 'team-a',
        organization_id: 'school-a',
        name: 'First XI',
        home_ground: null,
        season: null,
        status: 'active',
        owner_user_id: null,
        coach_user_id: null,
        coach_name: null,
        created_at: '',
        updated_at: '',
      },
    ]);
  });

  it('shows counts, unanswered players and lets a coach record a structured state', async () => {
    vi.mocked(schoolApi.recordOrganizationPlayerAvailability).mockResolvedValue({} as never);
    const wrapper = mountView('coach');
    await flushPromises();

    expect(wrapper.text()).toContain('Shared School availability');
    expect(wrapper.text()).toContain('No response');
    expect(wrapper.text()).toContain('Bob Baker');
    await wrapper.get('[data-test="set-maybe-player-b"]').trigger('click');
    await flushPromises();

    expect(schoolApi.recordOrganizationPlayerAvailability).toHaveBeenCalledWith(
      'school-a',
      'event',
      'event-a',
      'player-b',
      'maybe',
    );
  });

  it.each(['scorer', 'viewer'] as const)('keeps %s availability read-only', async (role) => {
    const wrapper = mountView(role);
    await flushPromises();

    expect(wrapper.text()).toContain('Available');
    expect(wrapper.find('[data-test="availability-deadline"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="set-available-player-a"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="send-availability-reminder"]').exists()).toBe(false);
    expect(schoolApi.getOrganizationAvailability).toHaveBeenCalled();
  });

  it('sends a bounded staff reminder without implying player delivery or mutation', async () => {
    vi.mocked(schoolApi.sendOrganizationAvailabilityReminder).mockResolvedValue({
      source_type: 'availability_target',
      source_id: 'target-a',
      source_version: 'version-a',
      target_type: 'event',
      no_response_count: 1,
      safe_user_recipient_count: 2,
      delivered_count: 2,
      suppressed_by_preference_count: 0,
      unresolved_roster_recipient_count: 1,
    });
    const wrapper = mountView('coach');
    await flushPromises();
    await wrapper.get('[data-test="send-availability-reminder"]').trigger('click');
    await flushPromises();

    expect(schoolApi.sendOrganizationAvailabilityReminder).toHaveBeenCalledWith(
      'school-a',
      'event',
      'event-a',
    );
    expect(wrapper.text()).toContain('Reminder sent to 2 staff Users');
    expect(wrapper.text()).toContain('1 roster response is still outstanding');
    expect(wrapper.text()).toContain('not directly reachable in-app');
    expect(schoolApi.recordOrganizationPlayerAvailability).not.toHaveBeenCalled();
  });

  it('prevents rapid duplicate reminder delivery while the first request is pending', async () => {
    let resolveReminder: (
      value: Awaited<ReturnType<typeof schoolApi.sendOrganizationAvailabilityReminder>>,
    ) => void = () => undefined;
    vi.mocked(schoolApi.sendOrganizationAvailabilityReminder).mockReturnValue(
      new Promise((resolve) => {
        resolveReminder = resolve;
      }),
    );
    const wrapper = mountView('owner');
    await flushPromises();
    const button = wrapper.get('[data-test="send-availability-reminder"]');
    await button.trigger('click');
    await button.trigger('click');
    expect(schoolApi.sendOrganizationAvailabilityReminder).toHaveBeenCalledTimes(1);
    resolveReminder({
      source_type: 'availability_target',
      source_id: 'target-a',
      source_version: 'version-a',
      target_type: 'event',
      no_response_count: 1,
      safe_user_recipient_count: 1,
      delivered_count: 1,
      suppressed_by_preference_count: 0,
      unresolved_roster_recipient_count: 1,
    });
    await flushPromises();
  });

  it('applies state and Team filters to the shared API', async () => {
    const wrapper = mountView('owner');
    await flushPromises();
    await wrapper.get('[data-test="availability-filter"]').setValue('no_response');
    await wrapper.get('[data-test="availability-team-filter"]').setValue('team-a');
    await flushPromises();

    expect(schoolApi.getOrganizationAvailability).toHaveBeenLastCalledWith(
      'school-a',
      'event',
      'event-a',
      { state: 'no_response', teamId: 'team-a', limit: 500 },
    );
  });

  it('shows retained responses without mutation controls', async () => {
    vi.mocked(schoolApi.getOrganizationAvailability).mockResolvedValue({
      ...summary,
      players: [{ ...summary.players[0], eligible: false }],
      counts: { available: 1, unavailable: 0, maybe: 0, no_response: 0, total: 1 },
      total: 1,
    });
    const wrapper = mountView('owner');
    await flushPromises();

    expect(wrapper.text()).toContain('Retained response · no longer eligible to update');
    expect(wrapper.find('[data-test="set-available-player-a"]').exists()).toBe(false);
  });

  it('clears filters and suppresses a stale response when the organization changes', async () => {
    let resolveOld: (value: typeof summary) => void = () => undefined;
    const oldRequest = new Promise<typeof summary>((resolve) => {
      resolveOld = resolve;
    });
    vi.mocked(schoolApi.getOrganizationAvailability)
      .mockReturnValueOnce(oldRequest)
      .mockResolvedValueOnce({
        ...summary,
        target: { ...summary.target, title: 'New Club Training' },
        players: [{ ...summary.players[1], player_name: 'Club Player' }],
      });
    const organizationId = ref('school-a');
    const wrapper = mountView('owner', organizationId);
    await wrapper.vm.$nextTick();
    organizationId.value = 'club-b';
    await flushPromises();

    expect(wrapper.text()).toContain('New Club Training');
    expect(wrapper.text()).toContain('Club Player');
    resolveOld({ ...summary, target: { ...summary.target, title: 'Old School Training' } });
    await flushPromises();
    expect(wrapper.text()).not.toContain('Old School Training');
    expect(schoolApi.getOrganizationAvailability).toHaveBeenLastCalledWith(
      'club-b',
      'event',
      'event-a',
      { state: undefined, teamId: undefined, limit: 500 },
    );
  });

  it('suppresses a late reminder result across a School to Club switch', async () => {
    let resolveReminder: (
      value: Awaited<ReturnType<typeof schoolApi.sendOrganizationAvailabilityReminder>>,
    ) => void = () => undefined;
    vi.mocked(schoolApi.sendOrganizationAvailabilityReminder).mockReturnValue(
      new Promise((resolve) => {
        resolveReminder = resolve;
      }),
    );
    const organizationId = ref('school-a');
    const organizationType = ref<FreeOrganizationType>('school');
    const wrapper = mountView('owner', organizationId, organizationType);
    await flushPromises();
    await wrapper.get('[data-test="send-availability-reminder"]').trigger('click');
    organizationId.value = 'club-b';
    organizationType.value = 'club';
    await flushPromises();
    resolveReminder({
      source_type: 'availability_target',
      source_id: 'target-a',
      source_version: 'version-a',
      target_type: 'event',
      no_response_count: 1,
      safe_user_recipient_count: 1,
      delivered_count: 1,
      suppressed_by_preference_count: 0,
      unresolved_roster_recipient_count: 1,
    });
    await flushPromises();

    expect(wrapper.text()).not.toContain('Reminder sent to 1 staff User');
  });
});

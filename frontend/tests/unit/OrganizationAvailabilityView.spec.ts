import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';

import { organizationBasePath, organizationTerminology } from '@/composables/useOrganizationTerminology';
import { schoolContextKey, type SchoolContext } from '@/composables/useSchoolContext';
import * as schoolApi from '@/services/schoolAdminApi';
import type { SchoolMembershipRole } from '@/types/schoolAdmin';
import OrganizationAvailabilityView from '@/views/school/OrganizationAvailabilityView.vue';

const mocks = vi.hoisted(() => ({
  route: { params: { targetType: 'event', targetId: 'event-a' } },
}));

vi.mock('@/services/schoolAdminApi');
vi.mock('vue-router', () => ({
  useRoute: () => mocks.route,
  RouterLink: { props: ['to'], template: '<a :href="String(to)"><slot /></a>' },
}));

function context(role: SchoolMembershipRole): SchoolContext {
  const writable = computed(() => ['owner', 'admin', 'coach'].includes(role));
  return {
    organizationId: computed(() => 'school-a'),
    organizationType: computed(() => 'school'),
    organizationBasePath: computed(() => organizationBasePath('school')),
    terminology: computed(() => organizationTerminology('school')),
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

function mountView(role: SchoolMembershipRole) {
  return mount(OrganizationAvailabilityView, {
    global: { provide: { [schoolContextKey as symbol]: context(role) } },
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
    expect(schoolApi.getOrganizationAvailability).toHaveBeenCalled();
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
});

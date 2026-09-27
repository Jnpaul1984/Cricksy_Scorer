import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref, type Ref } from 'vue';

import {
  organizationBasePath,
  organizationTerminology,
} from '@/composables/useOrganizationTerminology';
import { schoolContextKey, type SchoolContext } from '@/composables/useSchoolContext';
import * as schoolApi from '@/services/schoolAdminApi';
import type { SchoolMembershipRole } from '@/types/schoolAdmin';
import OrganizationAttendanceView from '@/views/school/OrganizationAttendanceView.vue';

vi.mock('@/services/schoolAdminApi');
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { eventId: 'event-a' } }),
  RouterLink: { props: ['to'], template: '<a :href="String(to)"><slot /></a>' },
}));

function context(
  role: SchoolMembershipRole,
  organizationId: Ref<string> = ref('school-a'),
): SchoolContext {
  const writable = computed(() => ['owner', 'admin', 'coach'].includes(role));
  return {
    organizationId: computed(() => organizationId.value),
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
      capabilities: ['organization_attendance'],
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

const register = {
  organization_id: 'school-a',
  event_id: 'event-a',
  event_title: 'Training',
  event_status: 'scheduled',
  start_at: '2020-01-01T10:00:00Z',
  counts: {
    present: 1,
    absent: 0,
    excused: 0,
    unmarked: 1,
    total: 2,
    attendance_percentage: 100,
  },
  players: [
    {
      roster_membership_id: 'player-a',
      player_profile_id: 'profile-a',
      player_name: 'Alice Able',
      team_ids: ['team-a'],
      eligible: true,
      state: 'present' as const,
      recorded_by_user_id: 'actor-a',
      recorded_at: '2020-01-01T11:00:00Z',
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
    },
  ],
  total: 2,
  limit: 500,
  offset: 0,
};

function mountView(role: SchoolMembershipRole, organizationId: Ref<string> = ref('school-a')) {
  return mount(OrganizationAttendanceView, {
    global: { provide: { [schoolContextKey as symbol]: context(role, organizationId) } },
  });
}

describe('shared organization attendance view', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(schoolApi.getOrganizationAttendance).mockResolvedValue(register);
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

  it('shows the register, counts and lets a coach record a constrained state', async () => {
    vi.mocked(schoolApi.recordOrganizationPlayerAttendance).mockResolvedValue({} as never);
    const wrapper = mountView('coach');
    await flushPromises();

    expect(wrapper.text()).toContain('Private School attendance');
    expect(wrapper.text()).toContain('Unmarked');
    expect(wrapper.text()).toContain('Attendance: 100%');
    await wrapper.get('[data-test="set-absent-player-b"]').trigger('click');
    await flushPromises();
    expect(schoolApi.recordOrganizationPlayerAttendance).toHaveBeenCalledWith(
      'school-a',
      'event-a',
      'player-b',
      'absent',
    );
  });

  it.each(['scorer', 'viewer'] as const)('does not expose attendance to %s', async (role) => {
    const wrapper = mountView(role);
    await flushPromises();
    expect(wrapper.text()).toContain('Owners, Admins and Coaches');
    expect(schoolApi.getOrganizationAttendance).not.toHaveBeenCalled();
    expect(wrapper.find('[data-test="set-present-player-a"]').exists()).toBe(false);
  });

  it('applies state and Team filters', async () => {
    const wrapper = mountView('owner');
    await flushPromises();
    await wrapper.get('[data-test="attendance-filter"]').setValue('unmarked');
    await wrapper.get('[data-test="attendance-team-filter"]').setValue('team-a');
    await flushPromises();
    expect(schoolApi.getOrganizationAttendance).toHaveBeenLastCalledWith('school-a', 'event-a', {
      state: 'unmarked',
      teamId: 'team-a',
      limit: 500,
    });
  });

  it('shows a future-event restriction and exposes no mutation controls', async () => {
    vi.mocked(schoolApi.getOrganizationAttendance).mockResolvedValue({
      ...register,
      start_at: '2099-01-01T10:00:00Z',
    });
    const wrapper = mountView('coach');
    await flushPromises();

    expect(wrapper.get('[data-test="attendance-future-notice"]').text()).toContain(
      'cannot be recorded until the event starts',
    );
    expect(wrapper.find('[data-test="set-present-player-a"]').exists()).toBe(false);
  });

  it('suppresses old attendance data and resets filters on organization change', async () => {
    let resolveOld: (value: typeof register) => void = () => undefined;
    const oldRequest = new Promise<typeof register>((resolve) => {
      resolveOld = resolve;
    });
    vi.mocked(schoolApi.getOrganizationAttendance)
      .mockReturnValueOnce(oldRequest)
      .mockResolvedValueOnce({
        ...register,
        organization_id: 'club-b',
        event_title: 'Club Training',
        players: [{ ...register.players[1], player_name: 'Club Player' }],
      });
    const organizationId = ref('school-a');
    const wrapper = mountView('coach', organizationId);
    await wrapper.vm.$nextTick();
    organizationId.value = 'club-b';
    await flushPromises();

    expect(wrapper.text()).toContain('Club Training');
    expect(wrapper.text()).toContain('Club Player');
    resolveOld({ ...register, event_title: 'Old School Training' });
    await flushPromises();
    expect(wrapper.text()).not.toContain('Old School Training');
    expect(schoolApi.getOrganizationAttendance).toHaveBeenLastCalledWith('club-b', 'event-a', {
      state: undefined,
      teamId: undefined,
      limit: 500,
    });
  });
});

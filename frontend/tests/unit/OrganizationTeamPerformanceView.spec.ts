import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref, type Ref } from 'vue';

import {
  organizationBasePath,
  organizationTerminology,
} from '@/composables/useOrganizationTerminology';
import { schoolContextKey, type SchoolContext } from '@/composables/useSchoolContext';
import * as schoolApi from '@/services/schoolAdminApi';
import type {
  FreeOrganizationType,
  OrganizationTeamPerformance,
  SchoolMembershipRole,
  SchoolTeam,
} from '@/types/schoolAdmin';
import OrganizationTeamPerformanceView from '@/views/school/OrganizationTeamPerformanceView.vue';

vi.mock('@/services/schoolAdminApi');
vi.mock('vue-router', () => ({
  RouterLink: { props: ['to'], template: '<a :href="String(to)"><slot /></a>' },
}));

function team(id: string, organizationId: string, status: 'active' | 'archived' = 'active'): SchoolTeam {
  return {
    id,
    organization_id: organizationId,
    name: id === 'team-a' ? 'First XI' : 'Archive XI',
    status,
    home_ground: null,
    season: null,
    owner_user_id: null,
    coach_user_id: null,
    coach_name: null,
    created_at: '',
    updated_at: '',
  };
}

function performance(
  organizationId: string,
  teamId: string,
  runs = 19,
): OrganizationTeamPerformance {
  return {
    organization_id: organizationId,
    team_id: teamId,
    overs_limit: 20,
    completeness: 'unknown',
    batting: {
      team_runs: runs,
      bat_runs: runs,
      wides: 0,
      no_ball_penalties: 0,
      byes: 0,
      leg_byes: 0,
      wickets_lost: 0,
      legal_balls: 11,
      legal_dots: 1,
      fours: 1,
      sixes: 0,
      run_rate: 10.36,
      legal_dot_percentage: 9.09,
      runs_per_wicket: null,
    },
    bowling: {
      opposition_team_runs: 0,
      bowler_charged_runs: 0,
      wides: 0,
      no_ball_penalties: 0,
      byes: 0,
      leg_byes: 0,
      team_wickets: 0,
      bowler_credited_wickets: 0,
      legal_balls: 0,
      legal_dots: 0,
      team_concession_rate: null,
      bowling_economy: null,
      legal_dot_percentage: null,
    },
    coverage: {
      status: 'usable_recorded_data',
      eligible_games: 1,
      included_games: 1,
      usable_batting_innings: 1,
      usable_bowling_innings: 0,
      used_delivery_rows: 11,
      observed_delivery_rows: 11,
      excluded_games: 0,
      excluded_innings: 0,
      cohort_excluded_games: 0,
      cohort_exclusion_counts: {},
      no_ledger_games: 0,
      invalid_data_games: 0,
      invalid_data_innings: 0,
      warning_counts: {},
    },
  };
}

function schoolContext(
  organizationId: Ref<string>,
  role: Ref<SchoolMembershipRole>,
  organizationType: Ref<FreeOrganizationType> = ref('school'),
): SchoolContext {
  const staff = computed(() => ['owner', 'admin', 'coach'].includes(role.value));
  const always = computed(() => true);
  return {
    organizationId: computed(() => organizationId.value),
    organizationType: computed(() => organizationType.value),
    organizationBasePath: computed(() => organizationBasePath(organizationType.value)),
    terminology: computed(() => organizationTerminology(organizationType.value)),
    organization: ref(null),
    membership: ref(null),
    entitlement: ref(null),
    canManageTeams: staff,
    canManageRosterMetadata: staff,
    canManageRosterLifecycle: staff,
    canManageTeamRoster: staff,
    canImport: staff,
    canCreateSchoolMatch: staff,
    canViewStatistics: always,
    canViewFixturesResults: always,
    canViewCompetitions: always,
    canManageCompetitions: staff,
    canDeleteCompetitions: staff,
    canLinkFixtures: staff,
    canPublishScorecards: staff,
    canViewEvents: always,
    canManageEvents: staff,
    canViewAnnouncements: always,
    canManageAnnouncements: staff,
    canManageCommunity: staff,
  };
}

function mountView(organizationId: Ref<string>, role: Ref<SchoolMembershipRole> = ref('coach')) {
  return mount(OrganizationTeamPerformanceView, {
    global: {
      provide: {
        [schoolContextKey as symbol]: schoolContext(organizationId, role),
      },
      stubs: { RouterLink: true },
    },
  });
}

describe('organization Team Performance pilot view', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(schoolApi.listSchoolTeams).mockImplementation(async (organizationId) => [
      team('team-a', organizationId, 'archived'),
    ]);
    vi.mocked(schoolApi.getOrganizationTeamPerformance).mockImplementation(
      async (organizationId, teamId) => performance(organizationId, teamId),
    );
  });

  it('shows archived Team scope, recorded metrics, and coverage without player averages', async () => {
    const wrapper = mountView(ref('school-a'));
    await flushPromises();

    expect(wrapper.text()).toContain('First XI (archived)');
    expect(wrapper.text()).toContain('Based on recorded delivery data. Historical completeness has not been verified.');
    expect(wrapper.text()).toContain('11 (1.5)');
    expect(wrapper.text()).toContain('Team runs per wicket');
    expect(wrapper.text()).not.toContain('Player average');
    expect(wrapper.text()).toContain('Eligible / included games');

    await wrapper.get('input[aria-label="Overs limit"]').setValue(50);
    await flushPromises();
    expect(schoolApi.getOrganizationTeamPerformance).toHaveBeenLastCalledWith(
      'school-a',
      'team-a',
      50,
    );
  });

  it('ignores late results after switching organizations', async () => {
    let resolveOld: (value: OrganizationTeamPerformance) => void = () => undefined;
    let resolveCurrent: (value: OrganizationTeamPerformance) => void = () => undefined;
    vi.mocked(schoolApi.getOrganizationTeamPerformance).mockImplementation(
      (organizationId) =>
        new Promise((resolve) => {
          if (organizationId === 'school-a') resolveOld = resolve;
          else resolveCurrent = resolve;
        }),
    );
    const organizationId = ref('school-a');
    const wrapper = mountView(organizationId);
    await flushPromises();
    expect(schoolApi.getOrganizationTeamPerformance).toHaveBeenCalledTimes(1);

    organizationId.value = 'club-b';
    await flushPromises();
    expect(schoolApi.getOrganizationTeamPerformance).toHaveBeenCalledTimes(2);
    resolveCurrent(performance('club-b', 'team-b', 77));
    await flushPromises();
    expect(wrapper.text()).toContain('77');

    resolveOld(performance('school-a', 'team-a', 11));
    await flushPromises();
    expect(wrapper.text()).toContain('77');
    expect(wrapper.text()).not.toContain('11\n');
  });

  it('clears aggregates immediately when contextual staff access is lost', async () => {
    const role = ref<SchoolMembershipRole>('coach');
    const wrapper = mountView(ref('school-a'), role);
    await flushPromises();
    expect(wrapper.text()).toContain('19');

    role.value = 'scorer';
    await flushPromises();
    expect(wrapper.text()).toContain('unavailable for this organization');
    expect(wrapper.text()).not.toContain('Team batting');
  });

  it('distinguishes an empty eligible cohort from a too-large request', async () => {
    vi.mocked(schoolApi.getOrganizationTeamPerformance).mockResolvedValue({
      ...performance('school-a', 'team-a'),
      coverage: {
        ...performance('school-a', 'team-a').coverage,
        status: 'no_eligible_games',
        eligible_games: 0,
        included_games: 0,
        usable_batting_innings: 0,
        used_delivery_rows: 0,
      },
    });
    const emptyWrapper = mountView(ref('school-a'));
    await flushPromises();
    expect(emptyWrapper.text()).toContain('No eligible official completed');
    expect(emptyWrapper.text()).not.toContain('Team batting');
    emptyWrapper.unmount();

    const tooLarge = Object.assign(new Error('scope too large'), { status: 413 });
    vi.mocked(schoolApi.getOrganizationTeamPerformance).mockRejectedValue(tooLarge);
    const oversizedWrapper = mountView(ref('school-a'));
    await flushPromises();
    expect(oversizedWrapper.text()).toContain('complete recorded-history scope is too large');
    expect(oversizedWrapper.text()).not.toContain('Team batting');
  });
});

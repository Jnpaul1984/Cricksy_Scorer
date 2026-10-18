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
  OrganizationTeamPerformanceTeamOption,
  SchoolMembershipRole,
} from '@/types/schoolAdmin';
import OrganizationTeamPerformanceView from '@/views/school/OrganizationTeamPerformanceView.vue';

vi.mock('@/services/schoolAdminApi');
vi.mock('vue-router', () => ({
  RouterLink: { props: ['to'], template: '<a :href="String(to)"><slot /></a>' },
}));

function team(
  id: string,
  _organizationId: string,
  status: 'active' | 'archived' = 'active',
): OrganizationTeamPerformanceTeamOption {
  return {
    id,
    name: id === 'team-a' ? 'First XI' : 'Archive XI',
    status,
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
    vi.mocked(schoolApi.listOrganizationTeamPerformanceTeams).mockImplementation(
      async (organizationId) => [team('team-a', organizationId, 'archived')],
    );
    vi.mocked(schoolApi.getOrganizationTeamPerformance).mockImplementation(
      async (organizationId, teamId) => performance(organizationId, teamId),
    );
  });

  it('shows archived Team scope, recorded metrics, and coverage without player averages', async () => {
    const wrapper = mountView(ref('school-a'));
    await flushPromises();

    expect(schoolApi.listOrganizationTeamPerformanceTeams).toHaveBeenCalledWith('school-a');
    expect(schoolApi.listSchoolTeams).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain('First XI (archived)');
    expect(wrapper.text()).toContain(
      'Based on recorded delivery data. Historical completeness has not been verified.',
    );
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

  it('ignores rejected stale analytics after old team selection loads and scope changes', async () => {
    let resolveOldTeams: (teams: OrganizationTeamPerformanceTeamOption[]) => void = () => undefined;
    let rejectOldAnalytics: (error: Error) => void = () => undefined;
    vi.mocked(schoolApi.listOrganizationTeamPerformanceTeams).mockImplementation(
      async (organizationId) => {
        if (organizationId === 'school-a') {
          return new Promise<OrganizationTeamPerformanceTeamOption[]>((resolve) => {
            resolveOldTeams = resolve;
          });
        }
        return [team('team-b', organizationId)];
      },
    );
    vi.mocked(schoolApi.getOrganizationTeamPerformance).mockImplementation((organizationId) => {
      if (organizationId === 'school-a') {
        return new Promise<OrganizationTeamPerformance>((_resolve, reject) => {
          rejectOldAnalytics = reject;
        });
      }
      return Promise.resolve(performance(organizationId, 'team-b', 77));
    });
    const organizationId = ref('school-a');
    const wrapper = mountView(organizationId);
    await flushPromises();
    expect(schoolApi.listOrganizationTeamPerformanceTeams).toHaveBeenCalledWith('school-a');
    resolveOldTeams([team('team-a', 'school-a')]);
    await flushPromises();
    expect(schoolApi.getOrganizationTeamPerformance).toHaveBeenCalledWith('school-a', 'team-a', 20);

    organizationId.value = 'club-b';
    await flushPromises();
    expect(schoolApi.getOrganizationTeamPerformance).toHaveBeenCalledWith('club-b', 'team-b', 20);
    expect(wrapper.text()).toContain('77');

    rejectOldAnalytics(Object.assign(new Error('stale analytics'), { status: 500 }));
    await flushPromises();
    expect(wrapper.text()).toContain('77');
    expect(wrapper.text()).not.toContain('unavailable for this organization');
    expect(wrapper.text()).not.toContain('stale analytics');
  });

  it('ignores a rejected stale team list after switching organizations', async () => {
    let rejectOldTeams: (error: Error) => void = () => undefined;
    vi.mocked(schoolApi.listOrganizationTeamPerformanceTeams).mockImplementation(
      async (organizationId) => {
        if (organizationId === 'school-a') {
          return new Promise<OrganizationTeamPerformanceTeamOption[]>((_resolve, reject) => {
            rejectOldTeams = reject;
          });
        }
        return [team('team-b', organizationId)];
      },
    );
    vi.mocked(schoolApi.getOrganizationTeamPerformance).mockResolvedValue(
      performance('club-b', 'team-b', 77),
    );

    const organizationId = ref('school-a');
    const wrapper = mountView(organizationId);
    await flushPromises();
    expect(schoolApi.listOrganizationTeamPerformanceTeams).toHaveBeenCalledWith('school-a');

    organizationId.value = 'club-b';
    await flushPromises();
    expect(wrapper.text()).toContain('77');

    rejectOldTeams(Object.assign(new Error('stale team load'), { status: 404 }));
    await flushPromises();
    expect(wrapper.text()).toContain('77');
    expect(wrapper.text()).not.toContain('unavailable for this organization');
    expect(wrapper.text()).not.toContain('stale team load');
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

  it.each([
    ['batting', 0, 1, 'No usable batting data.'],
    ['bowling', 1, 0, 'No usable bowling data.'],
  ])(
    'does not show an empty %s card when only the other perspective is usable',
    async (_label, usableBatting, usableBowling, unavailableText) => {
      vi.mocked(schoolApi.getOrganizationTeamPerformance).mockResolvedValue({
        ...performance('school-a', 'team-a'),
        coverage: {
          ...performance('school-a', 'team-a').coverage,
          status: 'usable_with_exclusions',
          usable_batting_innings: usableBatting as number,
          usable_bowling_innings: usableBowling as number,
          warning_counts: { invalid_numeric_field: 1 },
        },
      });
      const wrapper = mountView(ref('school-a'));
      await flushPromises();

      if (usableBatting === 0)
        expect(wrapper.find('[aria-labelledby="batting-heading"]').exists()).toBe(false);
      else expect(wrapper.find('[aria-labelledby="batting-heading"]').exists()).toBe(true);
      if (usableBowling === 0)
        expect(wrapper.find('[aria-labelledby="bowling-heading"]').exists()).toBe(false);
      else expect(wrapper.find('[aria-labelledby="bowling-heading"]').exists()).toBe(true);
      expect(wrapper.text()).toContain(unavailableText as string);
      expect(wrapper.text()).toContain('validation warnings');
      expect(wrapper.text()).not.toContain('outside the selected format');
    },
  );

  it('reports ordinary cohort exclusions without calling them validation warnings', async () => {
    vi.mocked(schoolApi.getOrganizationTeamPerformance).mockResolvedValue({
      ...performance('school-a', 'team-a'),
      coverage: {
        ...performance('school-a', 'team-a').coverage,
        status: 'usable_with_exclusions',
        cohort_excluded_games: 3,
        cohort_exclusion_counts: { overs_limit_mismatch: 3 },
      },
    });
    const wrapper = mountView(ref('school-a'));
    await flushPromises();

    expect(wrapper.text()).toContain(
      'Games outside the selected format or cohort are counted separately.',
    );
    expect(wrapper.text()).not.toContain('validation warnings');
    expect(wrapper.text()).not.toContain('Recorded-data validation warnings');
  });

  it.each([403, 404])('clears aggregates after a %i denied request', async (status) => {
    const wrapper = mountView(ref('school-a'));
    await flushPromises();
    expect(wrapper.text()).toContain('Team batting');

    const denied = Object.assign(new Error('denied'), { status });
    vi.mocked(schoolApi.getOrganizationTeamPerformance).mockRejectedValue(denied);
    await wrapper.get('input[aria-label="Overs limit"]').setValue(30);
    await flushPromises();
    expect(wrapper.text()).toContain('unavailable for this organization');
    expect(wrapper.text()).not.toContain('Team batting');
    wrapper.unmount();
  });

  it('handles an eligible cohort with no usable ledger', async () => {
    vi.mocked(schoolApi.getOrganizationTeamPerformance).mockResolvedValue({
      ...performance('school-a', 'team-a'),
      coverage: {
        ...performance('school-a', 'team-a').coverage,
        status: 'no_usable_ledger',
        included_games: 0,
        usable_batting_innings: 0,
        usable_bowling_innings: 0,
        used_delivery_rows: 0,
        no_ledger_games: 1,
        warning_counts: { invalid_numeric_field: 1 },
      },
    });
    const noLedger = mountView(ref('school-a'));
    await flushPromises();
    expect(noLedger.text()).toContain(
      'Eligible games exist, but no usable batting or bowling delivery ledger is available.',
    );
    expect(noLedger.text()).toContain(
      'Recorded-data validation warnings are listed above; data availability is reported separately.',
    );
    expect(noLedger.text()).not.toContain('Usable recorded data is shown');
    expect(noLedger.find('[aria-labelledby="batting-heading"]').exists()).toBe(false);
    expect(noLedger.find('[aria-labelledby="bowling-heading"]').exists()).toBe(false);
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

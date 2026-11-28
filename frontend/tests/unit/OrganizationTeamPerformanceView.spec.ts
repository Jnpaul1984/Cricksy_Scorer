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
  OrganizationTeamRecentForm,
  OrganizationTeamPhaseAnalysis,
  OrganizationTeamCoachReport,
  OrganizationTeamPerformanceTeamOption,
  SchoolMembershipRole,
  SchoolMembership,
  SchoolOrganization,
  OrganizationTeamTrialStatus,
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

function form(
  state: 'ready' | 'not_ready' | 'data_unavailable' = 'ready',
): OrganizationTeamRecentForm {
  const sample = performance('school-a', 'team-a');
  return {
    readiness: {
      organization_id: 'school-a',
      team_id: 'team-a',
      as_of_date: '2026-05-01',
      required_history: 5,
      usable_prior_match_count: state === 'ready' ? 5 : 4,
      remaining_match_count: state === 'ready' ? 0 : 1,
      state,
      usable_batting_match_count: 5,
      usable_bowling_match_count: 5,
      exclusion_counts: { same_date_ambiguous: state === 'data_unavailable' ? 2 : 0 },
    },
    sample_size: state === 'ready' ? 5 : 0,
    completeness: 'unknown',
    recorded_delivery_rows: state === 'ready' ? 55 : 0,
    batting: state === 'ready' ? sample.batting : null,
    bowling: state === 'ready' ? sample.bowling : null,
    matches:
      state === 'ready'
        ? Array.from({ length: 5 }, (_, index) => ({
            ordinal: index + 1,
            played_date: `2026-04-0${index + 1}`,
            batting: sample.batting,
            bowling: sample.bowling,
            recorded_delivery_rows: 11,
          }))
        : [],
  };
}

function phase(
  state: 'ready' | 'not_ready' | 'data_unavailable' = 'ready',
): OrganizationTeamPhaseAnalysis {
  const sample = performance('school-a', 'team-a');
  return {
    readiness: form(state).readiness,
    sample_size: state === 'ready' ? 5 : 0,
    completeness: 'unknown',
    phase_unavailable_matches: 1,
    phases:
      state === 'ready'
        ? [
            {
              name: 'opening',
              start_over: 1,
              end_over: 5,
              batting_observed_matches: 4,
              bowling_observed_matches: 4,
              batting_unavailable_matches: 1,
              bowling_unavailable_matches: 1,
              batting_recorded_rows: 30,
              bowling_recorded_rows: 30,
              batting: sample.batting,
              bowling: sample.bowling,
            },
            {
              name: 'middle',
              start_over: 6,
              end_over: 20,
              batting_observed_matches: 0,
              bowling_observed_matches: 0,
              batting_unavailable_matches: 5,
              bowling_unavailable_matches: 5,
              batting_recorded_rows: 0,
              bowling_recorded_rows: 0,
              batting: null,
              bowling: null,
            },
            {
              name: 'closing',
              start_over: 21,
              end_over: 25,
              batting_observed_matches: 0,
              bowling_observed_matches: 0,
              batting_unavailable_matches: 5,
              bowling_unavailable_matches: 5,
              batting_recorded_rows: 0,
              bowling_recorded_rows: 0,
              batting: null,
              bowling: null,
            },
          ]
        : [],
  };
}

function report(
  state: 'ready' | 'not_ready' | 'data_unavailable' = 'ready',
): OrganizationTeamCoachReport {
  return {
    ...form(state),
    phase_unavailable_matches: state === 'ready' ? 1 : 0,
    phases: phase(state).phases,
    observations: [],
  };
}

function schoolContext(
  organizationId: Ref<string>,
  role: Ref<SchoolMembershipRole>,
  organizationType: Ref<FreeOrganizationType> = ref('school'),
  membershipStatus: Ref<SchoolMembership['status']> = ref('active'),
  organizationStatus: Ref<SchoolOrganization['status']> = ref('active'),
): SchoolContext {
  const staff = computed(() => ['owner', 'admin', 'coach'].includes(role.value));
  const always = computed(() => true);
  return {
    organizationId: computed(() => organizationId.value),
    organizationType: computed(() => organizationType.value),
    organizationBasePath: computed(() => organizationBasePath(organizationType.value)),
    terminology: computed(() => organizationTerminology(organizationType.value)),
    organization: computed(() => ({
      id: organizationId.value,
      organization_type: organizationType.value,
      status: organizationStatus.value,
      membership_role: role.value,
    } as SchoolOrganization)),
    membership: computed(() => ({
      organization_id: organizationId.value,
      role: role.value,
      status: membershipStatus.value,
    } as SchoolMembership)),
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

function mountView(
  organizationId: Ref<string>,
  role: Ref<SchoolMembershipRole> = ref('coach'),
  membershipStatus: Ref<SchoolMembership['status']> = ref('active'),
  organizationStatus: Ref<SchoolOrganization['status']> = ref('active'),
) {
  return mount(OrganizationTeamPerformanceView, {
    global: {
      provide: {
        [schoolContextKey as symbol]: schoolContext(
          organizationId, role, ref('school'), membershipStatus, organizationStatus,
        ),
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
    vi.mocked(schoolApi.getOrganizationTeamPhaseAnalysis).mockResolvedValue(phase());
    vi.mocked(schoolApi.getOrganizationTeamCoachReport).mockResolvedValue(report());
  });

  it('loads the report only on request and clears stale Team, date and access results', async () => {
    let resolveOld: (value: OrganizationTeamCoachReport) => void = () => undefined;
    vi.mocked(schoolApi.getOrganizationTeamCoachReport)
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveOld = resolve;
          }),
      )
      .mockResolvedValue(report());
    vi.mocked(schoolApi.getOrganizationTeamRecentForm).mockResolvedValue(form());
    const role = ref<SchoolMembershipRole>('coach');
    const wrapper = mountView(ref('school-a'), role);
    await flushPromises();
    const date = wrapper.get('input[aria-label="Recent form as-of date"]');
    await date.setValue('2026-05-01');
    await flushPromises();
    expect(schoolApi.getOrganizationTeamCoachReport).not.toHaveBeenCalled();
    await wrapper.get('button').trigger('click');
    await flushPromises();
    expect(wrapper.text()).toContain('Loading Team coach report');
    await date.setValue('2026-05-02');
    await flushPromises();
    resolveOld(report());
    await flushPromises();
    expect(wrapper.find('table[aria-labelledby="report-trend-heading"]').exists()).toBe(false);
    await wrapper.get('button').trigger('click');
    await flushPromises();
    expect(wrapper.find('table[aria-labelledby="report-trend-heading"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('independently valid form');
    role.value = 'viewer';
    await flushPromises();
    expect(wrapper.find('table[aria-labelledby="report-trend-heading"]').exists()).toBe(false);
  });

  it('shows insufficient, unavailable, denied and error report states', async () => {
    vi.mocked(schoolApi.getOrganizationTeamCoachReport)
      .mockResolvedValueOnce(report('not_ready'))
      .mockResolvedValueOnce(report('data_unavailable'))
      .mockRejectedValueOnce(Object.assign(new Error('denied'), { status: 403 }))
      .mockRejectedValueOnce(new Error('report failed'));
    const wrapper = mountView(ref('school-a'));
    await flushPromises();
    const date = wrapper.get('input[aria-label="Recent form as-of date"]');
    for (const [index, expected] of [
      'Insufficient history',
      'evidence is unavailable',
      'unavailable for your current access',
      'report failed',
    ].entries()) {
      await date.setValue(`2026-05-0${index + 1}`);
      await flushPromises();
      await wrapper.get('button').trigger('click');
      await flushPromises();
      expect(wrapper.text()).toContain(expected);
      expect(wrapper.find('table[aria-labelledby="report-trend-heading"]').exists()).toBe(false);
    }
  });

  it('requests a fresh report after success, insufficient history, and a transient failure', async () => {
    vi.mocked(schoolApi.getOrganizationTeamCoachReport)
      .mockResolvedValueOnce(report())
      .mockResolvedValueOnce(report('not_ready'))
      .mockRejectedValueOnce(new Error('temporary report failure'))
      .mockResolvedValueOnce(report());
    const wrapper = mountView(ref('school-a'));
    await flushPromises();
    await wrapper.get('input[aria-label="Recent form as-of date"]').setValue('2026-05-01');
    await flushPromises();

    for (const [index, expected] of [
      'Five verified original 25-over matches',
      'Insufficient history',
      'temporary report failure',
      'Five verified original 25-over matches',
    ].entries()) {
      await wrapper.get('button').trigger('click');
      await flushPromises();
      expect(schoolApi.getOrganizationTeamCoachReport).toHaveBeenCalledTimes(index + 1);
      expect(schoolApi.getOrganizationTeamCoachReport).toHaveBeenLastCalledWith(
        'school-a',
        'team-a',
        '2026-05-01',
      );
      expect(wrapper.text()).toContain(expected);
    }
    expect(wrapper.text()).not.toContain('temporary report failure');
  });

  it('ignores stale report successes and failures after rapid Team and date changes', async () => {
    let resolveOld: (value: OrganizationTeamCoachReport) => void = () => undefined;
    let rejectOld: (reason: Error) => void = () => undefined;
    let resolveCurrent: (value: OrganizationTeamCoachReport) => void = () => undefined;
    vi.mocked(schoolApi.listOrganizationTeamPerformanceTeams).mockResolvedValue([
      team('team-a', 'school-a'),
      team('team-b', 'school-a'),
    ]);
    vi.mocked(schoolApi.getOrganizationTeamCoachReport)
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveOld = resolve;
          }),
      )
      .mockImplementationOnce(
        () =>
          new Promise((_resolve, reject) => {
            rejectOld = reject;
          }),
      )
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveCurrent = resolve;
          }),
      );
    const wrapper = mountView(ref('school-a'));
    await flushPromises();
    const date = wrapper.get('input[aria-label="Recent form as-of date"]');
    const teamSelect = wrapper.get('select[aria-label="Team"]');
    await date.setValue('2026-05-01');
    await wrapper.get('button').trigger('click');
    expect(wrapper.get('button').attributes('disabled')).toBeDefined();
    await wrapper.get('button').trigger('click');
    expect(schoolApi.getOrganizationTeamCoachReport).toHaveBeenCalledTimes(1);

    await teamSelect.setValue('team-b');
    await date.setValue('2026-05-02');
    await wrapper.get('button').trigger('click');
    await teamSelect.setValue('team-a');
    await date.setValue('2026-05-01');
    await wrapper.get('button').trigger('click');
    expect(schoolApi.getOrganizationTeamCoachReport).toHaveBeenCalledTimes(3);
    expect(schoolApi.getOrganizationTeamCoachReport).toHaveBeenNthCalledWith(
      2,
      'school-a',
      'team-b',
      '2026-05-02',
    );
    expect(schoolApi.getOrganizationTeamCoachReport).toHaveBeenNthCalledWith(
      3,
      'school-a',
      'team-a',
      '2026-05-01',
    );
    resolveOld(report());
    rejectOld(new Error('stale report failure'));
    await flushPromises();
    expect(wrapper.text()).toContain('Loading Team coach report');
    expect(wrapper.text()).not.toContain('stale report failure');
    expect(wrapper.find('table[aria-labelledby="report-trend-heading"]').exists()).toBe(false);
    resolveCurrent(report());
    await flushPromises();
    expect(wrapper.find('table[aria-labelledby="report-trend-heading"]').exists()).toBe(true);
  });

  it('shows approved bands, recorded zero and unavailable phase evidence', async () => {
    const wrapper = mountView(ref('school-a'));
    await flushPromises();
    await wrapper.get('input[aria-label="Recent form as-of date"]').setValue('2026-05-01');
    await flushPromises();
    expect(wrapper.text()).toContain('opening 1–5, middle 6–20, closing 21–25');
    expect(wrapper.text()).toContain('Matches with unavailable phase positions: 1');
    expect(wrapper.get('table[aria-label="Team batting phase analysis"]').text()).toContain(
      'Unavailable',
    );
    expect(wrapper.get('table[aria-label="Team bowling phase analysis"]').text()).toContain(
      'Economy',
    );
  });

  it('clears stale phase responses and shows insufficient, error, and denied states', async () => {
    let resolveOld: (value: OrganizationTeamPhaseAnalysis) => void = () => undefined;
    const oldRequest = new Promise<OrganizationTeamPhaseAnalysis>((resolve) => {
      resolveOld = resolve;
    });
    vi.mocked(schoolApi.getOrganizationTeamPhaseAnalysis)
      .mockReturnValueOnce(oldRequest)
      .mockResolvedValueOnce(phase('not_ready'))
      .mockRejectedValueOnce(new Error('phase request failed'))
      .mockRejectedValueOnce(Object.assign(new Error('denied'), { status: 403 }));
    vi.mocked(schoolApi.listOrganizationTeamPerformanceTeams).mockResolvedValue([
      team('team-a', 'school-a'),
      team('team-b', 'school-a'),
    ]);
    const wrapper = mountView(ref('school-a'));
    await flushPromises();
    const date = wrapper.get('input[aria-label="Recent form as-of date"]');
    await date.setValue('2026-05-01');
    await flushPromises();
    expect(wrapper.text()).toContain('Loading phase analysis');
    await wrapper.get('select[aria-label="Team"]').setValue('team-b');
    await flushPromises();
    resolveOld(phase());
    await flushPromises();
    expect(wrapper.text()).toContain('Insufficient history for phase analysis');
    expect(wrapper.find('table[aria-label="Team batting phase analysis"]').exists()).toBe(false);
    await date.setValue('2026-05-02');
    await flushPromises();
    expect(wrapper.text()).toContain('phase request failed');
    await date.setValue('2026-05-03');
    await flushPromises();
    expect(wrapper.text()).toContain('Phase analysis is unavailable');
  });

  it('shows the five-match trend and suppresses stale form after a Team switch', async () => {
    let resolveOld: (value: OrganizationTeamRecentForm) => void = () => undefined;
    const oldRequest = new Promise<OrganizationTeamRecentForm>((resolve) => {
      resolveOld = resolve;
    });
    vi.mocked(schoolApi.getOrganizationTeamRecentForm)
      .mockReturnValueOnce(oldRequest)
      .mockResolvedValue(form());
    vi.mocked(schoolApi.listOrganizationTeamPerformanceTeams).mockResolvedValue([
      team('team-a', 'school-a'),
      team('team-b', 'school-a'),
    ]);
    const wrapper = mountView(ref('school-a'));
    await flushPromises();
    await wrapper.get('input[aria-label="Recent form as-of date"]').setValue('2026-05-01');
    await flushPromises();
    expect(wrapper.text()).toContain('Loading recent form');
    await wrapper.get('select[aria-label="Team"]').setValue('team-b');
    await flushPromises();
    expect(wrapper.find('table[aria-label="Recent Team form trend"]').exists()).toBe(true);
    resolveOld(form('not_ready'));
    await flushPromises();
    expect(wrapper.text()).toContain('Sample size: 5');
    expect(wrapper.text()).not.toContain('Insufficient history');
  });

  it('shows insufficient, unavailable, and denied form states without a trend', async () => {
    vi.mocked(schoolApi.getOrganizationTeamRecentForm)
      .mockResolvedValueOnce(form('not_ready'))
      .mockResolvedValueOnce(form('data_unavailable'))
      .mockRejectedValueOnce(Object.assign(new Error('denied'), { status: 403 }));
    const wrapper = mountView(ref('school-a'));
    await flushPromises();
    const date = wrapper.get('input[aria-label="Recent form as-of date"]');
    await date.setValue('2026-05-01');
    await flushPromises();
    expect(wrapper.text()).toContain('Insufficient history');
    expect(wrapper.find('table[aria-label="Recent Team form trend"]').exists()).toBe(false);
    await date.setValue('2026-05-02');
    await flushPromises();
    expect(wrapper.text()).toContain('Chronology or evidence is unavailable');
    await date.setValue('2026-05-03');
    await flushPromises();
    expect(wrapper.text()).toContain('Recent form is unavailable');
    expect(wrapper.find('table[aria-label="Recent Team form trend"]').exists()).toBe(false);
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
  it('shows approved trial status and requires an explicit owner activation with a timezone', async () => {
    const initial: OrganizationTeamTrialStatus = {
      state: 'not_started', games_used: 0, games_remaining: 3,
      expires_at: null, report_access_until: null,
    };
    vi.mocked(schoolApi.getOrganizationTeamTrialStatus).mockResolvedValue(initial);
    vi.mocked(schoolApi.activateOrganizationTeamTrial).mockResolvedValue({
      state: 'active', games_used: 0, games_remaining: 3,
      expires_at: '2027-02-26T12:00:00Z', report_access_until: null,
    });
    const wrapper = mountView(ref('school-a'), ref('owner'));
    await flushPromises();
    expect(wrapper.text()).toContain('Games remaining: 3');
    expect(schoolApi.activateOrganizationTeamTrial).not.toHaveBeenCalled();
    await wrapper.get('input[aria-label="Venue timezone"]').setValue('America/Barbados');
    await wrapper.get('input[aria-label="Trial activation reason"]').setValue('Five verified matches');
    await wrapper.get('form').trigger('submit');
    await flushPromises();
    expect(schoolApi.activateOrganizationTeamTrial).toHaveBeenCalledWith(
      'school-a', 'team-a', 'America/Barbados', 'Five verified matches',
    );
    expect(wrapper.text()).toContain('Trial expires: 2027-02-26T12:00:00Z');
  });

  it('displays the retained report only after an explicit request and clears it on access loss', async () => {
    vi.mocked(schoolApi.listOrganizationTeamPerformanceTeams).mockResolvedValue([
      team('team-a', 'school-a', 'active'),
    ]);
    vi.mocked(schoolApi.getOrganizationTeamTrialStatus).mockResolvedValue({
      state: 'exhausted', games_used: 3, games_remaining: 0,
      expires_at: '2027-02-26T12:00:00Z', report_access_until: '2026-12-14T12:00:00Z',
    });
    vi.mocked(schoolApi.getOrganizationTeamTrialReport).mockResolvedValue(report());
    const role = ref<SchoolMembershipRole>('coach');
    const wrapper = mountView(ref('school-a'), role);
    await flushPromises();
    expect(wrapper.text()).toContain('Games used: 3');
    expect(schoolApi.getOrganizationTeamTrialReport).not.toHaveBeenCalled();
    const button = wrapper.findAll('button').find((item) => item.text().includes('View retained trial report'));
    expect(button).toBeDefined();
    await button!.trigger('click');
    await flushPromises();
    expect(schoolApi.getOrganizationTeamTrialReport).toHaveBeenCalledWith('school-a', 'team-a');
    expect(wrapper.find('table[aria-labelledby="report-trend-heading"]').exists()).toBe(true);
    role.value = 'viewer';
    await flushPromises();
    expect(wrapper.find('table[aria-labelledby="report-trend-heading"]').exists()).toBe(false);
  });

  it.each(['role', 'membership', 'organization', 'team', 'scope'] as const)(
    'discards a delayed retained-report success after %s access changes',
    async (change) => {
      vi.mocked(schoolApi.listOrganizationTeamPerformanceTeams).mockResolvedValue([
        team('team-a', 'school-a', 'active'), team('team-b', 'school-a', 'active'),
      ]);
      vi.mocked(schoolApi.getOrganizationTeamTrialStatus).mockResolvedValue({
        state: 'exhausted', games_used: 3, games_remaining: 0,
        expires_at: '2027-02-26T12:00:00Z', report_access_until: '2026-12-14T12:00:00Z',
      });
      let resolveReport!: (value: OrganizationTeamCoachReport) => void;
      vi.mocked(schoolApi.getOrganizationTeamTrialReport).mockImplementation(
        () => new Promise((resolve) => { resolveReport = resolve; }),
      );
      const organizationId = ref('school-a');
      const role = ref<SchoolMembershipRole>('coach');
      const membershipStatus = ref<SchoolMembership['status']>('active');
      const organizationStatus = ref<SchoolOrganization['status']>('active');
      const wrapper = mountView(organizationId, role, membershipStatus, organizationStatus);
      await flushPromises();
      await wrapper.findAll('button').find((item) => item.text().includes('View retained trial report'))!.trigger('click');
      expect(schoolApi.getOrganizationTeamTrialReport).toHaveBeenCalledTimes(1);
      if (change === 'role') role.value = 'viewer';
      if (change === 'membership') membershipStatus.value = 'disabled';
      if (change === 'organization') organizationStatus.value = 'suspended';
      if (change === 'team') await wrapper.get('select[aria-label="Team"]').setValue('team-b');
      if (change === 'scope') organizationId.value = 'school-b';
      await flushPromises();
      resolveReport(report());
      await flushPromises();
      expect(wrapper.find('table[aria-labelledby="report-trend-heading"]').exists()).toBe(false);
      wrapper.unmount();
    },
  );

  it('discards a delayed retained-report failure after role loss', async () => {
    vi.mocked(schoolApi.listOrganizationTeamPerformanceTeams).mockResolvedValue([
      team('team-a', 'school-a', 'active'),
    ]);
    vi.mocked(schoolApi.getOrganizationTeamTrialStatus).mockResolvedValue({
      state: 'exhausted', games_used: 3, games_remaining: 0,
      expires_at: '2027-02-26T12:00:00Z', report_access_until: '2026-12-14T12:00:00Z',
    });
    let rejectReport!: (reason: Error) => void;
    vi.mocked(schoolApi.getOrganizationTeamTrialReport).mockImplementation(
      () => new Promise((_resolve, reject) => { rejectReport = reject; }),
    );
    const role = ref<SchoolMembershipRole>('coach');
    const wrapper = mountView(ref('school-a'), role);
    await flushPromises();
    await wrapper.findAll('button').find((item) => item.text().includes('View retained trial report'))!.trigger('click');
    role.value = 'viewer';
    await flushPromises();
    rejectReport(new Error('late retained-report failure'));
    await flushPromises();
    expect(wrapper.text()).not.toContain('late retained-report failure');
    expect(wrapper.find('table[aria-labelledby="report-trend-heading"]').exists()).toBe(false);
  });
});

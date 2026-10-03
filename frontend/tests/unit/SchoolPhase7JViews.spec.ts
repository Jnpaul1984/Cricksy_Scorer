import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';

import {
  organizationBasePath,
  organizationTerminology,
} from '@/composables/useOrganizationTerminology';
import { schoolContextKey, type SchoolContext } from '@/composables/useSchoolContext';
import * as schoolApi from '@/services/schoolAdminApi';
import type { SchoolMembershipRole } from '@/types/schoolAdmin';
import SchoolCompetitionsView from '@/views/school/SchoolCompetitionsView.vue';
import SchoolFixturesResultsView from '@/views/school/SchoolFixturesResultsView.vue';
import SchoolPublicScorecardView from '@/views/school/SchoolPublicScorecardView.vue';
import SchoolStatisticsView from '@/views/school/SchoolStatisticsView.vue';

vi.mock('@/services/schoolAdminApi');

const publicScorecard = (runs = 90) => ({
  game_id: 'game-a', publication_state: 'published_live' as const, status: 'in_progress',
  team_a: { name: 'A', players: [{ name: 'Asha' }] }, team_b: { name: 'B', players: [{ name: 'Ben' }] },
  match_type: 'limited', overs_limit: 20, days_limit: null, overs_per_day: null,
  toss_winner_team: 'A', decision: 'bat', batting_team_name: 'A', bowling_team_name: 'B',
  total_runs: runs, total_wickets: 1, overs_completed: 4, balls_this_over: 2,
  current_inning: 1, result: null, batting_scorecard: [{ player_name: 'Asha', runs }],
  bowling_scorecard: [{ player_name: 'Ben', wickets_taken: 1 }],
});

function context(role: SchoolMembershipRole, organizationId = ref('school-a')): SchoolContext {
  const edit = computed(() => ['owner', 'admin', 'coach'].includes(role));
  const broad = computed(() => ['owner', 'admin', 'coach', 'scorer'].includes(role));
  return {
    organizationId: computed(() => organizationId.value),
    organizationType: computed(() => 'school'),
    organizationBasePath: computed(() => organizationBasePath('school')),
    terminology: computed(() => organizationTerminology('school')),
    organization: ref(null),
    membership: ref(null),
    entitlement: ref(null),
    canManageTeams: edit,
    canManageRosterMetadata: edit,
    canManageRosterLifecycle: computed(() => ['owner', 'admin'].includes(role)),
    canManageTeamRoster: edit,
    canImport: edit,
    canCreateSchoolMatch: broad,
    canViewStatistics: computed(() => true),
    canViewFixturesResults: computed(() => true),
    canViewCompetitions: computed(() => true),
    canManageCompetitions: edit,
    canDeleteCompetitions: computed(() => ['owner', 'admin'].includes(role)),
    canLinkFixtures: broad,
    canPublishScorecards: broad,
    canViewEvents: computed(() => true),
    canManageEvents: edit,
    canViewAnnouncements: computed(() => true),
    canManageAnnouncements: edit,
    canManageCommunity: edit,
  };
}

function mountSchool(
  component: object,
  role: SchoolMembershipRole = 'owner',
  organizationId = ref('school-a'),
) {
  return mount(component, {
    global: {
      provide: { [schoolContextKey as symbol]: context(role, organizationId) },
      stubs: { RouterLink: { props: ['to'], template: '<a :href="String(to)"><slot /></a>' } },
    },
  });
}

describe('Phase 7J School statistics and competition experience', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(schoolApi.listSchoolPlayerStatistics).mockResolvedValue([]);
    vi.mocked(schoolApi.listSchoolTeamStatistics).mockResolvedValue([]);
    vi.mocked(schoolApi.listSchoolFixtures).mockResolvedValue([]);
    vi.mocked(schoolApi.listSchoolResults).mockResolvedValue([]);
    vi.mocked(schoolApi.listSchoolCompetitions).mockResolvedValue([]);
    vi.mocked(schoolApi.listSchoolTeams).mockResolvedValue([]);
  });

  it('renders canonical player and archived team statistics without fielding claims', async () => {
    vi.mocked(schoolApi.listSchoolPlayerStatistics).mockResolvedValue([
      {
        player_profile_id: 'profile-a',
        player_name: 'Same Name',
        roster_status: 'inactive',
        matches: 2,
        innings: 2,
        runs: 30,
        highest_score: 20,
        batting_average: 30,
        balls_faced: 24,
        strike_rate: 125,
        fours: 3,
        sixes: 1,
        bowling_innings: 1,
        balls_bowled: 12,
        overs: '2.0',
        runs_conceded: 10,
        wickets: 2,
        bowling_average: 5,
        economy: 5,
        best_bowling: '2/10',
      },
    ]);
    vi.mocked(schoolApi.listSchoolTeamStatistics).mockResolvedValue([
      {
        team_id: 'team-a',
        team_name: 'First XI',
        team_status: 'archived',
        matches: 2,
        wins: 1,
        losses: 1,
        ties: 0,
        draws: 0,
        no_results: 0,
        runs_scored: 120,
        runs_conceded: 110,
        wickets_taken: 8,
        wickets_lost: 7,
      },
    ]);
    const wrapper = mountSchool(SchoolStatisticsView);
    await flushPromises();
    expect(wrapper.text()).toContain('Same Name');
    expect(wrapper.text()).toContain('inactive');
    expect(wrapper.text()).toContain('archived');
    expect(wrapper.text()).toContain('does not reliably retain fielder identity');
  });

  it('shows empty statistics state without fabricating values', async () => {
    const wrapper = mountSchool(SchoolStatisticsView, 'viewer');
    await flushPromises();
    expect(wrapper.text()).toContain('No attributable School match statistics yet.');
    expect(wrapper.text()).toContain('No persistent School teams are available.');
  });

  it('clears statistics when the organization context changes', async () => {
    vi.mocked(schoolApi.listSchoolPlayerStatistics)
      .mockResolvedValueOnce([
        {
          player_profile_id: 'profile-a',
          player_name: 'Tenant A Player',
          roster_status: 'active',
          matches: 0,
          innings: 0,
          runs: 0,
          highest_score: 0,
          batting_average: null,
          balls_faced: 0,
          strike_rate: 0,
          fours: 0,
          sixes: 0,
          bowling_innings: 0,
          balls_bowled: 0,
          overs: '0.0',
          runs_conceded: 0,
          wickets: 0,
          bowling_average: null,
          economy: null,
          best_bowling: null,
        },
      ])
      .mockResolvedValueOnce([]);
    const organizationId = ref('school-a');
    const wrapper = mountSchool(SchoolStatisticsView, 'viewer', organizationId);
    await flushPromises();
    expect(wrapper.text()).toContain('Tenant A Player');
    organizationId.value = 'school-b';
    await flushPromises();
    expect(wrapper.text()).not.toContain('Tenant A Player');
    expect(schoolApi.listSchoolPlayerStatistics).toHaveBeenLastCalledWith('school-b');
  });

  it('publishes only after explicit confirmation and exposes the public route', async () => {
    vi.mocked(schoolApi.listSchoolResults).mockResolvedValue([
      {
        game_id: 'game-a',
        team_a_id: 'team-a',
        team_a_name: 'A',
        team_b_id: 'team-b',
        team_b_name: 'B',
        status: 'completed',
        result: 'A won',
        publication_state: 'private',
        current_inning: 2,
        team_a_runs: 100,
        team_a_wickets: 5,
        team_b_runs: 90,
        team_b_wickets: 10,
        public_scorecard_available: false,
      },
    ]);
    vi.mocked(schoolApi.updateSchoolMatchPublication).mockResolvedValue({
      game_id: 'game-a',
      organization_id: 'school-a',
      publication_state: 'published_final',
    });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const wrapper = mountSchool(SchoolFixturesResultsView, 'scorer');
    await flushPromises();
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Publish final')!
      .trigger('click');
    await flushPromises();
    expect(schoolApi.updateSchoolMatchPublication).toHaveBeenCalledWith(
      'school-a',
      'game-a',
      'published_final',
    );
  });

  it('keeps publication controls read-only for viewers', async () => {
    vi.mocked(schoolApi.listSchoolResults).mockResolvedValue([
      {
        game_id: 'game-a',
        team_a_id: 'team-a',
        team_a_name: 'A',
        team_b_id: 'team-b',
        team_b_name: 'B',
        status: 'completed',
        result: 'A won',
        publication_state: 'private',
        current_inning: 2,
        team_a_runs: 1,
        team_a_wickets: 0,
        team_b_runs: 0,
        team_b_wickets: 1,
        public_scorecard_available: false,
      },
    ]);
    const wrapper = mountSchool(SchoolFixturesResultsView, 'viewer');
    await flushPromises();
    expect(wrapper.text()).not.toContain('Publish live');
    expect(wrapper.text()).not.toContain('Publish final');
  });

  it('keeps viewer competition UI read-only', async () => {
    vi.mocked(schoolApi.listSchoolCompetitions).mockResolvedValue([
      {
        id: 'comp-a',
        organization_id: 'school-a',
        name: 'Cup',
        description: null,
        tournament_type: 'league',
        start_date: null,
        end_date: null,
        status: 'upcoming',
        created_at: '',
        updated_at: '',
      },
    ]);
    vi.mocked(schoolApi.listSchoolCompetitionTeams).mockResolvedValue([]);
    vi.mocked(schoolApi.listSchoolCompetitionFixtures).mockResolvedValue([]);
    vi.mocked(schoolApi.getSchoolStandings).mockResolvedValue({
      competition_id: 'comp-a',
      entries: [],
      unresolved_completed_games: 0,
    });
    const viewer = mountSchool(SchoolCompetitionsView, 'viewer');
    await flushPromises();
    expect(viewer.text()).not.toContain('Create competition');
    expect(viewer.text()).not.toContain('Delete competition');
    expect(viewer.text()).not.toContain('Link match');
  });

  it.each<SchoolMembershipRole>(['admin', 'coach'])(
    'shows permitted competition editing to %s',
    async (role) => {
      vi.mocked(schoolApi.listSchoolCompetitions).mockResolvedValue([
        {
          id: 'comp-a',
          organization_id: 'school-a',
          name: 'Cup',
          description: null,
          tournament_type: 'league',
          start_date: null,
          end_date: null,
          status: 'upcoming',
          created_at: '',
          updated_at: '',
        },
      ]);
      vi.mocked(schoolApi.listSchoolCompetitionTeams).mockResolvedValue([]);
      vi.mocked(schoolApi.listSchoolCompetitionFixtures).mockResolvedValue([]);
      vi.mocked(schoolApi.getSchoolStandings).mockResolvedValue({
        competition_id: 'comp-a',
        entries: [],
        unresolved_completed_games: 0,
      });
      const wrapper = mountSchool(SchoolCompetitionsView, role);
      await flushPromises();
      expect(wrapper.text()).toContain('Create competition');
      expect(wrapper.text()).toContain('Save competition');
      if (role === 'admin') expect(wrapper.text()).toContain('Delete competition');
      else expect(wrapper.text()).not.toContain('Delete competition');
    },
  );

  it('lets a scorer explicitly link an existing School match without creating one', async () => {
    vi.mocked(schoolApi.listSchoolCompetitions).mockResolvedValue([
      {
        id: 'comp-a',
        organization_id: 'school-a',
        name: 'Cup',
        description: null,
        tournament_type: 'league',
        start_date: null,
        end_date: null,
        status: 'ongoing',
        created_at: '',
        updated_at: '',
      },
    ]);
    vi.mocked(schoolApi.listSchoolCompetitionTeams).mockResolvedValue([]);
    vi.mocked(schoolApi.listSchoolCompetitionFixtures).mockResolvedValue([
      {
        id: 'fixture-a',
        tournament_id: 'comp-a',
        team_a_id: 'team-a',
        team_b_id: 'team-b',
        team_a_name: 'A',
        team_b_name: 'B',
        match_number: 1,
        venue: null,
        scheduled_date: null,
        game_id: null,
        status: 'scheduled',
        created_at: '',
        updated_at: '',
      },
    ]);
    vi.mocked(schoolApi.getSchoolStandings).mockResolvedValue({
      competition_id: 'comp-a',
      entries: [],
      unresolved_completed_games: 0,
    });
    vi.mocked(schoolApi.linkSchoolFixtureGame).mockResolvedValue({} as never);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const scorer = mountSchool(SchoolCompetitionsView, 'scorer');
    await flushPromises();
    await scorer.get('input[aria-label="School match ID"]').setValue('game-a');
    await scorer.get('form.inline-form').trigger('submit');
    await flushPromises();
    expect(schoolApi.linkSchoolFixtureGame).toHaveBeenCalledWith(
      'school-a',
      'comp-a',
      'fixture-a',
      'game-a',
    );
    expect(schoolApi.createSchoolMatch).not.toHaveBeenCalled();
  });

  it('renders only the sanitized public scorecard contract', async () => {
    vi.mocked(schoolApi.getPublicSchoolScorecard).mockResolvedValue({
      game_id: 'game-a',
      publication_state: 'published_final',
      status: 'completed',
      team_a: { name: 'A', players: [{ name: 'Asha' }] },
      team_b: { name: 'B', players: [{ name: 'Ben' }] },
      match_type: 'limited',
      overs_limit: 20,
      days_limit: null,
      overs_per_day: null,
      toss_winner_team: 'A',
      decision: 'bat',
      batting_team_name: 'B',
      bowling_team_name: 'A',
      total_runs: 90,
      total_wickets: 10,
      overs_completed: 18,
      balls_this_over: 2,
      current_inning: 2,
      result: 'A won',
      batting_scorecard: [{ player_name: 'Ben', runs: 20 }],
      bowling_scorecard: [{ player_name: 'Asha', wickets_taken: 2 }],
    });
    const wrapper = mount(SchoolPublicScorecardView, { props: { gameId: 'game-a' } });
    await flushPromises();
    expect(wrapper.text()).toContain('A won');
    expect(wrapper.text()).toContain('student metadata are not displayed');
    expect(schoolApi.getPublicSchoolScorecard).toHaveBeenCalledWith('game-a');
  });

  it('fails closed when a public scorecard is private', async () => {
    vi.mocked(schoolApi.getPublicSchoolScorecard).mockRejectedValue(
      Object.assign(new Error('hidden'), { status: 404 }),
    );
    const wrapper = mount(SchoolPublicScorecardView, { props: { gameId: 'game-private' } });
    await flushPromises();
    expect(wrapper.text()).toContain('not published');
    expect(wrapper.text()).not.toContain('hidden');
  });

  it('refreshes an open legacy public scorecard without overlapping the initial request', async () => {
    vi.useFakeTimers();
    vi.mocked(schoolApi.getPublicSchoolScorecard)
      .mockResolvedValueOnce(publicScorecard(90))
      .mockResolvedValueOnce(publicScorecard(91));
    const wrapper = mount(SchoolPublicScorecardView, { props: { gameId: 'game-a' } });
    await flushPromises();
    expect(wrapper.text()).toContain('Last updated');
    expect(wrapper.text()).toContain('Supported by');
    expect(wrapper.find('.support-slot img').attributes('alt')).toBe('Cricksy');
    expect(wrapper.get('.support-slot img').attributes('src')).toContain('logo-w480.webp');
    await vi.advanceTimersByTimeAsync(120_000);
    await flushPromises();
    expect(schoolApi.getPublicSchoolScorecard).toHaveBeenCalledTimes(2);
    expect(wrapper.text()).toContain('91/1');
    wrapper.unmount();
  });

  describe('Public scorecard dark-background contrast', () => {
    const publicScorecardSource = readFileSync(
      resolve('src/views/school/SchoolPublicScorecardView.vue'),
      'utf8',
    );

    function luminance(hex: string) {
      const channels = hex.match(/[a-f\d]{2}/gi)!.map(channel => {
        const value = parseInt(channel, 16) / 255;
        return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
      });
      return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
    }

    it.each(['.freshness', '.freshness.stale', '.support-slot', '.support-slot strong'])(
      'keeps %s text at WCAG AA contrast across the page gradient',
      (selector) => {
        const rule = publicScorecardSource.split(`${selector} {`)[1]?.split('}')[0];
        const color = rule?.match(/(?:^|;)\s*color:\s*(#[a-f\d]{6})/i)?.[1];
        expect(color).toBeDefined();
        for (const background of ['#0f1115', '#151926', '#1c2340']) {
          const foregroundLuminance = luminance(color!);
          const backgroundLuminance = luminance(background);
          const contrast = (Math.max(foregroundLuminance, backgroundLuminance) + 0.05)
            / (Math.min(foregroundLuminance, backgroundLuminance) + 0.05);
          expect(contrast).toBeGreaterThanOrEqual(4.5);
        }
      },
    );
  });

  it('keeps the last verified score and retries after a temporary refresh failure', async () => {
    vi.useFakeTimers();
    vi.mocked(schoolApi.getPublicSchoolScorecard)
      .mockResolvedValueOnce(publicScorecard(90))
      .mockRejectedValueOnce(Object.assign(new Error('offline'), { status: 503 }));
    const wrapper = mount(SchoolPublicScorecardView, { props: { gameId: 'game-a' } });
    await flushPromises();
    await vi.advanceTimersByTimeAsync(120_000);
    await flushPromises();
    expect(wrapper.text()).toContain('90/1');
    expect(wrapper.text()).toContain('Retrying automatically');
    wrapper.unmount();
  });

  it('offers a manual refresh without changing the bounded automatic cadence', async () => {
    vi.useFakeTimers();
    vi.mocked(schoolApi.getPublicSchoolScorecard).mockResolvedValue(publicScorecard(90));
    const wrapper = mount(SchoolPublicScorecardView, { props: { gameId: 'game-a' } });
    await flushPromises();
    expect(wrapper.text()).toContain('every 2 minutes');
    await wrapper.get('button.refresh-now').trigger('click');
    await flushPromises();
    expect(schoolApi.getPublicSchoolScorecard).toHaveBeenCalledTimes(2);
    wrapper.unmount();
  });

  it('stops a canonical-route refresh and clears content after publication revocation', async () => {
    vi.useFakeTimers();
    vi.mocked(schoolApi.getPublicCompetitionScorecard)
      .mockResolvedValueOnce({ ...publicScorecard(90), public_identifier: 'sc_opaque' })
      .mockRejectedValueOnce(Object.assign(new Error('revoked'), { status: 404 }));
    const wrapper = mount(SchoolPublicScorecardView, {
      props: { publicIdentifier: 'org_opaque', competitionPublicKey: 'cmp_opaque', scorecardPublicIdentifier: 'sc_opaque' },
      global: { stubs: { PublicShareLinkButton: true } },
    });
    await flushPromises();
    await vi.advanceTimersByTimeAsync(120_000);
    await flushPromises();
    expect(wrapper.text()).toContain('not published or is no longer available');
    expect(wrapper.text()).not.toContain('90/1');
    await vi.advanceTimersByTimeAsync(240_000);
    expect(schoolApi.getPublicCompetitionScorecard).toHaveBeenCalledTimes(2);
    wrapper.unmount();
  });

  it('cleans up periodic work when the parent leaves the public scorecard', async () => {
    vi.useFakeTimers();
    vi.mocked(schoolApi.getPublicSchoolScorecard).mockResolvedValue(publicScorecard(90));
    const wrapper = mount(SchoolPublicScorecardView, { props: { gameId: 'game-a' } });
    await flushPromises();
    wrapper.unmount();
    await vi.advanceTimersByTimeAsync(240_000);
    expect(schoolApi.getPublicSchoolScorecard).toHaveBeenCalledTimes(1);
  });

  it('does not let a late response from a previous scorecard overwrite repeated navigation', async () => {
    let resolvePrevious: ((value: ReturnType<typeof publicScorecard>) => void) | undefined;
    vi.mocked(schoolApi.getPublicSchoolScorecard)
      .mockResolvedValueOnce(publicScorecard(90))
      .mockImplementationOnce(() => new Promise(resolve => { resolvePrevious = resolve; }))
      .mockResolvedValueOnce(publicScorecard(92));
    const wrapper = mount(SchoolPublicScorecardView, { props: { gameId: 'game-a' } });
    await flushPromises();
    await wrapper.setProps({ gameId: 'game-b' });
    await flushPromises();
    await wrapper.setProps({ gameId: 'game-c' });
    await flushPromises();
    resolvePrevious?.(publicScorecard(91));
    await flushPromises();
    expect(schoolApi.getPublicSchoolScorecard).toHaveBeenLastCalledWith('game-c');
    expect(wrapper.text()).toContain('92/1');
    expect(wrapper.text()).not.toContain('91/1');
    wrapper.unmount();
  });

  afterEach(() => {
    vi.useRealTimers();
  });
});

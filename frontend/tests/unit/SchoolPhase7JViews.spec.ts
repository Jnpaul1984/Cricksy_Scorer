import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
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
});

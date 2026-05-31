import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import TournamentIntelligencePanel from '@/components/TournamentIntelligencePanel.vue'
import {
  getTeamJourney,
  getTournamentGroups,
  getTournamentSummary,
  type TournamentGroupsResponse,
  type TournamentSummaryResponse,
} from '@/services/api'

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return {
    ...actual,
    getTournamentGroups: vi.fn(),
    getTournamentSummary: vi.fn(),
    getTeamJourney: vi.fn(),
  }
})

const groupsMock = vi.mocked(getTournamentGroups)
const summaryMock = vi.mocked(getTournamentSummary)
const journeyMock = vi.mocked(getTeamJourney)

const groupsFixture: TournamentGroupsResponse = {
  groups: [
    {
      group_key: {
        competition_code: 'CPL_MEN',
        competition_name: 'Caribbean Premier League',
        season: '2021',
        season_year: 2021,
        gender_category: 'men',
        format_family: 't20',
        source_type: 'historical',
      },
      match_count: 34,
      teams_count: 6,
      has_result_data: true,
      has_delivery_data: true,
      champion_detected: true,
      champion_team: 'St Kitts and Nevis Patriots',
      confidence: 'high',
    },
  ],
  total_groups: 1,
  total_matches: 34,
}

const summaryFixture: TournamentSummaryResponse = {
  group_key: groupsFixture.groups[0].group_key,
  match_count: 34,
  teams: ['Trinbago Knight Riders', 'Saint Lucia Kings'],
  venues: ['Warner Park'],
  total_runs: 9876,
  total_wickets: 321,
  highest_team_total: 210,
  highest_team_total_by: 'Trinbago Knight Riders',
  lowest_completed_total: 80,
  lowest_completed_total_by: 'Saint Lucia Kings',
  closest_match: {
    match_id: 'm-close',
    match_title: 'CPL Final',
    match_date: '2021-09-15',
    stage_label: 'Final',
    result: 'Won by 1 run',
    highlight_type: 'closest_match',
    detail: '1 run',
  },
  biggest_win_by_runs: {
    match_id: 'm-big',
    match_title: 'Qualifier',
    match_date: '2021-09-10',
    stage_label: 'Qualifier',
    result: 'Won by 78 runs',
    highlight_type: 'biggest_win_by_runs',
    detail: '78 runs',
  },
  biggest_win_by_wickets: null,
  top_run_scorer: {
    player_name: 'Player A',
    value: 450,
    matches_contributed: 10,
    stat_type: 'runs',
    source: 'derived',
    confidence: 'high',
  },
  top_wicket_taker: {
    player_name: 'Player B',
    value: 19,
    matches_contributed: 9,
    stat_type: 'wickets',
    source: 'derived',
    confidence: 'medium',
  },
  derived_standings: [
    {
      team_name: 'Trinbago Knight Riders',
      canonical_team_name: 'Trinbago Knight Riders',
      played: 10,
      wins: 7,
      losses: 3,
      ties: 0,
      no_results: 0,
      points: 14,
      net_run_rate: 1.25,
      nrr_available: true,
      confidence: 'high',
      note: 'derived',
    },
  ],
  standings_label: 'Derived standings — estimated from imported match results only. Not official.',
  knockout_context: {
    champion_team: 'St Kitts and Nevis Patriots',
    champion_team_canonical: 'St Kitts and Nevis Patriots',
    runner_up_team: 'Saint Lucia Kings',
    runner_up_team_canonical: 'Saint Lucia Kings',
    final_match_id: 'm-close',
    final_match_title: 'CPL Final',
    final_match_date: '2021-09-15',
    final_result: 'Won by 3 wickets',
    semi_final_matches: [],
    qualifier_matches: [],
    outcome_source: 'derived',
    confidence: 'high',
  },
  data_completeness: {
    total_matches: 34,
    matches_with_result: 33,
    matches_missing_result: 1,
    delivery_complete_matches: 30,
    phase_level_matches: 30,
    innings_totals_matches: 3,
    metadata_only_matches: 1,
    confidence_level: 'medium',
    note: 'derived',
  },
  podcast_facts: {
    competition_label: 'CPL',
    season_label: '2021',
    champion: 'St Kitts and Nevis Patriots',
    finalist: 'Saint Lucia Kings',
    strongest_team_by_wins: 'Trinbago Knight Riders',
    top_scoring_venue: 'Warner Park',
    highest_scoring_match_title: 'CPL Final',
    highest_match_total_runs: 395,
    key_journey_note: 'Saint Lucia surged late in the season',
    confidence: 'medium',
    source_label: 'validated imports',
  },
}

describe('TournamentIntelligencePanel', () => {
  beforeEach(() => {
    groupsMock.mockReset()
    summaryMock.mockReset()
    journeyMock.mockReset()
    groupsMock.mockResolvedValue(groupsFixture)
    summaryMock.mockResolvedValue(summaryFixture)
  })

  it('renders summary, champion, standings, and podcast dark-theme sections', async () => {
    const wrapper = mount(TournamentIntelligencePanel)
    await flushPromises()

    const groupCard = wrapper.find('.tip-group-card')
    expect(groupCard.text()).toContain('Caribbean Premier League')

    await groupCard.trigger('click')
    await flushPromises()

    expect(summaryMock).toHaveBeenCalledWith('CPL_MEN', '2021', 'men')

    const completeness = wrapper.get('[aria-label="Data completeness"]')
    expect(completeness.classes()).toContain('tip-completeness-bar')
    expect(completeness.text()).toContain('medium confidence')

    expect(wrapper.findAll('.tip-stat-card').length).toBeGreaterThanOrEqual(6)

    const champion = wrapper.get('[aria-label="Champion context"]')
    expect(champion.classes()).toContain('tip-champion-card')
    expect(champion.text()).toContain('Runner-up')

    const standings = wrapper.get('[aria-label="Derived standings"]')
    expect(standings.find('.tip-standings-table').exists()).toBe(true)
    expect(standings.text()).toContain('Not official')
    expect(wrapper.get('button.tip-journey-link').text()).toContain('Journey')

    const podcast = wrapper.get('[aria-label="Podcast talking points"]')
    expect(podcast.classes()).toContain('tip-podcast-section')
    expect(podcast.text()).toContain('validated imports')
  })
})

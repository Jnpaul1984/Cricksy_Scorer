import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import TournamentIntelligencePanel from '@/components/TournamentIntelligencePanel.vue'
import {
  getTeamJourney,
  getTournamentGroups,
  getTournamentPodcastRundown,
  getTournamentSummary,
  type TeamJourneyResponse,
  type TournamentGroupsResponse,
  type TournamentPodcastRundown,
  type TournamentSummaryResponse,
} from '@/services/api'

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return {
    ...actual,
    getTournamentGroups: vi.fn(),
    getTournamentSummary: vi.fn(),
    getTeamJourney: vi.fn(),
    getTournamentPodcastRundown: vi.fn(),
  }
})

const groupsMock = vi.mocked(getTournamentGroups)
const summaryMock = vi.mocked(getTournamentSummary)
const journeyMock = vi.mocked(getTeamJourney)
const rundownMock = vi.mocked(getTournamentPodcastRundown)

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

const journeyFixture: TeamJourneyResponse = {
  team_name: 'Trinbago Knight Riders',
  canonical_team_name: 'Trinbago Knight Riders',
  group_key: groupsFixture.groups[0].group_key,
  matches: [
    {
      match_id: 'm-journey',
      match_title: 'Trinbago Knight Riders vs Saint Lucia Kings',
      match_date: '2021-09-15',
      opponent: 'Saint Lucia Kings',
      venue: 'Warner Park',
      result: 'Saint Lucia Kings won by 1 wicket(s)',
      outcome: 'loss',
      team_runs: 150,
      opponent_runs: 151,
      stage_label: 'Final',
      highlight: 'Lost (won by 1 wicket)',
    },
  ],
  summary: {
    wins: 7,
    losses: 3,
    ties: 0,
    no_results: 0,
    total_runs_for: 1650,
    total_runs_against: 1590,
    best_win: null,
    worst_defeat: null,
    closest_match: null,
    top_scorer_name: 'Player A',
    top_scorer_runs: 450,
    note: 'Derived from imported match results only.',
  },
  note: 'Derived from imported match results only.',
}

const rundownFixture: TournamentPodcastRundown = {
  group_key: groupsFixture.groups[0].group_key,
  season_review: {
    narrative:
      'The 2021 Caribbean Premier League season ended with St Kitts & Nevis Patriots lifting the title. Derived standings are estimated and not official.',
    confidence: 'medium',
    source_label: 'derived from imported match data',
  },
  champion_journey: {
    champion_team: 'St Kitts and Nevis Patriots',
    final_opponent: 'Saint Lucia Kings',
    final_result: 'Won by 3 wickets',
    derived_group_standing: 'Estimated position derived from match results — not official.',
    key_note: 'Champion detected from knockout context.',
    confidence: 'high',
    source_label: 'derived from imported match data — not official',
  },
  road_to_final: {
    finalist_a: 'St Kitts and Nevis Patriots',
    finalist_b: 'Saint Lucia Kings',
    final_result: 'Won by 3 wickets',
    narrative: 'St Kitts and Nevis Patriots met Saint Lucia Kings in the final.',
    source_label: 'derived from imported match data — not official',
    confidence: 'high',
  },
  sections: [
    {
      section_key: 'opening_hook',
      title: 'Opening Hook',
      body: 'The 2021 Caribbean Premier League concluded with a dramatic final.',
      confidence: 'medium',
      source_label: 'derived',
    },
    {
      section_key: 'data_trust_note',
      title: 'Data Trust Note',
      body: 'All facts derived from imported match data. Standings are estimated and not official.',
      confidence: 'high',
      source_label: 'derived from imported match data — not official',
    },
  ],
  overall_confidence: 'medium',
  source_label: 'derived from imported match data. Standings are estimated and not official.',
  note: 'Source: derived from imported match data. Standings are estimated and not official.',
}


describe('TournamentIntelligencePanel', () => {
  beforeEach(() => {
    groupsMock.mockReset()
    summaryMock.mockReset()
    journeyMock.mockReset()
    rundownMock.mockReset()
    groupsMock.mockResolvedValue(groupsFixture)
    summaryMock.mockResolvedValue(summaryFixture)
    journeyMock.mockResolvedValue(journeyFixture)
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

  it('normalizes tournament result grammar at display boundaries without mutating payloads', async () => {
    const grammarSummaryFixture: TournamentSummaryResponse = {
      ...summaryFixture,
      closest_match: {
        ...summaryFixture.closest_match!,
        result: 'Won by 1 wicket(s)',
        detail: 'Narrow finish: Saint Lucia Kings won by 1 wicket(s)',
      },
      biggest_win_by_runs: {
        ...summaryFixture.biggest_win_by_runs!,
        result: 'Won by 1 runs',
        detail: 'Trinbago Knight Riders won by 1 runs',
      },
      biggest_win_by_wickets: {
        match_id: 'm-wkts',
        match_title: 'Eliminator',
        match_date: '2021-09-12',
        stage_label: 'Eliminator',
        result: 'Won by 2 wicket(s)',
        highlight_type: 'biggest_win_by_wickets',
        detail: 'Saint Lucia Kings won by 2 wicket(s)',
      },
      knockout_context: {
        ...summaryFixture.knockout_context!,
        final_result: 'Won by 1 wicket(s)',
      },
      podcast_facts: {
        ...summaryFixture.podcast_facts!,
        key_journey_note: 'Saint Lucia Kings won by 1 wicket(s) in the final.',
      },
    }

    const grammarJourneyFixture: TeamJourneyResponse = {
      ...journeyFixture,
      matches: [
        {
          ...journeyFixture.matches[0],
          result: 'Saint Lucia Kings won by 1 wicket(s)',
        },
      ],
    }

    summaryMock.mockResolvedValueOnce(grammarSummaryFixture)
    journeyMock.mockResolvedValueOnce(grammarJourneyFixture)

    const wrapper = mount(TournamentIntelligencePanel)
    await flushPromises()

    await wrapper.get('.tip-group-card').trigger('click')
    await flushPromises()

    const highlightTexts = wrapper.findAll('.tip-highlight-val').map((node) => node.text())
    expect(highlightTexts).toContain('Trinbago Knight Riders won by 1 run')
    expect(highlightTexts).toContain('Saint Lucia Kings won by 2 wickets')
    expect(highlightTexts).toContain('Narrow finish: Saint Lucia Kings won by 1 wicket')

    const champion = wrapper.get('[aria-label="Champion context"]')
    expect(champion.text()).toContain('Won by 1 wicket')

    const podcast = wrapper.get('[aria-label="Podcast talking points"]')
    expect(podcast.text()).toContain('Final result: Won by 1 wicket')
    expect(podcast.text()).toContain('Saint Lucia Kings won by 1 wicket in the final.')

    await wrapper.get('button.tip-journey-link').trigger('click')
    await flushPromises()

    expect(wrapper.get('.tip-journey-result').text()).toBe('Saint Lucia Kings won by 1 wicket')

    expect(grammarSummaryFixture.biggest_win_by_runs?.detail).toBe('Trinbago Knight Riders won by 1 runs')
    expect(grammarSummaryFixture.biggest_win_by_wickets?.detail).toBe('Saint Lucia Kings won by 2 wicket(s)')
    expect(grammarSummaryFixture.knockout_context?.final_result).toBe('Won by 1 wicket(s)')
    expect(grammarJourneyFixture.matches[0]?.result).toBe('Saint Lucia Kings won by 1 wicket(s)')
  })

  // ── Phase 10S.2: Podcast Rundown tests ──────────────────────────────────

  it('renders Generate Rundown button when a competition is selected', async () => {
    const wrapper = mount(TournamentIntelligencePanel)
    await flushPromises()

    await wrapper.get('.tip-group-card').trigger('click')
    await flushPromises()

    const btn = wrapper.get('[data-testid="generate-rundown-btn"]')
    expect(btn.attributes('disabled')).toBeUndefined()
    expect(btn.text()).toContain('Generate Rundown')
  })

  it('calls getTournamentPodcastRundown and renders rundown sections after clicking generate', async () => {
    rundownMock.mockResolvedValueOnce(rundownFixture)

    const wrapper = mount(TournamentIntelligencePanel)
    await flushPromises()

    await wrapper.get('.tip-group-card').trigger('click')
    await flushPromises()

    await wrapper.get('[data-testid="generate-rundown-btn"]').trigger('click')
    await flushPromises()

    expect(rundownMock).toHaveBeenCalledWith('CPL_MEN', '2021', 'men')

    const trustNote = wrapper.get('[data-testid="rundown-trust-note"]')
    expect(trustNote.text()).toContain('derived from imported match data')
    expect(trustNote.text()).toContain('not official')

    const seasonReview = wrapper.get('[data-testid="season-review-narrative"]')
    expect(seasonReview.text()).toContain('2021 Caribbean Premier League')
    expect(seasonReview.text()).toContain('not official')
  })

  it('renders champion journey card with champion team and confidence badge', async () => {
    rundownMock.mockResolvedValueOnce(rundownFixture)

    const wrapper = mount(TournamentIntelligencePanel)
    await flushPromises()
    await wrapper.get('.tip-group-card').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="generate-rundown-btn"]').trigger('click')
    await flushPromises()

    const card = wrapper.get('[data-testid="champion-journey-card"]')
    expect(card.text()).toContain('St Kitts and Nevis Patriots')
    expect(card.text()).toContain('Saint Lucia Kings')
    expect(card.text()).toContain('not official')
    expect(card.text()).toContain('high')
  })

  it('renders road-to-final card with both finalists', async () => {
    rundownMock.mockResolvedValueOnce(rundownFixture)

    const wrapper = mount(TournamentIntelligencePanel)
    await flushPromises()
    await wrapper.get('.tip-group-card').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="generate-rundown-btn"]').trigger('click')
    await flushPromises()

    const card = wrapper.get('[data-testid="road-to-final-card"]')
    expect(card.text()).toContain('St Kitts and Nevis Patriots')
    expect(card.text()).toContain('Saint Lucia Kings')
  })

  it('renders data trust note footer', async () => {
    rundownMock.mockResolvedValueOnce(rundownFixture)

    const wrapper = mount(TournamentIntelligencePanel)
    await flushPromises()
    await wrapper.get('.tip-group-card').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="generate-rundown-btn"]').trigger('click')
    await flushPromises()

    const note = wrapper.get('[data-testid="rundown-note"]')
    expect(note.text()).toContain('not official')
  })

  it('shows champion journey fallback card when champion_journey is null', async () => {
    const thinRundown: TournamentPodcastRundown = {
      ...rundownFixture,
      champion_journey: null,
    }
    rundownMock.mockResolvedValueOnce(thinRundown)

    const wrapper = mount(TournamentIntelligencePanel)
    await flushPromises()
    await wrapper.get('.tip-group-card').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="generate-rundown-btn"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="champion-journey-card"]').exists()).toBe(false)
    const fallback = wrapper.get('[data-testid="champion-journey-fallback"]')
    expect(fallback.text()).toContain('unavailable')
  })

  it('renders copy Markdown and copy plain text buttons after rundown is loaded', async () => {
    rundownMock.mockResolvedValueOnce(rundownFixture)

    const wrapper = mount(TournamentIntelligencePanel)
    await flushPromises()
    await wrapper.get('.tip-group-card').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="generate-rundown-btn"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="copy-md-btn"]').text()).toContain('Copy Markdown')
    expect(wrapper.get('[data-testid="copy-text-btn"]').text()).toContain('Copy Plain Text')
  })

  it('shows error state when getTournamentPodcastRundown rejects', async () => {
    rundownMock.mockRejectedValueOnce(new Error('Network error'))

    const wrapper = mount(TournamentIntelligencePanel)
    await flushPromises()
    await wrapper.get('.tip-group-card').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="generate-rundown-btn"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="rundown-trust-note"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Network error')
  })

  it('clears rundown when × Clear is clicked', async () => {
    rundownMock.mockResolvedValueOnce(rundownFixture)

    const wrapper = mount(TournamentIntelligencePanel)
    await flushPromises()
    await wrapper.get('.tip-group-card').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="generate-rundown-btn"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="rundown-trust-note"]').exists()).toBe(true)

    await wrapper.get('[data-testid="clear-rundown-btn"]').trigger('click')

    expect(wrapper.find('[data-testid="rundown-trust-note"]').exists()).toBe(false)
  })
})

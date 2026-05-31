import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import HistoricalArchiveExplorerPanel from '@/components/HistoricalArchiveExplorerPanel.vue'
import {
  getHistoricalArchiveExplorer,
  getTournamentGroups,
  type HistoricalArchiveExplorerResponse,
  type TournamentGroupsResponse,
} from '@/services/api'

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return {
    ...actual,
    getHistoricalArchiveExplorer: vi.fn(),
    getTournamentGroups: vi.fn(),
  }
})

const archiveMock = vi.mocked(getHistoricalArchiveExplorer)
const groupsMock = vi.mocked(getTournamentGroups)

const groupsFixture: TournamentGroupsResponse = {
  groups: [
    {
      group_key: {
        competition_code: 'CPL_MEN',
        competition_name: 'Caribbean Premier League',
        season: '2021',
        season_year: 2021,
        gender_category: 'men',
        format_family: 'T20',
        source_type: 'historical_import',
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

const archiveFixture: HistoricalArchiveExplorerResponse = {
  comparison_rows: [
    {
      group_key: groupsFixture.groups[0].group_key,
      imported_matches: 34,
      teams_count: 6,
      venues_count: 2,
      champion_detected: 'St Kitts and Nevis Patriots',
      runner_up_detected: 'Saint Lucia Kings',
      final_result: 'St Kitts and Nevis Patriots won by 3 wickets',
      total_runs: 9876,
      total_wickets: 321,
      average_runs_per_match: 290.47,
      average_runs_per_wicket: 30.77,
      data_completeness_label: '33/34 matches with results. 30 delivery-complete.',
      confidence: 'medium',
      incomplete_season: true,
      wicket_source_label: 'Derived from delivery dismissal records',
      note: 'Derived from imported match data.',
    },
  ],
  era_comparison_cards: [
    {
      card_key: 'highest_scoring_season',
      title: 'Highest-scoring season',
      value: 'Caribbean Premier League 2021',
      subtitle: '290.47 runs per match across 34 matches',
      confidence: 'medium',
      fallback: false,
      note: 'Derived from imported match data. Not official.',
    },
  ],
  champion_history: [
    {
      season: '2021',
      season_year: 2021,
      champion_detected: 'St Kitts and Nevis Patriots',
      runner_up_detected: 'Saint Lucia Kings',
      final_result: 'Won by 3 wicket(s)',
      confidence: 'high',
      source: 'detected_final_result',
      note: 'Champion history is derived from imported match data and detected final results. It is not an official record.',
    },
  ],
  champion_history_note: 'Champion history is derived from imported match data and detected final results. It is not an official record.',
  dynasty_indicators: [
    {
      metric_key: 'most_detected_titles',
      title: 'Most detected titles',
      team_name: 'St Kitts and Nevis Patriots',
      value: '1',
      subtitle: 'Detected titles from derived final results only.',
      confidence: 'medium',
      fallback: false,
      note: 'Detected titles only.',
    },
  ],
  venue_trends: [
    {
      venue: 'Warner Park',
      matches: 2,
      total_runs: 600,
      average_runs_per_match: 300,
      total_wickets: 25,
      wickets_per_match: 12.5,
      sample_note: 'Meets archive sample-size safeguards.',
      confidence: 'high',
      note: 'Venue trends are derived from imported match data.',
    },
  ],
  research_summary: {
    sections: [
      {
        section_key: 'archive_overview',
        title: 'Archive overview',
        body: 'The archive currently spans 1 competition-season group across 1 competitions and 34 imported matches.',
      },
      {
        section_key: 'data_trust_note',
        title: 'Data trust note',
        body: 'All archive views are derived from imported match data and are not official.',
      },
    ],
    markdown: '## Archive overview\nThe archive currently spans 1 competition-season group.\n\n## Data trust note\nAll archive views are derived from imported match data and are not official.',
    plain_text: 'Archive overview\nThe archive currently spans 1 competition-season group.\n\nData trust note\nAll archive views are derived from imported match data and are not official.',
    note: 'Derived from imported match data only.',
  },
  total_matches: 34,
  total_groups: 1,
  selected_competition_code: 'CPL_MEN',
  trust_note:
    'All archive views are derived from imported match data and are not official. Incomplete seasons may affect comparisons. Wicket trends use delivery-derived dismissal records only where available. Player leaderboards require player-level data and are not invented.',
  note: 'Historical Archive Explorer is deterministic and read-only.',
}

describe('HistoricalArchiveExplorerPanel', () => {
  beforeEach(() => {
    groupsMock.mockResolvedValue(groupsFixture)
    archiveMock.mockResolvedValue(archiveFixture)
  })

  it('renders comparison, champion history, venue trends, and trust wording', async () => {
    const wrapper = mount(HistoricalArchiveExplorerPanel)
    await flushPromises()

    expect(wrapper.get('[data-testid="archive-comparison-table"]').text()).toContain('St Kitts and Nevis Patriots')
    expect(wrapper.get('[data-testid="champion-history-table"]').text()).toContain('Won by 3 wickets')
    expect(wrapper.get('[data-testid="venue-trends-table"]').text()).toContain('Warner Park')
    expect(wrapper.get('[data-testid="archive-trust-note"]').text()).toContain('not official')
    expect(archiveMock).toHaveBeenCalled()
  })

  it('copies markdown and plain text archive summaries', async () => {
    const clipboardWriteMock = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(globalThis.navigator, 'clipboard', {
      configurable: true,
      value: { writeText: clipboardWriteMock },
    })

    const wrapper = mount(HistoricalArchiveExplorerPanel)
    await flushPromises()

    await wrapper.get('[data-testid="archive-copy-md-btn"]').trigger('click')
    expect(clipboardWriteMock.mock.calls.at(-1)?.[0]).toContain('## Archive overview')

    await wrapper.get('[data-testid="archive-copy-text-btn"]').trigger('click')
    expect(clipboardWriteMock.mock.calls.at(-1)?.[0]).toContain('Data trust note')
  })

  it('renders empty fallback when archive rows are unavailable', async () => {
    archiveMock.mockResolvedValueOnce({
      ...archiveFixture,
      comparison_rows: [],
      era_comparison_cards: [],
      champion_history: [],
      dynasty_indicators: [],
      venue_trends: [],
      research_summary: {
        ...archiveFixture.research_summary,
        sections: [{ section_key: 'archive_overview', title: 'Archive overview', body: 'No archive groups matched the current filters.' }],
        markdown: null,
        plain_text: null,
      },
      total_groups: 0,
      total_matches: 0,
    })

    const wrapper = mount(HistoricalArchiveExplorerPanel)
    await flushPromises()

    expect(wrapper.text()).toContain('No archive groups matched the current filters.')
  })
})

import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import HistoricalMetadataOnlyMatchesPanel from '@/components/HistoricalMetadataOnlyMatchesPanel.vue'
import * as api from '@/services/api'

vi.mock('@/services/api', () => ({
  historicalImportListMetadataOnlyMatches: vi.fn(),
}))

const flushPromises = async () => {
  await Promise.resolve()
  await Promise.resolve()
}

describe('HistoricalMetadataOnlyMatchesPanel', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.stubGlobal('navigator', {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    })
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:mock'),
      revokeObjectURL: vi.fn(),
    })
  })

  it('renders title and total count', async () => {
    vi.mocked(api.historicalImportListMetadataOnlyMatches).mockResolvedValue({
      status: 'ok',
      total: 1,
      items: [
        {
          match_id: 'match-1',
          batch_id: 'batch-1',
          source_filename: '635234.json',
          team_a: 'TKR',
          team_b: 'JAM',
          match_date: '2013-09-07',
          venue: 'Port of Spain',
          competition: 'Caribbean Premier League',
          season: '2013',
          completeness_status: 'metadata_only',
          expected_deliveries: 238,
          actual_deliveries: 0,
          expected_wickets: 9,
          actual_wickets: 0,
          source_payload_available: true,
          recommended_action: 'reimport_from_source_json',
        },
      ],
    })

    const wrapper = mount(HistoricalMetadataOnlyMatchesPanel)
    await flushPromises()

    expect(wrapper.text()).toContain('Metadata-Only Historical Matches')
    expect(wrapper.get('[data-testid="hmom-total-count"]').text()).toContain('1 metadata-only matches found')
  })

  it('renders returned match rows in table', async () => {
    vi.mocked(api.historicalImportListMetadataOnlyMatches).mockResolvedValue({
      status: 'ok',
      total: 1,
      items: [
        {
          match_id: 'match-1',
          batch_id: 'batch-1',
          source_filename: '635234.json',
          team_a: 'TKR',
          team_b: 'JAM',
          match_date: '2013-09-07',
          venue: 'Port of Spain',
          competition: 'Caribbean Premier League',
          season: '2013',
          completeness_status: 'metadata_only',
          expected_deliveries: 238,
          actual_deliveries: 0,
          expected_wickets: 9,
          actual_wickets: 0,
          source_payload_available: true,
          recommended_action: 'reimport_from_source_json',
        },
      ],
    })

    const wrapper = mount(HistoricalMetadataOnlyMatchesPanel)
    await flushPromises()

    expect(wrapper.get('[data-testid="hmom-table"]').text()).toContain('635234.json')
    expect(wrapper.get('[data-testid="hmom-table"]').text()).toContain('TKR vs JAM')
  })

  it('shows empty state when no metadata-only matches are returned', async () => {
    vi.mocked(api.historicalImportListMetadataOnlyMatches).mockResolvedValue({
      status: 'ok',
      total: 0,
      items: [],
    })

    const wrapper = mount(HistoricalMetadataOnlyMatchesPanel)
    await flushPromises()

    expect(wrapper.get('[data-testid="hmom-empty-state"]').text()).toContain(
      'No metadata-only historical matches found.',
    )
  })

  it('renders copy and export controls', async () => {
    vi.mocked(api.historicalImportListMetadataOnlyMatches).mockResolvedValue({
      status: 'ok',
      total: 1,
      items: [
        {
          match_id: 'match-1',
          batch_id: 'batch-1',
          source_filename: '635234.json',
          team_a: 'TKR',
          team_b: 'JAM',
          match_date: '2013-09-07',
          venue: 'Port of Spain',
          competition: 'Caribbean Premier League',
          season: '2013',
          completeness_status: 'metadata_only',
          expected_deliveries: 238,
          actual_deliveries: 0,
          expected_wickets: 9,
          actual_wickets: 0,
          source_payload_available: true,
          recommended_action: 'reimport_from_source_json',
        },
      ],
    })

    const wrapper = mount(HistoricalMetadataOnlyMatchesPanel)
    await flushPromises()

    expect(wrapper.get('[data-testid="hmom-copy-match-ids-btn"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="hmom-copy-batch-ids-btn"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="hmom-export-csv-btn"]').exists()).toBe(true)
  })
})

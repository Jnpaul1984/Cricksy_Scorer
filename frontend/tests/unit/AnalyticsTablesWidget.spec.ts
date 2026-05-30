import { flushPromises, mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick } from 'vue'

import AnalyticsTablesWidget from '@/components/AnalyticsTablesWidget.vue'

const mockGetAnalystDeliveries = vi.fn()
const mockGetMatchCaseStudy = vi.fn()

vi.mock('@/services/api', () => ({
  getAnalystDeliveries: (...args: unknown[]) => mockGetAnalystDeliveries(...args),
  getMatchCaseStudy: (...args: unknown[]) => mockGetMatchCaseStudy(...args),
}))

function buildCaseStudy({
  innings,
  phases,
}: {
  innings?: Array<{ team: string; runs: number; wickets: number; overs: number; run_rate: number }>
  phases?: Array<{
    id: string
    label: string
    start_over: number
    end_over: number
    runs: number
    wickets: number
    run_rate: number
  }>
}) {
  return {
    analysis_mode: 'limited_overs',
    match: {
      id: 'match-001',
      date: '2025-01-10',
      format: 'T20',
      teams_label: 'Lions vs Falcons',
      result: 'Lions won by 18 runs',
      innings: innings ?? [],
    },
    momentum_summary: {
      title: 'Momentum',
      subtitle: 'Summary',
    },
    key_phase: {
      title: 'Key phase',
      detail: 'Detail',
    },
    phases: phases ?? [],
    key_players: [],
    dismissal_patterns: null,
    ai: null,
  }
}

describe('AnalyticsTablesWidget', () => {
  beforeEach(() => {
    mockGetAnalystDeliveries.mockReset()
    mockGetMatchCaseStudy.mockReset()
  })

  it('renders delivery-complete summary metrics and graphs without NaN values', async () => {
    mockGetAnalystDeliveries.mockResolvedValue({
      items: [
        { match_id: 'match-001', innings: 1, over_number: 1, ball_number: 1, total_runs: 1, wicket: false, extra_type: null },
        { match_id: 'match-001', innings: 1, over_number: 1, ball_number: 2, total_runs: 4, wicket: false, extra_type: null },
        { match_id: 'match-001', innings: 1, over_number: 1, ball_number: 3, total_runs: 0, wicket: true, extra_type: null },
        { match_id: 'match-001', innings: 1, over_number: 1, ball_number: 4, total_runs: 2, wicket: false, extra_type: null },
        { match_id: 'match-001', innings: 1, over_number: 2, ball_number: 1, total_runs: 3, wicket: false, extra_type: null },
        { match_id: 'match-001', innings: 1, over_number: 2, ball_number: 2, total_runs: 6, wicket: false, extra_type: null },
        { match_id: 'match-001', innings: 2, over_number: 1, ball_number: 1, total_runs: 2, wicket: false, extra_type: null },
        { match_id: 'match-001', innings: 2, over_number: 1, ball_number: 2, total_runs: 1, wicket: false, extra_type: null },
        { match_id: 'match-001', innings: 2, over_number: 2, ball_number: 1, total_runs: 4, wicket: true, extra_type: null },
        { match_id: 'match-001', innings: 2, over_number: 2, ball_number: 2, total_runs: 1, wicket: false, extra_type: null },
      ],
      total: 10,
      data_completeness: 'delivery_complete',
    })
    mockGetMatchCaseStudy.mockResolvedValue(buildCaseStudy({
      innings: [
        { team: 'Lions', runs: 16, wickets: 1, overs: 1, run_rate: 16 },
        { team: 'Falcons', runs: 8, wickets: 1, overs: 1, run_rate: 8 },
      ],
      phases: [
        { id: 'powerplay', label: 'Powerplay', start_over: 1, end_over: 6, runs: 16, wickets: 1, run_rate: 16 },
      ],
    }))

    const wrapper = mount(AnalyticsTablesWidget, {
      props: {
        profile: null,
        matchId: 'match-001',
        matchSource: 'historical',
        matchTitle: 'Lions vs Falcons',
        dataCompleteness: 'delivery_complete',
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Lions vs Falcons')
    expect(wrapper.text()).toContain('Total Runs')
    expect(wrapper.text()).toContain('24')
    expect(wrapper.text()).toContain('Deliveries')
    expect(wrapper.text()).toContain('10')
    expect(wrapper.text()).toContain('Run Rate')
    expect(wrapper.text()).toContain('14.40')
    expect(wrapper.text()).toContain('Wickets')
    expect(wrapper.text()).toContain('2')
    expect(wrapper.text()).toContain('How to read this:')
    expect(wrapper.text()).toContain('Best scoring period')
    expect(wrapper.text()).not.toContain('NaN')
    expect(wrapper.findAll('.analytics-bar-chart__column')).toHaveLength(4)

    const inningsSelect = wrapper.find('select[aria-label="Select innings"]')
    await inningsSelect.setValue('1')
    await nextTick()
    expect(wrapper.text()).toContain('16')
    expect(wrapper.findAll('.analytics-bar-chart__column')).toHaveLength(2)

    const tabs = wrapper.findAll('.chart-tab')
    await tabs[1].trigger('click')
    await nextTick()
    expect(wrapper.findAll('circle').length).toBeGreaterThan(0)

    await tabs[2].trigger('click')
    await nextTick()
    expect(wrapper.findAll('circle').length).toBeGreaterThan(0)

    const scatterModeSelect = wrapper.find('select[aria-label="Select Scatter mode"]')
    await scatterModeSelect.setValue('delivery_index_vs_runs')
    await nextTick()
    expect(wrapper.text()).toContain('Delivery index')
  })

  it('falls back to phase-level analytics when delivery data is unavailable', async () => {
    mockGetAnalystDeliveries.mockResolvedValue({
      items: [],
      total: 0,
      data_completeness: 'phase_level',
    })
    mockGetMatchCaseStudy.mockResolvedValue(buildCaseStudy({
      innings: [
        { team: 'Lions', runs: 140, wickets: 4, overs: 20, run_rate: 7 },
      ],
      phases: [
        { id: 'powerplay', label: 'Powerplay', start_over: 1, end_over: 6, runs: 42, wickets: 1, run_rate: 7 },
        { id: 'middle', label: 'Middle overs', start_over: 7, end_over: 15, runs: 58, wickets: 2, run_rate: 6.44 },
        { id: 'death', label: 'Death overs', start_over: 16, end_over: 20, runs: 40, wickets: 1, run_rate: 8 },
      ],
    }))

    const wrapper = mount(AnalyticsTablesWidget, {
      props: {
        profile: null,
        matchId: 'match-001',
        matchSource: 'historical',
        matchTitle: 'Lions vs Falcons',
        dataCompleteness: 'phase_level',
      },
    })

    await flushPromises()

    expect(wrapper.findAll('.analytics-bar-chart__column')).toHaveLength(3)
    expect(wrapper.text()).toContain('Using phase summaries because delivery records are unavailable.')
    expect(wrapper.text()).not.toContain('NaN')

    const inningsTwoOption = wrapper.find('select[aria-label="Select innings"] option[value="2"]')
    expect(inningsTwoOption.exists()).toBe(false)
  })

  it('falls back to innings totals when only innings-level data exists', async () => {
    mockGetAnalystDeliveries.mockResolvedValue({
      items: [],
      total: 0,
      data_completeness: 'innings_totals',
    })
    mockGetMatchCaseStudy.mockResolvedValue(buildCaseStudy({
      innings: [
        { team: 'Lions', runs: 162, wickets: 5, overs: 20, run_rate: 8.1 },
        { team: 'Falcons', runs: 155, wickets: 8, overs: 20, run_rate: 7.75 },
      ],
      phases: [],
    }))

    const wrapper = mount(AnalyticsTablesWidget, {
      props: {
        profile: null,
        matchId: 'match-001',
        matchSource: 'live',
        matchTitle: 'Lions vs Falcons',
        dataCompleteness: 'innings_totals',
      },
    })

    await flushPromises()

    expect(wrapper.findAll('.analytics-bar-chart__column')).toHaveLength(2)
    expect(wrapper.text()).toContain('Using innings totals because only innings-level scoring is available.')
    expect(wrapper.text()).toContain('317')
    expect(wrapper.text()).not.toContain('NaN')
  })

  it('shows a clear insufficient-data state for metadata-only matches', async () => {
    mockGetAnalystDeliveries.mockResolvedValue({
      items: [],
      total: 0,
      data_completeness: 'metadata_only',
    })
    mockGetMatchCaseStudy.mockResolvedValue(buildCaseStudy({ innings: [], phases: [] }))

    const wrapper = mount(AnalyticsTablesWidget, {
      props: {
        profile: null,
        matchId: 'match-001',
        matchSource: 'historical',
        matchTitle: 'Lions vs Falcons',
        dataCompleteness: 'metadata_only',
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('This registry entry only has metadata.')
    expect(wrapper.text()).toContain('Unavailable')
    expect(wrapper.text()).not.toContain('NaN')
  })

  it('supports innings selector up to innings 4 for test/multi-day matches', async () => {
    mockGetAnalystDeliveries.mockResolvedValue({
      items: [],
      total: 0,
      data_completeness: 'innings_totals',
    })
    mockGetMatchCaseStudy.mockResolvedValue({
      ...buildCaseStudy({
        innings: [
          { team: 'AUS', runs: 320, wickets: 10, overs: 96, run_rate: 3.33 },
          { team: 'SA', runs: 280, wickets: 10, overs: 88, run_rate: 3.18 },
          { team: 'AUS', runs: 210, wickets: 10, overs: 70, run_rate: 3.0 },
          { team: 'SA', runs: 251, wickets: 7, overs: 82, run_rate: 3.06 },
        ],
        phases: [],
      }),
      analysis_mode: 'test_multi_day',
    })

    const wrapper = mount(AnalyticsTablesWidget, {
      props: {
        profile: null,
        matchId: 'match-001',
        matchSource: 'historical',
        matchTitle: 'AUS vs SA',
        dataCompleteness: 'innings_totals',
      },
    })

    await flushPromises()

    const inningsSelect = wrapper.find('select[aria-label="Select innings"]')
    expect(inningsSelect.html()).toContain('value="4"')
    await inningsSelect.setValue('4')
    await nextTick()
    expect(wrapper.text()).toContain('251')
  })
})

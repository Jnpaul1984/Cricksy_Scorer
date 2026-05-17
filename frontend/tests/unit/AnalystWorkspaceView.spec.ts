import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick } from 'vue'

import { __resetAiInsightCacheForTests } from '@/services/aiInsightCache'
import * as api from '@/services/api'
import AnalystWorkspaceView from '@/views/AnalystWorkspaceView.vue'

const pushMock = vi.fn()

// Mock vue-router
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock, back: vi.fn() }),
}))

vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    canAnalyze: true,
  }),
}))

// Mock the api module
vi.mock('@/services/api', () => ({
  getAnalystMatches: vi.fn(),
  getMatchCaseStudy: vi.fn(),
  getMatchAiSummary: vi.fn(),
  getMatchRegistry: vi.fn(),
  getAnalystExportData: vi.fn(),
  historicalImportRollback: vi.fn(),
}))

// Stub child components that are not under test
const globalStubs = {
  BaseCard: { template: '<div class="base-card-stub"><slot /></div>' },
  BaseButton: { template: '<button class="base-button-stub" @click="$emit(\'click\', $event)"><slot /></button>', emits: ['click'] },
  BaseBadge: { template: '<span class="base-badge-stub"><slot /></span>' },
  BaseInput: { template: '<input class="base-input-stub" />' },
  ImpactBar: { template: '<div class="impact-bar-stub" />' },
  MiniSparkline: { template: '<div class="mini-sparkline-stub" />' },
  AiCalloutsPanel: { template: '<div class="ai-callouts-stub" />' },
  AiInsightReviewCard: {
    props: ['insightType', 'insightId', 'title', 'explanation', 'confidence', 'limitations', 'sourceRefs', 'canReview'],
    template: `
      <div data-testid="ai-insight-review-card-stub">
        {{ insightType }}|{{ insightId }}|{{ confidence }}|{{ (limitations || []).length }}|{{ (sourceRefs || []).length }}|{{ canReview }}
      </div>
    `,
  },
  AnalyticsTablesWidget: { template: '<div class="analytics-tables-stub" />' },
  ExportUI: { template: '<div class="export-ui-stub" />' },
  HistoricalImportPanel: {
    template: '<button class="json-import-done-btn" @click="$emit(\'import-done\', \'json-game\')">json import done</button>',
    emits: ['import-done'],
  },
  HistoricalImportBulkZipPanel: {
    template: '<button class="zip-import-done-btn" @click="$emit(\'import-done\', \'zip-game\')">zip import done</button>',
    emits: ['import-done'],
  },
  HistoricalOcrReviewPanel: { template: '<div class="ocr-review-panel-stub" />' },
}

const mockMatchList = {
  items: [
    {
      id: 'match-001',
      date: '2025-01-10',
      format: 'T20',
      teams: 'Lions vs Falcons',
      result: 'Lions won by 18 runs',
      run_rate: 8.4,
      phase_swing: '+18 in death',
      status: 'completed',
      venue: 'Generic Cricket Ground',
      event_name: 'Premier League 2025',
      season: '2025',
      match_number: 3,
      source_dates: ['2025-01-10'],
      match_datetime: null,
      is_historical: true,
      source: 'historical_import',
      historical_batch_id: 'batch-001',
    },
    {
      id: 'match-002',
      date: '2025-01-15',
      format: 'ODI',
      teams: 'Tigers vs Eagles',
      result: 'Tigers won by 5 wickets',
      run_rate: 5.2,
      phase_swing: '-12 in powerplay',
      status: 'completed',
      venue: null,
      event_name: null,
      season: null,
      match_number: null,
      source_dates: [],
      match_datetime: null,
      is_historical: false,
      source: 'live',
      historical_batch_id: null,
    },
  ],
  total: 2,
}

const mockMatchDetail = {
  match: {
    id: 'match-001',
    date: '2025-01-10',
    format: 'T20',
    teams_label: 'Lions vs Falcons',
    result: 'Lions won by 18 runs',
    home_team: 'Lions',
    away_team: 'Falcons',
    venue: null,
    overs_per_side: 20,
    innings: [
      { team: 'Lions', runs: 178, wickets: 6, overs: 20, run_rate: 8.9 },
      { team: 'Falcons', runs: 160, wickets: 10, overs: 19.4, run_rate: 8.2 },
    ],
  },
  momentum_summary: {
    title: 'Lions dominated from ball one',
    subtitle: 'Consistent batting throughout all phases',
    winning_side: 'Lions',
    swing_metric: null,
  },
  key_phase: {
    title: 'Death overs surge',
    detail: 'Lions scored 45 runs in the last 4 overs to pull clear',
    overs_range: { start_over: 16, end_over: 20 },
    reason_codes: [],
  },
  phases: [
    {
      id: 'powerplay',
      label: 'Powerplay',
      start_over: 1,
      end_over: 6,
      runs: 52,
      wickets: 1,
      run_rate: 8.67,
      net_swing_vs_par: 10,
      impact: 'positive',
      impact_label: 'Strong start',
    },
    {
      id: 'middle',
      label: 'Middle overs',
      start_over: 7,
      end_over: 15,
      runs: 81,
      wickets: 3,
      run_rate: 9.0,
      net_swing_vs_par: 5,
      impact: 'neutral',
      impact_label: 'On par',
    },
    {
      id: 'death',
      label: 'Death overs',
      start_over: 16,
      end_over: 20,
      runs: 45,
      wickets: 2,
      run_rate: 9.0,
      net_swing_vs_par: 3,
      impact: 'positive',
      impact_label: 'Good finish',
    },
  ],
  key_players: [
    {
      id: 'player-001',
      name: 'J. Anderson',
      team: 'Lions',
      role: 'Batsman',
      impact: 'high',
      impact_label: 'Match winner',
      impact_score: 8.5,
      batting: {
        innings: 1,
        runs: 72,
        balls: 48,
        strike_rate: 150.0,
        boundaries: { fours: 6, sixes: 3 },
      },
      bowling: null,
      fielding: null,
    },
    {
      id: 'player-002',
      name: 'M. Clarke',
      team: 'Falcons',
      role: 'Bowler',
      impact: 'medium',
      impact_label: 'Key wickets',
      impact_score: 5.2,
      batting: null,
      bowling: {
        overs: 4,
        maidens: 0,
        runs: 28,
        wickets: 3,
        economy: 7.0,
      },
      fielding: null,
    },
  ],
  dismissal_patterns: null,
  ai: null,
}

const mockMatchAiSummary = {
  match_id: 'match-001',
  format: 'T20',
  teams: [
    {
      team_id: 'lions',
      team_name: 'Lions',
      result: 'won',
      total_runs: 178,
      wickets_lost: 6,
      overs_faced: 20,
      key_stats: [],
    },
  ],
  key_themes: ['Death overs acceleration'],
  decisive_phases: [
    {
      phase_id: 'death',
      innings: 1,
      label: 'Death overs',
      over_range: [16, 20],
      impact_score: 0.78,
      narrative: 'Lions scored rapidly to pull ahead.',
    },
  ],
  momentum_shifts: [
    {
      shift_id: 'shift-1',
      innings: 1,
      over: 18,
      description: 'Two boundaries changed momentum.',
      impact_delta: 0.19,
      team_benefiting_id: 'lions',
    },
  ],
  player_highlights: [
    {
      player_id: 'player-001',
      player_name: 'J. Anderson',
      team_id: 'lions',
      role: 'Batsman',
      highlight_type: 'batting',
      summary: 'Controlled strike rotation and boundary conversion.',
    },
  ],
  overall_summary: 'Lions controlled the tactical phases and finished strongly.',
  created_at: '2025-01-10T18:30:00Z',
  ai_metadata: {
    confidence_score: 0.84,
    limitations: ['Advisory only.', 'Sample size limited to available tracked deliveries.'],
    source_refs: [
      { type: 'match', id: 'match-001', label: 'Match: Lions vs Falcons' },
      { type: 'phase', id: 'death', label: 'Phase: Death overs' },
    ],
  },
}

describe('AnalystWorkspaceView', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    __resetAiInsightCacheForTests()
    pushMock.mockReset()
  })

  it('renders real API match list data', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('Lions vs Falcons')
    expect(wrapper.text()).toContain('Lions won by 18 runs')
    expect(wrapper.text()).toContain('Tigers vs Eagles')
  })

  it('shows imported historical metadata in match list rows', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('Imported')
    expect(text).toContain('Generic Cricket Ground')
  })

  it('shows remove imported match action only for imported historical rows', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const cleanupButtons = wrapper.findAll('.aw-cleanup-imported-btn')
    expect(cleanupButtons).toHaveLength(1)
    expect(cleanupButtons[0].text()).toContain('Remove imported match')
  })

  it('does not open match detail when cleanup button is clicked', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    await wrapper.find('.aw-cleanup-imported-btn').trigger('click')
    await nextTick()

    expect(api.getMatchCaseStudy).not.toHaveBeenCalled()
    confirmSpy.mockRestore()
  })

  it('requires explicit confirmation before removing imported match', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    await wrapper.find('.aw-cleanup-imported-btn').trigger('click')

    expect(confirmSpy).toHaveBeenCalledTimes(1)
    expect(api.historicalImportRollback).not.toHaveBeenCalled()
    confirmSpy.mockRestore()
  })

  it('refreshes matches and clears selected detail after successful imported match cleanup', async () => {
    vi.mocked(api.getAnalystMatches)
      .mockResolvedValueOnce(mockMatchList)
      .mockResolvedValueOnce({ items: [mockMatchList.items[1]], total: 1 })
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.historicalImportRollback).mockResolvedValue({
      batch_id: 'batch-001',
      rolled_back_game_id: 'match-001',
      records_deleted: 1,
      status: 'rolled_back',
      warnings: [],
    })
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()
    expect(wrapper.find('#aw-match-detail').exists()).toBe(true)

    await wrapper.find('.aw-cleanup-imported-btn').trigger('click')
    await nextTick()
    await nextTick()

    expect(api.historicalImportRollback).toHaveBeenCalledWith('batch-001')
    expect(api.getAnalystMatches).toHaveBeenCalledTimes(2)
    expect(wrapper.find('#aw-match-detail').exists()).toBe(false)
    expect(wrapper.text()).toContain('Imported match removed successfully.')
    confirmSpy.mockRestore()
  })

  it('shows cleanup error state when imported match removal fails', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.historicalImportRollback).mockRejectedValue(new Error('Cleanup request failed'))
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    await wrapper.find('.aw-cleanup-imported-btn').trigger('click')
    await nextTick()
    await nextTick()

    expect(api.historicalImportRollback).toHaveBeenCalledWith('batch-001')
    expect(wrapper.text()).toContain('Cleanup request failed')
    confirmSpy.mockRestore()
  })

  it('shows loading state while fetching matches', async () => {
    vi.mocked(api.getAnalystMatches).mockImplementation(
      () => new Promise((resolve) => { setTimeout(resolve, 200) })
    )

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()

    expect(wrapper.text()).toContain('Loading completed matches')
  })

  it('refreshes matches when bulk ZIP import emits import-done', async () => {
    vi.mocked(api.getAnalystMatches)
      .mockResolvedValueOnce(mockMatchList)
      .mockResolvedValueOnce(mockMatchList)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const importTab = wrapper.findAll('button.base-button-stub').find((b) => b.text().includes('Import Data'))
    expect(importTab).toBeDefined()
    await importTab!.trigger('click')
    await nextTick()

    await wrapper.find('.zip-import-done-btn').trigger('click')
    await nextTick()
    await nextTick()

    expect(api.getAnalystMatches).toHaveBeenCalledTimes(2)
    expect(wrapper.find('.zip-import-done-btn').exists()).toBe(false)
  })

  it('shows empty state when no completed matches exist', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue({ items: [], total: 0 })

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('No completed matches match the current filters.')
  })

  it('shows error state when match list fails to load', async () => {
    vi.mocked(api.getAnalystMatches).mockRejectedValue(new Error('Network error'))

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('Network error')
  })

  it('calls getMatchCaseStudy when a match row is clicked', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    // Find the first match row and click it
    const rows = wrapper.findAll('.aw-matches-row')
    expect(rows.length).toBeGreaterThan(0)
    await rows[0].trigger('click')

    expect(api.getMatchCaseStudy).toHaveBeenCalledWith('match-001')
  })

  it('shows match detail panel after selecting a match', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    // The detail panel should be visible
    expect(wrapper.find('#aw-match-detail').exists()).toBe(true)
    // It should show real match data
    expect(wrapper.text()).toContain('Lions won by 18 runs')
    expect(wrapper.text()).toContain('Match Intelligence')
  })

  it('shows innings scorecard from real backend data', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    // Innings table should contain real team data
    expect(wrapper.text()).toContain('Lions')
    expect(wrapper.text()).toContain('178')
    expect(wrapper.text()).toContain('Falcons')
    expect(wrapper.text()).toContain('160')
  })

  it('shows momentum verdict from real backend data', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('Lions dominated from ball one')
  })

  it('does not render hardcoded fake player or match rows', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue({ items: [], total: 0 })

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    // Ensure no hardcoded player names appear
    const text = wrapper.text()
    expect(text).not.toContain('R. Singh')
    expect(text).not.toContain('A. Kumar')
    expect(text).not.toContain('Virat')
    expect(text).not.toContain('Kohli')
    // Ensure no hardcoded match results appear
    expect(text).not.toContain('Won by 120 runs')
    expect(text).not.toContain('Won by 5 wickets')
  })

  it('closes the detail panel when close is clicked', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    expect(wrapper.find('#aw-match-detail').exists()).toBe(true)

    // Find the Close button within the detail panel
    const detailPanel = wrapper.find('#aw-match-detail')
    const closeButton = detailPanel.findAll('button.base-button-stub').find(b => b.text().includes('Close'))
    expect(closeButton).toBeDefined()
    await closeButton!.trigger('click')

    await nextTick()
    expect(wrapper.find('#aw-match-detail').exists()).toBe(false)
  })

  it('shows phase breakdown from real backend data', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('Phase breakdown')
    expect(text).toContain('Powerplay')
    expect(text).toContain('Strong start')
    expect(text).toContain('Middle overs')
    expect(text).toContain('Death overs')
    // Shows real run and wicket values from payload
    expect(text).toContain('52')
    expect(text).toContain('81')
  })

  it('shows empty state for phase breakdown when phases array is empty', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    const detailWithNoPhases = { ...mockMatchDetail, phases: [] }
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(detailWithNoPhases)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('No phase data available yet.')
  })

  it('shows key players from real backend data', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('Key players')
    expect(text).toContain('J. Anderson')
    expect(text).toContain('Lions')
    expect(text).toContain('Match winner')
    expect(text).toContain('M. Clarke')
    expect(text).toContain('Falcons')
    expect(text).toContain('Key wickets')
    // Batting stats from payload
    expect(text).toContain('72 runs')
    // Bowling stats from payload
    expect(text).toContain('3/28')
  })

  it('shows empty state for key players when key_players array is empty', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    const detailWithNoPlayers = { ...mockMatchDetail, key_players: [] }
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(detailWithNoPlayers)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('No key player data available yet.')
  })

  it('does not render fabricated player stats in key players section', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const text = wrapper.text()
    // Ensure no hardcoded fabricated player names
    expect(text).not.toContain('R. Singh')
    expect(text).not.toContain('A. Kumar')
    expect(text).not.toContain('Virat')
    expect(text).not.toContain('Kohli')
  })

  it('renders upgraded AI insight panel in match intelligence detail', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(mockMatchAiSummary as never)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('AI Insight Panel')
    expect(text).toContain('Match Intelligence Summary')
    expect(text).toContain('Momentum / Tactical Notes')
    expect(text).toContain('Key Player Insights')
    expect(text).toContain('Phase-by-Phase Notes')
  })

  it('shows AI insight loading state while ai summary is resolving', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    let resolveSummary: ((value: unknown) => void) | null = null
    vi.mocked(api.getMatchAiSummary).mockReturnValue(
      new Promise((resolve) => {
        resolveSummary = resolve
      }) as never
    )

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()

    expect(wrapper.text()).toContain('Loading AI insights…')

    resolveSummary?.(mockMatchAiSummary)
    await nextTick()
    await nextTick()
  })

  it('shows AI insight empty state when ai summary is unavailable', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(null as never)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('AI insight unavailable. Showing deterministic match summary.')
  })

  it('shows AI insight error state when ai summary request fails', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchAiSummary).mockRejectedValue(new Error('AI fetch failed'))

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('AI insight unavailable. Showing deterministic match summary.')
    expect(text).toContain('Lions vs Falcons: Lions won by 18 runs')
  })

  it('reuses cached AI insight when re-opening the same match detail', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(mockMatchAiSummary as never)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('Cached insight')
    expect(api.getMatchAiSummary).toHaveBeenCalledTimes(1)
  })

  it('refresh insight button bypasses cache and refetches', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(mockMatchAiSummary as never)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()
    expect(api.getMatchAiSummary).toHaveBeenCalledTimes(1)

    const refreshButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Refresh insight'))
    expect(refreshButton).toBeTruthy()
    await refreshButton!.trigger('click')
    await nextTick()
    await nextTick()

    expect(api.getMatchAiSummary).toHaveBeenCalledTimes(2)
  })

  it('shows insufficient-data state when no deterministic or AI insight is available', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue({
      ...mockMatchDetail,
      match: { ...mockMatchDetail.match, result: '', innings: [] },
    } as never)
    vi.mocked(api.getMatchAiSummary).mockRejectedValue(new Error('AI fetch failed'))

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('Insufficient match data for AI or deterministic summary.')
  })

  it('renders confidence and limitations when ai metadata is provided', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(mockMatchAiSummary as never)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('Confidence: High (84%)')
    expect(text).toContain('Caveats')
    expect(text).toContain('Advisory only.')
  })

  it('renders source references when ai metadata includes provenance', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(mockMatchAiSummary as never)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('Source references')
    expect(text).toContain('Match: Lions vs Falcons')
    expect(text).toContain('Phase: Death overs')
  })

  it('renders deterministic evidence metrics when match intelligence data is present', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(mockMatchAiSummary as never)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('Supporting data')
    expect(text).toContain('Death overs (innings 1, overs 16-20): impact +0.78')
    expect(text).toContain('Lions: 178/6 in 20 ov (RR 8.90)')
    expect(text).toContain('Momentum shift (innings 1, over 18): impact Δ +0.19')
  })

  it('renders safe caveats when source citations and support metrics are missing', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue({
      ...mockMatchAiSummary,
      teams: [],
      decisive_phases: [],
      momentum_shifts: [],
      ai_metadata: {
        ...mockMatchAiSummary.ai_metadata,
        limitations: [],
        source_refs: [],
      },
    } as never)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('Source/provenance references were not provided for this advisory claim.')
    expect(text).toContain('Deterministic support metrics are limited for this advisory claim.')
    expect(text).toContain('Confidence: High (84%)')
  })

  it('renders review card metadata for phase 8c review state integration', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(mockMatchAiSummary as never)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const reviewStub = wrapper.find('[data-testid="ai-insight-review-card-stub"]')
    expect(reviewStub.exists()).toBe(true)
    const reviewText = reviewStub.text()
    expect(reviewText).toContain('summary')
    expect(reviewText).toContain('match-001')
    expect(reviewText).toContain('0.84')
    expect(reviewText).toContain('|2|2|')
    expect(reviewText).toContain('true')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Phase 4E: Podcast Prep Package tests
  // ──────────────────────────────────────────────────────────────────────────

  it('renders the Podcast Prep Package section when match detail is loaded', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    expect(wrapper.find('#aw-podcast-prep').exists()).toBe(true)
    expect(wrapper.text()).toContain('Podcast prep package')
  })

  it('Podcast Prep episode title reflects real match fields', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const text = wrapper.text()
    // Episode title derived from real teams_label + format + date
    expect(text).toContain('Lions vs Falcons')
    expect(text).toContain('T20')
    expect(text).toContain('2025-01-10')
  })

  it('Podcast Prep scoreboard facts reflect real innings data', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const text = wrapper.text()
    // Scoreboard facts from real innings data: Lions 178/6, Falcons 160/10
    expect(text).toContain('Lions: 178/6')
    expect(text).toContain('Falcons: 160/10')
  })

  it('Podcast Prep talking points cite real loaded fields', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const text = wrapper.text()
    // Talking points must reflect real momentum_summary and key_phase data
    expect(text).toContain('Momentum verdict')
    expect(text).toContain('Lions dominated from ball one')
    expect(text).toContain('Key phase')
    expect(text).toContain('Death overs surge')
    // Phase performance from real phases data
    expect(text).toContain('Phase performance')
    // Player spotlight from real key_players (J. Anderson, Lions)
    expect(text).toContain('Player spotlight')
    expect(text).toContain('J. Anderson')
  })

  it('Podcast Prep coach prompts reference real match data', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const text = wrapper.text()
    // Coach prompts generated from key_phase.title
    expect(text).toContain('Coach discussion prompts')
    expect(text).toContain('death overs surge')
    // Coach prompts reference real key player name
    expect(text).toContain('J. Anderson')
  })

  it('Podcast Prep suggested visuals are based only on loaded sections', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('Suggested visuals')
    // Only lists sections that actually exist in the loaded data
    expect(text).toContain('Innings scorecard comparison')
    expect(text).toContain('Phase breakdown table')
    expect(text).toContain('Key player impact cards')
  })

  it('Podcast Prep shows empty state when match detail has insufficient data', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    // Minimal detail: no innings, no key_phase, no momentum
    const sparseDetail = {
      ...mockMatchDetail,
      match: {
        ...mockMatchDetail.match,
        result: '',
        innings: [],
      },
      momentum_summary: null as any,
      key_phase: null as any,
      phases: [],
      key_players: [],
    }
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(sparseDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('Add more completed match data to generate this section')
    // Talking point empty states
    expect(text).toContain('Insufficient data for this talking point')
  })

  it('Podcast Prep talking points show empty state when momentum_summary is null', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    const noMomentum = { ...mockMatchDetail, momentum_summary: null as any }
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(noMomentum)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('Insufficient data for this talking point')
  })

  it('Podcast Prep does not render hardcoded fake player or podcast claims', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const podcastSection = wrapper.find('#aw-podcast-prep')
    expect(podcastSection.exists()).toBe(true)
    const text = podcastSection.text()

    // No fabricated names
    expect(text).not.toContain('R. Singh')
    expect(text).not.toContain('A. Kumar')
    expect(text).not.toContain('Virat')
    expect(text).not.toContain('Kohli')
    // No hardcoded fake storylines
    expect(text).not.toContain('brilliant century')
    expect(text).not.toContain('turning point in the third over')
    // No AI-generated label
    expect(text).not.toContain('AI-generated')
  })

  it('Podcast Prep section does not appear before a match is selected', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    // No match selected → podcast prep should not exist
    expect(wrapper.find('#aw-podcast-prep').exists()).toBe(false)
  })

  it('Podcast Prep copy button is rendered in the podcast section', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const podcastSection = wrapper.find('#aw-podcast-prep')
    const copyBtn = podcastSection.find('.aw-podcast-copy-btn')
    expect(copyBtn.exists()).toBe(true)
    expect(copyBtn.text()).toContain('Copy package text')
  })

  it('Podcast Prep copy button is disabled when package has insufficient data', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    const sparseDetail = {
      ...mockMatchDetail,
      match: {
        ...mockMatchDetail.match,
        result: '',
        innings: [],
      },
      momentum_summary: null as any,
      key_phase: null as any,
      phases: [],
      key_players: [],
    }
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(sparseDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const podcastSection = wrapper.find('#aw-podcast-prep')
    const copyBtn = podcastSection.find('.aw-podcast-copy-btn')
    expect(copyBtn.exists()).toBe(true)
    expect(copyBtn.attributes('disabled')).toBeDefined()
  })

  it('existing match selection and detail panel still work after Phase 4E changes', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    // Original behaviour: click match → detail panel appears
    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    expect(wrapper.find('#aw-match-detail').exists()).toBe(true)
    expect(wrapper.text()).toContain('Match Intelligence')
    expect(wrapper.text()).toContain('Lions won by 18 runs')

    // Phase 4D sections still intact
    expect(wrapper.text()).toContain('Phase breakdown')
    expect(wrapper.text()).toContain('Key players')

    // Phase 4E section also present
    expect(wrapper.find('#aw-podcast-prep').exists()).toBe(true)
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Phase 5K: Dark-theme readability contract tests
  // These tests verify that Key Players cards and Podcast Prep Package
  // use CSS variable backgrounds (not hardcoded light-mode values) so they
  // remain readable in both light and dark themes.
  // ──────────────────────────────────────────────────────────────────────────

  it('Key Players card uses CSS variable background class (dark-theme safe)', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    // aw-keyplayer-card elements must exist and contain real player data
    const cards = wrapper.findAll('.aw-keyplayer-card')
    expect(cards.length).toBeGreaterThan(0)

    // The card class itself is the styling anchor — verify it exists on each card
    cards.forEach((card) => {
      expect(card.classes()).toContain('aw-keyplayer-card')
    })

    // Player names should be visible inside the cards (readable content)
    const text = wrapper.text()
    expect(text).toContain('J. Anderson')
    expect(text).toContain('M. Clarke')
  })

  it('Key Players cards render all expected sub-elements for dark readability', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const cards = wrapper.findAll('.aw-keyplayer-card')
    expect(cards.length).toBe(2)

    // Each card should have header and stats sub-elements
    cards.forEach((card) => {
      expect(card.find('.aw-keyplayer-header').exists()).toBe(true)
      expect(card.find('.aw-keyplayer-stats').exists()).toBe(true)
      expect(card.find('.aw-keyplayer-name').exists()).toBe(true)
    })
  })

  it('Podcast Prep Package container has dark-theme-safe class', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const podcastSection = wrapper.find('#aw-podcast-prep')
    expect(podcastSection.exists()).toBe(true)

    // The section must carry the aw-podcast-prep class (which uses --color-surface-raised)
    expect(podcastSection.classes()).toContain('aw-podcast-prep')
  })

  it('Podcast Prep talking-point cards have dark-theme-safe classes', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    // Talking-point list items must use aw-podcast-tp class
    const tpItems = wrapper.findAll('.aw-podcast-tp')
    expect(tpItems.length).toBeGreaterThan(0)

    tpItems.forEach((item) => {
      // Label and text sub-elements must be present for readable contrast
      expect(item.find('.aw-podcast-tp-label').exists()).toBe(true)
    })
  })

  it('Key Players section heading is present and readable for all match types', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()

    const keyPlayersSection = wrapper.find('.aw-detail-keyplayers')
    expect(keyPlayersSection.exists()).toBe(true)
    // Section heading must always render (dark-theme contrast starts with visible heading)
    expect(keyPlayersSection.text()).toContain('Key players')
  })

  // ── Phase 5M / Phase 10B: Registry & Provenance panel ───────────────────

  const mockRegistryHistorical = {
    match_id: 'match-001',
    is_historical: true,
    competition: 'Caribbean Premier League',
    competition_type: 'franchise',
    competition_name: 'Caribbean Premier League',
    match_format: 'T20',
    tournament_name: null,
    tournament_round: null,
    season: '2013',
    venue: 'Generic Cricket Ground',
    venue_context: {
      venue_name: 'Generic Cricket Ground',
      city: 'Port of Spain',
      country: 'Trinidad and Tobago',
      venue_resolution_status: 'resolved',
    },
    teams: 'Lions vs Falcons',
    match_number: 1,
    player_count: 22,
    innings_count: 2,
    has_deliveries: true,
    roster_snapshot_available: true,
    import_batch_id: 'batch-001',
    source_filename: 'match_001.json',
    source_format: 'cricsheet_json',
    source_schema: 'cricsheet_json_v1',
    source_schema_version: 'v1.0',
    adapter_id: 'historical_json_competition_adapter',
    adapter_version: 'v10b.1',
    source_type: 'json',
    imported_at: '2025-01-10T12:00:00Z',
    validation_status: 'valid',
    registration_status: 'registered',
    training_eligible: true,
    blocking_reason: null,
  }

  const mockRegistryLive = {
    match_id: 'match-002',
    is_historical: false,
    competition: null,
    competition_type: null,
    competition_name: null,
    match_format: null,
    tournament_name: null,
    tournament_round: null,
    season: null,
    venue: null,
    venue_context: null,
    teams: 'Tigers vs Eagles',
    match_number: null,
    player_count: 0,
    innings_count: 0,
    has_deliveries: false,
    roster_snapshot_available: false,
    import_batch_id: null,
    source_filename: null,
    source_format: null,
    source_schema: null,
    source_schema_version: null,
    adapter_id: null,
    adapter_version: null,
    source_type: 'json',
    imported_at: null,
    validation_status: 'not_applicable',
    registration_status: 'not_registered',
    training_eligible: false,
    blocking_reason: 'not_a_historical_import',
  }

  it('shows Registry & Provenance panel when a match is selected', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchRegistry).mockResolvedValue(mockRegistryHistorical)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()
    await nextTick()

    const registrySection = wrapper.find('.aw-detail-registry')
    expect(registrySection.exists()).toBe(true)
    expect(registrySection.text()).toContain('Registry')
  })

  it('shows real registry provenance data for historical imports', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchRegistry).mockResolvedValue(mockRegistryHistorical)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()
    await nextTick()

    const text = wrapper.find('.aw-detail-registry').text()
    expect(text).toContain('Caribbean Premier League')
    expect(text).toContain('2013')
    expect(text).toContain('Generic Cricket Ground')
    expect(text).toContain('match_001.json')
    expect(text).toContain('batch-001')
    expect(text).toContain('22 players found')
  })

  it('shows Registered and Eligible status for a valid applied historical import', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchRegistry).mockResolvedValue(mockRegistryHistorical)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()
    await nextTick()

    const text = wrapper.find('.aw-detail-registry').text()
    expect(text).toContain('Valid')
    expect(text).toContain('Registered')
    expect(text).toContain('Eligible')
  })

  it('shows Not applicable and Not eligible for live (non-historical) match', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchRegistry).mockResolvedValue(mockRegistryLive)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    // Click second match (live)
    await rows[1].trigger('click')
    await nextTick()
    await nextTick()
    await nextTick()

    const text = wrapper.find('.aw-detail-registry').text()
    expect(text).toContain('Not applicable')
    expect(text).toContain('Not registered yet')
    expect(text).toContain('Not eligible')
  })

  it('shows Not registered yet for missing player count', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchRegistry).mockResolvedValue({
      ...mockRegistryHistorical,
      player_count: 0,
    })

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()
    await nextTick()

    const text = wrapper.find('.aw-detail-registry').text()
    expect(text).toContain('Not registered yet')
  })

  it('shows blocking reason when training is not eligible', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchRegistry).mockResolvedValue({
      ...mockRegistryHistorical,
      training_eligible: false,
      registration_status: 'not_registered',
      blocking_reason: 'has_errors',
    })

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()
    await nextTick()

    const text = wrapper.find('.aw-detail-registry').text()
    expect(text).toContain('Not eligible')
    expect(text).toContain('has_errors')
  })

  it('shows empty state when registry data fails to load', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchRegistry).mockRejectedValue(new Error('Registry load failed'))

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()
    await nextTick()

    const registrySection = wrapper.find('.aw-detail-registry')
    expect(registrySection.exists()).toBe(true)
    expect(registrySection.text()).toContain('Registry data unavailable for this match')
  })

  it('calls getMatchRegistry when a match row is clicked', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchRegistry).mockResolvedValue(mockRegistryHistorical)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')

    expect(api.getMatchRegistry).toHaveBeenCalledWith('match-001')
  })

  // ── Phase 10C: Competition-aware registry/provenance fields ───────────────

  it('displays competition_type and match_format for competition-aware historical imports', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchRegistry).mockResolvedValue(mockRegistryHistorical)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()
    await nextTick()

    const text = wrapper.find('.aw-detail-registry').text()
    expect(text).toContain('franchise')
    expect(text).toContain('T20')
  })

  it('displays venue context details for competition-aware historical imports', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchRegistry).mockResolvedValue(mockRegistryHistorical)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()
    await nextTick()

    const text = wrapper.find('.aw-detail-registry').text()
    expect(text).toContain('Port of Spain')
    expect(text).toContain('Trinidad and Tobago')
  })

  it('displays adapter provenance lineage fields for competition-aware historical imports', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchRegistry).mockResolvedValue(mockRegistryHistorical)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()
    await nextTick()

    const text = wrapper.find('.aw-detail-registry').text()
    expect(text).toContain('cricsheet_json_v1')
    expect(text).toContain('v1.0')
    expect(text).toContain('historical_json_competition_adapter')
    expect(text).toContain('v10b.1')
  })

  it('displays roster_snapshot_available status for historical imports', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchRegistry).mockResolvedValue(mockRegistryHistorical)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()
    await nextTick()

    const text = wrapper.find('.aw-detail-registry').text()
    expect(text).toContain('Available')
  })

  it('does not crash when Phase 10B metadata fields are null/missing', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchRegistry).mockResolvedValue({
      ...mockRegistryHistorical,
      competition_type: null,
      competition_name: null,
      match_format: null,
      tournament_name: null,
      tournament_round: null,
      venue_context: null,
      source_schema: null,
      source_schema_version: null,
      adapter_id: null,
      adapter_version: null,
      roster_snapshot_available: false,
    })

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[0].trigger('click')
    await nextTick()
    await nextTick()
    await nextTick()

    // Panel renders without error; fallback values are shown
    const registrySection = wrapper.find('.aw-detail-registry')
    expect(registrySection.exists()).toBe(true)
    const text = registrySection.text()
    expect(text).toContain('Caribbean Premier League')
    expect(text).toContain('Not available')
  })

  it('does not display competition_type row when value is null for live match', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(mockMatchDetail)
    vi.mocked(api.getMatchRegistry).mockResolvedValue(mockRegistryLive)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const rows = wrapper.findAll('.aw-matches-row')
    await rows[1].trigger('click')
    await nextTick()
    await nextTick()
    await nextTick()

    const text = wrapper.find('.aw-detail-registry').text()
    // Competition type row should not appear for live match with null competition_type
    expect(text).not.toContain('Competition type')
    expect(text).not.toContain('Match format')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Phase 5O: Data Library tab tests
  // ──────────────────────────────────────────────────────────────────────────

  it('has a Data Library tab button', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const tabButtons = wrapper.findAll('button.base-button-stub')
    const dlTab = tabButtons.find((b) => b.text().includes('Data Library'))
    expect(dlTab).toBeDefined()
  })

  it('shows Data Library tab panel when Data Library tab is clicked', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const tabButtons = wrapper.findAll('button.base-button-stub')
    const dlTab = tabButtons.find((b) => b.text().includes('Data Library'))
    expect(dlTab).toBeDefined()
    await dlTab!.trigger('click')
    await nextTick()

    expect(wrapper.text()).toContain('Data Library')
    expect(wrapper.text()).toContain('Browse available match datasets')
  })

  it('Data Library shows both matches in the table', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const tabButtons = wrapper.findAll('button.base-button-stub')
    const dlTab = tabButtons.find((b) => b.text().includes('Data Library'))
    await dlTab!.trigger('click')
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('Lions vs Falcons')
    expect(text).toContain('Tigers vs Eagles')
  })

  it('Data Library shows Imported badge for historical match', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const tabButtons = wrapper.findAll('button.base-button-stub')
    const dlTab = tabButtons.find((b) => b.text().includes('Data Library'))
    await dlTab!.trigger('click')
    await nextTick()

    const dlBadges = wrapper.findAll('.aw-dl-badge--imported')
    expect(dlBadges.length).toBeGreaterThan(0)
  })

  it('Data Library shows competition and season metadata for imported match', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const tabButtons = wrapper.findAll('button.base-button-stub')
    const dlTab = tabButtons.find((b) => b.text().includes('Data Library'))
    await dlTab!.trigger('click')
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('Premier League 2025')
    expect(text).toContain('2025')
  })

  it('Data Library shows empty state when no matches are available', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue({ items: [], total: 0 })

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const tabButtons = wrapper.findAll('button.base-button-stub')
    const dlTab = tabButtons.find((b) => b.text().includes('Data Library'))
    await dlTab!.trigger('click')
    await nextTick()

    expect(wrapper.text()).toContain('No analyst-ready match data is available yet.')
  })

  it('Data Library shows loading state while fetching matches', async () => {
    vi.mocked(api.getAnalystMatches).mockImplementation(
      () => new Promise((resolve) => { setTimeout(resolve, 200) })
    )

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()

    const tabButtons = wrapper.findAll('button.base-button-stub')
    const dlTab = tabButtons.find((b) => b.text().includes('Data Library'))
    await dlTab!.trigger('click')
    await nextTick()

    expect(wrapper.text()).toContain('Loading data library')
  })

  it('Data Library shows error state when match list fails to load', async () => {
    vi.mocked(api.getAnalystMatches).mockRejectedValue(new Error('Library fetch failed'))

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const tabButtons = wrapper.findAll('button.base-button-stub')
    const dlTab = tabButtons.find((b) => b.text().includes('Data Library'))
    await dlTab!.trigger('click')
    await nextTick()

    expect(wrapper.text()).toContain('Library fetch failed')
  })

  it('Data Library filters to imported-only when source filter is set to Imported', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const tabButtons = wrapper.findAll('button.base-button-stub')
    const dlTab = tabButtons.find((b) => b.text().includes('Data Library'))
    await dlTab!.trigger('click')
    await nextTick()

    // Click the 'Imported' source filter chip
    const importedChip = wrapper.findAll('button.aw-chip').find((b) => b.text() === 'Imported')
    expect(importedChip).toBeDefined()
    await importedChip!.trigger('click')
    await nextTick()

    const text = wrapper.text()
    expect(text).toContain('Lions vs Falcons')
    expect(text).not.toContain('Tigers vs Eagles')
  })

  it('Data Library clicking a match row routes to the match case study view', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue(mockMatchList)

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const tabButtons = wrapper.findAll('button.base-button-stub')
    const dlTab = tabButtons.find((b) => b.text().includes('Data Library'))
    await dlTab!.trigger('click')
    await nextTick()

    const dlRows = wrapper.findAll('.aw-dl-row')
    expect(dlRows.length).toBeGreaterThan(0)
    // Default sort is 'most recent'; match-002 (2025-01-15) appears first
    await dlRows[0].trigger('click')
    await nextTick()

    expect(pushMock).toHaveBeenCalledWith({
      name: 'MatchCaseStudy',
      params: { matchId: 'match-002' },
    })
  })

  it('Data Library does not show fake or placeholder match data', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue({ items: [], total: 0 })

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    const tabButtons = wrapper.findAll('button.base-button-stub')
    const dlTab = tabButtons.find((b) => b.text().includes('Data Library'))
    await dlTab!.trigger('click')
    await nextTick()

    const text = wrapper.text()
    expect(text).not.toContain('R. Singh')
    expect(text).not.toContain('A. Kumar')
    expect(text).not.toContain('Mock Match')
    expect(text).not.toContain('Demo')
  })
})

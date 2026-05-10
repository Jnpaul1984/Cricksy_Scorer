import { mount } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick } from 'vue'

import * as api from '@/services/api'
import AnalystWorkspaceView from '@/views/AnalystWorkspaceView.vue'

// Mock vue-router
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

// Mock the api module
vi.mock('@/services/api', () => ({
  getAnalystMatches: vi.fn(),
  getMatchCaseStudy: vi.fn(),
  getAnalystExportData: vi.fn(),
}))

// Stub child components that are not under test
const globalStubs = {
  BaseCard: { template: '<div class="base-card-stub"><slot /></div>' },
  BaseButton: { template: '<button class="base-button-stub" @click="$emit(\'click\')"><slot /></button>', emits: ['click'] },
  BaseBadge: { template: '<span class="base-badge-stub"><slot /></span>' },
  BaseInput: { template: '<input class="base-input-stub" />' },
  ImpactBar: { template: '<div class="impact-bar-stub" />' },
  MiniSparkline: { template: '<div class="mini-sparkline-stub" />' },
  AiCalloutsPanel: { template: '<div class="ai-callouts-stub" />' },
  AnalyticsTablesWidget: { template: '<div class="analytics-tables-stub" />' },
  ExportUI: { template: '<div class="export-ui-stub" />' },
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
      venue: null,
      match_datetime: null,
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
      match_datetime: null,
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

describe('AnalystWorkspaceView', () => {
  beforeEach(() => {
    vi.resetAllMocks()
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

  it('shows loading state while fetching matches', async () => {
    vi.mocked(api.getAnalystMatches).mockImplementation(
      () => new Promise((resolve) => { setTimeout(resolve, 200) })
    )

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()

    expect(wrapper.text()).toContain('Loading matches')
  })

  it('shows empty state when no completed matches exist', async () => {
    vi.mocked(api.getAnalystMatches).mockResolvedValue({ items: [], total: 0 })

    const wrapper = mount(AnalystWorkspaceView, { global: { stubs: globalStubs } })
    await nextTick()
    await nextTick()

    expect(wrapper.text()).toContain('No matches found')
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
})

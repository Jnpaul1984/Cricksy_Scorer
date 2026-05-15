import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import { __resetAiInsightCacheForTests } from '@/services/aiInsightCache'
import * as api from '@/services/api'
import MatchCaseStudyView from '@/views/MatchCaseStudyView.vue'

const pushMock = vi.fn()
const backMock = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { matchId: 'match-001' } }),
  useRouter: () => ({ push: pushMock, back: backMock }),
}))

vi.mock('@/services/api', () => ({
  getMatchCaseStudy: vi.fn(),
  getMatchAiSummary: vi.fn(),
}))

vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    canAnalyze: true,
  }),
}))

const globalStubs = {
  BaseCard: { template: '<div class="base-card-stub"><slot /></div>' },
  BaseButton: {
    template: '<button class="base-button-stub" @click="$emit(\'click\', $event)"><slot /></button>',
    emits: ['click'],
  },
  BaseBadge: { template: '<span class="base-badge-stub"><slot /></span>' },
  ImpactBar: { template: '<div class="impact-bar-stub" />' },
  MiniSparkline: { template: '<div class="mini-sparkline-stub" />' },
  AiCalloutsPanel: { template: '<div class="ai-callouts-panel-stub" />' },
  AiInsightReviewCard: { template: '<div data-testid="ai-insight-review-card-stub" />' },
}

const baseCaseStudy = {
  match: {
    id: 'match-001',
    date: '2025-01-10',
    format: 'T20',
    teams_label: 'Lions vs Falcons',
    result: 'Lions won by 18 runs',
    innings: [
      { team: 'Lions', runs: 178, wickets: 6, overs: 20, run_rate: 8.9 },
      { team: 'Falcons', runs: 160, wickets: 10, overs: 19.4, run_rate: 8.2 },
    ],
  },
  momentum_summary: null,
  key_phase: null,
  phases: [],
  key_players: [],
  dismissal_patterns: null,
  ai: null,
}

const groundedAiSummary = {
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
  key_themes: ['Death overs surge'],
  decisive_phases: [
    {
      phase_id: 'death',
      innings: 1,
      label: 'Death overs',
      over_range: [16, 20],
      impact_score: 0.78,
      narrative: 'Lions accelerated hard at the death.',
    },
  ],
  momentum_shifts: [],
  player_highlights: [],
  overall_summary: 'Lions controlled the decisive scoring phases.',
  created_at: '2025-01-10T18:30:00Z',
  ai_metadata: {
    confidence_score: 0.84,
    limitations: ['Advisory only.'],
    grounding_summary: 'Based on innings totals and phase swing analysis.',
    source_refs: [
      { type: 'match', id: 'match-001', label: 'Match: Lions vs Falcons' },
      { type: 'innings', id: 'innings_1', label: 'Innings 1: Lions 178/6 in 20 overs' },
      { type: 'phase', id: 'death', label: 'Phase: Death overs' },
    ],
  },
}

async function flushAsync() {
  // The view loads case-study data and AI summary in separate onMounted async calls,
  // so two microtask/tick rounds keep the test aligned with the component lifecycle.
  await Promise.resolve()
  await nextTick()
  await Promise.resolve()
  await nextTick()
}

describe('MatchCaseStudyView', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    __resetAiInsightCacheForTests()
    pushMock.mockReset()
    backMock.mockReset()
  })

  it('renders advisory evidence when ai grounding metadata is present', async () => {
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(baseCaseStudy as never)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(groundedAiSummary as never)

    const wrapper = mount(MatchCaseStudyView, {
      global: { stubs: globalStubs },
    })
    await flushAsync()

    expect(wrapper.text()).toContain('AI Advisory')
    expect(wrapper.text()).toContain('Confidence: 84%')
    expect(wrapper.text()).toContain('Supporting data')
    expect(wrapper.text()).toContain('Based on innings totals and phase swing analysis.')
    expect(wrapper.text()).toContain('Death overs (innings 1, overs 16-20): impact +0.78')
    expect(wrapper.text()).toContain('Lions: 178/6 in 20 ov (RR 8.90)')
    expect(wrapper.text()).toContain('Source references')
    expect(wrapper.text()).toContain('Match: Lions vs Falcons')
    expect(wrapper.text()).toContain('Phase: Death overs')
    expect(wrapper.text()).toContain('Caveats')
    expect(wrapper.text()).toContain('Advisory only.')
    expect(wrapper.find('[data-testid="ai-insight-review-card-stub"]').exists()).toBe(true)
  })

  it('renders safe caveats when citations and deterministic support are missing', async () => {
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(baseCaseStudy as never)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue({
      ...groundedAiSummary,
      teams: [],
      decisive_phases: [],
      momentum_shifts: [],
      ai_metadata: {
        ...groundedAiSummary.ai_metadata,
        limitations: [],
        source_refs: [],
        grounding_summary: '',
      },
    } as never)

    const wrapper = mount(MatchCaseStudyView, {
      global: { stubs: globalStubs },
    })
    await flushAsync()

    expect(wrapper.text()).toContain('AI Advisory')
    expect(wrapper.text()).toContain('Confidence: 84%')
    expect(wrapper.text()).toContain('Source/provenance references were not provided for this advisory claim.')
    expect(wrapper.text()).toContain('Deterministic support metrics are limited for this advisory claim.')
  })

  it('reuses cached AI summary on remount', async () => {
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(baseCaseStudy as never)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(groundedAiSummary as never)

    const first = mount(MatchCaseStudyView, {
      global: { stubs: globalStubs },
    })
    await flushAsync()
    expect(first.text()).toContain('AI Advisory')
    first.unmount()

    const second = mount(MatchCaseStudyView, {
      global: { stubs: globalStubs },
    })
    await flushAsync()
    expect(second.text()).toContain('AI Match Summary')
    expect(api.getMatchAiSummary).toHaveBeenCalledTimes(1)
  })

  it('refresh button bypasses cache and refetches', async () => {
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(baseCaseStudy as never)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(groundedAiSummary as never)

    const wrapper = mount(MatchCaseStudyView, {
      global: { stubs: globalStubs },
    })
    await flushAsync()
    expect(api.getMatchAiSummary).toHaveBeenCalledTimes(1)

    const refreshButton = wrapper
      .findAll('button')
      .find((btn) => btn.text().includes('Refresh summary'))
    expect(refreshButton).toBeTruthy()
    await refreshButton!.trigger('click')
    await flushAsync()
    expect(api.getMatchAiSummary).toHaveBeenCalledTimes(2)
  })

  it('shows deterministic fallback when AI request fails', async () => {
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(baseCaseStudy as never)
    vi.mocked(api.getMatchAiSummary).mockRejectedValue(new Error('AI unavailable'))

    const wrapper = mount(MatchCaseStudyView, {
      global: { stubs: globalStubs },
    })
    await flushAsync()

    expect(wrapper.text()).toContain('AI insight unavailable. Showing deterministic match summary.')
    expect(wrapper.text()).toContain('Lions vs Falcons: Lions won by 18 runs')
  })

  it('shows insufficient-data state when AI fails and deterministic data is missing', async () => {
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue({
      ...baseCaseStudy,
      match: { ...baseCaseStudy.match, result: '', innings: [] },
    } as never)
    vi.mocked(api.getMatchAiSummary).mockRejectedValue(new Error('AI unavailable'))

    const wrapper = mount(MatchCaseStudyView, {
      global: { stubs: globalStubs },
    })
    await flushAsync()

    expect(wrapper.text()).toContain('Insufficient match data for AI or deterministic summary.')
  })
})

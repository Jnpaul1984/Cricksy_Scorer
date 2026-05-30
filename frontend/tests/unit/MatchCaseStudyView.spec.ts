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
  AiCalloutsPanel: {
    props: ['callouts'],
    template: '<div class="ai-callouts-panel-stub">{{ (callouts || []).map((c) => c.title).join(" | ") }}</div>',
  },
  AiInsightReviewCard: { template: '<div data-testid="ai-insight-review-card-stub" />' },
}

const baseCaseStudy = {
  analysis_mode: 'limited_overs',
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
  innings_analysis: [],
  match_callouts: [],
  match_level_summary: null,
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

const clipboardWriteMock = vi.fn()

async function flushAsync() {
  // The view loads case-study data and AI summary in separate onMounted async calls,
  // so two microtask/tick rounds keep the test aligned with the component lifecycle.
  await Promise.resolve()
  await nextTick()
  await Promise.resolve()
  await nextTick()
}

function createDeferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((res) => {
    resolve = res
  })
  return { promise, resolve }
}

describe('MatchCaseStudyView', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    __resetAiInsightCacheForTests()
    pushMock.mockReset()
    backMock.mockReset()
    clipboardWriteMock.mockReset()
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: clipboardWriteMock },
      configurable: true,
    })
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

  it('normalizes match result card and deterministic fallback display text', async () => {
    const rawResult = 'Durham won by 1 runs'
    const caseStudyPayload = {
      ...baseCaseStudy,
      match: {
        ...baseCaseStudy.match,
        teams_label: 'Durham vs Warwickshire',
        format: 'ODI',
        result: rawResult,
      },
    }
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(caseStudyPayload as never)
    vi.mocked(api.getMatchAiSummary).mockRejectedValue(new Error('AI unavailable'))

    const wrapper = mount(MatchCaseStudyView, { global: { stubs: globalStubs } })
    await flushAsync()

    const text = wrapper.text()
    expect(text).toContain('Durham won by 1 run')
    expect(text).toContain('Durham vs Warwickshire: Durham won by 1 run')
    expect(caseStudyPayload.match.result).toBe(rawResult)
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

  it('switches innings-specific story, dismissal, and callouts', async () => {
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue({
      ...baseCaseStudy,
      innings_analysis: [
        {
          innings_index: 0,
          team: 'Lions',
          deterministic_summary: 'Innings 1 summary',
          momentum_summary: { title: 'Innings 1 momentum', subtitle: 'I1 subtitle' },
          key_phase: { title: 'I1 key phase', detail: 'I1 detail' },
          phases: [],
          key_players: [],
          key_players_scope: 'match',
          dismissal_patterns: {
            summary: 'I1 dismissals',
            wickets_by_phase: [{ phase_id: 'powerplay', wickets: 1 }],
            wickets_by_over_band: [{ band: '1-6', wickets: 1 }],
            dismissal_types: [{ type: 'bowled', wickets: 1 }],
            wicket_timeline: [{ wicket_number: 1, over: 2, dismissal_type: 'bowled' }],
          },
          story_blocks: {
            opening_story: 'I1 opening',
            middle_overs_story: 'I1 middle',
            death_overs_story: 'I1 death',
            scoring_acceleration: 'I1 acceleration',
            wickets_by_phase: 'I1 wickets by phase',
            strongest_phase: 'I1 strongest',
            weakest_phase: 'I1 weakest',
            innings_outcome_contribution: 'I1 contribution',
          },
          callouts: [
            {
              title: 'I1 callout',
              level: 'innings',
              innings: 1,
              phase: 'Middle overs',
              category: 'momentum',
              severity: 'warning',
              explanation: 'I1 explanation',
              source_metrics: ['runs=30'],
              confidence: 0.9,
              why_it_matters: 'I1 why',
            },
          ],
        },
        {
          innings_index: 1,
          team: 'Falcons',
          deterministic_summary: 'Innings 2 summary',
          momentum_summary: { title: 'Innings 2 momentum', subtitle: 'I2 subtitle' },
          key_phase: { title: 'I2 key phase', detail: 'I2 detail' },
          phases: [],
          key_players: [],
          key_players_scope: 'match',
          dismissal_patterns: {
            summary: 'I2 dismissals',
            wickets_by_phase: [{ phase_id: 'death', wickets: 2 }],
            wickets_by_over_band: [{ band: '16+', wickets: 2 }],
            dismissal_types: [{ type: 'caught', wickets: 2 }],
            wicket_timeline: [{ wicket_number: 1, over: 17, dismissal_type: 'caught' }],
          },
          story_blocks: {
            opening_story: 'I2 opening',
            middle_overs_story: 'I2 middle',
            death_overs_story: 'I2 death',
            scoring_acceleration: 'I2 acceleration',
            wickets_by_phase: 'I2 wickets by phase',
            strongest_phase: 'I2 strongest',
            weakest_phase: 'I2 weakest',
            innings_outcome_contribution: 'I2 contribution',
          },
          callouts: [
            {
              title: 'I2 callout',
              level: 'innings',
              innings: 2,
              phase: 'Death overs',
              category: 'batting',
              severity: 'positive',
              explanation: 'I2 explanation',
              source_metrics: ['runs=50'],
              confidence: 0.85,
              why_it_matters: 'I2 why',
            },
          ],
        },
      ],
    } as never)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(groundedAiSummary as never)

    const wrapper = mount(MatchCaseStudyView, { global: { stubs: globalStubs } })
    await flushAsync()

    expect(wrapper.text()).toContain('Innings 1 summary')
    expect(wrapper.text()).toContain('I1 dismissals')
    expect(wrapper.text()).toContain('I1 callout')

    const inningsTwoButton = wrapper
      .findAll('button')
      .find((btn) => btn.text().includes('Innings 2'))
    expect(inningsTwoButton).toBeTruthy()
    await inningsTwoButton!.trigger('click')
    await flushAsync()

    expect(wrapper.text()).toContain('Innings 2 summary')
    expect(wrapper.text()).toContain('I2 dismissals')
    expect(wrapper.text()).toContain('I2 callout')
  })

  it('renders podcast prep assistant and generates reviewable cards', async () => {
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(baseCaseStudy as never)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(groundedAiSummary as never)

    const wrapper = mount(MatchCaseStudyView, { global: { stubs: globalStubs } })
    await flushAsync()

    expect(wrapper.find('#cs-podcast-prep').exists()).toBe(true)
    expect(wrapper.text()).toContain('AI wording only. Facts come from deterministic match data and require human review before use.')

    await wrapper.get('[data-testid="podcast-generate-btn"]').trigger('click')
    await flushAsync()

    const cards = wrapper.findAll('[data-testid^="podcast-card-"]')
    expect(cards.length).toBe(9)
    expect(wrapper.text()).toContain('Needs review / rejected (9)')
  })

  it('generates ODI podcast copy with ODI-safe phases and grammar', async () => {
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue({
      ...baseCaseStudy,
      analysis_mode: 'odi_limited_overs',
      match: {
        ...baseCaseStudy.match,
        format: 'ODI',
        teams_label: 'Durham vs Warwickshire',
        result: 'Durham won by 1 runs',
        innings: [
          { team: 'Durham', runs: 338, wickets: 8, overs: 50, run_rate: 6.76 },
          { team: 'Warwickshire', runs: 337, wickets: 8, overs: 50, run_rate: 6.74 },
        ],
      },
      key_players: [
        {
          id: 'bedingham',
          name: 'DG Bedingham',
          team: 'Durham',
          role: 'batter',
          impact: 'high',
          impact_label: 'scored 152 off 108 balls',
          batting: { innings: 1, runs: 152, balls: 108, strike_rate: 140.74, boundaries: { fours: 16, sixes: 3 } },
        },
      ],
      innings_analysis: [
        {
          innings_index: 0,
          team: 'Durham',
          deterministic_summary: 'Innings 1 summary',
          momentum_summary: { title: 'ODI momentum', subtitle: 'ODI subtitle' },
          key_phase: { title: 'Acceleration (26-40)', detail: 'ODI key phase detail' },
          phases: [
            { id: 'powerplay', label: 'Opening Powerplay (1-10)', start_over: 1, end_over: 10, runs: 48, wickets: 1, run_rate: 4.8, net_swing_vs_par: -6, impact: 'negative', impact_label: 'Below par' },
            { id: 'consolidation', label: 'Consolidation (11-25)', start_over: 11, end_over: 25, runs: 85, wickets: 2, run_rate: 5.67, net_swing_vs_par: -3, impact: 'negative', impact_label: 'Slightly below par' },
            { id: 'acceleration', label: 'Acceleration (26-40)', start_over: 26, end_over: 40, runs: 108, wickets: 2, run_rate: 7.2, net_swing_vs_par: 12, impact: 'positive', impact_label: 'Above par' },
            { id: 'death', label: 'Death Overs (41-50)', start_over: 41, end_over: 50, runs: 127, wickets: 3, run_rate: 12.7, net_swing_vs_par: 4, impact: 'positive', impact_label: 'Above par' },
          ],
          key_players: [],
          key_players_scope: 'match',
          dismissal_patterns: { summary: 'Durham dismissals', wicket_cluster_callout: 'A key wicket cluster came between overs 24 and 26, when 2 wickets fell.' },
          story_blocks: {
            opening_story: 'ODI opening',
            middle_overs_story: 'ODI middle',
            death_overs_story: 'ODI death',
            scoring_acceleration: 'ODI acceleration',
            wickets_by_phase: 'ODI wickets',
            strongest_phase: 'ODI strongest',
            weakest_phase: 'ODI weakest',
            innings_outcome_contribution: 'ODI contribution',
          },
          callouts: [],
        },
        {
          innings_index: 1,
          team: 'Warwickshire',
          deterministic_summary: 'Innings 2 summary',
          momentum_summary: { title: 'ODI chase momentum', subtitle: 'ODI chase subtitle' },
          key_phase: { title: 'Consolidation (11-25)', detail: 'ODI chase key phase detail' },
          phases: [
            { id: 'powerplay', label: 'Opening Powerplay (1-10)', start_over: 1, end_over: 10, runs: 58, wickets: 1, run_rate: 5.8, net_swing_vs_par: 1, impact: 'neutral', impact_label: 'On par' },
            { id: 'consolidation', label: 'Consolidation (11-25)', start_over: 11, end_over: 25, runs: 86, wickets: 2, run_rate: 5.73, net_swing_vs_par: -1, impact: 'neutral', impact_label: 'On par' },
            { id: 'acceleration', label: 'Acceleration (26-40)', start_over: 26, end_over: 40, runs: 118, wickets: 2, run_rate: 7.87, net_swing_vs_par: 8, impact: 'positive', impact_label: 'Above par' },
            { id: 'death', label: 'Death Overs (41-50)', start_over: 41, end_over: 50, runs: 75, wickets: 3, run_rate: 7.5, net_swing_vs_par: 3, impact: 'positive', impact_label: 'Above par' },
          ],
          key_players: [],
          key_players_scope: 'match',
          dismissal_patterns: { summary: 'Warwickshire dismissals', wicket_cluster_callout: 'A key wicket cluster came between overs 24 and 26, when 2 wickets fell.' },
          story_blocks: {
            opening_story: 'ODI opening 2',
            middle_overs_story: 'ODI middle 2',
            death_overs_story: 'ODI death 2',
            scoring_acceleration: 'ODI acceleration 2',
            wickets_by_phase: 'ODI wickets 2',
            strongest_phase: 'ODI strongest 2',
            weakest_phase: 'ODI weakest 2',
            innings_outcome_contribution: 'ODI contribution 2',
          },
          callouts: [],
        },
      ],
      odi_intelligence: {
        scoreboard_comparison: {
          team_1: 'Durham',
          team_1_runs: 338,
          team_1_wickets: 8,
          team_1_run_rate: 6.76,
          team_2: 'Warwickshire',
          team_2_runs: 337,
          team_2_wickets: 8,
          team_2_run_rate: 6.74,
          run_differential: 1,
          final_margin: 'Durham won by 1 runs',
        },
        chase_intelligence: {
          target: 339,
          chasing_team: 'Warwickshire',
          initial_required_rate: 6.78,
          required_rate_snapshots: [
            { over: 11, label: 'Consolidation', runs_needed: 281, overs_remaining: 40, required_rate: 7.03 },
            { over: 41, label: 'Death Overs', runs_needed: 89, overs_remaining: 10, required_rate: 8.9 },
          ],
          chase_pressure_note: 'Required rate at start: 7.03 RPO (entering the Consolidation phase, 281 runs from 40 overs). Required rate rose from 7.32 to 8.90 RPO entering the Death Overs.',
          final_10_overs_summary: 'Warwickshire entered the final 10 overs needing 89 runs with 5 wickets in hand.',
          chase_result: 'fell_short',
          runs_margin: 1,
          wickets_in_hand: 2,
          pressure_windows: ['Required rate rose from 7.32 to 8.90 RPO entering the Death Overs.'],
          data_quality: 'full',
        },
        partnerships: [
          {
            innings_number: 1,
            highest_partnership: {
              batter_1: 'DG Bedingham',
              batter_2: 'TSS Mackintosh',
              runs: 116,
              balls: 96,
              run_rate: 7.25,
              start_over: 31,
              end_over: 46,
            },
            best_run_rate_partnership: {
              batter_1: 'DG Bedingham',
              batter_2: 'MJ Killeen',
              runs: 49,
              balls: 18,
              run_rate: 16.33,
              start_over: 47,
              end_over: 49,
            },
            rebuilding_partnership: {
              batter_1: 'DG Bedingham',
              batter_2: 'TSS Mackintosh',
              runs: 116,
              balls: 96,
              run_rate: 7.25,
              start_over: 31,
              end_over: 46,
            },
            summary: 'Highest partnership: 116 runs (DG Bedingham & TSS Mackintosh, overs 31-46).',
            data_quality: 'full',
          },
        ],
        turning_point_candidate: 'Warwickshire stayed within one run of Durham’s 338, but the chase never quite closed. In a one-run ODI, every phase decision carried weight.',
      },
    } as never)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(groundedAiSummary as never)

    const wrapper = mount(MatchCaseStudyView, { global: { stubs: globalStubs } })
    await flushAsync()
    await wrapper.get('[data-testid="podcast-generate-btn"]').trigger('click')
    await flushAsync()

    const pageText = wrapper.text()
    const text = wrapper.get('#cs-podcast-prep').text()
    expect(pageText).toContain('Scoreboard comparison')
    expect(pageText).toContain('Durham won by 1 run')
    expect(pageText).not.toContain('Durham won by 1 runs')
    expect(text).toContain('Durham beat Warwickshire by 1 run.')
    expect(text).toContain('Warwickshire replied with 337/8 from 50 overs, falling 1 run short.')
    expect(text).toContain('Death Overs (41-50)')
    expect(text).not.toContain('entering entering')
    expect(text).toContain('entering the Consolidation phase')
    expect(text).toContain('entering the Death Overs')
    expect((text.match(/Required rate rose from 7\.32 to 8\.90 RPO entering the Death Overs\./g) ?? []).length).toBe(1)
    expect(text).toContain("Durham's strongest stand was 116 between DG Bedingham and TSS Mackintosh from overs 31–46.")
    expect(text).toContain('That partnership powered the late surge.')
    expect(text).toContain('Warwickshire stayed within one run of Durham’s 338, but the chase never quite closed.')
    expect(wrapper.findAll('.cs-odi-list').length).toBeGreaterThan(0)
    expect(text).not.toContain('Durham vs Warwickshire: Durham won by 1 run.')
    expect(text).not.toContain('durham won by 1 run')
    expect(text).not.toContain('Powerplay (1-6)')
    expect(text).not.toContain('Middle Overs (7-15)')
    expect(text).not.toContain('Death Overs (16-20)')
    expect(text).not.toContain('wicket(s)')
    expect(text).toContain("DG Bedingham anchored Durham's innings with 152 off 108 balls.")
    expect(text).toContain('A key wicket cluster came between overs 24 and 26, when 2 wickets fell.')
    expect(text).toContain('In a one-run ODI, which mattered more')
  })

  it('does not show match-not-found when imported case-study payload exists', async () => {
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(baseCaseStudy as never)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(groundedAiSummary as never)

    const wrapper = mount(MatchCaseStudyView, { global: { stubs: globalStubs } })
    await flushAsync()

    expect(wrapper.text()).toContain('Match case study')
    expect(wrapper.text()).not.toContain('Match not found')
    expect(wrapper.text()).not.toContain('No match data available for ID:')
  })

  it('shows match-not-found when payload is truly empty', async () => {
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue({
      analysis_mode: 'unknown',
      match: null,
      momentum_summary: null,
      key_phase: null,
      phases: [],
      key_players: [],
      dismissal_patterns: null,
      innings_analysis: [],
      match_callouts: [],
      match_level_summary: null,
      ai: null,
    } as never)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(groundedAiSummary as never)

    const wrapper = mount(MatchCaseStudyView, { global: { stubs: globalStubs } })
    await flushAsync()

    expect(wrapper.text()).toContain('Match not found')
    expect(wrapper.text()).toContain('No match data available for ID: match-001')
  })

  it('does not keep not-found visible after loading completes with payload', async () => {
    const deferred = createDeferred<typeof baseCaseStudy>()
    vi.mocked(api.getMatchCaseStudy).mockImplementation(() => deferred.promise as never)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(groundedAiSummary as never)

    const wrapper = mount(MatchCaseStudyView, { global: { stubs: globalStubs } })
    await nextTick()

    expect(wrapper.text()).not.toContain('Match not found')

    deferred.resolve(baseCaseStudy)
    await flushAsync()

    expect(wrapper.text()).toContain('Match case study')
    expect(wrapper.text()).not.toContain('Match not found')
  })

  it('renders test/multi-day innings-safe notice and four innings selectors', async () => {
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue({
      ...baseCaseStudy,
      analysis_mode: 'test_multi_day',
      match: {
        ...baseCaseStudy.match,
        format: 'TEST',
        innings: [
          { team: 'AUS', runs: 320, wickets: 10, overs: 96, run_rate: 3.33 },
          { team: 'SA', runs: 280, wickets: 10, overs: 88, run_rate: 3.18 },
          { team: 'AUS', runs: 210, wickets: 10, overs: 70, run_rate: 3.0 },
          { team: 'SA', runs: 251, wickets: 7, overs: 82, run_rate: 3.06 },
        ],
      },
      phases: [
        { id: 'powerplay', label: 'Powerplay', start_over: 1, end_over: 6, runs: 24, wickets: 1, run_rate: 4, net_swing_vs_par: 0, impact: 'neutral', impact_label: 'On par' },
      ],
      innings_analysis: [
        {
          innings_index: 0,
          team: 'AUS',
          deterministic_summary: 'Innings 1 summary',
          momentum_summary: { title: 'Innings-safe momentum summary', subtitle: 'Test-safe summary' },
          key_phase: { title: 'Innings 1 summary', detail: 'Innings-safe detail' },
          phases: [],
          key_players: [],
          key_players_scope: 'match',
          dismissal_patterns: { summary: 'I1 dismissals' },
          story_blocks: {
            opening_story: 'I1 opening',
            middle_overs_story: 'I1 middle',
            death_overs_story: 'I1 late innings',
            scoring_acceleration: 'I1 acceleration',
            wickets_by_phase: 'I1 wickets',
            strongest_phase: 'I1 strongest',
            weakest_phase: 'I1 weakest',
            innings_outcome_contribution: 'I1 contribution',
          },
          callouts: [],
        },
      ],
      multi_day_summary: {
        match_status: 'won',
        notice: 'Test/multi-day match. Analysis uses innings-safe bands; limited-overs phase labels are disabled.',
        innings: [
          { innings_number: 1, team: 'AUS', runs: 320, wickets: 10, overs: 96, deliveries: 576, lead_deficit_after_innings: 320 },
          { innings_number: 2, team: 'SA', runs: 280, wickets: 10, overs: 88, deliveries: 528, lead_deficit_after_innings: -40 },
          { innings_number: 3, team: 'AUS', runs: 210, wickets: 10, overs: 70, deliveries: 420, lead_deficit_after_innings: 170 },
          { innings_number: 4, team: 'SA', runs: 251, wickets: 7, overs: 82, deliveries: 492, lead_deficit_after_innings: 81 },
        ],
        fourth_innings_chase_note: 'Fourth-innings chase context',
        first_innings_lead_note: 'AUS took a 40-run first-innings lead.',
        lead_swing_notes: ['AUS took a 40-run first-innings lead.', 'AUS set SA a fourth-innings target of 251.'],
        fourth_innings_chase: {
          target: 251,
          chasing_team: 'SA',
          runs_scored: 251,
          wickets_lost: 7,
          wickets_in_hand: 3,
          chase_result: 'completed',
          pressure_note: 'Chase completed; 3 wickets in hand.',
        },
        wicket_clusters: [
          { innings_number: 2, overs_start: 45, overs_end: 47, wickets: 3, label: 'wicket cluster' },
        ],
        recovery_windows: [
          { innings_number: 2, overs_start: 48, overs_end: 55, runs_scored: 42, wickets_fell: 0, label: 'recovery period' },
        ],
        match_turning_point: 'A wicket cluster of 3 wickets in overs 45–47 (innings 2) may have been a key turning point.',
      },
    } as never)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(groundedAiSummary as never)

    const wrapper = mount(MatchCaseStudyView, { global: { stubs: globalStubs } })
    await flushAsync()

    // Notice text updated for Phase 10R.3
    expect(wrapper.text()).toContain('Test/multi-day match. Analysis uses innings-safe bands; limited-overs phase labels are disabled.')
    // Four innings selectors still visible
    expect(wrapper.text()).toContain('Innings 4 · SA')
    // No limited-overs labels
    expect(wrapper.text()).not.toContain('Net vs par')
    expect(wrapper.text()).not.toContain('Powerplay (1-6)')
    // New rich intelligence visible
    expect(wrapper.text()).toContain('AUS took a 40-run first-innings lead.')
    expect(wrapper.text()).toContain('AUS set SA a fourth-innings target of 251.')
    expect(wrapper.text()).toContain('SA')
    expect(wrapper.text()).toContain('chasing 251')
  })

  it('shows wicket cluster and recovery period cards for test/multi-day', async () => {
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue({
      ...baseCaseStudy,
      analysis_mode: 'test_multi_day',
      match: {
        ...baseCaseStudy.match,
        format: 'TEST',
        innings: [
          { team: 'AUS', runs: 320, wickets: 10, overs: 96, run_rate: 3.33 },
          { team: 'SA', runs: 280, wickets: 10, overs: 88, run_rate: 3.18 },
        ],
      },
      phases: [],
      innings_analysis: [],
      multi_day_summary: {
        match_status: 'unknown',
        notice: 'Test/multi-day match. Analysis uses innings-safe bands; limited-overs phase labels are disabled.',
        innings: [
          { innings_number: 1, team: 'AUS', runs: 320, wickets: 10, overs: 96, deliveries: 576, lead_deficit_after_innings: 320 },
          { innings_number: 2, team: 'SA', runs: 280, wickets: 10, overs: 88, deliveries: 528, lead_deficit_after_innings: -40 },
        ],
        wicket_clusters: [
          { innings_number: 1, overs_start: 30, overs_end: 32, wickets: 4, label: 'possible collapse window' },
        ],
        recovery_windows: [
          { innings_number: 1, overs_start: 33, overs_end: 40, runs_scored: 55, wickets_fell: 1, label: 'recovery period' },
        ],
        match_turning_point: 'A possible collapse window of 4 wickets in overs 30–32 (innings 1) may have been a key turning point.',
      },
    } as never)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(groundedAiSummary as never)

    const wrapper = mount(MatchCaseStudyView, { global: { stubs: globalStubs } })
    await flushAsync()

    expect(wrapper.text()).toContain('Wicket clusters')
    expect(wrapper.text()).toContain('possible collapse window')
    expect(wrapper.text()).toContain('Recovery periods')
    expect(wrapper.text()).toContain('Recovery (innings 1')
    expect(wrapper.text()).toContain('Match turning point candidate')
  })

  it('generates Test-specific podcast cards for test_multi_day mode', async () => {
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue({
      ...baseCaseStudy,
      analysis_mode: 'test_multi_day',
      match: {
        ...baseCaseStudy.match,
        format: 'TEST',
        innings: [
          { team: 'AUS', runs: 320, wickets: 10, overs: 96, run_rate: 3.33 },
          { team: 'SA', runs: 280, wickets: 10, overs: 88, run_rate: 3.18 },
          { team: 'AUS', runs: 200, wickets: 10, overs: 65, run_rate: 3.07 },
          { team: 'SA', runs: 155, wickets: 5, overs: 45, run_rate: 3.44 },
        ],
      },
      phases: [],
      innings_analysis: [
        {
          innings_index: 0,
          team: 'AUS',
          deterministic_summary: 'Innings 1 summary',
          momentum_summary: { title: 'Innings-safe', subtitle: 'Test-safe' },
          key_phase: { title: 'Innings 1', detail: 'Test detail' },
          phases: [],
          key_players: [],
          key_players_scope: 'match',
          dismissal_patterns: { summary: 'I1 dismissals' },
          story_blocks: {
            opening_story: 'I1 opening',
            middle_overs_story: 'I1 middle',
            death_overs_story: 'I1 death',
            scoring_acceleration: 'I1 acc',
            wickets_by_phase: 'I1 wkts',
            strongest_phase: 'I1 strongest',
            weakest_phase: 'I1 weakest',
            innings_outcome_contribution: 'I1 contribution',
          },
          callouts: [],
        },
      ],
      multi_day_summary: {
        match_status: 'won',
        notice: 'Test/multi-day match.',
        innings: [],
        first_innings_lead_note: 'AUS took a 40-run first-innings lead.',
        lead_swing_notes: ['AUS took a 40-run first-innings lead.'],
        fourth_innings_chase: {
          target: 151,
          chasing_team: 'SA',
          runs_scored: 155,
          wickets_lost: 5,
          wickets_in_hand: 5,
          chase_result: 'completed',
          pressure_note: 'Chase completed with 5 wickets in hand.',
        },
        wicket_clusters: [],
        recovery_windows: [],
        match_turning_point: null,
      },
    } as never)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(groundedAiSummary as never)

    const wrapper = mount(MatchCaseStudyView, { global: { stubs: globalStubs } })
    await flushAsync()

    await wrapper.get('[data-testid="podcast-generate-btn"]').trigger('click')
    await flushAsync()

    const text = wrapper.text()
    // Test-specific podcast card titles
    expect(text).toContain('First innings')
    expect(text).toContain('First-innings lead story')
    expect(text).toContain('Third innings')
    expect(text).toContain('Fourth-innings chase story')
    expect(text).toContain('Collapse / recovery talking point')
    // Must NOT contain limited-overs cards in test mode
    expect(text).not.toContain('Powerplay')
    expect(text).not.toContain('vs par')
  })

  it('generates Test podcast with presenter-ready copy and no grammar issues', async () => {
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue({
      ...baseCaseStudy,
      analysis_mode: 'test_multi_day',
      match: {
        ...baseCaseStudy.match,
        format: 'TEST',
        venue: 'Adelaide Oval',
        result: 'Australia won by 7 wickets',
        teams_label: 'Australia vs South Africa',
        innings: [
          { team: 'SA', runs: 259, wickets: 10, overs: 80, run_rate: 3.24 },
          { team: 'AUS', runs: 383, wickets: 10, overs: 121, run_rate: 3.16 },
          { team: 'SA', runs: 250, wickets: 0, overs: 73, run_rate: 3.42 },
          { team: 'AUS', runs: 127, wickets: 0, overs: 30, run_rate: 4.23 },
        ],
      },
      key_players: [
        {
          id: 'starc',
          name: 'MA Starc',
          team: 'Australia',
          role: 'all-rounder',
          impact: 'high',
          impact_label: 'scored 53 off 91 balls',
          batting: { innings: 1, runs: 53, balls: 91, strike_rate: 58.2, boundaries: { fours: 4, sixes: 0 } },
          bowling: { overs: 22, maidens: 3, runs: 71, wickets: 4, economy: 3.23 },
        },
      ],
      phases: [],
      innings_analysis: [],
      multi_day_summary: {
        match_status: 'won',
        notice: 'Test/multi-day match.',
        innings: [
          { innings_number: 1, team: 'SA', runs: 259, wickets: 10, overs: 80 },
          { innings_number: 2, team: 'AUS', runs: 383, wickets: 10, overs: 121 },
          { innings_number: 3, team: 'SA', runs: 250, wickets: 0, overs: 73 },
          { innings_number: 4, team: 'AUS', runs: 127, wickets: 0, overs: 30 },
        ],
        first_innings_lead_note: 'Australia took a 124-run first-innings lead.',
        lead_swing_notes: ['Australia took a 124-run first-innings lead.'],
        fourth_innings_chase: {
          target: 127,
          chasing_team: 'Australia',
          runs_scored: 127,
          wickets_lost: 0,
          wickets_in_hand: 10,
          chase_result: 'completed',
          pressure_note: 'Chase completed; 10 wickets in hand.',
        },
        wicket_clusters: [
          { innings_number: 2, overs_start: 13, overs_end: 15, wickets: 2, label: 'wicket cluster' },
        ],
        recovery_windows: [],
        match_turning_point: null,
      },
    } as never)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(groundedAiSummary as never)

    const wrapper = mount(MatchCaseStudyView, { global: { stubs: globalStubs } })
    await flushAsync()

    await wrapper.get('[data-testid="podcast-generate-btn"]').trigger('click')
    await flushAsync()

    const text = wrapper.text()

    // No "wicket(s)" pluralization artifact anywhere
    expect(text).not.toContain('wicket(s)')

    // Opening hook uses chase context + venue
    expect(text).toContain('Australia completed a controlled fourth-innings chase to beat South Africa by 7 wickets at Adelaide Oval.')

    // First innings story describes first batting team
    expect(text).toContain('SA posted 259 all out')

    // First-innings lead card combines reply + lead note
    expect(text).toContain('AUS replied with 383 all out')
    expect(text).toContain('Australia took a 124-run first-innings lead.')

    // Third innings story sets up the target
    expect(text).toContain('SA made 250, based on recorded innings data')
    expect(text).not.toContain('SA made 250/0')
    expect(text).toContain('target of 127')

    // Fourth-innings chase: concise, no repetition from pressure_note
    expect(text).toContain('Australia completed the chase at 127/0')
    expect(text).toContain('10 wickets in hand')
    // Podcast card must NOT reproduce the pressure_note verbatim
    const chaseCardText = wrapper.get('[data-testid="podcast-card-test-fourth-innings-chase"]').text()
    expect(chaseCardText).not.toContain('Chase completed; 10 wickets in hand')

    // Player spotlight uses batting and bowling facts — no "delivered scored" artifact
    const playerCardText = wrapper.get('[data-testid="podcast-card-test-player-impact"]').text()
    expect(playerCardText).not.toContain('delivered scored')
    expect(text).toContain('MA Starc')
    expect(text).toContain('all-round contribution')
    expect(text).toContain('53 runs off 91 balls')
    expect(text).toContain('4 wickets')

    // Closing question is discussion-ready (not generic placeholder)
    expect(text).not.toContain('What deterministic trend')
    expect(text).toContain("Australia's chase")

    // Turning point combines lead + chase context when both are available
    expect(text).toContain('Australia’s 124-run first-innings lead gave them control before the fourth-innings chase confirmed the result.')
  })

  it('exports approved podcast rundown only by default', async () => {
    vi.mocked(api.getMatchCaseStudy).mockResolvedValue(baseCaseStudy as never)
    vi.mocked(api.getMatchAiSummary).mockResolvedValue(groundedAiSummary as never)

    const wrapper = mount(MatchCaseStudyView, { global: { stubs: globalStubs } })
    await flushAsync()

    await wrapper.get('[data-testid="podcast-generate-btn"]').trigger('click')
    await flushAsync()

    await wrapper.get('[data-testid="podcast-approve-opening-hook"]').trigger('click')
    await flushAsync()

    await wrapper.get('[data-testid="podcast-copy-markdown"]').trigger('click')
    expect(clipboardWriteMock).toHaveBeenCalled()
    const copiedDefault = clipboardWriteMock.mock.calls.at(-1)?.[0] as string
    expect(copiedDefault).toContain('Opening hook')
    expect(copiedDefault).not.toContain('Match context')

    await wrapper.get('.cs-podcast-export-toggle input').setValue(true)
    await wrapper.get('[data-testid="podcast-copy-markdown"]').trigger('click')
    const copiedWithDrafts = clipboardWriteMock.mock.calls.at(-1)?.[0] as string
    expect(copiedWithDrafts).toContain('Match context')
  })
})

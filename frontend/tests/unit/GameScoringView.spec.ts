import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { computed, reactive, ref, nextTick } from 'vue'

import { useGameStore } from '@/stores/gameStore'
import GameScoringView from '@/views/GameScoringView.vue'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { gameId: 'test-game' }, query: {} }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}))

const createAuthStoreMock = () => ({
  canScore: ref(true),
  isFreeUser: ref(false),
  isPlayerPro: ref(false),
  role: ref('coach'),
})

const createGameStoreMock = () => {
  const uiState = {
    loading: false,
    error: null,
    selectedStrikerId: 'striker-1',
    selectedNonStrikerId: 'non-striker-1',
    selectedBowlerId: 'bowler-1',
    scoringDisabled: false,
    activeScorecardTab: 'batting',
  }
  const state = {
    needs_new_batter: false,
    needs_new_over: false,
    needs_new_innings: false,
    current_bowler_id: 'bowler-1',
    last_ball_bowler_id: null,
    current_over_balls: 0,
    mid_over_change_used: false,
    batting_order_ids: [],
  }
  const score = reactive({ runs: 0, overs: '0.0', wickets: 0 })
  const battingPlayers = [
    { id: 'striker-1', name: 'Striker One' },
    { id: 'non-striker-1', name: 'Non Striker' },
  ]
  const bowlingPlayers = [{ id: 'bowler-1', name: 'Bowler One' }]

  const battingRosterXI = ref(battingPlayers)
  const bowlingRosterXI = ref(bowlingPlayers)

  const battingRowsXI = ref(
    battingPlayers.map((player) => ({
      id: player.id,
      name: player.name,
      runs: 0,
      balls: 0,
      fours: 0,
      sixes: 0,
      sr: 0,
      isOut: false,
    }))
  )
  const bowlingRowsXI = ref(
    bowlingPlayers.map((player) => ({
      id: player.id,
      name: player.name,
      runs: 0,
      balls: 0,
      maidens: 0,
      wickets: 0,
      wkts: 0,
      econ: 0,
    }))
  )

  return {
    applyDls: vi.fn(),
    changeBowlerMidOver: vi.fn(),
    connectionStatus: 'connected',
    currentGame: {
      id: 'test-game',
      status: 'in_progress',
      current_inning: 1,
      team_a: { name: 'Team A', players: battingPlayers },
      team_b: { name: 'Team B', players: bowlingPlayers },
      deliveries: [],
      batting_order_ids: [],
      dls_enabled: false,
      overs_limit: 20,
    },
    dlsApplied: false,
    dlsPanel: {},
    dlsParNow: vi.fn(),
    dlsPreview: ref(null),
    fetchDlsPreview: vi.fn(),
    flushQueue: vi.fn(),
    initLive: vi.fn(),
    loadGame: vi.fn(),
    offlineQueue: [],
    reduceOvers: vi.fn(),
    reduceOversForInnings: vi.fn(),
    replaceBatter: vi.fn(),
    scoreExtra: vi.fn(),
    scoreRuns: vi.fn(),
    scoreWicket: vi.fn(),
    setSelectedBowler: (id: string | null) => {
      uiState.selectedBowlerId = id
    },
    setSelectedNonStriker: (id: string | null) => {
      uiState.selectedNonStrikerId = id
    },
    setSelectedStriker: (id: string | null) => {
      uiState.selectedStrikerId = id
    },
    startInterruption: vi.fn(),
    startNewOver: vi.fn(),
    state,
    stopInterruption: vi.fn(),
    stopLive: vi.fn(),
    uiState,
    canScore: true,
    canScoreDelivery: true,
    liveSnapshot: ref(null),
    needsNewBatter: ref(false),
    needsNewOver: ref(false),
    extrasBreakdown: ref({
      wides: 0,
      no_balls: 0,
      byes: 0,
      leg_byes: 0,
      penalty: 0,
      total: 0,
    }),
    dlsKind: ref<'t20'>('t20'),
    runsRequired: ref(null),
    targetSafe: ref(null),
    requiredRunRate: ref(null),
    ballsBowledTotal: ref(0),
    score,
    battingRosterXI,
    bowlingRosterXI,
    battingRowsXI,
    bowlingRowsXI,
    fieldingSubs: ref([]),
    fielderRosterAll: ref([]),
  }
}

let gameStoreMock = createGameStoreMock()
let authStoreMock = createAuthStoreMock()

vi.mock('@/stores/gameStore', () => ({
  useGameStore: () => gameStoreMock,
}))

vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => authStoreMock,
}))

const ScoreboardStub = {
  template: `
    <div data-testid="mock-scoreboard">
      <span data-testid="scoreboard-runs">{{ runs }}</span>
      <span data-testid="scoreboard-overs">{{ overs }}</span>
    </div>
  `,
  setup() {
    const store = useGameStore()
    const runs = computed(() => store.score?.runs ?? 0)
    const overs = computed(() => store.score?.overs ?? '0.0')
    return { runs, overs }
  },
}

describe('GameScoringView', () => {
  let pinia: ReturnType<typeof createPinia>

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    gameStoreMock = createGameStoreMock()
    authStoreMock = createAuthStoreMock()
  })

  const mountView = async (attachTo?: HTMLElement) => {
    const wrapper = mount(GameScoringView, {
      attachTo,
      global: {
        plugins: [pinia],
        stubs: {
          ScoreboardWidget: ScoreboardStub,
          PresenceBar: true,
          DeliveryTable: true,
          BattingCard: true,
          BowlingCard: true,
          EventLogTab: true,
          InningsGradeWidget: true,
          PhaseTimelineWidget: true,
          PressureMapWidget: true,
          ShotMapCanvas: true,
          WinProbabilityChart: true,
          WinProbabilityWidget: true,
          RouterLink: true,
        },
      },
    })

    await nextTick()
    return wrapper
  }

  it('disables scoring when the store gate is closed', async () => {
    gameStoreMock.canScore = false
    gameStoreMock.canScoreDelivery = false
    authStoreMock.canScore.value = true

    const wrapper = await mountView()
    const controls = wrapper.get('[data-testid="scorer-controls"]')
    const submitButton = wrapper.get('[data-testid="submit-delivery"]')
    expect(controls.classes()).toContain('scorer-controls--disabled')
    expect(controls.attributes('aria-disabled')).toBe('true')
    expect(wrapper.get('[data-testid="delivery-run-0"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-testid="delivery-extra-wd"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-testid="delivery-wicket"]').attributes('disabled')).toBeDefined()
    expect(submitButton).toBeDefined()
    expect(submitButton?.attributes('disabled')).toBeDefined()
  })

  it('enables scoring when the store allows', async () => {
    gameStoreMock.canScore = true
    gameStoreMock.canScoreDelivery = true
    authStoreMock.canScore.value = true

    const wrapper = await mountView()
    const submitButton = wrapper.get('[data-testid="submit-delivery"]')
    expect(submitButton).toBeDefined()
    expect(submitButton?.attributes('disabled')).toBeUndefined()
  })

  it('renders the primary run, extras, and wicket controls with scorer classes', async () => {
    const wrapper = await mountView()

    for (const runs of [0, 1, 2, 3, 4, 6]) {
      const control = wrapper.get(`[data-testid="delivery-run-${runs}"]`)
      expect(control.text()).toBe(String(runs))
      expect(control.classes()).toContain('btn-score')
      expect(control.attributes('type')).toBe('button')
      expect(control.attributes('disabled')).toBeUndefined()
    }

    for (const extra of ['legal', 'wd', 'nb', 'b', 'lb']) {
      const control = wrapper.get(`[data-testid="delivery-extra-${extra}"]`)
      expect(control.classes()).toContain('btn-input')
      expect(control.attributes('type')).toBe('button')
    }

    const wicket = wrapper.get('[data-testid="delivery-wicket"]')
    expect(wicket.attributes('type')).toBe('checkbox')
    expect(wicket.element.closest('label')?.textContent).toContain('WICKET')
  })

  it('keeps enabled scoring buttons keyboard focusable', async () => {
    const host = document.createElement('div')
    document.body.appendChild(host)
    const wrapper = await mountView(host)
    const runControl = wrapper.get('[data-testid="delivery-run-1"]')

    ;(runControl.element as HTMLButtonElement).focus()

    expect(document.activeElement).toBe(runControl.element)
    wrapper.unmount()
    host.remove()
  })

  it('submits a run and shows the updated score when scoring is allowed', async () => {
    const runAmount = 4
    gameStoreMock.canScore = true
    gameStoreMock.canScoreDelivery = true
    gameStoreMock.scoreRuns = vi.fn(async () => {
      gameStoreMock.score.runs = runAmount
      gameStoreMock.score.overs = '0.1'
    })

    const wrapper = await mountView()
    await wrapper.get('[data-testid="delivery-run-4"]').trigger('click')
    await wrapper.get('[data-testid="submit-delivery"]').trigger('click')
    await flushPromises()

    expect(gameStoreMock.scoreRuns).toHaveBeenCalledTimes(1)
    expect(gameStoreMock.scoreRuns).toHaveBeenCalledWith('test-game', runAmount, null)
    expect(wrapper.get('[data-testid="scoreboard-runs"]').text()).toBe(String(runAmount))
  })

  it('does not score when delivery scoring is disabled', async () => {
    gameStoreMock.canScore = false
    gameStoreMock.canScoreDelivery = false

    const wrapper = await mountView()
    await wrapper.get('[data-testid="delivery-run-4"]').trigger('click')
    await wrapper.get('[data-testid="submit-delivery"]').trigger('click')
    await flushPromises()

    expect(gameStoreMock.scoreRuns).not.toHaveBeenCalled()
  })

  it('submits an extra through the existing score handler', async () => {
    const wrapper = await mountView()

    await wrapper.get('[data-testid="delivery-extra-wd"]').trigger('click')
    await wrapper.get('[data-testid="submit-delivery"]').trigger('click')
    await flushPromises()

    expect(gameStoreMock.scoreExtra).toHaveBeenCalledWith('test-game', 'wd', 1)
  })

  it('presents the pre-first-innings gate as a start action, not an innings break', async () => {
    gameStoreMock.currentGame.status = 'innings_break'
    gameStoreMock.currentGame.current_inning = 0
    gameStoreMock.canScore = false
    gameStoreMock.canScoreDelivery = false

    const wrapper = await mountView()
    const gate = wrapper.get('[data-testid="gate-innings"]')

    expect(gate.attributes('role')).toBe('region')
    expect(gate.text()).toContain('Match action')
    expect(gate.text()).toContain('Ready to Start')
    expect(gate.text()).toContain('Start First Innings')
    expect(gate.text()).not.toContain('Innings Break')
    expect(wrapper.find('[data-testid="delivery-run-0"]').exists()).toBe(true)
  })

  it('retains the legitimate innings-break presentation after an innings', async () => {
    gameStoreMock.currentGame.status = 'innings_break'
    gameStoreMock.currentGame.current_inning = 1
    gameStoreMock.canScore = false
    gameStoreMock.canScoreDelivery = false

    const wrapper = await mountView()
    const gate = wrapper.get('[data-testid="gate-innings"]')

    expect(gate.text()).toContain('Innings Break')
    expect(gate.text()).toContain('previous innings is complete')
    expect(gate.text()).toContain('Start Next Innings')
    expect(gate.text()).not.toContain('Ready to Start')
  })
})

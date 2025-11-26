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

  const mountView = async () => {
    const wrapper = mount(GameScoringView, {
      global: {
        plugins: [pinia],
        stubs: {
          ScoreboardWidget: ScoreboardStub,
          PresenceBar: true,
          DeliveryTable: true,
          BattingCard: true,
          BowlingCard: true,
          ShotMapCanvas: true,
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
    const submitButton = wrapper.get('[data-testid="submit-delivery"]')
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
    expect(wrapper.get('[data-testid="scoreboard-overs"]').text()).toBe('0.1')
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
})

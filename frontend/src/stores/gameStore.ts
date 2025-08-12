/**
 * Game Store for Cricksy Scorer
 * - Central game state + UI state
 * - REST actions (create/load/score/next-innings)
 * - Socket live snapshots
 * - Offline queue (enqueue while disconnected, flush on reconnect)
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/* Types — single source of truth */
import type {
  GameState,
  CreateGameRequest,
  ScoreDeliveryRequest,
  Player,
  Team,
  BattingScorecardEntry,
  BowlingScorecardEntry,
  Snapshot,
  StateUpdatePayload,
  UIState,
} from '@/types'

/* API helpers */
import { apiService, getErrorMessage } from '@/utils/api'

/* Socket helpers (generic typed on/off) */
import { on as onSocket, off as offSocket, connectSocket, disconnectSocket } from '@/utils/socket'

/* ===== Local helpers ===== */
type PendingStatus = 'queued' | 'flushing' | 'failed'
type PendingDelivery = {
  id: string
  gameId: string
  payload: ScoreDeliveryRequest
  createdAt: number
  tries: number
  status: PendingStatus
}

function makeId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

export const useGameStore = defineStore('game', () => {
  /* ========================================================================
   * Reactive State
   * ====================================================================== */
  const currentGame = ref<GameState | null>(null)

  const uiState = ref<UIState>({
    loading: false,
    error: null,
    selectedStrikerId: null,
    selectedNonStrikerId: null,
    selectedBowlerId: null,
    scoringDisabled: false,
    activeScorecardTab: 'batting',
  })

  const operationLoading = ref({
    createGame: false,
    loadGame: false,
    scoreDelivery: false,
    startInnings: false,
  })

  /* Live sockets */
  const isLive = ref(false)
  const liveGameId = ref<string | null>(null)
  const connectionStatus = ref<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected')
  const lastLiveAt = ref<number | null>(null)
  const liveSnapshot = ref<Snapshot | null>(null)

  /* Offline queue */
  const offlineEnabled = ref(true)
  const offlineQueue = ref<PendingDelivery[]>([])
  const isFlushing = ref(false)
  const QKEY = 'cricksy.offline.queue.v1'

  function loadQueue() {
    try {
      const raw = localStorage.getItem(QKEY)
      offlineQueue.value = raw ? JSON.parse(raw) : []
    } catch {
      offlineQueue.value = []
    }
  }
  function saveQueue() {
    try {
      localStorage.setItem(QKEY, JSON.stringify(offlineQueue.value))
    } catch {}
  }
  loadQueue()

  /* ========================================================================
   * Simple proxies expected by views
   * ====================================================================== */
  const isLoading = computed(() => uiState.value.loading)
  const error = computed(() => uiState.value.error)

  /* ========================================================================
   * Status flags
   * ====================================================================== */
  const isGameActive = computed(() => currentGame.value?.status === 'in_progress')
  const isInningsBreak = computed(() => currentGame.value?.status === 'innings_break')
  const isGameCompleted = computed(() => currentGame.value?.status === 'completed')
  const isFirstInnings = computed(() => currentGame.value?.current_inning === 1)
  const isSecondInnings = computed(() => currentGame.value?.current_inning === 2)

  /* ========================================================================
   * Teams & players
   * ====================================================================== */
  const battingTeam = computed<Team | null>(() => {
    if (!currentGame.value) return null
    return currentGame.value.batting_team_name === currentGame.value.team_a.name
      ? currentGame.value.team_a
      : currentGame.value.team_b
  })

  const bowlingTeam = computed<Team | null>(() => {
    if (!currentGame.value) return null
    return currentGame.value.bowling_team_name === currentGame.value.team_a.name
      ? currentGame.value.team_a
      : currentGame.value.team_b
  })

  const availableBatsmen = computed<Player[]>(() => {
    const team = battingTeam.value
    if (!team || !currentGame.value) return []
    const card: Record<string, BattingScorecardEntry> = currentGame.value.batting_scorecard || {}
    return team.players.filter((p) => !card[p.id]?.is_out)
  })

  const availableBowlers = computed<Player[]>(() => {
    const team = bowlingTeam.value
    return team ? team.players : []
  })

  /* ========================================================================
   * Score helpers
   * ====================================================================== */
  const currentOver = computed(() => {
    if (!currentGame.value) return '0.0'
    const o = currentGame.value.overs_completed ?? 0
    const b = currentGame.value.balls_this_over ?? 0
    return `${o}.${b}`
  })

  const scoreDisplay = computed(() => {
    if (!currentGame.value) return '0/0 (0.0)'
    const r = currentGame.value.total_runs ?? 0
    const w = currentGame.value.total_wickets ?? 0
    return `${r}/${w} (${currentOver.value})`
  })

  const targetDisplay = computed(() => {
    if (!currentGame.value || currentGame.value.target == null) return ''
    return `Target: ${currentGame.value.target}`
  })

  const runsRequired = computed(() => {
    if (!currentGame.value || currentGame.value.target == null) return null
    const req = currentGame.value.target - (currentGame.value.total_runs ?? 0)
    return req > 0 ? req : 0
  })

  /* ========================================================================
   * UI helpers
   * ====================================================================== */
  function setLoading(v: boolean) {
    uiState.value.loading = v
  }
  function setError(msg: string | null) {
    uiState.value.error = msg
  }
  function setOperationLoading(key: keyof typeof operationLoading.value, v: boolean) {
    operationLoading.value[key] = v
  }

  /* ========================================================================
   * LIVE socket handlers
   * ====================================================================== */
  function handleStateUpdate(payload: StateUpdatePayload) {
    if (!liveGameId.value || payload.id !== liveGameId.value) return
    liveSnapshot.value = payload.snapshot
    lastLiveAt.value = Date.now()
    // Optionally: map snapshot into currentGame if you want
  }

  async function initLive(id: string) {
    liveGameId.value = id
    connectionStatus.value = 'connecting'
    isLive.value = true

    try {
      connectSocket()

      onSocket('hello', () => {
        connectionStatus.value = 'connected'
        if (liveGameId.value) flushQueue(liveGameId.value).catch(() => {})
      })

      onSocket<StateUpdatePayload>('state:update', handleStateUpdate)
    } catch (e) {
      connectionStatus.value = 'error'
      console.error('Socket error:', e)
    }
  }

  function stopLive() {
    offSocket<StateUpdatePayload>('state:update', handleStateUpdate)
    disconnectSocket()
    connectionStatus.value = 'disconnected'
    isLive.value = false
    liveGameId.value = null
  }

  /* Also flush when the browser regains network */
  let listenersBound = false
  function bindNetworkListeners() {
    if (listenersBound) return
    listenersBound = true
    window.addEventListener('online', () => {
      if (liveGameId.value) flushQueue(liveGameId.value).catch(() => {})
    })
  }
  bindNetworkListeners()

  /* ========================================================================
   * Offline queue
   * ====================================================================== */
  function enqueueDelivery(gameId: string, payload: ScoreDeliveryRequest) {
    const item: PendingDelivery = {
      id: makeId(),
      gameId,
      payload,
      createdAt: Date.now(),
      tries: 0,
      status: 'queued',
    }
    offlineQueue.value.push(item)
    saveQueue()
    return item.id
  }

  async function flushQueue(gameId: string) {
    if (isFlushing.value) return
    if (connectionStatus.value !== 'connected') return

    isFlushing.value = true
    try {
      for (const item of [...offlineQueue.value]) {
        if (item.gameId !== gameId) continue
        if (item.status === 'flushing') continue

        item.status = 'flushing'
        item.tries += 1
        saveQueue()

        try {
          await apiService.scoreDelivery(item.gameId, item.payload)
          offlineQueue.value = offlineQueue.value.filter((q) => q.id !== item.id)
          saveQueue()
        } catch (e) {
          item.status = 'failed'
          saveQueue()
          break // preserve order on failure
        }
      }
    } finally {
      isFlushing.value = false
    }
  }

  /* ========================================================================
   * Actions: Game lifecycle
   * ====================================================================== */
  async function createNewGame(payload: CreateGameRequest) {
    setOperationLoading('createGame', true)
    setError(null)
    try {
      setLoading(true)
      const game = await apiService.createGame(payload)
      currentGame.value = game
      return game
    } catch (e) {
      setError(getErrorMessage(e))
      throw e
    } finally {
      setLoading(false)
      setOperationLoading('createGame', false)
    }
  }

  async function loadGame(gameId: string) {
    setOperationLoading('loadGame', true)
    setError(null)
    try {
      setLoading(true)
      const game = await apiService.getGame(gameId)
      currentGame.value = game
      return game
    } catch (e) {
      setError(getErrorMessage(e))
      throw e
    } finally {
      setLoading(false)
      setOperationLoading('loadGame', false)
    }
  }

  async function scoreDelivery(gameId: string, delivery: ScoreDeliveryRequest) {
    setOperationLoading('scoreDelivery', true)
    setError(null)
    try {
      setLoading(true)
      const updated = await apiService.scoreDelivery(gameId, delivery)
      currentGame.value = updated
      return updated
    } catch (e) {
      setError(getErrorMessage(e))
      throw e
    } finally {
      setLoading(false)
      setOperationLoading('scoreDelivery', false)
    }
  }

  async function startNextInnings(gameId: string) {
    setOperationLoading('startInnings', true)
    setError(null)
    try {
      setLoading(true)
      const updated = await apiService.startNextInnings(gameId)
      currentGame.value = updated
      return updated
    } catch (e) {
      setError(getErrorMessage(e))
      throw e
    } finally {
      setLoading(false)
      setOperationLoading('startInnings', false)
    }
  }

  /* Smart submit: queue when offline, post when online */
  async function submitDelivery(gameId: string, payload: ScoreDeliveryRequest) {
    const onlineAndLive = connectionStatus.value === 'connected'
    if (!onlineAndLive && offlineEnabled.value) {
      enqueueDelivery(gameId, payload)
      return { queued: true }
    }
    return scoreDelivery(gameId, payload)
  }

  /* ========================================================================
   * Selection & convenience
   * ====================================================================== */
  const selectedStriker = computed<Player | null>(() => {
    const id = uiState.value.selectedStrikerId
    const team = battingTeam.value
    return id && team ? team.players.find((p) => p.id === id) || null : null
  })
  const selectedNonStriker = computed<Player | null>(() => {
    const id = uiState.value.selectedNonStrikerId
    const team = battingTeam.value
    return id && team ? team.players.find((p) => p.id === id) || null : null
  })
  const selectedBowler = computed<Player | null>(() => {
    const id = uiState.value.selectedBowlerId
    const team = bowlingTeam.value
    return id && team ? team.players.find((p) => p.id === id) || null : null
  })

  const canScore = computed(
    () =>
      Boolean(
        currentGame.value &&
          currentGame.value.status === 'in_progress' &&
          uiState.value.selectedStrikerId &&
          uiState.value.selectedNonStrikerId &&
          uiState.value.selectedBowlerId &&
          uiState.value.selectedStrikerId !== uiState.value.selectedNonStrikerId &&
          !uiState.value.loading &&
          !uiState.value.scoringDisabled,
      ),
  )

  function setSelectedStriker(playerId: string | null) {
    uiState.value.selectedStrikerId = playerId
  }
  function setSelectedNonStriker(playerId: string | null) {
    uiState.value.selectedNonStrikerId = playerId
  }
  function setSelectedBowler(playerId: string | null) {
    uiState.value.selectedBowlerId = playerId
  }
  function swapBatsmen() {
    const a = uiState.value.selectedStrikerId
    const b = uiState.value.selectedNonStrikerId
    uiState.value.selectedStrikerId = b
    uiState.value.selectedNonStrikerId = a
  }
  function setActiveScorecardTab(tab: 'batting' | 'bowling') {
    uiState.value.activeScorecardTab = tab
  }
  function setScoringDisabled(disabled: boolean) {
    uiState.value.scoringDisabled = disabled
  }

  /* Convenience actions that the UI can call */
  async function scoreRuns(gameId: string, runs: number) {
    if (
      !uiState.value.selectedStrikerId ||
      !uiState.value.selectedNonStrikerId ||
      !uiState.value.selectedBowlerId
    ) {
      throw new Error('Cannot score runs - missing selected players')
    }
    const payload: ScoreDeliveryRequest = {
      striker_id: uiState.value.selectedStrikerId,
      non_striker_id: uiState.value.selectedNonStrikerId,
      bowler_id: uiState.value.selectedBowlerId,
      runs_scored: runs,
      is_wicket: false,
    } as unknown as ScoreDeliveryRequest
    return submitDelivery(gameId, payload)
  }

  async function scoreExtra(gameId: string, code: 'wd' | 'nb' | 'b' | 'lb', runs = 1) {
    if (
      !uiState.value.selectedStrikerId ||
      !uiState.value.selectedNonStrikerId ||
      !uiState.value.selectedBowlerId
    ) {
      throw new Error('Cannot score extra - missing selected players')
    }
    const payload: ScoreDeliveryRequest = {
      striker_id: uiState.value.selectedStrikerId,
      non_striker_id: uiState.value.selectedNonStrikerId,
      bowler_id: uiState.value.selectedBowlerId,
      runs_scored: runs,
      extra: code,
      is_wicket: false,
    } as unknown as ScoreDeliveryRequest
    return submitDelivery(gameId, payload)
  }

  async function scoreWicket(
    gameId: string,
    dismissal_type: string,
    dismissed_player_id?: string | null,
    commentary?: string,
  ) {
    if (
      !uiState.value.selectedStrikerId ||
      !uiState.value.selectedNonStrikerId ||
      !uiState.value.selectedBowlerId
    ) {
      throw new Error('Cannot score wicket - missing selected players')
    }
    const payload: ScoreDeliveryRequest = {
      striker_id: uiState.value.selectedStrikerId,
      non_striker_id: uiState.value.selectedNonStrikerId,
      bowler_id: uiState.value.selectedBowlerId,
      runs_scored: 0,
      is_wicket: true,
      dismissal_type,
      dismissed_player_id: dismissed_player_id ?? uiState.value.selectedStrikerId,
      commentary: commentary ?? '',
    } as unknown as ScoreDeliveryRequest
    return submitDelivery(gameId, payload)
  }

  /* Utility */
  function clearError() {
    setError(null)
  }
  function clearGame() {
    currentGame.value = null
    uiState.value.selectedStrikerId = null
    uiState.value.selectedNonStrikerId = null
    uiState.value.selectedBowlerId = null
    uiState.value.scoringDisabled = false
    liveSnapshot.value = null
    isLive.value = false
    liveGameId.value = null
  }

  /* ========================================================================
   * Expose API
   * ====================================================================== */
  return {
    // State
    currentGame,
    uiState,
    operationLoading,

    // Proxies
    isLoading,
    error,

    // Status
    isGameActive,
    isInningsBreak,
    isGameCompleted,
    isFirstInnings,
    isSecondInnings,

    // Teams/players
    battingTeam,
    bowlingTeam,
    availableBatsmen,
    availableBowlers,
    selectedStriker,
    selectedNonStriker,
    selectedBowler,

    // Score helpers
    currentOver,
    scoreDisplay,
    targetDisplay,
    runsRequired,

    // Live
    isLive,
    liveGameId,
    connectionStatus,
    lastLiveAt,
    liveSnapshot,
    initLive,
    stopLive,

    // Offline
    offlineEnabled,
    offlineQueue,
    isFlushing,
    enqueueDelivery,
    flushQueue,
    submitDelivery,

    // Actions
    createNewGame,
    loadGame,
    scoreDelivery,
    startNextInnings,

    // Selections
    setSelectedStriker,
    setSelectedNonStriker,
    setSelectedBowler,
    swapBatsmen,
    setActiveScorecardTab,
    setScoringDisabled,

    // Convenience
    scoreRuns,
    scoreExtra,
    scoreWicket,

    // Utils
    clearError,
    clearGame,
  }
})

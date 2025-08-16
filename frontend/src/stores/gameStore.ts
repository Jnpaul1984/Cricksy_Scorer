/**
 * Game Store for Cricksy Scorer
 * - Central game state + UI state
 * - REST actions (create/load/score/next-innings)
 * - Socket live snapshots
 * - Offline queue (enqueue while disconnected, flush on reconnect)
 * - Option B additions:
 *   • Map live snapshots into currentGame
 *   • Central commentary feed + postCommentary action
 *   • Shaped scorecard rows for components
 *   • Small strike/wicket UX helpers
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/* Types — single source of truth (your existing /types barrel) */
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

/* If you have a centralized apiService, keep using it for CRUD */
import { apiService, getErrorMessage } from '@/utils/api'

/* Socket helpers (now including joinGame + emit) */
import {
  on as onSocket,
  off as offSocket,
  connectSocket,
  disconnectSocket,
  joinGame as joinGameSocket,
  emit as emitSocket,
} from '@/utils/socket'

/* Score payload from the deliveries endpoint (services/api) */
import type { ScoreUpdatePayload, BatterLine, BowlerLine } from '@/services/api'

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

/* Commentary (Option B) */
type CommentaryItem = { id: string; at: number; over?: string; text: string; author?: string }

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

  /* Commentary feed (Option B) */
  const commentaryFeed = ref<CommentaryItem[]>([])

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
   * Shaped scorecards for components (Option B)
   * ====================================================================== */
  const battingRows = computed(() => {
    const g = currentGame.value
    if (!g || !g.batting_scorecard) return []
    return Object.values(g.batting_scorecard).map((row) => ({
      id: row.player_id,
      name: row.player_name,
      runs: row.runs,
      balls: row.balls,
      fours: row.fours,
      sixes: row.sixes,
      sr: row.strike_rate,
      howOut: row.how_out,
      isOut: row.is_out,
    }))
  })

  const bowlingRows = computed(() => {
    const g = currentGame.value
    if (!g || !g.bowling_scorecard) return []
    return Object.values(g.bowling_scorecard).map((row) => ({
      id: row.player_id,
      name: row.player_name,
      overs: row.overs,
      maidens: row.maidens,
      runs: row.runs_conceded,
      wkts: row.wickets,
      econ: row.economy,
    }))
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

  // Convert "14.3" -> { overs_completed: 14, balls_this_over: 3 }
  function splitOvers(oversStr?: string): { overs_completed: number; balls_this_over: number } {
    if (!oversStr) return { overs_completed: 0, balls_this_over: 0 };
    const [o, b] = oversStr.split('.');
    const oi = Number.isFinite(Number(o)) ? Number(o) : 0;
    const bi = Number.isFinite(Number(b)) ? Number(b) : 0;
    return { overs_completed: oi, balls_this_over: bi };
  }


  // Map ScoreUpdatePayload (server snapshot) into your Snapshot shape
  function mapScorePayloadToSnapshot(p: ScoreUpdatePayload): Snapshot {
  const { score, batting, bowling } = p;

  const battingCard: Record<string, BattingScorecardEntry> = {};
  batting.forEach((b) => {
    battingCard[b.player_id] = {
      player_id: b.player_id,
      player_name: b.name,
      runs: b.runs,
      balls: b.balls,
      fours: b.fours,
      sixes: b.sixes,
      strike_rate: b.strike_rate,
      // If your backend sends how_out/is_out, map them here. Using placeholders:
      how_out: b.is_striker ? 'not out' : undefined as unknown as string,
      is_out: false,
    };
  });

  const bowlingCard: Record<string, BowlingScorecardEntry> = {};
  bowling.forEach((bw) => {
    bowlingCard[bw.player_id] = {
      player_id: bw.player_id,
      player_name: bw.name,
      overs: bw.overs,
      maidens: bw.maidens,
      runs_conceded: bw.runs,
      wickets: bw.wickets,
      economy: bw.econ,
    };
  });

  const { overs_completed, balls_this_over } = splitOvers(score.overs);

  // If Team JSON in GameState has no `id`, don’t try to resolve names by id.
  // Keep current names from `currentGame` so types stay `string`.
  const battingTeamName =
    currentGame.value?.batting_team_name ?? (currentGame.value?.team_a?.name || '') as string;
  const bowlingTeamName =
    currentGame.value?.bowling_team_name ?? (currentGame.value?.team_b?.name || '') as string;

  const snap: Snapshot = {
    total_runs: score.runs,
    total_wickets: score.wickets,
    overs_completed,
    balls_this_over,
    current_inning: score.innings_no,
    batting_team_name: battingTeamName,
    bowling_team_name: bowlingTeamName,
    batting_scorecard: battingCard,
    bowling_scorecard: bowlingCard,
  };
  return snap;
}

  

  // Merge a partial live snapshot into the current game (reactive-safe)
  function applySnapshotToGame(s: Snapshot) {
    if (!currentGame.value) return
    const g: any = currentGame.value
    const snap: any = s

    // Core scoreboard
    if (snap.total_runs != null) g.total_runs = snap.total_runs
    if (snap.total_wickets != null) g.total_wickets = snap.total_wickets
    if (snap.overs_completed != null) g.overs_completed = snap.overs_completed
    if (snap.balls_this_over != null) g.balls_this_over = snap.balls_this_over
    if (snap.current_inning != null) g.current_inning = snap.current_inning
    if (snap.status != null) g.status = snap.status
    if (snap.target != null) g.target = snap.target

    // Which team is batting/bowling (affects selectors & cards)
    if (snap.batting_team_name != null) g.batting_team_name = snap.batting_team_name
    if (snap.bowling_team_name != null) g.bowling_team_name = snap.bowling_team_name

    // Live rosters/scorecards
    if (snap.batting_scorecard) g.batting_scorecard = snap.batting_scorecard
    if (snap.bowling_scorecard) g.bowling_scorecard = snap.bowling_scorecard

    // New deliveries (if your server emits them)
    if (Array.isArray(snap.deliveries)) g.deliveries = snap.deliveries

    // Optional convenience fields your backend might send
    if (snap.current_striker_id != null) g.current_striker_id = snap.current_striker_id
    if (snap.current_non_striker_id != null) g.current_non_striker_id = snap.current_non_striker_id
  }

  function handleStateUpdate(payload: StateUpdatePayload) {
    if (!liveGameId.value || payload.id !== liveGameId.value) return
    liveSnapshot.value = payload.snapshot
    lastLiveAt.value = Date.now()
    applySnapshotToGame(payload.snapshot)
  }

  function handleScoreUpdate(payload: ScoreUpdatePayload) {
    if (!liveGameId.value) return
    const snap = mapScorePayloadToSnapshot(payload)
    liveSnapshot.value = { ...(liveSnapshot.value || {}), ...snap }
    lastLiveAt.value = Date.now()
    applySnapshotToGame(snap)
  }

  const handleCommentary = (msg: {
    id: string
    at: number
    text: string
    over?: string
    author?: string
    game_id: string
  }) => {
    if (!liveGameId.value || msg.game_id !== liveGameId.value) return
    commentaryFeed.value.unshift({
      id: msg.id,
      at: msg.at,
      over: msg.over,
      text: msg.text,
      author: msg.author,
    })
    if (commentaryFeed.value.length > 200) commentaryFeed.value.pop()
  }

  async function initLive(id: string) {
    liveGameId.value = id
    connectionStatus.value = 'connecting'
    isLive.value = true

    try {
      connectSocket()

      // Join the game room (prefer helper; fall back to plain emit if needed)
      if (typeof joinGameSocket === 'function') {
        joinGameSocket(id)
      } else {
        emitSocket('join_game', { game_id: id })
      }

      // Connection ack
      onSocket('hello', () => {
        connectionStatus.value = 'connected'
        if (liveGameId.value) flushQueue(liveGameId.value).catch(() => {})
      })

      // Live updates
      onSocket('state:update', handleStateUpdate)
      onSocket('score:update', handleScoreUpdate)

      // Commentary (server payload: { game_id, text, at })
      onSocket('commentary:new', (payload: { game_id: string; text: string; at: string }) => {
        if (!liveGameId.value || payload.game_id !== liveGameId.value) return
        commentaryFeed.value.unshift({
          id: makeId(),
          at: Date.parse(payload.at) || Date.now(),
          text: payload.text,
        })
        if (commentaryFeed.value.length > 200) commentaryFeed.value.pop()
      })
    } catch (e) {
      connectionStatus.value = 'error'
      console.error('Socket error:', e)
    }
  }



  function stopLive() {
    offSocket('state:update', handleStateUpdate)
    offSocket('score:update', handleScoreUpdate)
    offSocket('commentary:new') // no handler needed since we inlined it
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

  /* Optional small UX helpers (Option B) */
  function afterRunsApplied(runs: number, isExtra?: boolean) {
    if (runs % 2 === 1 && !isExtra) {
      swapBatsmen()
    }
  }

  function afterWicketApplied(dismissed_player_id: string) {
    if (uiState.value.selectedStrikerId === dismissed_player_id) {
      uiState.value.selectedStrikerId = null
    }
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
    const res = await submitDelivery(gameId, payload)
    afterRunsApplied(runs, false)
    return res
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
    const res = await submitDelivery(gameId, payload)
    // For simplicity, consider extras as not rotating strike here
    afterRunsApplied(runs, true)
    return res
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
    const res = await submitDelivery(gameId, payload)
    afterWicketApplied(payload.dismissed_player_id!)
    return res
  }

  /* Commentary action (Option B) */
  async function postCommentary(gameId: string, text: string, over?: string) {
    const tempId = makeId()
    const tempItem: CommentaryItem = { id: tempId, at: Date.now(), text, over }
    commentaryFeed.value.unshift(tempItem)

    try {
      await apiService.postCommentary(gameId, { text, over })
      return { ok: true }
    } catch (e) {
      // Roll back optimistic insert on failure
      commentaryFeed.value = commentaryFeed.value.filter((c) => c.id !== tempId)
      throw e
    }
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
    commentaryFeed.value = []
  }

  /* Optional: merge partial patches into currentGame */
  function mergeGamePatch(patch: Partial<GameState>) {
    if (!currentGame.value) return
    currentGame.value = { ...currentGame.value, ...patch }
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

    // Shaped scorecards (Option B)
    battingRows,
    bowlingRows,

    // Live
    isLive,
    liveGameId,
    connectionStatus,
    lastLiveAt,
    liveSnapshot,
    initLive,
    stopLive,

    // Commentary (Option B)
    commentaryFeed,
    postCommentary,

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
    mergeGamePatch,
  }
})

// src/stores/gameStore.ts

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// ---- UI domain types
import type {
  GameState,
  Player,
  Team,
  BattingScorecardEntry,
  BowlingScorecardEntry,
  Snapshot as UiSnapshot,
  UIState,
  MatchType,
  MatchStatus,
} from '@/types'

// ---- API client & wire types
import { apiService, getErrorMessage } from '@/utils/api'
import type {
  CreateGameRequest as ApiCreateGameRequest,
  ScoreDeliveryRequest as ApiScoreDeliveryRequest,
  Snapshot as ApiSnapshot,
} from '@/utils/api'

// ---- Socket helpers
import {
  on as onSocket,
  off as offSocket,
  connectSocket,
  disconnectSocket,
  joinGame as joinGameSocket,
  emit as emitSocket,
} from '@/utils/socket'

// ---- Cricket math helpers
import {
  isLegalBall,
  fmtEconomy,
  oversDisplayFromBalls,
  oversNotationToFloat,
} from '@/utils/cricket'

import { getDlsPreview, postDlsApply, patchReduceOvers, type DLSPreviewOut } from '@/utils/api'
import type { Interruption as ApiInterruption } from '@/utils/api'
// Loose wrappers so we can listen to custom events
const on = onSocket as unknown as (event: string, handler: (...args: any[]) => void) => void
const off = offSocket as unknown as (event: string, handler?: (...args: any[]) => void) => void

// ---------------------------------------------------------------------------
// Local helpers & types
// ---------------------------------------------------------------------------

type PendingStatus = 'queued' | 'flushing' | 'failed'
interface PendingDelivery {
  id: string
  gameId: string
  payload: ApiScoreDeliveryRequest
  createdAt: number
  tries: number
  status: PendingStatus
}

function makeId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

interface CommentaryItem { id: string; at: number; over?: string; text: string; author?: string }

interface ScoreUpdatePayloadSlim {
  game_id?: string
  score?: { runs: number; wickets: number; overs: string | number; innings_no?: number }
  batting?: Array<{ player_id: string; name: string; runs: number; balls?: number; fours?: number; sixes?: number; strike_rate?: number; is_striker?: boolean }>
  bowling?: Array<{ player_id: string; name: string; overs?: number | string; maidens?: number; runs: number; wickets: number; econ?: number }>
}

function splitOvers(overs: string | number | undefined): { overs_completed: number; balls_this_over: number } {
  if (overs == null) return { overs_completed: 0, balls_this_over: 0 }
  if (typeof overs === 'number') {
    const whole = Math.trunc(overs)
    const frac = Math.round((overs - whole) * 10)
    return { overs_completed: whole, balls_this_over: frac }
  }
  const [o, b] = String(overs).split('.')
  const oi = Number.isFinite(Number(o)) ? Number(o) : 0
  const bi = Number.isFinite(Number(b)) ? Number(b) : 0
  return { overs_completed: oi, balls_this_over: bi }
}

function coerceSnapshot(s: ApiSnapshot | any): UiSnapshot {
  const overAny = s?.over?.completed ?? s?.overs_completed ?? 0
  const ballsAny = s?.over?.balls_this_over ?? s?.balls_this_over ?? 0

  return {
    total_runs: Number(s?.total_runs ?? s?.score?.runs ?? 0),
    total_wickets: Number(s?.total_wickets ?? s?.score?.wickets ?? 0),
    overs_completed: Number(overAny),
    balls_this_over: Number(ballsAny),
    current_inning: Number(s?.current_inning ?? 1),
    batting_team_name: String(s?.batting_team_name ?? s?.teams?.batting?.name ?? ''),
    bowling_team_name: String(s?.bowling_team_name ?? s?.teams?.bowling?.name ?? ''),

    batting_scorecard: (s?.batting_scorecard !== undefined ? s.batting_scorecard : undefined) as any,
    bowling_scorecard: (s?.bowling_scorecard !== undefined ? s.bowling_scorecard : undefined) as any,

    current_striker_id: s?.current_striker_id ?? null,
    current_non_striker_id: s?.current_non_striker_id ?? null,
    target: s?.target ?? null,
    status: s?.status ?? undefined,

    // ✅ top-level “gate” flags
    needs_new_batter: Boolean(s?.needs_new_batter ?? false),
    needs_new_over: Boolean(s?.needs_new_over ?? false),

    // runtime bowling context
    current_bowler_id: s?.current_bowler_id ?? s?.currentBowlerId ?? s?.current_bowler?.id ?? null,
    last_ball_bowler_id: s?.last_ball_bowler_id ?? s?.lastBallBowlerId ?? s?.last_ball_bowler?.id ?? null,
    current_over_balls: Number(s?.current_over_balls ?? s?.currentOverBalls ?? s?.balls_this_over ?? 0),
    mid_over_change_used: Boolean(s?.mid_over_change_used ?? s?.midOverChangeUsed ?? false),
    balls_bowled_total: Number(s?.balls_bowled_total ?? s?.ballsBowledTotal ?? 0),

    last_delivery: s?.last_delivery
      ? {
          over_number: Number(s.last_delivery.over_number ?? s.last_delivery.over ?? 0),
          ball_number: Number(s.last_delivery.ball_number ?? s.last_delivery.ball ?? 0),
          striker_id: String(s.last_delivery.striker_id ?? ''),
          non_striker_id: String(s.last_delivery.non_striker_id ?? ''),
          bowler_id: String(s.last_delivery.bowler_id ?? ''),
          runs_scored: Number(s.last_delivery.runs_scored ?? s.last_delivery.runs ?? 0),
          is_wicket: Boolean(s.last_delivery.is_wicket),
          is_extra: Boolean(s.last_delivery.is_extra ?? (s.last_delivery.extra_type != null || s.last_delivery.extra != null)),
          extra_type: (s.last_delivery.extra_type ?? s.last_delivery.extra ?? null) as 'wd' | 'nb' | 'b' | 'lb' | null,
          dismissal_type: s.last_delivery.dismissal_type ?? null,
          dismissed_player_id: s.last_delivery.dismissed_player_id ?? null,
          commentary: s.last_delivery.commentary ?? null,
          fielder_id: s.last_delivery.fielder_id ?? null,
          at_utc: s.last_delivery.at_utc ?? null,
        }
      : null,
  } as UiSnapshot
}



function mergeScorecard<T extends Record<string, any>>(
  prev: Record<string, T> | undefined,
  patch: Record<string, Partial<T>> | undefined
): Record<string, T> | undefined {
  if (!patch) return prev
  const next: Record<string, T> = { ...(prev || {}) } as any
  for (const [id, row] of Object.entries(patch)) {
    next[id] = { ...(next[id] as any), ...(row as any) } as T
  }
  return next
}

function normalizeServerSnapshot(s: any): UiSnapshot {
  const total_runs = s?.total_runs ?? s?.score?.runs ?? 0
  const total_wickets = s?.total_wickets ?? s?.score?.wickets ?? 0
  const ocRaw: string | number | undefined =
  s?.over?.completed ?? s?.overs_completed ?? s?.score?.overs ?? s?.overs
  const { overs_completed, balls_this_over } = splitOvers(ocRaw)

  return {
    total_runs,
    total_wickets,
    overs_completed,
    balls_this_over: s?.balls_this_over ?? s?.over?.balls_this_over ?? balls_this_over,
    current_inning: Number(s?.current_inning ?? 1),
    batting_team_name: s?.batting_team_name ?? s?.teams?.batting?.name ?? '',
    bowling_team_name: s?.bowling_team_name ?? s?.teams?.bowling?.name ?? '',
    batting_scorecard: (s?.batting_scorecard ?? {}) as Record<string, BattingScorecardEntry>,
    bowling_scorecard: (s?.bowling_scorecard ?? {}) as Record<string, BowlingScorecardEntry>,
    current_striker_id: s?.current_striker_id ?? null,
    current_non_striker_id: s?.current_non_striker_id ?? null,

    // runtime bowling fields
    current_bowler_id: s?.current_bowler_id ?? s?.currentBowlerId ?? s?.current_bowler?.id ?? null,
    last_ball_bowler_id: s?.last_ball_bowler_id ?? s?.lastBallBowlerId ?? s?.last_ball_bowler?.id ?? null,
    current_over_balls: Number(s?.current_over_balls ?? s?.currentOverBalls ?? s?.balls_this_over ?? 0),
    mid_over_change_used: Boolean(s?.mid_over_change_used ?? s?.midOverChangeUsed ?? false),
    balls_bowled_total: Number(s?.balls_bowled_total ?? s?.ballsBowledTotal ?? 0),
    needs_new_batter: Boolean(s?.needs_new_batter ?? false),
    needs_new_over: Boolean(s?.needs_new_over ?? false),
    target: s?.target ?? null,
    status: s?.status ?? undefined,
  }
}

function offBatRuns(d: any): number {
  const ex = (d.extra_type ?? d.extra ?? null) as 'wd' | 'nb' | 'b' | 'lb' | null
  // wides/byes/leg-byes never credit the batter
  if (ex === 'wd' || ex === 'b' || ex === 'lb') return 0
  // for nb, server wants runs_scored to be OFF-BAT runs
  return Number(d.runs_scored ?? d.runs ?? 0)
}


function coerceGameFromApi(raw: any): GameState {
  const teamA: Team = {
    name: String(raw?.team_a?.name ?? raw?.team_a_name ?? 'Team A'),
    players: (raw?.team_a?.players ?? raw?.players_a ?? []).map((p: any) => ({ id: String(p?.id), name: String(p?.name) })),
  }
  const teamB: Team = {
    name: String(raw?.team_b?.name ?? raw?.team_b_name ?? 'Team B'),
    players: (raw?.team_b?.players ?? raw?.players_b ?? []).map((p: any) => ({ id: String(p?.id), name: String(p?.name) })),
  }
  const toDecision = (v: unknown): 'bat' | 'bowl' => (v === 'bowl' ? 'bowl' : 'bat')

  return {
    id: String(raw?.id ?? raw?.game_id ?? ''),
    match_type: (raw?.match_type as MatchType) ?? 'limited',
    status: (raw?.status as MatchStatus) ?? 'in_progress',
    team_a: teamA,
    team_b: teamB,
    dls_enabled: Boolean(raw?.dls_enabled ?? false),
    interruptions: raw?.interruptions ?? [],
    toss_winner_team: String(raw?.toss_winner_team ?? ''),
    decision: toDecision(raw?.decision),
    batting_team_name: String(raw?.batting_team_name ?? teamA.name),
    bowling_team_name: String(raw?.bowling_team_name ?? teamB.name),
    overs_limit: Number(raw?.overs_limit ?? 0) as any,

    current_inning: Number(raw?.current_inning ?? 1),
    total_runs: Number(raw?.total_runs ?? 0),
    total_wickets: Number(raw?.total_wickets ?? 0),
    overs_completed: Number(raw?.overs_completed ?? 0),
    balls_this_over: Number(raw?.balls_this_over ?? 0),
    current_striker_id: raw?.current_striker_id ?? null,
    current_non_striker_id: raw?.current_non_striker_id ?? null,
    target: raw?.target ?? null,
    result: raw?.result ?? null,

    // roles
    team_a_captain_id: raw?.team_a_captain_id ?? null,
    team_a_keeper_id: raw?.team_a_keeper_id ?? null,
    team_b_captain_id: raw?.team_b_captain_id ?? null,
    team_b_keeper_id: raw?.team_b_keeper_id ?? null,

    // deliveries
    deliveries: Array.isArray(raw?.deliveries)
      ? raw.deliveries.map((d: any) => ({
          over_number: Number(d.over_number ?? d.over ?? 0),
          ball_number: Number(d.ball_number ?? d.ball ?? 0),
          striker_id: String(d.striker_id ?? ''),
          non_striker_id: String(d.non_striker_id ?? ''),
          bowler_id: String(d.bowler_id ?? ''),
          runs_scored: Number(d.runs_scored ?? d.runs ?? 0),
          is_wicket: Boolean(d.is_wicket),
          is_extra: Boolean(d.is_extra ?? (d.extra_type != null || d.extra != null)),
          extra_type: (d.extra_type ?? d.extra ?? null) as 'wd' | 'nb' | 'b' | 'lb' | null,
          dismissal_type: d.dismissal_type ?? null,
          dismissed_player_id: d.dismissed_player_id ?? null,
          commentary: d.commentary ?? null,
          fielder_id: d.fielder_id ?? null,
          at_utc: d.at_utc ?? null,
        }))
      : [],

    batting_scorecard: (raw?.batting_scorecard ?? {}) as Record<string, BattingScorecardEntry>,
    bowling_scorecard: (raw?.bowling_scorecard ?? {}) as Record<string, BowlingScorecardEntry>,
  } as GameState
}


export const useGameStore = defineStore('game', () => {
  // ========================================================================
  // Reactive State
  // ========================================================================
  const currentGame = ref<GameState | null>(null)
  
  const dlsPanel = ref<{ method: 'DLS'; par?: number; target?: number } | null>(null)
  
  const dlsPreview = ref<DLSPreviewOut | null>(null)
  const dlsApplied = ref(false)
  const dlsKind = computed<'odi' | 't20'>(() => {
    const g = currentGame.value
    const limit = Number((g as any)?.overs_limit ?? 0)
    return limit >= 40 ? 'odi' : 't20'
  })

  // Keeps currentGame.overs_limit in sync if the object actually contains it
  function syncOversLimitFrom(obj: any): void {
    if (!currentGame.value) return
    if (obj && Object.prototype.hasOwnProperty.call(obj, 'overs_limit')) {
      ;(currentGame.value as any).overs_limit = Number(obj.overs_limit ?? 0)
    }
  }

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

  const isLive = ref(false)
  const liveGameId = ref<string | null>(null)
  const connectionStatus = ref<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected')
  const lastLiveAt = ref<number | null>(null)
  const liveSnapshot = ref<UiSnapshot | null>(null)
  const needsNewBatter = computed(() =>
    Boolean(liveSnapshot.value?.needs_new_batter ?? (currentGame.value as any)?.needs_new_batter ?? false)
  )
  const needsNewOver = computed(() =>
    Boolean(liveSnapshot.value?.needs_new_over ?? (currentGame.value as any)?.needs_new_over ?? false)
  )

  const commentaryFeed = ref<CommentaryItem[]>([])

  const offlineEnabled = ref(true)
  const offlineQueue = ref<PendingDelivery[]>([])
  const isFlushing = ref(false)
  const QKEY = 'cricksy.offline.queue.v1'

  function loadQueue(): void {
    try {
      const raw = localStorage.getItem(QKEY)
      offlineQueue.value = raw ? (JSON.parse(raw) as PendingDelivery[]) : []
    } catch {
      offlineQueue.value = []
    }
  }
  function saveQueue(): void {
    try {
      localStorage.setItem(QKEY, JSON.stringify(offlineQueue.value))
    } catch { /* noop */ }
  }
  loadQueue()

  // ========================================================================
  // Proxies & Status
  // ========================================================================
  const isLoading = computed<boolean>(() => uiState.value.loading)
  const error = computed<string | null>(() => uiState.value.error)

  const isGameActive = computed<boolean>(() => currentGame.value?.status === 'in_progress')
  const isInningsBreak = computed<boolean>(() => currentGame.value?.status === 'innings_break')
  const isGameCompleted = computed<boolean>(() => currentGame.value?.status === 'completed')
  const isFirstInnings = computed<boolean>(() => (currentGame.value?.current_inning ?? 1) === 1)
  const isSecondInnings = computed<boolean>(() => (currentGame.value?.current_inning ?? 1) === 2)

  // ========================================================================
  // Teams & Players
  // ========================================================================
  const battingTeam = computed<Team | null>(() => {
    const g = currentGame.value
    if (!g) return null
    return g.batting_team_name === g.team_a.name ? g.team_a : g.team_b
  })

  const bowlingTeam = computed<Team | null>(() => {
    const g = currentGame.value
    if (!g) return null
    return g.bowling_team_name === g.team_a.name ? g.team_a : g.team_b
  })
  const bowlingTeamPlayers = computed<Player[]>(() => bowlingTeam.value?.players ?? [])

  // Minimal score object
  const score = computed(() => ({
    runs: Number(currentGame.value?.total_runs ?? 0),
    wickets: Number(currentGame.value?.total_wickets ?? 0),
  }))

  // Current-innings deliveries passthrough
  const currentInningsDeliveries = computed(() =>
    Array.isArray(currentGame.value?.deliveries) ? currentGame.value!.deliveries : []
  )

  // Optional: pre-aggregated bowling stats by player (runs/balls)
  const bowlingStatsByPlayer = computed<Record<string, { runsConceded: number; balls: number }>>(() => {
    const delivs: any[] = Array.isArray(currentInningsDeliveries.value) ? (currentInningsDeliveries.value as any[]) : []
    const map: Record<string, { runsConceded: number; balls: number }> = {}

    for (const d of delivs) {
      const id = String(d.bowler_id || '')
      if (!id) continue
      if (!map[id]) map[id] = { runsConceded: 0, balls: 0 }

      const offBat = offBatRuns(d)
      const ex = (d.extra_type ?? d.extra ?? null) as 'wd' | 'nb' | 'b' | 'lb' | null
      let extrasConceded = 0
      if (ex === 'wd') extrasConceded += Number(d.runs_scored ?? d.runs ?? 1) || 1
      else if (ex === 'nb') extrasConceded += 1
      else if (ex === 'b' || ex === 'lb') extrasConceded += Number(d.runs_scored ?? d.runs ?? 0)
      map[id].runsConceded += offBat + extrasConceded
      if (isLegalBall(d)) map[id].balls += 1
    }

    return map
  })

  const availableBatsmen = computed<Player[]>(() => {
    const team = battingTeam.value
    const g = currentGame.value
    if (!team || !g) return []
    const card = (g.batting_scorecard || {}) as Record<string, BattingScorecardEntry>
    return team.players.filter((p) => !card[p.id]?.is_out)
  })

  const availableBowlers = computed<Player[]>(() => bowlingTeam.value ? bowlingTeam.value.players : [])

  
  // ========================================================================
  // Score helpers
  // ========================================================================
  const currentOver = computed<string>(() => {
    const g = currentGame.value
    if (!g) return '0.0'
    const o = g.overs_completed ?? 0
    const b = g.balls_this_over ?? 0
    return `${o}.${b}`
  })

  const scoreDisplay = computed<string>(() => {
    const g = currentGame.value
    if (!g) return '0/0 (0.0)'
    const r = g.total_runs ?? 0
    const w = g.total_wickets ?? 0
    return `${r}/${w} (${currentOver.value})`
  })

  const targetDisplay = computed<string>(() => {
    const g = currentGame.value
    if (!g || g.target == null) return ''
    return `Target: ${g.target}`
  })

  const runsRequired = computed<number | null>(() => {
    const g = currentGame.value
    if (!g || g.target == null) return null
    const req = g.target - (g.total_runs ?? 0)
    return req > 0 ? req : 0
  })

  // ⬇️ ADD: DLS convenience getters
const isChase = computed<boolean>(() =>
  (liveSnapshot.value?.current_inning ?? currentGame.value?.current_inning ?? 1) >= 2
)

const dls = computed(() => dlsPanel.value)
const dlsPar = computed<number | null>(() => dlsPanel.value?.par ?? null)
const dlsTarget = computed<number | null>(() => dlsPanel.value?.target ?? null)
const dlsAheadBy = computed<number | null>(() => {
  if (!isChase.value) return null
  const par = dlsPanel.value?.par
  if (par == null) return null
  const runsNow = liveSnapshot.value?.total_runs ?? currentGame.value?.total_runs ?? 0
  return runsNow - par // + ahead, - behind, 0 level
})

  // ========================================================================
  // Scorecards (defensive shaping)
  // ========================================================================
  const battingRows = computed(() => {
    const g = currentGame.value
    if (!g || !g.batting_scorecard) return [] as Array<{
      id: string; name: string; runs: number; balls: number; fours: number; sixes: number; sr: number; howOut?: string; isOut: boolean
    }>

    return Object.values(g.batting_scorecard as Record<string, any>).map((row: any) => {
      const id = String(row.player_id)
      const name = String(row.player_name || '')
      const runs = Number(row.runs ?? 0)
      const balls = Number(row.balls_faced ?? row.balls ?? 0)
      const fours = Number(row.fours ?? 0)
      const sixes = Number(row.sixes ?? 0)
      const sr = balls > 0 ? Number(((runs * 100) / balls).toFixed(1)) : 0

      return {
        id, name, runs, balls, fours, sixes, sr,
        howOut: row.how_out,
        isOut: Boolean(row.is_out),
      }
    })
  })

  
  const extrasBreakdown = computed(() => {
    type D = {
      extra_type?: 'wd' | 'nb' | 'b' | 'lb' | null
      extra?: 'wd' | 'nb' | 'b' | 'lb' | null
      runs_scored?: number
      runs?: number
    }

    const delivs = (currentInningsDeliveries.value ?? []) as D[]

    let wides = 0, no_balls = 0, byes = 0, leg_byes = 0, penalty = 0

    for (const d of delivs) {
      const ex = (d.extra_type ?? d.extra ?? null) as D['extra_type']
      const r = Number(d.runs_scored ?? d.runs ?? 0)

      if (ex === 'wd') {
        // wides are all extras; if server sent 0/undefined, count as 1
        wides += r || 1
      } else if (ex === 'nb') {
        // only the 1 penalty is an extra; off-bat runs go to batter
        no_balls += 1
      } else if (ex === 'b') {
        byes += r
      } else if (ex === 'lb') {
        leg_byes += r
      }
    }

    const total = wides + no_balls + byes + leg_byes + penalty
    return { wides, no_balls, byes, leg_byes, penalty, total }
  })


  const bowlingRows = computed(() => {
    const g = currentGame.value
    if (!g || !g.bowling_scorecard) {
      return [] as Array<{ id: string; name: string; overs: string; maidens: number; runs: number; wkts: number; econ: number | string }>
    }

    return Object.values(g.bowling_scorecard as Record<string, any>).map((row: any) => {
      const id = String(row.player_id)
      const name = String(row.player_name || '')
      const maidens = Number(row.maidens ?? 0)
      const wkts = Number(row.wickets ?? row.wickets_taken ?? 0)

      const stats = bowlingStatsByPlayer.value[id]

      // balls from deliveries if we have them; else from overs notation on the card
      const balls = typeof stats?.balls === 'number'
        ? stats.balls
        : Math.round(oversNotationToFloat(row.overs ?? row.overs_bowled ?? 0) * 6)

      // runs conceded from deliveries if we have them; else from the card
      const runs = typeof stats?.runsConceded === 'number'
        ? stats.runsConceded
        : Number(row.runs_conceded ?? row.runs ?? 0)

      const oversText = oversDisplayFromBalls(Math.max(0, balls | 0))
      const econ = balls > 0 ? Number(fmtEconomy(runs, balls)) : (typeof row.economy === 'number' ? row.economy : '—')

      return { id, name, overs: oversText, maidens, runs, wkts, econ }
    })
  })


  // Merge liveSnapshot + game for simple access in views
    const state = computed(() => {
      const g: any = currentGame.value || {}
      const s: any = liveSnapshot.value || {}
      return {
        balls_this_over: Number(g.balls_this_over ?? s.balls_this_over ?? 0),
        current_bowler_id: s.current_bowler_id ?? g.current_bowler_id ?? null,
        last_ball_bowler_id: s.last_ball_bowler_id ?? g.last_ball_bowler_id ?? null,
        current_over_balls: Number(s.current_over_balls ?? g.current_over_balls ?? g.balls_this_over ?? 0),
        mid_over_change_used: Boolean(s.mid_over_change_used ?? g.mid_over_change_used ?? false),
        balls_bowled_total: Number(s.balls_bowled_total ?? g.balls_bowled_total ?? 0),
        needs_new_batter: Boolean(s.needs_new_batter ?? false),
        needs_new_over: Boolean(s.needs_new_over ?? false),
      }
    })

    // --- XI helpers -------------------------------------------------------------
function playingXI(team: Team | null): Player[] {
  if (!team) return []
  // OPTIONAL: if you keep explicit XI ids, prefer them:
  // const xiIds: string[] | undefined = (currentGame.value as any)?.[team.name === currentGame.value?.team_a.name ? 'team_a_xi_ids' : 'team_b_xi_ids']
  // if (Array.isArray(xiIds) && xiIds.length) {
  //   const map = new Map(team.players.map(p => [p.id, p]))
  //   return xiIds.map(id => map.get(String(id))).filter(Boolean) as Player[]
  // }
  return (team.players || []).slice(0, 11)  // default: first 11 in order
}

const battingXI = computed<Player[]>(() => playingXI(battingTeam.value))
const bowlingXI = computed<Player[]>(() => playingXI(bowlingTeam.value))

function makeBattingRow(p: Player, row: any) {
  const runs = Number(row?.runs ?? 0)
  const balls = Number(row?.balls_faced ?? row?.balls ?? 0)
  const fours = Number(row?.fours ?? 0)
  const sixes = Number(row?.sixes ?? 0)
  const sr = balls > 0 ? Number(((runs * 100) / balls).toFixed(1)) : 0
  return {
    id: p.id,
    name: p.name,
    runs, balls, fours, sixes, sr,
    howOut: row?.how_out,
    isOut: Boolean(row?.is_out),
  }
}

/** Show only batters up to the highest position that has appeared (in or out). */
const battingRowsXI = computed(() => {
  const g = currentGame.value
  const xi = battingXI.value
  if (!g || !xi.length) return [] as Array<{ id:string; name:string; runs:number; balls:number; fours:number; sixes:number; sr:number; howOut?:string; isOut:boolean }>
  const card = (g.batting_scorecard ?? {}) as Record<string, any>

  // anyone currently batting
  const included = new Set<string>()
  if (g.current_striker_id) included.add(String(g.current_striker_id))
  if (g.current_non_striker_id) included.add(String(g.current_non_striker_id))

  // anyone who has faced a ball or got out
  for (const [id, row] of Object.entries(card)) {
    const balls = Number(row?.balls_faced ?? row?.balls ?? 0)
    if (balls > 0 || row?.is_out) included.add(String(id))
  }

  // cap list at the highest XI index that’s included.
  let maxIdx = -1
  xi.forEach((p, idx) => { if (included.has(p.id)) maxIdx = Math.max(maxIdx, idx) })
  // Before first ball, default to openers
  if (maxIdx < 0) maxIdx = Math.min(1, xi.length - 1)

  const upto = xi.slice(0, maxIdx + 1)
  return upto.map(p => makeBattingRow(p, card[p.id] || {}))
})

/** Only bowlers who’ve actually bowled (≥1 legal ball), limited to XI. */
const bowlingRowsXI = computed(() => {
  const g = currentGame.value
  if (!g) return [] as Array<{ id:string; name:string; overs:string; maidens:number; runs:number; wkts:number; econ:number|string }>
  const xiIds = new Set(bowlingXI.value.map(p => p.id))
  const statsMap = bowlingStatsByPlayer.value
  const card = (g.bowling_scorecard ?? {}) as Record<string, any>

  function ballsFrom(row:any, id:string) {
    if (typeof statsMap[id]?.balls === 'number') return statsMap[id].balls
    const o = row?.overs ?? row?.overs_bowled ?? 0
    return Math.round(oversNotationToFloat(o) * 6)
  }
  function runsFrom(row:any, id:string) {
    if (typeof statsMap[id]?.runsConceded === 'number') return statsMap[id].runsConceded
    return Number(row?.runs_conceded ?? row?.runs ?? 0)
  }

  
  // consider union of XI ids that appear in either card or stats
  const ids = new Set<string>()
  Object.keys(card).forEach(id => { if (xiIds.has(id)) ids.add(id) })
  Object.keys(statsMap).forEach(id => { if (xiIds.has(id)) ids.add(id) })

  const rows = [] as Array<{ id:string; name:string; overs:string; maidens:number; runs:number; wkts:number; econ:number|string }>
  for (const id of ids) {
    const row = card[id] || {}
    const balls = ballsFrom(row, id)
    const hasBowled = balls > 0
    if (!hasBowled) continue

    const runs = runsFrom(row, id)
    const maidens = Number(row?.maidens ?? 0)
    const wkts = Number(row?.wickets ?? row?.wickets_taken ?? 0)
    const oversText = oversDisplayFromBalls(Math.max(0, balls | 0))
    const econ = balls > 0 ? Number(fmtEconomy(runs, balls)) : (typeof row?.economy === 'number' ? row.economy : '—')

    // find name from XI
    const name = (bowlingXI.value.find(p => p.id === id)?.name) || String(row?.player_name || '')
    rows.push({ id, name, overs: oversText, maidens, runs, wkts, econ })
  }
  return rows
})

// Players on the current fielding team who are NOT in the XI
const fieldingBench = computed<Player[]>(() => {
  const team = bowlingTeam.value
  if (!team) return []
  const xiIds = new Set((bowlingXI.value || []).map(p => p.id))
  return (team.players || []).filter(p => !xiIds.has(p.id))
})

// --- Helpers to resolve XI ids for batting/bowling sides
function resolveXIForTeam(team: Team | null | undefined, sideKey: 'A' | 'B'): Set<string> {
  if (!team) return new Set<string>()
  // prefer explicit XI if present on the team or game
  const g: any = currentGame.value as any
  const explicit: string[] =
    (team as any)?.playing_xi
    ?? (sideKey === 'A' ? g?.team_a_xi_ids : g?.team_b_xi_ids)
    ?? []
  if (Array.isArray(explicit) && explicit.length) return new Set(explicit.map(String))
  // fallback: first 11 from roster order
  return new Set((team.players || []).slice(0, 11).map(p => String(p.id)))
}

function sideOf(teamName: string | undefined): 'A' | 'B' | null {
  const g = currentGame.value
  if (!g || !teamName) return null
  if (teamName === g.team_a.name) return 'A'
  if (teamName === g.team_b.name) return 'B'
  return null
}

// ---------- UI rosters ----------
const battingRosterXI = computed<Player[]>(() => {
  const g = currentGame.value
  if (!g) return []
  const battingIsA = sideOf(g.batting_team_name) === 'A'
  const team = battingIsA ? g.team_a : g.team_b
  const xi = resolveXIForTeam(team, battingIsA ? 'A' : 'B')
  return (team.players || []).filter(p => xi.has(p.id))
})

const bowlingRosterXI = computed<Player[]>(() => {
  const g = currentGame.value
  if (!g) return []
  const bowlingIsA = sideOf(g.bowling_team_name) === 'A'
  const team = bowlingIsA ? g.team_a : g.team_b
  const xi = resolveXIForTeam(team, bowlingIsA ? 'A' : 'B')
  return (team.players || []).filter(p => xi.has(p.id))
})

/** Fielding subs = players on fielding team who are NOT in the XI (for catches/run-outs). */
const fieldingSubs = computed<Player[]>(() => {
  const g = currentGame.value
  if (!g) return []
  const bowlingIsA = sideOf(g.bowling_team_name) === 'A'
  const team = bowlingIsA ? g.team_a : g.team_b
  const xi = resolveXIForTeam(team, bowlingIsA ? 'A' : 'B')
  return (team.players || []).filter(p => !xi.has(p.id))
})

/** If you want one list that contains XI + subs specifically for fielder pickers: */
const fielderRosterAll = computed<Player[]>(() => {
  const g = currentGame.value
  if (!g) return []
  const bowlingIsA = sideOf(g.bowling_team_name) === 'A'
  const team = bowlingIsA ? g.team_a : g.team_b
  return team.players || []
})

// ---------- Interruptions ----------
type Interruption = ApiInterruption

const interruptions = ref<Interruption[]>([])
const interruptionsLoading = ref(false)
const interruptionsError = ref<string | null>(null)
const interBusy = ref(false)

function isInterruptionOpen(it: any) {
  const end = it?.ended_at ?? it?.endedAt ?? it?.end ?? null
  // open if null / "" / undefined (many APIs omit until closed)
  return end == null || end === ''
}



function normalizeInterruption(it: any): Interruption {
  const endPresent =
    Object.prototype.hasOwnProperty.call(it, 'ended_at') ||
    Object.prototype.hasOwnProperty.call(it, 'endedAt') ||
    Object.prototype.hasOwnProperty.call(it, 'end')

  const endVal =
    Object.prototype.hasOwnProperty.call(it, 'ended_at') ? it.ended_at :
    Object.prototype.hasOwnProperty.call(it, 'endedAt') ? it.endedAt :
    Object.prototype.hasOwnProperty.call(it, 'end')     ? it.end :
    undefined

  return {
    id: String(it.id ?? it._id ?? makeId()),
    kind: String(it.kind ?? it.type ?? 'weather'),
    note: it.note ?? it.notes ?? '',
    started_at: it.started_at ?? it.startedAt ?? it.start ?? null,
    ended_at: endPresent ? (endVal ?? null) : undefined,
  }
}

/** 
 * Dedupe + throttle network calls so socket bursts don’t spam the API.
 * - Reuses an in-flight request
 * - Returns cache when called again within INTER_MIN_MS
 */
const INTER_MIN_MS = 6000
let interLastFetch = 0
let interInFlight: Promise<Interruption[]> | null = null

async function fetchInterruptions(gameId?: string, opts: { force?: boolean } = {}): Promise<Interruption[]> {
  const id = gameId ?? liveGameId.value ?? currentGame.value?.id
  if (!id) return interruptions.value

  const now = Date.now()

  // short-circuit to cache if recently fetched
  if (!opts.force && (now - interLastFetch) < INTER_MIN_MS && interruptions.value.length) {
    return interruptions.value
  }

  // dedupe concurrent callers
  if (interInFlight) return interInFlight

  interruptionsLoading.value = true
  interruptionsError.value = null

  interInFlight = (async () => {
    try {
      const raw = await apiService.getInterruptions(id)
      const list = (Array.isArray(raw) ? raw : []).map(normalizeInterruption)
      interruptions.value = list
      if (currentGame.value && 'interruptions' in (currentGame.value as any)) {
        ;(currentGame.value as any).interruptions = list
      }
      interLastFetch = Date.now()
      return list
    } catch (e: any) {
      interruptionsError.value = getErrorMessage(e)
      return interruptions.value
    } finally {
      interruptionsLoading.value = false
      interInFlight = null
    }
  })()

  return interInFlight
}

// Backward-compatible helper
function refreshInterruptions(opts: { force?: boolean } = {}) {
  return fetchInterruptions(undefined, opts)
}

// Instant UI hide when server tells us it ended (before next fetch)
function optimisticallyCloseCurrentInterruption() {
  const list = interruptions.value.slice()
  for (let i = list.length - 1; i >= 0; i--) {
    if (isInterruptionOpen(list[i])) { list[i] = { ...list[i], ended_at: undefined }; break }
  }
  interruptions.value = list
  if (currentGame.value && 'interruptions' in (currentGame.value as any)) {
    ;(currentGame.value as any).interruptions = list
  }
}

const currentInterruption = computed<Interruption | null>(() => {
  const list = interruptions.value || []
  for (let i = list.length - 1; i >= 0; i--) if (isInterruptionOpen(list[i])) return list[i]
  return null
})
const hasOpenInterruption = computed<boolean>(() => !!currentInterruption.value)

// Admin controls (idempotent)
async function startInterruption(
  kind: 'weather' | 'injury' | 'light' | 'other' | string = 'weather',
  note?: string
) {
  const id = liveGameId.value ?? currentGame.value?.id
  if (!id || interBusy.value) return
  interBusy.value = true
  try {
    await apiService.openInterruption(id, kind, note)
  } catch (e: any) {
    const msg = (e?.message || '').toLowerCase()
    if (!msg.includes('already active')) throw e
  } finally {
    await refreshInterruptions({ force: true })
    interBusy.value = false
  }
}

async function stopInterruptionAction(kind?: 'weather' | 'injury' | 'light' | 'other') {
  const id = liveGameId.value ?? currentGame.value?.id
  if (!id || interBusy.value) return
  interBusy.value = true
  try {
    await apiService.stopInterruption(id, kind)
  } catch (e: any) {
    const msg = (e?.message || '').toLowerCase()
    if (!msg.includes('no active interruption')) throw e
  } finally {
    await refreshInterruptions({ force: true })
    interBusy.value = false
  }
}


  
  function mapScorePayloadToSnapshot(p: ScoreUpdatePayloadSlim): UiSnapshot {
    const slim = p?.score ?? { runs: 0, wickets: 0, overs: '0.0' }

    // Prefer a non-zero overs source
    const fromScore = splitOvers(slim.overs)
    const fromRoot  = splitOvers((p as any)?.overs)   // e.g. "0.1" that your server sends at root
    let overs_completed = 0
    let balls_this_over = 0

    // helper: true if either part is non-zero
    const has = (x: {overs_completed:number; balls_this_over:number}) =>
      x.overs_completed > 0 || x.balls_this_over > 0

    if (has(fromRoot)) {
      overs_completed = fromRoot.overs_completed
      balls_this_over = fromRoot.balls_this_over
    } else if (has(fromScore)) {
      overs_completed = fromScore.overs_completed
      balls_this_over = fromScore.balls_this_over
    } else if ((p as any)?.last_delivery) {
      const ld = (p as any).last_delivery
      overs_completed = Number(ld.over_number ?? ld.over ?? 0)
      balls_this_over = Number(ld.ball_number ?? ld.ball ?? 0)
    } else if (liveSnapshot.value != null) {
      // Do not regress if the event is empty; coerce to numbers and keep previous if undefined
      overs_completed = Number(
        (liveSnapshot.value as Partial<UiSnapshot>).overs_completed ?? overs_completed
      )
      balls_this_over = Number(
        (liveSnapshot.value as Partial<UiSnapshot>).balls_this_over ?? balls_this_over
      )
    }


    // Build cards (unchanged)
    const battingCard: Record<string, BattingScorecardEntry> = {}
    for (const b of p?.batting ?? []) {
      battingCard[String(b.player_id)] = {
        player_id: String(b.player_id),
        player_name: String(b.name),
        runs: Number(b.runs ?? 0),
        balls_faced: Number(b.balls ?? 0),
        is_out: Boolean((b as any).is_out ?? false),
        fours: Number(b.fours ?? 0),
        sixes: Number(b.sixes ?? 0),
        strike_rate: typeof b.strike_rate === 'number' ? b.strike_rate : undefined,
      }
    }

    const bowlingCard: Record<string, BowlingScorecardEntry> = {}
    for (const bw of p?.bowling ?? []) {
      const oversNum = typeof bw.overs === 'number' ? bw.overs : (bw.overs != null ? Number(bw.overs) : 0)
      bowlingCard[String(bw.player_id)] = {
        player_id: String(bw.player_id),
        player_name: String(bw.name),
        overs_bowled: oversNum,
        runs_conceded: Number(bw.runs ?? 0),
        wickets_taken: Number(bw.wickets ?? 0),
        maidens: Number(bw.maidens ?? 0),
        economy: typeof bw.econ === 'number' ? bw.econ : undefined,
      }
    }

    return {
      total_runs: Number(slim.runs ?? 0),
      total_wickets: Number(slim.wickets ?? 0),
      overs_completed,
      balls_this_over,
      current_inning: Number(slim.innings_no ?? currentGame.value?.current_inning ?? 1),
      batting_team_name: currentGame.value?.batting_team_name ?? '',
      bowling_team_name: currentGame.value?.bowling_team_name ?? '',
      batting_scorecard: battingCard,
      bowling_scorecard: bowlingCard,
      current_striker_id: currentGame.value?.current_striker_id ?? null,
      current_non_striker_id: currentGame.value?.current_non_striker_id ?? null,
      target: currentGame.value?.target ?? null,
      status: currentGame.value?.status ?? undefined,
    }
  }


  function deliveryKey(d: any): string {
    // Robust key so score:=slim and snapshot versions dedupe
    const o = Number(d.over_number ?? d.over ?? 0)
    const b = Number(d.ball_number ?? d.ball ?? 0)
    const s = String(d.striker_id ?? '')
    const bow = String(d.bowler_id ?? '')
    const rs = Number(d.runs_scored ?? d.runs ?? 0)
    const ex = String(d.extra_type ?? d.extra ?? '')
    return `${o}|${b}|${s}|${bow}|${rs}|${ex}`
  }

  function applySnapshotToGame(s: UiSnapshot): void {
    const g = currentGame.value as GameState | null
    if (!g || !s) return

    if (s.total_runs != null) g.total_runs = s.total_runs
    if (s.total_wickets != null) g.total_wickets = s.total_wickets
    if (s.overs_completed != null) g.overs_completed = s.overs_completed
    if (s.balls_this_over != null) g.balls_this_over = s.balls_this_over
    if (s.current_inning != null) g.current_inning = s.current_inning
    if (s.status != null) g.status = s.status
    if (s.target != null) g.target = s.target
    if (s.batting_team_name != null) g.batting_team_name = s.batting_team_name
    if (s.bowling_team_name != null) g.bowling_team_name = s.bowling_team_name
    if ((s as any).needs_new_batter != null) (currentGame.value as any).needs_new_batter = Boolean((s as any).needs_new_batter)
    if ((s as any).needs_new_over   != null) (currentGame.value as any).needs_new_over   = Boolean((s as any).needs_new_over)

    // Merge cards only if present
    if (s.batting_scorecard && Object.keys(s.batting_scorecard).length > 0) {
      g.batting_scorecard = mergeScorecard(g.batting_scorecard as any, s.batting_scorecard as any) as any
    }
    if (s.bowling_scorecard && Object.keys(s.bowling_scorecard).length > 0) {
      g.bowling_scorecard = mergeScorecard(g.bowling_scorecard as any, s.bowling_scorecard as any) as any
    }

    if (s.current_striker_id !== undefined && s.current_striker_id !== null) {
      g.current_striker_id = s.current_striker_id
      // reflect in UI selectors if they differ
      uiState.value.selectedStrikerId = s.current_striker_id
    }
    if (s.current_non_striker_id !== undefined && s.current_non_striker_id !== null) {
      g.current_non_striker_id = s.current_non_striker_id
      uiState.value.selectedNonStrikerId = s.current_non_striker_id
    }

    // 🔧 bowler from snapshot should drive scoring gate
    const nextBowler = (s as any).current_bowler_id ?? null
    if (nextBowler !== null) {
      ;(currentGame.value as any).current_bowler_id = nextBowler
      uiState.value.selectedBowlerId = nextBowler
    }
    // Runtime bowling context
    const nextCurrentBowlerId =
      (s as any).current_bowler_id ?? (currentGame.value as any).current_bowler_id ?? null
    ;(currentGame.value as any).current_bowler_id = nextCurrentBowlerId

    const nextLastBallBowlerId =
      (s as any).last_ball_bowler_id ?? (currentGame.value as any).last_ball_bowler_id ?? null
    ;(currentGame.value as any).last_ball_bowler_id = nextLastBallBowlerId

    if ((s as any).current_over_balls != null) (currentGame.value as any).current_over_balls = (s as any).current_over_balls
    if ((s as any).mid_over_change_used != null) (currentGame.value as any).mid_over_change_used = (s as any).mid_over_change_used
    if ((s as any).balls_bowled_total != null) (currentGame.value as any).balls_bowled_total = (s as any).balls_bowled_total

    // Append last_delivery if new (stronger dedupe)
    const ld = (s as any).last_delivery as GameState['deliveries'][number] | null | undefined
    if (ld) {
      if (!Array.isArray(g.deliveries)) g.deliveries = []
      const k = deliveryKey(ld)
      const exists = g.deliveries.some(d => deliveryKey(d) === k)
      if (!exists) g.deliveries.push(ld)
    }
  }

  // -------------------------------------------------------------------------
  // Socket handlers
  // -------------------------------------------------------------------------
  function handleStateUpdate(payload: { id: string; snapshot: any }): void {
    if (!liveGameId.value || payload.id !== liveGameId.value) return
    const snap = normalizeServerSnapshot(payload.snapshot)
    liveSnapshot.value = snap
    lastLiveAt.value = Date.now()
    applySnapshotToGame(snap)

    syncOversLimitFrom(payload.snapshot)
    // NEW: pick up DLS panel if server included one on the snapshot
    if (payload?.snapshot?.dls && payload.snapshot.dls.method === 'DLS') {
      dlsPanel.value = {
        method: 'DLS',
        par: typeof payload.snapshot.dls.par === 'number' ? payload.snapshot.dls.par : undefined,
        target: typeof payload.snapshot.dls.target === 'number' ? payload.snapshot.dls.target : undefined,
      }
    }
  }


  async function handleScoreUpdate(payload: ScoreUpdatePayloadSlim): Promise<void> {
  const snap = mapScorePayloadToSnapshot(payload)
  liveSnapshot.value = { ...(liveSnapshot.value || ({} as UiSnapshot)), ...snap }
  lastLiveAt.value = Date.now()
  applySnapshotToGame(snap)

  // Enrich with full snapshot (cards, targets, DLS, etc.)
  try {
    if (liveGameId.value) {
      const full = await apiService.getSnapshot(liveGameId.value)
      if (full) {
        applySnapshotToGame(coerceSnapshot(full))
        if ((full as any)?.dls?.method === 'DLS') {
          dlsPanel.value = {
            method: 'DLS',
            par: typeof (full as any).dls.par === 'number' ? (full as any).dls.par : undefined,
            target: typeof (full as any).dls.target === 'number' ? (full as any).dls.target : undefined,
          }
        }
        if (currentGame.value) {
          (currentGame.value as any).overs_limit = Number((full as any)?.overs_limit ?? (currentGame.value as any).overs_limit ?? 0)
        }
      }
    }
  } catch {
    /* ignore */
  }
}

  const handleCommentary = (msg: { id: string; at: number; text: string; over?: string; author?: string; game_id: string }): void => {
    if (!liveGameId.value || msg.game_id !== liveGameId.value) return
    commentaryFeed.value.unshift({ id: msg.id, at: msg.at, over: msg.over, text: msg.text, author: msg.author })
    if (commentaryFeed.value.length > 200) commentaryFeed.value.pop()
  }

  let presenceInitHandler: ((p: { game_id: string; members: Array<{ sid: string; role: string; name: string }> }) => void) | null = null
  let commentaryHandler: ((payload: { game_id: string; text: string; at: string }) => void) | null = null

  async function initLive(id: string): Promise<void> {
    liveGameId.value = id
    connectionStatus.value = 'connecting'
    isLive.value = true

    try {
      connectSocket()

      if (typeof joinGameSocket === 'function') {
        joinGameSocket(id)
      } else {
        emitSocket('join', { game_id: id } as any)
      }

      presenceInitHandler = (p) => {
        if (!liveGameId.value || p.game_id !== liveGameId.value) return
        connectionStatus.value = 'connected'
        if (liveGameId.value) void flushQueue(liveGameId.value)
      }

      commentaryHandler = (payload) => {
        if (!liveGameId.value || payload.game_id !== liveGameId.value) return
        commentaryFeed.value.unshift({ id: makeId(), at: Date.parse(payload.at) || Date.now(), text: payload.text })
        if (commentaryFeed.value.length > 200) commentaryFeed.value.pop()
      }

      interUpdateHandler = async (p) => {
        if (!liveGameId.value || !p || !p.game_id || p.game_id !== liveGameId.value) return
        await refreshInterruptions({ force: true })
      }
      interEndedHandler = () => optimisticallyCloseCurrentInterruption()

      on('presence:init', presenceInitHandler)
      on('state:update', handleStateUpdate as any)
      on('score:update', handleScoreUpdate as any)
      on('commentary:new', commentaryHandler)
      on('interruptions:update', interUpdateHandler)
      on('interruption:ended', interEndedHandler)

      void refreshInterruptions()
    } catch (e) {
      connectionStatus.value = 'error'
      console.error('Socket error:', e)
    }
  }

  function stopLive(): void {
    // Remove using the same references, with null guards
    if (presenceInitHandler) {
      off('presence:init', presenceInitHandler!);
      presenceInitHandler = null;
    }
    if (commentaryHandler) {
      off('commentary:new', commentaryHandler!);
      commentaryHandler = null;
    }
    if (interUpdateHandler) { off('interruptions:update', interUpdateHandler); interUpdateHandler = null }
    if (interEndedHandler)  { off('interruption:ended',  interEndedHandler);  interEndedHandler  = null }

    off('state:update', handleStateUpdate as any);
    off('score:update', handleScoreUpdate as any);
    

    disconnectSocket();
    connectionStatus.value = 'disconnected';
    isLive.value = false;
    liveGameId.value = null;
  }
  let interUpdateHandler: ((p: { game_id?: string }) => void) | null = null
  let interEndedHandler: (() => void) | null = null



  let listenersBound = false
  function bindNetworkListeners(): void {
    if (listenersBound) return
    listenersBound = true
    window.addEventListener('online', () => {
      if (liveGameId.value) void flushQueue(liveGameId.value)
    })
  }
  bindNetworkListeners()

  // ========================================================================
  // Offline queue
  // ========================================================================
  function enqueueDelivery(gameId: string, payload: ApiScoreDeliveryRequest): string {
    const item: PendingDelivery = { id: makeId(), gameId, payload, createdAt: Date.now(), tries: 0, status: 'queued' }
    offlineQueue.value.push(item)
    saveQueue()
    return item.id
  }

  async function flushQueue(gameId: string): Promise<void> {
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
        const snap = await apiService.scoreDelivery(gameId, item.payload)
        applySnapshotToGame(coerceSnapshot(snap))

        // Pull authoritative snapshot and update DLS panel if present
        try {
          const full = await apiService.getSnapshot(gameId)
          if (full) {
            applySnapshotToGame(coerceSnapshot(full))
            syncOversLimitFrom(full)
            if ((full as any)?.dls?.method === 'DLS') {
              dlsPanel.value = {
                method: 'DLS',
                par: typeof (full as any).dls.par === 'number' ? (full as any).dls.par : undefined,
                target: typeof (full as any).dls.target === 'number' ? (full as any).dls.target : undefined,
              }

            }
          }
        } catch { /* ignore */ }

        offlineQueue.value = offlineQueue.value.filter((q) => q.id !== item.id)
        saveQueue()
      } catch {
        item.status = 'failed'
        saveQueue()
        break
      }
    }
  } finally {
    isFlushing.value = false
  }
}
        
     
// ========================================================================
// Central scoring helper (ALWAYS uses ids from the latest snapshot)
// ========================================================================
async function postDeliveryAuthoritative(
  gameId: string,
  opts: {
    extra: null | 'wd' | 'nb' | 'b' | 'lb',
    runs_scored?: number,
    runs_off_bat?: number | null,
    is_wicket?: boolean,
    dismissal_type?: string,
    dismissed_player_id?: string | null,
    commentary?: string,
    fielder_id?: string, 
  }
): Promise<any> {
  // Pull ids from server snapshot first; fall back to game / UI selectors only if needed
  const sId  = liveSnapshot.value?.current_striker_id
           ?? currentGame.value?.current_striker_id
           ?? uiState.value.selectedStrikerId
  const nsId = liveSnapshot.value?.current_non_striker_id
           ?? currentGame.value?.current_non_striker_id
           ?? uiState.value.selectedNonStrikerId
  const bow  = liveSnapshot.value?.current_bowler_id
           ?? (currentGame.value as any)?.current_bowler_id
           ?? uiState.value.selectedBowlerId

  if (!sId || !nsId || !bow) {
    throw new Error('Missing striker/non-striker/bowler from snapshot')
  }

  const payload: ApiScoreDeliveryRequest = {
    striker_id: sId,
    non_striker_id: nsId,
    bowler_id: bow,
    extra: opts.extra,
    is_wicket: Boolean(opts.is_wicket),
    dismissal_type: opts.dismissal_type,
    dismissed_player_id: opts.dismissed_player_id ?? undefined,
    commentary: opts.commentary,
  } as ApiScoreDeliveryRequest

  if (opts.fielder_id) (payload as any).fielder_id = opts.fielder_id
  // Encoding rules:
  // - legal ball:      extra=null, runs_scored = off-bat runs
  // - no-ball:         extra='nb',  runs_off_bat = off-bat runs (server adds +1)
  // - byes/leg-byes:   extra='b'|'lb', runs_scored = extras count
  // - wides:           extra='wd', runs_scored = *runs actually RUN* on the wide (0 for a plain wide)
  if (opts.extra === 'nb') {
    payload.runs_off_bat = opts.runs_off_bat ?? opts.runs_scored ?? 0
  } else {
    payload.runs_scored = opts.runs_scored ?? 0
  }

  // Uses offline queue if needed and applies snapshot on success
  return submitDelivery(gameId, payload)
}

  // ========================================================================
  // Actions: Game lifecycle
  // ========================================================================
 async function createNewGame(payload: ApiCreateGameRequest): Promise<any> {
  operationLoading.value.createGame = true
  uiState.value.error = null
  try {
    uiState.value.loading = true

    // ✅ actually create the game (you were missing this)
    const game = await apiService.createGame(payload)
    currentGame.value = coerceGameFromApi(game)
    interruptions.value = ((currentGame.value as any)?.interruptions ?? []).map(normalizeInterruption)

    // Pull a fresh snapshot & wire DLS panel if present
    try {
      const snap = await apiService.getSnapshot(String((game as any).id ?? (game as any).game_id))
      if (snap) {
        applySnapshotToGame(coerceSnapshot(snap))
        
        syncOversLimitFrom(snap)
        
        if ((snap as any)?.dls?.method === 'DLS') {
          dlsPanel.value = {
            method: 'DLS',
            par: typeof (snap as any).dls.par === 'number' ? (snap as any).dls.par : undefined,
            target: typeof (snap as any).dls.target === 'number' ? (snap as any).dls.target : undefined,
          }
        }
      }
    } catch { /* ignore */ }

    return game
  } catch (e) {
    uiState.value.error = getErrorMessage(e)
    throw e
  } finally {
    uiState.value.loading = false
    operationLoading.value.createGame = false
  }
}


  async function loadGame(gameId: string): Promise<any> {
  operationLoading.value.loadGame = true
  uiState.value.error = null
  try {
    uiState.value.loading = true

    const game = await apiService.getGame(gameId)
    currentGame.value = coerceGameFromApi(game)
    interruptions.value = ((currentGame.value as any)?.interruptions ?? []).map(normalizeInterruption)
    // Pull a fresh snapshot & wire DLS panel if present
    try {
      const snap = await apiService.getSnapshot(gameId)
      if (snap) {
        applySnapshotToGame(coerceSnapshot(snap))
        syncOversLimitFrom(snap)
        if ((snap as any)?.dls?.method === 'DLS') {
          dlsPanel.value = {
            method: 'DLS',
            par: typeof (snap as any).dls.par === 'number' ? (snap as any).dls.par : undefined,
            target: typeof (snap as any).dls.target === 'number' ? (snap as any).dls.target : undefined,
          }
        }
      }
      void refreshInterruptions()
    } catch { /* ignore */ }

    return game
  } catch (e) {
    uiState.value.error = getErrorMessage(e)
    throw e
  } finally {
    uiState.value.loading = false
    operationLoading.value.loadGame = false
  }
}

  async function scoreDelivery(gameId: string, delivery: ApiScoreDeliveryRequest): Promise<ApiSnapshot> {
    operationLoading.value.scoreDelivery = true
    uiState.value.error = null
    try {
      uiState.value.loading = true
      const snap = await apiService.scoreDelivery(gameId, delivery)
      applySnapshotToGame(coerceSnapshot(snap))
      syncOversLimitFrom(snap)
      try {
        const full = await apiService.getSnapshot(gameId)
        if (full) applySnapshotToGame(coerceSnapshot(full))
        if ((full as any)?.dls?.method === 'DLS') {
          dlsPanel.value = {
            method: 'DLS',
            par: typeof (full as any).dls.par === 'number' ? (full as any).dls.par : undefined,
            target: typeof (full as any).dls.target === 'number' ? (full as any).dls.target : undefined,
          }
        }

        } catch { /* non-fatal */ }

      return snap
    } catch (e: any) {
      // NEW: if server rejected due to gate (409), pull the latest snapshot so flags arrive
      const status = e?.status ?? e?.response?.status
      if (status === 409) {
        try {
          const full = await apiService.getSnapshot(gameId)
          if (full) applySnapshotToGame(coerceSnapshot(full))
          if ((full as any)?.dls?.method === 'DLS') {
            dlsPanel.value = {
              method: 'DLS',
              par: typeof (full as any).dls.par === 'number' ? (full as any).dls.par : undefined,
              target: typeof (full as any).dls.target === 'number' ? (full as any).dls.target : undefined,
            }
          }

          } catch {/* ignore */}
      }
      uiState.value.error = getErrorMessage(e)
      throw e
    } finally {
      uiState.value.loading = false
      operationLoading.value.scoreDelivery = false
    }
  }

  // inside defineStore, near other actions
async function changeBowlerMidOver(gameId: string, newBowlerId: string, reason: 'injury' | 'other' = 'injury') {
  if (!gameId) throw new Error('Missing gameId')
  setScoringDisabled(true)
  try {
    const svc: any = apiService as any
    if (typeof svc.changeBowlerMidOver !== 'function') {
      // thin fallback if your client hasn't got it typed
      await fetch(`/games/${gameId}/bowling/mid-over-change`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bowler_id: newBowlerId, reason }),
      }).then(r => { if (!r.ok) throw r })
    } else {
      await svc.changeBowlerMidOver(gameId, newBowlerId, reason)
    }

    // Pull authoritative snapshot so gates/cards/bowler sync
    const full = await apiService.getSnapshot(gameId)
    if (full) applySnapshotToGame(coerceSnapshot(full))
  } finally {
    setScoringDisabled(false)
  }
}

  async function startNextInnings(gameId: string): Promise<UiSnapshot | undefined> {
    operationLoading.value.startInnings = true
    uiState.value.error = null
    try {
      uiState.value.loading = true
      const svc: any = apiService as any
      if (typeof svc.startNextInnings !== 'function') {
        throw new Error('Start next innings is not implemented on the server yet.')
      }
      const snap = await svc.startNextInnings(gameId)
      const coerced = coerceSnapshot(snap)
      applySnapshotToGame(coerced)
      syncOversLimitFrom(snap)
      return coerced
    } catch (e) {
      uiState.value.error = getErrorMessage(e)
      throw e
    } finally {
      uiState.value.loading = false
      operationLoading.value.startInnings = false
    }
  }

  async function submitDelivery(gameId: string, payload: ApiScoreDeliveryRequest): Promise<any> {
    const onlineAndLive = connectionStatus.value === 'connected'
    if (!onlineAndLive && offlineEnabled.value) {
      enqueueDelivery(gameId, payload)
      return { queued: true }
    }
    return scoreDelivery(gameId, payload)
  }

  // ========================================================================
  // Selection & convenience
  // ========================================================================
  const selectedStriker = computed<Player | null>(() => {
    const id = uiState.value.selectedStrikerId
    const team = battingTeam.value
    return id && team ? (team.players.find((p) => p.id === id) ?? null) : null
  })
  const selectedNonStriker = computed<Player | null>(() => {
    const id = uiState.value.selectedNonStrikerId
    const team = battingTeam.value
    return id && team ? (team.players.find((p) => p.id === id) ?? null) : null
  })
  const selectedBowler = computed<Player | null>(() => {
    const id = uiState.value.selectedBowlerId
    const team = bowlingTeam.value
    return id && team ? (team.players.find((p) => p.id === id) ?? null) : null
  })

   const canScore = computed<boolean>(() => {
    const g  = currentGame.value
    const s  = state.value
    const ui = uiState.value

    const statusOk =
      !!g && ['in_progress', 'live', 'started'].includes(String(g.status || ''))

    const haveBatters =
      !!ui.selectedStrikerId &&
      !!ui.selectedNonStrikerId &&
      ui.selectedStrikerId !== ui.selectedNonStrikerId

    const serverHasBowler = !!s.current_bowler_id
    const bowlerMatches =
      !ui.selectedBowlerId ? false : ui.selectedBowlerId === s.current_bowler_id

    const gatesClear =
      !needsNewBatter.value &&
      !needsNewOver.value &&
      !ui.loading &&
      !ui.scoringDisabled

    return Boolean(statusOk && haveBatters && serverHasBowler && bowlerMatches && gatesClear)
  })


  
    console.table({
      hasGame: !!currentGame.value,
      inProgress: currentGame.value?.status === 'in_progress',
      strikerSet: !!uiState.value.selectedStrikerId,
      nonStrikerSet: !!uiState.value.selectedNonStrikerId,
      bowlerSet: !!uiState.value.selectedBowlerId,
      differentBatters: uiState.value.selectedStrikerId !== uiState.value.selectedNonStrikerId,
      notLoading: !uiState.value.loading,
      notDisabled: !uiState.value.scoringDisabled,
      needsNewBatter: needsNewBatter.value,
      needsNewOver: needsNewOver.value,
    })



  function setSelectedStriker(playerId: string | null): void { uiState.value.selectedStrikerId = playerId }
  function setSelectedNonStriker(playerId: string | null): void { uiState.value.selectedNonStrikerId = playerId }
  function setSelectedBowler(playerId: string | null): void { uiState.value.selectedBowlerId = playerId }
  function setActiveScorecardTab(tab: 'batting' | 'bowling'): void { uiState.value.activeScorecardTab = tab }
  function setScoringDisabled(disabled: boolean): void { uiState.value.scoringDisabled = disabled }

  
  

  async function scoreRuns(gameId: string, runs: number): Promise<any> {
    // legal off-bat runs; server will rotate on odd runs
    return postDeliveryAuthoritative(gameId, { extra: null, runs_scored: runs })
  }


  async function scoreExtra(gameId: string, code: 'wd' | 'nb' | 'b' | 'lb', runs = 1): Promise<any> {
  if (code === 'nb') {
    // off-bat runs on a no-ball
    return postDeliveryAuthoritative(gameId, { extra: 'nb', runs_off_bat: runs })
  }
  if (code === 'wd') {
    // UI passes total wides (incl. the automatic 1). Convert to "runs actually run".
    const ran = Math.max(0, runs - 1)
    return postDeliveryAuthoritative(gameId, { extra: 'wd', runs_scored: ran })
  }
  // byes / leg-byes: send extras count as-is
  return postDeliveryAuthoritative(gameId, { extra: code, runs_scored: runs })
}




  async function replaceBatter(newBatterId: string): Promise<void> {
    if (!liveGameId.value) throw new Error('No live game to update');
    try {
      // Disable scoring while we perform the gate
      setScoringDisabled(true);
      const snap = await apiService.replaceBatter(liveGameId.value, newBatterId);
      applySnapshotToGame(coerceSnapshot(snap));
      // (Optional) fetch full snapshot for card consistency
      try {
        const full = await apiService.getSnapshot(liveGameId.value);
        if (full) applySnapshotToGame(coerceSnapshot(full));
        if ((full as any)?.dls?.method === 'DLS') {
          dlsPanel.value = {
            method: 'DLS',
            par: typeof (full as any).dls.par === 'number' ? (full as any).dls.par : undefined,
            target: typeof (full as any).dls.target === 'number' ? (full as any).dls.target : undefined,
          }
        }

      } catch { /* non-fatal */ }
    } finally {
      setScoringDisabled(false);
    }
  }

  async function startNewOver(bowlerId: string): Promise<void> {
    if (!liveGameId.value) throw new Error('No live game to update');
    try {
      setScoringDisabled(true);

      // 1) tell server to start the over (no snapshot merging here)
      await apiService.startOver(liveGameId.value, bowlerId);

      // 2) immediately fetch a fresh snapshot (authoritative)
      const full = await apiService.getSnapshot(liveGameId.value);
      
      if (full) applySnapshotToGame(coerceSnapshot(full));
      uiState.value.selectedBowlerId = bowlerId
      
      if ((full as any)?.dls?.method === 'DLS') {
        dlsPanel.value = {
          method: 'DLS',
          par: typeof (full as any).dls.par === 'number' ? (full as any).dls.par : undefined,
          target: typeof (full as any).dls.target === 'number' ? (full as any).dls.target : undefined,
        }
      }

    } finally {
      setScoringDisabled(false);
    }
  }

  /**
 * Reduce overs mid-match (e.g., weather). Server persists & emits snapshot.
 * Also refreshes full snapshot (which may include DLS panel).
 */
async function reduceOvers(gameId: string, oversLimit: number): Promise<void> {
  if (!gameId) throw new Error('Missing gameId')
  setScoringDisabled(true)
  try {
    const svc: any = apiService as any
    if (typeof svc.setOversLimit === 'function') {
      await svc.setOversLimit(gameId, oversLimit)     // POST /games/{id}/overs-limit
    } else {
      // Optional ultra-thin fallback if your apiService doesn’t have it yet:
      await fetch(`/games/${gameId}/overs-limit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ overs_limit: oversLimit })
      }).then(r => { if (!r.ok) throw r })
    }

    // Pull authoritative snapshot (may include dls panel)
    const full = await apiService.getSnapshot(gameId)
    if (full) {
      applySnapshotToGame(coerceSnapshot(full))
      syncOversLimitFrom(full)
      if ((full as any)?.dls?.method === 'DLS') {
        dlsPanel.value = {
          method: 'DLS',
          par: typeof (full as any).dls.par === 'number' ? (full as any).dls.par : undefined,
          target: typeof (full as any).dls.target === 'number' ? (full as any).dls.target : undefined,
        }
      }
    }
  } finally {
    setScoringDisabled(false)
  }
}

/**
 * Compute revised target per DLS. Typically called between innings or after a reduction.
 * Sets currentGame.target so your target UI updates immediately.
 */
async function dlsRevisedTarget(
  gameId: string,
  kind: 'odi' | 't20',
  innings: 1 | 2,
  max_overs?: number
): Promise<{ R1_total: number; R2_total: number; S1: number; target: number }> {
  const svc: any = apiService as any
  let res: any
  if (typeof svc.dlsRevisedTarget === 'function') {
    res = await svc.dlsRevisedTarget(gameId, { kind, innings, max_overs })
  } else {
    res = await fetch(`/games/${gameId}/dls/revised-target`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind, innings, max_overs })
    }).then(r => r.json())
  }

  // Update UI target and DLS panel
  if (currentGame.value) currentGame.value.target = Number(res?.target ?? currentGame.value.target)
  dlsPanel.value = { method: 'DLS', target: Number(res?.target) }

  return res
}

/**
 * Compute live par (second innings). Good for “are we ahead/behind?” panels.
 */
async function dlsParNow(
  gameId: string,
  kind: 'odi' | 't20',
  innings: 1 | 2,
  max_overs?: number
): Promise<{ R1_total: number; R2_used: number; S1: number; par: number; ahead_by: number }> {
  const svc: any = apiService as any
  let res: any
  if (typeof svc.dlsParNow === 'function') {
    res = await svc.dlsParNow(gameId, { kind, innings, max_overs })
  } else {
    res = await fetch(`/games/${gameId}/dls/par`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind, innings, max_overs })
    }).then(r => r.json())
  }

  // Update DLS panel in the store so UI shows it live
  dlsPanel.value = { method: 'DLS', par: Number(res?.par) }
  return res
}

// ⬇️ ADD inside the same defineStore body (not in the return yet)

async function fetchDlsPreview(gameId: string, G50 = 245) {
  dlsPreview.value = await getDlsPreview(gameId, G50)
  return dlsPreview.value
}

async function applyDls(gameId: string, G50 = 245) {
  const res = await postDlsApply(gameId, G50)
  dlsPreview.value = res as any
  dlsApplied.value = Boolean((res as any)?.applied)

  // Optional: refresh game & snapshot so targets/DLS panel propagate
  await loadGame(gameId)
  try {
    const full = await apiService.getSnapshot(gameId)
    if (full) applySnapshotToGame(coerceSnapshot(full))
  } catch { /* ignore */ }

  return res
}

/** If you want the innings-specific reducer your snippet had: */
async function reduceOversForInnings(gameId: string, innings: 1 | 2, newOvers: number) {
  const res = await patchReduceOvers(gameId, innings, newOvers)
  await loadGame(gameId)
  try {
    const full = await apiService.getSnapshot(gameId)
    if (full) applySnapshotToGame(coerceSnapshot(full))
  } catch { /* ignore */ }
  return res
}

  async function scoreWicket(
  gameId: string,
  dismissal_type: string,
  dismissed_player_id?: string | null,
  commentary?: string,
  fielderId?: string
): Promise<any> {
  const needsFielder = ['caught', 'run_out', 'stumped'].includes(String(dismissal_type))

  return postDeliveryAuthoritative(gameId, {
    extra: null,
    is_wicket: true,
    dismissal_type,
    dismissed_player_id: dismissed_player_id ?? uiState.value.selectedStrikerId,
    commentary,
    ...(needsFielder && fielderId ? { fielder_id: fielderId } as any : {})
  })
}



  function clearError(): void { uiState.value.error = null }
  function clearGame(): void {
    currentGame.value = null
    uiState.value.selectedStrikerId = null
    uiState.value.selectedNonStrikerId = null
    uiState.value.selectedBowlerId = null
    uiState.value.scoringDisabled = false
    liveSnapshot.value = null
    isLive.value = false
    liveGameId.value = null
    commentaryFeed.value = []

    // ⬇️ ADD: reset DLS bits
    dlsPanel.value = null
    dlsPreview.value = null
    dlsApplied.value = false
  }

  function mergeGamePatch(patch: Partial<GameState>): void {
    if (!currentGame.value) return
    currentGame.value = { ...currentGame.value, ...patch }
  }

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

    // Shaped scorecards
    battingRows,          // keep old for compatibility
    bowlingRows,          // keep old for compatibility
    battingRowsXI,        // NEW
    bowlingRowsXI,        // NEW
    battingXI,            // optional export if you want
    bowlingXI, 
    extrasBreakdown,
    battingRosterXI,
    bowlingRosterXI,
    fieldingSubs,
    fielderRosterAll,
    fieldingBench,

    // Live
    isLive,
    liveGameId,
    connectionStatus,
    lastLiveAt,
    liveSnapshot,
    initLive,
    stopLive,
    
    // Gate flags for UI
    canScore,
    needsNewBatter,
    needsNewOver,
    // Commentary
    commentaryFeed,

    // Offline
    offlineEnabled,
    offlineQueue,
    isFlushing,
    enqueueDelivery,
    flushQueue,
    submitDelivery,

    // Convenience for views
    state,
    bowlingTeamPlayers,
    score,
    currentInningsDeliveries,
    bowlingStatsByPlayer,

    // Actions
    createNewGame,
    loadGame,
    scoreDelivery,
    startNextInnings,
    changeBowlerMidOver,
    replaceBatter,
    startNewOver,

    // DLS panel
    dlsPanel,

    // State
    dlsPreview,
    dlsApplied,
    // DLS getters
    dls,
    isChase,
    dlsPar,
    dlsTarget,
    dlsAheadBy,
    dlsKind,
    // DLS actions
    fetchDlsPreview,
    applyDls,
    // If you kept the innings-specific version:
    reduceOversForInnings,

    // Interruptions
    interruptions,
    interruptionsLoading,
    interruptionsError,
    currentInterruption,
    hasOpenInterruption,
    refreshInterruptions,
    startInterruption,
    stopInterruption: stopInterruptionAction,
    optimisticallyCloseCurrentInterruption,

    // DLS actions
    reduceOvers,
    dlsRevisedTarget,
    dlsParNow,

    // Selections
    setSelectedStriker,
    setSelectedNonStriker,
    setSelectedBowler,
    setActiveScorecardTab,
    setScoringDisabled,

    // Utils
    scoreRuns,
    scoreExtra,
    scoreWicket,
    clearError,
    clearGame,
    mergeGamePatch,
  }
})

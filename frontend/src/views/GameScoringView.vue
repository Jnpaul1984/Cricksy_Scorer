<script setup lang="ts">
/* --- Vue & Router --- */
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/* --- Stores --- */
import { useGameStore } from '@/stores/gameStore'
import { storeToRefs } from 'pinia'

/* --- UI Components --- */
import DeliveryTable from '@/components/DeliveryTable.vue'
import BattingCard from '@/components/BattingCard.vue'
import BowlingCard from '@/components/BowlingCard.vue'
import PresenceBar from '@/components/PresenceBar.vue'
import ScoreboardWidget from '@/components/ScoreboardWidget.vue'

const isDev = import.meta.env.DEV
const normId = (v: unknown) => String(v ?? '').trim()
// ================== Local domain types (narrow) ==================
type UUID = string
type Player = { id: UUID; name: string }
type Team = { name: string; players: Player[]; playing_xi?: UUID[] }
type BatCardEntry = {
  player_id: UUID; player_name: string; runs: number; balls_faced: number;
  fours: number; sixes: number; strike_rate: number; how_out?: string; is_out: boolean
}
type BowlCardEntry = {
  player_id: UUID; player_name: string; overs_bowled: number; maidens: number;
  runs_conceded: number; wickets_taken: number; economy: number
}
type DeliveryRowForTable = {
  over_number: number; ball_number: number; runs_scored: number;
  striker_id: UUID; non_striker_id: UUID; bowler_id: UUID;
  extra?: 'wd' | 'nb' | 'b' | 'lb'; is_wicket?: boolean; commentary?: string;
  dismissed_player_id?: UUID | null; at_utc?: string
  extra_runs?: number
  runs_off_bat?: number 
}

// ================== Single-panel state ==================
type ExtraOpt = 'none' | 'nb' | 'wd' | 'b' | 'lb'

const shotAngle = ref<number | null>(null)
// --- Fielder (XI + subs) for wicket events ---
const selectedFielderId = ref<UUID>('' as UUID)
const inningsStartIso = ref<string | null>(null)
// Does this dismissal type require a fielder?
const needsFielder = computed<boolean>(() => {
  const t = (dismissal.value || '').toLowerCase()
  return t === 'caught' || t === 'run_out' || t === 'stumped'
})

// Mark which ids belong to the XI so we can label subs in the dropdown
const bowlingXIIds = computed<Set<UUID>>(() => new Set(bowlingRosterXI.value.map(p => p.id)))

// Reset fielder when wicket toggled off / dismissal changes to a non-fielder type
watch(isWicket, (on) => {
  if (!on) { dismissal.value = null; selectedFielderId.value = '' as UUID }
})
watch(dismissal, (t) => {
  if (!needsFielder.value) selectedFielderId.value = '' as UUID
})
watch(extra, (t) => {
  if (t === 'wd') { extraRuns.value = 1; offBat.value = 0 }
  else if (t === 'b' || t === 'lb') { extraRuns.value = 0; offBat.value = 0 }
  else if (t === 'none') { offBat.value = 0 }
  if (t !== 'none' && t !== 'nb') shotAngle.value = null
})


const route = useRoute()
const router = useRouter()
const gameStore = useGameStore()

// Reactive refs from the store
const { canScore, liveSnapshot } = storeToRefs(gameStore)
const { needsNewBatter, needsNewOver } = storeToRefs(gameStore)
const { extrasBreakdown } = storeToRefs(gameStore)
const { dlsKind } = storeToRefs(gameStore)
const { runsRequired, targetSafe, requiredRunRate, ballsBowledTotal } = storeToRefs(gameStore)
// Allow a manual start even if the server gate didn't flip yet
const canForceStartInnings = computed(() =>
  Boolean(gameId.value) &&
  !isStartingInnings.value &&
  pendingCount.value === 0
)

function forceStartInnings(): void {
  if (!canForceStartInnings.value) return

  // If the normal conditions aren't met, warn before proceeding
  const safeToStart = needsNewInningsLive.value || allOut.value || oversExhausted.value
  if (!safeToStart) {
    const ok = window.confirm(
      'It looks like the current innings may not be finished yet.\n\nStart the next innings anyway?'
    )
    if (!ok) return
  }

  // Reuse the same picker modal for openers & (optional) opening bowler
  openStartInnings()
}

// Current gameId (param or ?id=)
const gameId = computed<string>(() => (route.params.gameId as string) || (route.query.id as string) || '')

const canSubmitSimple = computed(() => {
  const firstBall = Number(currentOverBalls.value || 0) === 0
  if (!gameId.value || needsNewBatterLive.value) return false
  // Allow submit if it's the first ball and a bowler is chosen
  if (needsNewOverLive.value && !(firstBall && !!selectedBowler.value)) return false
  if (!selectedStriker.value || !selectedNonStriker.value || !selectedBowler.value) return false
  if (needsNewInningsLive.value) return false
  if (isStartingInnings.value) return false
  // If it's a wicket that needs a fielder, require one
  if (isWicket.value && needsFielder.value && !selectedFielderId.value) return false

  if (extra.value === 'nb') return offBat.value >= 0
  if (extra.value === 'wd') return extraRuns.value >= 1
  if (extra.value === 'b' || extra.value === 'lb') return extraRuns.value >= 0
  return offBat.value >= 0 // legal
})


async function submitSimple() {
  const firstBall = Number(currentOverBalls.value || 0) === 0
  if (needsNewOverLive.value && !(firstBall && !!selectedBowler.value)) {
    openStartOver(); onError('Start the next over first'); return
  }
  if (needsNewBatterLive.value) { openSelectBatter(); onError('Select the next batter first'); return }

  try {
    const anyStore: any = gameStore as any
    const unifiedPossible = typeof anyStore.scoreDelivery === 'function'

    if (unifiedPossible) {
      const payload: Record<string, unknown> = {}

      if (extra.value === 'wd') {
        payload.extra_type = 'wd'
        payload.extra_runs = extraRuns.value
      } else if (extra.value === 'nb') {
        payload.extra_type = 'nb'
        payload.runs_off_bat = offBat.value
        payload.shot_angle_deg = shotAngle.value ?? null
      } else if (extra.value === 'b' || extra.value === 'lb') {
        payload.extra_type = extra.value
        payload.extra_runs = extraRuns.value
      } else {
        payload.runs_off_bat = offBat.value
        payload.shot_angle_deg = shotAngle.value ?? null
      }

      if (isWicket.value) {
        payload.is_wicket = true
        payload.dismissal_type = (dismissal.value || 'bowled')
        payload.dismissed_player_name = (dismissedName.value || null)
        payload.fielder_id = needsFielder.value ? (selectedFielderId.value || null) : null
      }

      await anyStore.scoreDelivery(gameId.value, payload)
    } else {
      if (isWicket.value && extra.value === 'none') {
        await gameStore.scoreWicket(
          gameId.value,
          (dismissal.value || 'bowled'),
          undefined,
          undefined,
          (needsFielder.value ? (selectedFielderId.value || undefined) : undefined)
        )
      } else if (!isWicket.value && extra.value === 'nb') {
        await gameStore.scoreExtra(gameId.value, 'nb', offBat.value, shotAngle.value ?? null)
      } else if (!isWicket.value && extra.value === 'wd') {
        await gameStore.scoreExtra(gameId.value, 'wd', extraRuns.value)
      } else if (!isWicket.value && (extra.value === 'b' || extra.value === 'lb')) {
        await gameStore.scoreExtra(gameId.value, extra.value, extraRuns.value)
      } else if (!isWicket.value && extra.value === 'none') {
        await gameStore.scoreRuns(gameId.value, offBat.value, shotAngle.value ?? null)
      } else {
        const res = await fetch(`${apiBase}/games/${encodeURIComponent(gameId.value)}/deliveries`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            extra_type: extra.value !== 'none' ? extra.value : null,
            extra_runs: extra.value === 'wd'
              ? extraRuns.value
              : (extra.value === 'b' || extra.value === 'lb')
                ? extraRuns.value
                : undefined,
            runs_off_bat: extra.value === 'nb'
              ? offBat.value
              : extra.value === 'none'
                ? offBat.value
                : undefined,
            is_wicket: true,
            dismissal_type: (dismissal.value || 'bowled'),
            dismissed_player_name: (dismissedName.value || null),
            shot_angle_deg: (extra.value === 'none' || extra.value === 'nb') ? (shotAngle.value ?? null) : null,
            fielder_id: needsFielder.value ? (selectedFielderId.value || null) : null,
          }),
        })
        if (!res.ok) throw new Error(await res.text())
      }
    }

    extra.value = 'none'
    offBat.value = 0
    extraRuns.value = 1
    isWicket.value = false
    dismissal.value = null
    dismissedName.value = null
    selectedFielderId.value = '' as UUID
    shotAngle.value = null
    onScored()

    await nextTick()
    maybeRotateFromLastDelivery()
  } catch (e: any) {
    onError(e?.message || 'Scoring failed')
  }
}

// --- Delete last delivery ------------------------------
const deletingLast = ref(false)

const lastDelivery = computed<any | null>(() =>
  // Prefer live snapshot (if your store fills it), else fall back to the game object
  (gameStore as any)?.state?.last_delivery ??
  (gameStore.currentGame as any)?.last_delivery ??
  (rawDeliveries.value.length ? rawDeliveries.value[rawDeliveries.value.length - 1] : null)
)

// Block when: there is no ball yet, an innings gate is up, or you still have queued actions
const canDeleteLast = computed<boolean>(() =>
  Boolean(lastDelivery.value) &&
  !needsNewInningsLive.value &&
  !isStartingInnings.value &&        // â† add this guard
  pendingCount.value === 0
)


async function deleteLastDelivery(): Promise<void> {
  const id = gameId.value
  if (!id || !canDeleteLast.value || deletingLast.value) return
  deletingLast.value = true
  try {
    const anyStore: any = gameStore as any
    if (typeof anyStore.deleteLastDelivery === 'function') {
      await anyStore.deleteLastDelivery(id)
    } else if (typeof anyStore.undoLastDelivery === 'function') {
      await anyStore.undoLastDelivery(id)
    } else {
      await fetch(`${apiBase}/games/${encodeURIComponent(id)}/undo-last`, { method: 'POST' })
    }
    showToast('Last delivery deleted', 'success')

    // Ensure local UI refreshes even if the socket message arrives slowly
    await gameStore.loadGame(id)
  } catch (e:any) {
    onError(e?.message || 'Failed to delete last delivery')
  } finally {
    deletingLast.value = false
  }
}

// --- DLS panel state ---
const G50 = ref(245)
const dls = computed(() => gameStore.dlsPreview)
const canShowDls = computed(() => Boolean(gameId.value) && !!(gameStore.currentGame as any)?.dls_enabled)
const loadingDls = ref(false)
const applyingDls = ref(false)

async function refreshDls() {
  if (!gameId.value) return
  loadingDls.value = true
  try {
    await gameStore.fetchDlsPreview(gameId.value, G50.value)
  } catch (e: any) {
    onError(e?.message || 'DLS preview failed')
  } finally {
    loadingDls.value = false
  }
}

async function applyDls() {
  if (!gameId.value) return
  applyingDls.value = true
  try {
    await gameStore.applyDls(gameId.value, G50.value)
    onScored()
  } catch (e:any) {
    onError(e?.message || 'Apply DLS failed')
  } finally {
    applyingDls.value = false
  }
}

// --- Reduce Overs & Live Par ---
const oversLimit = computed<number>(() => Number((gameStore.currentGame as any)?.overs_limit ?? 0))
const currentInnings = computed<1 | 2>(() => Number((gameStore.currentGame as any)?.current_inning ?? 1) as 1 | 2)
// Balls & overs remaining in the chase (defensive if not a chase or no limit)
const ballsRemaining = computed<number>(() => {
  const limit = oversLimit.value ? Number(oversLimit.value) * 6 : 0
  return Math.max(0, limit - Number(ballsBowledTotal.value || 0))
})
const oversRemainingDisplay = computed<string>(() => {
  const balls = ballsRemaining.value
  const ov = Math.floor(balls / 6)
  const rem = balls % 6
  return `${ov}.${rem}`
})

const reduceScope = ref<'match' | 'innings'>('match')
const reduceInnings = ref<1 | 2>(currentInnings.value)
const oversNew = ref<number | null>(null)
const reducingOvers = ref(false)
const computingPar = ref(false)
// --- Optional "Fielding subs" management card ---
const showSubsCard = ref<boolean>(false)
const SUBS_CARD_KEY = 'cricksy.ui.showSubsCard'

onMounted(() => {
  try {
    const saved = localStorage.getItem(SUBS_CARD_KEY)
    if (saved != null) showSubsCard.value = saved === '1'
  } catch {}
})
watch(showSubsCard, (v) => {
  try { localStorage.setItem(SUBS_CARD_KEY, v ? '1' : '0') } catch {}
})

const canReduce = computed(() => oversNew.value != null && oversNew.value! > 0)

async function doReduceOvers() {
  if (!gameId.value || !canReduce.value) return
  reducingOvers.value = true
  try {
    if (reduceScope.value === 'innings') {
      await gameStore.reduceOversForInnings(gameId.value, reduceInnings.value, oversNew.value as number)
    } else {
      await gameStore.reduceOvers(gameId.value, oversNew.value as number)
    }
    showToast('Overs limit updated', 'success')
    try { await refreshDls() } catch {}
  } catch (e:any) {
    onError(e?.message || 'Failed to reduce overs')
  } finally {
    reducingOvers.value = false
  }
}

async function updateParNow() {
  if (!gameId.value) return
  computingPar.value = true
  try {
    await gameStore.dlsParNow(gameId.value, dlsKind.value, currentInnings.value)
    showToast('Par updated', 'success')
  } catch (e:any) {
    onError(e?.message || 'Par calc failed')
  } finally {
    computingPar.value = false
  }
}

// prime input with current limit when game loads
watch(() => oversLimit.value, (v) => { if (v && !oversNew.value) oversNew.value = v })

// --- Match controls: Weather + Reduce Overs quick actions ---
const weatherDlg = ref<HTMLDialogElement | null>(null)
const weatherNote = ref<string>('')

function openWeather() { weatherDlg.value?.showModal() }
function closeWeather() { weatherDlg.value?.close() }

const apiBase =
  (import.meta as any).env?.VITE_API_BASE?.replace(/\/$/, '') ||
  (import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin).replace(/\/$/, '')

// Store is the single writer; no manual refresh calls here.
async function startWeatherDelay() {
  const id = gameId.value
  if (!id) return
  try {
    await gameStore.startInterruption('weather', weatherNote.value || undefined)
    showToast('Weather delay started', 'success')
    closeWeather()
    await nextTick()
  } catch (e:any) {
    onError(e?.message || 'Failed to start interruption')
  }
}

async function resumeAfterWeather() {
  const id = gameId.value
  if (!id) return
  try {
    await gameStore.stopInterruption('weather')
    showToast('Play resumed', 'success')
    closeWeather()
    await nextTick()
  } catch (e:any) {
    onError(e?.message || 'Failed to resume')
  }
}

// Smooth jump to the existing "Reduce Overs" card
const reduceOversCardRef = ref<HTMLElement | null>(null)
function jumpToReduceOvers() {
  reduceOversCardRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// ================== XI LOCAL STORAGE ==================
type XI = { team_a_xi: UUID[]; team_b_xi: UUID[] }
const XI_KEY = (id: string) => `cricksy.xi.${id}`
const xiA = ref<Set<UUID> | null>(null)
const xiB = ref<Set<UUID> | null>(null)
const xiLoaded = ref<boolean>(false)

function loadXIForGame(id: string): void {
  xiA.value = xiB.value = null
  xiLoaded.value = false
  try {
    const raw = localStorage.getItem(XI_KEY(id))
    if (raw) {
      const parsed = JSON.parse(raw) as XI
      if (Array.isArray(parsed.team_a_xi)) xiA.value = new Set(parsed.team_a_xi)
      if (Array.isArray(parsed.team_b_xi)) xiB.value = new Set(parsed.team_b_xi)
    }
  } catch { /* ignore */ }
  xiLoaded.value = true
}

// ================== SELECTION STATE ==================
const selectedStriker = computed<string>({
  get: () => (gameStore.uiState.selectedStrikerId || '') as string,
  set: (v) => gameStore.setSelectedStriker(normId(v) || null),
})
const selectedNonStriker = computed<string>({
  get: () => (gameStore.uiState.selectedNonStrikerId || '') as string,
  set: (v) => gameStore.setSelectedNonStriker(normId(v) || null),
})
const selectedBowler = computed<string>({
  get: () => (gameStore.uiState.selectedBowlerId || '') as string,
  set: (v) => gameStore.setSelectedBowler(normId(v) || null),
})


// ================== CONNECTION / OFFLINE QUEUE ==================
const liveReady = computed<boolean>(() => gameStore.connectionStatus === 'connected')
const pendingForThisGame = computed(() => gameStore.offlineQueue.filter(q => q.gameId === gameId.value && q.status !== 'flushing'))
const pendingCount = computed<number>(() => pendingForThisGame.value.length)


// ================== ROSTERS (FILTERED BY XI) ==================


// Names for status text
const selectedStrikerName = computed<string>(() => battingPlayers.value.find((p) => p.id === selectedStriker.value)?.name || '')
const selectedNonStrikerName = computed<string>(() => battingPlayers.value.find((p) => p.id === selectedNonStriker.value)?.name || '')
const selectedBowlerName = computed<string>(() => bowlingPlayers.value.find((p) => p.id === selectedBowler.value)?.name || '')

// Dismissed dropdown: limit to current batters to avoid ambiguity
const dismissedOptions = computed<Player[]>(() => {
  const list = battingPlayers.value
  const s = list.find(p => p.id === selectedStriker.value)
  const ns = list.find(p => p.id === selectedNonStriker.value)
  const out: Player[] = []
  if (s) out.push(s)
  if (ns && (!s || ns.id !== s.id)) out.push(ns)
  return out
})

watch([isWicket, selectedStriker, selectedNonStriker], () => {
  if (isWicket.value && !dismissedName.value && dismissedOptions.value.length > 0) {
    dismissedName.value = dismissedOptions.value[0].name
  }
})
const {
  battingRosterXI,
  bowlingRosterXI,
  battingRowsXI,       // NEW: stat rows for current batting XI
  bowlingRowsXI,       // NEW: stat rows for current bowling XI
  fieldingSubs,
  fielderRosterAll,
} = storeToRefs(gameStore)

// selectors:
const battingPlayers = computed(() => battingRosterXI.value)
const bowlingPlayers = computed(() => bowlingRosterXI.value)
const fielderOptions = computed(() => [
  ...bowlingRosterXI.value,     // XI
  ...fieldingSubs.value,        // subs
])

const nextBattingXI = computed<Player[]>(() =>
  needsNewInningsLive.value ? bowlingRosterXI.value : battingRosterXI.value
)
const nextBowlingXI = computed<Player[]>(() =>
  needsNewInningsLive.value ? battingRosterXI.value : bowlingRosterXI.value
)
// ================== SCORECARDS (from store) ==================
// Preferred order from the store if available
const storeBattingOrderIds = computed<string[] | null>(() => {
  const ids = (stateAny.value?.batting_order_ids as string[] | undefined) ||
              ((gameStore.currentGame as any)?.batting_order_ids as string[] | undefined)
  return Array.isArray(ids) ? ids.map(normId) : null
})

// Fallback: infer order from first appearance **in this innings** only
const battingAppearanceOrder = computed<string[]>(() => {
  if (storeBattingOrderIds.value && storeBattingOrderIds.value.length) return storeBattingOrderIds.value
  const seen = new Set<string>()
  const order: string[] = []
  for (const d of deliveriesThisInnings.value) {
    for (const id of [d.striker_id, d.non_striker_id]) {
      const nid = normId(id)
      if (nid && !seen.has(nid)) { seen.add(nid); order.push(nid) }
    }
  }
  return order
})

const battingEntries = computed(() => {
  const rows = (battingRowsXI.value || []).map((r: any) => ({
    player_id: r.id,
    player_name: String(r.name),
    runs: Number(r.runs),
    balls_faced: Number(r.balls),
    fours: Number(r.fours),
    sixes: Number(r.sixes),
    strike_rate: Number(r.sr),
    how_out: r.howOut,
    is_out: Boolean(r.isOut),
    // optional: if your row has a batting position/index, keep it for tie-breaks
    _pos: typeof r.pos === 'number' ? r.pos : undefined
  }))

  const order = battingAppearanceOrder.value
  const rank = new Map(order.map((id, i) => [id, i]))

  rows.sort((a, b) => {
    const ra = rank.get(normId(a.player_id)) ?? 9999
    const rb = rank.get(normId(b.player_id)) ?? 9999
    if (ra !== rb) return ra - rb
    // tie-breaker: explicit position if present
    if (a._pos != null && b._pos != null) return a._pos - b._pos
    return String(a.player_name).localeCompare(String(b.player_name))
  })

  return rows as unknown as BatCardEntry[]
})


const bowlingEntries = computed(() =>
  (bowlingRowsXI.value || []).map((r: any) => {
    const pid = String(r.id)
    const derived = bowlingDerivedByPlayer.value[pid]
    const balls = derived ? derived.balls : 0
    const runsToBowler = derived ? derived.runs : Number(r.runs ?? r.runs_conceded ?? 0)
    const maidens = derived ? derived.maidens : Number(r.maidens ?? 0)
    const oversTxt = balls ? oversDisplayFromBalls(balls) : String(r.overs ?? r.overs_bowled ?? '0.0')
    const econTxt = balls ? econ(runsToBowler, balls) : (typeof r.econ === 'number' ? r.econ.toFixed(2) : (Number(r.econ || 0)).toFixed(2))

    return {
      player_id: pid,
      player_name: String(r.name),
      overs_bowled: oversTxt,
      maidens,
      runs_conceded: runsToBowler,
      wickets_taken: Number(r.wkts ?? r.wickets_taken ?? 0),
      economy: Number(econTxt),
    }
  })
)



// ================== Deliveries (DEDUPE) ==================
// normalize over/ball before keying
function obOf(d:any){
  const overLike = d.over_number ?? d.over
  const ballLike = d.ball_number ?? d.ball
  if (typeof ballLike === 'number' && typeof overLike === 'number') {
    return { over: Math.max(0, Math.floor(overLike)), ball: Math.max(0, ballLike) }
  }
  if (typeof overLike === 'string') {
    const [o,b] = overLike.split('.')
    return { over: Number(o)||0, ball: Number(b)||0 }
  }
  if (typeof overLike === 'number') {
    const whole = Math.floor(overLike)
    const tenth = Math.round((overLike - whole) * 10)
    return { over: whole, ball: Math.max(0, Math.min(5, tenth)) }
  }
  return { over: 0, ball: 0 }
}

// âœ… stable identity: innings + over + ball only
function makeKey(d:any): string {
  const inn = Number(d.innings ?? d.inning ?? d.inning_no ?? d.innings_no ?? d.inning_number ?? 0)
  const { over, ball } = obOf(d)
  return `${inn}:${over}:${ball}`
}


const rawDeliveries = computed<any[]>(() => {
  const g = gameStore.currentGame as any
  return Array.isArray(g?.deliveries) ? g.deliveries : []
})

const dedupedDeliveries = computed<DeliveryRowForTable[]>(() => {
  const byKey = new Map<string, any>()
  for (const d of rawDeliveries.value) byKey.set(makeKey(d), d) // last one wins
  const parseOverBall = (overLike: unknown, ballLike: unknown) => {
    if (typeof ballLike === 'number') return { over: Math.max(0, Math.floor(Number(overLike) || 0)), ball: ballLike }
    if (typeof overLike === 'string') { const [o, b] = overLike.split('.'); return { over: Number(o) || 0, ball: Number(b) || 0 } }
    if (typeof overLike === 'number') { const over = Math.floor(overLike); const ball = Math.max(0, Math.round((overLike - over) * 10)); return { over, ball } }
    return { over: 0, ball: 0 }
  }
  return Array.from(byKey.values()).map((d: any) => {
    const { over, ball } = parseOverBall(d.over_number ?? d.over, d.ball_number ?? d.ball)
    return {
      over_number: over,
      ball_number: ball,
      runs_scored: Number(d.runs_scored ?? d.runs) || 0,
      striker_id: normId(d.striker_id),
      non_striker_id: normId(d.non_striker_id),
      bowler_id: normId(d.bowler_id),
      extra: (d.extra ?? d.extra_type ?? undefined) as DeliveryRowForTable['extra'] | undefined,
      extra_runs: Number(d.extra_runs ?? 0), 
      runs_off_bat: Number(d.runs_off_bat ?? d.runs ?? 0),
      is_wicket: Boolean(d.is_wicket),
      commentary: d.commentary as string | undefined,
      dismissed_player_id: (d.dismissed_player_id ? normId(d.dismissed_player_id) : null) as UUID | null,
      at_utc: d.at_utc as string | undefined,
    }
  }).sort((a, b) => (a.over_number - b.over_number) || (a.ball_number - b.ball_number))
})

// ðŸ”§ NEW: helpers to scope deliveries to the current innings
function inningsOf(d:any): number | null {
  const v = Number(d.innings ?? d.inning ?? d.inning_no ?? d.innings_no ?? d.inning_number)
  return Number.isFinite(v) ? v : null
}

const deliveriesThisInningsRaw = computed<any[]>(() => {
  const cur = currentInnings.value
  const arr = rawDeliveries.value
  const hasInnings = arr.some(d => inningsOf(d) != null)
  if (hasInnings) return arr.filter(d => inningsOf(d) === cur)

  // Fallback only if absolutely no innings markers exist (old data)
  if (cur === 1) return arr
  if (inningsStartIso.value) {
    // strict: only include items with a timestamp after start
    return arr.filter(d => d.at_utc && String(d.at_utc) >= inningsStartIso.value!)
  }
  return [] // no markers, no timestamps â€” donâ€™t risk mixing innings
})



function dedupeByKey(arr:any[]) {
  const byKey = new Map<string, any>()
  for (const d of arr) byKey.set(makeKey(d), d)
  return Array.from(byKey.values())
}

const deliveriesThisInnings = computed<DeliveryRowForTable[]>(() => {
  const parseOverBall = (overLike: unknown, ballLike: unknown) => {
    if (typeof ballLike === 'number') return { over: Math.max(0, Math.floor(Number(overLike) || 0)), ball: ballLike }
    if (typeof overLike === 'string') { const [o, b] = overLike.split('.'); return { over: Number(o) || 0, ball: Number(b) || 0 } }
    if (typeof overLike === 'number') { const over = Math.floor(overLike); const ball = Math.max(0, Math.round((overLike - over) * 10)); return { over, ball } }
    return { over: 0, ball: 0 }
  }
  return dedupeByKey(deliveriesThisInningsRaw.value).map((d: any) => {
    const { over, ball } = parseOverBall(d.over_number ?? d.over, d.ball_number ?? d.ball)
    return {
      over_number: over,
      ball_number: ball,
      runs_scored: Number(d.runs_scored ?? d.runs) || 0,
      striker_id: normId(d.striker_id),
      non_striker_id: normId(d.non_striker_id),
      bowler_id: normId(d.bowler_id),
      extra: (d.extra ?? d.extra_type ?? undefined) as DeliveryRowForTable['extra'] | undefined,
      extra_runs: Number(d.extra_runs ?? 0),                       // âœ… added
      runs_off_bat: Number(d.runs_off_bat ?? d.runs ?? 0),        // âœ… added
      is_wicket: Boolean(d.is_wicket),
      commentary: d.commentary as string | undefined,
      dismissed_player_id: (d.dismissed_player_id ? normId(d.dismissed_player_id) : null) as UUID | null,
      at_utc: d.at_utc as string | undefined,
    }
  }).sort((a, b) => (a.over_number - b.over_number) || (a.ball_number - b.ball_number))
})

// == Derived bowling figures from deliveries in *this innings* ==
const bowlingDerivedByPlayer = computed<Record<string, { balls: number; runs: number; maidens: number }>>(() => {
  const out: Record<string, { balls: number; runs: number; maidens: number }> = {}
  // group per over for maiden detection
  const overRuns: Record<string, number> = {}

  const add = (pid: string) => (out[pid] ||= { balls: 0, runs: 0, maidens: 0 })

  for (const d of deliveriesThisInnings.value) {
    const pid = String(d.bowler_id || '')
    if (!pid) continue
    const rec = add(pid)

    // Runs conceded to bowler
    if (d.extra === 'wd') {
      rec.runs += Number(d.extra_runs || 0)               // wides: all wides to bowler
    } else if (d.extra === 'nb') {
      rec.runs += 1 + Number(d.runs_off_bat || 0)         // no-ball: 1 penalty + off-bat
      // ball does NOT count
    } else if (d.extra === 'b' || d.extra === 'lb') {
      // byes/leg-byes: NO runs to bowler, but DO consume a ball
      rec.balls += 1
    } else {
      // legal: off-bat runs to bowler, consumes a ball
      rec.runs += Number(d.runs_off_bat ?? d.runs_scored ?? 0)
      rec.balls += 1
    }

    // Track runs in the *over* to compute maidens later (legal extras still count to over total)
    const overKey = `${d.bowler_id}:${d.over_number}`
    let totalThisBall = 0
    if (d.extra === 'wd') totalThisBall = Number(d.extra_runs || 0)
    else if (d.extra === 'nb') totalThisBall = 1 + Number(d.runs_off_bat || 0)
    else if (d.extra === 'b' || d.extra === 'lb') totalThisBall = Number(d.runs_scored || d.extra_runs || 0)
    else totalThisBall = Number(d.runs_off_bat ?? d.runs_scored ?? 0)
    overRuns[overKey] = (overRuns[overKey] || 0) + totalThisBall
  }

  // Maidens: any completed over with 0 runs
  for (const key of Object.keys(overRuns)) {
    const [pid, overStr] = key.split(':')
    const over = Number(overStr)
    // count legal balls in that over
    const legalBallsInOver = deliveriesThisInnings.value.filter(d =>
      String(d.bowler_id) === pid &&
      d.over_number === over &&
      (d.extra !== 'wd' && d.extra !== 'nb')
    ).length
    if (legalBallsInOver === 6 && overRuns[key] === 0) {
      add(pid).maidens += 1
    }
  }

  return out
})

// === Current bowler figures (match the scorecardâ€™s logic) ====================
const currentBowlerDerived = computed(() => {
  const id = currentBowlerId.value
  if (!id) return null

  // Derived balls/runs/maidens for this innings
  const base = bowlingDerivedByPlayer.value[id]

  // Get wickets from the live XI rows (authoritative wicket tally)
  const r = (bowlingRowsXI.value || []).find((p: any) => String(p.id) === String(id)) as any
  const wkts = Number(r?.wkts ?? r?.wickets_taken ?? 0)

  const balls = Number(base?.balls || 0)
  const runs  = Number(base?.runs  || 0)

  return {
    wkts,
    runs,
    balls,
    oversText: oversDisplayFromBalls(balls),
    econText: econ(runs, balls),
  }
})

// Name lookup for DeliveryTable
function playerNameById(id?: UUID | null): string {
  const nid = normId(id)
  if (!nid) return ''
  const g = gameStore.currentGame as unknown as { team_a: Team; team_b: Team } | null
  if (!g) return ''
  return (
    g.team_a.players.find(p => normId(p.id) === nid)?.name ??
    g.team_b.players.find(p => normId(p.id) === nid)?.name ??
    ''
  )
}


// ================== Helpers: SR and Economy (local) ==================
function oversDisplayFromBalls(balls: number): string {
  const ov = Math.floor(balls / 6)
  const rem = balls % 6
  return `${ov}.${rem}`
}
function econ(runsConceded: number, ballsBowled: number): string {
  if (!ballsBowled) return 'â€”'
  const overs = ballsBowled / 6
  return (runsConceded / overs).toFixed(2)
}

const cantScoreReasons = computed(() => {
  const rs:string[] = []
  const firstBall = Number(currentOverBalls.value || 0) === 0
  if (!gameStore.currentGame) rs.push('No game loaded')
  else if (!['in_progress','live','started'].includes(String((gameStore.currentGame as any).status || '')))
    rs.push(`Game is ${(gameStore.currentGame as any).status}`)

  if (!selectedStriker.value) rs.push('Select striker')
  if (!selectedNonStriker.value) rs.push('Select non-striker')
  if (selectedStriker.value && selectedStriker.value === selectedNonStriker.value)
    rs.push('Striker and non-striker cannot be the same')

  if (!currentBowlerId.value && !(needsNewOverLive.value && firstBall && !!selectedBowler.value)) {
    rs.push('Start next over / choose bowler')
  }
  if (!selectedBowler.value) rs.push('Choose bowler')
  if (needsNewOver.value && !(firstBall && !!selectedBowler.value)) rs.push('Start next over')
  if (needsNewBatter.value) rs.push('Select next batter')
  if (needsNewInningsLive.value) rs.push('Start next innings')

  return rs
})

function clearQueuedDeliveriesForThisGame(): void {
  const id = gameId.value
  if (!id) return
  ;(gameStore as any).offlineQueue = (gameStore as any).offlineQueue.filter((q: any) => q.gameId !== id)
  console.info('Cleared offlineQueue for game', id)
}

// ================== Live strip data (current bowler / over) ==================
// ================== Live strip data (current bowler / over) ==================
const stateAny = computed(() => gameStore.state as any)
const isStartingInnings = ref(false)
// First-innings summary captured locally when we flip to innings 2
const firstInnings = ref<{ runs: number; wickets: number; overs: string } | null>(null)

// ðŸ”§ NEW: if backend publishes an innings start, adopt it
watch(() => (stateAny.value?.innings_start_at as string | undefined), (t) => {
  if (t) inningsStartIso.value = String(t)
}, { immediate: true })

// Count legal balls in *this* innings (wides/no-balls don't consume a ball)
const legalBallsBowled = computed(() =>
  deliveriesThisInnings.value.filter(d => d.extra !== 'wd' && d.extra !== 'nb').length
)


// NEW: wickets directly from deliveries (robust even before store catches up)
const wicketsFromDeliveries = computed(() => {
  const battingIds = new Set(battingPlayers.value.map(p => normId(p.id)))
  const dismissed = new Set<string>()
  for (const d of deliveriesThisInnings.value) {
    const did = normId(d.dismissed_player_id)
    if (d.is_wicket && did && battingIds.has(did)) dismissed.add(did)
  }
  return dismissed.size
})

// All-out fallback (use XI size if available; cricket all-out threshold is 10)
const allOut = computed(() => {
  const xiSize = battingPlayers.value?.length || 11
  const maxOut = Math.max(10, xiSize - 1)
  const wicketsFromScore = Number((gameStore as any).score?.wickets ?? 0)
  const wicketsFromRows  = battingEntries.value.filter(b => b.is_out).length
  const wickets = Math.max(wicketsFromScore, wicketsFromRows, wicketsFromDeliveries.value)
  return wickets >= maxOut
})

// Overs exhausted fallback â€” IMPORTANT: use current_over_balls (your storeâ€™s field)
const ballsThisOver = computed(() => Number(stateAny.value?.current_over_balls ?? 0))
const ballsPerInningsLimit = computed(() =>
  (oversLimit.value ? oversLimit.value * 6 : Infinity)
)
const oversExhausted = computed(() =>
  legalBallsBowled.value >= ballsPerInningsLimit.value && ballsThisOver.value === 0
)

// Track last time the innings number changed
const inningsFlipAt = ref<number>(0)
watch(() => (gameStore.currentGame as any)?.current_inning, () => {
  inningsFlipAt.value = Date.now()
})

// Small suppression window after flip (ms)
const SUPPRESS_DERIVED_MS = 10000

const needsNewInningsLive = computed<boolean>(() => {
  const status = String((gameStore.currentGame as any)?.status || '')
  const serverGate =
    Boolean(stateAny.value?.needs_new_innings) ||
    status === 'innings_break'

  // If server says the gate is up, respect it.
  if (serverGate) return true

  // While server says we're in progress, don't re-raise the gate locally.
  if (status === 'in_progress') return false

  // Right after an innings flip, ignore local "allOut/oversExhausted" noise.
  if (Date.now() - inningsFlipAt.value < SUPPRESS_DERIVED_MS) return false

  // Otherwise, the local fallbacks can raise the gate.
  return allOut.value || oversExhausted.value
})




const needsNewOverLive   = computed<boolean>(() => Boolean(stateAny.value?.needs_new_over))
const needsNewBatterLive = computed<boolean>(() => Boolean(stateAny.value?.needs_new_batter))
const currentBowlerId   = computed<UUID | null>(() => (stateAny.value?.current_bowler_id ?? null) as UUID | null)
const lastBallBowlerId  = computed<UUID | null>(() => (stateAny.value?.last_ball_bowler_id ?? null) as UUID | null)
const currentOverBalls  = computed<number>(() => Number(stateAny.value?.current_over_balls ?? 0))
const midOverChangeUsed = computed<boolean>(() => Boolean(stateAny.value?.mid_over_change_used))

const currentBowler = computed<Player | null>(() => {
  const id = currentBowlerId.value
  if (!id) return null
  return bowlingPlayers.value.find(p => p.id === id) || null
})

const currentBowlerStats = computed<{ runs: number; balls: number }>(() => {
  const id = currentBowlerId.value
  if (!id) return { runs: 0, balls: 0 }

  // Prefer precomputed store stats if available
  const sAny = (gameStore as any).bowlingStatsByPlayer as
    | Record<string, { runsConceded: number; balls: number }>
    | undefined
  const s = sAny?.[id]
  if (s) return { runs: Number(s.runsConceded), balls: Number(s.balls) }

  // Fallback: derive from deliveries (per your backend semantics)
  const filtered = deliveriesThisInnings.value.filter(d => d.bowler_id === id)

  const addRuns = (d: DeliveryRowForTable) => {
    if (d.extra === 'wd') return Number(d.extra_runs || 0)            // all wides to bowler
    if (d.extra === 'nb') return 1 + Number(d.runs_off_bat || 0)      // penalty + off bat
    if (d.extra === 'b' || d.extra === 'lb') return 0                  // byes: none to bowler
    return Number(d.runs_off_bat ?? d.runs_scored ?? 0)                // legal: off bat
  }

  const runs = filtered.reduce((sum, d) => sum + addRuns(d), 0)

  // Legal balls: byes/leg-byes DO consume a ball; wides/nb do not
  const isLegal = (d: DeliveryRowForTable) => !d.extra || d.extra === 'b' || d.extra === 'lb'
  const balls = filtered.filter(isLegal).length

  return { runs, balls }
})


function parseOversNotation(s?: string | number | null) {
  if (s == null) return { oc: 0, ob: 0 }
  const str = String(s)
  const [o, b] = str.split('.')
  const oc = Number(o) || 0
  let ob = Number(b) || 0
  if (ob < 0) ob = 0
  if (ob > 5) ob = 5
  return { oc, ob }
}

const oversDisplay = computed<string>(() => {
  const legal = deliveriesThisInnings.value.filter(d => d.extra !== 'wd' && d.extra !== 'nb').length
  const ov = Math.floor(legal / 6)
  const rem = legal % 6
  return `${ov}.${rem}`
})


const eligibleNextOverBowlers = computed<Player[]>(() => bowlingPlayers.value.filter(p => p.id !== lastBallBowlerId.value))
const replacementOptions = computed<Player[]>(() => bowlingPlayers.value.filter(p => p.id !== currentBowlerId.value))
const canUseMidOverChange = computed(() => currentOverBalls.value < 6 && !midOverChangeUsed.value)
const overInProgress = computed<boolean>(() => Number((stateAny.value?.balls_this_over ?? 0)) > 0)

const inningsScore = computed<{ runs: number; wickets: number }>(() => ({
  runs: Number((gameStore as any).score?.runs ?? 0),
  wickets: Number((gameStore as any).score?.wickets ?? 0),
}))

// Target shown during the chase (if server provided)
const target = computed<number | null>(() => {
  const t = (gameStore.currentGame as any)?.target
  return typeof t === 'number' ? t : null
})

// Legal balls in the *current* (latest) over
const legalBallsThisOver = computed(() => {
  const arr = deliveriesThisInnings.value
  if (!arr.length) return 0
  const lastOver = Math.max(...arr.map(d => d.over_number))
  return arr.filter(d =>
    d.over_number === lastOver && (d.extra !== 'wd' && d.extra !== 'nb')
  ).length
})

// Local fallback: if weâ€™ve bowled 6 legal balls and no innings gate is up, prompt next over.
const needsNewOverDerived = computed(() =>
  legalBallsThisOver.value === 6 && !needsNewInningsLive.value
)

// ---- Start Next Innings ----
const startInningsDlg = ref<HTMLDialogElement | null>(null)
const nextStrikerId = ref<UUID>('' as UUID)
const nextNonStrikerId = ref<UUID>('' as UUID)
const openingBowlerId = ref<UUID>('' as UUID)

function openStartInnings(): void {
  // sensible defaults
  const bat = nextBattingXI.value
  const bowl = nextBowlingXI.value
  nextStrikerId.value = (bat[0]?.id ?? '') as UUID
  nextNonStrikerId.value = (bat[1]?.id ?? '') as UUID
  openingBowlerId.value = (bowl[0]?.id ?? '') as UUID
  startInningsDlg.value?.showModal()
}
function closeStartInnings(): void { startInningsDlg.value?.close() }

async function confirmStartInnings(): Promise<void> {
  console.log('[confirmStartInnings] clicked');
  const id = gameId.value
  if (!id) return
  try {
    inningsStartIso.value = new Date().toISOString()
    isStartingInnings.value = true

    // Cache the first-innings summary locally (runs/wkts/overs) before we flip
    try {
      firstInnings.value = {
        runs: inningsScore.value.runs,
        wickets: inningsScore.value.wickets,
        overs: oversDisplay.value,
      }
    } catch { /* noop */ }

    const payload = {
      striker_id:        normId(nextStrikerId.value)     || null,
      non_striker_id:    normId(nextNonStrikerId.value)  || null,
      opening_bowler_id: normId(openingBowlerId.value)   || null,
    }

    const anyStore: any = gameStore as any
    if (typeof anyStore.startNextInnings === 'function') {
      await anyStore.startNextInnings(id, payload)
    } else {
      const res = await fetch(`${apiBase}/games/${encodeURIComponent(id)}/innings/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(await res.text())
      await gameStore.loadGame(id)
    }

    // ðŸ”§ Optimistic local clear so the dialog actually goes away now
    // (server snapshot will arrive and confirm shortly)
    gameStore.mergeGamePatch({ status: 'in_progress' } as any)
    inningsFlipAt.value = Date.now()
    if (liveSnapshot.value) {
      liveSnapshot.value = { ...liveSnapshot.value, needs_new_innings: false } as any
    }

    // Optimistic selections
    selectedStriker.value = normId(nextStrikerId.value) as string
    selectedNonStriker.value = normId(nextNonStrikerId.value) as string
    if (openingBowlerId.value) selectedBowler.value = normId(openingBowlerId.value) as string


    isStartingInnings.value = false
    showToast('Next innings started', 'success')
    closeStartInnings()
  } catch (e:any) {
    isStartingInnings.value = false
    onError(e?.message || 'Failed to start next innings')
    // (Optional) console for quick visibility:
    console.error('startNextInnings error:', e)
  }
}


// ================== EMBED / SHARE PANEL ==================
const theme = ref<'auto' | 'dark' | 'light'>('dark')
const title = ref<string>('Live Scoreboard')
const logo = ref<string>('')
const height = ref<number>(180)

// script setup

const sponsorsUrl = ref<string>(`${apiBase}/sponsors/cricksy/sponsors.json`)


const embedUrl = computed<string>(() => {
  const routerMode = (import.meta as any).env?.VITE_ROUTER_MODE ?? 'history'
  const useHash = routerMode === 'hash'
  const base = window.location.origin + (useHash ? '/#' : '')
  const path = `/embed/${encodeURIComponent(gameId.value)}`
  const qs = new URLSearchParams()
  if (theme.value && theme.value !== 'auto') qs.set('theme', theme.value)
  if (title.value) qs.set('title', title.value)
  if (logo.value) qs.set('logo', logo.value)
  if (sponsorsUrl.value) qs.set('sponsorsUrl', sponsorsUrl.value)
  const q = qs.toString()
  return q ? `${base}${path}?${q}` : `${base}${path}`
})

const iframeCode = computed<string>(() => `<iframe src="${embedUrl.value}" width="100%" height="${height.value}" frameborder="0" scrolling="no" allowtransparency="true"></iframe>`)

const shareOpen = ref<boolean>(false)
const copied = ref<boolean>(false)
const codeRef = ref<HTMLTextAreaElement | null>(null)

function closeShare(): void { shareOpen.value = false; copied.value = false }
async function copyEmbed(): Promise<void> {
  const txt = iframeCode.value
  try {
    await navigator.clipboard.writeText(txt)
    copied.value = true
  } catch {
    const el = codeRef.value
    if (el) {
      el.focus()
      el.select()
      try { document.execCommand('copy') } catch { /* ignore */ }
      copied.value = true
    }
  }
  window.setTimeout(() => (copied.value = false), 1600)
}
watch(shareOpen, (o) => { if (o) setTimeout(() => codeRef.value?.select(), 75) })

// ================== Tiny toast ==================
type ToastType = 'success' | 'error' | 'info'
const toast = ref<{ message: string; type: ToastType } | null>(null)
let toastTimer: number | null = null
function showToast(message: string, type: ToastType = 'success', ms = 1800): void {
  toast.value = { message, type }
  if (toastTimer) window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => (toast.value = null), ms) as unknown as number
}
function onScored(): void { showToast(pendingCount.value > 0 ? 'Saved (queued) âœ“' : 'Saved âœ“', 'success') }
function onError(message: string): void { showToast(message || 'Something went wrong', 'error', 3000) }

// ================== Lifecycle ==================
onMounted(async () => {
  const id = gameId.value
  if (!id) { void router.replace('/'); return }

  // Persist lastGameId for resume functionality
  try {
    localStorage.setItem('lastGameId', id)
  } catch (err) {
    console.warn('Failed to save lastGameId:', err)
  }

  try {
    await gameStore.loadGame(id)
    loadXIForGame(id)
    gameStore.initLive(id)
    clearQueuedDeliveriesForThisGame()

    // Gate prompts after initial load
    if (liveSnapshot.value) syncBattersFromSnapshot(liveSnapshot.value as any)
    if (currentBowlerId.value) selectedBowler.value = currentBowlerId.value as UUID
    if (needsNewBatterLive.value) openSelectBatter()
    if (needsNewOverLive.value)  openStartOver()
  } catch (e) {
    showToast('Failed to load or connect', 'error', 3000)
    console.error('load/init failed:', e)
  }
})

onUnmounted(() => {
  if (toastTimer) window.clearTimeout(toastTimer)
  gameStore.stopLive()
})

// --- Client fallback: derive striker/non-striker from the last delivery when snapshot is odd ---
function maybeRotateFromLastDelivery() {
  const last: any =
    (liveSnapshot.value as any)?.last_delivery ??
    (gameStore.currentGame as any)?.last_delivery
  if (!last) return

  const prevS = normId(selectedStriker.value)
  const prevNS = normId(selectedNonStriker.value)
  if (!prevS || !prevNS) return

  const x = (last.extra_type as DeliveryRowForTable['extra'] | null) || null
  const legal = !x || x === 'b' || x === 'lb'
  let swap = false

  if (legal) {
    // On legal balls, parity of off-the-bat runs decides strike
    const offBat = Number(last.runs_off_bat ?? last.runs_scored ?? 0)
    swap = (offBat % 2) === 1
  } else if (x === 'wd') {
    // wides: total includes automatic 1; only the *run(s) actually run* flip strike
    const totalWides = Math.max(1, Number(last.extra_runs ?? 1))
    const runsRun = totalWides - 1
    swap = (runsRun % 2) === 1
  } else if (x === 'nb') {
    // no-balls: penalty 1 plus *additional* runs (off bat or nb-byes if you add them later)
    const offBat = Number(last.runs_off_bat ?? 0)
    const extraBeyondPenalty = Math.max(0, Number(last.extra_runs ?? 1) - 1)
    swap = ((offBat + extraBeyondPenalty) % 2) === 1
  }

  if (swap) {
    const s = selectedStriker.value
    selectedStriker.value = selectedNonStriker.value
    selectedNonStriker.value = s
  }
}

// Keep UI batters in lockstep with server, but fix snapshot oddities locally.
function syncBattersFromSnapshot(snap: any): void {
  if (!snap) return
  const sId  = normId(snap.current_striker_id ?? snap?.batsmen?.striker?.id ?? '')
  const nsId = normId(snap.current_non_striker_id ?? snap?.batsmen?.non_striker?.id ?? '')

  if (sId)  selectedStriker.value = sId as string
  if (nsId) selectedNonStriker.value = nsId as string

  // Guard: snapshot sometimes sends SAME id for both ends; fix using last delivery parity.
  if (sId && nsId && sId === nsId) {
    maybeRotateFromLastDelivery()
  }
}

watch(liveSnapshot, (snap) => syncBattersFromSnapshot(snap))

// Keep selections valid when innings flips or XI loads
watch(currentBowlerId, (id) => { selectedBowler.value = id ? (id as UUID) : '' as unknown as UUID })
watch([bowlingPlayers, xiLoaded, currentBowlerId], () => {
  const id = selectedBowler.value
  if (id && !bowlingPlayers.value.some(p => p.id === id) && id !== currentBowlerId.value) selectedBowler.value = '' as unknown as UUID
})
watch(needsNewInningsLive, (v) => {
  if (!v) return
  if (isStartingInnings.value) return               // donâ€™t pop while weâ€™re starting
  if (startInningsDlg.value?.open) return           // already open
  if (v) {
    selectedBowler.value = '' as any   // force explicit choice for the new innings
  }
  try { startOverDlg.value?.close() } catch {}
  try { selectBatterDlg.value?.close() } catch {}
  nextTick().then(() => openStartInnings())
})



watch(() => stateAny.value?.needs_new_innings, (v) => {
  if (!v) isStartingInnings.value = false
})


// Only open these gates if an innings is NOT required
watch(needsNewBatterLive, (v) => { if (v && !needsNewInningsLive.value) openSelectBatter() })
watch([needsNewOverLive, needsNewOverDerived], ([serverGate, localGate]) => {
  if ((serverGate || localGate) && !needsNewInningsLive.value) {
    // Keep any user-chosen next bowler; just nudge the dialog if you want.
    if (!selectedBowler.value) {
      selectedBowler.value = (eligibleNextOverBowlers.value[0]?.id || '') as UUID
      }
      selectedNextOverBowlerId.value = selectedBowler.value as UUID
      openStartOver()
    }
})

watch([battingPlayers, needsNewInningsLive], ([list]) => {
  const ids = new Set(list.map(p => p.id))
  if (selectedStriker.value && !ids.has(selectedStriker.value)) {
    selectedStriker.value = '' as any
  }
  if (selectedNonStriker.value && !ids.has(selectedNonStriker.value)) {
    selectedNonStriker.value = '' as any
  }
})

watch([bowlingPlayers, needsNewInningsLive], ([list]) => {
  const ids = new Set(list.map(p => p.id))
  if (selectedBowler.value && !ids.has(selectedBowler.value)) {
    selectedBowler.value = '' as any
  }
})


// Reconnect + flush controls
function reconnect(): void {
  const id = gameId.value
  if (!id) return
  try {
    gameStore.initLive(id)
    showToast('Reconnectingâ€¦', 'info')
  } catch {
    showToast('Reconnect failed', 'error', 2500)
  }
}
function flushNow(): void {
  const id = gameId.value
  if (!id) return
  gameStore.flushQueue(id)
  showToast('Flushing queueâ€¦', 'info')
}

// ================== Start Over & Mid-over Change ==================
const startOverDlg = ref<HTMLDialogElement | null>(null)
const changeBowlerDlg = ref<HTMLDialogElement | null>(null)
const selectedNextOverBowlerId = ref<UUID>('' as UUID)
const selectedReplacementBowlerId = ref<UUID>('' as UUID)
const selectBatterDlg = ref<HTMLDialogElement | null>(null)
const selectedNextBatterId = ref<UUID>('' as UUID)
const canStartOverNow = computed(() => needsNewOverLive.value || !currentBowlerId.value)
const candidateBatters = computed<Player[]>(() => {
  const anyStore = gameStore as any
  if (Array.isArray(anyStore.availableBatsmen) && anyStore.availableBatsmen.length) {
    return anyStore.availableBatsmen as Player[]
  }
  const outSet = new Set(battingEntries.value.filter(b => b.is_out).map(b => b.player_id))
  return battingPlayers.value.filter(p => !outSet.has(p.id))
})



function openSelectBatter(): void { selectedNextBatterId.value = '' as UUID; selectBatterDlg.value?.showModal() }
function closeSelectBatter(): void { selectBatterDlg.value?.close() }

async function confirmSelectBatter() {
  const batter = normId(selectedNextBatterId.value)
  if (!batter) return

  await gameStore.replaceBatter(batter)

  // Prefer authoritative IDs from the latest snapshot / state
  const snap: any = (liveSnapshot.value as any) ?? (gameStore as any).state ?? {}
  const sId  = normId(snap.current_striker_id ?? snap?.batsmen?.striker?.id ?? '')
  const nsId = normId(snap.current_non_striker_id ?? snap?.batsmen?.non_striker?.id ?? '')

  if (sId || nsId) {
    if (sId)  selectedStriker.value = sId as string
    if (nsId) selectedNonStriker.value = nsId as string
  } else {
    // Fallback: use last deliveryâ€™s dismissed id to decide end
    const last: any =
      liveSnapshot.value?.last_delivery ??
      (gameStore.currentGame as any)?.deliveries?.slice(-1)?.[0]

    const dismissed = normId(last?.dismissed_player_id || '')
    if (dismissed && normId(selectedStriker.value) === dismissed)       selectedStriker.value = batter as string
    else if (dismissed && normId(selectedNonStriker.value) === dismissed) selectedNonStriker.value = batter as string
    else if (!selectedStriker.value)                                     selectedStriker.value = batter as string
    else if (!selectedNonStriker.value)                                  selectedNonStriker.value = batter as string
  }

  showToast('Next batter set', 'success')
  closeSelectBatter()
}


function openStartOver(): void {
  const first = eligibleNextOverBowlers.value[0]?.id ?? '' as UUID
  selectedNextOverBowlerId.value = first as UUID
  startOverDlg.value?.showModal()
}
function closeStartOver(): void { startOverDlg.value?.close() }

// Store only
async function confirmStartOver(): Promise<void> {
  const id = gameId.value
  const bowler = selectedNextOverBowlerId.value
  if (!id || !bowler) return
  try {
    await gameStore.startNewOver(bowler)
    selectedBowler.value = bowler
    selectedNextOverBowlerId.value = '' as UUID
    showToast('Over started', 'success')
    closeStartOver()
  } catch (err:any) {
    const msg = err?.message || 'Failed to start over'
    showToast(msg, 'error')
    console.error('confirmStartOver error:', err)
  }
}

function openChangeBowler(): void { selectedReplacementBowlerId.value = '' as UUID; changeBowlerDlg.value?.showModal() }
function closeChangeBowler(): void { changeBowlerDlg.value?.close() }

async function confirmChangeBowler(): Promise<void> {
  const id = gameId.value
  const repl = selectedReplacementBowlerId.value
  if (!id || !repl) return
  try {
    await gameStore.changeBowlerMidOver(id, repl, 'injury')
    if (currentBowlerId.value) selectedBowler.value = currentBowlerId.value as UUID
    showToast('Bowler changed', 'success')
  } catch (e: any) {
    await gameStore.loadGame(id)
    selectedBowler.value = (currentBowlerId.value || '') as UUID
    onError(e?.message || 'Failed to change bowler')
  } finally {
    selectedReplacementBowlerId.value = '' as UUID
    closeChangeBowler()
  }
}
</script>

<template>
  <div class="game-scoring">
    <!-- Top toolbar -->
    <header class="toolbar">
      <div class="left">
        <h2 class="title">Scoring Console</h2>
        <span class="meta" v-if="gameId">Game: {{ gameId }}</span>
      </div>

      <div class="right">
        <select v-model="theme" class="sel" aria-label="Theme" name="theme">
          <option value="auto">Theme: Auto</option>
          <option value="dark">Theme: Dark</option>
          <option value="light">Theme: Light</option>
        </select>

        <input v-model="title" class="inp" type="text" name="embedTitle" placeholder="Embed title (optional)" aria-label="Embed title" />
        <input v-model="logo" class="inp" type="url" name="logoUrl" placeholder="Logo URL (optional)" aria-label="Logo URL" />
        <button class="btn btn-primary" @click="shareOpen = true">Share</button>
      </div>
    </header>

    <main class="content">
      <!-- Live scoreboard preview â€” widget reads from store; interruptions polling disabled -->
      <ScoreboardWidget
        :game-id="gameId"
        :theme="theme"
        :title="title"
        :logo="logo"
        :api-base="apiBase"
        :sponsors-url="sponsorsUrl"
        :can-control="false"
        interruptions-mode="off"
      />

      <PresenceBar class="mb-3" :game-id="gameId" :status="gameStore.connectionStatus" :pending="pendingCount" />

      <section
        class="selectors card alt small-metrics"
        v-if="Number((gameStore.currentGame as any)?.current_inning) === 2 && (firstInnings || targetSafe != null)"
      >
        <div class="row compact">
          <div class="col" v-if="firstInnings">
            <strong>Innings 1:</strong>
            {{ firstInnings.runs }}/{{ firstInnings.wickets }} ({{ firstInnings.overs }})
          </div>

          <div class="col" v-if="targetSafe != null">
            <strong>Target:</strong> {{ targetSafe }}
          </div>

          <div class="col" v-if="requiredRunRate != null">
            <strong>Req RPO:</strong> {{ requiredRunRate.toFixed(2) }}
            <small class="hint" v-if="runsRequired != null && ballsRemaining >= 0">
              Â· Need {{ runsRequired }} off {{ ballsRemaining }} balls ({{ oversRemainingDisplay }} overs)
            </small>
          </div>
        </div>
      </section>


      <!-- Player selectors -->
      <section class="selectors card" style="border:1px solid rgba(0,0,0,.08); border-radius:12px; padding:12px; margin-bottom:12px;">
        <h3 style="margin:0 0 8px; font-size:14px;">Players</h3>
        <div class="row">
          <div class="col">
            <label class="lbl">Striker</label>
            <select v-model="selectedStriker" class="sel" aria-label="Select striker">
              <option disabled value="">Choose strikerâ€¦</option>
              <option
                v-for="p in battingPlayers"
                :key="p.id"
                :value="p.id"
                :disabled="p.id === selectedNonStriker"
              >
                {{ p.name }}
              </option>
            </select>
          </div>

          <div class="col">
            <label class="lbl">Non-striker</label>
            <select v-model="selectedNonStriker" class="sel" aria-label="Select non-striker">
              <option disabled value="">Choose non-strikerâ€¦</option>
              <option
                v-for="p in battingPlayers"
                :key="p.id"
                :value="p.id"
                :disabled="p.id === selectedStriker"
              >
                {{ p.name }}
              </option>
            </select>
          </div>

          <div class="col">
            <label class="lbl">Bowler</label>
            <select v-model="selectedBowler" class="sel" aria-label="Select bowler">
              <option disabled value="">Choose bowlerâ€¦</option>
              <option v-for="p in bowlingPlayers" :key="p.id" :value="p.id">
                {{ p.name }}
              </option>
            </select>
          </div>
        </div>

        <small class="hint" v-if="selectedStrikerName && selectedBowlerName">
          {{ selectedStrikerName }} facing {{ selectedBowlerName }}.
        </small>
      </section>

      <!-- Bowling controls -->
      <section class="selectors card alt">
        <div class="row tight">
          <div class="col">
            <button class="btn" :disabled="needsNewInningsLive || !canStartOverNow" @click="openStartOver">
              Start Next Over
            </button>
            <small class="hint">
              {{ !currentBowlerId ? 'No active bowler yet â€” start the over.' : 'Disables previous overâ€™s last bowler.' }}
            </small>
          </div>
          <div class="col">
            <button class="btn" :disabled="!canUseMidOverChange" @click="openChangeBowler">Mid-over Change</button>
            <small class="hint">Allowed once per over (injury).</small>
          </div>
          <div class="col bowler-now" v-if="currentBowler">
            <strong>Current:</strong> {{ currentBowler.name }} Â·
            <span>{{ currentBowlerDerived?.wkts ?? 0 }}-{{ currentBowlerDerived?.runs ?? 0 }}
              ({{ currentBowlerDerived?.oversText ?? '0.0' }})
            </span>
            <span> Â· Econ {{ currentBowlerDerived?.econText ?? 'â€”' }}</span>
          </div>
        </div>
      </section>

      <!-- Match controls -->
      <section class="selectors card alt">
        <div class="row tight">
          <div class="col">
            <button class="btn" @click="openWeather">Weather interruption</button>
            <small class="hint">Pause/resume play; logs delay.</small>
          </div>
          <div class="col">
            <button class="btn" @click="jumpToReduceOvers">Reduce oversâ€¦</button>
            <small class="hint">Adjust match or innings limit.</small>
          </div>
          <div class="col">
            <button class="btn btn-ghost" :disabled="!canForceStartInnings" @click="forceStartInnings">
              Start next innings (fallback)
            </button>
            <small class="hint">Use if the innings gate doesnâ€™t appear.</small>
          </div>
          <!-- NEW: toggle for subs card -->
          <div class="col">
            <label class="lbl" style="display:flex; align-items:center; gap:6px;">
              <input type="checkbox" v-model="showSubsCard" />
              Fielding subs card
            </label>
            <small class="hint">Lists eligible substitute fielders.</small>
          </div>
        </div>
      </section>


      <!-- Gate banners -->
      <div v-if="needsNewBatterLive || needsNewOverLive || needsNewInningsLive" class="placeholder mb-3" role="status" aria-live="polite">
        <div v-if="needsNewInningsLive">New innings required. <button class="btn btn-ghost" @click="openStartInnings">Start next innings</button></div>
        <div v-else-if="needsNewBatterLive">New batter required. <button class="btn btn-ghost" @click="openSelectBatter">Select next batter</button></div>
        <div v-else-if="needsNewOverLive">New over required. <button class="btn btn-ghost" @click="openStartOver">Choose bowler</button></div>
      </div>
      <small class="hint" v-if="(!canScore || !canSubmitSimple) && cantScoreReasons.length">
        {{ cantScoreReasons[0] }}
      </small>

      <pre v-if="isDev" class="dev-debug">
      canScore: {{ canScore }}
      striker: {{ selectedStriker }} ({{ selectedStrikerName }})
      nonStriker: {{ selectedNonStriker }}
      bowler: {{ selectedBowler }} ({{ selectedBowlerName }})
      battingPlayers: {{ battingPlayers.length }} | bowlingPlayers: {{ bowlingPlayers.length }}
      currentBowlerId: {{ currentBowlerId }} | needsNewOverLive: {{ needsNewOverLive }} (store: {{ needsNewOver }})
      needsNewInningsLive: {{ needsNewInningsLive }}
      allOut: {{ allOut }} | wicketsFromDeliveries: {{ wicketsFromDeliveries }}
      oversExhausted: {{ oversExhausted }} | legalBallsBowled: {{ legalBallsBowled }} / {{ oversLimit*6 || 'âˆž' }} | current_over_balls: {{ stateAny?.current_over_balls }}
      inningsStartIso: {{ inningsStartIso }}
      ballsThisInnings(legal): {{ legalBallsBowled }}
      </pre>

      <!-- Delivery (single panel) -->
      <section class="selectors card" style="border:1px solid rgba(0,0,0,.08); border-radius:12px; padding:12px; margin-bottom:12px;">
        <h3 style="margin:0 0 8px; font-size:14px;">Delivery</h3>

        <div class="row" style="grid-template-columns:1fr;">
          <!-- Extra type -->
          <div class="col" style="display:flex; gap:8px; flex-wrap:wrap;">
            <button class="btn" :class="extra==='none' && 'btn-primary'" @click="extra='none'">Legal</button>
            <button class="btn" :class="extra==='nb' && 'btn-primary'" @click="extra='nb'">No-ball</button>
            <button class="btn" :class="extra==='wd' && 'btn-primary'" @click="extra='wd'">Wide</button>
            <button class="btn" :class="extra==='b' && 'btn-primary'" @click="extra='b'">Bye</button>
            <button class="btn" :class="extra==='lb' && 'btn-primary'" @click="extra='lb'">Leg-bye</button>
          </div>

          <!-- Amount selector -->
          <div class="col" v-if="extra==='none' || extra==='nb'">
            <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
              <span>Off the bat:</span>
              <button v-for="r in [0,1,2,3,4,5,6]" :key="r" class="btn" :class="offBat===r && 'btn-primary'" @click="offBat=r">{{ r }}</button>
            </div>
          </div>

          <div class="col" v-else>
            <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
              <span v-if="extra==='wd'">Total wides:</span>
              <span v-else>Extras:</span>
              <button
                v-for="r in (extra==='wd' ? [1,2,3,4,5] : [0,1,2,3,4])"
                :key="r"
                class="btn"
                :class="extraRuns===r && 'btn-primary'"
                @click="extraRuns=r"
              >{{ r }}</button>
            </div>
            <small v-if="extra==='wd'" class="hint">
              1 = just wide; 2 = wide + 1 run; 5 = wide to boundary.
            </small>
          </div>


          <!-- Optional wicket -->
          <div class="col" style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
            <label><input type="checkbox" v-model="isWicket" /> Wicket</label>
            <select v-if="isWicket" v-model="dismissal" class="sel">
              <option disabled value="">Select dismissal</option>
              <option value="bowled">Bowled</option>
              <option value="caught">Caught</option>
              <option value="lbw">LBW</option>
              <option value="run_out">Run-out</option>
              <option value="stumped">Stumped</option>
              <option value="hit_wicket">Hit wicket</option>
            </select>
           <!-- NEW: Fielder (XI + subs) when needed -->
          <select
            v-if="isWicket && needsFielder"
            v-model="selectedFielderId"
            class="sel"
            aria-label="Select fielder"
          >
            <option disabled value="">Select fielderâ€¦</option>
            <option v-for="p in fielderOptions" :key="p.id" :value="p.id">
              {{ p.name }}{{ bowlingXIIds.has(p.id) ? '' : ' (sub)' }}
            </option>
          </select>
          <small
            v-if="isWicket && needsFielder && selectedFielderId && !bowlingXIIds.has(selectedFielderId)"
            class="hint"
          >
            Sub fielder will be credited.
          </small>
          <!-- /NEW -->

          <!-- Shot angle (optional, for legal ball or no-ball) -->
          <input
            v-if="extra==='none' || extra==='nb'"
            type="number"
            min="-180"
            max="180"
            step="5"
            v-model.number="shotAngle"
            placeholder="Shot angle (deg)"
            class="inp"
          />

          <select v-if="isWicket" v-model="dismissedName" class="sel" aria-label="Select dismissed batter">
            <option disabled value="">Select dismissed batter…</option>
            <option v-for="p in dismissedOptions" :key="p.id" :value="p.name">{{ p.name }}</option>
          </select>
        </div>

          <!-- Submit -->
          <div class="col" style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
            <button class="btn btn-primary" :disabled="!canSubmitSimple || !canScore" @click="submitSimple">
              Submit delivery
            </button>

            <button class="btn btn-ghost"
                    :disabled="!canDeleteLast || deletingLast"
                    @click="deleteLastDelivery">
              {{ deletingLast ? 'Deletingâ€¦' : 'Delete last delivery' }}
            </button>
            <small class="hint" v-if="pendingCount > 0">
              Wait for queued actions to finish before deleting.
            </small>

            <small class="hint" v-if="!canScore">
              Select striker/non-striker/bowler and clear any â€œNew over / New batterâ€ prompts.
            </small>
          </div>
        </div>
      </section>

      <!-- Score pad + deliveries on the left; 3 cards side-by-side on the right -->
      <section class="mt-3 layout-2col">
        <div class="left">
          <DeliveryTable
            :deliveries="deliveriesThisInnings"
            :player-name-by-id="playerNameById"
            class="mt-3"
          />
        </div>

        <div class="right">
          <div class="scorecards-grid">
            <BattingCard :entries="battingEntries" />
            
            <BowlingCard :entries="bowlingEntries" />

            <!-- NEW: compact fielding subs card -->
            <div v-if="showSubsCard" class="card subs-card">
              <div class="subs-hdr">
                <h4>Fielding subs</h4>
                <span class="count" v-if="fieldingSubs?.length">{{ fieldingSubs.length }}</span>
              </div>

              <ul class="subs-list" v-if="fieldingSubs && fieldingSubs.length">
                <li v-for="p in fieldingSubs" :key="p.id" class="subs-row">
                  <span class="name">{{ p.name }}</span>
                  <span class="chip">SUB</span>
                </li>
              </ul>
              <div v-else class="empty">
                <small class="hint">No subs on the bench.</small>
              </div>
            </div>

            <!-- Extras / DLS / Reduce Overs -->
            <div class="card extras-card">
              <h4>Extras</h4>
              <div class="extras-grid">
                <span>Wides</span><strong>{{ extrasBreakdown.wides }}</strong>
                <span>No-balls</span><strong>{{ extrasBreakdown.no_balls }}</strong>
                <span>Byes</span><strong>{{ extrasBreakdown.byes }}</strong>
                <span>Leg-byes</span><strong>{{ extrasBreakdown.leg_byes }}</strong>
                <span>Penalty</span><strong>{{ extrasBreakdown.penalty }}</strong>

                <span class="sep">Total</span>
                <strong class="sep">{{ extrasBreakdown.total }}</strong>
              </div>

              <!-- DLS panel -->
              <div v-if="canShowDls" class="card dls-card">
                <h4>DLS</h4>
                <div class="dls-grid">
                  <div class="row-inline">
                    <label class="lbl">G50</label>
                    <input
                      class="inp"
                      type="number"
                      v-model.number="G50"
                      min="150"
                      max="300"
                      step="1"
                      style="width:90px;"
                    />
                    <button class="btn" :disabled="loadingDls" @click="refreshDls">
                      {{ loadingDls ? 'Loadingâ€¦' : 'Preview' }}
                    </button>
                  </div>

                  <template v-if="dls">
                    <div class="dls-stats">
                      <span>Team 1</span>
                      <strong>{{ dls.team1_score }} ({{ dls.team1_resources.toFixed(1) }}%)</strong>

                      <span>Team 2 resources</span>
                      <strong>{{ dls.team2_resources.toFixed(1) }}%</strong>

                      <span>Revised target</span>
                      <strong>{{ dls.target }}</strong>
                    </div>

                    <button class="btn btn-primary" :disabled="applyingDls" @click="applyDls">
                      {{ applyingDls ? 'Applyingâ€¦' : 'Apply DLS Target' }}
                    </button>

                    <small class="hint" v-if="gameStore.dlsApplied">DLS target applied.</small>
                  </template>
                  <small class="hint" v-else>Preview to compute a DLS target based on current resources.</small>
                </div>
              </div>

              <!-- Reduce Overs -->
              <div ref="reduceOversCardRef" class="card dls-card" style="margin-top:12px;">
                <h4>Reduce Overs</h4>
                <div class="dls-grid">
                  <div class="row-inline" style="flex-wrap:wrap;">
                    <label class="lbl">Scope</label>
                    <label><input type="radio" value="match" v-model="reduceScope"> Match</label>
                    <label><input type="radio" value="innings" v-model="reduceScope"> Specific innings</label>

                    <select v-if="reduceScope==='innings'" v-model.number="reduceInnings" class="sel">
                      <option :value="1">Innings 1</option>
                      <option :value="2">Innings 2</option>
                    </select>
                  </div>

                  <div class="row-inline" style="flex-wrap:wrap;">
                    <label class="lbl">New limit</label>
                    <input class="inp" type="number" v-model.number="oversNew" min="1" step="1" style="width:90px;">
                    <small class="hint">Current limit: {{ oversLimit || 'â€”' }} overs</small>
                  </div>

                  <button class="btn btn-primary" :disabled="!canReduce || reducingOvers" @click="doReduceOvers">
                    {{ reducingOvers ? 'Updatingâ€¦' : 'Apply Overs Limit' }}
                  </button>
                </div>
              </div>

              <!-- Live Par helper -->
              <div class="card dls-card" style="margin-top:12px;">
                <h4>DLS â€” Par Now</h4>
                <div class="dls-grid">
                  <button class="btn" :disabled="computingPar" @click="updateParNow">
                    {{ computingPar ? 'Computingâ€¦' : 'Update Live Par' }}
                  </button>
                  <small class="hint" v-if="(gameStore.dlsPanel as any)?.par != null">
                    Par: {{ (gameStore.dlsPanel as any).par }}
                  </small>
                  <small class="hint" v-else>Par will appear here once computed.</small>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- Share & Monetize Modal -->
    <div v-if="shareOpen" class="backdrop" @click.self="closeShare" role="dialog" aria-modal="true" aria-labelledby="share-title">
      <div class="modal">
        <header class="modal-hdr">
          <h3 id="share-title">Share & Monetize</h3>
          <button class="x" @click="closeShare" aria-label="Close modal">âœ•</button>
        </header>

        <section class="modal-body">
          <div class="row">
            <label class="lbl">Embed code (read-only)</label>
            <div class="code-wrap">
              <textarea ref="codeRef" class="code" readonly :value="iframeCode" aria-label="Embed iframe HTML"></textarea>
              <button class="copy" @click="copyEmbed">{{ copied ? 'Copied!' : 'Copy' }}</button>
            </div>
          </div>

          <div class="row grid two">
            <div>
              <label class="lbl">Preview URL</label>
              <input class="inp wide" :value="embedUrl" readonly @focus="(e) => (e.target as HTMLInputElement | null)?.select()" />
            </div>
            <div class="align-end">
              <a class="btn btn-ghost" :href="embedUrl" target="_blank" rel="noopener">Open preview</a>
            </div>
          </div>

          <div class="note">
            <strong>Tip (TV/OBS):</strong> Add a <em>Browser Source</em> with the iframeâ€™s
            <code>src</code> URL (or paste this embed into a simple HTML file). Set width to your canvas,
            height â‰ˆ <b>{{ height }}</b> px, and enable transparency if you want rounded corners to blend.
          </div>
        </section>

        <footer class="modal-ftr">
          <div class="spacer"></div>
          <button class="btn btn-primary" @click="copyEmbed">{{ copied ? 'Copied!' : 'Copy embed' }}</button>
        </footer>
      </div>
    </div>

    <!-- Start Over Modal -->
    <dialog ref="startOverDlg">
      <form method="dialog" class="dlg">
        <h3>Start next over</h3>
        <p>Select a bowler (cannot be the bowler who delivered the last ball of previous over).</p>
        <select v-model="selectedNextOverBowlerId" class="sel">
          <option disabled value="">Choose bowlerâ€¦</option>
          <option v-for="p in eligibleNextOverBowlers" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <footer>
          <button type="button" class="btn" @click="closeStartOver">Cancel</button>
          <button type="button" class="btn btn-primary" :disabled="!selectedNextOverBowlerId" @click.prevent="confirmStartOver">Start</button>
        </footer>
      </form>
    </dialog>

    <!-- Start Next Innings Modal -->
    <dialog ref="startInningsDlg">
      <form method="dialog" class="dlg">
        <h3>Start next innings</h3>
        <p>Select openers and (optional) opening bowler.</p>

        <label class="lbl">Striker</label>
        <select v-model="nextStrikerId" class="sel">
          <option disabled value="">Choose strikerâ€¦</option>
          <option v-for="p in nextBattingXI" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>

        <label class="lbl">Non-striker</label>
        <select v-model="nextNonStrikerId" class="sel">
          <option disabled value="">Choose non-strikerâ€¦</option>
          <option v-for="p in nextBattingXI" :key="p.id" :value="p.id" :disabled="p.id === nextStrikerId">{{ p.name }}</option>
        </select>

        <label class="lbl">Opening bowler (optional)</label>
        <select v-model="openingBowlerId" class="sel">
          <option value="">â€” None (choose later) â€”</option>
          <option v-for="p in nextBowlingXI" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>

        <footer>
          <button type="button" class="btn" @click="closeStartInnings">Cancel</button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="!nextStrikerId || !nextNonStrikerId || nextStrikerId===nextNonStrikerId"
            @click.prevent="confirmStartInnings"
          >
            Start innings
          </button>
        </footer>
      </form>
    </dialog>

    <!-- Select Next Batter Modal (Gate) -->
    <dialog ref="selectBatterDlg">
      <form method="dialog" class="dlg">
        <h3>Select next batter</h3>
        <p>Pick a batter who is not out.</p>
        <select v-model="selectedNextBatterId" class="sel">
          <option disabled value="">Choose batterâ€¦</option>
          <option v-for="p in candidateBatters" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <footer>
          <button type="button" class="btn" @click="closeSelectBatter">Cancel</button>
          <button type="button" class="btn btn-primary" :disabled="!selectedNextBatterId" @click.prevent="confirmSelectBatter">Confirm</button>
        </footer>
      </form>
    </dialog>

    <!-- Weather Interruption Modal -->
    <dialog ref="weatherDlg">
      <form method="dialog" class="dlg">
        <h3>Weather interruption</h3>
        <p>Add an optional note (e.g., â€œRain, covers onâ€).</p>
        <input class="inp" v-model="weatherNote" placeholder="Note (optional)" />
        <footer>
          <button type="button" class="btn" @click="closeWeather">Close</button>
          <button type="button" class="btn" @click.prevent="resumeAfterWeather">Resume play</button>
          <button type="button" class="btn btn-primary" @click.prevent="startWeatherDelay">Start delay</button>
          <button class="btn" :disabled="needsNewInningsLive || !canStartOverNow" @click="openStartOver">Start Next Over</button>
        </footer>
      </form>
    </dialog>

    <!-- Mid-over Change Modal -->
    <dialog ref="changeBowlerDlg">
      <form method="dialog" class="dlg">
        <h3>Mid-over change (injury)</h3>
        <p>Pick a replacement to finish this over. You can do this only once per over.</p>
        <select v-model="selectedReplacementBowlerId" class="sel">
          <option disabled value="">Choose replacementâ€¦</option>
          <option v-for="p in replacementOptions" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <footer>
          <button type="button" class="btn" @click="closeChangeBowler">Cancel</button>
          <button type="button" class="btn btn-primary" :disabled="!selectedReplacementBowlerId" @click.prevent="confirmChangeBowler">Change</button>
          <button class="btn" :disabled="needsNewInningsLive || !canUseMidOverChange" @click="openChangeBowler">Mid-over Change</button>
        </footer>
      </form>
    </dialog>
  </div>
</template>

<style scoped>
/* Layout */
.game-scoring { padding: 12px; display: grid; gap: 12px; }
.toolbar { display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,.08); }
.left { display: flex; align-items: baseline; gap: 10px; }
.title { margin: 0; font-size: 18px; font-weight: 800; letter-spacing: .01em; }
.meta { font-size: 12px; color: #6b7280; }
.right { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }

.content { padding: 8px 0; }
.mb-3 { margin-bottom: 12px; }
.placeholder { padding: 16px; border: 1px dashed rgba(0,0,0,.2); border-radius: 12px; color: #6b7280; background: rgba(0,0,0,.02); }
.dev-debug { background: #111827; color: #e5e7eb; padding: 8px; border-radius: 8px; font-size: 12px; white-space: pre-wrap; margin: 8px 0; }

/* Controls */
.inp, .sel { height: 34px; border-radius: 10px; border: 1px solid #e5e7eb; padding: 0 10px; font-size: 14px; background: #fff; color: #111827; }
.inp.wide { width: 100%; }
.btn { appearance: none; border-radius: 10px; padding: 8px 12px; font-weight: 700; font-size: 14px; cursor: pointer; }
.btn-primary { border: 0; background: #22d3ee; color: #0b0f1a; }
.btn-ghost { border: 1px solid #e5e7eb; background: #fff; color: #111827; text-decoration: none; }

/* Bowling controls block */
.card.alt { background: rgba(0,0,0,.03); border: 1px solid rgba(0,0,0,.08); border-radius: 12px; padding: 10px; }
.row.tight { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 8px; align-items: center; }
.bowler-now { font-size: 14px; color: #111827; }

/* Selectors */
.selectors.card { border: 1px solid rgba(0,0,0,.08); border-radius: 12px; padding: 12px; }
.row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.col { display: grid; gap: 6px; }
.align-end { display: grid; align-items: end; }
.lbl { font-size: 12px; color: #6b7280; }
.hint { font-size: 11px; color: #9ca3af; }
.debug { margin-top: 8px; font-size: 12px; color: #6b7280; }

/* Live strip */
.live-strip { display: grid; grid-template-columns: 1fr 2fr 1fr; gap: 12px; align-items: center; margin: 12px 0; }
.score { font-size: 20px; }
.batters { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.batter, .bowler { display: flex; flex-direction: column; gap: 2px; }

/* Two-column shell with a wider right column */
.layout-2col {
  display: grid;
  grid-template-columns: minmax(620px, 1.65fr) minmax(440px, 1fr);
  gap: 12px;
}
.layout-2col .left,
.layout-2col .right { display: block; }

/* Keep the right column visible while scrolling */
.layout-2col .right { position: sticky; top: 12px; align-self: start; }

/* Scorecards: 2-up (Batting | Bowling), Extras spans full width */
.scorecards-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  align-items: start;
}
.scorecards-grid .extras-card { grid-column: 1 / -1; }

/* Slightly larger type & padding in nested tables/components */
.scorecards-grid :deep(table) { font-size: 13px; }
.scorecards-grid :deep(th),
.scorecards-grid :deep(td) { padding: 6px 8px; }
.scorecards-grid :deep(.card),
.scorecards-grid :deep(.pane) { padding: 14px; }

/* Extras & DLS polish */
.extras-card {
  padding: 12px;
  border: 1px solid rgba(0,0,0,.08);
  border-radius: 12px;
}
.extras-card h4 { margin: 0 0 8px; font-size: 14px; }
.extras-grid {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 6px;
  font-size: 13px;
}
.extras-grid .sep {
  border-top: 1px solid rgba(0,0,0,.08);
  margin-top: 4px; padding-top: 4px;
}
.scorecards-grid > * { align-self: start; }
.scorecards-grid .card, .scorecards-grid .extras-card { height: 100%; }

.subs-card {
  padding: 12px;
  border: 1px solid rgba(0,0,0,.08);
  border-radius: 12px;
}
.subs-card h4 { margin: 0; font-size: 14px; }
.subs-hdr {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px;
}
.subs-hdr .count {
  font-size: 12px; color: #6b7280;
}
.subs-list {
  list-style: none; padding: 0; margin: 0;
  display: grid; gap: 6px;
}
.subs-row {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 13px; padding: 4px 0;
  border-bottom: 1px dashed rgba(0,0,0,.06);
}
.subs-row:last-child { border-bottom: 0; }
.subs-row .name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.chip {
  font-size: 10px; font-weight: 700; letter-spacing: .02em;
  padding: 2px 6px; border-radius: 999px;
  border: 1px solid rgba(0,0,0,.12);
  background: rgba(0,0,0,.04); color: #374151;
}
.subs-card .empty { padding: 6px 0; }

/* Light mode polish */
@media (prefers-color-scheme: light) {
  .chip { border-color: #e5e7eb; background: #f3f4f6; color: #374151; }
}

.dls-card {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid rgba(0,0,0,.08);
  border-radius: 12px;
}
.dls-card h4 { margin: 0 0 8px; font-size: 14px; }
.dls-grid { display: grid; gap: 8px; font-size: 13px; }
.row-inline { display: flex; gap: 8px; align-items: center; }
.dls-stats {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 6px;
}

/* Compact metrics row */
.small-metrics .row.compact {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}
.small-metrics .col { align-items: center; grid-auto-flow: column; grid-auto-columns: max-content; gap: 8px; }

/* Responsive */
@media (max-width: 1200px) {
  .layout-2col { grid-template-columns: 1.4fr 1fr; }
}
@media (max-width: 1100px) {
  .scorecards-grid { grid-template-columns: 1fr; }
}
@media (max-width: 900px) {
  .layout-2col { grid-template-columns: 1fr; } /* stack on small screens */
  .layout-2col .right { position: static; } /* disable sticky when stacked */
}

/* Modal overlay (Share) */
.backdrop { position: fixed; inset: 0; background: rgba(0,0,0,.45); display: grid; place-items: center; padding: 16px; z-index: 60; }
.modal { width: min(760px, 96vw); background: #0b0f1a; color: #e5e7eb; border-radius: 16px; box-shadow: 0 20px 50px rgba(0,0,0,.5); overflow: hidden; }
.modal-hdr, .modal-ftr { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.modal-hdr { padding: 14px 16px; border-bottom: 1px solid rgba(255,255,255,.06); }
.modal-ftr { padding: 12px 16px; border-top: 1px solid rgba(255,255,255,.06); }
.modal-hdr h3 { margin: 0; font-size: 16px; letter-spacing: .01em; }
.x { background: transparent; border: 0; color: #9ca3af; font-size: 18px; cursor: pointer; }
.modal-body { padding: 14px 16px; display: grid; gap: 12px; }
.code-wrap { position: relative; }
.code { width: 100%; min-height: 120px; resize: vertical; background: #0f172a; color: #e5e7eb; border: 1px solid rgba(255,255,255,.08); border-radius: 12px; padding: 12px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; line-height: 1.4; }
.copy { position: absolute; top: 8px; right: 8px; border: 1px solid rgba(255,255,255,.12); background: rgba(255,255,255,.06); color: #e5e7eb; border-radius: 10px; padding: 6px 10px; font-size: 12px; cursor: pointer; }

/* Light mode polish */
@media (prefers-color-scheme: light) {
  .toolbar { border-bottom-color: #e5e7eb; }
  .placeholder { border-color: #e5e7eb; background: #ffffff; }
  .inp, .sel { background: #fff; color: #111827; border-color: #e5e7eb; }
  .btn-ghost { background: #fff; color: #111827; border-color: #e5e7eb; }
  .modal { background: #ffffff; color: #111827; }
  .modal-hdr { border-bottom-color: #e5e7eb; }
  .modal-ftr { border-top-color: #e5e7eb; }
  .x { color: #6b7280; }
  .code { background: #f9fafb; color: #111827; border-color: #e5e7eb; }
}

/* Dialog (native) */
dialog::backdrop { background: rgba(0,0,0,0.2); }
dialog .dlg { display: flex; flex-direction: column; gap: 10px; min-width: 320px; }
dialog footer { display: flex; justify-content: flex-end; gap: 8px; }
</style>



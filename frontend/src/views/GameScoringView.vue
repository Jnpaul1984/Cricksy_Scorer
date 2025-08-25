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
}

// ================== Single-panel state ==================
type ExtraOpt = 'none' | 'nb' | 'wd' | 'b' | 'lb'
const extra = ref<ExtraOpt>('none')
const offBat = ref<number>(0)      // used for legal + nb
const extraRuns = ref<number>(1)   // used for wd (≥1) and b/lb (≥0)
const isWicket = ref(false)
const dismissal = ref<string | null>(null)
const dismissedId = ref<string | null>(null)
// --- Fielder (XI + subs) for wicket events ---
const selectedFielderId = ref<UUID>('' as UUID)

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

const route = useRoute()
const router = useRouter()
const gameStore = useGameStore()

// Reactive refs from the store
const { canScore, liveSnapshot } = storeToRefs(gameStore)
const { needsNewBatter, needsNewOver } = storeToRefs(gameStore)
const { extrasBreakdown } = storeToRefs(gameStore)
const { dlsKind } = storeToRefs(gameStore)

// Current gameId (param or ?id=)
const gameId = computed<string>(() => (route.params.gameId as string) || (route.query.id as string) || '')

const canSubmitSimple = computed(() => {
  if (!gameId.value || needsNewOverLive.value || needsNewBatterLive.value) return false
  if (!selectedStriker.value || !selectedNonStriker.value || !selectedBowler.value) return false

  // If it's a wicket that needs a fielder, require one
  if (isWicket.value && needsFielder.value && !selectedFielderId.value) return false

  if (extra.value === 'nb') return offBat.value >= 0
  if (extra.value === 'wd') return extraRuns.value >= 1
  if (extra.value === 'b' || extra.value === 'lb') return extraRuns.value >= 0
  return offBat.value >= 0 // legal
})


async function submitSimple() {
  if (needsNewOverLive.value)  { openStartOver();   onError('Start the next over first'); return }
  if (needsNewBatterLive.value){ openSelectBatter(); onError('Select the next batter first'); return }

  try {
    if (isWicket.value) {
      await gameStore.scoreWicket(
        gameId.value,
        (dismissal.value || 'bowled'),
        (dismissedId.value || undefined),
        undefined, // commentary (optional)
        (needsFielder.value ? (selectedFielderId.value || undefined) : undefined)
      )
    } else if (extra.value === 'nb') {
      await gameStore.scoreExtra(gameId.value, 'nb', offBat.value)
    } else if (extra.value === 'wd') {
      await gameStore.scoreExtra(gameId.value, 'wd', extraRuns.value)
    } else if (extra.value === 'b' || extra.value === 'lb') {
      await gameStore.scoreExtra(gameId.value, extra.value, extraRuns.value)
    } else {
      await gameStore.scoreRuns(gameId.value, offBat.value)
    }

    // Reset panel
    extra.value = 'none'
    offBat.value = 0
    extraRuns.value = 1
    isWicket.value = false
    dismissal.value = null
    dismissedId.value = null
    selectedFielderId.value = '' as UUID   // ✅ clear fielder
    onScored()
  } catch (e: any) {
    onError(e?.message || 'Scoring failed')
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
const selectedStriker = computed<UUID>({
  get: () => (gameStore.uiState.selectedStrikerId || '') as UUID,
  set: (v) => gameStore.setSelectedStriker(v || null),
})
const selectedNonStriker = computed<UUID>({
  get: () => (gameStore.uiState.selectedNonStrikerId || '') as UUID,
  set: (v) => gameStore.setSelectedNonStriker(v || null),
})
const selectedBowler = computed<UUID>({
  get: () => (gameStore.uiState.selectedBowlerId || '') as UUID,
  set: (v) => gameStore.setSelectedBowler(v || null),
})

// ================== CONNECTION / OFFLINE QUEUE ==================
const liveReady = computed<boolean>(() => gameStore.connectionStatus === 'connected')
const pendingForThisGame = computed(() => gameStore.offlineQueue.filter(q => q.gameId === gameId.value && q.status !== 'flushing'))
const pendingCount = computed<number>(() => pendingForThisGame.value.length)


// ================== ROSTERS (FILTERED BY XI) ==================


// Names for status text
const selectedStrikerName = computed<string>(() => battingPlayers.value.find((p) => p.id === selectedStriker.value)?.name || '')
const selectedBowlerName = computed<string>(() => bowlingPlayers.value.find((p) => p.id === selectedBowler.value)?.name || '')
const {
  battingRosterXI,
  bowlingRosterXI,
  fieldingSubs,        // handy for a fielder dropdown when scoring wickets
  fielderRosterAll,    // (optional) if you want XI + subs together
} = storeToRefs(gameStore)

// selectors:
const battingPlayers = computed(() => battingRosterXI.value)
const bowlingPlayers = computed(() => bowlingRosterXI.value)
const fielderOptions = computed(() => [
  ...bowlingRosterXI.value,     // XI
  ...fieldingSubs.value,        // subs
])
// ================== SCORECARDS (from store) ==================
const battingEntries = computed(() =>
  battingPlayers.value.map((r: any) => ({
    player_id: r.id,
    player_name: String(r.name),
    runs: Number(r.runs),
    balls_faced: Number(r.balls),
    fours: Number(r.fours),
    sixes: Number(r.sixes),
    strike_rate: Number(r.sr),
    how_out: r.howOut,
    is_out: Boolean(r.isOut),
  }))
)

const bowlingEntries = computed(() =>
  bowlingPlayers.value.map((r: any) => ({
    player_id: r.id,
    player_name: String(r.name),
    // ⚠️ r.overs is a string like "3.2" from the store; don't Number() it or you'll get NaN.
    // If BowlingCard expects a string, pass r.overs. If it expects balls, convert:
    // overs_bowled: Math.round(oversNotationToFloat(r.overs) * 6)
    overs_bowled: r.overs,               // or convert to balls if your card needs a number
    maidens: Number(r.maidens),
    runs_conceded: Number(r.runs),
    wickets_taken: Number(r.wkts),
    economy: typeof r.econ === 'number' ? r.econ : 0,
  }))
)

// ================== Deliveries (DEDUPE) ==================
function makeKey(d: any): string {
  const o  = Number(d.over_number ?? d.over ?? 0)
  const b  = Number(d.ball_number ?? d.ball ?? 0)
  const s  = String(d.striker_id ?? '')
  const bw = String(d.bowler_id ?? '')
  const rs = Number(d.runs_scored ?? d.runs ?? 0)
  const ex = String(d.extra ?? d.extra_type ?? '')
  return `${o}:${b}:${s}:${bw}:${rs}:${ex}`
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
      striker_id: String(d.striker_id ?? ''),
      non_striker_id: String(d.non_striker_id ?? ''),
      bowler_id: String(d.bowler_id ?? ''),
      extra: d.extra as DeliveryRowForTable['extra'] | undefined,
      is_wicket: Boolean(d.is_wicket),
      commentary: d.commentary as string | undefined,
      dismissed_player_id: (d.dismissed_player_id ? String(d.dismissed_player_id) : null) as UUID | null,
      at_utc: d.at_utc as string | undefined,
    }
  }).sort((a, b) => (a.over_number - b.over_number) || (a.ball_number - b.ball_number))
})

// Name lookup for DeliveryTable
function playerNameById(id?: UUID | null): string {
  if (!id) return ''
  const g = gameStore.currentGame as unknown as { team_a: Team; team_b: Team } | null
  if (!g) return ''
  return (
    g.team_a.players.find(p => p.id === id)?.name ??
    g.team_b.players.find(p => p.id === id)?.name ??
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
  if (!ballsBowled) return '—'
  const overs = ballsBowled / 6
  return (runsConceded / overs).toFixed(2)
}

const cantScoreReasons = computed(() => {
  const rs:string[] = []
  if (!gameStore.currentGame) rs.push('No game loaded')
  else if (!['in_progress','live','started'].includes(String((gameStore.currentGame as any).status || '')))
    rs.push(`Game is ${(gameStore.currentGame as any).status}`)

  if (!selectedStriker.value) rs.push('Select striker')
  if (!selectedNonStriker.value) rs.push('Select non-striker')
  if (selectedStriker.value && selectedStriker.value === selectedNonStriker.value)
    rs.push('Striker and non-striker cannot be the same')

  if (!currentBowlerId.value) rs.push('Start next over / choose bowler')
  if (!selectedBowler.value) rs.push('Choose bowler')
  if (needsNewOver.value) rs.push('Start next over')
  if (needsNewBatter.value) rs.push('Select next batter')

  return rs
})

function clearQueuedDeliveriesForThisGame(): void {
  const id = gameId.value
  if (!id) return
  ;(gameStore as any).offlineQueue = (gameStore as any).offlineQueue.filter((q: any) => q.gameId !== id)
  console.info('Cleared offlineQueue for game', id)
}

// ================== Live strip data (current bowler / over) ==================
const stateAny = computed(() => gameStore.state as any)
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
  const sAny = (gameStore as any).bowlingStatsByPlayer as Record<string, { runsConceded: number; balls: number }> | undefined
  const s = sAny?.[id]
  if (s) return { runs: Number(s.runsConceded), balls: Number(s.balls) }
  const filtered = dedupedDeliveries.value.filter(d => d.bowler_id === id)
  const runs = filtered.reduce((a, d) => a + Number(d.runs_scored || 0) + (d.extra && (d.extra === 'wd' || d.extra === 'nb') ? 1 : 0), 0)
  const isLegal = (d: DeliveryRowForTable) => !d.extra || d.extra === 'b' || d.extra === 'lb'
  const balls = filtered.filter(isLegal).length
  return { runs, balls }
})

const oversDisplay = computed<string>(() => {
  const totalBalls = Number((stateAny.value?.balls_bowled_total ?? 0))
  if (totalBalls > 0) {
    const ov = Math.floor(totalBalls / 6)
    const rem = totalBalls % 6
    return `${ov}.${rem}`
  }
  const legal = dedupedDeliveries.value.filter(d => !d.extra || d.extra === 'lb' || d.extra === 'b').length
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
function onScored(): void { showToast(pendingCount.value > 0 ? 'Saved (queued) ✓' : 'Saved ✓', 'success') }
function onError(message: string): void { showToast(message || 'Something went wrong', 'error', 3000) }

// ================== Lifecycle ==================
onMounted(async () => {
  const id = gameId.value
  if (!id) { void router.replace('/'); return }

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

// Keep UI batters in lockstep with server
function syncBattersFromSnapshot(snap: any): void {
  if (!snap) return
  const sId  = snap.current_striker_id ?? snap?.batsmen?.striker?.id ?? ''
  const nsId = snap.current_non_striker_id ?? snap?.batsmen?.non_striker?.id ?? ''
  if (sId && sId !== selectedStriker.value)       selectedStriker.value = sId as UUID
  if (nsId && nsId !== selectedNonStriker.value)  selectedNonStriker.value = nsId as UUID
}
watch(liveSnapshot, (snap) => syncBattersFromSnapshot(snap))

// Keep selections valid when innings flips or XI loads
watch(currentBowlerId, (id) => { selectedBowler.value = id ? (id as UUID) : '' as unknown as UUID })
watch([bowlingPlayers, xiLoaded, currentBowlerId], () => {
  const id = selectedBowler.value
  if (id && !bowlingPlayers.value.some(p => p.id === id) && id !== currentBowlerId.value) selectedBowler.value = '' as unknown as UUID
})
watch(needsNewBatterLive, (v) => { if (v) openSelectBatter() })
watch(needsNewOverLive, (v) => {
  if (v) {
    selectedBowler.value = '' as unknown as UUID
    selectedNextOverBowlerId.value = '' as unknown as UUID
    openStartOver()
  }
})

// Reconnect + flush controls
function reconnect(): void {
  const id = gameId.value
  if (!id) return
  try {
    gameStore.initLive(id)
    showToast('Reconnecting…', 'info')
  } catch {
    showToast('Reconnect failed', 'error', 2500)
  }
}
function flushNow(): void {
  const id = gameId.value
  if (!id) return
  gameStore.flushQueue(id)
  showToast('Flushing queue…', 'info')
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
  const batter = selectedNextBatterId.value
  if (!batter) return
  await gameStore.replaceBatter(selectedNextBatterId.value)
  const last: any =
    liveSnapshot.value?.last_delivery ??
    (gameStore.currentGame as any)?.deliveries?.slice(-1)?.[0]
  if (last) {
    const dismissed = (last.dismissed_player_id || '') as UUID
    if (dismissed && selectedStriker.value === dismissed)          selectedStriker.value = batter
    else if (dismissed && selectedNonStriker.value === dismissed)  selectedNonStriker.value = batter
    else if (!selectedStriker.value)                               selectedStriker.value = batter
    else if (!selectedNonStriker.value)                            selectedNonStriker.value = batter
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
      <!-- Live scoreboard preview — widget reads from store; interruptions polling disabled -->
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

      <!-- Player selectors -->
      <section class="selectors card" style="border:1px solid rgba(0,0,0,.08); border-radius:12px; padding:12px; margin-bottom:12px;">
        <h3 style="margin:0 0 8px; font-size:14px;">Players</h3>
        <div class="row">
          <div class="col">
            <label class="lbl">Striker</label>
            <select v-model="selectedStriker" class="sel" aria-label="Select striker">
              <option disabled value="">Choose striker…</option>
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
              <option disabled value="">Choose non-striker…</option>
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
            <select v-model="selectedBowler" class="sel" aria-label="Select bowler" :disabled="needsNewOverLive">
              <option disabled value="">Choose bowler…</option>
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
            <button class="btn" :disabled="!canStartOverNow" @click="openStartOver">
              Start Next Over
            </button>
            <small class="hint">
              {{ !currentBowlerId ? 'No active bowler yet — start the over.' : 'Disables previous over’s last bowler.' }}
            </small>
          </div>
          <div class="col">
            <button class="btn" :disabled="!canUseMidOverChange" @click="openChangeBowler">Mid-over Change</button>
            <small class="hint">Allowed once per over (injury).</small>
          </div>
          <div class="col bowler-now" v-if="currentBowler">
            <strong>Current:</strong> {{ currentBowler.name }} ·
            <span>{{ oversDisplayFromBalls(currentBowlerStats.balls) }}-{{ currentBowlerStats.runs }}</span>
            <span> · Econ {{ econ(currentBowlerStats.runs, currentBowlerStats.balls) }}</span>
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
            <button class="btn" @click="jumpToReduceOvers">Reduce overs…</button>
            <small class="hint">Adjust match or innings limit.</small>
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
      <div v-if="needsNewBatterLive || needsNewOverLive" class="placeholder mb-3" role="status" aria-live="polite">
        <div v-if="needsNewBatterLive">New batter required. <button class="btn btn-ghost" @click="openSelectBatter">Select next batter</button></div>
        <div v-if="needsNewOverLive">New over required. <button class="btn btn-ghost" @click="openStartOver">Choose bowler</button></div>
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
              <span>Extras:</span>
              <button v-for="r in (extra==='wd' ? [1,2,3,4,5] : [0,1,2,3,4])" :key="r" class="btn" :class="extraRuns===r && 'btn-primary'" @click="extraRuns=r">{{ r }}</button>
            </div>
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
            <option disabled value="">Select fielder…</option>
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

          <input v-if="isWicket" v-model="dismissedId" placeholder="Dismissed player id" class="inp" />
        </div>

          <!-- Submit -->
          <div class="col" style="display:flex; gap:8px;">
            <button class="btn btn-primary" :disabled="!canSubmitSimple || !canScore" @click="submitSimple">
              Submit delivery
            </button>
            <small class="hint" v-if="!canScore">
              Select striker/non-striker/bowler and clear any “New over / New batter” prompts.
            </small>
          </div>
        </div>
      </section>

      <!-- Score pad + deliveries on the left; 3 cards side-by-side on the right -->
      <section class="mt-3 layout-2col">
        <div class="left">
          <DeliveryTable
            :deliveries="dedupedDeliveries"
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
                      {{ loadingDls ? 'Loading…' : 'Preview' }}
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
                      {{ applyingDls ? 'Applying…' : 'Apply DLS Target' }}
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
                    <small class="hint">Current limit: {{ oversLimit || '—' }} overs</small>
                  </div>

                  <button class="btn btn-primary" :disabled="!canReduce || reducingOvers" @click="doReduceOvers">
                    {{ reducingOvers ? 'Updating…' : 'Apply Overs Limit' }}
                  </button>
                </div>
              </div>

              <!-- Live Par helper -->
              <div class="card dls-card" style="margin-top:12px;">
                <h4>DLS — Par Now</h4>
                <div class="dls-grid">
                  <button class="btn" :disabled="computingPar" @click="updateParNow">
                    {{ computingPar ? 'Computing…' : 'Update Live Par' }}
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
          <button class="x" @click="closeShare" aria-label="Close modal">✕</button>
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
            <strong>Tip (TV/OBS):</strong> Add a <em>Browser Source</em> with the iframe’s
            <code>src</code> URL (or paste this embed into a simple HTML file). Set width to your canvas,
            height ≈ <b>{{ height }}</b> px, and enable transparency if you want rounded corners to blend.
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
          <option disabled value="">Choose bowler…</option>
          <option v-for="p in eligibleNextOverBowlers" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <footer>
          <button type="button" class="btn" @click="closeStartOver">Cancel</button>
          <button type="button" class="btn btn-primary" :disabled="!selectedNextOverBowlerId" @click.prevent="confirmStartOver">Start</button>
        </footer>
      </form>
    </dialog>

    <!-- Select Next Batter Modal (Gate) -->
    <dialog ref="selectBatterDlg">
      <form method="dialog" class="dlg">
        <h3>Select next batter</h3>
        <p>Pick a batter who is not out.</p>
        <select v-model="selectedNextBatterId" class="sel">
          <option disabled value="">Choose batter…</option>
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
        <p>Add an optional note (e.g., “Rain, covers on”).</p>
        <input class="inp" v-model="weatherNote" placeholder="Note (optional)" />
        <footer>
          <button type="button" class="btn" @click="closeWeather">Close</button>
          <button type="button" class="btn" @click.prevent="resumeAfterWeather">Resume play</button>
          <button type="button" class="btn btn-primary" @click.prevent="startWeatherDelay">Start delay</button>
        </footer>
      </form>
    </dialog>

    <!-- Mid-over Change Modal -->
    <dialog ref="changeBowlerDlg">
      <form method="dialog" class="dlg">
        <h3>Mid-over change (injury)</h3>
        <p>Pick a replacement to finish this over. You can do this only once per over.</p>
        <select v-model="selectedReplacementBowlerId" class="sel">
          <option disabled value="">Choose replacement…</option>
          <option v-for="p in replacementOptions" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <footer>
          <button type="button" class="btn" @click="closeChangeBowler">Cancel</button>
          <button type="button" class="btn btn-primary" :disabled="!selectedReplacementBowlerId" @click.prevent="confirmChangeBowler">Change</button>
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
.row.tight { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 8px; align-items: center; }
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

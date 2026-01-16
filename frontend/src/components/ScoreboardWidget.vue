<script setup lang="ts">
/* eslint-disable */
import { storeToRefs } from 'pinia'
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { RouterLink } from 'vue-router'

import { BaseButton, BaseCard, BaseBadge } from '@/components'
import { useHighlights, type Snapshot as HL } from '@/composables/useHighlights'
import { useRoleBadge } from '@/composables/useRoleBadge'
import { useGameStore } from '@/stores/gameStore'
import { isValidUUID } from '@/utils'
import { fmtSR, fmtEconomy, oversDisplayFromBalls, oversDisplayFromAny, deriveBowlerFigures } from '@/utils/cricket'
import WinProbabilityChart from '@/components/WinProbabilityChart.vue'
/* ------------------------------------------------------------------ */
/* Props                                                               */
/* ------------------------------------------------------------------ */
const props = withDefaults(defineProps<{
  gameId: string
  apiBase?: string
  theme?: 'dark' | 'light' | 'auto'
  title?: string
  logo?: string
  sponsorsUrl?: string
  interruptionsMode?: 'auto' | 'poll' | 'socket' | 'off'
  pollMs?: number
  canControl?: boolean
}>(), {
  apiBase: '',
  theme: 'dark',
  title: 'Live Scoreboard',
  interruptionsMode: 'auto',
  pollMs: 5000,
  canControl: false,
})

/* ---------------------------------- */
/* Store: single source of truth      */
/* ---------------------------------- */
const gameStore = useGameStore()
const {
  currentGame,
  error: storeError,
  dlsPanel,
  interruptions,
  currentInterruption,
  state,
  battingRowsXI,
  bowlingRowsXI,
  liveSnapshot,
  currentBowlerFigures: bowlerRow,
  isGameOver,
  resultText,
  currentPrediction,
} = storeToRefs(gameStore)

const { targetSafe, requiredRunRate, runsRequired, ballsBowledTotal } = storeToRefs(gameStore)

/* ---------------------- */
/* Bootstrapping (NEW)    */
/* ---------------------- */
let pollTimer: number | null = null
const ownsLive = ref(false)

async function startFeed() {
  console.log('[ScoreboardWidget] startFeed gameId:', props.gameId)
  // Ensure we have the game model to render names/score even before first event
  try {
    if (!currentGame.value || (currentGame.value as any).id !== props.gameId) {
      await gameStore.loadGame(props.gameId)
    }
  } catch {}

  if (props.interruptionsMode === 'off') {
    return
  }

  // Prefer sockets in 'socket' or 'auto'
  const wantSocket = props.interruptionsMode === 'socket' || props.interruptionsMode === 'auto'

  if (wantSocket) {
    try {
      if (gameStore.liveGameId !== props.gameId) {
        await gameStore.initLive(props.gameId)
        ownsLive.value = true
      }
    } catch {
      // ignore; we’ll fall back to polling below if in 'auto'
    }
  }

  // Always fetch once so the banner can show immediately
  try {
    console.log('[ScoreboardWidget] calling refreshInterruptions')
    await gameStore.refreshInterruptions()
  } catch {}

  // Poll if: explicitly 'poll' OR 'auto' but not connected
  const shouldPoll =
    props.interruptionsMode === 'poll' ||
    (props.interruptionsMode === 'auto' && gameStore.connectionStatus !== 'connected')

  if (shouldPoll) {
    stopPoll()
    pollTimer = window.setInterval(() => { void gameStore.refreshInterruptions() }, props.pollMs) as unknown as number
  }
}

function stopPoll() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

function teardown() {
  stopPoll()
  // Only stop the socket if *this* widget started it
  if (ownsLive.value) {
    gameStore.stopLive()
    ownsLive.value = false
  }
}

watch(() => props.gameId, async () => {
  teardown()
  await startFeed()
})

onMounted(() => { void startFeed() })
onUnmounted(() => teardown())

/* -------------------- */
/* Exposed to parent    */
/* -------------------- */
defineExpose({
  refreshInterruptions: () => gameStore.refreshInterruptions(),
})

/* ---------------------------------- */
/* Sponsors (robust parsing)          */
/* ---------------------------------- */
type SponsorLike =
  | string
  | {
      name?: string
      logoUrl?: string
      clickUrl?: string
      image_url?: string
      img?: string
      link_url?: string
      url?: string
      alt?: string
      rail?: 'left' | 'right' | 'badge'    // NEW: optional explicit placement
      maxPx?: number | string               // NEW: optional per-logo max size
      size?: number | string                // alias if you prefer
    }

const base = computed(() =>
  props.apiBase?.replace(/\/$/, '') || window.location.origin.replace(/\/$/, '')
)
const resolvedSponsorsUrl = computed(() =>
  props.sponsorsUrl || `${base.value}/games/${encodeURIComponent(props.gameId)}/sponsors`
)
const sponsorsBase = computed<URL | null>(() => {
  try { return new URL(resolvedSponsorsUrl.value, window.location.href) } catch { return null }
})
const sponsors = ref<SponsorLike[]>([])
const sponsorsLoading = ref(false)

function toAbsolute(url: string): string {
  if (!url) return ''
  if (/^(https?:)?\/\//i.test(url) || /^(data|blob):/i.test(url)) return url
  try { if (sponsorsBase.value) return new URL(url, sponsorsBase.value).toString() } catch {}
  const originBase = (props.apiBase?.replace(/\/$/, '') || window.location.origin.replace(/\/$/, ''))
  if (url.startsWith('/')) return `${originBase}${url}`.replace(/([^:]\/)\/+/g, '$1')
  if (url.startsWith('static/')) return `${originBase}/${url}`.replace(/([^:]\/)\/+/g, '$1')
  return url
}

const logoUrl = computed(() => toAbsolute(props.logo || ''))
const logoOk = ref(true)
function onLogoErr() { logoOk.value = false }

// --- helpers ---
function sponsorImg(s: SponsorLike): string {
  const raw = typeof s === 'string' ? s : (s.logoUrl || s.image_url || s.img || '')
  return toAbsolute(raw)
}
function sponsorHref(s: SponsorLike): string | undefined {
  const raw = typeof s === 'string' ? undefined : (s.clickUrl || s.link_url || s.url || undefined)
  return raw ? toAbsolute(raw) : undefined
}
function sponsorAlt(s: SponsorLike): string {
  if (typeof s === 'string') return 'Sponsor'
  return (s as any).alt || (s as any).name || 'Sponsor'
}

// NEW: read a per-item max size, fallback to the CSS default
function railMaxPx(s: SponsorLike | null, fallback = 72): string {
  if (!s || typeof s === 'string') return `${fallback}px`
  const raw = (s as any).maxPx ?? (s as any).size
  if (raw == null) return `${fallback}px`
  const n = typeof raw === 'string' ? parseInt(raw, 10) : Number(raw)
  return Number.isFinite(n) && n > 0 ? `${n}px` : `${fallback}px`
}

// --- choose left/right (explicit rail beats index order) ---
const leftSponsor = computed(() =>
  sponsors.value.find(s => typeof s !== 'string' && (s as any).rail === 'left')
  ?? sponsors.value?.[0] ?? null
)
const rightSponsor = computed(() =>
  sponsors.value.find(s => typeof s !== 'string' && (s as any).rail === 'right')
  ?? sponsors.value?.[1] ?? null
)
const badgeSponsor = computed(() =>
  sponsors.value.find(s => typeof s !== 'string' && (s as any).rail === 'badge')
  ?? sponsors.value?.[2] ?? sponsors.value?.[0] ?? null
)

// Accept {items:[]}, {sponsors:[]}, {data:[]}, or [] directly
function normalizeSponsors(raw: any): SponsorLike[] {
  const arr = Array.isArray(raw?.items) ? raw.items
    : Array.isArray(raw?.sponsors)     ? raw.sponsors
    : Array.isArray(raw?.data)         ? raw.data
    : Array.isArray(raw)               ? raw
    : []

  return arr
    .map((it: any) => {
      if (typeof it === 'string') return it
      const logo = it.logoUrl || it.image_url || it.img || it.logo || it.path || it.src
      const link = it.clickUrl || it.link_url || it.url
      const alt  = it.alt || it.name
      return { logoUrl: logo, clickUrl: link, alt }
    })
    .filter((it: SponsorLike) =>
      typeof it === 'string' ? true : Boolean((it as any).logoUrl))
}

async function loadSponsors() {
  sponsorsLoading.value = true
  try {
    const apiOrigin = base.value.replace(/\/$/, '')
    const raw = (resolvedSponsorsUrl.value || '').replace(/^\s+|\s+$/g, '')

    // Build candidates: user-provided first, then common mounts
    const candidates: string[] = []
    const absolutize = (p: string) =>
      /^https?:\/\//i.test(p) || p.startsWith('//')
        ? p
        : p.startsWith('/') ? `${apiOrigin}${p}` : `${apiOrigin}/${p}`

    if (raw) candidates.push(absolutize(raw))
    // helpful fallbacks for your setup
    candidates.push(
      `${apiOrigin}/sponsors/cricksy/sponsors.json`,
      `${apiOrigin}/cricksy/sponsors.json`,
      `${apiOrigin}/static/sponsors/cricksy/sponsors.json`
    )

    let lastErr: any = null
    for (const url of candidates) {
      try {
        console.info('[Sponsors] GET', url)
        const res = await fetch(url, { cache: 'no-store', mode: 'cors', headers: { Accept: 'application/json' } })
        const ct = res.headers.get('content-type') || ''
        if (!res.ok || !ct.includes('application/json')) {
          const preview = (await res.text()).slice(0, 200)
          console.warn('[Sponsors] skip', url, res.status, ct, preview)
          continue
        }
        const data = await res.json()
        const arr = normalizeSponsors(data)
        sponsors.value = arr
        console.info('[Sponsors] parsed', arr)
        return
      } catch (e) { lastErr = e }
    }

    console.error('[Sponsors] failed all candidates', lastErr)
    sponsors.value = []  // render without sponsors
  } finally {
    sponsorsLoading.value = false
  }
}
const teamA = computed<any>(() => (currentGame.value as any)?.team_a || {})
const teamB = computed<any>(() => (currentGame.value as any)?.team_b || {})

function bestTeamNameShape(t: any): string {
  return String(
    t?.name ?? t?.team_name ?? t?.short_name ?? t?.abbr ?? ''
  )
}

const teamAName = computed(() => bestTeamNameShape(teamA.value))
const teamBName = computed(() => bestTeamNameShape(teamB.value))
const teamAId   = computed(() => String(teamA.value?.id ?? ''))
const teamBId   = computed(() => String(teamB.value?.id ?? ''))

const currentInningNo = computed(() =>
  Number((currentGame.value as any)?.current_inning ?? 1)
)

const battingTeamId = computed(() =>
  String((currentGame.value as any)?.batting_team_id ?? '')
)

const battingTeamName = computed(() =>
  (currentGame.value as any)?.batting_team_name
  ?? (battingTeamId.value === teamAId.value ? teamAName.value
     : battingTeamId.value === teamBId.value ? teamBName.value
     : '')
)

const bowlingTeamName = computed(() =>
  (currentGame.value as any)?.bowlingTeamName
  ?? (currentGame.value as any)?.bowling_team_name
  ?? ''
)

// ✅ Deterministic: who played the FIRST innings?
const innings1TeamName = computed(() => {
  if (currentInningNo.value === 1) {
    // first innings still in progress
    return battingTeamName.value || teamAName.value || teamBName.value || ''
  }
  // second innings -> the other side batted first
  if (battingTeamId.value && teamAId.value && teamBId.value) {
    return battingTeamId.value === teamAId.value ? teamBName.value : teamAName.value
  }
  const bt = String((currentGame.value as any)?.batting_team_name || '')
  if (bt && bt === teamAName.value) return teamBName.value
  if (bt && bt === teamBName.value) return teamAName.value
  return ''
})



watch(resolvedSponsorsUrl, () => { void loadSponsors() })
onMounted(() => { void loadSponsors() })


/* ----------------- */
/* Small UI helpers  */
/* ----------------- */
function elapsedSince(iso?: string | null): string {
  if (!iso) return ''
  const start = new Date(iso).getTime()
  const ms = Math.max(0, Date.now() - start)
  const m = Math.floor(ms / 60000)
  const h = Math.floor(m / 60)
  const mm = m % 60
  return h ? `${h}h ${String(mm).padStart(2,'0')}m` : `${m}m`
}

/* ----------------------------- */
/* Derived scoreboard from store */
/* ----------------------------- */
const sAny = computed(() => (state.value || {}) as any)

// All deliveries (model or live state), newest last
const allDeliveries = computed<any[]>(() => {
  const fromState = Array.isArray((state.value as any)?.recent_deliveries)
    ? (state.value as any).recent_deliveries
    : []
  const fromModel = Array.isArray((currentGame.value as any)?.deliveries)
    ? (currentGame.value as any).deliveries
    : []
  const combined = fromModel.length ? [...fromModel, ...fromState] : fromState
  return combined.length ? dedupeByKey(combined) : []
})


// Prefer server’s total if present; else fall back to derived legal balls; else model counters.
const totalBallsThisInnings = computed(() =>
  deliveriesThisInnings.value.filter(isLegal).length
)


const oversText = computed(() => oversDisplayFromBalls(totalBallsThisInnings.value))

// Totals (prefer live state, then snapshot, then model)
const runs = computed(() =>
  Number(sAny.value?.total_runs ?? liveSnapshot.value?.total_runs ?? currentGame.value?.total_runs ?? 0)
)

const wkts = computed(() =>
  Number(sAny.value?.total_wickets ??
        liveSnapshot.value?.total_wickets ??
        currentGame.value?.total_wickets ?? 0)
)

// Rates now based on backend calculations (NO local fallback allowed)
const crr = computed(() => {
  // FIX B1: Use backend-calculated current_run_rate ONLY
  // Remove local fallback - if backend doesn't send it, show '—'
  const backendCrr = liveSnapshot.value?.current_run_rate
  return backendCrr != null ? backendCrr.toFixed(2) : '—'
})

// Show CRR only when backend provides it
const showCrr = computed(() => liveSnapshot.value?.current_run_rate != null)

const parTxt = computed(() => {
  const p = dlsPanel.value as any
  return typeof p?.par === 'number' ? String(p.par) : null
})

const targetDisplay = computed<number | null>(() => {
  const t = targetSafe?.value
  if (t == null || Number.isNaN(Number(t))) return null
  return Number(t)
})





function makeKey(d: any): string {
  // innings number (support multiple possible field names)
  const inn = Number(
    d.innings ?? d.inning ?? d.inning_no ?? d.innings_no ?? d.inning_number ?? 0
  )

  // normalize over & ball into integers: over=0.., ball=0..5
  const { over, ball } = parseOverBall(d)

  // include distinguishing payload so wides/no-balls don’t collapse into the legal ball
  const ex = String(d.extra ?? d.extra_type ?? '')                 // '', 'wd', 'nb', 'b', 'lb', ...
  const rb = Number(d.runs_off_bat ?? d.runs ?? 0)                 // off-bat runs (for nbs)
  const rs = Number(d.runs_scored ?? d.extra_runs ?? 0)            // total/extra runs
  const w  = d.is_wicket ? 1 : 0                                   // wicket flag

  // Only identical re-sends will produce the same key
  return `${inn}:${over}:${ball}:${ex}:${rb}:${rs}:${w}`
}


// ADD this helper right after makeKey
function dedupeByKey(arr: any[]) {
  const byKey = new Map<string, any>()
  for (const d of arr) byKey.set(makeKey(d), d)  // last write wins
  return Array.from(byKey.values())
}


const allDeliveriesRaw = computed<any[]>(() => allDeliveries.value)

// only this innings; if there are no innings markers at all, fall back to everything for innings 1, else empty


// helper: is the ball legal (consumes ball)
const isLegal = (d:any) => {
  const x = String(d.extra ?? d.extra_type ?? '')
  return x !== 'wd' && x !== 'nb'
}

function parseOversNotation(s?: string | number | null) {
  // Accept "13.3" or 13.3; clamp balls 0..5
  if (s == null) return { oc: 0, ob: 0 }
  const str = String(s)
  const [o, b] = str.split('.')
  const oc = Number(o) || 0
  let ob = Number(b) || 0
  if (ob < 0) ob = 0
  if (ob > 5) ob = 5
  return { oc, ob }
}

const overStr = computed(() =>
  // Prefer canonical "overs" (e.g., "13.3"); fallback to completed+this_over
  (currentGame.value as any)?.overs ??
  `${(currentGame.value as any)?.overs_completed ?? 0}.${(currentGame.value as any)?.balls_this_over ?? 0}`
)

const ocob = computed(() => parseOversNotation(overStr.value))
const oversC = computed(() => ocob.value.oc)
const ballsO = computed(() => ocob.value.ob)
const ballsBowled = computed(() => totalBallsThisInnings.value)



const legalBallsThisOver = computed(() => {
  if (!deliveriesThisInnings.value.length) return 0
  const lastOver = Math.max(...deliveriesThisInnings.value.map(d => {
    const o = d.over_number ?? d.over
    return typeof o === 'number' ? Math.floor(o) : Number(String(o).split('.')[0] || 0)
  }))
  return deliveriesThisInnings.value.filter(d => {
    const o = d.over_number ?? d.over
    const over = typeof o === 'number' ? Math.floor(o) : Number(String(o).split('.')[0] || 0)
    return over === lastOver && isLegal(d)
  }).length % 6
})

// If the server ever omits "overs", uncomment the next line to force fallback:
// const ballsO = computed(() => overStr.value ? ocob.value.ob : legalBallsThisOver.value)






const oversLimit = computed(() => Number((currentGame.value as any)?.overs_limit ?? 0))
const target = computed<number | null>(() => (currentGame.value?.target ?? null) as number | null)
const isSecondInnings = computed(() => Number(currentGame.value?.current_inning ?? 1) === 2)

// Chase mode: second innings with a valid target set
const isChase = computed(() => isSecondInnings.value && targetSafe.value != null && targetSafe.value > 0)

// RRR: prefer store value, fallback to local calculation
const rrr = computed(() => {
  // Use store's requiredRunRate if available
  if (requiredRunRate.value != null && Number.isFinite(requiredRunRate.value)) {
    return requiredRunRate.value.toFixed(2)
  }
  // Fallback to local calculation
  if (!isSecondInnings.value || target.value == null) return null
  const need = Math.max(0, target.value - runs.value)
  if (!oversLimit.value) return null
  const remBalls = Math.max(0, oversLimit.value * 6 - totalBallsThisInnings.value)
  if (remBalls <= 0) return null
  return (need / (remBalls / 6)).toFixed(2)
})

const oversLeft = computed(() => {
  if (!oversLimit.value) return null
  const rem = Math.max(0, oversLimit.value * 6 - totalBallsThisInnings.value)
  return rem > 0 ? oversDisplayFromBalls(rem) : null
})

// --- First-innings summary (derive from deliveries if innings markers exist)
function inningsOf(d: any): number | null {
  const v = Number(
    d.innings ?? d.inning ?? d.inning_no ?? d.innings_no ?? d.inning_number
  )
  return Number.isFinite(v) ? v : null
}


const currentInningsNo = computed(() => Number(currentGame.value?.current_inning ?? 1))
const deliveriesThisInnings = computed(() =>
  hasInningsMarkers.value
    ? allDeliveries.value.filter(d => Number(inningsOf(d)) === currentInningsNo.value)
    : allDeliveries.value // old data with no innings markers
)

// Derived, per-bowler figures (runs/balls/maidens/overs/econ) for *this innings*
const figuresByBowler = computed<Record<string, ReturnType<typeof deriveBowlerFigures>>>(() => {
  const map: Record<string, ReturnType<typeof deriveBowlerFigures>> = {}
  // collect unique bowler ids seen in this innings
  const ids = Array.from(
    new Set(
      deliveriesThisInnings.value
        .map(d => String(d.bowler_id ?? ''))
        .filter(Boolean)
    )
  )
  for (const id of ids) {
    map[id] = deriveBowlerFigures(deliveriesThisInnings.value as any, id)
  }
  return map
})

const legalBallsThisInningsDerived = computed(() =>
  deliveriesThisInnings.value.filter(d => {
    const ex = String(d.extra ?? d.extra_type ?? '')
    return ex !== 'wd' && ex !== 'nb'
  }).length
)

const hasInningsMarkers = computed(() =>
  allDeliveriesRaw.value.some(d => inningsOf(d) != null)
)

// De-dupe first-innings feed so the last ball isn't double-counted
const innings1Deliveries = computed(() =>
  hasInningsMarkers.value
    ? dedupeByKey(allDeliveriesRaw.value.filter(d => inningsOf(d) === 1))
    : []
)



// Total runs for one delivery (robust across legal+extras)
function totalRunsOf(d: any): number {
  const ex = String(d.extra ?? d.extra_type ?? '')
  const rb = Number(d.runs_off_bat ?? d.runs ?? 0)     // off the bat
  const rs = Number(d.runs_scored ?? d.extra_runs ?? 0) // backend "total" if present
  if (ex === 'wd') return rs || Math.max(1, Number(d.extra_runs ?? 1))
  if (ex === 'nb') return (rs || 0) || (1 + rb)        // prefer rs if provided
  if (ex === 'b' || ex === 'lb') return rs || Number(d.extra_runs ?? 0)
  return rs || rb                                      // legal: off bat (or total)
}

// Balls = legal only (wides/no-balls don't consume a ball)
const innings1 = computed<null | { runs: number; wkts: number; balls: number }>(() => {
  if (!innings1Deliveries.value.length) return null
  const legal = (d: any) => {
    const ex = String(d.extra ?? d.extra_type ?? '')
    return ex !== 'wd' && ex !== 'nb'
  }
  const balls = innings1Deliveries.value.filter(legal).length
  const runs  = innings1Deliveries.value.reduce((s, d) => s + totalRunsOf(d), 0)
  const wkts  = innings1Deliveries.value.filter(d => Boolean(d.is_wicket)).length
  return { runs, wkts, balls }
})

const innings1Line = computed<string | null>(() => {
  const snap = liveSnapshot.value

  // If we're in innings 2 or later, ALWAYS use the snapshot summary (most reliable)
  if (currentInningsNo.value >= 2) {
    const summary = snap?.first_inning_summary || (snap as any)?.first_innings_summary
    if (summary) {
      const runs = summary.runs ?? 0
      const wickets = summary.wickets ?? 0
      const overs = summary.overs ?? 0
      return `${runs}/${wickets} (${overs} ov)`
    }
  }

  // For live innings 1, calculate from deliveries
  if (innings1.value) {
    return `${innings1.value.runs}/${innings1.value.wkts} (${oversDisplayFromBalls(innings1.value.balls)} ov)`
  }

  return null
})

// === Highlights (FOUR/SIX/WICKET/DUCK/50/100) =========================
const enableHighlights = ref(true)   // make a prop later if you want
const highlightMs = ref(1800)
const {
  current: highlight,              // <- 'FOUR' | 'SIX' | 'WICKET' | 'DUCK' | 'FIFTY' | 'HUNDRED' | null
  enqueueFromSnapshots,
  reset: resetHighlights,
} = useHighlights(enableHighlights, highlightMs)

const prevHL = ref<HL | null>(null)

// map your Pinia/live snapshot to the useHighlights Snapshot shape
function mapToHL(s: any): HL {
  const g: any = currentGame.value || {}
  const card = (g.batting_scorecard || {}) as Record<string, any>

  const findName = (id?: string | null): string => {
    if (!id) return ''
    const tA = g.team_a?.players || []
    const tB = g.team_b?.players || []
    return (
      tA.find((p:any)=>String(p.id)===String(id))?.name ||
      tB.find((p:any)=>String(p.id)===String(id))?.name ||
      card[String(id)]?.player_name ||
      ''
    )
  }

  const mkBatter = (id?: string | null) => {
    if (!id) return undefined
    const row = card[String(id)] || {}
    return {
      id: String(id),
      name: findName(id),
      runs: Number(row?.runs ?? 0),
      balls: Number(row?.balls_faced ?? row?.balls ?? 0),
      out: Boolean(row?.is_out),
    }
  }

  const ld = s?.last_delivery
  const runsOffBat = Number(ld?.runs_scored ?? ld?.runs ?? 0)
  const isExtra = Boolean(ld?.is_extra ?? (ld?.extra_type != null))
  const lastBall = ld
    ? {
        runs: runsOffBat,
        // count only off-the-bat 4/6 as boundaries; tweak if you want “wide four” etc.
        isBoundary4: !isExtra && runsOffBat === 4,
        isBoundary6: !isExtra && runsOffBat === 6,
        isWicket: Boolean(ld?.is_wicket),
        dismissedBatterId: ld?.dismissed_player_id ? String(ld.dismissed_player_id) : undefined,
      }
    : undefined

  return {
    total: {
      runs: Number(s?.total_runs ?? g.total_runs ?? 0),
      wickets: Number(s?.total_wickets ?? g.total_wickets ?? 0),
    },
    striker: mkBatter(s?.current_striker_id ?? g.current_striker_id),
    nonStriker: mkBatter(s?.current_non_striker_id ?? g.current_non_striker_id),
    lastBall,
  }
}

// enqueue on every live snapshot change (skip first paint)
watch(liveSnapshot, (next) => {
  if (!next) return
  const nextHL = mapToHL(next)
  if (prevHL.value) enqueueFromSnapshots(prevHL.value, nextHL)
  prevHL.value = nextHL
}, { deep: true })

onUnmounted(() => { resetHighlights() })

/* ----------------------------- */
/* Striker / Non-striker / Bowler */
/* ----------------------------- */
type BatRow = {
  id: string; name: string; runs: number; balls: number; fours: number; sixes: number;
  sr: number | string; isOut: boolean; howOut?: string
}
const battingRows = computed<BatRow[]>(() =>
  (battingRowsXI.value || []).map((r: any) => ({
    id: String(r.id),
    name: String(r.name),
    runs: Number(r.runs ?? 0),
    balls: Number(r.balls ?? r.balls_faced ?? 0),
    fours: Number(r.fours ?? 0),
    sixes: Number(r.sixes ?? 0),
    sr: typeof r.sr === 'number' ? r.sr : Number(r.sr ?? 0),
    isOut: Boolean(r.isOut ?? r.is_out),
    howOut: r.howOut ?? r.how_out ?? undefined,
  }))
)

type BowlRow = {
  id: string
  name: string
  overs: string
  maidens: number
  runs: number
  wkts: number
  econ: number | string
}

const bowlingRows = computed<BowlRow[]>(() =>
   (bowlingRowsXI.value || []).map((r: any) => {
     const id = String(r.id)
     const fig = figuresByBowler.value[id]
     return {
       id,
       name: String(r.name),
       overs: fig?.oversText ?? oversDisplayFromAny(r),
       maidens: fig?.maidens ?? Number(r.maidens ?? 0),
       runs: fig?.runs ?? Number(r.runs ?? r.runs_conceded ?? 0),
       wkts: Number(r.wkts ?? r.wickets_taken ?? 0), // keep server wickets
       econ: fig?.econText ?? (typeof r.econ === 'number' ? r.econ : Number(r.econ ?? 0)),
     }
   })
 )


// --- Decide strike swap from the last delivery (handles wd/nb running correctly)
function shouldSwapStrikeFromLast(ld: any): boolean {
  if (!ld) return false
  const x = String(ld.extra_type ?? ld.extra ?? '')
  if (!x || x === 'b' || x === 'lb') {
    const offBat = Number(ld.runs_off_bat ?? ld.runs_scored ?? ld.runs ?? 0)
    return (offBat % 2) === 1
  }
  if (x === 'wd') {
    // wides: only *run(s) actually run* flip strike
    const total = Math.max(1, Number(ld.runs_scored ?? ld.extra_runs ?? 1))
    const runsRun = total - 1
    return (runsRun % 2) === 1
  }
  if (x === 'nb') {
    // no-ball: penalty 1 + off-bat (and any extra beyond penalty)
    const offBat = Number(ld.runs_off_bat ?? 0)
    const extraBeyondPenalty = Math.max(0, Number(ld.extra_runs ?? 1) - 1)
    return ((offBat + extraBeyondPenalty) % 2) === 1
  }
  return false
}

const safeStrikerId = computed<string | null>(() => {
  const g:any = currentGame.value || {}
  const st = String(
    (state.value as any)?.current_striker_id ??
    liveSnapshot.value?.current_striker_id ??
    g.current_striker_id ?? ''
  ) || null
  const nst = String(
    (state.value as any)?.current_non_striker_id ??
    liveSnapshot.value?.current_non_striker_id ??
    g.current_non_striker_id ?? ''
  ) || null

  if (st && nst && st === nst) {
    const ld = (state.value as any)?.last_delivery ?? g.last_delivery
    return shouldSwapStrikeFromLast(ld) ? nst : st
  }
  return st
})

const safeNonStrikerId = computed<string | null>(() => {
  const g:any = currentGame.value || {}
  const st  = String(
    (state.value as any)?.current_striker_id ??
    liveSnapshot.value?.current_striker_id ??
    g.current_striker_id ?? ''
  ) || null
  const nst = String(
    (state.value as any)?.current_non_striker_id ??
    liveSnapshot.value?.current_non_striker_id ??
    g.current_non_striker_id ?? ''
  ) || null

  if (st && nst && st === nst) {
    const ld = (state.value as any)?.last_delivery ?? g.last_delivery
    return shouldSwapStrikeFromLast(ld) ? st : nst
  }
  return nst
})


// striker/non-striker lookups
const strikerRow = computed(() =>
  safeStrikerId.value
    ? battingRows.value.find(r => String(r.id) === safeStrikerId.value) || null
    : null
)

const nonStrikerRow = computed(() =>
  safeNonStrikerId.value
    ? battingRows.value.find(r => String(r.id) === safeNonStrikerId.value) || null
    : null
)

/* ---------------------------------- */
/* Captain / Keeper badge helpers     */
/* ---------------------------------- */
const isBattingTeamA = computed(() => battingTeamName.value === teamAName.value)
const { roleBadge } = useRoleBadge({
  currentGame,
  isBattingTeamA,
})


/* --------------------- */
/* Last 10 balls         */
/* --------------------- */
type Delivery = { over_number?: number | string; ball_number?: number; runs_scored?: number; runs_off_bat?: number; extra?: 'wd' | 'nb' | 'b' | 'lb' | string | null; is_wicket?: boolean; commentary?: string }
function parseOverBall(d: any): { over: number; ball: number } {
  const overLike = d?.over_number ?? d?.over
  const ballLike = d?.ball_number ?? d?.ball
  if (typeof ballLike === 'number' && typeof overLike === 'number') return { over: Math.max(0, Math.floor(overLike)), ball: Math.max(0, ballLike) }
  if (typeof overLike === 'string') { const [o, b] = overLike.split('.'); return { over: Number(o) || 0, ball: Number(b) || 0 } }
  if (typeof overLike === 'number') { const whole = Math.floor(overLike); const tenth = Math.round((overLike - whole) * 10); return { over: whole, ball: Math.max(0, Math.min(5, tenth)) } }
  return { over: 0, ball: 0 }
}
function outcomeTag(d: Delivery): string {
  const ex = (d.extra || '') as string
  const rb = Number(d.runs_off_bat ?? d.runs_scored ?? 0)
  const re = Number(d.runs_scored ?? 0)
  if (d.is_wicket) return 'W'
  if (ex === 'wd') return re > 1 ? `Wd+${re - 1}` : 'Wd'
  if (ex === 'nb') return rb ? `Nb+${rb}` : 'Nb'
  if (ex === 'b')  return re ? `B${re}` : 'B'
  if (ex === 'lb') return re ? `LB${re}` : 'LB'
  return String(rb || re || 0)
}
function ballLabel(d: Delivery): string {
  const { over, ball } = parseOverBall(d)
  const parts = [`${over}.${ball}`, outcomeTag(d)]
  if (d.commentary) parts.push(`— ${d.commentary}`)
  return parts.join(' ')
}
const recentDeliveries = computed(() =>
  deliveriesThisInnings.value.slice(-10)   // (de-dup already applied above)
)

 // Current bowler (safe id + name + derived figures)
 const safeCurrentBowlerId = computed<string | null>(() => {
   const s: any = state.value || {}
   const id = s.current_bowler_id ?? s.last_ball_bowler_id ?? (currentGame.value as any)?.current_bowler_id
   return id != null ? String(id) : null
 })

 const safeCurrentBowlerName = computed<string>(() => {
   const id = safeCurrentBowlerId.value
   if (!id) return ''
   const row = (bowlingRowsXI.value || []).find((p: any) => String(p.id) === id)
   if (row?.name) return String(row.name)

   // Fallback: look in the team roster
   const g = currentGame.value
   if (!g) return ''
   const p = [...(g.team_a?.players||[]), ...(g.team_b?.players||[])].find(p => String(p.id) === id)
   return p?.name || ''
 })

 const currentBowlerDerived = computed(() => {
   const id = safeCurrentBowlerId.value
   return id ? figuresByBowler.value[id] : undefined
 })

  const currentBowlerWkts = computed<number>(() => {
   const id = safeCurrentBowlerId.value
   if (!id) return 0
   const r = (bowlingRowsXI.value as any[]).find((p: any) => String(p.id) === id) as any
   return Number((r?.wkts ?? r?.wickets_taken ?? 0) as number)
 })


/* ------------------- */
/* Interruption control */
/* ------------------- */
const showInterruptionBanner = computed(() => !!currentInterruption.value)
const interBusy = ref(false)

async function startDelay(kind: 'weather' | 'injury' | 'light' | 'other' = 'weather', note?: string) {
  if (interBusy.value) return
  interBusy.value = true
  try { await gameStore.startInterruption(kind, note) }
  finally { interBusy.value = false }
}
async function resumePlay(kind: 'weather' | 'injury' | 'light' | 'other' = 'weather') {
  if (interBusy.value) return
  interBusy.value = true
  try { await gameStore.stopInterruption(kind) }
  finally { interBusy.value = false }
}
</script>

<template>
  <section class="board" :data-theme="theme">
    <!-- Highlight overlay -->
    <div v-if="highlight" class="hl-banner" aria-live="polite">
      <span v-if="highlight==='FOUR'">FOUR!</span>
      <span v-else-if="highlight==='SIX'">SIX!</span>
      <span v-else-if="highlight==='WICKET'">WICKET!</span>
      <span v-else-if="highlight==='DUCK'">DUCK!</span>
      <span v-else-if="highlight==='FIFTY'">FIFTY!</span>
      <span v-else-if="highlight==='HUNDRED'">HUNDRED!</span>
    </div>

    <!-- Left sponsor rail -->
    <aside v-if="leftSponsor" class="sponsor-rail rail-left rail-large">
      <component
        :is="sponsorHref(leftSponsor) ? 'a' : 'div'"
        :href="sponsorHref(leftSponsor)"
        target="_blank"
        rel="noopener"
        class="rail-link"
      >
        <img :src="sponsorImg(leftSponsor)" :alt="sponsorAlt(leftSponsor)" />
      </component>
    </aside>

    <!-- Header -->
    <header class="hdr">
      <img
        v-if="logoUrl && logoOk"
        :key="logoUrl"
        class="brand"
        :src="logoUrl"
        alt="Logo"
        @error="onLogoErr"
      />
      <h3>{{ title || 'Live Scoreboard' }}</h3>
      <BaseBadge v-if="!isGameOver" variant="primary">● LIVE</BaseBadge>
      <BaseBadge v-else variant="success">FINAL</BaseBadge>


      <!-- Presented by badge -->
      <a
        v-if="badgeSponsor"
        class="badge-sponsor"
        :href="sponsorHref(badgeSponsor)"
        target="_blank"
        rel="noopener"
        :aria-label="`Presented by ${sponsorAlt(badgeSponsor)}`"
      >
        <span class="badge-label">Presented by</span>
        <img :src="sponsorImg(badgeSponsor)" :alt="sponsorAlt(badgeSponsor)" />
      </a>
    </header>

    <!-- Controls -->
    <div v-if="props.canControl && !showInterruptionBanner" class="ctrl-row">
      <BaseButton
        variant="secondary"
        size="sm"
        :disabled="interBusy"
        @click="startDelay('weather')"
      >
        {{ interBusy ? 'Starting…' : 'Start delay' }}
      </BaseButton>
    </div>

    <!-- Main card -->
    <div v-if="storeError" class="error">{{ storeError }}</div>
    <div v-else class="card">
      <!-- Interruption banner -->
      <div
        v-if="showInterruptionBanner"
        class="interrupt-banner"
        role="status"
        aria-live="polite"
        data-testid="interrupt-banner"
      >
        <span class="icon">⛈</span>
        <strong class="kind">
          {{ (currentInterruption?.kind || 'weather') === 'weather' ? 'Rain delay' : (currentInterruption?.kind || 'Interruption') }}
        </strong>
        <span class="dot">•</span>
        <span class="elapsed">Paused {{ elapsedSince(currentInterruption?.started_at) }}</span>
        <span v-if="currentInterruption?.note" class="note">— {{ currentInterruption?.note }}</span>

        <BaseButton
          v-if="props.canControl"
          variant="ghost"
          size="sm"
          :disabled="interBusy"
          class="resume-btn"
          data-testid="btn-resume-interruption"
          @click="resumePlay(currentInterruption?.kind as any)"
        >
          {{ interBusy ? 'Resuming…' : 'Resume play' }}
        </BaseButton>
      </div>

      <!-- Result banner: show if game is over OR any result text is present -->
      <div
        v-if="isGameOver || resultText"
        class="result-banner"
        role="status"
        aria-live="polite"
        data-testid="scoreboard-result-banner"
      >
        <strong>{{ resultText || 'Match completed' }}</strong>
      </div>

      <!-- Topline -->
      <div class="topline">
        <div class="teams">
          <strong>{{ currentGame?.batting_team_name || '' }}</strong>
          <span>vs</span>
          <strong>{{ currentGame?.bowling_team_name || '' }}</strong>
        </div>
        <div class="score">
          <span v-if="currentInningNo === 2" class="bt">{{ battingTeamName }}</span>
          <span class="big" data-testid="scoreboard-score">
            <span data-testid="scoreboard-runs">{{ runs }}</span>/<span data-testid="scoreboard-wkts">{{ wkts }}</span>
          </span>
          <span class="ov" data-testid="scoreboard-overs">({{ oversText }} ov)</span>
        </div>
      </div>

      <!-- First-innings summary -->
      <div v-if="innings1Line" class="first-inn">
        <span class="lbl">First Innings — {{ innings1TeamName || '—' }}</span>
        <strong>{{ innings1Line }}</strong>
      </div>


      <!-- Three-pane row + tables -->
      <div class="grid grid-3">
        <!-- Striker -->
        <div class="pane">
          <div class="pane-title">Striker</div>
          <div class="row"><div class="label">Name</div><div class="val" data-testid="scoreboard-striker-name"><RouterLink v-if="strikerRow?.id && isValidUUID(strikerRow.id)" :to="{ name: 'PlayerProfile', params: { playerId: strikerRow.id } }" class="player-link" target="_blank" rel="noopener noreferrer">{{ strikerRow.name }}</RouterLink><span v-else>{{ strikerRow?.name || '-' }}</span><span v-if="strikerRow?.id" class="role-badge">{{ roleBadge(strikerRow.id) }}</span></div></div>
          <div class="row"><div class="label">Runs (Balls)</div><div class="val">{{ strikerRow?.runs ?? 0 }} ({{ strikerRow?.balls ?? 0 }})</div></div>
          <div class="row"><div class="label">Strike Rate</div><div class="val">{{ fmtSR(strikerRow?.runs ?? 0, strikerRow?.balls ?? 0) }}</div></div>
        </div>

        <!-- Non-striker -->
        <div class="pane">
          <div class="pane-title">Non-striker</div>
          <div class="row"><div class="label">Name</div><div class="val" data-testid="scoreboard-nonstriker-name"><RouterLink v-if="nonStrikerRow?.id && isValidUUID(nonStrikerRow.id)" :to="{ name: 'PlayerProfile', params: { playerId: nonStrikerRow.id } }" class="player-link" target="_blank" rel="noopener noreferrer">{{ nonStrikerRow.name }}</RouterLink><span v-else>{{ nonStrikerRow?.name || '-' }}</span><span v-if="nonStrikerRow?.id" class="role-badge">{{ roleBadge(nonStrikerRow.id) }}</span></div></div>
          <div class="row"><div class="label">Runs (Balls)</div><div class="val">{{ nonStrikerRow?.runs ?? 0 }} ({{ nonStrikerRow?.balls ?? 0 }})</div></div>
          <div class="row"><div class="label">Strike Rate</div><div class="val">{{ fmtSR(nonStrikerRow?.runs ?? 0, nonStrikerRow?.balls ?? 0) }}</div></div>
        </div>

        <!-- Current bowler -->
        <div class="pane">
          <div class="pane-title">Bowler</div>
          <div class="row"><div class="label">Name</div><div class="val" data-testid="scoreboard-bowler-name">{{ safeCurrentBowlerName || '-' }}</div></div>
          <div class="row">
            <div class="label">Figures</div>
            <div class="val">
              {{ currentBowlerWkts }}-{{ currentBowlerDerived?.runs ?? 0 }} ({{ currentBowlerDerived?.oversText ?? '0.0' }})
            </div>
          </div>
          <div class="row">
            <div class="label">Economy</div>
            <div class="val">{{ currentBowlerDerived?.econText ?? '—' }}</div>
          </div>
        </div>

        <!-- Info strip: CRR always (when balls bowled); Target/RRR/Overs left only in chase -->
        <div class="info-strip">
          <div v-if="showCrr" class="cell" data-testid="scoreboard-crr">
            <span class="lbl">CRR</span> <strong>{{ crr }}</strong>
          </div>
          <div v-if="isChase && targetDisplay != null" class="cell" data-testid="scoreboard-target">
            <span class="lbl">Target</span> <strong>{{ targetDisplay }}</strong>
          </div>
          <div v-if="isChase && rrr" class="cell" data-testid="scoreboard-rrr">
            <span class="lbl">RRR</span> <strong>{{ rrr }}</strong>
          </div>
          <div v-if="parTxt" class="cell" data-testid="scoreboard-par">
            <span class="lbl">Par</span> <strong>{{ parTxt }}</strong>
          </div>
          <div v-if="isChase && oversLeft" class="cell" data-testid="scoreboard-overs-left">
            <span class="lbl">Overs left</span> <strong>{{ oversLeft }}</strong>
          </div>
        </div>

        <!-- Mini scorecards -->
        <div class="full-span">
          <div class="pane wide-pane">
            <div class="pane-title">Batting</div>
            <table class="mini batting-table">
              <thead>
                <tr>
                  <th class="name">Player</th>
                  <th class="num">R</th>
                  <th class="num">B</th>
                  <th class="num">4s</th>
                  <th class="num">6s</th>
                  <th class="num">SR</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="b in battingRows" :key="b.id">
                  <td class="name"><RouterLink v-if="isValidUUID(b.id)" :to="{ name: 'PlayerProfile', params: { playerId: b.id } }" class="player-link" target="_blank" rel="noopener noreferrer">{{ b.name }}</RouterLink><span v-else>{{ b.name }}</span><span class="role-badge">{{ roleBadge(b.id) }}</span></td>
                  <td class="num">{{ b.runs }}</td>
                  <td class="num">{{ b.balls }}</td>
                  <td class="num">{{ b.fours }}</td>
                  <td class="num">{{ b.sixes }}</td>
                  <td class="num">{{ fmtSR(b.runs, b.balls) }}</td>
                  <td class="status">{{ b.isOut ? (b.howOut ? `Out (${b.howOut})` : 'Out') : 'Not out' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="pane wide-pane">
            <div class="pane-title">Bowling</div>
            <table class="mini bowling-table">
              <thead>
                <tr>
                  <th class="name">Bowler</th>
                  <th class="num">O</th>
                  <th class="num">M</th>
                  <th class="num">R</th>
                  <th class="num">W</th>
                  <th class="num">Econ</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="bw in bowlingRows" :key="bw.id">
                  <td class="name"><RouterLink v-if="isValidUUID(bw.id)" :to="{ name: 'PlayerProfile', params: { playerId: bw.id } }" class="player-link" target="_blank" rel="noopener noreferrer">{{ bw.name }}</RouterLink><span v-else>{{ bw.name }}</span></td>
                  <td class="num">{{ bw.overs }}</td>
                  <td class="num">{{ bw.maidens }}</td>
                  <td class="num">{{ bw.runs }}</td>
                  <td class="num">{{ bw.wkts }}</td>
                  <td class="num">{{ typeof bw.econ === 'number' ? bw.econ.toFixed(2) : bw.econ }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Last 10 balls -->
        <div class="pane">
          <div class="pane-title">Last 10 balls</div>
          <div class="balls">
            <div v-for="(d, i) in recentDeliveries" :key="i" class="ball" :title="ballLabel(d)">
              {{ outcomeTag(d) }}
            </div>
          </div>
        </div>
      </div> <!-- /.grid -->

      <!-- Win Probability Prediction (visible to viewers) -->
      <div v-if="currentPrediction" class="prediction-section">
        <WinProbabilityChart :show-chart="false" />
      </div>
    </div>   <!-- /.card -->
  </section>
</template>


<style scoped>
/* =====================================================
   SCOREBOARD WIDGET - Using Design System Tokens
   ===================================================== */

/* Header logo */
.brand {
  height: 30px;
  width: auto;
  opacity: 0.9;
}

/* Board: only space for a single LARGE left rail */
.board {
  position: relative;
  width: min(980px, 96vw);
  margin: 0 auto;
  padding-left: 180px;
  padding-right: 0;
}

/* Single LEFT sponsor rail (large) */
.sponsor-rail {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  display: grid;
  place-items: center;
  padding: var(--space-3);
  border-radius: var(--radius-lg);
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  z-index: 3;
}

.rail-left {
  left: var(--space-3);
}

/* Large panel sizing */
.rail-large {
  width: 160px;
}

.rail-large img {
  max-width: 144px;
  max-height: 144px;
  object-fit: contain;
  display: block;
  filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.25));
}

.rail-link {
  text-decoration: none;
}

/* Completed match banner */
.result-banner {
  background: var(--color-success-soft);
  border: 1px solid var(--color-success);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  margin: var(--space-2) 0 var(--space-3);
  text-align: center;
  font-weight: var(--font-extrabold);
  color: var(--color-success);
}

/* Control row */
.ctrl-row {
  margin: var(--space-2) 0;
}

/* Resume button alignment */
.resume-btn {
  margin-left: auto;
}

/* Light theme variants */
:where([data-theme="light"]) .sponsor-rail {
  background: var(--color-surface);
  border-color: var(--color-border);
}

/* Mobile/Tablet: dock the large rail at the top and shrink a bit */
@media (max-width: 1100px) {
  .board {
    padding-left: 0;
    padding-top: 96px;
  }

  .sponsor-rail {
    top: var(--space-3);
    left: var(--space-3);
    transform: none;
    padding: var(--space-2) var(--space-3);
  }

  .rail-large {
    width: auto;
  }

  .rail-large img {
    max-width: 120px;
    max-height: 60px;
  }

  /* Keep highlight toast clear of the rail */
  .hl-banner {
    top: 96px;
    right: var(--space-3);
  }
}

/* Presented-by badge in header */
.badge-sponsor {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-pill);
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  text-decoration: none;
}

.badge-sponsor .badge-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-bold);
  letter-spacing: 0.02em;
}

.badge-sponsor img {
  height: 20px;
  width: auto;
  display: block;
}

:where([data-theme="light"]) .badge-sponsor {
  background: var(--color-surface);
  border-color: var(--color-border);
}

/* Interruption banner */
.interrupt-banner {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  margin-bottom: var(--space-3);
  border: 1px solid var(--color-border);
  background: var(--color-success-soft);
  color: var(--color-success);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
}

.interrupt-banner .icon {
  font-size: var(--text-base);
}

.interrupt-banner .dot {
  opacity: 0.7;
}

.interrupt-banner .note {
  font-weight: var(--font-semibold);
  opacity: 0.9;
}

:where([data-theme="light"]) .interrupt-banner {
  background: var(--color-success-soft);
  border-color: var(--color-success);
  color: var(--color-success);
}

/* First innings summary */
.first-inn {
  margin: var(--space-2) 0 0;
  display: flex;
  gap: var(--space-2);
  align-items: baseline;
  color: var(--color-text-muted);
}

.first-inn .lbl {
  font-size: var(--text-xs);
}

:where([data-theme="light"]) .first-inn {
  color: var(--color-text-muted);
}

/* Info strip */
.info-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: var(--space-3);
  margin: var(--space-3) 0 var(--space-4);
}

.info-strip .cell {
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-strip .lbl {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

:where([data-theme="light"]) .info-strip .cell {
  background: var(--color-surface);
  border-color: var(--color-border);
}

@media (min-width: 1200px) {
  .info-strip {
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: var(--space-4);
  }
}

/* Header */
.hdr {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin: var(--space-3) 0;
}

/* Main card */
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  box-shadow: var(--shadow-card);
}

/* Topline */
.topline {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--space-4);
  margin-bottom: var(--space-3);
}

.teams {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  color: var(--color-text-muted);
}

.score {
  display: flex;
  gap: var(--space-2);
  align-items: baseline;
}

.big {
  font-weight: var(--font-extrabold);
  font-size: var(--text-3xl);
  letter-spacing: 0.5px;
}

.ov {
  color: var(--color-text-muted);
  font-weight: var(--font-semibold);
}

/* Grid layout */
.grid {
  display: grid;
  gap: var(--space-3);
  margin-top: var(--space-2);
}

.grid-3 {
  grid-template-columns: repeat(3, 1fr);
}

@media (max-width: 860px) {
  .grid-3 {
    grid-template-columns: 1fr;
  }
}

/* Pane */
.pane {
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-3);
}

.pane-title {
  font-weight: var(--font-extrabold);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin-bottom: var(--space-2);
}

.row {
  display: grid;
  grid-template-columns: 160px 1fr;
  padding: var(--space-2) 0;
  border-top: 1px dashed var(--color-border);
}

.row:first-of-type {
  border-top: 0;
}

.label {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.val {
  font-weight: var(--font-bold);
}

.bt {
  font-weight: var(--font-extrabold);
  margin-right: var(--space-2);
  opacity: 0.9;
}

:where([data-theme="light"]) .card {
  background: var(--color-surface);
  border-color: var(--color-border);
}

:where([data-theme="light"]) .pane {
  background: var(--color-bg);
  border-color: var(--color-border);
}

:where([data-theme="light"]) .ov,
:where([data-theme="light"]) .teams,
:where([data-theme="light"]) .label {
  color: var(--color-text-muted);
}

/* Tables */
.wide-pane {
  overflow-x: auto;
}

.batting-table th,
.batting-table td {
  padding: var(--space-1) var(--space-2);
  white-space: nowrap;
}

.bowling-table th,
.bowling-table td {
  padding: var(--space-1) var(--space-2);
  white-space: nowrap;
}

.full-span {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* Ball indicators */
.balls {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.ball {
  min-width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-border);
  background: var(--color-surface-hover);
  font-weight: var(--font-extrabold);
  font-size: var(--text-xs);
}

:where([data-theme="light"]) .ball {
  background: var(--color-surface);
  border-color: var(--color-border);
}

/* Highlight toast */
.hl-banner {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
  z-index: 5;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-primary-soft);
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
  font-weight: var(--font-extrabold);
  letter-spacing: 0.04em;
  font-size: var(--text-base);
  animation: hl-pop 800ms ease, hl-fade 1800ms ease forwards;
  pointer-events: none;
}

@keyframes hl-pop {
  from {
    transform: scale(0.92);
    opacity: 0.4;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes hl-fade {
  0% { opacity: 1; }
  70% { opacity: 1; }
  100% { opacity: 0; }
}

:where([data-theme="light"]) .hl-banner {
  background: var(--color-primary-soft);
  border-color: var(--color-primary);
  color: var(--color-primary-hover);
}

/* Captain / Keeper role badge */
.role-badge {
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  color: var(--color-accent);
  opacity: 0.85;
  margin-left: var(--space-1);
}

:where([data-theme="light"]) .role-badge {
  color: var(--color-accent-hover);
}

/* Player profile link */
.player-link {
  color: inherit;
  text-decoration: none;
}

.player-link:hover {
  text-decoration: underline;
  text-decoration-style: dotted;
}

/* Error state */
.error {
  color: var(--color-error);
  padding: var(--space-4);
  text-align: center;
}

/* =====================================================
   PROJECTOR MODE CSS VARIABLES

   Applied at root level via :style binding in parents
   - --sb-scale: Scale factor (1, 1.1, 1.25, 1.5)
   - --sb-density-padding: Padding for density (12px/16px/24px)
   - --sb-density-font: Font scale (0.9em/1em/1.1em)
   - --sb-density-gap: Gap/spacing (8px/12px/16px)
   - --sb-safe-pad: Safe area padding for TV edge (0px or 20px)
   ===================================================== */

:root {
  --sb-scale: 1;
  --sb-density-padding: 16px;
  --sb-density-font: 1em;
  --sb-density-gap: 12px;
  --sb-safe-pad: 0px;
}

/* Apply scale and density to card */
.card {
  transform: scale(var(--sb-scale));
  transform-origin: top center;
  font-size: var(--sb-density-font);
  padding: calc(var(--sb-density-padding) + var(--sb-safe-pad));
}

/* Responsive grid adjustments for density */
.grid {
  gap: var(--sb-density-gap);
}

.pane {
  padding: var(--sb-density-padding);
}

/* Win Probability Section */
.prediction-section {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}
</style>

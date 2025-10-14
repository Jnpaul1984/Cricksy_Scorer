<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { fmtSR, fmtEconomy, oversDisplayFromBalls, oversDisplayFromAny, deriveBowlerFigures } from '@/utils/cricket'
import { useGameStore } from '@/stores/gameStore'
import { storeToRefs } from 'pinia'
import { useHighlights, type Snapshot as HL } from '@/composables/useHighlights'
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
  pollMs: 30000,
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
} = storeToRefs(gameStore)

const { targetSafe, requiredRunRate, runsRequired, ballsBowledTotal } = storeToRefs(gameStore)

/* ---------------------- */
/* Bootstrapping (NEW)    */
/* ---------------------- */
let pollTimer: number | null = null
const ownsLive = ref(false)

async function startFeed() {
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
  try { await gameStore.refreshInterruptions() } catch {}

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
    : null
  const fromModel = Array.isArray((currentGame.value as any)?.deliveries)
    ? (currentGame.value as any).deliveries
    : []
  return (fromState ?? fromModel)
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

const scoreline = computed(() => `${runs.value}/${wkts.value}`)

// Rates now based on totalBalls
const crr = computed(() =>
  totalBallsThisInnings.value ? (runs.value / (totalBallsThisInnings.value / 6)).toFixed(2) : '—'
)

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


const allDeliveriesRaw = computed<any[]>(() => {
  const fromState = Array.isArray((state.value as any)?.recent_deliveries)
    ? (state.value as any).recent_deliveries
    : null
  const fromModel = Array.isArray((currentGame.value as any)?.deliveries)
    ? (currentGame.value as any).deliveries
    : []
  return (fromState ?? fromModel)
})

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

const rrr = computed(() => {
  if (!isSecondInnings.value || target.value == null) return null
  const need = Math.max(0, target.value - runs.value)
  if (!oversLimit.value) return null
  const remBalls = Math.max(0, oversLimit.value * 6 - totalBallsThisInnings.value)
  if (remBalls <= 0) return null
  return (need / (remBalls / 6)).toFixed(2)
})

const oversLeft = computed(() => {
  if (!oversLimit.value) return '—'
  const rem = Math.max(0, oversLimit.value * 6 - totalBallsThisInnings.value)
  return oversDisplayFromBalls(rem)
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

const innings1Line = computed<string | null>(() =>
  innings1.value ? `${innings1.value.runs}/${innings1.value.wkts} (${oversDisplayFromBalls(innings1.value.balls)} ov)` : null
)

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
   return row?.name ? String(row.name) : ''
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
        class="brand"
        :src="logoUrl"
        alt="Logo"
        @error="onLogoErr"
        :key="logoUrl"
      />
      <h3>{{ title || 'Live Scoreboard' }}</h3>
      <span v-if="!isGameOver" class="pill live">● LIVE</span>
      <span v-else class="pill final">FINAL</span>


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
    <div v-if="props.canControl && !showInterruptionBanner" class="ctrl-row" style="margin:8px 0;">
      <button class="btn" :disabled="interBusy" @click="startDelay('weather')">
        {{ interBusy ? 'Starting…' : 'Start delay' }}
      </button>
    </div>

    <!-- Main card -->
    <div v-if="storeError" class="error">{{ storeError }}</div>
    <div v-else class="card">
      <!-- Interruption banner -->
      <div v-if="showInterruptionBanner" class="interrupt-banner" role="status" aria-live="polite">
        <span class="icon">⛈</span>
        <strong class="kind">
          {{ (currentInterruption?.kind || 'weather') === 'weather' ? 'Rain delay' : (currentInterruption?.kind || 'Interruption') }}
        </strong>
        <span class="dot">•</span>
        <span class="elapsed">Paused {{ elapsedSince(currentInterruption?.started_at) }}</span>
        <span v-if="currentInterruption?.note" class="note">— {{ currentInterruption?.note }}</span>

        <button
          v-if="props.canControl"
          class="btn btn-ghost"
          :disabled="interBusy"
          @click="resumePlay(currentInterruption?.kind as any)"
          style="margin-left:auto"
        >
          {{ interBusy ? 'Resuming…' : 'Resume play' }}
        </button>
      </div>

      <!-- Result banner (only when match is completed) -->
      <div v-if="isGameOver" class="result-banner" role="status" aria-live="polite">
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
          <span class="big">{{ scoreline }}</span>
          <span class="ov">({{ oversText }} ov)</span>
        </div>
      </div>

      <!-- First-innings summary -->
      <div class="first-inn" v-if="innings1Line">
        <span class="lbl">First Innings — {{ innings1TeamName || '—' }}</span>
        <strong>{{ innings1Line }}</strong>
      </div>


      <!-- Three-pane row + tables -->
      <div class="grid grid-3">
        <!-- Striker -->
        <div class="pane">
          <div class="pane-title">Striker</div>
          <div class="row"><div class="label">Name</div><div class="val">{{ strikerRow?.name || '—' }}</div></div>
          <div class="row"><div class="label">Runs (Balls)</div><div class="val">{{ strikerRow?.runs ?? 0 }} ({{ strikerRow?.balls ?? 0 }})</div></div>
          <div class="row"><div class="label">Strike Rate</div><div class="val">{{ fmtSR(strikerRow?.runs ?? 0, strikerRow?.balls ?? 0) }}</div></div>
        </div>

        <!-- Non-striker -->
        <div class="pane">
          <div class="pane-title">Non-striker</div>
          <div class="row"><div class="label">Name</div><div class="val">{{ nonStrikerRow?.name || '—' }}</div></div>
          <div class="row"><div class="label">Runs (Balls)</div><div class="val">{{ nonStrikerRow?.runs ?? 0 }} ({{ nonStrikerRow?.balls ?? 0 }})</div></div>
          <div class="row"><div class="label">Strike Rate</div><div class="val">{{ fmtSR(nonStrikerRow?.runs ?? 0, nonStrikerRow?.balls ?? 0) }}</div></div>
        </div>

        <!-- Current bowler -->
        <div class="pane">
          <div class="pane-title">Bowler</div>
          <div class="row"><div class="label">Name</div><div class="val">{{ safeCurrentBowlerName || '—' }}</div></div>
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

        <!-- Info strip -->
        <div class="info-strip">
          <div class="cell"><span class="lbl">CRR</span><strong>{{ crr }}</strong></div>
          <div v-if="rrr" class="cell"><span class="lbl">RRR</span><strong>{{ rrr }}</strong></div>
          <div v-if="targetDisplay != null" class="cell">
            <span class="lbl">Target</span><strong>{{ targetDisplay }}</strong>
          </div>
          <div v-if="parTxt" class="cell"><span class="lbl">Par</span><strong>{{ parTxt }}</strong></div>
          <div class="cell"><span class="lbl">Overs left</span><strong>{{ oversLeft }}</strong></div>
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
                  <td class="name">{{ b.name }}</td>
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
                  <td class="name">{{ bw.name }}</td>
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
            <div class="ball" v-for="(d, i) in recentDeliveries" :key="i" :title="ballLabel(d)">
              {{ outcomeTag(d) }}
            </div>
          </div>
        </div>
      </div> <!-- /.grid -->
    </div>   <!-- /.card -->
  </section>
</template>


<style scoped>
/* Header logo */
.brand { height: 30px; width: auto; opacity: .9; }

/* Board: only space for a single LARGE left rail */
.board {
  position: relative;
  width: min(980px, 96vw);
  margin: 0 auto;
  padding-left: 180px;   /* space for big left rail */
  padding-right: 0;      /* no right rail */
}

/* Single LEFT sponsor rail (large) */
.sponsor-rail {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  display: grid;
  place-items: center;
  padding: 12px;
  border-radius: 12px;
  background: rgba(0,0,0,.14);
  border: 1px solid rgba(255,255,255,.06);
  z-index: 3;
}
.rail-left { left: 12px; }

/* Large panel sizing */
.rail-large { width: 160px; }
.rail-large img {
  max-width: 144px;
  max-height: 144px;
  object-fit: contain;
  display: block;
  filter: drop-shadow(0 2px 6px rgba(0,0,0,.25));
}
.rail-link { text-decoration: none; }

/* Completed match banner */
.result-banner {
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.6);
  border-radius: 10px;
  padding: 10px 12px;
  margin: 8px 0 12px;
  text-align: center;
  font-weight: 800;
}
:where([data-theme="light"]) .result-banner {
  background: #ecfdf5;
  border-color: #a7f3d0;
}

/* FINAL pill */
.pill.final {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #ef444422;  /* red-ish */
  color: #ef4444;
  border: 1px solid #ef444455;
  font-weight: 800;
}

/* Light theme variants */
:where([data-theme="light"]) .sponsor-rail { background: #f9fafb; border-color: #e5e7eb; }

/* Mobile/Tablet: dock the large rail at the top and shrink a bit */
@media (max-width: 1100px) {
  .board { padding-left: 0; padding-top: 96px; }

  .sponsor-rail {
    top: 10px;
    left: 12px;
    transform: none;
    padding: 8px 10px;
  }
  .rail-large { width: auto; }
  .rail-large img { max-width: 120px; max-height: 60px; }

  /* Keep highlight toast clear of the rail */
  .hl-banner { top: 96px; right: 12px; }
}

/* Presented-by badge in header */
.badge-sponsor {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(0,0,0,.10);
  border: 1px solid rgba(255,255,255,.10);
  text-decoration: none;
}
.badge-sponsor .badge-label { font-size: 11px; color: #9ca3af; font-weight: 700; letter-spacing: .02em; }
.badge-sponsor img { height: 20px; width: auto; display: block; }
:where([data-theme="light"]) .badge-sponsor { background: #f3f4f6; border-color: #e5e7eb; }

/* --- Existing UI styles (unchanged) --- */
.interrupt-banner{
  display:flex; align-items:center; gap:8px;
  padding:8px 10px; margin-bottom:10px;
  border:1px solid rgba(255,255,255,.12);
  background: rgba(16,185,129,.08);
  color:#10b981; border-radius:10px; font-size:13px; font-weight:700;
}
.interrupt-banner .icon{ font-size:16px; }
.interrupt-banner .dot{ opacity:.7; }
.interrupt-banner .note{ font-weight:600; opacity:.9; }
:where([data-theme="light"]) .interrupt-banner{
  background:#ecfdf5; border-color:#a7f3d0; color:#047857;
}

.first-inn {
  margin: 6px 0 0;
  display: flex;
  gap: 8px;
  align-items: baseline;
  color: #9ca3af;
}
.first-inn .lbl { font-size: 12px; }
:where([data-theme="light"]) .first-inn { color: #6b7280; }

.info-strip{
  display: grid;
  /* wrap nicely: each cell is at least 160px, expands up to 1fr */
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;                /* was 8px */
  margin: 12px 0 16px;      /* a little more vertical space */
}

.info-strip .cell{
  background: rgba(0,0,0,.14);
  border: 1px solid rgba(255,255,255,.06);
  border-radius: 10px;
  padding: 10px 14px;       /* was 8px 10px */
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-strip .lbl{ font-size: 12px; color: #9ca3af; }

:where([data-theme="light"]) .info-strip .cell{
  background:#f9fafb; border-color:#e5e7eb;
}

/* (optional) give even more room on big screens */
@media (min-width: 1200px){
  .info-strip{
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
  }
}

.hdr { display: flex; align-items: center; gap: 10px; margin: 10px 0; }
.pill.live { font-size: 12px; padding: 2px 8px; border-radius: 999px; background: #10b98122; color: #10b981; border: 1px solid #10b98155; }
.card { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,.08); border-radius: 14px; padding: 16px; }
.topline { display:flex; justify-content:space-between; align-items: baseline; gap:16px; margin-bottom: 10px; }
.teams { display:flex; gap:8px; align-items:center; color:#9ca3af; }
.score { display:flex; gap:8px; align-items:baseline; }
.big { font-weight: 900; font-size: 28px; letter-spacing: .5px; }
.ov { color:#9ca3af; font-weight:600; }
.grid { display:grid; gap:12px; margin-top: 8px; }
.grid-3 { grid-template-columns: repeat(3, 1fr); }
@media (max-width: 860px) { .grid-3 { grid-template-columns: 1fr; } }
.pane { background: rgba(0,0,0,.18); border:1px solid rgba(255,255,255,.06); border-radius:12px; padding:12px; }
.pane-title { font-weight: 800; font-size: 13px; color:#9ca3af; margin-bottom:8px; }
.row { display:grid; grid-template-columns: 160px 1fr; padding:6px 0; border-top:1px dashed rgba(255,255,255,.06); }
.row:first-of-type { border-top: 0; }
.label { color:#9ca3af; font-size: 13px; }
.val { font-weight: 700; }
.bt { font-weight: 800; margin-right: 6px; opacity: .9; }

:where([data-theme="light"]) .card { background:#fff; border-color:#e5e7eb; }
:where([data-theme="light"]) .pane { background:#f9fafb; border-color:#e5e7eb; }
:where([data-theme="light"]) .ov,
:where([data-theme="light"]) .teams,
:where([data-theme="light"]) .label { color:#6b7280; }

.wide-pane { overflow-x: auto; }
.batting-table th, .batting-table td { padding: 4px 6px; white-space: nowrap; }
.bowling-table th, .bowling-table td { padding: 4px 6px; white-space: nowrap; }
.full-span { grid-column: 1 / -1; display: flex; flex-direction: column; gap: 16px; }

.balls { display:flex; flex-wrap: wrap; gap:6px; }
.ball { min-width: 28px; height: 28px; display:grid; place-items:center; border-radius:999px; border:1px solid rgba(255,255,255,.12); background:rgba(0,0,0,.18); font-weight:800; font-size:12px; }
:where([data-theme="light"]) .ball { background:#f9fafb; border-color:#e5e7eb; }

/* Highlight toast */
.hl-banner{
  position:absolute; top:12px; right:12px; z-index:5;
  padding:6px 10px; border-radius:10px;
  background: rgba(34,211,238,.14);
  border:1px solid rgba(34,211,238,.35);
  color:#22d3ee; font-weight:900; letter-spacing:.04em; font-size:16px;
  animation: hl-pop 800ms ease, hl-fade 1800ms ease forwards;
  pointer-events:none;
}
@keyframes hl-pop { from{ transform:scale(.92); opacity:.4 } to{ transform:scale(1); opacity:1 } }
@keyframes hl-fade { 0%{opacity:1} 70%{opacity:1} 100%{opacity:0} }

:where([data-theme="light"]) .hl-banner{
  background:#e8fbfe; border-color:#a5ecf6; color:#0e7490;
}
</style>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { fmtSR, fmtEconomy, oversDisplayFromBalls } from '@/utils/cricket'
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
  battingRowsXI,   // <— use these
  bowlingRowsXI,
  liveSnapshot,
} = storeToRefs(gameStore)

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
const runs   = computed(() => Number(currentGame.value?.total_runs ?? 0))
const wkts   = computed(() => Number(currentGame.value?.total_wickets ?? 0))
const oversC = computed(() => Number(currentGame.value?.overs_completed ?? 0))
const ballsO = computed(() => Number(currentGame.value?.balls_this_over ?? 0))
const ballsBowled = computed(() => oversC.value * 6 + ballsO.value)

const scoreline = computed(() => `${runs.value}/${wkts.value}`)
const oversText = computed(() => `${oversC.value}.${ballsO.value}`)

const target = computed<number | null>(() => (currentGame.value?.target ?? null) as number | null)
const isSecondInnings = computed(() => Number(currentGame.value?.current_inning ?? 1) === 2)
const oversLimit = computed(() => Number((currentGame.value as any)?.overs_limit ?? 0))

const crr = computed(() => ballsBowled.value ? (runs.value / (ballsBowled.value / 6)).toFixed(2) : '—')
const rrr = computed(() => {
  if (!isSecondInnings.value || target.value == null) return null
  const need = Math.max(0, target.value - runs.value)
  if (!oversLimit.value) return null
  const remBalls = Math.max(0, oversLimit.value * 6 - ballsBowled.value)
  if (remBalls <= 0) return null
  return (need / (remBalls / 6)).toFixed(2)
})
const oversLeft = computed(() => {
  if (!oversLimit.value) return '—'
  const rem = Math.max(0, oversLimit.value * 6 - ballsBowled.value)
  return oversDisplayFromBalls(rem)
})
const parTxt = computed(() => {
  const p = dlsPanel.value as any
  return typeof p?.par === 'number' ? String(p.par) : null
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
// striker/non-striker lookups
const strikerRow = computed(() => {
  const id = String(currentGame.value?.current_striker_id ?? '')
  return id ? battingRowsXI.value.find(r => r.id === id) || null : null
})
const nonStrikerRow = computed(() => {
  const id = String(currentGame.value?.current_non_striker_id ?? '')
  return id ? battingRowsXI.value.find(r => r.id === id) || null : null
})
const bowlerRow = computed(() => {
  const id = String((state.value as any)?.current_bowler_id ?? (currentGame.value as any)?.current_bowler_id ?? '')
  return id ? bowlingRowsXI.value.find(r => r.id === id) || null : null
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
const recentDeliveries = computed<Delivery[]>(() => {
  const del: any[] = Array.isArray((currentGame.value as any)?.deliveries) ? (currentGame.value as any).deliveries : []
  return del.slice(-10)
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

    

   <header class="hdr">
    <!-- brand/logo in header -->
    <img
      v-if="logoUrl && logoOk"
      class="brand"
      :src="logoUrl"
      alt="Logo"
      @error="onLogoErr"
      :key="logoUrl"
    />

    <h3>{{ title || 'Live Scoreboard' }}</h3>
    <span class="pill live">● LIVE</span>

    <!-- Presented by badge -->
    <a v-if="badgeSponsor"
      class="badge-sponsor"
      :href="sponsorHref(badgeSponsor)"
      target="_blank" rel="noopener"
      :aria-label="`Presented by ${sponsorAlt(badgeSponsor)}`">
      <span class="badge-label">Presented by</span>
      <img :src="sponsorImg(badgeSponsor)" :alt="sponsorAlt(badgeSponsor)" />
    </a>
  </header>


    <div v-if="props.canControl && !showInterruptionBanner" class="ctrl-row" style="margin:8px 0;">
      <button class="btn" :disabled="interBusy" @click="startDelay('weather')">
        {{ interBusy ? 'Starting…' : 'Start delay' }}
      </button>
    </div>

    <div v-if="storeError" class="error">{{ storeError }}</div>
    <div v-else class="card">
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
      

      <div class="topline">
        <div class="teams">
          <strong>{{ currentGame?.batting_team_name || '' }}</strong>
          <span>vs</span>
          <strong>{{ currentGame?.bowling_team_name || '' }}</strong>
        </div>
        <div class="score">
          <span class="big">{{ scoreline }}</span>
          <span class="ov">({{ oversText }} ov)</span>
        </div>
      </div>

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

        <!-- Bowler -->
        <div class="pane">
          <div class="pane-title">Bowler</div>
          <div class="row"><div class="label">Name</div><div class="val">{{ bowlerRow?.name || '—' }}</div></div>
          <div class="row">
            <div class="label">Figures</div>
            <div class="val">
              {{ (bowlerRow?.wkts ?? 0) }}-{{ (bowlerRow?.runs ?? 0) }} ({{ bowlerRow?.overs ?? '0.0' }})
            </div>
          </div>
          <div class="row"><div class="label">Economy</div><div class="val">{{ typeof bowlerRow?.econ === 'number' ? bowlerRow?.econ.toFixed(2) : (bowlerRow?.econ ?? '—') }}</div></div>
        </div>

        <!-- Info strip -->
        <div class="info-strip">
          <div class="cell"><span class="lbl">CRR</span><strong>{{ crr }}</strong></div>
          <div v-if="rrr" class="cell"><span class="lbl">RRR</span><strong>{{ rrr }}</strong></div>
          <div v-if="target != null" class="cell"><span class="lbl">Target</span><strong>{{ target }}</strong></div>
          <div v-if="parTxt" class="cell"><span class="lbl">Par</span><strong>{{ parTxt }}</strong></div>
          <div class="cell"><span class="lbl">Overs left</span><strong>{{ oversLeft }}</strong></div>
        </div>

        <!-- Mini scorecards -->
        <div class="full-span">
          <div class="pane wide-pane">
            <div class="pane-title">Batting</div>
            <table class="mini batting-table">
              <thead>
                <tr><th>Player</th><th class="num">R</th><th class="num">B</th><th class="num">4s</th><th class="num">6s</th><th class="num">SR</th><th>Status</th></tr>
              </thead>
              <tbody>
                <tr v-for="b in battingRowsXI" :key="b.id">
                  <td class="name">{{ b.name }}</td>
                  <td class="num">{{ b.runs }}</td>
                  <td class="num">{{ b.balls }}</td>
                  <td class="num">{{ b.fours }}</td>
                  <td class="num">{{ b.sixes }}</td>
                  <td class="num">{{ b.sr }}</td>
                  <td class="status">{{ b.isOut ? (b.howOut ? `Out (${b.howOut})` : 'Out') : 'Not out' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="pane wide-pane">
            <div class="pane-title">Bowling</div>
            <table class="mini bowling-table">
              <thead>
                <tr><th>Bowler</th><th class="num">O</th><th class="num">M</th><th class="num">R</th><th class="num">W</th><th class="num">Econ</th></tr>
              </thead>
              <tbody>
                <tr v-for="bw in bowlingRowsXI" :key="bw.id">
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
      </div>
    </div>
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

.info-strip{
  display:grid; grid-template-columns: repeat(5, minmax(0,1fr));
  gap:8px; margin:8px 0 12px;
}
.info-strip .cell{
  background: rgba(0,0,0,.14);
  border:1px solid rgba(255,255,255,.06);
  border-radius:10px; padding:8px 10px; display:flex; justify-content:space-between; align-items:center;
}
.info-strip .lbl{ font-size:12px; color:#9ca3af; }
:where([data-theme="light"]) .info-strip .cell{ background:#f9fafb; border-color:#e5e7eb; }

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

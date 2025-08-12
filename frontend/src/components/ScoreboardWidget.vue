<template>
  <section :class="['csw-root', themeClass]">
    <!-- Header -->
    <header class="csw-header" v-if="title || logo">
      <img v-if="logo" :src="logo" alt="" class="csw-logo" />
      <h1 class="csw-title">{{ title }}</h1>
      <span class="csw-live" :class="{ on: isConnected }">
        <span class="dot"></span>{{ isConnected ? 'LIVE' : 'RECONNECTING' }}
      </span>
    </header>

    <!-- Scoreboard payload states -->
    <div v-if="loading" class="csw-loading">Loading scoreboard…</div>
    <div v-else-if="error" class="csw-error">{{ error }}</div>

    <div v-else class="csw-scoreboard">
      <!-- Topline -->
      <div class="csw-topline">
        <div class="csw-score">
          <div class="teams">
            <strong class="team">{{ snapshot?.teams?.batting?.name || '--' }}</strong>
            <span class="sep">vs</span>
            <strong class="team">{{ snapshot?.teams?.bowling?.name || '--' }}</strong>
          </div>
          <div class="scoreline">
            <span class="runs">{{ snapshot?.score?.runs ?? 0 }}</span>/<span class="wkts">{{ snapshot?.score?.wickets ?? 0 }}</span>
            <span class="overs">({{ snapshot?.score?.overs ?? 0 }} ov)</span>
          </div>
        </div>

        <div class="csw-batsmen">
          <div class="bat">
            <span class="name">{{ snapshot?.batsmen?.striker?.name || '-' }}*</span>
            <span class="stat">{{ snapshot?.batsmen?.striker?.runs ?? 0 }} ({{ snapshot?.batsmen?.striker?.balls ?? 0 }})</span>
          </div>
          <div class="bat">
            <span class="name">{{ snapshot?.batsmen?.non_striker?.name || '-' }}</span>
            <span class="stat">{{ snapshot?.batsmen?.non_striker?.runs ?? 0 }} ({{ snapshot?.batsmen?.non_striker?.balls ?? 0 }})</span>
          </div>
        </div>
      </div>

      <!-- Sponsors (optional) -->
      <div class="csw-sponsors" v-if="resolvedSponsors.length">
        <SponsorsBar
          :sponsors="resolvedSponsors"
          :sponsor-rotate-ms="sponsorRotateMs"
          :sponsor-clickable="sponsorClickable"
          @impression="onImpression"
          @click="onSponsorClick"
        />
      </div>

      <!-- Analytics mini-cards -->
      <AnalyticsStrip
        :snapshot="snapshot"
        :striker-dots="strikerDots"
        :striker-balls="strikerBalls"
        :bowler-dots="bowlerDotsC"
        :bowler-balls="bowlerBallsC"
      />

      <!-- Celebration overlay -->
      <EventOverlay
        :event="currentHighlight"
        :visible="enableAnimations"
        :duration="animationDurationMs"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import SponsorsBar, { type Sponsor } from '@/components/SponsorsBar.vue'
import EventOverlay from '@/components/EventOverlay.vue'
import AnalyticsStrip from '@/components/AnalyticsStrip.vue'
import { useHighlights, type Snapshot as HiSnapshot } from '@/composables/useHighlights'

// ---------- Props ----------
const props = withDefaults(defineProps<{
  // Scoreboard basics
  theme?: 'auto' | 'dark' | 'light'
  title?: string
  logo?: string
  apiBase?: string
  gameId?: string

  // Sponsors
  sponsors?: Sponsor[]
  sponsorsUrl?: string
  sponsorRotateMs?: number
  sponsorClickable?: boolean

  // Animations
  enableAnimations?: boolean
  animationDurationMs?: number
}>(), {
  theme: 'auto',
  title: '',
  logo: '',
  apiBase: (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000',
  gameId: '',
  sponsors: () => [],
  sponsorsUrl: '',
  sponsorRotateMs: 8000,
  sponsorClickable: false,
  enableAnimations: true,
  animationDurationMs: 1800,
})

// ---------- State ----------
type ApiSnapshot = {
  id: string
  score: { runs: number; wickets: number; overs: number }
  batsmen: {
    striker: { id: string; name: string; runs: number; balls: number }
    non_striker: { id: string; name: string; runs: number; balls: number }
  }
  teams?: { batting?: { name: string }, bowling?: { name: string } }
  bowler?: { id?: string; name?: string } | null // optional; card auto-hides if absent
}

const route = useRoute()
const routeGameId = computed(() => String(route.params.gameId ?? ''))
const gameId = computed(() => props.gameId || routeGameId.value)

const themeClass = computed(() => `theme-${props.theme}`)
const isConnected = ref(true) // placeholder; wire to Socket.IO presence when ready

const loading = ref(false)
const error = ref<string | null>(null)
const snapshot = ref<ApiSnapshot | null>(null)

// Sponsors data when fetched from URL
const sponsorsFromUrl = ref<Sponsor[]>([])
const resolvedSponsors = computed<Sponsor[]>(() => {
  return (props.sponsors && props.sponsors.length) ? props.sponsors : sponsorsFromUrl.value
})

// ---------- Highlights state ----------
const prevSnap = ref<HiSnapshot | null>(null)
const currSnap = ref<HiSnapshot | null>(null)

const enableAnimRef = ref<boolean>(props.enableAnimations)
const durationRef = ref<number>(props.animationDurationMs)
const { current: currentHighlight, enqueueFromSnapshots, reset } = useHighlights(enableAnimRef, durationRef)

// keep props reactive
watch(() => props.enableAnimations, (v) => { enableAnimRef.value = !!v; if (!v) reset() })
watch(() => props.animationDurationMs, (v) => { if (typeof v === 'number') durationRef.value = v })

// ---------- Dot-ball analytics counters (session-based) ----------
type DotCounters = { balls: number; dots: number }
const batterDots = ref<Record<string, DotCounters>>({})
const bowlerDots = ref<Record<string, DotCounters>>({})

function ensureCounter(map: Record<string, DotCounters>, id: string) {
  if (!map[id]) map[id] = { balls: 0, dots: 0 }
}
function incBatter(batterId: string, isDot: boolean) {
  ensureCounter(batterDots.value, batterId)
  batterDots.value[batterId].balls += 1
  if (isDot) batterDots.value[batterId].dots += 1
}
function incBowler(bowlerId: string, isDot: boolean) {
  ensureCounter(bowlerDots.value, bowlerId)
  bowlerDots.value[bowlerId].balls += 1
  if (isDot) bowlerDots.value[bowlerId].dots += 1
}

// ---------- Mapping helpers ----------
function toHiSnapshot(api: ApiSnapshot | null): HiSnapshot | null {
  if (!api) return null
  return {
    total: { runs: api.score?.runs ?? 0, wickets: api.score?.wickets ?? 0 },
    striker: {
      id: api.batsmen?.striker?.id,
      name: api.batsmen?.striker?.name,
      runs: api.batsmen?.striker?.runs,
      balls: api.batsmen?.striker?.balls,
    },
    nonStriker: {
      id: api.batsmen?.non_striker?.id,
      name: api.batsmen?.non_striker?.name,
      runs: api.batsmen?.non_striker?.runs,
      balls: api.batsmen?.non_striker?.balls,
    },
  }
}

// Given previous & next API snapshots, infer lastBall semantics for boundaries / wicket / dot attribution
function inferLastBall(prevApi: ApiSnapshot | null, nextApi: ApiSnapshot | null) {
  if (!prevApi || !nextApi) return null

  const pRuns = prevApi.score?.runs ?? 0
  const nRuns = nextApi.score?.runs ?? 0
  const pWkts = prevApi.score?.wickets ?? 0
  const nWkts = nextApi.score?.wickets ?? 0

  const deltaRuns = nRuns - pRuns
  const wicketUp = nWkts > pWkts

  // Determine facing batter by balls increment (legal deliveries only)
  const prevSB = prevApi.batsmen?.striker?.balls ?? 0
  const prevNB = prevApi.batsmen?.non_striker?.balls ?? 0
  const nextSB = nextApi.batsmen?.striker?.balls ?? 0
  const nextNB = nextApi.batsmen?.non_striker?.balls ?? 0

  let facingBatterId: string | undefined
  let batterRuns: number | undefined
  let isLegalDelivery = false

  if (nextSB === prevSB + 1) {
    facingBatterId = prevApi.batsmen?.striker?.id
    batterRuns = (nextApi.batsmen?.striker?.runs ?? 0) - (prevApi.batsmen?.striker?.runs ?? 0)
    isLegalDelivery = true
  } else if (nextNB === prevNB + 1) {
    facingBatterId = prevApi.batsmen?.non_striker?.id
    batterRuns = (nextApi.batsmen?.non_striker?.runs ?? 0) - (prevApi.batsmen?.non_striker?.runs ?? 0)
    isLegalDelivery = true
  } else {
    // Wide/no-ball likely; don't count in dot% balls
    isLegalDelivery = false
  }

  // Guess dismissed batter (for DUCK decision upstream)
  let dismissedBatterId: string | undefined
  if (wicketUp) {
    const strikerChanged = prevApi.batsmen?.striker?.id !== nextApi.batsmen?.striker?.id
    const nonStrikerChanged = prevApi.batsmen?.non_striker?.id !== nextApi.batsmen?.non_striker?.id
    if (strikerChanged) dismissedBatterId = prevApi.batsmen?.striker?.id
    else if (nonStrikerChanged) dismissedBatterId = prevApi.batsmen?.non_striker?.id
  }

  return {
    runs: deltaRuns,
    isBoundary4: deltaRuns === 4,
    isBoundary6: deltaRuns === 6,
    isWicket: wicketUp,
    dismissedBatterId,
    // added for analytics
    facingBatterId,
    batterRuns,
    isLegalDelivery,
  }
}

function onSnapshotUpdate(nextApi: ApiSnapshot | null) {
  // Move current -> prev
  const previousApi = snapshot.value
  snapshot.value = nextApi

  const prev = toHiSnapshot(previousApi)
  const next = toHiSnapshot(nextApi)

  // Attach inferred lastBall on next snapshot for event detection + dot analytics
  if (next && previousApi && nextApi) {
    next.lastBall = inferLastBall(previousApi, nextApi) || undefined
  }

  prevSnap.value = currSnap.value
  currSnap.value = next

  // Drive highlights
  enqueueFromSnapshots(prevSnap.value, currSnap.value)

  // Update dot analytics (session)
  if (previousApi && nextApi && next?.lastBall) {
    const lb: any = next.lastBall
    if (lb.isLegalDelivery && lb.facingBatterId) {
      const isDotForBatter = (lb.batterRuns ?? 0) === 0 && !lb.isWicket
      incBatter(lb.facingBatterId, isDotForBatter)

      const bowlerId = nextApi.bowler?.id || nextApi.bowler?.name
      if (bowlerId) {
        incBowler(String(bowlerId), isDotForBatter)
      }
    }
  }
}

// ---------- Fetch: scoreboard snapshot ----------
async function fetchSnapshot() {
  if (!gameId.value) return
  loading.value = true
  error.value = null
  try {
    const res = await fetch(`${props.apiBase}/games/${gameId.value}/snapshot`, { cache: 'no-store' })
    if (!res.ok) throw new Error(await res.text())
    const data: ApiSnapshot = await res.json()
    onSnapshotUpdate(data)
  } catch (e: any) {
    error.value = e?.message || 'Failed to load'
  } finally {
    loading.value = false
  }
}

// ---------- Fetch: sponsors (if sponsorsUrl provided) ----------
async function fetchSponsors() {
  if (!props.sponsorsUrl) { sponsorsFromUrl.value = []; return }
  try {
    const res = await fetch(props.sponsorsUrl, { cache: 'no-store' })
    if (!res.ok) throw new Error(await res.text())
    const arr = await res.json()
    // Expecting [{ id, name, logoUrl, clickUrl, ... }]
    sponsorsFromUrl.value = Array.isArray(arr) ? arr.filter((x: any) => x?.logoUrl) : []
  } catch (e) {
    // Fail silently for the widget; just don’t show sponsors if fetch fails
    sponsorsFromUrl.value = []
  }
}

// ---------- Impression logging (PR 10) ----------
async function logImpression(sp: Sponsor | null) {
  if (!sp || !gameId.value) return
  try {
    await fetch(`${props.apiBase}/sponsor_impressions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        game_id: gameId.value,
        sponsor_id: sp.id ?? sp.name, // prefer real id; fallback name
        at: new Date().toISOString(),
      }),
      keepalive: true
    })
  } catch {
    /* non-fatal */
  }
}
function onImpression(sp: Sponsor | null) { logImpression(sp) }
function onSponsorClick(sp: Sponsor | null) {
  // Optional: could add click tracking later
}

// ---------- Lifecyle ----------
onMounted(() => {
  fetchSnapshot()
  fetchSponsors()
})
watch(gameId, () => fetchSnapshot())
watch(() => props.sponsorsUrl, () => fetchSponsors())

// ---------- Computed: analytics getters for strip ----------
const strikerId = computed(() => snapshot.value?.batsmen?.striker?.id || '')
const bowlerKey = computed(() => {
  const b = snapshot.value?.bowler
  return b?.id ? String(b.id) : (b?.name ? String(b.name) : '')
})

const strikerDots = computed(() => (strikerId.value && batterDots.value[strikerId.value]?.dots) || 0)
const strikerBalls = computed(() => (strikerId.value && batterDots.value[strikerId.value]?.balls) || 0)
const bowlerDotsC = computed(() => (bowlerKey.value && bowlerDots.value[bowlerKey.value]?.dots) || 0)
const bowlerBallsC = computed(() => (bowlerKey.value && bowlerDots.value[bowlerKey.value]?.balls) || 0)
</script>

<style scoped>
.csw-root {
  --bg: #0b0f1a;
  --fg: #e5e7eb;
  --muted: #9ca3af;
  --accent: #22d3ee;
  color: var(--fg);
  background: var(--bg);
  border-radius: 16px;
  padding: 12px 12px 4px;
  box-shadow: 0 8px 24px rgba(0,0,0,.25);
}

/* Light theme override */
.theme-light { --bg: #ffffff; --fg: #111827; --muted: #6b7280; --accent: #0ea5e9; }

/* “Auto” theme adapts to OS preference (not empty) */
@media (prefers-color-scheme: light) {
  .theme-auto { --bg: #ffffff; --fg: #111827; --muted: #6b7280; --accent: #0ea5e9; }
}

/* Header — filled so it’s not an empty ruleset */
.csw-header {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 12px;
  align-items: center;
  margin-bottom: 6px;
}
.csw-logo { height: 28px; object-fit: contain; }
.csw-title { font-size: 14px; font-weight: 700; letter-spacing: .02em; margin: 0; }
.csw-live { font-size: 12px; color: var(--muted); display: inline-flex; align-items: center; gap: 6px; }
.csw-live .dot { width: 8px; height: 8px; border-radius: 50%; background: #f59e0b; display: inline-block; }
.csw-live.on .dot { background: #22c55e; }

/* Loading / error */
.csw-loading, .csw-error { padding: 24px; text-align: center; color: var(--muted); }

/* Scoreboard layout */
.csw-scoreboard {
  display: grid;
  gap: 10px;
  position: relative; /* <-- allow overlay absolute positioning */
}
.csw-topline {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
  align-items: center;
}
.csw-score .teams { font-size: 14px; color: var(--muted); display: flex; gap: 6px; align-items: baseline; }
.csw-score .team { color: var(--fg); }
.csw-score .sep { opacity: .6 }
.csw-score .scoreline { font-size: 24px; font-weight: 800; letter-spacing: .02em; }
.csw-score .runs, .csw-score .wkts { font-variant-numeric: tabular-nums; }
.csw-score .overs { font-size: 12px; color: var(--muted); margin-left: 8px; }

/* Batsmen row */
.csw-batsmen { display: grid; grid-auto-flow: column; gap: 14px; }
.csw-batsmen .bat { display: grid; grid-auto-flow: column; gap: 6px; font-size: 12px; color: var(--muted); }
.csw-batsmen .name { color: var(--fg); font-weight: 600; }

/* Sponsors bar — center logos, add divider, ensure fit */
.csw-sponsors {
  margin-top: 6px;
  border-top: 1px solid rgba(255,255,255,.06);
  padding-top: 6px;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 56px;
}
.csw-sponsors img {
  max-height: 44px;
  max-width: 100%;
  object-fit: contain;
  filter: drop-shadow(0 1px 1px rgba(0,0,0,.2));
}
</style>

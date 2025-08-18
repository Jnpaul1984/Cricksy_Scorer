<script setup lang="ts">
/* --- Vue & Router --- */
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/* --- Stores --- */
import { useGameStore } from '@/stores/gameStore'

/* --- UI Components --- */
import ScoringPanel from '@/components/scoring/ScoringPanel.vue'
import DeliveryTable from '@/components/DeliveryTable.vue'
import BattingCard from '@/components/BattingCard.vue'
import BowlingCard from '@/components/BowlingCard.vue'
import CompactPad from '@/components/CompactPad.vue'
import PresenceBar from '@/components/PresenceBar.vue'
import ScoreboardWidget from '@/components/ScoreboardWidget.vue'
import { storeToRefs } from 'pinia'

// ================== Local domain types (narrow) ==================
type UUID = string

type Player = { id: UUID; name: string }

type Team = {
  name: string
  players: Player[]
  playing_xi?: UUID[]
}

type BatCardEntry = {
  player_id: UUID
  player_name: string
  runs: number
  balls_faced: number
  fours: number
  sixes: number
  strike_rate: number
  how_out?: string
  is_out: boolean
}

type BowlCardEntry = {
  player_id: UUID
  player_name: string
  overs_bowled: number
  maidens: number
  runs_conceded: number
  wickets_taken: number
  economy: number
}

type DeliveryRowForTable = {
  over_number: number
  ball_number: number
  runs_scored: number
  striker_id: UUID
  non_striker_id: UUID
  bowler_id: UUID
  extra?: 'wd' | 'nb' | 'b' | 'lb'
  is_wicket?: boolean
  commentary?: string
  dismissed_player_id?: UUID | null
  at_utc?: string
}

// ================== ROUTE + STORE ==================
const route = useRoute()
const router = useRouter()
const gameStore = useGameStore()

// Reactive refs from the store (always stays in sync)
const { canScore, liveSnapshot } = storeToRefs(gameStore)
// If you also want flags directly:
const { needsNewBatter, needsNewOver } = storeToRefs(gameStore)

const { extrasBreakdown } = storeToRefs(gameStore)


// Current gameId (param or ?id=)
const gameId = computed<string>(() => (route.params.gameId as string) || (route.query.id as string) || '')

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
  } catch {
    // ignore
  }
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
const battingPlayers = computed<Player[]>(() => {
  const g = gameStore.currentGame as unknown as { batting_team_name?: string; team_a?: Team; team_b?: Team } | null
  if (!g) return []
  const battingIsA = g.batting_team_name === g.team_a?.name
  const team = (battingIsA ? g.team_a : g.team_b) as Team | undefined
  const all = team?.players ?? []
  if (!xiLoaded.value) return all
  const xiSet = (battingIsA ? xiA.value : xiB.value) ?? (team?.playing_xi && team.playing_xi.length ? new Set(team.playing_xi) : null)
  return xiSet ? all.filter((p) => xiSet.has(p.id)) : all
})

const bowlingPlayers = computed<Player[]>(() => {
  const g = gameStore.currentGame as unknown as { bowling_team_name?: string; team_a?: Team; team_b?: Team } | null
  if (!g) return []
  const bowlingIsA = g.bowling_team_name === g.team_a?.name
  const team = (bowlingIsA ? g.team_a : g.team_b) as Team | undefined
  const all = team?.players ?? []
  if (!xiLoaded.value) return all
  const xiSet = (bowlingIsA ? xiA.value : xiB.value) ?? (team?.playing_xi && team.playing_xi.length ? new Set(team.playing_xi) : null)
  return xiSet ? all.filter((p) => xiSet.has(p.id)) : all
})

// Can score? prevent same batter in both roles



// Names for status text (useful in UI / a11y hints)
const selectedStrikerName = computed<string>(() => battingPlayers.value.find((p) => p.id === selectedStriker.value)?.name || '')
const selectedBowlerName = computed<string>(() => bowlingPlayers.value.find((p) => p.id === selectedBowler.value)?.name || '')

// ================== SCORECARDS (from store) ==================
const battingEntries = computed<BatCardEntry[]>(() =>
  gameStore.battingRows.map((r: any) => ({
    player_id: r.id as UUID,
    player_name: String(r.name),
    runs: Number(r.runs),
    balls_faced: Number(r.balls),
    fours: Number(r.fours),
    sixes: Number(r.sixes),
    strike_rate: Number(r.sr),
    how_out: r.howOut as string | undefined,
    is_out: Boolean(r.isOut),
  }))
)

const bowlingEntries = computed<BowlCardEntry[]>(() =>
  gameStore.bowlingRows.map((r: any) => ({
    player_id: r.id as UUID,
    player_name: String(r.name),
    overs_bowled: Number(r.overs),
    maidens: Number(r.maidens),
    runs_conceded: Number(r.runs),
    wickets_taken: Number(r.wkts),
    economy: Number(r.econ),
  }))
)

// ================== Deliveries (DEDUPE) ==================
// Some backends + optimistic UI can emit the same delivery twice (e.g., via socket + refetch).
// We dedupe by a stable key and prefer the *latest* occurrence.
function makeKey(d: any): string {
  // include batter swap edge cases by keying on over, ball, striker and bowler
  const o = Number(d.over_number ?? d.over ?? 0)
  const b = Number(d.ball_number ?? d.ball ?? 0)
  const s = String(d.striker_id ?? '')
  const bw = String(d.bowler_id ?? '')
  return `${o}:${b}:${s}:${bw}`
}

const rawDeliveries = computed<any[]>(() => {
  const g = gameStore.currentGame as any
  return Array.isArray(g?.deliveries) ? g.deliveries : []
})

const dedupedDeliveries = computed<DeliveryRowForTable[]>(() => {
  const byKey = new Map<string, any>()
  for (const d of rawDeliveries.value) {
    byKey.set(makeKey(d), d) // last one wins
  }
  const parseOverBall = (overLike: unknown, ballLike: unknown) => {
    if (typeof ballLike === 'number') {
      return { over: Math.max(0, Math.floor(Number(overLike) || 0)), ball: ballLike }
    }
    if (typeof overLike === 'string') {
      const [o, b] = overLike.split('.')
      return { over: Number(o) || 0, ball: Number(b) || 0 }
    }
    if (typeof overLike === 'number') {
      const over = Math.floor(overLike)
      const ball = Math.max(0, Math.round((overLike - over) * 10))
      return { over, ball }
    }
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
function sr(runs: number, balls: number): string {
  if (!balls) return '—'
  return (runs * 100 / balls).toFixed(1)
}
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

console.log('store.currentGame?.id', (gameStore.currentGame as any)?.id, 'status', (gameStore.currentGame as any)?.status)

// ================== Live strip data (current bowler / over) ==================
const stateAny = computed(() => gameStore.state as any)
const currentBowlerId = computed<UUID | null>(() => (stateAny.value?.currentBowlerId ?? stateAny.value?.current_bowler_id ?? null) as UUID | null)
const lastBallBowlerId = computed<UUID | null>(() => (stateAny.value?.lastBallBowlerId ?? stateAny.value?.last_ball_bowler_id ?? null) as UUID | null)
const currentOverBalls = computed<number>(() => Number(stateAny.value?.currentOverBalls ?? stateAny.value?.current_over_balls ?? 0))
const midOverChangeUsed = computed<boolean>(() => Boolean(stateAny.value?.midOverChangeUsed ?? stateAny.value?.mid_over_change_used))

const currentBowler = computed<Player | null>(() => {
  const id = currentBowlerId.value
  if (!id) return null
  return bowlingPlayers.value.find(p => p.id === id) || null
})

// Bowler stats (from store if available, else aggregate from DEDUPED deliveries)
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

// Over display (global innings balls total from store if exposed; fallback from DEDUPED deliveries)
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

// Eligible next-over bowlers (cannot equal lastBallBowlerId)
const eligibleNextOverBowlers = computed<Player[]>(() => bowlingPlayers.value.filter(p => p.id !== lastBallBowlerId.value))

// Mid‑over change options (must differ from current bowler)
const replacementOptions = computed<Player[]>(() => bowlingPlayers.value.filter(p => p.id !== currentBowlerId.value))

const canUseMidOverChange = computed<boolean>(() => currentOverBalls.value < 6 && !midOverChangeUsed.value)
const overInProgress = computed<boolean>(() => Number((stateAny.value?.balls_this_over ?? 0)) > 0)

// Score summary for the strip
const inningsScore = computed<{ runs: number; wickets: number }>(() => ({
  runs: Number((gameStore as any).score?.runs ?? 0),
  wickets: Number((gameStore as any).score?.wickets ?? 0),
}))

// ================== EMBED / SHARE PANEL ==================
const theme = ref<'auto' | 'dark' | 'light'>('dark')
const title = ref<string>('Live Scoreboard')
const logo = ref<string>('')
const height = ref<number>(180)

const apiBase: string = (import.meta as any).env?.VITE_API_BASE || window.location.origin
const sponsorsUrl = computed<string>(() => (gameId.value ? `${apiBase}/games/${encodeURIComponent(gameId.value)}/sponsors` : ''))

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

// ================== Swap ==================
function swapBatsmen(): void {
  const t = selectedStriker.value
  selectedStriker.value = selectedNonStriker.value
  selectedNonStriker.value = t
}

// ================== Lifecycle ==================
onMounted(() => {
  if (needsNewBatter.value) openSelectBatter()
  if (needsNewOver.value) openStartOver()
})

onMounted(async () => {
  const id = gameId.value
  if (!id) { void router.replace('/') ; return }
  try {
    await gameStore.loadGame(id)
    gameStore.initLive(id)
  } catch (e) {
    showToast('Failed to load or connect', 'error', 3000)
    console.error('load/init failed:', e)
  }
})

onUnmounted(() => {
  if (toastTimer) window.clearTimeout(toastTimer)
  gameStore.stopLive()
})


// Keep selections valid when innings flips or XI loads
watch([battingPlayers, bowlingPlayers, xiLoaded], () => {
  if (selectedStriker.value && !battingPlayers.value.find((p) => p.id === selectedStriker.value)) selectedStriker.value = ''
  if (selectedNonStriker.value && !battingPlayers.value.find((p) => p.id === selectedNonStriker.value)) selectedNonStriker.value = ''
  if (selectedBowler.value && !bowlingPlayers.value.find((p) => p.id === selectedBowler.value)) selectedBowler.value = ''
})

watch(() => [ (gameStore.currentGame as any)?.batting_team_name, (gameStore.currentGame as any)?.bowling_team_name ], () => {
  if (selectedStriker.value && !battingPlayers.value.find(p => p.id === selectedStriker.value)) selectedStriker.value = ''
  if (selectedNonStriker.value && !battingPlayers.value.find(p => p.id === selectedNonStriker.value)) selectedNonStriker.value = ''
  if (selectedBowler.value && !bowlingPlayers.value.find(p => p.id === selectedBowler.value)) selectedBowler.value = ''
})

watch(needsNewBatter, (v) => {
  if (v) openSelectBatter()
})
watch(needsNewOver, (v) => {
  if (v) openStartOver()
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

// ================== Start Over & Mid‑over Change ==================
const startOverDlg = ref<HTMLDialogElement | null>(null)
const changeBowlerDlg = ref<HTMLDialogElement | null>(null)
const selectedNextOverBowlerId = ref<UUID>('')
const selectedReplacementBowlerId = ref<UUID>('')
const selectBatterDlg = ref<HTMLDialogElement | null>(null)
const selectedNextBatterId = ref<UUID>('')

const candidateBatters = computed<Player[]>(() => {
  const anyStore = gameStore as any
  if (Array.isArray(anyStore.availableBatsmen) && anyStore.availableBatsmen.length) {
    return anyStore.availableBatsmen as Player[]
  }
  const outSet = new Set(battingEntries.value.filter(b => b.is_out).map(b => b.player_id))
  return battingPlayers.value.filter(p => !outSet.has(p.id))
})

function openSelectBatter(): void { selectedNextBatterId.value = ''; selectBatterDlg.value?.showModal() }
function closeSelectBatter(): void { selectBatterDlg.value?.close() }

// Select next batter
async function confirmSelectBatter() {
  const batter = selectedNextBatterId.value
  if (!batter) return
  await (gameStore as any).replaceBatter(gameId.value, batter)   // ← pass gameId

  const last: any =
    liveSnapshot.value?.last_delivery ||
    (gameStore.currentGame as any)?.deliveries?.slice(-1)?.[0] ||
    null
  const dismissed = (last?.dismissed_player_id || '') as UUID

  if (dismissed && selectedStriker.value === dismissed)          selectedStriker.value = batter
  else if (dismissed && selectedNonStriker.value === dismissed)  selectedNonStriker.value = batter
  else if (!selectedStriker.value)                               selectedStriker.value = batter
  else if (!selectedNonStriker.value)                            selectedNonStriker.value = batter

  showToast('Next batter set', 'success')
  closeSelectBatter()
}

function openStartOver(): void {
  selectedNextOverBowlerId.value = ''
  startOverDlg.value?.showModal()
}
function closeStartOver(): void {
  startOverDlg.value?.close()
}

async function confirmStartOver(): Promise<void> {
  const id = gameId.value
  const bowler = selectedNextOverBowlerId.value
  if (!id || !bowler) return
  try {
    await (gameStore as any).startNewOver(id, bowler)
    showToast('Over started', 'success')
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'Failed to start over'
    onError(msg)
  }
  closeStartOver()
}







function openChangeBowler(): void { selectedReplacementBowlerId.value = ''; changeBowlerDlg.value?.showModal() }
function closeChangeBowler(): void { changeBowlerDlg.value?.close() }

async function confirmChangeBowler(): Promise<void> {
  const id = gameId.value
  const repl = selectedReplacementBowlerId.value
  if (!id || !repl) return
  try {
    const res = await fetch(`${apiBase}/games/${encodeURIComponent(id)}/overs/change_bowler`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ new_bowler_id: repl, reason: 'injury' })
    })
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to change bowler')
    showToast('Bowler changed', 'success')
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : 'Failed to change bowler'
    showToast(msg, 'error', 3000)
  }
  closeChangeBowler()
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
      <!-- Live scoreboard preview (socket-driven) -->
      <ScoreboardWidget
        class="mb-3"
        :game-id="gameId"
        :theme="theme"
        :title="title"
        :logo="logo"
        :api-base="apiBase"
      />

      <PresenceBar class="mb-3" :game-id="gameId" :status="gameStore.connectionStatus" :pending="pendingCount" />

      <!-- Bowling controls (optional) -->
      <section class="selectors card alt">
        <div class="row tight">
          <div class="col">
            <button class="btn" :disabled="overInProgress" @click="openStartOver"></button>
            <small class="hint">Disables previous over's last bowler.</small>
          </div>
          <div class="col">
            <button class="btn" :disabled="!canUseMidOverChange" @click="openChangeBowler">Mid‑over Change</button>
            <small class="hint">Allowed once per over (injury).</small>
          </div>
          <div class="col bowler-now" v-if="currentBowler">
            <strong>Current:</strong> {{ currentBowler.name }} ·
            <span>{{ oversDisplayFromBalls(currentBowlerStats.balls) }}‑{{ currentBowlerStats.runs }}</span>
            <span> · Econ {{ econ(currentBowlerStats.runs, currentBowlerStats.balls) }}</span>
          </div>
        </div>
      </section>

      <!-- Gate banners (explain why scoring is disabled) -->
      <div v-if="needsNewBatter || needsNewOver" class="placeholder mb-3" role="status" aria-live="polite">
        <div v-if="needsNewBatter">New batter required. <button class="btn btn-ghost" @click="openSelectBatter">Select next batter</button></div>
        <div v-if="needsNewOver">New over required. <button class="btn btn-ghost" @click="openStartOver">Choose bowler</button></div>
      </div>

      <!-- Existing scoring panel -->
      <ScoringPanel
        :game-id="gameId"
        :can-score="canScore"
        :striker-id="selectedStriker"
        :non-striker-id="selectedNonStriker"
        :bowler-id="selectedBowler"
        :batting-players="battingPlayers"
        @swap="swapBatsmen"
        @scored="onScored"
        @error="onError"
      />

      <pre class="dev-debug">
      canScore: {{ canScore }}
      striker: {{ selectedStriker }} ({{ selectedStrikerName }})
      nonStriker: {{ selectedNonStriker }}
      bowler: {{ selectedBowler }} ({{ selectedBowlerName }})
      battingPlayers: {{ battingPlayers.length }} | bowlingPlayers: {{ bowlingPlayers.length }}
      </pre>

      <!-- Player selectors -->
      <section class="selectors card">
        <div class="row">
          <div class="col">
            <label class="lbl" for="sel-striker">Striker</label>
            <select id="sel-striker" name="striker" class="sel" v-model="selectedStriker" :disabled="battingPlayers.length === 0" title="Choose striker" aria-describedby="sel-striker-hint">
              <option disabled value="">Choose striker</option>
              <option v-for="p in battingPlayers" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
            <small id="sel-striker-hint" class="hint">Pick a batter on strike · SR updates live</small>
          </div>

          <div class="col">
            <label class="lbl" for="sel-nonstriker">Non‑striker</label>
            <select id="sel-nonstriker" name="nonStriker" class="sel" v-model="selectedNonStriker" :disabled="battingPlayers.length === 0" title="Choose non-striker" aria-describedby="sel-nonstriker-hint">
              <option disabled value="">Choose non‑striker</option>
              <option v-for="p in battingPlayers" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
            <small id="sel-nonstriker-hint" class="hint">Pick the other batter</small>
          </div>

          <div class="col">
            <label class="lbl" for="sel-bowler">Bowler</label>
            <select id="sel-bowler" name="bowler" class="sel" v-model="selectedBowler" :disabled="bowlingPlayers.length === 0" title="Choose bowler" aria-describedby="sel-bowler-hint">
              <option disabled value="">Choose bowler</option>
              <option v-for="p in bowlingPlayers" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
            <small id="sel-bowler-hint" class="hint">Current over bowler</small>
          </div>


          <div class="col align-end">
            <button class="btn" :disabled="overInProgress || needsNewOver" @click="openStartOver">Start Next Over</button>
            <div class="debug">
              canScore: <b>{{ String(canScore) }}</b>
              &nbsp;|&nbsp; S: {{ selectedStriker || '∅' }}
              &nbsp;|&nbsp; NS: {{ selectedNonStriker || '∅' }}
              &nbsp;|&nbsp; B: {{ selectedBowler || '∅' }}
            </div>
          </div>
        </div>
      </section>

      <!-- Live strip: score + batters with SR -->
      <section class="live-strip">
        <div class="score">
          <strong>{{ inningsScore.runs }} / {{ inningsScore.wickets }}</strong>
          <span>({{ oversDisplay }})</span>
        </div>
        <div class="batters">
          <div class="batter">
            <strong>Striker:</strong>
            <span>{{ playerNameById(selectedStriker) || '—' }}</span>
            <span v-if="battingEntries.length">
              <template v-for="b in battingEntries" :key="b.player_id">
                <template v-if="b.player_id === selectedStriker">
                  {{ b.runs }} ({{ b.balls_faced }}) • SR {{ sr(b.runs, b.balls_faced) }}
                </template>
              </template>
            </span>
          </div>
          <div class="batter">
            <strong>Non‑striker:</strong>
            <span>{{ playerNameById(selectedNonStriker) || '—' }}</span>
            <span v-if="battingEntries.length">
              <template v-for="b in battingEntries" :key="b.player_id + '-ns'">
                <template v-if="b.player_id === selectedNonStriker">
                  {{ b.runs }} ({{ b.balls_faced }}) • SR {{ sr(b.runs, b.balls_faced) }}
                </template>
              </template>
            </span>
          </div>
        </div>
        <div class="bowler" v-if="currentBowler">
          <strong>Bowler:</strong>
          <span>{{ currentBowler.name }}</span>
          <span>
            {{ oversDisplayFromBalls(currentBowlerStats.balls) }}‑{{ currentBowlerStats.runs }} • Econ {{ econ(currentBowlerStats.runs, currentBowlerStats.balls) }}
          </span>
        </div>
      </section>

      <!-- Scoring + Scorecards -->
      <section class="grid2">
        <div class="left">
          <CompactPad
            :game-id="gameId"
            :striker-id="selectedStriker"
            :non-striker-id="selectedNonStriker"
            :bowler-id="selectedBowler"
            :can-score="canScore"
            @scored="onScored"
            @error="onError"
          />

          <DeliveryTable :deliveries="dedupedDeliveries" :player-name-by-id="playerNameById" class="mt-3" />
        </div>

        <div class="right">
          <BattingCard :entries="battingEntries" class="mb-3" />
          <BowlingCard :entries="bowlingEntries" />
          <div class="card mt-3" style="padding:12px; border:1px solid rgba(0,0,0,.08); border-radius:12px;">
            <h4 style="margin:0 0 8px; font-size:14px;">Extras</h4>
            <div style="display:grid; grid-template-columns:1fr auto; gap:6px; font-size:13px;">
              <span>Wides</span><strong>{{ extrasBreakdown.wides }}</strong>
              <span>No-balls</span><strong>{{ extrasBreakdown.no_balls }}</strong>
              <span>Byes</span><strong>{{ extrasBreakdown.byes }}</strong>
              <span>Leg-byes</span><strong>{{ extrasBreakdown.leg_byes }}</strong>
              <span>Penalty</span><strong>{{ extrasBreakdown.penalty }}</strong>
              <span style="border-top:1px solid rgba(0,0,0,.08); margin-top:4px; padding-top:4px;">Total</span>
              <strong style="border-top:1px solid rgba(0,0,0,.08); margin-top:4px; padding-top:4px;">{{ extrasBreakdown.total }}</strong>
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


    <!-- Mid-over Change Modal -->
    <dialog ref="changeBowlerDlg">
      <form method="dialog" class="dlg">
        <h3>Mid‑over change (injury)</h3>
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

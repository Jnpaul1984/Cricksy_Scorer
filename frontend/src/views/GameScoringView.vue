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
/* NEW: live preview of the same scoreboard the audience sees */
import ScoreboardWidget from '@/components/ScoreboardWidget.vue'

// ---- Minimal domain types used locally (keep it small) ----
type Player = { id: string; name: string }

type Team = {
  name: string
  players: Player[]
  playing_xi?: string[]
}

type BatCardEntry = {
  player_id: string
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
  player_id: string
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
  striker_id: string
  non_striker_id: string
  bowler_id: string
  extra?: 'wd' | 'nb' | 'b' | 'lb'
  is_wicket?: boolean
  commentary?: string
  dismissed_player_id?: string | null
  at_utc?: string
}

/* ========== ROUTE + STORE ========== */
const route = useRoute()
const router = useRouter()
const gameStore = useGameStore()

/* Current gameId (param or ?id=) */
const gameId = computed(() => (route.params.gameId as string) || (route.query.id as string) || '')

/* ========== XI LOCAL STORAGE ========== */
type XI = { team_a_xi: string[]; team_b_xi: string[] }
const XI_KEY = (id: string) => `cricksy.xi.${id}`
const xiA = ref<Set<string> | null>(null)
const xiB = ref<Set<string> | null>(null)
const xiLoaded = ref(false)

function loadXIForGame(id: string) {
  xiA.value = xiB.value = null
  xiLoaded.value = false
  try {
    const raw = localStorage.getItem(XI_KEY(id))
    if (raw) {
      const parsed = JSON.parse(raw) as XI
      if (Array.isArray(parsed.team_a_xi)) xiA.value = new Set(parsed.team_a_xi)
      if (Array.isArray(parsed.team_b_xi)) xiB.value = new Set(parsed.team_b_xi)
    }
  } catch {}
  xiLoaded.value = true
}

/* ========== SELECTION STATE ========== */
const selectedStriker = ref<string>('')
const selectedNonStriker = ref<string>('')
const selectedBowler = ref<string>('')

// Keep the store's selection in sync with the view
watch([selectedStriker, selectedNonStriker, selectedBowler], ([s, n, b]) => {
  if (typeof (gameStore as any).setSelectedStriker === 'function') {
    gameStore.setSelectedStriker(s || null)
    gameStore.setSelectedNonStriker(n || null)
    gameStore.setSelectedBowler(b || null)
  }
})

/* ========== CONNECTION / OFFLINE QUEUE ========== */
const liveReady = computed(() => gameStore.connectionStatus === 'connected')
const pendingForThisGame = computed(() => gameStore.offlineQueue.filter(q => q.gameId === gameId.value && q.status !== 'flushing'))
const pendingCount = computed(() => pendingForThisGame.value.length)

/* ========== ROSTERS (FILTERED BY XI) ========== */
const battingPlayers = computed<Player[]>(() => {
  const g = gameStore.currentGame
  if (!g) return []
  const battingIsA = g.batting_team_name === g.team_a?.name
  const team = (battingIsA ? g.team_a : g.team_b) as unknown as Team | undefined
  const all = team?.players ?? []
  if (!xiLoaded.value) return all
  const xiSet = (battingIsA ? xiA.value : xiB.value) ?? (team?.playing_xi && team.playing_xi.length ? new Set(team.playing_xi) : null)
  return xiSet ? all.filter((p) => xiSet.has(p.id)) : all
})

const bowlingPlayers = computed<Player[]>(() => {
  const g = gameStore.currentGame
  if (!g) return []
  const bowlingIsA = g.bowling_team_name === g.team_a?.name
  const team = (bowlingIsA ? g.team_a : g.team_b) as unknown as Team | undefined
  const all = team?.players ?? []
  if (!xiLoaded.value) return all
  const xiSet = (bowlingIsA ? xiA.value : xiB.value) ?? (team?.playing_xi && team.playing_xi.length ? new Set(team.playing_xi) : null)
  return xiSet ? all.filter((p) => xiSet.has(p.id)) : all
})

/* Can score? prevent same batter in both roles */
const canScore = computed(() => !!selectedStriker.value && !!selectedNonStriker.value && selectedStriker.value !== selectedNonStriker.value && !!selectedBowler.value)

/* Names for status text */
const selectedStrikerName = computed(() => battingPlayers.value.find((p: Player) => p.id === selectedStriker.value)?.name || '')
const selectedBowlerName = computed(() => bowlingPlayers.value.find((p: Player) => p.id === selectedBowler.value)?.name || '')

/* ========== SCORECARDS (one source of truth from the store) ========== */
/* NEW: map exactly to the shapes emitted by gameStore.battingRows/bowlingRows */
const battingEntries = computed<BatCardEntry[]>(() =>
  gameStore.battingRows.map((r: any) => ({
    player_id: r.id,
    player_name: r.name,
    runs: r.runs,
    balls_faced: r.balls,
    fours: r.fours,
    sixes: r.sixes,
    strike_rate: r.sr,
    how_out: r.howOut,
    is_out: r.isOut,
  }))
)

const bowlingEntries = computed<BowlCardEntry[]>(() =>
  gameStore.bowlingRows.map((r: any) => ({
    player_id: r.id,
    player_name: r.name,
    overs_bowled: r.overs,
    maidens: r.maidens,
    runs_conceded: r.runs,
    wickets_taken: r.wkts,
    economy: r.econ,
  }))
)

/* Deliveries table */
const deliveries = computed<DeliveryRowForTable[]>(() => {
  const list = gameStore.currentGame?.deliveries ?? []
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
  return list.map((d: any) => {
    const { over, ball } = parseOverBall(d.over_number ?? d.over, d.ball_number ?? d.ball)
    return {
      over_number: over,
      ball_number: ball,
      runs_scored: Number(d.runs_scored ?? d.runs) || 0,
      striker_id: String(d.striker_id ?? ''),
      non_striker_id: String(d.non_striker_id ?? ''),
      bowler_id: String(d.bowler_id ?? ''),
      extra: d.extra,
      is_wicket: !!d.is_wicket,
      commentary: d.commentary,
      dismissed_player_id: d.dismissed_player_id ?? null,
      at_utc: d.at_utc,
    }
  })
})

/* Name lookup for DeliveryTable */
function playerNameById(id?: string | null): string {
  if (!id) return ''
  const g = gameStore.currentGame
  if (!g) return ''
  return (
    g.team_a.players.find(p => p.id === id)?.name ??
    g.team_b.players.find(p => p.id === id)?.name ??
    ''
  )
}

/* Tiny toast */
type ToastType = 'success' | 'error' | 'info'
const toast = ref<{ message: string; type: ToastType } | null>(null)
let toastTimer: number | null = null
function showToast(message: string, type: ToastType = 'success', ms = 1800) {
  toast.value = { message, type }
  if (toastTimer) window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => (toast.value = null), ms) as unknown as number
}
function onScored() { showToast(pendingCount.value > 0 ? 'Saved (queued) ✓' : 'Saved ✓', 'success') }
function onError(message: string) { showToast(message || 'Something went wrong', 'error', 3000) }

/* Swap */
function swapBatsmen() {
  const t = selectedStriker.value
  selectedStriker.value = selectedNonStriker.value
  selectedNonStriker.value = t
}

/* ========== EMBED / SHARE PANEL (MERGED) ========== */
const theme = ref<'auto' | 'dark' | 'light'>('dark')
const title = ref<string>('Live Scoreboard')
const logo = ref<string>('')
const height = ref<number>(180)

const apiBase = (import.meta as any).env?.VITE_API_BASE || window.location.origin
const sponsorsUrl = computed(() => (gameId.value ? `${apiBase}/games/${encodeURIComponent(gameId.value)}/sponsors` : ''))

/* NEW: make the preview URL match the router mode (history by default) */
const embedUrl = computed(() => {
  const routerMode = (import.meta as any).env?.VITE_ROUTER_MODE ?? 'history' // set to 'hash' if you use createWebHashHistory
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

const iframeCode = computed(() => `<iframe src="${embedUrl.value}" width="100%" height="${height.value}" frameborder="0" scrolling="no" allowtransparency="true"></iframe>`)

/* Share modal state + clipboard copy */
const shareOpen = ref(false)
const copied = ref(false)
const codeRef = ref<HTMLTextAreaElement | null>(null)

function closeShare() { shareOpen.value = false; copied.value = false }

async function copyEmbed() {
  const txt = iframeCode.value
  try {
    await navigator.clipboard.writeText(txt)
    copied.value = true
  } catch {
    if (codeRef.value) {
      codeRef.value.focus()
      codeRef.value.select()
      try { document.execCommand('copy') } catch {}
      copied.value = true
    }
  }
  window.setTimeout(() => (copied.value = false), 1600)
}

watch(shareOpen, (o) => { if (o) setTimeout(() => codeRef.value?.select(), 75) })

/* ========== LIFECYCLE ========== */
onMounted(async () => {
  const id = gameId.value
  if (!id) return router.replace('/')
  try {
    await gameStore.loadGame(id)
    gameStore.initLive(id)
  } catch (e) {
    showToast('Failed to load or connect', 'error', 3000)
    console.error('load/init failed:', e)
  }
  loadXIForGame(id)
  if (typeof (gameStore as any).setSelectedStriker === 'function') {
    gameStore.setSelectedStriker(selectedStriker.value || null)
    gameStore.setSelectedNonStriker(selectedNonStriker.value || null)
    gameStore.setSelectedBowler(selectedBowler.value || null)
  }
})

onUnmounted(() => {
  if (toastTimer) window.clearTimeout(toastTimer)
  gameStore.stopLive()
})

/* Keep selections valid when innings flips or XI loads */
watch([battingPlayers, bowlingPlayers, xiLoaded], () => {
  if (selectedStriker.value && !battingPlayers.value.find((p: Player) => p.id === selectedStriker.value)) selectedStriker.value = ''
  if (selectedNonStriker.value && !battingPlayers.value.find((p: Player) => p.id === selectedNonStriker.value)) selectedNonStriker.value = ''
  if (selectedBowler.value && !bowlingPlayers.value.find((p: Player) => p.id === selectedBowler.value)) selectedBowler.value = ''
})

watch(() => [gameStore.currentGame?.batting_team_name, gameStore.currentGame?.bowling_team_name], () => {
  if (selectedStriker.value && !battingPlayers.value.find(p => p.id === selectedStriker.value)) selectedStriker.value = ''
  if (selectedNonStriker.value && !battingPlayers.value.find(p => p.id === selectedNonStriker.value)) selectedNonStriker.value = ''
  if (selectedBowler.value && !bowlingPlayers.value.find(p => p.id === selectedBowler.value)) selectedBowler.value = ''
})

/* Reconnect + flush controls */
function reconnect() {
  const id = gameId.value
  if (!id) return
  try {
    gameStore.initLive(id)
    showToast('Reconnecting…', 'info')
  } catch {
    showToast('Reconnect failed', 'error', 2500)
  }
}
function flushNow() {
  const id = gameId.value
  if (!id) return
  gameStore.flushQueue(id)
  showToast('Flushing queue…', 'info')
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
      <!-- NEW: live scoreboard preview (socket-driven) -->
      <ScoreboardWidget
        class="mb-3"
        :game-id="gameId"
        :theme="theme"
        :title="title"
        :logo="logo"
        :api-base="apiBase"
      />

      <PresenceBar class="mb-3" :game-id="gameId" :status="gameStore.connectionStatus" :pending="pendingCount" />

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
      striker: {{ selectedStriker }}
      nonStriker: {{ selectedNonStriker }}
      bowler: {{ selectedBowler }}
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
            <small id="sel-striker-hint" class="hint">Pick a batter on strike</small>
          </div>

          <div class="col">
            <label class="lbl" for="sel-nonstriker">Non-striker</label>
            <select id="sel-nonstriker" name="nonStriker" class="sel" v-model="selectedNonStriker" :disabled="battingPlayers.length === 0" title="Choose non-striker" aria-describedby="sel-nonstriker-hint">
              <option disabled value="">Choose non-striker</option>
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
            <small id="sel-bowler-hint" class="hint">Pick current bowler</small>
          </div>

          <div class="col align-end">
            <button class="btn" :disabled="!canScore" @click="swapBatsmen" aria-label="Swap striker and non-striker">Swap Batters</button>
            <div class="debug" style="margin-top:8px;font-size:12px;color:#6b7280">
              canScore: <b>{{ String(canScore) }}</b>
              &nbsp;|&nbsp; S: {{ selectedStriker || '∅' }}
              &nbsp;|&nbsp; NS: {{ selectedNonStriker || '∅' }}
              &nbsp;|&nbsp; B: {{ selectedBowler || '∅' }}
              &nbsp;|&nbsp; battingPlayers: {{ battingPlayers.length }}
              &nbsp;|&nbsp; bowlingPlayers: {{ bowlingPlayers.length }}
            </div>
          </div>
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

          <DeliveryTable :deliveries="deliveries" :player-name-by-id="playerNameById" class="mt-3" />
        </div>

        <div class="right">
          <BattingCard :entries="battingEntries" class="mb-3" />
          <BowlingCard :entries="bowlingEntries" />
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
              <input class="inp wide" :value="embedUrl" readonly @focus="(e) => (e.target as HTMLTextAreaElement | null)?.select()" />
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
.mb-3 { margin-bottom: 12px; } /* small helper */
.placeholder { padding: 16px; border: 1px dashed rgba(0,0,0,.2); border-radius: 12px; color: #6b7280; background: rgba(0,0,0,.02); }
.dev-debug { background: #111827; color: #e5e7eb; padding: 8px; border-radius: 8px; font-size: 12px; white-space: pre-wrap; margin: 8px 0; }

/* Controls */
.inp, .sel { height: 34px; border-radius: 10px; border: 1px solid #e5e7eb; padding: 0 10px; font-size: 14px; background: #fff; color: #111827; }
.inp.wide { width: 100%; }
.btn { appearance: none; border-radius: 10px; padding: 8px 12px; font-weight: 700; font-size: 14px; cursor: pointer; }
.btn-primary { border: 0; background: #22d3ee; color: #0b0f1a; }
.btn-ghost { border: 1px solid #e5e7eb; background: #fff; color: #111827; text-decoration: none; }

/* Modal */
.backdrop { position: fixed; inset: 0; background: rgba(0,0,0,.45); display: grid; place-items: center; padding: 16px; z-index: 60; }
.modal { width: min(760px, 96vw); background: #0b0f1a; color: #e5e7eb; border-radius: 16px; box-shadow: 0 20px 50px rgba(0,0,0,.5); overflow: hidden; }
.modal-hdr, .modal-ftr { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.modal-hdr { padding: 14px 16px; border-bottom: 1px solid rgba(255,255,255,.06); }
.modal-ftr { padding: 12px 16px; border-top: 1px solid rgba(255,255,255,.06); }
.modal-hdr h3 { margin: 0; font-size: 16px; letter-spacing: .01em; }
.x { background: transparent; border: 0; color: #9ca3af; font-size: 18px; cursor: pointer; }
.modal-body { padding: 14px 16px; display: grid; gap: 12px; }
.row { display: grid; gap: 6px; }
.grid.two { grid-template-columns: 1fr auto; align-items: end; gap: 12px; }
.align-end { display: grid; align-items: end; }
.lbl { font-size: 12px; color: #9ca3af; }

.code-wrap { position: relative; }
.code { width: 100%; min-height: 120px; resize: vertical; background: #0f172a; color: #e5e7eb; border: 1px solid rgba(255,255,255,.08); border-radius: 12px; padding: 12px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; line-height: 1.4; }
.copy { position: absolute; top: 8px; right: 8px; border: 1px solid rgba(255,255,255,.12); background: rgba(255,255,255,.06); color: #e5e7eb; border-radius: 10px; padding: 6px 10px; font-size: 12px; cursor: pointer; }

.note { font-size: 12px; color: #9ca3af; }
.note code { background: rgba(255,255,255,.06); padding: 1px 6px; border-radius: 6px; }

.spacer { flex: 1; }

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
  .note { color: #6b7280; }
}
</style>

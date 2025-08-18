<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  connectSocket,
  disconnectSocket,
  emit as emitSocket,
  on as onSocket,
  off as offSocket,
} from '@/utils/socket'
import { fmtSR, fmtEconomy, oversDisplayFromBalls } from '@/utils/cricket'

// Allow listening to custom events safely
const onAny = onSocket as unknown as (ev: string, cb: (...a:any[])=>void)=>void
const offAny = offSocket as unknown as (ev: string, cb?: (...a:any[])=>void)=>void

const props = withDefaults(defineProps<{
  gameId: string
  apiBase?: string
  theme?: 'dark' | 'light' | 'auto'
  title?: string
}>(), {
  apiBase: '',
  theme: 'dark',
  title: 'Live Scoreboard',
})

const base = computed(() =>
  props.apiBase?.replace(/\/$/, '') || window.location.origin.replace(/\/$/, '')
)

const snap = ref<any>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function loadSnapshot() {
  loading.value = true
  try {
    const r = await fetch(`${base.value}/games/${encodeURIComponent(props.gameId)}/snapshot`)
    if (!r.ok) throw new Error(await r.text())
    snap.value = await r.json()
  } catch (e: any) {
    error.value = e?.message || 'Failed to load'
  } finally {
    loading.value = false
  }
}

// Keep references so we can remove exactly the same handlers (Pylance-safe)
let handleStateUpdate: ((payload: any) => void) | null = null
let handleScoreUpdate: ((payload: any) => void) | null = null

onMounted(async () => {
  await loadSnapshot()

  try {
    connectSocket()
    emitSocket('join', { game_id: props.gameId, role: 'VIEWER', name: 'Scoreboard' } as any)

    handleStateUpdate = (payload: any) => {
      if (payload?.id !== props.gameId) return
      const keep = snap.value ?? {}
      snap.value = { ...keep, ...(payload.snapshot ?? {}) }
    }

    handleScoreUpdate = (payload: any) => {
      if (payload?.game_id && payload.game_id !== props.gameId) return
      void loadSnapshot()
    }

    onAny('state:update', handleStateUpdate)
    onAny('score:update', handleScoreUpdate)
  } catch {/* non-fatal */}
})

onUnmounted(() => {
  if (handleStateUpdate) offAny('state:update', handleStateUpdate)
  if (handleScoreUpdate) offAny('score:update', handleScoreUpdate)
  disconnectSocket()
})

// ---------------------- helpers ----------------------
function oversString(): string {
  const s = snap.value
  if (!s) return '0.0'

  // 1) Prefer top-level `overs` (your API sends "0.1" here)
  const top = s?.overs
  if (typeof top === 'string') return top
  if (typeof top === 'number') {
    const whole = Math.trunc(top)
    const balls = Math.max(0, Math.min(5, Math.round((top - whole) * 10)))
    return `${whole}.${balls}`
  }

  // 2) Fallback to score.overs (some older payloads)
  const sc = s?.score?.overs
  if (typeof sc === 'string') return sc
  if (typeof sc === 'number') {
    const whole = Math.trunc(sc)
    const balls = Math.max(0, Math.min(5, Math.round((sc - whole) * 10)))
    return `${whole}.${balls}`
  }

  // 3) Last resort: separate fields
  const oc = s?.over?.completed ?? s?.overs_completed ?? 0
  const b  = s?.over?.balls_this_over ?? s?.balls_this_over ?? 0
  return `${oc}.${b}`
}


function findById(list: any[] | undefined, id?: string | null) {
  if (!id || !Array.isArray(list)) return null
  return list.find(p => String(p.id) === String(id)) ?? null
}
function batCard(id?: string | null) {
  if (!id) return null
  return snap.value?.batting_scorecard?.[id] ?? null
}
function bowlCard(id?: string | null) {
  if (!id) return null
  return snap.value?.bowling_scorecard?.[id] ?? null
}

// Convert overs notation (e.g., 3.4) to balls
function oversToBalls(value: number | string | undefined): number {
  if (value == null) return 0
  if (typeof value === 'number') {
    const whole = Math.trunc(value)
    const tenth = Math.round((value - whole) * 10)
    return whole * 6 + Math.max(0, Math.min(5, tenth))
  }
  const [o, b] = String(value).split('.')
  const oi = Number(o) || 0
  const bi = Math.max(0, Math.min(5, Number(b) || 0))
  return oi * 6 + bi
}

// Batter blocks (now with Strike Rate instead of Dot%)
const striker = computed(() => {
  const s = snap.value
  if (!s) return { id: null, name: '', runs: 0, balls: 0, sr: '—' }
  const id = s?.batsmen?.striker?.id ?? s?.current_striker_id ?? null
  const name = s?.batsmen?.striker?.name || batCard(id)?.player_name || findById(s?.players?.batting, id)?.name || ''
  const runs  = s?.batsmen?.striker?.runs  ?? batCard(id)?.runs        ?? 0
  const balls = s?.batsmen?.striker?.balls ?? batCard(id)?.balls_faced ?? 0
  return { id, name, runs, balls, sr: fmtSR(runs, balls) }
})

const nonStriker = computed(() => {
  const s = snap.value
  if (!s) return { id: null, name: '', runs: 0, balls: 0, sr: '—' }
  const id = s?.batsmen?.non_striker?.id ?? s?.current_non_striker_id ?? null
  const name = s?.batsmen?.non_striker?.name || batCard(id)?.player_name || findById(s?.players?.batting, id)?.name || ''
  const runs  = s?.batsmen?.non_striker?.runs  ?? batCard(id)?.runs        ?? 0
  const balls = s?.batsmen?.non_striker?.balls ?? batCard(id)?.balls_faced ?? 0
  return { id, name, runs, balls, sr: fmtSR(runs, balls) }
})

// Bowler block (prefer last_delivery bowler, fallback to current_bowler_id if provided)
const bowler = computed(() => {
  const s = snap.value
  if (!s) return { id: null, name: '', wkts: 0, runs: 0, balls: 0, oversTxt: '0.0', econ: '—' }
  const id = s?.last_delivery?.bowler_id ?? s?.current_bowler_id ?? null
  const card = bowlCard(id)
  const name = card?.player_name || findById(s?.players?.bowling, id)?.name || ''
  const runs = card?.runs_conceded ?? 0
  // Try to compute legal balls from card; if only overs_bowled is present, interpret cricket notation (e.g. 3.4 = 22 balls)
  const balls = (card && 'balls_bowled' in card) ? Number((card as any).balls_bowled) || 0 : oversToBalls(card?.overs_bowled as any)
  const oversTxt = oversDisplayFromBalls(balls)
  const econ = fmtEconomy(runs, balls)
  const wkts = card?.wickets_taken ?? 0
  return { id, name, wkts, runs, balls, oversTxt, econ }
})

const scoreline = computed(() => {
  const s = snap.value
  return `${s?.score?.runs ?? 0}/${s?.score?.wickets ?? 0}`
})
const teamA = computed(() => snap.value?.batting_team_name || '')
const teamB = computed(() => snap.value?.bowling_team_name || '')
</script>

<template>
  <section class="board" :data-theme="theme">
    <header class="hdr">
      <h3>{{ title || 'Live Scoreboard' }}</h3>
      <span class="pill live">● LIVE</span>
    </header>

    <div v-if="error" class="error">{{ error }}</div>
    <div v-else-if="!snap" class="loading">Loading…</div>
    <div v-else class="card">
      <div class="topline">
        <div class="teams">
          <strong>{{ teamA }}</strong>
          <span>vs</span>
          <strong>{{ teamB }}</strong>
        </div>
        <div class="score">
          <span class="big">{{ scoreline }}</span>
          <span class="ov">({{ oversString() }} ov)</span>
        </div>
      </div>

      <div class="grid grid-3">
        <!-- Striker -->
        <div class="pane">
          <div class="pane-title">Striker</div>
          <div class="row">
            <div class="label">Name</div>
            <div class="val">{{ striker.name || '—' }}</div>
          </div>
          <div class="row">
            <div class="label">Runs (Balls)</div>
            <div class="val">{{ striker.runs }} ({{ striker.balls }})</div>
          </div>
          <div class="row">
            <div class="label">Strike Rate</div>
            <div class="val">{{ striker.sr }}</div>
          </div>
        </div>

        <!-- Non-striker -->
        <div class="pane">
          <div class="pane-title">Non-striker</div>
          <div class="row">
            <div class="label">Name</div>
            <div class="val">{{ nonStriker.name || '—' }}</div>
          </div>
          <div class="row">
            <div class="label">Runs (Balls)</div>
            <div class="val">{{ nonStriker.runs }} ({{ nonStriker.balls }})</div>
          </div>
          <div class="row">
            <div class="label">Strike Rate</div>
            <div class="val">{{ nonStriker.sr }}</div>
          </div>
        </div>

        <!-- Bowler -->
        <div class="pane">
          <div class="pane-title">Bowler</div>
          <div class="row">
            <div class="label">Name</div>
            <div class="val">{{ bowler.name || '—' }}</div>
          </div>
          <div class="row">
            <div class="label">Figures</div>
            <div class="val">{{ bowler.wkts }}-{{ bowler.runs }} ({{ bowler.oversTxt }})</div>
          </div>
          <div class="row">
            <div class="label">Economy</div>
            <div class="val">{{ bowler.econ }}</div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.board { width: min(980px, 96vw); margin: 0 auto; }
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
:where([data-theme="light"]) .ov,.teams,.label { color:#6b7280; }
</style>

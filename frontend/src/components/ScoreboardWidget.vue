<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

// If you already have socket helpers, use them.
// These casts let us listen to custom events like 'state:update' safely.
import {
  connectSocket,
  disconnectSocket,
  emit as emitSocket,
  on as onSocket,
  off as offSocket,
} from '@/utils/socket'

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

onMounted(async () => {
  await loadSnapshot()

  // Live updates
  try {
    connectSocket()
    emitSocket('join', { game_id: props.gameId, role: 'VIEWER', name: 'Scoreboard' } as any)

    onAny('state:update', (payload: any) => {
      if (payload?.id !== props.gameId) return
      // Merge the new snapshot but keep any bootstrap fields we may rely on (players lists)
      const keep = snap.value ?? {}
      snap.value = { ...keep, ...(payload.snapshot ?? {}) }
    })

    // Some servers emit a slim score payload — refresh to get names/scorecards
    onAny('score:update', (payload: any) => {
      if (payload?.game_id && payload.game_id !== props.gameId) return
      void loadSnapshot()
    })
  } catch {/* non-fatal */}
})

onUnmounted(() => {
  offAny('state:update')
  offAny('score:update')
  disconnectSocket()
})

// ---------------------- helpers ----------------------
function oversString(): string {
  const s = snap.value
  if (!s) return '0.0'
  const o = s?.score?.overs
  if (typeof o === 'string') return o
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

// Batter blocks
const striker = computed(() => {
  const s = snap.value
  if (!s) return { id: null, name: '', runs: 0, balls: 0 }
  const id = s?.batsmen?.striker?.id ?? s?.current_striker_id ?? null
  const name =
    s?.batsmen?.striker?.name ||
    batCard(id)?.player_name ||
    findById(s?.players?.batting, id)?.name ||
    ''
  const runs  = s?.batsmen?.striker?.runs  ?? batCard(id)?.runs        ?? 0
  const balls = s?.batsmen?.striker?.balls ?? batCard(id)?.balls_faced ?? 0
  return { id, name, runs, balls }
})
const nonStriker = computed(() => {
  const s = snap.value
  if (!s) return { id: null, name: '', runs: 0, balls: 0 }
  const id = s?.batsmen?.non_striker?.id ?? s?.current_non_striker_id ?? null
  const name =
    s?.batsmen?.non_striker?.name ||
    batCard(id)?.player_name ||
    findById(s?.players?.batting, id)?.name ||
    ''
  const runs  = s?.batsmen?.non_striker?.runs  ?? batCard(id)?.runs        ?? 0
  const balls = s?.batsmen?.non_striker?.balls ?? batCard(id)?.balls_faced ?? 0
  return { id, name, runs, balls }
})

// Bowler block (use last_delivery to decide the “current” bowler)
const bowler = computed(() => {
  const s = snap.value
  if (!s) return { id: null, name: '', wkts: 0, runs: 0, overs: '0.0' }
  const id = s?.last_delivery?.bowler_id ?? null
  const card = bowlCard(id)
  const name =
    card?.player_name ||
    findById(s?.players?.bowling, id)?.name ||
    ''
  // overs_bowled can be fractional (0.7 ~ 4 balls) — still fine for now
  const overs =
    typeof card?.overs_bowled === 'number'
      ? card.overs_bowled.toFixed(1)
      : '0.0'
  return {
    id,
    name,
    wkts: card?.wickets_taken ?? 0,
    runs: card?.runs_conceded ?? 0,
    overs,
  }
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

      <div class="grid">
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
            <div class="label">Dot %</div>
            <div class="val">—</div>
          </div>
        </div>

        <div class="pane">
          <div class="pane-title">Bowler</div>
          <div class="row">
            <div class="label">Name</div>
            <div class="val">{{ bowler.name || '—' }}</div>
          </div>
          <div class="row">
            <div class="label">Figures</div>
            <div class="val">{{ bowler.wkts }}-{{ bowler.runs }} ({{ bowler.overs }})</div>
          </div>
          <div class="row">
            <div class="label">Dot %</div>
            <div class="val">—</div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.board { width: min(920px, 96vw); margin: 0 auto; }
.hdr { display: flex; align-items: center; gap: 10px; margin: 10px 0; }
.pill.live { font-size: 12px; padding: 2px 8px; border-radius: 999px; background: #10b98122; color: #10b981; border: 1px solid #10b98155; }
.card { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,.08); border-radius: 14px; padding: 16px; }
.topline { display:flex; justify-content:space-between; align-items: baseline; gap:16px; margin-bottom: 10px; }
.teams { display:flex; gap:8px; align-items:center; color:#9ca3af; }
.score { display:flex; gap:8px; align-items:baseline; }
.big { font-weight: 900; font-size: 28px; letter-spacing: .5px; }
.ov { color:#9ca3af; font-weight:600; }
.grid { display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-top: 8px; }
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

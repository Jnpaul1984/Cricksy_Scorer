<script setup lang="ts">
import { ref, computed } from 'vue'
import apiService from '@/utils/api'

type UUID = string
type Delivery = {
  inning?: number
  over_number?: number
  ball_number?: number
  runs_scored?: number
  runs_off_bat?: number
  is_extra?: boolean
  extra_type?: 'wd'|'nb'|'b'|'lb'|string|null
  is_wicket?: boolean
  dismissed_player_id?: string|null
}

const qTeamA = ref('')
const qTeamB = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const results = ref<Array<{ id: UUID; team_a_name: string; team_b_name: string; status?: string }>>([])
const selectedId = ref<UUID>('' as UUID)

// Data for selected game
const snapshot = ref<any | null>(null)
const deliveries = ref<Delivery[]>([])

async function search() {
  loading.value = true
  error.value = null
  try {
    results.value = await apiService.searchGames(qTeamA.value.trim() || undefined, qTeamB.value.trim() || undefined)
  } catch (e: any) {
    error.value = e?.message || 'Search failed'
  } finally {
    loading.value = false
  }
}

async function loadGame(id: string) {
  selectedId.value = id as UUID
  loading.value = true
  error.value = null
  try {
    snapshot.value = await apiService.getGame(id)
    const res = await apiService.deliveries(id, { order: 'asc' })
    deliveries.value = (res?.deliveries || []) as Delivery[]
  } catch (e: any) {
    error.value = e?.message || 'Load failed'
  } finally {
    loading.value = false
  }
}

// ---------------- Analytics helpers ----------------
const innings = computed(() => {
  const out: Record<number, Delivery[]> = { 1: [], 2: [] }
  for (const d of deliveries.value) {
    const inn = Number(d?.inning ?? (d as any)?.over?.inning ?? 1)
    if (!out[inn]) out[inn] = []
    out[inn].push(d)
  }
  return out
})

function runsPerOver(dl: Delivery[]): number[] {
  const m: Record<number, number> = {}
  for (const d of dl) {
    const ov = Number(d?.over_number ?? 0)
    const rs = Number((d as any)?.runs_scored ?? (d as any)?.runs ?? 0)
    m[ov] = (m[ov] || 0) + rs
  }
  const keys = Object.keys(m).map(n => Number(n)).sort((a,b)=>a-b)
  return keys.map(k => m[k])
}

const manhattan = computed(() => {
  const i = innings.value
  return {
    1: runsPerOver(i[1] || []),
    2: runsPerOver(i[2] || []),
  }
})

const worm = computed(() => {
  const mk = (arr: number[]) => {
    const out: number[] = []
    let t = 0
    for (const v of arr) { t += v; out.push(t) }
    return out
  }
  return { 1: mk(manhattan.value[1]), 2: mk(manhattan.value[2]) }
})

function legalBall(d: Delivery): boolean {
  const x = (d.extra_type || '').toString().toLowerCase()
  return !(x === 'wd' || x === 'nb')
}

const dotBoundary = computed(() => {
  let legal = 0, dots = 0, boundaries = 0
  for (const d of deliveries.value) {
    if (!legalBall(d)) continue
    legal++
    const rs = Number(d.runs_scored ?? 0)
    if (rs === 0) dots++
    if (rs === 4 || rs === 6) boundaries++
  }
  const dotPct = legal ? (dots / legal) * 100 : 0
  const boundaryPct = legal ? (boundaries / legal) * 100 : 0
  return { legal, dots, boundaries, dotPct, boundaryPct }
})

const currRuns = computed(() => Number(snapshot.value?.total_runs ?? 0))
const ballsBowled = computed(() => Number(snapshot.value?.overs_completed ?? 0) * 6 + Number(snapshot.value?.balls_this_over ?? 0))
const crr = computed(() => {
  const ov = ballsBowled.value / 6
  return ov > 0 ? (currRuns.value / ov) : 0
})

const req = computed(() => {
  const target = snapshot.value?.target
  if (target == null) return { rrr: null, remainingOvers: null, remainingRuns: null }
  const remRuns = Math.max(0, Number(target) - currRuns.value)
  const remBalls = Math.max(0, Number(snapshot.value?.overs_limit || 0) * 6 - ballsBowled.value)
  const remOvers = remBalls / 6
  const rrr = remOvers > 0 ? (remRuns / remOvers) : null
  return { rrr, remainingOvers: remOvers, remainingRuns: remRuns }
})

const extrasTotals = computed(() => snapshot.value?.extras_totals || {})
const fow = computed(() => (snapshot.value?.fall_of_wickets || []) as Array<{ score_at_fall?: number; over?: number; batter_id?: string }>)
const dlsPanel = computed(() => snapshot.value?.dls || {})

// Batting & Bowling tables
const battingRows = computed(() => {
  const card = snapshot.value?.batting_scorecard || {}
  return Object.values(card).map((e: any) => {
    const balls = Number(e?.balls_faced ?? 0)
    const runs = Number(e?.runs ?? 0)
    const sr = balls > 0 ? (runs * 100) / balls : 0
    return {
      name: e?.player_name || '',
      runs, balls, sr,
      fours: Number(e?.fours ?? 0),
      sixes: Number(e?.sixes ?? 0),
      how_out: (e?.how_out || '').toString(),
    }
  })
})

const bowlingRows = computed(() => {
  const card = snapshot.value?.bowling_scorecard || {}
  return Object.values(card).map((e: any) => {
    const ov = Number(e?.overs_bowled ?? 0)
    const econ = ov > 0 ? Number(e?.runs_conceded ?? 0) / ov : 0
    return {
      name: e?.player_name || '',
      overs: ov,
      maidens: Number(e?.maidens ?? 0),
      runs: Number(e?.runs_conceded ?? 0),
      wickets: Number(e?.wickets_taken ?? 0),
      econ,
      // if backend phases exist, surface as-is
      phases: (snapshot.value?.phases || {})[e?.player_id || ''] || null,
    }
  })
})

</script>

<template>
  <main class="container">
    <h1>Match Analytics</h1>
    <section class="card">
      <h2>Search</h2>
      <div class="row">
        <input v-model="qTeamA" placeholder="Team A name" class="inp" />
        <input v-model="qTeamB" placeholder="Team B name" class="inp" />
        <button class="btn" :disabled="loading" @click="search">Search</button>
      </div>
      <div v-if="error" class="error">{{ error }}</div>
      <ul class="list">
        <li v-for="g in results" :key="g.id">
          <button class="link" @click="loadGame(g.id)">{{ g.team_a_name }} vs {{ g.team_b_name }} <small>({{ g.status }})</small></button>
        </li>
      </ul>
    </section>

    <section v-if="selectedId && snapshot" class="grid">
      <div class="card">
        <h3>Run Rate</h3>
        <div>Current: {{ crr.toFixed(2) }} rpo</div>
        <div v-if="req.rrr != null">Required: {{ (req.rrr as number).toFixed(2) }} rpo ({{ req.remainingRuns }} runs in {{ req.remainingOvers?.toFixed(1) }} overs)</div>
      </div>

      <div class="card">
        <h3>Manhattan (runs per over)</h3>
        <div>Inns 1: {{ manhattan[1].join(', ') || '—' }}</div>
        <div>Inns 2: {{ manhattan[2].join(', ') || '—' }}</div>
      </div>

      <div class="card">
        <h3>Worm (cumulative)</h3>
        <div>Inns 1: {{ worm[1].join(', ') || '—' }}</div>
        <div>Inns 2: {{ worm[2].join(', ') || '—' }}</div>
      </div>

      <div class="card">
        <h3>Extras / Dot & Boundary %</h3>
        <pre>{{ extrasTotals }}</pre>
        <div>Legal balls: {{ dotBoundary.legal }}, Dots: {{ dotBoundary.dots }} ({{ dotBoundary.dotPct.toFixed(1) }}%), Boundaries: {{ dotBoundary.boundaries }} ({{ dotBoundary.boundaryPct.toFixed(1) }}%)</div>
      </div>

      <div class="card wide">
        <h3>Batting</h3>
        <table class="tbl">
          <thead><tr><th>Batter</th><th>R</th><th>B</th><th>SR</th><th>4s</th><th>6s</th><th>Dismissal</th></tr></thead>
          <tbody>
            <tr v-for="r in battingRows" :key="r.name">
              <td>{{ r.name }}</td><td>{{ r.runs }}</td><td>{{ r.balls }}</td><td>{{ r.sr.toFixed(1) }}</td><td>{{ r.fours }}</td><td>{{ r.sixes }}</td><td>{{ r.how_out }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card wide">
        <h3>Bowling</h3>
        <table class="tbl">
          <thead><tr><th>Bowler</th><th>O</th><th>M</th><th>R</th><th>W</th><th>Econ</th></tr></thead>
          <tbody>
            <tr v-for="r in bowlingRows" :key="r.name">
              <td>{{ r.name }}</td><td>{{ r.overs }}</td><td>{{ r.maidens }}</td><td>{{ r.runs }}</td><td>{{ r.wickets }}</td><td>{{ r.econ.toFixed(2) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card">
        <h3>Fall of Wickets</h3>
        <ul>
          <li v-for="(w,i) in fow" :key="i">{{ w.score_at_fall }} at {{ w.over }}</li>
        </ul>
      </div>

      <div class="card">
        <h3>DLS</h3>
        <div v-if="dlsPanel.target != null">Target: {{ dlsPanel.target }}</div>
        <div v-if="dlsPanel.par != null">Par: {{ dlsPanel.par }}</div>
        <div v-if="dlsPanel.ahead_by != null">Ahead by: {{ dlsPanel.ahead_by }}</div>
        <div v-else>—</div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.container { max-width: 1100px; margin: 24px auto; padding: 0 12px; }
.row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.grid { display:grid; gap:16px; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
.card { border:1px solid #e5e7eb; border-radius:12px; padding:12px; background:#fff; }
.card.wide { grid-column: 1 / -1; }
.inp { padding:8px 10px; border:1px solid #d1d5db; border-radius:8px; }
.btn { padding:8px 12px; border-radius:8px; border:1px solid #d1d5db; background:#f9fafb; cursor:pointer; }
.btn:disabled { opacity:.6; cursor:not-allowed; }
.list { margin:8px 0; padding-left: 16px; }
.link { background:none; border:none; color:#2563eb; cursor:pointer; padding:0; }
.error { color:#b91c1c; }
.tbl { width:100%; border-collapse: collapse; }
.tbl th, .tbl td { border-bottom:1px solid #eee; padding:6px 8px; text-align:left; }
</style>

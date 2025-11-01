<script setup lang="ts">
import { ref, computed } from 'vue'

import ShotMapPreview from '@/components/ShotMapPreview.vue'
import ChartBar from '@/components/analytics/ChartBar.vue'
import ChartLine from '@/components/analytics/ChartLine.vue'
import PartnershipHeatmap from '@/components/analytics/PartnershipHeatmap.vue'
import PhaseSplits from '@/components/analytics/PhaseSplits.vue'
import WagonWheel from '@/components/analytics/WagonWheel.vue'
import RunRateComparison from '@/components/analytics/RunRateComparison.vue'

type UUID = string

type Delivery = {
  inning?: number
  over_number?: number
  ball_number?: number
  runs_scored?: number
  runs_off_bat?: number
  is_extra?: boolean
  extra_type?: 'wd' | 'nb' | 'b' | 'lb' | string | null
  is_wicket?: boolean
  dismissed_player_id?: string | null
  striker_id?: string | null
  non_striker_id?: string | null
  shot_angle_deg?: number | null
  shot_map?: string | null
}

const qTeamA = ref('')
const qTeamB = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const results = ref<Array<{ id: UUID; team_a_name: string; team_b_name: string; status?: string }>>([])
const selectedId = ref<UUID>('' as UUID)
const snapshot = ref<any | null>(null)
const deliveries = ref<Delivery[]>([])

/* Read ?apiBase=... so Cypress can point this view at the backend */
function apiBase(): string {
  try {
    const u = new URL(window.location.href)
    const v = u.searchParams.get('apiBase') || ''
    return v ? v.replace(/\/+$/, '') : ''
  } catch {
    return ''
  }
}

async function search() {
  loading.value = true
  error.value = null
  try {
    const base = apiBase()
    const qp = new URLSearchParams()
    if (qTeamA.value.trim()) qp.set('team_a', qTeamA.value.trim())
    if (qTeamB.value.trim()) qp.set('team_b', qTeamB.value.trim())
    const qs = qp.toString()
    const path = `/games/search${qs ? `?${qs}` : ''}`
    const url = base ? `${base}${path}` : path

    const res = await fetch(url, { cache: 'no-store' })
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
    const data = await res.json()
    results.value = Array.isArray(data) ? data : []
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
    const base = apiBase()

    // GET /games/{id}
    {
      const path = `/games/${encodeURIComponent(id)}`
      const url = base ? `${base}${path}` : path
      const res = await fetch(url, { cache: 'no-store' })
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
      snapshot.value = await res.json()
    }

    // GET /games/{id}/deliveries?order=asc
    {
      const path = `/games/${encodeURIComponent(id)}/deliveries?order=asc`
      const url = base ? `${base}${path}` : path
      const res = await fetch(url, { cache: 'no-store' })
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
      const j = await res.json()
      deliveries.value = (j?.deliveries || []) as Delivery[]
    }
  } catch (e: any) {
    error.value = e?.message || 'Load failed'
  } finally {
    loading.value = false
  }
}

const innings = computed(() => {
  const out: Record<number, Delivery[]> = { 1: [], 2: [] }
  for (const d of deliveries.value) {
    const inn = Number(d?.inning ?? 1)
    if (!out[inn]) out[inn] = []
    out[inn].push(d)
  }
  return out
})

function runsPerOver(dl: Delivery[]): number[] {
  const tally: Record<number, number> = {}
  for (const d of dl) {
    const ov = Number(d?.over_number ?? 0)
    const rs = Number(d.runs_scored ?? (d as any)?.runs ?? 0)
    tally[ov] = (tally[ov] || 0) + rs
  }
  const overs = Object.keys(tally).map(n => Number(n)).sort((a, b) => a - b)
  return overs.map(o => tally[o])
}

const manhattan = computed(() => ({
  1: runsPerOver(innings.value[1] || []),
  2: runsPerOver(innings.value[2] || []),
}))

const worm = computed(() => {
  const mk = (arr: number[]) => {
    const out: (number | null)[] = []
    let total = 0
    for (let i = 0; i < arr.length; i += 1) {
      total += arr[i]
      out.push(total)
    }
    return out
  }
  return {
    1: mk(manhattan.value[1]),
    2: mk(manhattan.value[2]),
  }
})

function padSeries(arr: number[], len: number): (number | null)[] {
  return Array.from({ length: len }, (_, i) => arr[i] ?? null)
}

const manhattanChart = computed(() => {
  const len = Math.max(manhattan.value[1].length, manhattan.value[2].length)
  if (!len) {
    return {
      labels: [] as string[],
      series: [] as Array<{ label: string; data: (number | null)[] }>,
    }
  }
  const labels = Array.from({ length: len }, (_, i) => `Over ${i + 1}`)
  return {
    labels,
    series: [
      { label: 'Innings 1', data: padSeries(manhattan.value[1], len) },
      { label: 'Innings 2', data: padSeries(manhattan.value[2], len) },
    ],
  }
})

const wormChart = computed(() => {
  const len = Math.max(worm.value[1].length, worm.value[2].length)
  if (!len) {
    return {
      labels: [] as string[],
      series: [] as Array<{ label: string; data: (number | null)[] }>,
    }
  }
  const labels = Array.from({ length: len }, (_, i) => `Over ${i + 1}`)
  return {
    labels,
    series: [
      { label: 'Innings 1', data: padSeries(worm.value[1] as number[], len) },
      { label: 'Innings 2', data: padSeries(worm.value[2] as number[], len) },
    ],
  }
})

function isLegalBall(d: Delivery): boolean {
  const x = (d.extra_type || '').toString().toLowerCase()
  return !(x === 'wd' || x === 'nb')
}

const dotBoundary = computed(() => {
  let legal = 0
  let dots = 0
  let boundaries = 0
  for (const d of deliveries.value) {
    if (!isLegalBall(d)) continue
    legal += 1
    const rs = Number(d.runs_scored ?? 0)
    if (rs === 0) dots += 1
    if (rs === 4 || rs === 6) boundaries += 1
  }
  return {
    legal,
    dots,
    boundaries,
    dotPct: legal ? (dots / legal) * 100 : 0,
    boundaryPct: legal ? (boundaries / legal) * 100 : 0,
  }
})

const currRuns = computed(() => Number(snapshot.value?.total_runs ?? 0))
const ballsBowled = computed(
  () =>
    Number(snapshot.value?.overs_completed ?? 0) * 6 +
    Number(snapshot.value?.balls_this_over ?? 0),
)
const crr = computed(() => {
  const overs = ballsBowled.value / 6
  return overs > 0 ? currRuns.value / overs : 0
})

const req = computed(() => {
  const target = snapshot.value?.target
  if (target == null) {
    return {
      rrr: null as number | null,
      remainingOvers: null as number | null,
      remainingRuns: null as number | null,
    }
  }
  const remainingRuns = Math.max(0, Number(target) - currRuns.value)
  const remainingBalls = Math.max(
    0,
    Number(snapshot.value?.overs_limit || 0) * 6 - ballsBowled.value,
  )
  const remainingOvers = remainingBalls / 6
  const rrr = remainingOvers > 0 ? remainingRuns / remainingOvers : null
  return { rrr, remainingOvers, remainingRuns }
})

const extrasTotals = computed<Record<string, number>>(
  () => snapshot.value?.extras_totals || {},
)
const fallOfWickets = computed(
  () =>
    (snapshot.value?.fall_of_wickets || []) as Array<{
      score_at_fall?: number
      over?: number
      batter_id?: string
    }>,
)
const dlsPanel = computed(() => snapshot.value?.dls || {})

const battingRows = computed(() => {
  const card = snapshot.value?.batting_scorecard || {}
  return Object.values(card).map((e: any) => {
    const balls = Number(e?.balls_faced ?? 0)
    const runs = Number(e?.runs ?? 0)
    const sr = balls > 0 ? (runs * 100) / balls : 0
    return {
      name: e?.player_name || '',
      runs,
      balls,
      sr,
      fours: Number(e?.fours ?? 0),
      sixes: Number(e?.sixes ?? 0),
      how_out: (e?.how_out || '').toString(),
    }
  })
})

const bowlingRows = computed(() => {
  const card = snapshot.value?.bowling_scorecard || {}
  return Object.values(card).map((e: any) => {
    const overs = Number(e?.overs_bowled ?? 0)
    const econ = overs > 0 ? Number(e?.runs_conceded ?? 0) / overs : 0
    return {
      name: e?.player_name || '',
      overs,
      maidens: Number(e?.maidens ?? 0),
      runs: Number(e?.runs_conceded ?? 0),
      wickets: Number(e?.wickets_taken ?? 0),
      econ,
    }
  })
})

type PairKey = string
const pairKey = (a?: string | null, b?: string | null): PairKey => {
  const A = String(a || '')
  const B = String(b || '')
  return A < B ? `${A}|${B}` : `${B}|${A}`
}

const partnerships = computed(() => {
  const map = new Map<PairKey, number>()
  const appeared = new Set<string>()
  for (const d of deliveries.value) {
    const s = String(d.striker_id || '')
    const n = String(d.non_striker_id || '')
    if (s) appeared.add(s)
    if (n) appeared.add(n)
    if (s && n && s !== n) {
      const key = pairKey(s, n)
      const add = Number(d.runs_scored ?? (d as any)?.runs ?? 0)
      map.set(key, (map.get(key) || 0) + add)
    }
  }
  const players: Array<{ id: string; name: string }> = []
  const nameMap = new Map<string, string>()
  const pushList = (list: any[] | undefined) => {
    for (const p of list ?? []) {
      const id = String(p?.id ?? '')
      if (!id) continue
      const name = String(p?.name ?? '')
      if (!nameMap.has(id)) nameMap.set(id, name)
    }
  }
  pushList(snapshot.value?.team_a?.players)
  pushList(snapshot.value?.team_b?.players)
  const card = snapshot.value?.batting_scorecard || {}
  for (const [id, row] of Object.entries(card)) {
    if (!nameMap.has(id)) nameMap.set(id, String((row as any)?.player_name ?? ''))
  }
  for (const id of appeared) {
    players.push({ id, name: nameMap.get(id) || id })
  }
  players.sort((a, b) => a.name.localeCompare(b.name))
  const matrix = players.map(() => players.map(() => 0))
  const index = new Map<string, number>()
  players.forEach((p, i) => index.set(p.id, i))
  for (const [key, value] of map.entries()) {
    const [a, b] = key.split('|')
    if (!index.has(a) || !index.has(b)) continue
    const ia = index.get(a)!
    const ib = index.get(b)!
    matrix[ia][ib] = matrix[ib][ia] = value
  }
  return { players, matrix }
})

function phaseBuckets(oversLimit: number): Array<{
  name: string
  start: number
  end: number
}> {
  if (oversLimit >= 45)
    return [
      { name: 'Powerplay', start: 1, end: 10 },
      { name: 'Middle', start: 11, end: oversLimit - 10 },
      { name: 'Death', start: oversLimit - 9, end: oversLimit },
    ]
  const death = Math.min(5, Math.floor(oversLimit / 4) || 1)
  const powerplay = Math.min(6, Math.max(1, Math.floor(oversLimit / 3) || 1))
  const middleEnd = Math.max(powerplay + 1, oversLimit - death)
  return [
    { name: 'Powerplay', start: 1, end: powerplay },
    { name: 'Middle', start: powerplay + 1, end: middleEnd },
    { name: 'Death', start: middleEnd + 1, end: oversLimit },
  ]
}

const phaseSplits = computed(() => {
  const oversLimit = Number(snapshot.value?.overs_limit ?? 0)
  if (!oversLimit)
    return [] as Array<{ name: string; runs: number; overs: number; wkts: number }>
  const buckets = phaseBuckets(oversLimit)
  const acc: Record<string, { runs: number; balls: number; wkts: number }> = {}
  for (const bucket of buckets) acc[bucket.name] = { runs: 0, balls: 0, wkts: 0 }
  for (const d of deliveries.value) {
    const over = Number(d.over_number ?? 0) + 1
    const bucket = buckets.find(b => over >= b.start && over <= b.end)
    if (!bucket) continue
    const entry = acc[bucket.name]
    entry.runs += Number(d.runs_scored ?? (d as any)?.runs ?? 0)
    if (isLegalBall(d)) entry.balls += 1
    if (d.is_wicket) entry.wkts += 1
  }
  return buckets.map(bucket => ({
    name: bucket.name,
    runs: acc[bucket.name].runs,
    overs: acc[bucket.name].balls / 6,
    wkts: acc[bucket.name].wkts,
  }))
})

const wagonStrokes = computed(() => {
  const out: Array<{ angleDeg: number; runs: number; kind?: '4' | '6' | 'other' }> = []
  for (const d of deliveries.value) {
    const angle = (d as any)?.shot_angle_deg
    if (angle == null || Number.isNaN(Number(angle))) continue
    const runs = Number(d.runs_scored ?? 0)
    const kind = runs === 6 ? '6' : runs === 4 ? '4' : 'other'
    out.push({ angleDeg: Number(angle), runs, kind })
  }
  return out
})

const shotMapDeliveries = computed(() => {
  const withMap = deliveries.value.filter((d) => {
    const value = (d as any)?.shot_map
    return typeof value === 'string' && value.length > 0
  })
  return withMap.reverse()
})
</script>

<template>
  <main class="container analytics">
    <h1>Match Analytics</h1>

    <section class="card">
      <h2>Search</h2>
      <div class="row">
        <input v-model="qTeamA" placeholder="Team A name" class="inp" />
        <input v-model="qTeamB" placeholder="Team B name" class="inp" />
        <button class="btn" :disabled="loading" @click="search">Search</button>
      </div>
      <div v-if="error" class="error">{{ error }}</div>
      <ul class="result-list">
        <li v-for="g in results" :key="g.id">
          <button class="link" @click="loadGame(g.id)">
            {{ g.team_a_name }} vs {{ g.team_b_name }}
            <small>({{ g.status }})</small>
          </button>
        </li>
      </ul>
    </section>

    <section v-if="selectedId && snapshot" class="grid">
      <div class="card wide">
        <h3>Run Rate Comparison</h3>
        <RunRateComparison
          :current-run-rate="crr"
          :required-run-rate="req.rrr"
          :current-score="currRuns"
          :balls-bowled="ballsBowled"
          :overs-limit="Number(snapshot?.overs_limit ?? 0)"
          :target-score="snapshot?.target ?? null"
        />
      </div>

      <div v-if="manhattanChart.labels.length" class="card">
        <h3>Manhattan (runs per over)</h3>
        <ChartBar :labels="manhattanChart.labels" :series="manhattanChart.series" />
      </div>

      <div v-if="wormChart.labels.length" class="card">
        <h3>Worm (cumulative)</h3>
        <ChartLine :labels="wormChart.labels" :series="wormChart.series" />
      </div>

      <div class="card">
        <h3>Extras / Dot & Boundary %</h3>
        <div class="extras-grid">
          <template v-for="(value, key) in extrasTotals" :key="key">
            <span class="label">{{ key }}</span>
            <span class="value">{{ value }}</span>
          </template>
        </div>
        <div class="summary">
          Legal balls: {{ dotBoundary.legal }},
          Dots: {{ dotBoundary.dots }} ({{ dotBoundary.dotPct.toFixed(1) }}%),
          Boundaries: {{ dotBoundary.boundaries }} ({{ dotBoundary.boundaryPct.toFixed(1) }}%)
        </div>
      </div>

      <div class="card wide">
        <h3>Batting</h3>
        <table class="tbl">
          <thead>
            <tr><th>Batter</th><th>R</th><th>B</th><th>SR</th><th>4s</th><th>6s</th><th>Dismissal</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in battingRows" :key="r.name">
              <td>{{ r.name }}</td>
              <td>{{ r.runs }}</td>
              <td>{{ r.balls }}</td>
              <td>{{ r.sr.toFixed(1) }}</td>
              <td>{{ r.fours }}</td>
              <td>{{ r.sixes }}</td>
              <td>{{ r.how_out }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card wide">
        <h3>Bowling</h3>
        <table class="tbl">
          <thead>
            <tr><th>Bowler</th><th>O</th><th>M</th><th>R</th><th>W</th><th>Econ</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in bowlingRows" :key="r.name">
              <td>{{ r.name }}</td>
              <td>{{ r.overs }}</td>
              <td>{{ r.maidens }}</td>
              <td>{{ r.runs }}</td>
              <td>{{ r.wickets }}</td>
              <td>{{ r.econ.toFixed(2) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card wide">
        <h3>Partnerships</h3>
        <div v-if="partnerships.players.length">
          <PartnershipHeatmap :players="partnerships.players" :matrix="partnerships.matrix" />
        </div>
        <div v-else class="empty">No partnership data yet.</div>
      </div>

      <div class="card">
        <h3>Phase Splits</h3>
        <PhaseSplits :splits="phaseSplits" />
      </div>

      <div class="card">
        <h3>Fall of Wickets</h3>
        <ul>
          <li v-for="(w, i) in fallOfWickets" :key="i">
            {{ w.score_at_fall }} at {{ w.over }}
          </li>
        </ul>
      </div>

      <div class="card">
        <h3>DLS Panel</h3>
        <div v-if="dlsPanel.target != null">Target: {{ dlsPanel.target }}</div>
        <div v-if="dlsPanel.par != null">Par: {{ dlsPanel.par }}</div>
        <div v-if="dlsPanel.ahead_by != null">Ahead by: {{ dlsPanel.ahead_by }}</div>
        <div v-else>—</div>
      </div>

      <div class="card">
        <h3>Wagon Wheel</h3>
        <WagonWheel :strokes="wagonStrokes" />
        <small v-if="!wagonStrokes.length" class="hint">
          Shot angles will appear here once captured during scoring.
        </small>
      </div>

      <div v-if="shotMapDeliveries.length" class="card wide">
        <h3>Shot Maps</h3>
        <ul class="shot-map-list">
          <li
            v-for="d in shotMapDeliveries.slice(0, 12)"
            :key="`${d.inning ?? 0}-${d.over_number ?? 0}-${d.ball_number ?? 0}`"
          >
            <div class="shot-map-meta">
              Inn {{ d.inning ?? '?' }},
              Over {{ (d.over_number ?? 0) + 1 }}.{{ d.ball_number ?? 0 }}
            </div>
            <ShotMapPreview :value="(d as any).shot_map" :size="88" />
          </li>
        </ul>
      </div>
    </section>
  </main>
</template>

<style scoped>
:root { --sticky-header-height: 96px; }
.container { max-width: 1100px; margin: 24px auto; padding: 0 12px; }
.analytics { padding-top: var(--sticky-header-height); }
.analytics h1, .analytics h2, .analytics h3 { scroll-margin-top: var(--sticky-header-height); }
.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.shot-map-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 12px; list-style: none; padding: 0; margin: 0; }
.shot-map-list li { display: flex; flex-direction: column; align-items: center; gap: 6px; }
.shot-map-meta { font-size: 0.8rem; color: #475569; text-align: center; }
.card { border: 1px solid #e5e7eb; border-radius: 12px; padding: 12px; background: #fff; }
.card.wide { grid-column: 1 / -1; }
.grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }
.inp { padding: 8px 10px; border: 1px solid #d1d5db; border-radius: 8px; }
.btn { padding: 8px 12px; border-radius: 8px; border: 1px solid #d1d5db; background: #f9fafb; cursor: pointer; }
.btn:disabled { opacity: .6; cursor: not-allowed; }
.result-list { margin: 8px 0; padding-left: 16px; }
.link { background: none; border: none; color: #2563eb; cursor: pointer; padding: 0; display: flex; align-items: center; gap: 6px; }
.error { color: #b91c1c; }
.tbl { width: 100%; border-collapse: collapse; }
.tbl th, .tbl td { border-bottom: 1px solid #eee; padding: 6px 8px; text-align: left; }
.extras-grid { display: grid; grid-template-columns: auto auto; gap: 6px; font-size: 13px; }
.label { color: #6b7280; }
.value { font-weight: 600; }
.summary { margin-top: 8px; font-size: 13px; }
.empty { color: #6b7280; font-size: 13px; }
.hint { display: block; margin-top: 8px; color: #6b7280; font-size: 12px; }
</style>

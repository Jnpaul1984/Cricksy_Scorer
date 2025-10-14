<script setup lang="ts">
import { computed, withDefaults, defineProps } from 'vue'
import { fmtSR } from '@/utils/cricket'

type BatEntry = {
  player_id: string
  player_name: string
  runs: number | string
  balls_faced: number | string
  fours: number | string
  sixes: number | string
  strike_rate?: number | string
  how_out?: string
  is_out: boolean
}

const props = withDefaults(defineProps<{
  entries: BatEntry[]
  strikerId?: string
  nonStrikerId?: string
}>(), {
  entries: () => [],
  strikerId: undefined,
  nonStrikerId: undefined,
})

/* ---------- helpers ---------- */
const i = (v: unknown) => {
  const n = Number(v)
  return Number.isFinite(n) ? Math.max(0, Math.trunc(n)) : 0
}
const f = (v: unknown) => {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}
function sr(e: BatEntry) {
  const given = f(e.strike_rate)
  if (given > 0) return given.toFixed(1)
  return fmtSR(i(e.runs), i(e.balls_faced))
}
function status(e: BatEntry) {
  if (e.is_out) return e.how_out ? `Out (${e.how_out})` : 'Out'
  return 'Not out'
}

/* ---------- view-model rows (normalized once) ---------- */
type Row = {
  id: string
  name: string
  runs: number
  balls: number
  fours: number
  sixes: number
  sr: string
  status: string
  isOut: boolean
  isStriker: boolean
  isNonStriker: boolean
}

const rows = computed<Row[]>(() =>
  (props.entries || []).map((e) => ({
    id: e.player_id,
    name: e.player_name,
    runs: i(e.runs),
    balls: i(e.balls_faced),
    fours: i(e.fours),
    sixes: i(e.sixes),
    sr: sr(e),
    status: status(e),
    isOut: !!e.is_out,
    isStriker: props.strikerId === e.player_id,
    isNonStriker: props.nonStrikerId === e.player_id,
  })),
)
</script>

<template>
  <div class="card" role="region" aria-label="Batting card">
    <h3>Batting</h3>

    <table v-if="rows.length">
      <caption class="visually-hidden">Batting scorecard</caption>
      <colgroup>
        <col />
        <col style="width:5ch" />
        <col style="width:5ch" />
        <col style="width:5ch" />
        <col style="width:5ch" />
        <col style="width:6ch" />
        <col />
      </colgroup>
      <thead>
        <tr>
          <th scope="col">Player</th>
          <th scope="col" class="num">R</th>
          <th scope="col" class="num">B</th>
          <th scope="col" class="num">4s</th>
          <th scope="col" class="num">6s</th>
          <th scope="col" class="num">SR</th>
          <th scope="col">Status</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id"
            :class="[{ out: r.isOut, striker: r.isStriker, nonStriker: r.isNonStriker }]">
          <td class="name" :title="r.name">
            <span class="dot" v-if="r.isStriker" aria-label="on strike" />
            <span class="nameText">{{ r.name }}</span>
          </td>
          <td class="num">{{ r.runs }}</td>
          <td class="num">{{ r.balls }}</td>
          <td class="num">{{ r.fours }}</td>
          <td class="num">{{ r.sixes }}</td>
          <td class="num">{{ r.sr }}</td>
          <td class="status" :title="r.status">{{ r.status }}</td>
        </tr>
      </tbody>
    </table>

    <div v-else class="empty">No batting entries yet.</div>
  </div>
</template>

<style scoped>
.card { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,.08); border-radius: 14px; padding: 12px; }
h3 { margin: 0 0 8px; font-size: 14px; font-weight: 800; }
table { width: 100%; border-collapse: collapse; }
caption.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
th, td { padding: 6px 8px; border-top: 1px dashed rgba(255,255,255,.08); }
thead th { border-top: 0; text-align: left; font-size: 12px; color: #9ca3af; font-weight: 700; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.name { font-weight: 700; max-width: 0; }
.nameText { display: inline-block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; vertical-align: bottom; }
.status { color: #9ca3af; font-size: 12px; }
.empty { color: #9ca3af; font-size: 13px; padding: 8px 0; }

/* highlights */
tr.striker .name { color: #e5ff7a; }
tr.nonStriker .name { color: #a7f3d0; }
tr.out .name { opacity: .7; }
.dot { display:inline-block; width:6px; height:6px; border-radius:50%; background:#e5ff7a; margin-right:6px; vertical-align: middle; }
</style>

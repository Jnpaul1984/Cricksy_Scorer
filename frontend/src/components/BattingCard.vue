<script setup lang="ts">
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

const props = defineProps<{ entries: BatEntry[] }>()

function normInt(v: unknown): number { const n = Number(v); return Number.isFinite(n) ? Math.max(0, Math.trunc(n)) : 0 }
function normNum(v: unknown): number { const n = Number(v); return Number.isFinite(n) ? n : 0 }

function sr(e: BatEntry) {
  // Prefer provided strike_rate if valid, else compute using normalized ints
  const given = normNum(e.strike_rate)
  if (given > 0) return given.toFixed(1)
  const runs = normInt(e.runs)
  const balls = normInt(e.balls_faced)
  return fmtSR(runs, balls)
}

function status(e: BatEntry) {
  if (e.is_out) return e.how_out ? `Out (${e.how_out})` : 'Out'
  return 'Not out'
}
</script>

<template>
  <div class="card">
    <h3>Batting</h3>
    <table v-if="props.entries.length">
      <thead>
        <tr>
          <th>Player</th>
          <th>R</th>
          <th>B</th>
          <th>4s</th>
          <th>6s</th>
          <th>SR</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="e in props.entries" :key="e.player_id">
          <td class="name">{{ e.player_name }}</td>
          <td class="num">{{ Number(e.runs) || 0 }}</td>
          <td class="num">{{ Number(e.balls_faced) || 0 }}</td>
          <td class="num">{{ Number(e.fours) || 0 }}</td>
          <td class="num">{{ Number(e.sixes) || 0 }}</td>
          <td class="num">{{ sr(e) }}</td>
          <td class="status">{{ status(e) }}</td>
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
th, td { padding: 6px 8px; border-top: 1px dashed rgba(255,255,255,.08); }
thead th { border-top: 0; text-align: left; font-size: 12px; color: #9ca3af; font-weight: 700; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.name { font-weight: 700; }
.status { color: #9ca3af; font-size: 12px; }
.empty { color: #9ca3af; font-size: 13px; padding: 8px 0; }
</style>
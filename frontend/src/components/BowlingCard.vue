<script setup lang="ts">
import { fmtEconomy, oversDisplayFromBalls } from '@/utils/cricket'

type BowlEntry = {
  player_id: string
  player_name: string
  overs_bowled?: number | string
  balls_bowled?: number | string
  maidens?: number | string
  runs_conceded: number | string
  wickets_taken: number | string
  economy?: number | string
}

const props = defineProps<{ entries: BowlEntry[] }>()

function econ(e: BowlEntry) {
  const given = Number(e.economy)
  if (Number.isFinite(given) && given > 0) return given.toFixed(2)
  const balls = Number(e.balls_bowled)
  if (Number.isFinite(balls) && balls > 0) return fmtEconomy(Number(e.runs_conceded)||0, balls)
  // Fallback from overs decimal, e.g. 3.4 → 22 balls
  const ob = Number(e.overs_bowled)
  if (!Number.isFinite(ob) || ob <= 0) return '—'
  const whole = Math.trunc(ob)
  const fracBalls = Math.round((ob - whole) * 10)
  const ballsFromOvers = whole * 6 + Math.min(5, Math.max(0, fracBalls))
  return fmtEconomy(Number(e.runs_conceded)||0, ballsFromOvers)
}

function oversText(e: BowlEntry) {
  const balls = Number(e.balls_bowled)
  if (Number.isFinite(balls) && balls >= 0) return oversDisplayFromBalls(balls)
  const ob = Number(e.overs_bowled)
  if (!Number.isFinite(ob)) return '0.0'
  return ob.toFixed(1)
}
</script>

<template>
  <div class="card">
    <h3>Bowling</h3>
    <table v-if="props.entries.length">
      <thead>
        <tr>
          <th>Player</th>
          <th>O</th>
          <th>M</th>
          <th>R</th>
          <th>W</th>
          <th>Econ</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="e in props.entries" :key="e.player_id">
          <td class="name">{{ e.player_name }}</td>
          <td class="num">{{ oversText(e) }}</td>
          <td class="num">{{ Number(e.maidens) || 0 }}</td>
          <td class="num">{{ Number(e.runs_conceded) || 0 }}</td>
          <td class="num">{{ Number(e.wickets_taken) || 0 }}</td>
          <td class="num">{{ econ(e) }}</td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty">No bowling entries yet.</div>
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
.empty { color: #9ca3af; font-size: 13px; padding: 8px 0; }
</style>

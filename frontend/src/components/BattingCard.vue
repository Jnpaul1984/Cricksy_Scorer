<script setup lang="ts">
type BatEntry = {
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

const props = defineProps<{ entries: BatEntry[] }>()

function sr(e: BatEntry) {
  // Prefer provided strike_rate; fall back to computed, avoid NaN
  const fromProp = Number.isFinite(e.strike_rate) ? e.strike_rate : undefined
  const computed = e.balls_faced ? (e.runs / e.balls_faced) * 100 : undefined
  const val = fromProp ?? computed
  return val != null ? val.toFixed(1) : '—'
}

function status(e: BatEntry) {
  if (e.is_out) return e.how_out ? `Out (${e.how_out})` : 'Out'
  return 'Not out'
}
</script>

<template>
  <div class="card">
    <h3>Batting</h3>
    <table v-if="entries.length">
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
        <tr v-for="e in entries" :key="e.player_id">
          <td class="name">{{ e.player_name }}</td>
          <td class="num">{{ e.runs }}</td>
          <td class="num">{{ e.balls_faced }}</td>
          <td class="num">{{ e.fours }}</td>
          <td class="num">{{ e.sixes }}</td>
          <td class="num">{{ sr(e) }}</td>
          <td class="status">{{ status(e) }}</td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty">No batting entries yet.</div>
  </div>
</template>

<script setup lang="ts">
type BatEntry = {
  player_id: string
  player_name: string
  runs: number
  balls_faced: number
  is_out: boolean
}
const props = defineProps<{ entries: BatEntry[] }>()
function sr(e: BatEntry) {
  return e.balls_faced ? ((e.runs / e.balls_faced) * 100).toFixed(1) : '—'
}
</script>

<template>
  <div class="card">
    <h3>Batting</h3>
    <table v-if="entries?.length">
      <thead>
        <tr>
          <th>Player</th>
          <th>R</th>
          <th>B</th>
          <th>SR</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="e in entries" :key="e.player_id">
          <td class="name">{{ e.player_name }}</td>
          <td class="num">{{ e.runs }}</td>
          <td class="num">{{ e.balls_faced }}</td>
          <td class="num">{{ sr(e) }}</td>
          <td class="status">{{ e.is_out ? 'Out' : 'Not out' }}</td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty">No batting data yet.</div>
  </div>
</template>

<style scoped>
.card{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.15);border-radius:16px;padding:1rem}
h3{color:#fff;margin:0 0 .75rem}
table{width:100%;border-collapse:collapse}
th,td{padding:.6rem .7rem;border-bottom:1px solid rgba(255,255,255,.08);color:#fff}
th{background:rgba(255,255,255,.06);text-align:left;font-weight:600}
.name{font-weight:500}
.num{font-variant-numeric:tabular-nums}
.status{opacity:.9}
.empty{color:#fff;opacity:.85}
</style>

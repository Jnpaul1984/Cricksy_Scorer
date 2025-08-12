<script setup lang="ts">
type BowlEntry = {
  player_id: string
  player_name: string
  overs_bowled: number
  runs_conceded: number
  wickets_taken: number
}
const props = defineProps<{ entries: BowlEntry[] }>()
function econ(e: BowlEntry) {
  return e.overs_bowled ? (e.runs_conceded / e.overs_bowled).toFixed(1) : '—'
}
</script>

<template>
  <div class="card">
    <h3>Bowling</h3>
    <table v-if="entries?.length">
      <thead>
        <tr>
          <th>Player</th>
          <th>Ov</th>
          <th>R</th>
          <th>W</th>
          <th>Econ</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="e in entries" :key="e.player_id">
          <td class="name">{{ e.player_name }}</td>
          <td class="num">{{ e.overs_bowled }}</td>
          <td class="num">{{ e.runs_conceded }}</td>
          <td class="num">{{ e.wickets_taken }}</td>
          <td class="num">{{ econ(e) }}</td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty">No bowling data yet.</div>
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
.empty{color:#fff;opacity:.85}
</style>

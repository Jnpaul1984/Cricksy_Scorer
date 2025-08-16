<script setup lang="ts">
type BowlEntry = {
  player_id: string
  player_name: string
  overs_bowled: number     // should already be normalized to O + balls/6
  maidens: number
  runs_conceded: number
  wickets_taken: number
  economy: number
}

const props = defineProps<{ entries: BowlEntry[] }>()

function econ(e: BowlEntry) {
  // Prefer provided economy; fall back to R/O
  const fromProp = Number.isFinite(e.economy) ? e.economy : undefined
  const computed = e.overs_bowled ? e.runs_conceded / e.overs_bowled : undefined
  const val = fromProp ?? computed
  return val != null ? val.toFixed(1) : '—'
}
</script>

<template>
  <div class="card">
    <h3>Bowling</h3>
    <table v-if="entries.length">
      <thead>
        <tr>
          <th>Player</th>
          <th>Ov</th>
          <th>M</th>
          <th>R</th>
          <th>W</th>
          <th>Econ</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="e in entries" :key="e.player_id">
          <td class="name">{{ e.player_name }}</td>
          <td class="num">{{ e.overs_bowled }}</td>
          <td class="num">{{ e.maidens }}</td>
          <td class="num">{{ e.runs_conceded }}</td>
          <td class="num">{{ e.wickets_taken }}</td>
          <td class="num">{{ econ(e) }}</td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty">No bowling entries yet.</div>
  </div>
</template>

<script setup lang="ts">
import { BaseCard } from '@/components'
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
  <BaseCard as="section" padding="md" class="bowling-card">
    <h3>Bowling</h3>
    <table v-if="props.entries.length">
      <thead>
        <tr>
          <th>Player</th>
          <th class="num">O</th>
          <th class="num">M</th>
          <th class="num">R</th>
          <th class="num">W</th>
          <th class="num">Econ</th>
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
  </BaseCard>
</template>

<style scoped>
/* BaseCard handles background/border/radius/padding */
.bowling-card h3 {
  margin: 0 0 var(--space-2);
  font-size: var(--text-sm);
  font-weight: var(--font-extrabold);
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: var(--space-2);
  border-top: 1px dashed var(--color-border-subtle);
}

thead th {
  border-top: 0;
  text-align: left;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-bold);
}

.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.name {
  font-weight: var(--font-bold);
}

.empty {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  padding: var(--space-2) 0;
}
</style>

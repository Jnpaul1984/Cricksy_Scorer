<template>
  <section class="as-root">
    <!-- Simple, type-safe analytics strip -->
    <div class="as-cards">
      <div class="as-card">
        <div class="as-title">Striker</div>
        <div class="as-row">
          <span class="as-label">Name</span>
          <span class="as-val">{{ snapshot?.batsmen.striker.name || '-' }}</span>
        </div>
        <div class="as-row">
          <span class="as-label">Runs (Balls)</span>
          <span class="as-val">{{ snapshot?.batsmen.striker.runs ?? 0 }} ({{ snapshot?.batsmen.striker.balls ?? 0 }})</span>
        </div>
        <div class="as-row">
          <span class="as-label">Dot %</span>
          <span class="as-val">{{ strikerDotPct }}</span>
        </div>
      </div>

      <div class="as-card">
        <div class="as-title">Bowler</div>
        <div class="as-row">
          <span class="as-label">Dot %</span>
          <span class="as-val">{{ bowlerDotPct }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

/*
  This component is intentionally small and strictly typed.
  It fixes TS2304/2552 you saw by:
  - Defining explicit props for strikerDots/strikerBalls/bowlerDots/bowlerBalls
  - Expecting a strict Snapshot shape where batsmen.striker and batsmen.non_striker are REQUIRED
  - Not referencing undeclared names like `batterDots` or `bowlerDotsC`
*/

type Batter = { id: string; name: string; runs: number; balls: number }
export type Snapshot = {
  score: { runs: number; wickets: number; overs: number }
  batsmen: { striker: Batter; non_striker: Batter }
}

const props = defineProps<{
  snapshot: Snapshot | null
  strikerDots: number
  strikerBalls: number
  bowlerDots: number
  bowlerBalls: number
}>()

const strikerDotPct = computed(() => {
  const balls = props.strikerBalls || 0
  const dots = props.strikerDots || 0
  return balls > 0 ? `${Math.round((dots / balls) * 100)}%` : '—'
})

const bowlerDotPct = computed(() => {
  const balls = props.bowlerBalls || 0
  const dots = props.bowlerDots || 0
  return balls > 0 ? `${Math.round((dots / balls) * 100)}%` : '—'
})
</script>

<style scoped>
.as-root { padding: 6px 8px; }
.as-cards { display: grid; grid-auto-flow: column; gap: 10px; }
.as-card { background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12); border-radius: 10px; padding: 8px 10px; }
.as-title { font-weight: 700; font-size: 12px; margin-bottom: 6px; opacity: .9; }
.as-row { display: flex; justify-content: space-between; gap: 10px; font-size: 12px; }
.as-label { color: #9ca3af; }
.as-val { font-variant-numeric: tabular-nums; }
@media (prefers-color-scheme: light) {
  .as-card { background: #ffffff; border-color: #e5e7eb; }
  .as-label { color: #6b7280; }
}
</style>

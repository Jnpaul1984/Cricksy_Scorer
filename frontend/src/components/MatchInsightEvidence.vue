<script setup lang="ts">
import { computed } from 'vue'

interface SourceRef {
  type: string
  id: string
  label: string
}

interface DecisivePhase {
  phase_id: string
  innings: number
  label: string
  over_range: [number, number]
  impact_score: number
}

interface MomentumShift {
  shift_id: string
  innings: number
  over: number
  impact_delta: number
}

interface TeamSummary {
  team_id: string
  team_name: string
  total_runs: number
  wickets_lost: number
  overs_faced: number
}

interface Props {
  sourceRefs?: SourceRef[]
  limitations?: string[]
  groundingSummary?: string | null
  confidenceScore?: number | null
  decisivePhases?: DecisivePhase[]
  momentumShifts?: MomentumShift[]
  teams?: TeamSummary[]
}

const props = withDefaults(defineProps<Props>(), {
  sourceRefs: () => [],
  limitations: () => [],
  groundingSummary: null,
  confidenceScore: null,
  decisivePhases: () => [],
  momentumShifts: () => [],
  teams: () => [],
})

const sourceReferences = computed(() => props.sourceRefs.filter((ref) => ref.type !== 'metric'))

const supportingMetrics = computed(() => {
  const metrics: string[] = []

  for (const ref of props.sourceRefs) {
    if (ref.type === 'metric') metrics.push(ref.label)
  }

  for (const phase of props.decisivePhases.slice(0, 3)) {
    metrics.push(
      `${phase.label} (innings ${phase.innings}, overs ${phase.over_range[0]}-${phase.over_range[1]}): impact ${
        phase.impact_score >= 0 ? '+' : ''
      }${phase.impact_score.toFixed(2)}`,
    )
  }

  for (const team of props.teams.slice(0, 2)) {
    const overs = team.overs_faced > 0 ? team.overs_faced : 0
    const runRate = overs > 0 ? (team.total_runs / overs).toFixed(2) : '—'
    metrics.push(`${team.team_name}: ${team.total_runs}/${team.wickets_lost} in ${team.overs_faced} ov (RR ${runRate})`)
  }

  for (const shift of props.momentumShifts.slice(0, 2)) {
    metrics.push(
      `Momentum shift (innings ${shift.innings}, over ${shift.over}): impact Δ ${
        shift.impact_delta >= 0 ? '+' : ''
      }${shift.impact_delta.toFixed(2)}`,
    )
  }

  return Array.from(new Set(metrics))
})

const caveats = computed(() => {
  const items = [...props.limitations]
  if (sourceReferences.value.length === 0) {
    items.push('Source/provenance references were not provided for this advisory claim.')
  }
  if (supportingMetrics.value.length === 0) {
    items.push('Deterministic support metrics are limited for this advisory claim.')
  }
  if (props.confidenceScore == null) {
    items.push('Confidence score is unavailable.')
  } else if (props.confidenceScore < 0.5) {
    items.push('Low-confidence advisory; verify with scorecard and phase data before action.')
  }
  return Array.from(new Set(items))
})

const hasGroundingSummary = computed(() => {
  return typeof props.groundingSummary === 'string' && props.groundingSummary.trim().length > 0
})
</script>

<template>
  <section class="mie-block" data-testid="match-insight-evidence">
    <section v-if="hasGroundingSummary || supportingMetrics.length" class="mie-section">
      <h5 class="mie-title">Supporting data</h5>
      <p v-if="hasGroundingSummary" class="mie-summary">{{ groundingSummary }}</p>
      <ul v-if="supportingMetrics.length" class="mie-list" data-testid="match-insight-supporting-data">
        <li v-for="metric in supportingMetrics" :key="metric">{{ metric }}</li>
      </ul>
    </section>

    <section class="mie-section">
      <h5 class="mie-title">Source references</h5>
      <ul v-if="sourceReferences.length" class="mie-list" data-testid="match-insight-source-refs">
        <li v-for="source in sourceReferences" :key="`${source.type}-${source.id}`">
          {{ source.label }} <span class="mie-muted">({{ source.type }})</span>
        </li>
      </ul>
      <p v-else class="mie-muted">No source references were provided.</p>
    </section>

    <section class="mie-section">
      <h5 class="mie-title">Caveats</h5>
      <ul class="mie-list" data-testid="match-insight-caveats">
        <li v-for="caveat in caveats" :key="caveat">{{ caveat }}</li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.mie-block {
  display: grid;
  gap: 0.5rem;
}

.mie-section {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 0.75rem;
  padding: 0.75rem;
  background: rgba(11, 18, 32, 0.4);
}

.mie-title {
  margin: 0 0 0.4rem;
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  text-transform: uppercase;
}

.mie-summary {
  margin: 0 0 0.4rem;
  font-size: 0.86rem;
}

.mie-list {
  margin: 0;
  padding-left: 1rem;
  display: grid;
  gap: 0.35rem;
  font-size: 0.82rem;
}

.mie-muted {
  opacity: 0.74;
}
</style>

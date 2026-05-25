<script setup lang="ts">
import { computed } from 'vue'

import BaseBadge from './BaseBadge.vue'
import BaseCard from './BaseCard.vue'
import AiInsightReviewCard from './AiInsightReviewCard.vue'

import type { PlayerAIInsights } from '@/services/api'

interface Props {
  playerName: string
  playerRole: string
  insights: PlayerAIInsights | null
  loading?: boolean
  error?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
})

const hasInsights = computed(() => Boolean(props.insights))
const insightId = computed(() => props.insights?.player_id ?? '')

const mainStrength = computed(() => props.insights?.strengths?.[0] ?? null)
const mainImprovement = computed(() => props.insights?.weaknesses?.[0] ?? null)

const technicalFocus = computed(() => {
  if (!props.insights) return null
  const recommendation = props.insights.recommendations.find((item) =>
    /(shot|bat|bowl|length|variation|fundamental|technique|pace)/i.test(item),
  )
  return recommendation ?? props.insights.recommendations[0] ?? mainImprovement.value
})

const tacticalFocus = computed(() => {
  if (!props.insights) return null
  const recommendation = props.insights.recommendations.find((item) =>
    /(pressure|selection|situations|rotation|build|innings|scenario|tempo)/i.test(item),
  )
  return recommendation ?? props.insights.recommendations[1] ?? props.insights.summary ?? null
})

const recommendedDrillCategory = computed(() => {
  const hint = `${technicalFocus.value ?? ''} ${mainImprovement.value ?? ''}`.toLowerCase()
  if (!hint.trim()) return null
  if (hint.includes('bowl') || hint.includes('economy') || hint.includes('length')) {
    return 'Bowling consistency drills'
  }
  if (hint.includes('field') || hint.includes('catch') || hint.includes('run-out')) {
    return 'Fielding repetition drills'
  }
  if (hint.includes('strike') || hint.includes('bat') || hint.includes('shot') || hint.includes('innings')) {
    return 'Batting tempo and shot-selection drills'
  }
  return 'Foundational skill reinforcement drills'
})

const confidenceScore = computed(() => props.insights?.ai_metadata?.confidence_score ?? null)
const confidencePercent = computed(() =>
  confidenceScore.value == null ? null : Math.round(confidenceScore.value * 100),
)
const confidenceLabel = computed(() => {
  if (confidencePercent.value == null) return 'Not available'
  if (confidencePercent.value >= 80) return 'High confidence'
  if (confidencePercent.value >= 50) return 'Medium confidence'
  return 'Low confidence (early signal)'
})

const limitations = computed(() => props.insights?.ai_metadata?.limitations ?? [])
const sourceRefs = computed(() => props.insights?.ai_metadata?.source_refs ?? [])
const sampleWarning = computed(() => {
  if (!props.insights) return null
  if (limitations.value.length > 0) return limitations.value[0]
  const trendPoints = props.insights.recent_form?.trend?.length ?? 0
  if (trendPoints < 5) {
    return `Limited recent-form sample (${trendPoints} trend point${trendPoints === 1 ? '' : 's'}). Treat this as a developmental early signal.`
  }
  return null
})
</script>

<template>
  <BaseCard padding="lg" class="player-dev-card" data-testid="player-development-insight-card">
    <header class="player-dev-header">
      <h3>Player Development Card</h3>
      <div class="player-dev-context">
        <BaseBadge variant="primary" :uppercase="false">{{ playerName }}</BaseBadge>
        <BaseBadge variant="neutral" :uppercase="false">{{ playerRole }}</BaseBadge>
      </div>
    </header>

    <div v-if="loading" class="player-dev-loading" data-testid="player-dev-loading">
      Loading player development insight…
    </div>

    <p v-else-if="error" class="player-dev-error" data-testid="player-dev-error">
      {{ error }}
    </p>

    <p
      v-else-if="!hasInsights"
      class="player-dev-empty"
      data-testid="player-dev-empty"
    >
      Insufficient data to generate player development guidance yet.
    </p>

    <div v-else class="player-dev-grid">
      <section>
        <h4>Main strength</h4>
        <p>{{ mainStrength ?? 'No clear strength identified yet.' }}</p>
      </section>
      <section>
        <h4>Main improvement area</h4>
        <p>{{ mainImprovement ?? 'No improvement focus identified yet.' }}</p>
      </section>
      <section>
        <h4>Technical focus</h4>
        <p>{{ technicalFocus ?? 'No technical focus available yet.' }}</p>
      </section>
      <section>
        <h4>Tactical focus</h4>
        <p>{{ tacticalFocus ?? 'No tactical focus available yet.' }}</p>
      </section>
      <section>
        <h4>Recommended drill category</h4>
        <p>{{ recommendedDrillCategory ?? 'Collect more training data to recommend drills.' }}</p>
      </section>
      <section>
        <h4>Confidence level</h4>
        <p data-testid="player-dev-confidence">
          <template v-if="confidencePercent != null">
            {{ confidencePercent }}% · {{ confidenceLabel }}
          </template>
          <template v-else>{{ confidenceLabel }}</template>
        </p>
      </section>
      <section v-if="sampleWarning">
        <h4>Sample-size warning</h4>
        <p data-testid="player-dev-sample-warning">{{ sampleWarning }}</p>
      </section>
      <section v-if="limitations.length > 0">
        <h4>Limitations</h4>
        <ul>
          <li v-for="(item, idx) in limitations" :key="idx">{{ item }}</li>
        </ul>
      </section>
      <section v-if="sourceRefs.length > 0">
        <h4>Source references</h4>
        <ul data-testid="player-dev-source-refs">
          <li v-for="ref in sourceRefs" :key="`${ref.type}-${ref.id}`">{{ ref.label }}</li>
        </ul>
      </section>
      <AiInsightReviewCard
        :insight-type="'insight'"
        :insight-id="insightId"
        title="Coach review status"
        :can-review="false"
      />
    </div>
  </BaseCard>
</template>

<style scoped>
.player-dev-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.player-dev-header h3 {
  margin: 0;
  font-size: var(--h4-size);
}

.player-dev-context {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.player-dev-grid {
  display: grid;
  gap: var(--space-3);
}

.player-dev-grid h4 {
  margin: 0 0 var(--space-1);
  font-size: var(--text-sm);
}

.player-dev-grid p,
.player-dev-grid li {
  margin: 0;
  color: var(--color-text-muted);
}

.player-dev-grid ul {
  margin: 0;
  padding-left: 1rem;
}

.player-dev-loading,
.player-dev-empty,
.player-dev-error {
  color: var(--color-text-muted);
}

.player-dev-error {
  color: var(--color-error);
}
</style>

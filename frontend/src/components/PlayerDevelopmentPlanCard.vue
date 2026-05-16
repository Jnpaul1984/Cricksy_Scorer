<script setup lang="ts">
/**
 * PlayerDevelopmentPlanCard.vue — Phase 9D
 *
 * Coach-facing component that renders a single draft player development plan.
 * All plans displayed here are ADVISORY / DRAFT only.
 *
 * Rules enforced:
 * - Development areas use safe_display_label, never the raw internal label.
 * - No activation or approval controls are shown.
 * - Confidence and limitations are always shown when present.
 * - Evidence references are always shown when present.
 * - Coach review required badge is always visible on draft plans.
 */

import { computed } from 'vue'

import BaseBadge from './BaseBadge.vue'
import BaseCard from './BaseCard.vue'

import type {
  PlayerDevelopmentPlanDraftBundle,
} from '@/services/playerDevelopmentApi'

interface Props {
  bundle: PlayerDevelopmentPlanDraftBundle
}

const props = defineProps<Props>()

const plan = computed(() => props.bundle.plan)
const goals = computed(() => props.bundle.goals)
const strengthTags = computed(() => props.bundle.strength_tags)
const weaknessTags = computed(() => props.bundle.weakness_tags)
const drills = computed(() => props.bundle.drill_assignments)
const checkpoints = computed(() => props.bundle.progress_checkpoints)

const confidencePercent = computed(() => {
  const score = plan.value.confidence_score
  if (score === null || score === undefined) return null
  return Math.round(score * 100)
})

const confidenceLabel = computed(() => {
  const pct = confidencePercent.value
  if (pct === null) return 'Not available'
  if (pct >= 80) return 'High confidence'
  if (pct >= 50) return 'Medium confidence'
  return 'Low confidence (early signal)'
})

const limitations = computed<string[]>(() => {
  const meta = plan.value.ai_metadata
  if (Array.isArray(meta?.limitations)) return meta.limitations as string[]
  return []
})

const evidenceRefs = computed(() => plan.value.evidence_refs ?? [])

const approvalStateLabel = computed(() => {
  switch (plan.value.approval_state) {
    case 'approved':
      return 'Approved'
    case 'rejected':
      return 'Rejected'
    case 'pending_review':
      return 'Pending review'
    case 'not_required':
      return 'No review required'
    case 'changes_requested':
      return 'Changes requested'
    default:
      return plan.value.approval_state
  }
})

const approvalBadgeVariant = computed<'success' | 'warning' | 'neutral' | 'primary'>(() => {
  switch (plan.value.approval_state) {
    case 'approved':
      return 'success'
    case 'rejected':
      return 'warning'
    case 'pending_review':
      return 'primary'
    default:
      return 'neutral'
  }
})

const statusLabel = computed(() => {
  switch (plan.value.status) {
    case 'draft':
      return 'Draft'
    case 'active':
      return 'Active'
    case 'paused':
      return 'Paused'
    case 'completed':
      return 'Completed'
    case 'archived':
      return 'Archived'
    default:
      return plan.value.status
  }
})

const statusBadgeVariant = computed<'success' | 'warning' | 'neutral' | 'primary'>(() => {
  switch (plan.value.status) {
    case 'active':
      return 'success'
    case 'draft':
      return 'warning'
    default:
      return 'neutral'
  }
})

const isAiAssisted = computed(() =>
  plan.value.source_type === 'ai_insight',
)

const formattedDate = (isoString: string | null): string => {
  if (!isoString) return '—'
  try {
    return new Date(isoString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return isoString
  }
}
</script>

<template>
  <BaseCard padding="lg" class="plan-card" data-testid="player-development-plan-card">
    <!-- Plan Header -->
    <header class="plan-header">
      <div class="plan-title-row">
        <h3 class="plan-title">{{ plan.title }}</h3>
        <div class="plan-badges">
          <BaseBadge variant="warning" data-testid="plan-draft-badge">
            Draft
          </BaseBadge>
          <BaseBadge variant="primary" data-testid="plan-review-badge">
            Coach review required
          </BaseBadge>
          <BaseBadge :variant="statusBadgeVariant" data-testid="plan-status-badge">
            {{ statusLabel }}
          </BaseBadge>
          <BaseBadge v-if="isAiAssisted" variant="neutral" data-testid="plan-ai-badge">
            AI-assisted advisory
          </BaseBadge>
        </div>
      </div>

      <div class="plan-meta">
        <span class="meta-item">
          <span class="meta-label">Approval:</span>
          <BaseBadge :variant="approvalBadgeVariant" condensed data-testid="plan-approval-state">
            {{ approvalStateLabel }}
          </BaseBadge>
        </span>
        <span v-if="!plan.coach_approved" class="meta-item" data-testid="plan-not-approved">
          <BaseBadge variant="neutral" condensed>Not yet coach-approved</BaseBadge>
        </span>
        <span class="meta-item">
          <span class="meta-label">Created:</span> {{ formattedDate(plan.created_at) }}
        </span>
      </div>

      <p v-if="plan.summary" class="plan-summary" data-testid="plan-summary">
        {{ plan.summary }}
      </p>
    </header>

    <div class="plan-body">
      <!-- Confidence -->
      <section class="plan-section">
        <h4 class="section-title">Confidence</h4>
        <p data-testid="plan-confidence">
          <template v-if="confidencePercent !== null">
            {{ confidencePercent }}% · {{ confidenceLabel }}
          </template>
          <template v-else>{{ confidenceLabel }}</template>
        </p>
      </section>

      <!-- Limitations -->
      <section v-if="limitations.length > 0" class="plan-section">
        <h4 class="section-title">Limitations</h4>
        <ul data-testid="plan-limitations">
          <li v-for="(item, idx) in limitations" :key="`lim-${idx}`">{{ item }}</li>
        </ul>
      </section>

      <!-- Evidence References -->
      <section v-if="evidenceRefs.length > 0" class="plan-section">
        <h4 class="section-title">Evidence references</h4>
        <ul data-testid="plan-evidence-refs">
          <li v-for="ref in evidenceRefs" :key="`${ref.type}-${ref.id}`">
            {{ ref.label }}
          </li>
        </ul>
      </section>

      <!-- Strengths -->
      <section class="plan-section" data-testid="plan-strengths-section">
        <h4 class="section-title">Strengths</h4>
        <ul v-if="strengthTags.length > 0" data-testid="plan-strengths">
          <li v-for="tag in strengthTags" :key="tag.id">
            <span class="tag-label">{{ tag.label }}</span>
            <span v-if="tag.category" class="tag-category"> · {{ tag.category }}</span>
          </li>
        </ul>
        <p v-else class="empty-sub" data-testid="plan-strengths-empty">
          No strengths identified yet.
        </p>
      </section>

      <!-- Development Areas (always use safe_display_label) -->
      <section class="plan-section" data-testid="plan-dev-areas-section">
        <h4 class="section-title">Development areas</h4>
        <ul v-if="weaknessTags.length > 0" data-testid="plan-dev-areas">
          <li v-for="tag in weaknessTags" :key="tag.id">
            <span class="tag-label" data-testid="dev-area-label">{{ tag.safe_display_label }}</span>
            <span v-if="tag.category" class="tag-category"> · {{ tag.category }}</span>
            <BaseBadge
              v-if="tag.severity !== 'medium'"
              variant="neutral"
              condensed
              class="tag-severity"
            >
              {{ tag.severity }}
            </BaseBadge>
          </li>
        </ul>
        <p v-else class="empty-sub" data-testid="plan-dev-areas-empty">
          No development areas identified yet.
        </p>
      </section>

      <!-- Goals -->
      <section class="plan-section" data-testid="plan-goals-section">
        <h4 class="section-title">Goals</h4>
        <ul v-if="goals.length > 0" data-testid="plan-goals">
          <li v-for="goal in goals" :key="goal.id" class="goal-item">
            <span class="goal-title">{{ goal.title }}</span>
            <BaseBadge variant="warning" condensed class="goal-status-badge">
              {{ goal.status }}
            </BaseBadge>
            <p v-if="goal.description" class="goal-description">{{ goal.description }}</p>
            <p v-if="goal.due_date" class="goal-due">
              Due: {{ formattedDate(goal.due_date) }}
            </p>
          </li>
        </ul>
        <p v-else class="empty-sub" data-testid="plan-goals-empty">No goals assigned yet.</p>
      </section>

      <!-- Drills -->
      <section class="plan-section" data-testid="plan-drills-section">
        <h4 class="section-title">Drill assignments</h4>
        <div v-if="drills.length > 0" class="drills-list" data-testid="plan-drills">
          <div v-for="drill in drills" :key="drill.id" class="drill-item">
            <div class="drill-header">
              <span class="drill-name">{{ drill.drill_name }}</span>
              <BaseBadge variant="neutral" condensed>{{ drill.status }}</BaseBadge>
            </div>
            <p v-if="drill.drill_description" class="drill-description">
              {{ drill.drill_description }}
            </p>
            <span v-if="drill.frequency" class="drill-frequency">
              Frequency: {{ drill.frequency }}
            </span>
          </div>
        </div>
        <p v-else class="empty-sub" data-testid="plan-drills-empty">No drills assigned yet.</p>
      </section>

      <!-- Checkpoints -->
      <section class="plan-section" data-testid="plan-checkpoints-section">
        <h4 class="section-title">Progress checkpoints <span class="advisory-note">(planned / advisory)</span></h4>
        <div v-if="checkpoints.length > 0" class="checkpoints-list" data-testid="plan-checkpoints">
          <div v-for="cp in checkpoints" :key="cp.id" class="checkpoint-item">
            <div class="checkpoint-header">
              <span class="checkpoint-date">{{ formattedDate(cp.checkpoint_date) }}</span>
              <BaseBadge variant="neutral" condensed>{{ cp.progress_status }}</BaseBadge>
            </div>
            <p class="checkpoint-summary">{{ cp.summary }}</p>
          </div>
        </div>
        <p v-else class="empty-sub" data-testid="plan-checkpoints-empty">
          No checkpoints yet.
        </p>
      </section>
    </div>

    <!-- Advisory footer -->
    <footer class="plan-advisory-footer" data-testid="plan-advisory-footer">
      <p>
        ⚠️ This is a <strong>draft development plan</strong> generated for coach review only.
        It is advisory and must not be treated as official player assessment or truth.
        Plans require coach review before any action.
      </p>
    </footer>
  </BaseCard>
</template>

<style scoped>
.plan-card {
  border: 2px solid var(--color-border);
}

.plan-header {
  margin-bottom: var(--space-md, 1rem);
}

.plan-title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: var(--space-sm, 0.5rem);
  margin-bottom: var(--space-sm, 0.5rem);
}

.plan-title {
  margin: 0;
  font-size: var(--text-lg, 1.125rem);
  flex: 1 1 auto;
}

.plan-badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs, 0.25rem);
}

.plan-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-md, 1rem);
  align-items: center;
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-muted);
  margin-bottom: var(--space-sm, 0.5rem);
}

.meta-label {
  font-weight: 600;
  margin-right: var(--space-xs, 0.25rem);
}

.plan-summary {
  margin: var(--space-sm, 0.5rem) 0 0;
  color: var(--color-muted);
}

.plan-body {
  display: grid;
  gap: var(--space-md, 1rem);
  margin-top: var(--space-md, 1rem);
}

.plan-section h4.section-title {
  margin: 0 0 var(--space-xs, 0.25rem);
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-on-surface);
  font-weight: 600;
}

.plan-section ul {
  margin: 0;
  padding-left: 1.25rem;
}

.plan-section li {
  margin-bottom: var(--space-xs, 0.25rem);
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-muted);
}

.plan-section p {
  margin: 0;
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-muted);
}

.tag-label {
  font-weight: 500;
}

.tag-category {
  color: var(--color-muted);
  font-size: var(--text-xs, 0.75rem);
}

.tag-severity {
  margin-left: var(--space-xs, 0.25rem);
}

.goal-item {
  list-style: none;
  padding: var(--space-sm, 0.5rem);
  background: var(--color-surface-alt);
  border-radius: var(--radius-sm, 0.25rem);
  margin-bottom: var(--space-xs, 0.25rem);
}

.goal-title {
  font-weight: 600;
  font-size: var(--text-sm, 0.875rem);
}

.goal-status-badge {
  margin-left: var(--space-xs, 0.25rem);
}

.goal-description,
.goal-due {
  margin: var(--space-xs, 0.25rem) 0 0;
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-muted);
}

.drills-list,
.checkpoints-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 0.5rem);
}

.drill-item,
.checkpoint-item {
  padding: var(--space-sm, 0.5rem);
  background: var(--color-surface-alt);
  border-radius: var(--radius-sm, 0.25rem);
  border: 1px solid var(--color-border);
}

.drill-header,
.checkpoint-header {
  display: flex;
  align-items: center;
  gap: var(--space-xs, 0.25rem);
  margin-bottom: var(--space-xs, 0.25rem);
}

.drill-name,
.checkpoint-date {
  font-weight: 600;
  font-size: var(--text-sm, 0.875rem);
}

.drill-description,
.checkpoint-summary {
  margin: var(--space-xs, 0.25rem) 0 0;
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-muted);
}

.drill-frequency {
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-muted);
}

.empty-sub {
  color: var(--color-muted);
  font-style: italic;
}

.advisory-note {
  font-size: var(--text-xs, 0.75rem);
  font-weight: 400;
  color: var(--color-muted);
  margin-left: var(--space-xs, 0.25rem);
}

.plan-advisory-footer {
  margin-top: var(--space-md, 1rem);
  padding: var(--space-sm, 0.5rem);
  border-top: 1px solid var(--color-border);
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-muted);
}

.plan-advisory-footer p {
  margin: 0;
}
</style>

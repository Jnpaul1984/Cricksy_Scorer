<script setup lang="ts">
/**
 * AiInsightReviewCard.vue — Phase 8C
 *
 * Displays the current review state and reviewer controls for an AI-generated insight.
 *
 * Governance rule:
 *   This component handles advisory review metadata only.
 *   It must never be used to mutate official cricket truth.
 *
 * Props:
 *   insightType   — AI output type (summary | insight | recommendation | report | commentary | draft)
 *   insightId     — Logical ID (match_id, player_id, etc.)
 *   title         — Human-readable insight title
 *   explanation   — Insight explanation / rationale text
 *   confidence    — Optional confidence score 0.0–1.0
 *   limitations   — Optional known limitations list
 *   sourceRefs    — Optional source reference list
 *   canReview     — Whether the current user is authorized to submit reviews
 */

import { ref, computed, onMounted } from 'vue'

import BaseBadge from './BaseBadge.vue'
import BaseButton from './BaseButton.vue'
import BaseCard from './BaseCard.vue'

import {
  getAiInsightReviewState,
  submitAiInsightReview,
  type AiInsightReviewState,
  type AiInsightFeedbackType,
  type AiInsightReviewStateResponse,
} from '@/services/api'

interface SourceRef {
  type: string
  id: string
  label: string
}

interface Props {
  insightType: string
  insightId: string
  title: string
  explanation?: string
  confidence?: number | null
  limitations?: string[]
  sourceRefs?: SourceRef[]
  /** True when the authenticated user has analyst_pro or org_pro role. */
  canReview?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  explanation: '',
  confidence: null,
  limitations: () => [],
  sourceRefs: () => [],
  canReview: false,
})

// ── State ──────────────────────────────────────────────────────────────────

const loading = ref(false)
const submitting = ref(false)
const error = ref<string | null>(null)
const successMsg = ref<string | null>(null)

const reviewState = ref<AiInsightReviewStateResponse | null>(null)

// Form state
const selectedReviewState = ref<AiInsightReviewState>('approved')
const selectedFeedbackType = ref<AiInsightFeedbackType | ''>('')
const reviewNote = ref('')
const showReviewForm = ref(false)

// ── Computed ───────────────────────────────────────────────────────────────

const currentState = computed<AiInsightReviewState>(
  () => reviewState.value?.current_state ?? 'pending',
)

const confidencePct = computed(() => {
  if (props.confidence == null) return null
  return Math.round(props.confidence * 100)
})

const confidenceLabel = computed(() => {
  if (confidencePct.value == null) return null
  if (confidencePct.value >= 80) return 'High'
  if (confidencePct.value >= 50) return 'Medium'
  return 'Low'
})

function stateBadgeVariant(
  state: AiInsightReviewState,
): 'success' | 'warning' | 'danger' | 'neutral' | 'primary' {
  switch (state) {
    case 'approved':
      return 'success'
    case 'rejected':
      return 'danger'
    case 'flagged':
      return 'danger'
    case 'changes_requested':
      return 'warning'
    default:
      return 'neutral'
  }
}

function stateLabel(state: AiInsightReviewState): string {
  switch (state) {
    case 'pending':
      return 'Pending review'
    case 'approved':
      return 'Approved'
    case 'rejected':
      return 'Rejected'
    case 'changes_requested':
      return 'Changes requested'
    case 'flagged':
      return 'Flagged'
  }
}

// ── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(async () => {
  await fetchReviewState()
})

// ── Methods ────────────────────────────────────────────────────────────────

async function fetchReviewState() {
  loading.value = true
  error.value = null
  try {
    reviewState.value = await getAiInsightReviewState(props.insightType, props.insightId)
  } catch {
    // Non-reviewer callers will receive 403; treat as no state loaded silently.
    reviewState.value = null
  } finally {
    loading.value = false
  }
}

async function submitReview() {
  if (!selectedReviewState.value) return

  submitting.value = true
  error.value = null
  successMsg.value = null

  try {
    await submitAiInsightReview(props.insightType, props.insightId, {
      review_state: selectedReviewState.value,
      feedback_type: (selectedFeedbackType.value as AiInsightFeedbackType) || null,
      note: reviewNote.value.trim() || null,
    })
    successMsg.value = 'Review submitted.'
    showReviewForm.value = false
    reviewNote.value = ''
    selectedFeedbackType.value = ''
    await fetchReviewState()
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Failed to submit review.'
    error.value = msg
  } finally {
    submitting.value = false
  }
}

function openReviewForm() {
  showReviewForm.value = true
  successMsg.value = null
  error.value = null
}

function cancelReview() {
  showReviewForm.value = false
  error.value = null
}
</script>

<template>
  <BaseCard padding="md" class="air-card" data-testid="ai-insight-review-card">
    <!-- Header row -->
    <header class="air-header">
      <div class="air-title-row">
        <h3 class="air-title">{{ title }}</h3>
        <BaseBadge variant="neutral" size="sm" :uppercase="false" class="air-advisory-badge">
          AI Advisory
        </BaseBadge>
      </div>

      <!-- Review state badge (always shown if loaded) -->
      <div v-if="!loading && reviewState" class="air-state-row">
        <BaseBadge
          :variant="stateBadgeVariant(currentState)"
          :uppercase="false"
          data-testid="review-state-badge"
        >
          {{ stateLabel(currentState) }}
        </BaseBadge>
        <span v-if="reviewState.total_reviews > 0" class="air-review-count">
          {{ reviewState.total_reviews }} review{{ reviewState.total_reviews === 1 ? '' : 's' }}
        </span>
      </div>

      <!-- Loading skeleton for review state -->
      <div v-else-if="loading" class="air-state-row">
        <span class="air-skeleton air-skeleton--badge" />
      </div>
    </header>

    <!-- Advisory notice -->
    <p class="air-advisory-notice" data-testid="advisory-notice">
      This insight is advisory only and does not change official scoring, match records, or
      official player statistics.
    </p>

    <!-- Explanation -->
    <p v-if="explanation" class="air-explanation" data-testid="insight-explanation">
      {{ explanation }}
    </p>

    <!-- Confidence band -->
    <div
      v-if="confidencePct != null"
      class="air-confidence"
      data-testid="confidence-band"
    >
      <span class="air-meta-label">Confidence</span>
      <span class="air-confidence-value">
        {{ confidencePct }}% · {{ confidenceLabel }}
      </span>
    </div>

    <!-- Limitations -->
    <section
      v-if="limitations && limitations.length > 0"
      class="air-limitations"
      data-testid="limitations-section"
    >
      <p class="air-meta-label">Limitations</p>
      <ul class="air-limitations-list">
        <li v-for="(lim, idx) in limitations" :key="idx">{{ lim }}</li>
      </ul>
    </section>

    <!-- Source references -->
    <section
      v-if="sourceRefs && sourceRefs.length > 0"
      class="air-sources"
      data-testid="source-refs-section"
    >
      <p class="air-meta-label">Sources</p>
      <ul class="air-sources-list">
        <li v-for="ref in sourceRefs" :key="ref.id" class="air-source-item">
          <BaseBadge variant="neutral" size="sm" :uppercase="false">{{ ref.type }}</BaseBadge>
          <span class="air-source-label">{{ ref.label }}</span>
        </li>
      </ul>
    </section>

    <!-- Latest reviewer note (read-only) -->
    <div
      v-if="reviewState?.latest_review?.note"
      class="air-latest-note"
      data-testid="latest-reviewer-note"
    >
      <p class="air-meta-label">Reviewer note</p>
      <p class="air-note-text">{{ reviewState.latest_review.note }}</p>
    </div>

    <!-- Success message -->
    <p
      v-if="successMsg"
      class="air-success"
      role="status"
      data-testid="review-success-msg"
    >
      {{ successMsg }}
    </p>

    <!-- Error message -->
    <p
      v-if="error"
      class="air-error"
      role="alert"
      data-testid="review-error-msg"
    >
      {{ error }}
    </p>

    <!-- Reviewer actions (visible only to authorized users) -->
    <div v-if="canReview" class="air-actions" data-testid="reviewer-actions">
      <BaseButton
        v-if="!showReviewForm"
        variant="ghost"
        size="sm"
        data-testid="open-review-form-btn"
        @click="openReviewForm"
      >
        Review insight
      </BaseButton>

      <!-- Inline review form -->
      <form
        v-if="showReviewForm"
        class="air-review-form"
        data-testid="review-form"
        @submit.prevent="submitReview"
      >
        <div class="air-form-row">
          <label class="air-form-label" for="air-review-state">Decision</label>
          <select
            id="air-review-state"
            v-model="selectedReviewState"
            class="air-select"
            data-testid="review-state-select"
            required
          >
            <option value="approved">Approve for internal use</option>
            <option value="rejected">Reject / block</option>
            <option value="changes_requested">Request changes</option>
            <option value="flagged">Flag (unsafe / unsupported claim)</option>
          </select>
        </div>

        <div class="air-form-row">
          <label class="air-form-label" for="air-feedback-type">Feedback (optional)</label>
          <select
            id="air-feedback-type"
            v-model="selectedFeedbackType"
            class="air-select"
            data-testid="feedback-type-select"
          >
            <option value="">— none —</option>
            <option value="useful">Useful</option>
            <option value="not_useful">Not useful</option>
            <option value="unsafe">Unsafe language</option>
            <option value="unsupported_claim">Unsupported claim</option>
          </select>
        </div>

        <div class="air-form-row">
          <label class="air-form-label" for="air-review-note">Note (optional)</label>
          <textarea
            id="air-review-note"
            v-model="reviewNote"
            class="air-textarea"
            data-testid="review-note-textarea"
            maxlength="2000"
            rows="3"
            placeholder="Add context, requested changes, or reviewer notes…"
          />
        </div>

        <div class="air-form-buttons">
          <BaseButton
            type="submit"
            variant="primary"
            size="sm"
            :disabled="submitting"
            data-testid="submit-review-btn"
          >
            {{ submitting ? 'Submitting…' : 'Submit review' }}
          </BaseButton>
          <BaseButton
            type="button"
            variant="ghost"
            size="sm"
            data-testid="cancel-review-btn"
            @click="cancelReview"
          >
            Cancel
          </BaseButton>
        </div>
      </form>
    </div>
  </BaseCard>
</template>

<style scoped>
.air-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.air-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.air-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.air-title {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.air-advisory-badge {
  flex-shrink: 0;
}

.air-state-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.air-review-count {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.air-skeleton {
  display: inline-block;
  border-radius: var(--radius-full);
  background: var(--color-border);
  animation: air-shimmer 1.4s infinite linear;
}

.air-skeleton--badge {
  width: 5rem;
  height: 1.2rem;
}

@keyframes air-shimmer {
  0% { opacity: 1; }
  50% { opacity: 0.4; }
  100% { opacity: 1; }
}

.air-advisory-notice {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-style: italic;
}

.air-explanation {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text);
  line-height: var(--leading-relaxed);
}

.air-confidence {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
}

.air-confidence-value {
  font-weight: var(--font-medium);
  color: var(--color-text);
}

.air-meta-label {
  margin: 0 0 var(--space-1);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.air-limitations {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.air-limitations-list {
  margin: 0;
  padding-left: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.air-limitations-list li {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.air-sources {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.air-sources-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.air-source-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.air-source-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.air-latest-note {
  padding: var(--space-2);
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  border-left: 2px solid var(--color-border);
}

.air-note-text {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text);
  white-space: pre-wrap;
}

.air-success {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-success, #22c55e);
  font-weight: var(--font-medium);
}

.air-error {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-danger, #ef4444);
  font-weight: var(--font-medium);
}

.air-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.air-review-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.air-form-row {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.air-form-label {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
}

.air-select,
.air-textarea {
  font-size: var(--text-xs);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-2);
  background: var(--color-surface);
  color: var(--color-text);
  width: 100%;
}

.air-select:focus,
.air-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
}

.air-textarea {
  resize: vertical;
  min-height: 4rem;
  font-family: inherit;
}

.air-form-buttons {
  display: flex;
  gap: var(--space-2);
}
</style>

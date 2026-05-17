<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import BaseBadge from './BaseBadge.vue';
import BaseButton from './BaseButton.vue';
import BaseCard from './BaseCard.vue';

import type { ApprovalState, EvidenceRef } from '@/services/playerDevelopmentApi';

interface Props {
  planId: string;
  playerProfileId: string;
  sessionTitle?: string | null;
  sessionId: string;
  jobId: string;
  analysisMode?: string | null;
  approvalState: ApprovalState;
  coachApproved: boolean;
  evidenceRefs?: EvidenceRef[];
  confidenceScore?: number | null;
  limitations?: string[];
  recommendationText?: string | null;
  focusAreas?: string[];
  suggestedDrills?: string[];
  evidenceStatusText?: string | null;
  reviewLoading?: boolean;
  reviewError?: string | null;
  reviewSuccess?: string | null;
  reviewerNotes?: string | null;
  reviewedByUserId?: string | null;
  reviewedAt?: string | null;
  canReview?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  sessionTitle: null,
  analysisMode: null,
  evidenceRefs: () => [],
  confidenceScore: null,
  limitations: () => [],
  recommendationText: null,
  focusAreas: () => [],
  suggestedDrills: () => [],
  evidenceStatusText: null,
  reviewLoading: false,
  reviewError: null,
  reviewSuccess: null,
  reviewerNotes: null,
  reviewedByUserId: null,
  reviewedAt: null,
  canReview: false,
});

const emit = defineEmits<{
  (e: 'approve', notes: string): void;
  (e: 'reject', notes: string): void;
  (e: 'request-changes', notes: string): void;
}>();

const reviewNotesDraft = ref(props.reviewerNotes ?? '');

watch(
  () => props.reviewerNotes,
  (value) => {
    if (value && !reviewNotesDraft.value.trim()) {
      reviewNotesDraft.value = value;
    }
  },
);

const confidencePercent = computed(() => {
  if (props.confidenceScore == null) return null;
  return Math.round(props.confidenceScore * 100);
});

const approvalStateLabel = computed(() => {
  switch (props.approvalState) {
    case 'approved':
      return 'Approved';
    case 'rejected':
      return 'Rejected';
    case 'changes_requested':
      return 'Changes requested';
    case 'pending_review':
      return 'Pending review';
    case 'not_required':
      return 'No review required';
    default:
      return props.approvalState;
  }
});

const approvalVariant = computed<'success' | 'warning' | 'danger' | 'neutral' | 'primary'>(() => {
  switch (props.approvalState) {
    case 'approved':
      return 'success';
    case 'rejected':
      return 'danger';
    case 'changes_requested':
      return 'warning';
    case 'pending_review':
      return 'primary';
    default:
      return 'neutral';
  }
});

const approvalVisibilityMessage = computed(() =>
  props.coachApproved
    ? 'Coach approved. This recommendation can appear on player-facing surfaces that respect the approval gate.'
    : 'Coach approval controls player-facing visibility. Until approved, this recommendation remains internal/advisory only.',
);

const formattedReviewedAt = computed(() => {
  if (!props.reviewedAt) return null;
  try {
    return new Date(props.reviewedAt).toLocaleString();
  } catch {
    return props.reviewedAt;
  }
});

function emitDecision(eventName: 'approve' | 'reject' | 'request-changes') {
  const notes = reviewNotesDraft.value.trim();
  if (eventName === 'approve') {
    emit('approve', notes);
    return;
  }
  if (eventName === 'reject') {
    emit('reject', notes);
    return;
  }
  emit('request-changes', notes);
}
</script>

<template>
  <BaseCard padding="md" class="review-card" data-testid="coaching-skill-review-card">
    <div class="review-card__header">
      <div>
        <h4 class="review-card__title">Governed recommendation review</h4>
        <p class="review-card__subtitle">
          Plan {{ planId }} · Player {{ playerProfileId }}
        </p>
      </div>
      <BaseBadge :variant="approvalVariant" :uppercase="false" data-testid="review-approval-badge">
        {{ approvalStateLabel }}
      </BaseBadge>
    </div>

    <p class="review-card__notice" data-testid="review-visibility-notice">
      {{ approvalVisibilityMessage }}
    </p>

    <dl class="review-card__context" data-testid="review-context">
      <div>
        <dt>Video session</dt>
        <dd>{{ sessionTitle || sessionId }}</dd>
      </div>
      <div>
        <dt>Session ID</dt>
        <dd>{{ sessionId }}</dd>
      </div>
      <div>
        <dt>Analysis job</dt>
        <dd>{{ jobId }}</dd>
      </div>
      <div>
        <dt>Analysis mode</dt>
        <dd>{{ analysisMode || 'Not available yet' }}</dd>
      </div>
      <div v-if="evidenceStatusText">
        <dt>Evidence timing</dt>
        <dd>{{ evidenceStatusText }}</dd>
      </div>
      <div v-if="confidencePercent !== null">
        <dt>Confidence</dt>
        <dd>{{ confidencePercent }}%</dd>
      </div>
    </dl>

    <section v-if="recommendationText" class="review-card__section" data-testid="review-summary">
      <h5>Recommendation summary</h5>
      <p>{{ recommendationText }}</p>
    </section>

    <section v-if="focusAreas.length > 0" class="review-card__section" data-testid="review-focus-areas">
      <h5>Focus areas</h5>
      <ul>
        <li v-for="item in focusAreas" :key="item">{{ item }}</li>
      </ul>
    </section>

    <section
      v-if="suggestedDrills.length > 0"
      class="review-card__section"
      data-testid="review-suggested-drills"
    >
      <h5>Suggested drills</h5>
      <ul>
        <li v-for="item in suggestedDrills" :key="item">{{ item }}</li>
      </ul>
    </section>

    <section v-if="limitations.length > 0" class="review-card__section" data-testid="review-limitations">
      <h5>Limitations</h5>
      <ul>
        <li v-for="item in limitations" :key="item">{{ item }}</li>
      </ul>
    </section>

    <section v-if="evidenceRefs.length > 0" class="review-card__section" data-testid="review-evidence-refs">
      <h5>Evidence references</h5>
      <ul>
        <li v-for="ref in evidenceRefs" :key="`${ref.type}-${ref.id}`">{{ ref.label }}</li>
      </ul>
    </section>

    <section
      v-if="reviewedByUserId || formattedReviewedAt || reviewerNotes"
      class="review-card__section"
      data-testid="review-latest-review"
    >
      <h5>Latest review activity</h5>
      <p v-if="reviewedByUserId">Reviewer: {{ reviewedByUserId }}</p>
      <p v-if="formattedReviewedAt">Reviewed at: {{ formattedReviewedAt }}</p>
      <p v-if="reviewerNotes">Notes: {{ reviewerNotes }}</p>
    </section>

    <p v-if="reviewError" class="review-card__error" data-testid="review-error">
      {{ reviewError }}
    </p>
    <p v-else-if="reviewSuccess" class="review-card__success" data-testid="review-success">
      {{ reviewSuccess }}
    </p>

    <div v-if="canReview" class="review-card__controls" data-testid="review-controls">
      <label class="review-card__notes-label" for="coach-reviewer-notes">Reviewer notes</label>
      <textarea
        id="coach-reviewer-notes"
        v-model="reviewNotesDraft"
        rows="3"
        placeholder="Optional notes for the governed review decision"
      />

      <div class="review-card__actions">
        <BaseButton
          type="button"
          variant="secondary"
          :disabled="reviewLoading"
          @click="emitDecision('request-changes')"
        >
          Request changes
        </BaseButton>
        <BaseButton
          type="button"
          variant="danger"
          :disabled="reviewLoading"
          @click="emitDecision('reject')"
        >
          Reject
        </BaseButton>
        <BaseButton
          type="button"
          variant="primary"
          :disabled="reviewLoading"
          @click="emitDecision('approve')"
        >
          {{ reviewLoading ? 'Submitting…' : 'Approve for player-facing use' }}
        </BaseButton>
      </div>
    </div>
  </BaseCard>
</template>

<style scoped>
.review-card {
  border: 1px solid var(--color-border);
}

.review-card__header {
  display: flex;
  justify-content: space-between;
  gap: var(--space-sm, 0.5rem);
  align-items: flex-start;
}

.review-card__title {
  margin: 0;
  font-size: var(--text-md, 1rem);
}

.review-card__subtitle,
.review-card__notice,
.review-card__section p,
.review-card__section li,
.review-card__context dd {
  margin: 0;
  color: var(--color-muted);
  font-size: var(--text-sm, 0.875rem);
}

.review-card__subtitle {
  margin-top: var(--space-xs, 0.25rem);
}

.review-card__notice {
  margin-top: var(--space-sm, 0.5rem);
  padding: var(--space-sm, 0.5rem);
  background: var(--color-surface-alt);
  border-radius: var(--radius-sm, 0.25rem);
}

.review-card__context {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-sm, 0.5rem);
  margin: var(--space-md, 1rem) 0;
}

.review-card__context dt,
.review-card__section h5,
.review-card__notes-label {
  margin: 0 0 var(--space-xs, 0.25rem);
  font-size: var(--text-xs, 0.75rem);
  font-weight: 600;
  color: var(--color-on-surface);
}

.review-card__context dd {
  word-break: break-word;
}

.review-card__section + .review-card__section {
  margin-top: var(--space-sm, 0.5rem);
}

.review-card__section ul {
  margin: 0;
  padding-left: 1rem;
}

.review-card__controls {
  margin-top: var(--space-md, 1rem);
}

.review-card__controls textarea {
  width: 100%;
  min-height: 5rem;
  padding: var(--space-sm, 0.5rem);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm, 0.25rem);
  background: var(--color-surface);
  color: var(--color-on-surface);
}

.review-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm, 0.5rem);
  margin-top: var(--space-sm, 0.5rem);
}

.review-card__error,
.review-card__success {
  margin: var(--space-sm, 0.5rem) 0 0;
  font-size: var(--text-sm, 0.875rem);
}

.review-card__error {
  color: var(--color-error);
}

.review-card__success {
  color: var(--color-success, #1f7a1f);
}
</style>

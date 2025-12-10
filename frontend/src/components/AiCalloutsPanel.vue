<script setup lang="ts">
import { computed } from "vue"

import BaseBadge from "./BaseBadge.vue"
import BaseButton from "./BaseButton.vue"
import BaseCard from "./BaseCard.vue"

export type CalloutSeverity = "info" | "positive" | "warning" | "critical"

export interface AiCallout {
  id: string
  title: string
  body: string
  category?: string
  severity?: CalloutSeverity
  scope?: string
  /** Optional: the phase ID from backend */
  targetPhaseId?: string
  /** Optional: explicit DOM id to scroll to */
  targetDomId?: string
  /** Optional: group/innings ID to expand/select before scrolling (e.g. innings index) */
  targetGroupId?: number
}

interface Props {
  title?: string
  description?: string
  callouts: AiCallout[]
  loading?: boolean
  maxItems?: number
  dense?: boolean
  showViewAllButton?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: "AI Callouts",
  description: "Key insights Cricksy AI thinks you should know.",
  loading: false,
  maxItems: 5,
  dense: false,
  showViewAllButton: false,
})

const emit = defineEmits<{
  (e: "select", callout: AiCallout): void
  (e: "viewAll"): void
}>()

const limitedCallouts = computed(() => {
  if (!props.callouts) return []
  if (!props.maxItems || props.callouts.length <= props.maxItems) {
    return props.callouts
  }
  return props.callouts.slice(0, props.maxItems)
})

const isEmpty = computed(
  () => !props.loading && (!props.callouts || props.callouts.length === 0)
)

function severityToVariant(
  severity?: CalloutSeverity
): "success" | "warning" | "danger" | "neutral" {
  switch (severity) {
    case "positive":
      return "success"
    case "warning":
      return "warning"
    case "critical":
      return "danger"
    default:
      return "neutral"
  }
}

function handleCalloutClick(callout: AiCallout) {
  emit("select", callout)
}

function handleViewAll() {
  emit("viewAll")
}
</script>

<template>
  <BaseCard padding="md" class="ai-callouts-panel">
    <!-- Header -->
    <header class="ai-callouts-header">
      <div>
        <h2 class="ai-callouts-title">
          {{ title }}
        </h2>
        <p class="ai-callouts-description">
          {{ description }}
        </p>
      </div>
    </header>

    <!-- Loading skeleton -->
    <div v-if="loading" class="ai-callouts-skeleton">
      <div v-for="n in 3" :key="n" class="skeleton-item">
        <div class="skeleton-line skeleton-line--title" />
        <div class="skeleton-line skeleton-line--body" />
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="isEmpty" class="ai-callouts-empty">
      <p>No AI callouts yet.</p>
      <p class="ai-callouts-empty-hint">
        Once enough data is available, Cricksy AI will surface key insights here.
      </p>
    </div>

    <!-- Callouts list -->
    <ul v-else class="ai-callouts-list" :data-dense="dense">
      <li
        v-for="callout in limitedCallouts"
        :key="callout.id"
        class="ai-callout-item"
      >
        <button
          type="button"
          class="ai-callout-row"
          @click="handleCalloutClick(callout)"
        >
          <div class="ai-callout-main">
            <div class="ai-callout-title-row">
              <h3 class="ai-callout-title">
                {{ callout.title }}
              </h3>

              <BaseBadge
                v-if="callout.severity"
                :variant="severityToVariant(callout.severity)"
                :uppercase="false"
              >
                {{ callout.severity }}
              </BaseBadge>
            </div>

            <p class="ai-callout-body">
              {{ callout.body }}
            </p>
          </div>

          <div class="ai-callout-meta">
            <BaseBadge v-if="callout.category" variant="neutral" :uppercase="false">
              {{ callout.category }}
            </BaseBadge>
            <span v-if="callout.scope" class="ai-callout-scope">
              {{ callout.scope }}
            </span>
          </div>
        </button>
      </li>
    </ul>

    <!-- View all button -->
    <div v-if="showViewAllButton && !loading && !isEmpty" class="ai-callouts-footer">
      <BaseButton
        variant="ghost"
        size="sm"
        class="ai-callouts-view-all"
        @click="handleViewAll"
      >
        View all insights
      </BaseButton>
    </div>
  </BaseCard>
</template>

<style scoped>
.ai-callouts-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.ai-callouts-header {
  margin-bottom: var(--space-1);
}

.ai-callouts-title {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.ai-callouts-description {
  margin: var(--space-1) 0 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.ai-callouts-skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.skeleton-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.skeleton-line {
  height: 0.7rem;
  border-radius: var(--radius-full);
  background: linear-gradient(
    90deg,
    var(--color-surface-hover),
    var(--color-border),
    var(--color-surface-hover)
  );
  background-size: 200% 100%;
  animation: ai-callouts-shimmer 1.4s infinite linear;
}

.skeleton-line--title {
  width: 80%;
}

.skeleton-line--body {
  width: 95%;
}

@keyframes ai-callouts-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.ai-callouts-empty {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  padding: var(--space-3);
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  border: 1px dashed var(--color-border);
}

.ai-callouts-empty p {
  margin: 0;
}

.ai-callouts-empty-hint {
  margin-top: var(--space-1) !important;
  color: var(--color-text-muted);
  opacity: 0.8;
}

.ai-callouts-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.ai-callout-item {
  padding: var(--space-1);
  border-radius: var(--radius-md);
  background: var(--color-surface-alt);
}

.ai-callout-row {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: 100%;
  border: none;
  padding: var(--space-2);
  background: transparent;
  text-align: left;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background-color 140ms ease-out;
}

.ai-callout-row:hover,
.ai-callout-row:focus-visible {
  background: var(--color-surface-hover);
  outline: none;
}

.ai-callout-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.ai-callout-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-2);
}

.ai-callout-title {
  margin: 0;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.ai-callout-body {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  line-height: var(--leading-relaxed);
}

.ai-callout-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  font-size: 0.7rem;
  color: var(--color-text-muted);
}

.ai-callout-scope {
  font-size: 0.7rem;
}

.ai-callouts-footer {
  margin-top: var(--space-2);
  display: flex;
  justify-content: flex-start;
}

.ai-callouts-view-all {
  font-size: var(--text-xs);
}

/* Dense mode */
.ai-callouts-list[data-dense="true"] .ai-callout-item {
  padding: var(--space-1);
}

.ai-callouts-list[data-dense="true"] .ai-callout-title {
  font-size: 0.7rem;
}

.ai-callouts-list[data-dense="true"] .ai-callout-body {
  font-size: 0.7rem;
}
</style>

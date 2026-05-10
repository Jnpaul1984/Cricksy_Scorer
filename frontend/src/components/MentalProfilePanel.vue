<template>
  <div class="mental-profile-panel">
    <!-- Coaching disclaimer -->
    <div class="coaching-disclaimer">
      <span class="disclaimer-icon">ℹ️</span>
      <span>This is a coaching development tool, not a medical or psychological diagnosis.</span>
    </div>

    <!-- Latest Summary Section -->
    <section class="profile-summary-section">
      <div class="section-header">
        <h3 class="section-title">🧠 Latest Mental Profile</h3>
        <BaseButton
          variant="ghost"
          size="sm"
          :disabled="summaryLoading"
          @click="loadLatestProfile"
        >
          <span v-if="summaryLoading">Loading…</span>
          <span v-else>↻ Refresh</span>
        </BaseButton>
      </div>

      <!-- Loading -->
      <div v-if="summaryLoading" class="loading-state" aria-busy="true">
        <div class="skeleton-line" />
        <div class="skeleton-line" />
        <div class="skeleton-line short" />
      </div>

      <!-- Error -->
      <p v-else-if="summaryError" class="error-text">
        {{ summaryError }}
      </p>

      <!-- No data yet -->
      <div v-else-if="!latestProfile" class="empty-state">
        <p>No mental profile recorded for this player yet.</p>
        <p class="empty-hint">Use the questionnaire below to add the first assessment.</p>
      </div>

      <!-- Profile data -->
      <div v-else class="profile-data">
        <div class="overall-score-row">
          <span class="score-label">Overall coaching score</span>
          <span class="overall-score">{{ latestProfile.overall_average_score.toFixed(1) }} / 5</span>
          <span class="score-date">{{ formatDate(latestProfile.created_at) }}</span>
        </div>

        <p class="overall-summary">{{ latestProfile.overall_summary }}</p>

        <!-- Category scores -->
        <div v-if="latestProfile.category_scores.length" class="category-scores">
          <h4 class="subsection-title">Category Scores</h4>
          <div class="scores-grid">
            <div
              v-for="cs in latestProfile.category_scores"
              :key="cs.category"
              class="score-card"
            >
              <span class="score-card-label">{{ formatCategory(cs.category) }}</span>
              <span class="score-card-value">{{ cs.average_score.toFixed(1) }}</span>
              <div class="score-bar-track">
                <div
                  class="score-bar-fill"
                  :style="{ width: `${(cs.average_score / 5) * 100}%` }"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Strengths -->
        <div v-if="latestProfile.strengths.length" class="strengths-block">
          <h4 class="subsection-title">💪 Coaching Strengths</h4>
          <ul class="insight-list">
            <li v-for="(s, idx) in latestProfile.strengths" :key="idx">{{ s }}</li>
          </ul>
        </div>

        <!-- Development areas -->
        <div v-if="latestProfile.development_areas.length" class="development-block">
          <h4 class="subsection-title">🎯 Growth Opportunities</h4>
          <ul class="insight-list">
            <li v-for="(d, idx) in latestProfile.development_areas" :key="idx">{{ d }}</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- Questionnaire Form Section -->
    <section class="questionnaire-section">
      <div class="section-header">
        <h3 class="section-title">📋 New Assessment</h3>
        <BaseButton
          v-if="!showForm"
          variant="primary"
          size="sm"
          :disabled="templateLoading"
          @click="openForm"
        >
          {{ templateLoading ? 'Loading…' : 'Launch Questionnaire' }}
        </BaseButton>
        <BaseButton
          v-else
          variant="ghost"
          size="sm"
          @click="closeForm"
        >
          Cancel
        </BaseButton>
      </div>

      <p v-if="templateError" class="error-text">{{ templateError }}</p>

      <!-- Questionnaire form -->
      <div v-if="showForm && template" class="questionnaire-form">
        <form @submit.prevent="handleSubmit">
          <div
            v-for="cat in template.categories"
            :key="cat.category"
            class="category-group"
          >
            <h4 class="category-heading">{{ formatCategory(cat.category) }}</h4>
            <div
              v-for="q in cat.questions"
              :key="q.id"
              class="question-item"
            >
              <label :for="`q-${q.id}`" class="question-label">{{ q.question_text }}</label>
              <div class="score-selector" role="group" :aria-label="`Score for question ${q.id}, 1 to 5`">
                <button
                  v-for="n in 5"
                  :key="n"
                  type="button"
                  class="score-btn"
                  :class="{ active: answers[q.id] === n }"
                  :aria-pressed="answers[q.id] === n"
                  @click="answers[q.id] = n"
                >
                  {{ n }}
                </button>
              </div>
              <span v-if="submitAttempted && !answers[q.id]" class="field-error">
                Please select a score (1–5).
              </span>
            </div>
          </div>

          <div class="form-actions">
            <p v-if="submitError" class="error-text">{{ submitError }}</p>
            <BaseButton
              type="submit"
              variant="primary"
              :disabled="isSubmitting"
            >
              {{ isSubmitting ? 'Submitting…' : 'Submit Assessment' }}
            </BaseButton>
          </div>
        </form>
      </div>
    </section>

    <!-- Response History Section -->
    <section class="history-section">
      <div class="section-header">
        <h3 class="section-title">📅 Assessment History</h3>
      </div>

      <div v-if="historyLoading" class="loading-state" aria-busy="true">
        <div class="skeleton-line" />
        <div class="skeleton-line short" />
      </div>

      <p v-else-if="historyError" class="error-text">{{ historyError }}</p>

      <div v-else-if="history.length === 0" class="empty-state">
        <p>No assessment history yet.</p>
      </div>

      <ul v-else class="history-list">
        <li
          v-for="item in history"
          :key="item.session_id"
          class="history-item"
        >
          <div class="history-item-row">
            <span class="history-date">{{ formatDate(item.created_at) }}</span>
            <span class="history-score">{{ item.overall_average_score.toFixed(1) }} / 5</span>
          </div>
          <p class="history-summary">{{ item.overall_summary }}</p>
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

import { BaseButton } from '@/components'
import {
  getMentalQuestionnaireTemplate,
  getLatestMentalProfile,
  getMentalResponseHistory,
  submitMentalQuestionnaire,
} from '@/services/mentalQuestionnaireApi'
import type { MentalProfileSummary, MentalQuestionnaireTemplate } from '@/types/mentalQuestionnaire'

const props = defineProps<{
  playerId: string
}>()

/** Extract a human-readable message from an unknown API error. */
function apiErrorMessage(err: unknown): string {
  if (!err) return 'An unknown error occurred.'
  if (typeof err === 'string') return err
  const e = err as Record<string, unknown>
  if (typeof e.message === 'string' && e.message) return e.message
  return 'An unexpected error occurred.'
}

/** Return the HTTP status code embedded by apiRequest, or undefined. */
function apiErrorStatus(err: unknown): number | undefined {
  if (!err || typeof err !== 'object') return undefined
  return (err as Record<string, unknown>).status as number | undefined
}

// ── Latest profile ─────────────────────────────────────────────────────────
const summaryLoading = ref(false)
const summaryError = ref<string | null>(null)
const latestProfile = ref<MentalProfileSummary | null>(null)

async function loadLatestProfile() {
  summaryLoading.value = true
  summaryError.value = null
  try {
    latestProfile.value = await getLatestMentalProfile(props.playerId)
  } catch (err: unknown) {
    if (apiErrorStatus(err) === 404) {
      // No profile yet — not an error condition
      latestProfile.value = null
    } else {
      summaryError.value = apiErrorMessage(err)
    }
  } finally {
    summaryLoading.value = false
  }
}

// ── Template ───────────────────────────────────────────────────────────────
const templateLoading = ref(false)
const templateError = ref<string | null>(null)
const template = ref<MentalQuestionnaireTemplate | null>(null)
const showForm = ref(false)

async function openForm() {
  if (template.value) {
    showForm.value = true
    return
  }
  templateLoading.value = true
  templateError.value = null
  try {
    template.value = await getMentalQuestionnaireTemplate()
    showForm.value = true
  } catch (err: unknown) {
    templateError.value = apiErrorMessage(err)
  } finally {
    templateLoading.value = false
  }
}

function closeForm() {
  showForm.value = false
  submitAttempted.value = false
  submitError.value = null
  answers.value = {}
}

// ── Questionnaire submission ────────────────────────────────────────────────
const answers = ref<Record<number, number>>({})
const isSubmitting = ref(false)
const submitError = ref<string | null>(null)
const submitAttempted = ref(false)

async function handleSubmit() {
  submitAttempted.value = true

  // Validate: every question must have an answer
  if (!template.value) return
  const allQuestionIds = template.value.categories.flatMap((c) => c.questions.map((q) => q.id))
  const allAnswered = allQuestionIds.every((id) => answers.value[id] !== undefined)
  if (!allAnswered) return

  isSubmitting.value = true
  submitError.value = null
  try {
    const payload = allQuestionIds.map((id) => ({ question_id: id, score: answers.value[id] }))
    const updated = await submitMentalQuestionnaire(props.playerId, payload)
    latestProfile.value = updated
    // Refresh history
    await loadHistory()
    closeForm()
  } catch (err: unknown) {
    submitError.value = apiErrorMessage(err)
  } finally {
    isSubmitting.value = false
  }
}

// ── History ─────────────────────────────────────────────────────────────────
const historyLoading = ref(false)
const historyError = ref<string | null>(null)
const history = ref<MentalProfileSummary[]>([])

async function loadHistory() {
  historyLoading.value = true
  historyError.value = null
  try {
    history.value = await getMentalResponseHistory(props.playerId)
  } catch (err: unknown) {
    historyError.value = apiErrorMessage(err)
  } finally {
    historyLoading.value = false
  }
}

// ── Helpers ─────────────────────────────────────────────────────────────────
// Category display labels aligned with backend MentalQuestionnaireCategory enum
// (backend/sql_app/models.py). Update here if the backend adds new categories.
const CATEGORY_LABELS: Record<string, string> = {
  mental_toughness: 'Mental Toughness',
  pressure_handling: 'Pressure Handling',
  game_awareness: 'Game Awareness / Cricket IQ',
  training_habits: 'Training Habits & Discipline',
}

function formatCategory(raw: string): string {
  return CATEGORY_LABELS[raw] ?? raw.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return iso
  }
}

// ── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([loadLatestProfile(), loadHistory()])
})
</script>

<style scoped>
.mental-profile-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg, 1.5rem);
}

/* Disclaimer */
.coaching-disclaimer {
  display: flex;
  align-items: flex-start;
  gap: var(--space-xs, 0.25rem);
  padding: var(--space-sm, 0.5rem) var(--space-md, 1rem);
  background: var(--color-surface-alt, #f5f5f5);
  border-left: 3px solid var(--color-primary, #1976d2);
  border-radius: var(--radius-sm, 4px);
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-muted, #666);
}

.disclaimer-icon {
  flex-shrink: 0;
  margin-top: 1px;
}

/* Section layout */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-md, 1rem);
}

.section-title {
  margin: 0;
  font-size: var(--text-md, 1rem);
  font-weight: 600;
}

/* Loading skeleton */
.loading-state {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 0.5rem);
}

.skeleton-line {
  height: 1rem;
  background: linear-gradient(90deg, var(--color-border, #e0e0e0) 25%, var(--color-surface-alt, #f5f5f5) 50%, var(--color-border, #e0e0e0) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-sm, 4px);
}

.skeleton-line.short {
  width: 60%;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Error / empty */
.error-text {
  color: var(--color-error, #d32f2f);
  font-size: var(--text-sm, 0.875rem);
  margin: 0;
}

.empty-state {
  color: var(--color-muted, #666);
  font-size: var(--text-sm, 0.875rem);
}

.empty-state p {
  margin: 0 0 var(--space-xs, 0.25rem);
}

.empty-hint {
  font-style: italic;
}

/* Overall score row */
.overall-score-row {
  display: flex;
  align-items: center;
  gap: var(--space-md, 1rem);
  margin-bottom: var(--space-sm, 0.5rem);
  flex-wrap: wrap;
}

.score-label {
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-muted, #666);
}

.overall-score {
  font-size: var(--text-xl, 1.5rem);
  font-weight: 700;
  color: var(--color-primary, #1976d2);
}

.score-date {
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-muted, #666);
  margin-left: auto;
}

.overall-summary {
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text, #333);
  margin: 0 0 var(--space-md, 1rem);
  line-height: 1.5;
}

/* Category scores */
.subsection-title {
  font-size: var(--text-sm, 0.875rem);
  font-weight: 600;
  margin: 0 0 var(--space-sm, 0.5rem);
  color: var(--color-text, #333);
}

.scores-grid {
  display: grid;
  gap: var(--space-sm, 0.5rem);
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  margin-bottom: var(--space-md, 1rem);
}

.score-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs, 0.25rem);
  padding: var(--space-sm, 0.5rem) var(--space-md, 1rem);
  background: var(--color-surface-alt, #f5f5f5);
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-border, #e0e0e0);
}

.score-card-label {
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-muted, #666);
}

.score-card-value {
  font-size: var(--text-lg, 1.25rem);
  font-weight: 700;
  color: var(--color-primary, #1976d2);
}

.score-bar-track {
  height: 4px;
  background: var(--color-border, #e0e0e0);
  border-radius: 2px;
  overflow: hidden;
}

.score-bar-fill {
  height: 100%;
  background: var(--color-primary, #1976d2);
  border-radius: 2px;
  transition: width 0.4s ease;
}

/* Strengths / development */
.strengths-block,
.development-block {
  margin-bottom: var(--space-md, 1rem);
}

.insight-list {
  margin: 0;
  padding-left: var(--space-md, 1rem);
  display: flex;
  flex-direction: column;
  gap: var(--space-xs, 0.25rem);
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text, #333);
}

/* Questionnaire form */
.questionnaire-form {
  padding-top: var(--space-sm, 0.5rem);
}

.category-group {
  margin-bottom: var(--space-lg, 1.5rem);
}

.category-heading {
  font-size: var(--text-sm, 0.875rem);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-muted, #666);
  margin: 0 0 var(--space-sm, 0.5rem);
  padding-bottom: var(--space-xs, 0.25rem);
  border-bottom: 1px solid var(--color-border, #e0e0e0);
}

.question-item {
  margin-bottom: var(--space-md, 1rem);
}

.question-label {
  display: block;
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text, #333);
  margin-bottom: var(--space-xs, 0.25rem);
  line-height: 1.4;
}

.score-selector {
  display: flex;
  gap: var(--space-xs, 0.25rem);
  flex-wrap: wrap;
}

.score-btn {
  width: 2.25rem;
  height: 2.25rem;
  border: 1px solid var(--color-border, #e0e0e0);
  border-radius: var(--radius-sm, 4px);
  background: var(--color-surface, #fff);
  font-size: var(--text-sm, 0.875rem);
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
  color: var(--color-text, #333);
}

.score-btn:hover {
  border-color: var(--color-primary, #1976d2);
  background: var(--color-surface-alt, #f5f5f5);
}

.score-btn.active {
  background: var(--color-primary, #1976d2);
  border-color: var(--color-primary, #1976d2);
  color: #fff;
}

.field-error {
  display: block;
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-error, #d32f2f);
  margin-top: var(--space-xs, 0.25rem);
}

.form-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-sm, 0.5rem);
  padding-top: var(--space-sm, 0.5rem);
}

/* History */
.history-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 0.5rem);
}

.history-item {
  padding: var(--space-sm, 0.5rem) var(--space-md, 1rem);
  background: var(--color-surface-alt, #f5f5f5);
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-border, #e0e0e0);
}

.history-item-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-xs, 0.25rem);
}

.history-date {
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-muted, #666);
}

.history-score {
  font-weight: 700;
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-primary, #1976d2);
}

.history-summary {
  margin: 0;
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text, #333);
  line-height: 1.4;
}
</style>

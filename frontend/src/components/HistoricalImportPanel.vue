<template>
  <div class="hip-panel">
    <!-- STEP: SELECT FILE -->
    <div v-if="step === 'select'" class="hip-step">
      <div class="hip-intro">
        <h3 class="hip-title">Import Historical JSON</h3>
        <p class="hip-desc">
          Upload a <code>.json</code> match file (Cricksy fixture or Cricsheet format).
          A dry-run preview will be shown before any data is saved.
        </p>
      </div>

      <div
        class="hip-dropzone"
        :class="{ 'hip-dropzone--drag': isDragging }"
        role="button"
        tabindex="0"
        aria-label="Select JSON file to upload"
        @click="triggerFileInput"
        @keydown.enter.prevent="triggerFileInput"
        @keydown.space.prevent="triggerFileInput"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop"
      >
        <span class="hip-dropzone-icon" aria-hidden="true">📂</span>
        <span class="hip-dropzone-text">
          Drop a <strong>.json</strong> file here, or click to browse
        </span>
        <input
          ref="fileInputRef"
          type="file"
          accept=".json,application/json"
          class="hip-file-input"
          aria-hidden="true"
          @change="onFileChange"
        />
      </div>

      <p v-if="fileSelectError" class="hip-error" role="alert">{{ fileSelectError }}</p>
    </div>

    <!-- STEP: PREVIEW (dry-run results) -->
    <div v-else-if="step === 'preview'" class="hip-step">
      <div class="hip-step-header">
        <h3 class="hip-title">Dry-Run Preview</h3>
        <button class="hip-link-btn" type="button" @click="resetToSelect">← Start over</button>
      </div>

      <!-- Loading state -->
      <div v-if="loading" class="hip-loading" role="status" aria-live="polite">
        <span>Running preview…</span>
      </div>

      <!-- Error: unsupported/invalid JSON -->
      <div v-else-if="preview && preview.status !== 'valid'" class="hip-preview-error" role="alert">
        <p class="hip-preview-status-label">
          ⚠️ {{ preview.status === 'invalid' ? 'Invalid JSON' : 'Unsupported format' }}
        </p>
        <p class="hip-preview-status-detail">
          This file cannot be imported. Review the errors below and upload a supported match JSON.
        </p>
        <ul v-if="preview.errors.length" class="hip-issue-list">
          <li v-for="(err, i) in preview.errors" :key="i" class="hip-issue hip-issue--error">
            <code>{{ err.code }}</code> {{ err.message }}
          </li>
        </ul>
        <button class="hip-btn hip-btn--ghost" type="button" @click="resetToSelect">
          Upload a different file
        </button>
      </div>

      <!-- Valid preview -->
      <div v-else-if="preview" class="hip-preview-valid">
        <!-- Format + counts summary -->
        <div class="hip-preview-summary">
          <div class="hip-preview-row">
            <span class="hip-preview-label">File</span>
            <span class="hip-preview-value">{{ selectedFile?.name }}</span>
          </div>
          <div class="hip-preview-row">
            <span class="hip-preview-label">Detected format</span>
            <span class="hip-preview-value">{{ preview.detected_format }}</span>
          </div>
          <div class="hip-preview-row">
            <span class="hip-preview-label">Teams</span>
            <span class="hip-preview-value">
              {{ preview.teams_preview.length ? preview.teams_preview.join(' vs ') : '—' }}
            </span>
          </div>
          <div class="hip-preview-row">
            <span class="hip-preview-label">Match type</span>
            <span class="hip-preview-value">{{ preview.metadata_preview.match_type || '—' }}</span>
          </div>
          <div v-if="preview.metadata_preview.date" class="hip-preview-row">
            <span class="hip-preview-label">Date</span>
            <span class="hip-preview-value">{{ preview.metadata_preview.date }}</span>
          </div>
          <div v-if="preview.metadata_preview.venue" class="hip-preview-row">
            <span class="hip-preview-label">Venue</span>
            <span class="hip-preview-value">{{ preview.metadata_preview.venue }}</span>
          </div>
          <div class="hip-preview-row">
            <span class="hip-preview-label">Innings</span>
            <span class="hip-preview-value">{{ preview.innings_count }}</span>
          </div>
          <div class="hip-preview-row">
            <span class="hip-preview-label">Deliveries</span>
            <span class="hip-preview-value">{{ preview.delivery_count }}</span>
          </div>
        </div>

        <!-- Innings breakdown -->
        <div v-if="preview.innings_preview.length" class="hip-innings">
          <h4 class="hip-section-title">Innings breakdown</h4>
          <table class="hip-table">
            <thead>
              <tr>
                <th>Inning</th>
                <th>Team</th>
                <th>Deliveries</th>
                <th>Runs</th>
                <th>Wickets</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="inns in preview.innings_preview" :key="inns.inning_no">
                <td>{{ inns.inning_no }}</td>
                <td>{{ inns.team || '—' }}</td>
                <td>{{ inns.deliveries }}</td>
                <td>{{ inns.runs ?? '—' }}</td>
                <td>{{ inns.wickets ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Duplicate detection -->
        <div class="hip-dup-result" :class="dupResultClass" role="alert">
          <span class="hip-dup-icon" aria-hidden="true">{{ dupResultIcon }}</span>
          <span>{{ preview.duplicate_detection.message }}</span>
          <span v-if="preview.duplicate_detection.duplicate_batch_id" class="hip-dup-batch">
            Existing batch: <code>{{ preview.duplicate_detection.duplicate_batch_id }}</code>
          </span>
        </div>

        <!-- Warnings -->
        <div v-if="preview.warnings.length" class="hip-issues">
          <h4 class="hip-section-title">Warnings ({{ preview.warnings.length }})</h4>
          <ul class="hip-issue-list">
            <li v-for="(w, i) in preview.warnings" :key="i" class="hip-issue hip-issue--warning">
              <code>{{ w.code }}</code> {{ w.message }}
            </li>
          </ul>
        </div>

        <!-- Actions -->
        <div class="hip-actions">
          <button
            class="hip-btn hip-btn--primary"
            type="button"
            :disabled="loading"
            @click="recordPreview"
          >
            Save import record
          </button>
          <button class="hip-btn hip-btn--ghost" type="button" @click="resetToSelect">
            Cancel
          </button>
        </div>
        <p class="hip-action-hint">
          Saving creates a batch record without importing any match data.
        </p>
      </div>

      <!-- Error fetching preview -->
      <div v-else-if="error" class="hip-error" role="alert">
        <p>{{ error }}</p>
        <button class="hip-btn hip-btn--ghost" type="button" @click="resetToSelect">
          Try again
        </button>
      </div>
    </div>

    <!-- STEP: APPLY (confirm + run apply) -->
    <div v-else-if="step === 'apply'" class="hip-step">
      <div class="hip-step-header">
        <h3 class="hip-title">Apply Import</h3>
      </div>

      <div class="hip-confirm-box">
        <p class="hip-confirm-intro">
          Batch record saved.
          <span v-if="batchId"> ID: <code>{{ batchId }}</code></span>
        </p>
        <p class="hip-confirm-desc">
          The next step creates a historical match record in the database.
          No deliveries are imported yet. You can rollback after this step.
        </p>

        <div v-if="loading" class="hip-loading" role="status" aria-live="polite">
          <span>Applying…</span>
        </div>

        <div v-else-if="error" class="hip-error" role="alert">
          <p>{{ error }}</p>
        </div>

        <div v-if="!loading" class="hip-actions">
          <button
            class="hip-btn hip-btn--primary"
            type="button"
            @click="applyBatch"
          >
            Confirm: Create match record
          </button>
          <button class="hip-btn hip-btn--ghost" type="button" @click="resetToSelect">
            Cancel
          </button>
        </div>
        <p class="hip-action-hint">
          This creates a <em>historical</em> game row. It does not affect live scoring.
        </p>
      </div>
    </div>

    <!-- STEP: APPLY DELIVERIES (confirm + run apply-deliveries) -->
    <div v-else-if="step === 'apply-deliveries'" class="hip-step">
      <div class="hip-step-header">
        <h3 class="hip-title">Import Ball-by-Ball Data</h3>
      </div>

      <div class="hip-confirm-box">
        <p class="hip-confirm-intro">
          Match record created.
          <span v-if="applyResult?.applied_game_id">
            Game ID: <code>{{ applyResult.applied_game_id }}</code>
          </span>
        </p>
        <p class="hip-confirm-desc">
          The next (optional) step imports ball-by-ball delivery data into the match record.
          The original JSON file will be re-validated (hash-checked) before any write.
        </p>

        <div v-if="loading" class="hip-loading" role="status" aria-live="polite">
          <span>Importing deliveries…</span>
        </div>

        <div v-else-if="error" class="hip-error" role="alert">
          <p>{{ error }}</p>
        </div>

        <div v-if="!loading" class="hip-actions">
          <button
            class="hip-btn hip-btn--primary"
            type="button"
            @click="applyDeliveries"
          >
            Confirm: Import deliveries
          </button>
          <button
            class="hip-btn hip-btn--ghost"
            type="button"
            @click="skipDeliveries"
          >
            Skip — finish without deliveries
          </button>
        </div>
        <p class="hip-action-hint">
          Skipping keeps metadata + innings totals only. Run <code>apply-deliveries</code> to unlock
          delivery rows, wickets, phase analytics, and CPL match-story visuals.
        </p>
      </div>
    </div>

    <!-- STEP: DONE -->
    <div v-else-if="step === 'done'" class="hip-step">
      <div class="hip-done">
        <span class="hip-done-icon" aria-hidden="true">✅</span>
        <h3 class="hip-title">Import complete</h3>

        <div class="hip-done-summary">
          <div v-if="applyResult?.applied_game_id" class="hip-done-row">
            <span class="hip-done-label">Game ID</span>
            <code class="hip-done-value">{{ applyResult.applied_game_id }}</code>
          </div>
          <div v-if="deliveriesResult" class="hip-done-row">
            <span class="hip-done-label">Deliveries imported</span>
            <span class="hip-done-value">{{ deliveriesResult.deliveries_imported }}</span>
          </div>
          <div v-else class="hip-done-row">
            <span class="hip-done-label">Deliveries</span>
            <span class="hip-done-value hip-done-value--muted">
              Skipped — metadata/innings only. Run apply-deliveries later to mark as delivery-complete.
            </span>
          </div>
          <div v-if="trainingStatus" class="hip-done-row">
            <span class="hip-done-label">Training eligible</span>
            <span
              class="hip-done-value"
              :class="trainingStatus.training_eligible ? 'hip-done-value--ok' : 'hip-done-value--muted'"
            >
              {{ trainingStatus.training_eligible ? 'Yes' : 'No' }}
              <span v-if="trainingStatus.exclusion_reason">
                ({{ trainingStatus.exclusion_reason }})
              </span>
            </span>
          </div>
          <div class="hip-done-row">
            <span class="hip-done-label">Raw JSON retained</span>
            <span class="hip-done-value hip-done-value--muted">
              No — deferred to Phase 5J
            </span>
          </div>
        </div>

        <p class="hip-done-hint">
          The imported match is now visible in the <strong>Matches</strong> tab
          with an <em>Imported</em> badge. Refresh the match list to see it.
        </p>

        <div class="hip-actions">
          <button
            class="hip-btn hip-btn--primary"
            type="button"
            @click="emit('import-done', applyResult?.applied_game_id ?? null)"
          >
            View in Matches tab
          </button>
          <button class="hip-btn hip-btn--ghost" type="button" @click="resetToSelect">
            Import another file
          </button>
        </div>
      </div>
    </div>

    <!-- Progress indicator -->
    <div v-if="step !== 'select'" class="hip-progress" aria-label="Import progress">
      <span
        v-for="s in STEPS"
        :key="s.key"
        class="hip-progress-dot"
        :class="{
          'hip-progress-dot--active': s.key === step,
          'hip-progress-dot--done': isStepDone(s.key),
        }"
        :title="s.label"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  historicalImportDryRun,
  historicalImportApply,
  historicalImportApplyDeliveries,
  historicalImportGetTrainingStatus,
  type HistoricalImportDryRunResponse,
  type HistoricalImportApplyResponse,
  type HistoricalImportApplyDeliveriesResponse,
  type HistoricalImportTrainingStatus,
} from '@/services/api'

// ---------------------------------------------------------------------------
// Emits
// ---------------------------------------------------------------------------

const emit = defineEmits<{
  /** Fired when import is fully complete; passes the applied_game_id or null. */
  (e: 'import-done', gameId: string | null): void
}>()

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ImportStep = 'select' | 'preview' | 'apply' | 'apply-deliveries' | 'done'

const STEPS: { key: ImportStep; label: string }[] = [
  { key: 'select', label: 'Select file' },
  { key: 'preview', label: 'Preview' },
  { key: 'apply', label: 'Apply' },
  { key: 'apply-deliveries', label: 'Import deliveries' },
  { key: 'done', label: 'Done' },
]

const STEP_ORDER: ImportStep[] = ['select', 'preview', 'apply', 'apply-deliveries', 'done']

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const step = ref<ImportStep>('select')
const loading = ref(false)
const error = ref<string | null>(null)

const selectedFile = ref<File | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const fileSelectError = ref<string | null>(null)

const preview = ref<HistoricalImportDryRunResponse | null>(null)
const batchId = ref<string | null>(null)
const applyResult = ref<HistoricalImportApplyResponse | null>(null)
const deliveriesResult = ref<HistoricalImportApplyDeliveriesResponse | null>(null)
const trainingStatus = ref<HistoricalImportTrainingStatus | null>(null)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

const dupResultClass = computed(() => {
  if (!preview.value) return ''
  return preview.value.duplicate_detection.probable_duplicate === 'likely_duplicate'
    ? 'hip-dup-result--warn'
    : 'hip-dup-result--ok'
})

const dupResultIcon = computed(() => {
  if (!preview.value) return ''
  return preview.value.duplicate_detection.probable_duplicate === 'likely_duplicate' ? '⚠️' : '✅'
})

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isStepDone(s: ImportStep): boolean {
  const cur = STEP_ORDER.indexOf(step.value)
  const idx = STEP_ORDER.indexOf(s)
  return idx < cur
}

function resetToSelect() {
  step.value = 'select'
  loading.value = false
  error.value = null
  selectedFile.value = null
  fileSelectError.value = null
  preview.value = null
  batchId.value = null
  applyResult.value = null
  deliveriesResult.value = null
  trainingStatus.value = null
  if (fileInputRef.value) fileInputRef.value.value = ''
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

function validateAndSetFile(file: File | null | undefined) {
  fileSelectError.value = null
  if (!file) return
  if (!file.name.endsWith('.json') && file.type !== 'application/json') {
    fileSelectError.value = 'Only .json files are supported.'
    return
  }
  selectedFile.value = file
  step.value = 'preview'
  runDryRun()
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  validateAndSetFile(input.files?.[0])
}

function onDrop(event: DragEvent) {
  isDragging.value = false
  validateAndSetFile(event.dataTransfer?.files[0])
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

async function runDryRun() {
  if (!selectedFile.value) return
  loading.value = true
  error.value = null
  preview.value = null
  try {
    preview.value = await historicalImportDryRun(selectedFile.value, false)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Dry-run preview failed'
  } finally {
    loading.value = false
  }
}

async function recordPreview() {
  if (!selectedFile.value) return
  loading.value = true
  error.value = null
  try {
    const result = await historicalImportDryRun(selectedFile.value, true)
    preview.value = result
    batchId.value = result.record_id ?? null
    step.value = 'apply'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to save import record'
  } finally {
    loading.value = false
  }
}

async function applyBatch() {
  if (!batchId.value) return
  loading.value = true
  error.value = null
  try {
    applyResult.value = await historicalImportApply(batchId.value)
    step.value = 'apply-deliveries'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Apply failed'
  } finally {
    loading.value = false
  }
}

async function applyDeliveries() {
  if (!batchId.value || !selectedFile.value) return
  loading.value = true
  error.value = null
  try {
    deliveriesResult.value = await historicalImportApplyDeliveries(batchId.value, selectedFile.value)
    await fetchTrainingStatus()
    step.value = 'done'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Delivery import failed'
  } finally {
    loading.value = false
  }
}

async function skipDeliveries() {
  await fetchTrainingStatus()
  step.value = 'done'
}

async function fetchTrainingStatus() {
  if (!batchId.value) return
  try {
    trainingStatus.value = await historicalImportGetTrainingStatus(batchId.value)
  } catch {
    // Training status is informational; non-fatal if unavailable
    trainingStatus.value = null
  }
}
</script>

<style scoped>
/* =====================================================
   HISTORICAL IMPORT PANEL — Design System Token-based
   ===================================================== */

.hip-panel {
  display: grid;
  gap: var(--space-4);
}

.hip-step {
  display: grid;
  gap: var(--space-4);
}

.hip-step-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

/* Title */
.hip-title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.hip-desc {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Drop zone */
.hip-dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-6) var(--space-4);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised, #f8fafc);
  cursor: pointer;
  text-align: center;
  transition: border-color 0.15s, background 0.15s;
}

.hip-dropzone:hover,
.hip-dropzone:focus-visible {
  border-color: var(--color-primary);
  background: var(--color-primary-subtle, #eff6ff);
  outline: none;
}

.hip-dropzone--drag {
  border-color: var(--color-primary);
  background: var(--color-primary-subtle, #eff6ff);
}

.hip-dropzone-icon {
  font-size: 2rem;
  line-height: 1;
}

.hip-dropzone-text {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.hip-file-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

/* Preview summary */
.hip-preview-summary {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised, #f8fafc);
}

.hip-preview-row {
  display: flex;
  gap: var(--space-3);
  font-size: var(--text-sm);
}

.hip-preview-label {
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  min-width: 120px;
  flex-shrink: 0;
}

.hip-preview-value {
  color: var(--color-text);
}

/* Preview error */
.hip-preview-error {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-danger, #dc2626);
  border-radius: var(--radius-md);
  background: var(--color-danger-subtle, #fef2f2);
}

.hip-preview-status-label {
  margin: 0;
  font-weight: var(--font-semibold);
  color: var(--color-danger, #dc2626);
}

.hip-preview-status-detail {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Duplicate detection result */
.hip-dup-result {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}

.hip-dup-result--ok {
  background: var(--color-success-subtle, #dcfce7);
  color: var(--color-success, #16a34a);
}

.hip-dup-result--warn {
  background: var(--color-warning-subtle, #fef9c3);
  color: var(--color-warning, #a16207);
}

.hip-dup-icon {
  flex-shrink: 0;
}

.hip-dup-batch {
  font-size: var(--text-xs);
  opacity: 0.8;
}

/* Issues list */
.hip-issues {
  display: grid;
  gap: var(--space-2);
}

.hip-section-title {
  margin: 0 0 var(--space-1);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.hip-issue-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--space-1);
}

.hip-issue {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  font-size: var(--text-sm);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
}

.hip-issue--error {
  background: var(--color-danger-subtle, #fef2f2);
  color: var(--color-danger, #dc2626);
}

.hip-issue--warning {
  background: var(--color-warning-subtle, #fef9c3);
  color: var(--color-warning, #a16207);
}

/* Innings table */
.hip-innings {
  display: grid;
  gap: var(--space-2);
}

.hip-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.hip-table th {
  text-align: left;
  padding: var(--space-1) var(--space-2);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  border-bottom: 1px solid var(--color-border);
}

.hip-table td {
  padding: var(--space-1) var(--space-2);
  color: var(--color-text);
  border-bottom: 1px solid var(--color-border-subtle, #f1f5f9);
}

/* Confirm box */
.hip-confirm-box {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.hip-confirm-intro {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text);
}

.hip-confirm-desc {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Actions */
.hip-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.hip-action-hint {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* Buttons */
.hip-btn {
  display: inline-flex;
  align-items: center;
  padding: var(--space-2) var(--space-3);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  text-decoration: none;
}

.hip-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.hip-btn--primary {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.hip-btn--primary:hover:not(:disabled) {
  background: var(--color-primary-hover, #1d4ed8);
}

.hip-btn--ghost {
  background: transparent;
  color: var(--color-text-muted);
  border-color: var(--color-border);
}

.hip-btn--ghost:hover:not(:disabled) {
  background: var(--color-surface-raised, #f8fafc);
}

/* Link-style button */
.hip-link-btn {
  background: none;
  border: none;
  padding: 0;
  font-size: var(--text-sm);
  color: var(--color-primary);
  cursor: pointer;
  text-decoration: underline;
}

.hip-link-btn:hover {
  text-decoration: none;
}

/* Loading */
.hip-loading {
  padding: var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Error */
.hip-error {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--color-danger-subtle, #fef2f2);
  color: var(--color-danger, #dc2626);
  font-size: var(--text-sm);
}

/* Intro */
.hip-intro {
  display: grid;
  gap: var(--space-2);
}

/* Done */
.hip-done {
  display: grid;
  gap: var(--space-4);
  text-align: center;
}

.hip-done-icon {
  font-size: 2.5rem;
  line-height: 1;
}

.hip-done-summary {
  display: grid;
  gap: var(--space-2);
  text-align: left;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.hip-done-row {
  display: flex;
  gap: var(--space-3);
  font-size: var(--text-sm);
}

.hip-done-label {
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  min-width: 140px;
  flex-shrink: 0;
}

.hip-done-value {
  color: var(--color-text);
}

.hip-done-value--ok {
  color: var(--color-success, #16a34a);
  font-weight: var(--font-medium);
}

.hip-done-value--muted {
  color: var(--color-text-muted);
}

.hip-done-hint {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Progress dots */
.hip-progress {
  display: flex;
  justify-content: center;
  gap: var(--space-2);
  padding-top: var(--space-2);
}

.hip-progress-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-border);
  transition: background 0.15s;
}

.hip-progress-dot--active {
  background: var(--color-primary);
}

.hip-progress-dot--done {
  background: var(--color-success, #16a34a);
}

/* Preview: valid wrapper */
.hip-preview-valid {
  display: grid;
  gap: var(--space-4);
}
</style>

<template>
  <div class="hiz-panel">
    <div class="hiz-header">
      <h3 class="hiz-title">Bulk ZIP import</h3>
      <p class="hiz-subtitle">
        Upload a <code>.zip</code> bundle with historical match JSON files.
      </p>
    </div>

    <div class="hiz-controls">
      <input
        ref="fileInputRef"
        type="file"
        accept=".zip,application/zip,application/x-zip-compressed,multipart/x-zip"
        :disabled="loading"
        @change="onFileChange"
      />
      <button
        class="hiz-btn hiz-btn--primary"
        type="button"
        :disabled="!selectedZipFile || loading"
        @click="runDryRun"
      >
        {{ loading && loadingStep === 'dry-run' ? 'Validating ZIP…' : 'Preview ZIP import' }}
      </button>
    </div>

    <p v-if="fileSelectError" class="hiz-error" role="alert">{{ fileSelectError }}</p>
    <p v-if="error" class="hiz-error" role="alert">{{ error }}</p>
    <p v-if="loading" class="hiz-loading" role="status" aria-live="polite">
      {{ loadingStep === 'apply' ? 'Applying selected files…' : 'Uploading and validating…' }}
    </p>

    <section v-if="dryRunResult" class="hiz-result">
      <h4 class="hiz-section-title">Import preview summary</h4>
      <ul class="hiz-summary-list">
        <li>Files processed: {{ dryRunResult.total_entries }}</li>
        <li>JSON files found: {{ dryRunResult.json_entries }}</li>
        <li>Non-JSON files skipped: {{ dryRunResult.non_json_entries }}</li>
        <li>Valid files: {{ dryRunResult.summary.valid ?? 0 }}</li>
        <li>Duplicate files: {{ dryRunResult.summary.duplicate ?? 0 }}</li>
        <li>Invalid/failed files: {{ (dryRunResult.summary.invalid ?? 0) + (dryRunResult.summary.error ?? 0) }}</li>
      </ul>

      <div v-if="validFiles.length" class="hiz-apply-block">
        <h4 class="hiz-section-title">Select files to import</h4>
        <label
          v-for="item in validFiles"
          :key="item.file_name"
          class="hiz-file-option"
        >
          <input
            type="checkbox"
            :checked="selectedFileNames.includes(item.file_name)"
            :disabled="loading"
            @change="onSelectedFileToggle(item.file_name, $event)"
          />
          <span>{{ item.file_name }}</span>
        </label>

        <button
          class="hiz-btn hiz-btn--primary"
          type="button"
          :disabled="loading || selectedFileNames.length === 0"
          @click="applySelected"
        >
          {{ loading && loadingStep === 'apply' ? 'Importing…' : `Import selected (${selectedFileNames.length})` }}
        </button>
      </div>

      <div v-if="nonValidFiles.length" class="hiz-warnings">
        <h4 class="hiz-section-title">Skipped / failed files</h4>
        <ul class="hiz-errors-list">
          <li v-for="item in nonValidFiles" :key="item.file_name">
            <strong>{{ item.file_name }}</strong>: {{ item.message }}
          </li>
        </ul>
      </div>
    </section>

    <section v-if="applyResult" class="hiz-result">
      <h4 class="hiz-section-title">Import result</h4>
      <ul class="hiz-summary-list">
        <li>Matches imported: {{ applyResult.applied_count }}</li>
        <li>Skipped/duplicates: {{ applyResult.skipped_count }}</li>
        <li>Failed records/files: {{ applyResult.error_count }}</li>
      </ul>

      <ul v-if="applyIssues.length" class="hiz-errors-list">
        <li v-for="issue in applyIssues" :key="issue.file_name">
          <strong>{{ issue.file_name }}</strong>: {{ issue.message }}
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  historicalImportBulkZipApply,
  historicalImportBulkZipDryRun,
  type HistoricalImportBulkZipApplyResponse,
  type HistoricalImportBulkZipDryRunResponse,
  type HistoricalImportBulkZipFilePreview,
} from '@/services/api'

const emit = defineEmits<{
  (e: 'import-done', gameId: string | null): void
}>()

const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedZipFile = ref<File | null>(null)
const fileSelectError = ref<string | null>(null)
const error = ref<string | null>(null)
const loading = ref(false)
const loadingStep = ref<'dry-run' | 'apply'>('dry-run')
const dryRunResult = ref<HistoricalImportBulkZipDryRunResponse | null>(null)
const applyResult = ref<HistoricalImportBulkZipApplyResponse | null>(null)
const selectedFileNames = ref<string[]>([])

const validFiles = computed(() =>
  dryRunResult.value?.files.filter((item) => item.status === 'valid') ?? [],
)

const nonValidFiles = computed(() =>
  dryRunResult.value?.files.filter((item) => item.status !== 'valid') ?? [],
)

const applyIssues = computed(() =>
  applyResult.value?.results.filter((item) => item.status !== 'applied') ?? [],
)

function isZipFile(file: File): boolean {
  const lower = file.name.toLowerCase()
  return lower.endsWith('.zip') || [
    'application/zip',
    'application/x-zip-compressed',
    'multipart/x-zip',
  ].includes((file.type || '').toLowerCase())
}

function onFileChange(event: Event) {
  fileSelectError.value = null
  error.value = null
  dryRunResult.value = null
  applyResult.value = null
  selectedFileNames.value = []
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!isZipFile(file)) {
    fileSelectError.value = 'Only .zip files are supported for bulk import.'
    selectedZipFile.value = null
    return
  }
  selectedZipFile.value = file
}

function normalizeErrorMessage(err: unknown): string {
  if (!(err instanceof Error)) return 'Bulk ZIP import failed'
  try {
    const parsed = JSON.parse(err.message)
    if (typeof parsed === 'string') return parsed
    if (parsed && typeof parsed.detail === 'string') return parsed.detail
  } catch {
    // noop
  }
  return err.message || 'Bulk ZIP import failed'
}

function collectDefaultSelection(files: HistoricalImportBulkZipFilePreview[]) {
  selectedFileNames.value = files
    .filter((item) => item.status === 'valid')
    .map((item) => item.file_name)
}

function toggleSelectedFile(fileName: string, checked: boolean) {
  const current = new Set(selectedFileNames.value)
  if (checked) current.add(fileName)
  else current.delete(fileName)
  selectedFileNames.value = [...current]
}

function onSelectedFileToggle(fileName: string, event: Event) {
  const target = event.target as HTMLInputElement | null
  toggleSelectedFile(fileName, Boolean(target?.checked))
}

async function runDryRun() {
  if (!selectedZipFile.value || loading.value) return
  loading.value = true
  loadingStep.value = 'dry-run'
  error.value = null
  applyResult.value = null
  try {
    const result = await historicalImportBulkZipDryRun(selectedZipFile.value)
    dryRunResult.value = result
    collectDefaultSelection(result.files)
  } catch (err) {
    error.value = normalizeErrorMessage(err)
  } finally {
    loading.value = false
  }
}

async function applySelected() {
  if (!selectedZipFile.value || selectedFileNames.value.length === 0 || loading.value) return
  loading.value = true
  loadingStep.value = 'apply'
  error.value = null
  try {
    const result = await historicalImportBulkZipApply(selectedZipFile.value, selectedFileNames.value)
    applyResult.value = result
    const firstApplied = result.results.find((item) => item.status === 'applied' && item.applied_game_id)
    emit('import-done', firstApplied?.applied_game_id ?? null)
  } catch (err) {
    error.value = normalizeErrorMessage(err)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.hiz-panel {
  display: grid;
  gap: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  background: var(--color-surface-raised, #f8fafc);
}

.hiz-title {
  margin: 0;
  font-size: var(--text-md);
}

.hiz-subtitle {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.hiz-controls {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}

.hiz-btn {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
}

.hiz-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.hiz-btn--primary {
  background: var(--color-primary);
  color: var(--color-primary-contrast, #fff);
  border-color: var(--color-primary);
}

.hiz-error {
  margin: 0;
  color: var(--color-danger, #b91c1c);
  font-size: var(--text-sm);
}

.hiz-loading {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.hiz-result {
  display: grid;
  gap: var(--space-2);
}

.hiz-section-title {
  margin: 0;
  font-size: var(--text-sm);
}

.hiz-summary-list,
.hiz-errors-list {
  margin: 0;
  padding-left: 1.1rem;
  display: grid;
  gap: 0.2rem;
}

.hiz-apply-block,
.hiz-warnings {
  display: grid;
  gap: var(--space-2);
}

.hiz-file-option {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
}
</style>

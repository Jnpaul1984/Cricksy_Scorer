<template>
  <div class="bzsr-panel">
    <div class="bzsr-header">
      <h3 class="bzsr-title">Bulk ZIP Source Payload Recovery</h3>
      <p class="bzsr-subtitle">
        Upload the original CPL ZIP to dry-run map every JSON file to existing historical import
        records. Then apply source-payload reattach for safe exact/likely mappings only.
      </p>
    </div>

    <p class="bzsr-warning-banner">
      Reattach stores provenance only. No delivery rows are inserted. No player/stat recalculation.
      Run Historical Backfill Audit + Reprocess after successful reattach.
    </p>

    <label class="bzsr-field">
      Original CPL ZIP (.zip)
      <input
        type="file"
        accept=".zip,application/zip,application/x-zip-compressed"
        :disabled="loading"
        data-testid="bzsr-file-input"
        @change="onFileChange"
      />
    </label>

    <div class="bzsr-actions">
      <button
        type="button"
        class="bzsr-btn bzsr-btn--primary"
        :disabled="loading || !selectedFile"
        data-testid="bzsr-run-dry-run-btn"
        @click="runDryRun"
      >
        {{ loading && loadingStep === 'dry-run' ? 'Running dry-run…' : 'Run dry-run' }}
      </button>
    </div>

    <p v-if="error" class="bzsr-error" role="alert" data-testid="bzsr-error">{{ error }}</p>

    <!-- Dry-run summary -->
    <section v-if="dryRunResult" class="bzsr-section" data-testid="bzsr-dry-run-summary">
      <h4 class="bzsr-section-title">Dry-run summary</h4>
      <ul class="bzsr-list">
        <li>Candidate JSON files: <strong>{{ dryRunResult.summary.candidate_json_count }}</strong></li>
        <li>Exact matches: <strong data-testid="bzsr-exact-count">{{ dryRunResult.summary.exact_match_count }}</strong></li>
        <li>Likely matches: <strong data-testid="bzsr-likely-count">{{ dryRunResult.summary.likely_match_count }}</strong></li>
        <li>Ambiguous matches: <strong>{{ dryRunResult.summary.ambiguous_count }}</strong></li>
        <li>No matches: <strong>{{ dryRunResult.summary.no_match_count }}</strong></li>
        <li>Already retained: <strong>{{ dryRunResult.summary.already_retained_count }}</strong></li>
        <li>Malformed JSON: <strong>{{ dryRunResult.summary.malformed_count }}</strong></li>
        <li>Unsafe ZIP entries: <strong>{{ dryRunResult.summary.unsafe_count }}</strong></li>
      </ul>
    </section>

    <!-- Candidate mapping table -->
    <section v-if="dryRunResult && dryRunResult.files.length > 0" class="bzsr-section" data-testid="bzsr-mapping-table">
      <h4 class="bzsr-section-title">Candidate mapping table</h4>
      <p class="bzsr-hint">
        Select exact/likely mappings to apply. Ambiguous, no-match, malformed, and unsafe entries
        cannot be selected.
      </p>
      <div class="bzsr-table-wrap">
        <table class="bzsr-table">
          <thead>
            <tr>
              <th>Select</th>
              <th>Source file</th>
              <th>Status</th>
              <th>Match ID</th>
              <th>Batch ID</th>
              <th>Teams</th>
              <th>Date</th>
              <th>Competition</th>
              <th>Venue</th>
              <th>Registry.people</th>
              <th>Exp. deliveries</th>
              <th>Exp. wickets</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in dryRunResult.files"
              :key="item.file_name"
              :class="rowClass(item)"
            >
              <td>
                <input
                  v-if="isSelectable(item)"
                  type="checkbox"
                  :checked="isSelected(item)"
                  :disabled="loading"
                  :data-testid="`bzsr-select-${item.file_name}`"
                  @change="toggleSelection(item)"
                />
                <span v-else class="bzsr-blocked-icon" :title="item.match_confidence">—</span>
              </td>
              <td class="bzsr-mono">{{ item.file_name }}</td>
              <td>
                <span :class="confidenceBadgeClass(item.match_confidence)">
                  {{ item.match_confidence }}
                </span>
              </td>
              <td class="bzsr-mono">{{ item.matched_target?.match_id ?? '—' }}</td>
              <td class="bzsr-mono">{{ item.matched_target?.batch_id ?? '—' }}</td>
              <td>{{ item.metadata.teams?.join(' vs ') ?? '—' }}</td>
              <td>{{ item.metadata.date ?? '—' }}</td>
              <td>{{ item.metadata.competition_name ?? '—' }}</td>
              <td>{{ item.metadata.venue ?? '—' }}</td>
              <td>{{ item.metadata.registry_people_available ? 'Yes' : 'No' }}</td>
              <td>{{ item.metadata.expected_deliveries ?? 0 }}</td>
              <td>{{ item.metadata.expected_wickets ?? 0 }}</td>
              <td>{{ item.message }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Apply section -->
    <section v-if="dryRunResult && selectedMappings.length > 0" class="bzsr-section" data-testid="bzsr-apply-section">
      <h4 class="bzsr-section-title">Apply selected mappings</h4>
      <p>Selected exact/likely mappings: <strong>{{ selectedMappings.length }}</strong></p>
      <label class="bzsr-confirm">
        <input
          v-model="confirmApply"
          type="checkbox"
          :disabled="loading"
          data-testid="bzsr-confirm-checkbox"
        />
        I confirm these selected mappings should attach retained source JSON only.
        No delivery rows will be created.
      </label>
      <button
        type="button"
        class="bzsr-btn bzsr-btn--primary"
        :disabled="loading || selectedMappings.length === 0 || !confirmApply"
        data-testid="bzsr-apply-btn"
        @click="applySelected"
      >
        {{
          loading && loadingStep === 'apply'
            ? 'Applying…'
            : `Apply selected (${selectedMappings.length})`
        }}
      </button>
    </section>

    <!-- Apply result -->
    <section v-if="applyResult" class="bzsr-section" data-testid="bzsr-apply-result">
      <h4 class="bzsr-section-title">Apply response</h4>
      <ul class="bzsr-list">
        <li>Status: <strong>{{ applyResult.status }}</strong></li>
        <li>Applied: <strong>{{ applyResult.applied_count }}</strong></li>
        <li>Skipped (already retained): <strong>{{ applyResult.skipped_count }}</strong></li>
        <li>Ambiguous (from full ZIP scan): <strong>{{ applyResult.ambiguous_count }}</strong></li>
        <li>No match (from full ZIP scan): <strong>{{ applyResult.no_match_count }}</strong></li>
        <li>Malformed (from full ZIP scan): <strong>{{ applyResult.malformed_count }}</strong></li>
        <li>Errors: <strong>{{ applyResult.error_count }}</strong></li>
      </ul>
      <p class="bzsr-follow-up" data-testid="bzsr-follow-up-message">
        {{ applyResult.follow_up_message }}
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  historicalBulkZipSourcePayloadApply,
  historicalBulkZipSourcePayloadDryRun,
  type HistoricalBulkZipSourcePayloadApplyResponse,
  type HistoricalBulkZipSourcePayloadDryRunResponse,
  type HistoricalSourcePayloadReattachDryRunFileResult,
} from '@/services/api'

const loading = ref(false)
const loadingStep = ref<'dry-run' | 'apply'>('dry-run')
const selectedFile = ref<File | null>(null)
const error = ref<string | null>(null)
const dryRunResult = ref<HistoricalBulkZipSourcePayloadDryRunResponse | null>(null)
const applyResult = ref<HistoricalBulkZipSourcePayloadApplyResponse | null>(null)
const confirmApply = ref(false)

// Set of selected file names (only exact/likely non-ambiguous entries)
const selectedFileNames = ref<Set<string>>(new Set())

const selectedMappings = computed(() => {
  if (!dryRunResult.value) return []
  return dryRunResult.value.files
    .filter(
      (f) =>
        selectedFileNames.value.has(f.file_name) &&
        f.matched_target != null,
    )
    .map((f) => ({
      file_name: f.file_name,
      batch_id: f.matched_target!.batch_id,
    }))
})

function isSelectable(item: HistoricalSourcePayloadReattachDryRunFileResult): boolean {
  return (
    !item.blocked_from_apply &&
    item.match_confidence !== 'ambiguous' &&
    item.match_confidence !== 'no_match' &&
    item.matched_target != null
  )
}

function isSelected(item: HistoricalSourcePayloadReattachDryRunFileResult): boolean {
  return selectedFileNames.value.has(item.file_name)
}

function toggleSelection(item: HistoricalSourcePayloadReattachDryRunFileResult): void {
  if (!isSelectable(item)) return
  const next = new Set(selectedFileNames.value)
  if (next.has(item.file_name)) {
    next.delete(item.file_name)
  } else {
    next.add(item.file_name)
  }
  selectedFileNames.value = next
}

function rowClass(item: HistoricalSourcePayloadReattachDryRunFileResult): string {
  if (item.match_confidence === 'exact_match') return 'bzsr-row--exact'
  if (item.match_confidence === 'likely_match') return 'bzsr-row--likely'
  if (item.match_confidence === 'ambiguous') return 'bzsr-row--ambiguous'
  return 'bzsr-row--blocked'
}

function confidenceBadgeClass(confidence: string): string {
  const map: Record<string, string> = {
    exact_match: 'bzsr-badge bzsr-badge--exact',
    likely_match: 'bzsr-badge bzsr-badge--likely',
    ambiguous: 'bzsr-badge bzsr-badge--ambiguous',
    no_match: 'bzsr-badge bzsr-badge--no-match',
  }
  return map[confidence] ?? 'bzsr-badge'
}

function onFileChange(event: Event): void {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0] ?? null
  selectedFile.value = file
  dryRunResult.value = null
  applyResult.value = null
  error.value = null
  selectedFileNames.value = new Set()
  confirmApply.value = false
}

async function runDryRun(): Promise<void> {
  if (!selectedFile.value) return
  loading.value = true
  loadingStep.value = 'dry-run'
  error.value = null
  dryRunResult.value = null
  applyResult.value = null
  selectedFileNames.value = new Set()
  confirmApply.value = false
  try {
    dryRunResult.value = await historicalBulkZipSourcePayloadDryRun(selectedFile.value)
  } catch (err) {
    error.value =
      err instanceof Error
        ? err.message
        : 'Unable to run bulk ZIP source payload dry-run.'
  } finally {
    loading.value = false
  }
}

async function applySelected(): Promise<void> {
  if (!selectedFile.value || selectedMappings.value.length === 0) return
  loading.value = true
  loadingStep.value = 'apply'
  error.value = null
  try {
    applyResult.value = await historicalBulkZipSourcePayloadApply(
      selectedFile.value,
      selectedMappings.value,
    )
  } catch (err) {
    error.value =
      err instanceof Error
        ? err.message
        : 'Unable to apply bulk ZIP source payload reattach.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.bzsr-panel {
  display: grid;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid var(--color-border-soft, #d6d9e0);
  border-radius: 0.75rem;
  background: var(--color-surface, #fff);
}

.bzsr-header {
  display: grid;
  gap: 0.35rem;
}

.bzsr-title,
.bzsr-section-title {
  margin: 0;
}

.bzsr-subtitle,
.bzsr-hint {
  margin: 0;
  color: var(--color-text-muted, #5f677a);
  font-size: 0.92rem;
}

.bzsr-warning-banner,
.bzsr-error {
  margin: 0;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
}

.bzsr-warning-banner {
  background: rgba(255, 196, 0, 0.12);
  color: #715400;
}

.bzsr-error {
  background: rgba(214, 47, 70, 0.12);
  color: #9f1730;
}

.bzsr-field,
.bzsr-section {
  display: grid;
  gap: 0.5rem;
}

.bzsr-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.bzsr-btn {
  border: 1px solid transparent;
  border-radius: 0.5rem;
  padding: 0.65rem 1rem;
  font-weight: 600;
  cursor: pointer;
}

.bzsr-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.bzsr-btn--primary {
  background: #1f5eff;
  color: #fff;
}

.bzsr-table-wrap {
  overflow-x: auto;
}

.bzsr-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}

.bzsr-table th,
.bzsr-table td {
  padding: 0.55rem 0.5rem;
  border-bottom: 1px solid var(--color-border-soft, #d6d9e0);
  text-align: left;
  vertical-align: top;
}

.bzsr-table th {
  font-weight: 600;
  white-space: nowrap;
  background: var(--color-surface-alt, #f6f7fa);
}

.bzsr-mono {
  font-family: monospace;
  font-size: 0.82rem;
  word-break: break-all;
}

.bzsr-row--exact {
  background: rgba(0, 180, 80, 0.04);
}

.bzsr-row--likely {
  background: rgba(255, 196, 0, 0.06);
}

.bzsr-row--ambiguous,
.bzsr-row--blocked {
  opacity: 0.7;
}

.bzsr-badge {
  display: inline-block;
  padding: 0.2rem 0.45rem;
  border-radius: 0.35rem;
  font-size: 0.78rem;
  font-weight: 600;
  white-space: nowrap;
}

.bzsr-badge--exact {
  background: rgba(0, 180, 80, 0.14);
  color: #00622c;
}

.bzsr-badge--likely {
  background: rgba(255, 196, 0, 0.18);
  color: #715400;
}

.bzsr-badge--ambiguous {
  background: rgba(255, 120, 0, 0.14);
  color: #7a3200;
}

.bzsr-badge--no-match {
  background: rgba(214, 47, 70, 0.1);
  color: #9f1730;
}

.bzsr-blocked-icon {
  color: var(--color-text-muted, #5f677a);
}

.bzsr-list {
  margin: 0;
  padding-left: 1.25rem;
}

.bzsr-confirm {
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
  font-size: 0.92rem;
}

.bzsr-follow-up {
  margin: 0;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  background: rgba(31, 94, 255, 0.08);
  color: #0a2a8a;
  font-weight: 500;
}
</style>

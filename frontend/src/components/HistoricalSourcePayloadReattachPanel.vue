<template>
  <div class="hsr-panel">
    <div class="hsr-header">
      <h3 class="hsr-title">Historical Source Payload Reattach</h3>
      <p class="hsr-subtitle">
        Upload original JSON or ZIP repair payloads, dry-run deterministic matching, and reattach retained source JSON without recreating matches.
      </p>
    </div>

    <p class="hsr-warning-banner">
      Reattach stores provenance only. Delivery backfill/reprocess must be run separately after a successful reattach.
    </p>

    <label class="hsr-field">
      Repair payload (.json or .zip)
      <input
        type="file"
        accept=".json,.zip,application/json,application/zip"
        :disabled="loading"
        data-testid="hsr-file-input"
        @change="onFileChange"
      />
    </label>

    <div class="hsr-actions">
      <button
        type="button"
        class="hsr-btn hsr-btn--primary"
        :disabled="loading || !selectedFile"
        data-testid="hsr-run-dry-run-btn"
        @click="runDryRun"
      >
        {{ loading && loadingStep === 'dry-run' ? 'Running reattach dry-run…' : 'Run reattach dry-run' }}
      </button>
    </div>

    <p v-if="error" class="hsr-error" role="alert">{{ error }}</p>

    <section v-if="dryRunResult" class="hsr-section">
      <h4 class="hsr-section-title">Dry-run summary</h4>
      <ul class="hsr-list">
        <li>Total candidate files: {{ dryRunResult.total_candidates }}</li>
        <li>Ready exact/likely matches: {{ dryRunResult.ready_candidates }}</li>
        <li>Blocked files: {{ dryRunResult.blocked_candidates }}</li>
      </ul>
    </section>

    <section v-if="dryRunResult" class="hsr-section">
      <h4 class="hsr-section-title">Candidate mappings</h4>
      <div class="hsr-table-wrap">
        <table class="hsr-table">
          <thead>
            <tr>
              <th>Select</th>
              <th>File</th>
              <th>Confidence</th>
              <th>Match ID</th>
              <th>Batch ID</th>
              <th>Teams</th>
              <th>Date</th>
              <th>Competition</th>
              <th>Venue</th>
              <th>registry.people</th>
              <th>Expected deliveries</th>
              <th>Expected wickets</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in dryRunResult.files" :key="item.file_name">
              <td>
                <input
                  type="checkbox"
                  :checked="selectedKeys.includes(selectionKey(item))"
                  :disabled="loading || !isSelectable(item)"
                  @change="toggleSelection(item, $event)"
                />
              </td>
              <td>{{ item.file_name }}</td>
              <td>{{ item.match_confidence }}</td>
              <td>{{ item.matched_target?.match_id ?? '—' }}</td>
              <td>{{ item.matched_target?.batch_id ?? '—' }}</td>
              <td>{{ item.metadata.teams.join(' vs ') || '—' }}</td>
              <td>{{ item.metadata.date || '—' }}</td>
              <td>{{ item.metadata.competition_name || '—' }}</td>
              <td>{{ item.metadata.venue || item.metadata.city || '—' }}</td>
              <td>{{ item.metadata.registry_people_available ? 'Yes' : 'No' }}</td>
              <td>{{ item.metadata.expected_deliveries }}</td>
              <td>{{ item.metadata.expected_wickets }}</td>
              <td>{{ describeItem(item) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="hasBlockedWarnings" class="hsr-warning-banner">
        Ambiguous and no-match files are blocked from apply. Review candidate mappings before retrying.
      </p>
    </section>

    <section v-if="dryRunResult" class="hsr-section">
      <h4 class="hsr-section-title">Controlled reattach apply</h4>
      <p>Selected exact/likely mappings: <strong>{{ selectedMappings.length }}</strong></p>
      <label class="hsr-confirm">
        <input v-model="confirmApply" type="checkbox" :disabled="loading" />
        I confirm these selected mappings should attach retained source JSON only.
      </label>
      <button
        type="button"
        class="hsr-btn hsr-btn--primary"
        :disabled="loading || !selectedFile || selectedMappings.length === 0 || !confirmApply"
        data-testid="hsr-apply-btn"
        @click="applySelected"
      >
        {{ loading && loadingStep === 'apply' ? 'Applying reattach…' : `Apply selected (${selectedMappings.length})` }}
      </button>
    </section>

    <section v-if="applyResult" class="hsr-section">
      <h4 class="hsr-section-title">Apply response</h4>
      <ul class="hsr-list">
        <li>Status: {{ applyResult.status }}</li>
        <li>Reattached: {{ applyResult.reattached_count }}</li>
        <li>Skipped: {{ applyResult.skipped_count }}</li>
        <li>Errors: {{ applyResult.error_count }}</li>
      </ul>
      <p class="hsr-idempotency-note">{{ applyResult.follow_up_message }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import {
  historicalSourcePayloadReattachApply,
  historicalSourcePayloadReattachDryRun,
  type HistoricalSourcePayloadReattachApplyResponse,
  type HistoricalSourcePayloadReattachDryRunFileResult,
  type HistoricalSourcePayloadReattachDryRunResponse,
} from '@/services/api'

const loading = ref(false)
const loadingStep = ref<'dry-run' | 'apply'>('dry-run')
const selectedFile = ref<File | null>(null)
const error = ref<string | null>(null)
const dryRunResult = ref<HistoricalSourcePayloadReattachDryRunResponse | null>(null)
const applyResult = ref<HistoricalSourcePayloadReattachApplyResponse | null>(null)
const confirmApply = ref(false)
const selectedKeys = ref<string[]>([])

const selectionKey = (item: HistoricalSourcePayloadReattachDryRunFileResult) =>
  `${item.file_name}::${item.matched_target?.batch_id ?? ''}`

const isSelectable = (item: HistoricalSourcePayloadReattachDryRunFileResult) =>
  item.status === 'ready' && !item.blocked_from_apply && Boolean(item.matched_target?.batch_id)

const selectedMappings = computed(() =>
  (dryRunResult.value?.files ?? [])
    .filter((item) => selectedKeys.value.includes(selectionKey(item)) && item.matched_target)
    .map((item) => ({
      file_name: item.file_name,
      batch_id: item.matched_target!.batch_id,
    })),
)

const hasBlockedWarnings = computed(() =>
  (dryRunResult.value?.files ?? []).some((item) => item.blocked_from_apply),
)

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
  dryRunResult.value = null
  applyResult.value = null
  selectedKeys.value = []
  confirmApply.value = false
  error.value = null
}

function toggleSelection(item: HistoricalSourcePayloadReattachDryRunFileResult, event: Event) {
  const checked = (event.target as HTMLInputElement).checked
  const key = selectionKey(item)
  if (!checked) {
    selectedKeys.value = selectedKeys.value.filter((value) => value !== key)
    return
  }
  if (!selectedKeys.value.includes(key)) {
    selectedKeys.value = [...selectedKeys.value, key]
  }
}

function describeItem(item: HistoricalSourcePayloadReattachDryRunFileResult) {
  if (item.candidate_matches.length > 1 && item.blocked_from_apply) {
    return `${item.message} (${item.candidate_matches.length} candidates)`
  }
  return item.message
}

async function runDryRun() {
  if (!selectedFile.value) return
  loading.value = true
  loadingStep.value = 'dry-run'
  error.value = null
  selectedKeys.value = []
  confirmApply.value = false
  applyResult.value = null
  try {
    dryRunResult.value = await historicalSourcePayloadReattachDryRun(selectedFile.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to run source payload reattach dry-run.'
  } finally {
    loading.value = false
  }
}

async function applySelected() {
  if (!selectedFile.value || selectedMappings.value.length === 0) return
  loading.value = true
  loadingStep.value = 'apply'
  error.value = null
  try {
    applyResult.value = await historicalSourcePayloadReattachApply(
      selectedFile.value,
      selectedMappings.value,
    )
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to apply source payload reattach.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.hsr-panel {
  display: grid;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid var(--color-border-soft, #d6d9e0);
  border-radius: 0.75rem;
  background: var(--color-surface, #fff);
}

.hsr-header {
  display: grid;
  gap: 0.35rem;
}

.hsr-title,
.hsr-section-title {
  margin: 0;
}

.hsr-subtitle,
.hsr-idempotency-note {
  margin: 0;
  color: var(--color-text-muted, #5f677a);
}

.hsr-warning-banner,
.hsr-error {
  margin: 0;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
}

.hsr-warning-banner {
  background: rgba(255, 196, 0, 0.12);
  color: #715400;
}

.hsr-error {
  background: rgba(214, 47, 70, 0.12);
  color: #9f1730;
}

.hsr-field,
.hsr-section {
  display: grid;
  gap: 0.5rem;
}

.hsr-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.hsr-btn {
  border: 1px solid transparent;
  border-radius: 0.5rem;
  padding: 0.65rem 1rem;
  font-weight: 600;
  cursor: pointer;
}

.hsr-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.hsr-btn--primary {
  background: #1f5eff;
  color: #fff;
}

.hsr-table-wrap {
  overflow-x: auto;
}

.hsr-table {
  width: 100%;
  border-collapse: collapse;
}

.hsr-table th,
.hsr-table td {
  padding: 0.65rem 0.5rem;
  border-bottom: 1px solid var(--color-border-soft, #d6d9e0);
  text-align: left;
  vertical-align: top;
}

.hsr-list {
  margin: 0;
  padding-left: 1.25rem;
}

.hsr-confirm {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
</style>

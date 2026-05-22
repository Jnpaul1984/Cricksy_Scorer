<template>
  <div class="hcrr-panel">
    <div class="hcrr-header">
      <h3 class="hcrr-title">Clean Historical CPL Reset + Reimport</h3>
      <p class="hcrr-subtitle">
        Safely reset and reimport historical CPL records from original JSON/ZIP source with mandatory
        dry-run preview before any destructive apply.
      </p>
    </div>

    <section class="hcrr-section">
      <h4 class="hcrr-section-title">What this does</h4>
      <p class="hcrr-note">
        This controlled workflow is for historical CPL recovery only. Dry-run is read-only and does not
        delete data.
      </p>
    </section>

    <section class="hcrr-section">
      <h4 class="hcrr-section-title">Source bundle</h4>
      <label class="hcrr-field">
        Original CPL source (.json or .zip)
        <input
          type="file"
          accept=".json,.zip,application/json,application/zip"
          :disabled="loading"
          data-testid="hcrr-file-input"
          @change="onFileChange"
        />
      </label>
    </section>

    <section class="hcrr-section">
      <h4 class="hcrr-section-title">Scope</h4>
      <label class="hcrr-field">
        Season filter (future backend support)
        <input
          v-model="seasonFilter"
          type="text"
          disabled
          placeholder="Not yet supported by reset/reimport endpoint"
          data-testid="hcrr-season-filter"
        />
      </label>
      <label class="hcrr-field">
        Max records for controlled run
        <input
          v-model.number="maxRecords"
          type="number"
          min="1"
          max="25"
          :disabled="loading"
          data-testid="hcrr-max-records"
          @change="invalidatePreviewState"
        />
      </label>
      <p class="hcrr-note">Safe default is 1 record first.</p>
    </section>

    <div class="hcrr-actions">
      <button
        type="button"
        class="hcrr-btn hcrr-btn--primary"
        :disabled="loading || !selectedFile"
        data-testid="hcrr-dry-run-btn"
        @click="runDryRun"
      >
        {{ loading && loadingStep === 'dry-run' ? 'Running dry-run…' : 'Run dry-run (mandatory)' }}
      </button>
    </div>

    <p v-if="error" class="hcrr-error" role="alert" data-testid="hcrr-error">{{ error }}</p>

    <section v-if="dryRunResult" class="hcrr-section" data-testid="hcrr-dry-run-summary">
      <h4 class="hcrr-section-title">Dry-run preview</h4>
      <ul class="hcrr-list">
        <li>Candidate source files: <strong>{{ dryRunResult.source_file_mapping.length }}</strong></li>
        <li>Candidate existing historical CPL records: <strong>{{ dryRunResult.total_candidate_existing_historical_records }}</strong></li>
        <li>Safe reset records: <strong>{{ dryRunResult.records_safe_to_reset }}</strong></li>
        <li>Blocked records: <strong>{{ dryRunResult.records_blocked_from_reset }}</strong></li>
        <li>Expected matches: <strong>{{ dryRunResult.expected_matches_to_import }}</strong></li>
        <li>Expected deliveries: <strong>{{ dryRunResult.expected_deliveries }}</strong></li>
        <li>Expected wickets: <strong>{{ dryRunResult.expected_wickets }}</strong></li>
        <li>Expected players: <strong>{{ dryRunResult.expected_players }}</strong></li>
        <li>Duplicate risks: <strong>{{ dryRunResult.duplicate_risks }}</strong></li>
      </ul>
    </section>

    <section v-if="dryRunResult" class="hcrr-section">
      <h4 class="hcrr-section-title">Destructive action summary</h4>
      <ul class="hcrr-list">
        <li>Matches to reset: {{ dryRunResult.destructive_action_summary.matches_to_reset }}</li>
        <li>Historical batches in scope: {{ dryRunResult.destructive_action_summary.historical_batches_in_scope }}</li>
        <li>Delivery rows to rebuild: {{ dryRunResult.destructive_action_summary.delivery_rows_to_rebuild }}</li>
        <li>Blocked records: {{ dryRunResult.destructive_action_summary.blocked_records }}</li>
      </ul>
      <p class="hcrr-note">Source JSON retention is attempted during apply when mappings are safe.</p>
    </section>

    <section v-if="dryRunResult" class="hcrr-section">
      <h4 class="hcrr-section-title">Source mapping confidence</h4>
      <ul class="hcrr-list">
        <li>Exact matches: {{ sourceMappingCounts.exact_match }}</li>
        <li>Likely matches: {{ sourceMappingCounts.likely_match }}</li>
        <li>No match: {{ sourceMappingCounts.no_match }}</li>
      </ul>
    </section>

    <section v-if="dryRunResult?.blocked_records.length" class="hcrr-section">
      <h4 class="hcrr-section-title">Blocked records + reasons</h4>
      <div class="hcrr-table-wrap">
        <table class="hcrr-table">
          <thead>
            <tr>
              <th>Match ID</th>
              <th>Batch ID</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in dryRunResult.blocked_records" :key="`${record.batch_id}-${record.match_id}`">
              <td>{{ record.match_id || '—' }}</td>
              <td>{{ record.batch_id || '—' }}</td>
              <td>{{ record.reason }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="hcrr-section" data-testid="hcrr-apply-section">
      <h4 class="hcrr-section-title">Controlled apply</h4>
      <p v-if="!dryRunResult" class="hcrr-note">
        Run dry-run first. Apply remains disabled until a successful dry-run exists with safe scope.
      </p>
      <p class="hcrr-warning">
        Destructive operation: historical CPL records in scope will be reset/reimported.
      </p>
      <label class="hcrr-confirm">
        <input v-model="confirmApply" type="checkbox" :disabled="loading" />
        I confirm this controlled CPL reset/reimport operation.
      </label>
      <label class="hcrr-field">
        Type confirmation phrase
        <input
          v-model="confirmationPhrase"
          type="text"
          :disabled="loading"
          placeholder="I confirm this controlled CPL reset/reimport operation"
          data-testid="hcrr-confirmation-phrase"
        />
      </label>
      <button
        type="button"
        class="hcrr-btn hcrr-btn--danger"
        :disabled="!canApply"
        data-testid="hcrr-apply-btn"
        @click="applyResetReimport"
      >
        {{ loading && loadingStep === 'apply' ? 'Applying controlled reset/reimport…' : 'Apply reset/reimport' }}
      </button>
    </section>

    <section v-if="applyResult" class="hcrr-section" data-testid="hcrr-final-report">
      <h4 class="hcrr-section-title">Final import report</h4>
      <ul class="hcrr-list">
        <li>Operation status: <strong>{{ applyResult.status }}</strong></li>
        <li>Operation ID: <strong>{{ applyResult.operation_id }}</strong></li>
        <li>Matches reset (selected batches): <strong>{{ applyResult.reimport_report.selected_batches }}</strong></li>
        <li>Matches imported (selected matches): <strong>{{ applyResult.reimport_report.selected_matches }}</strong></li>
        <li>Source payloads reattached (apply report): <strong>{{ applyResult.source_payload_retention.report?.reattached_count ?? 0 }}</strong></li>
        <li>Source payload apply skipped count: <strong>{{ applyResult.source_payload_retention.report?.skipped_count ?? 0 }}</strong></li>
        <li>Source payload apply errors: <strong>{{ applyResult.source_payload_retention.report?.error_count ?? 0 }}</strong></li>
        <li>Deliveries — Expected from dry-run: <strong>{{ dryRunResult?.expected_deliveries ?? 0 }}</strong></li>
        <li>Wickets — Expected from dry-run: <strong>{{ dryRunResult?.expected_wickets ?? 0 }}</strong></li>
        <li>Players — Expected from dry-run: <strong>{{ dryRunResult?.expected_players ?? 0 }}</strong></li>
        <li>Unresolved players — Expected from dry-run audit: <strong>{{ dryRunResult?.audit?.records ? unresolvedPlayers : 0 }}</strong></li>
        <li>Unresolved venues — Expected from dry-run audit: <strong>{{ dryRunResult?.audit?.records ? unresolvedVenues : 0 }}</strong></li>
        <li>Blocked records — From dry-run preview: <strong>{{ dryRunResult?.records_blocked_from_reset ?? 0 }}</strong></li>
        <li>Skipped duplicate risk — From dry-run preview: <strong>{{ dryRunResult?.duplicate_risks ?? 0 }}</strong></li>
        <li>Venue extraction count: <strong>Not reported by current apply response</strong></li>
      </ul>
      <p class="hcrr-note">
        Verify now in Analyst Workspace tabs: Deliveries, Players, CPL Dashboard, and Case Studies.
      </p>
      <ul class="hcrr-links" data-testid="hcrr-verification-links">
        <li><a href="/analyst/workspace">Open Analyst Workspace</a> → Deliveries tab</li>
        <li><a href="/analyst/workspace">Open Analyst Workspace</a> → Players tab</li>
        <li><a href="/analyst/workspace">Open Analyst Workspace</a> → CPL Dashboard tab</li>
        <li><a href="/analyst/workspace">Open Analyst Workspace</a> → Case Studies tab</li>
        <li><a href="/analyst">Open Analyst Workspace home</a> for historical report context</li>
      </ul>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  applyCplResetReimport,
  getErrorMessage,
  runCplResetReimportDryRun,
  type HistoricalCplResetReimportApplyResponse,
  type HistoricalCplResetReimportDryRunResponse,
} from '@/services/api'

const CONFIRMATION_TEXT = 'I confirm this controlled CPL reset/reimport operation'

const loading = ref(false)
const loadingStep = ref<'dry-run' | 'apply'>('dry-run')
const selectedFile = ref<File | null>(null)
const seasonFilter = ref('')
const maxRecords = ref(1)
const error = ref<string | null>(null)
const dryRunResult = ref<HistoricalCplResetReimportDryRunResponse | null>(null)
const applyResult = ref<HistoricalCplResetReimportApplyResponse | null>(null)
const confirmApply = ref(false)
const confirmationPhrase = ref('')

const sourceMappingCounts = computed(() => {
  const counts = {
    exact_match: 0,
    likely_match: 0,
    no_match: 0,
  }
  for (const row of dryRunResult.value?.source_file_mapping ?? []) {
    if (row.match_confidence === 'exact_match') counts.exact_match += 1
    if (row.match_confidence === 'likely_match') counts.likely_match += 1
    if (row.match_confidence === 'no_match') counts.no_match += 1
  }
  return counts
})

const hasSafeSourceAction = computed(() =>
  (dryRunResult.value?.source_file_mapping ?? []).some(
    (row) =>
      !row.blocked_from_apply &&
      (row.match_confidence === 'exact_match' || row.match_confidence === 'likely_match'),
  ),
)

const hasSafeAction = computed(
  () => (dryRunResult.value?.records_safe_to_reset ?? 0) > 0 || hasSafeSourceAction.value,
)

const canApply = computed(
  () =>
    Boolean(selectedFile.value) &&
    Boolean(dryRunResult.value) &&
    hasSafeAction.value &&
    confirmApply.value &&
    confirmationPhrase.value.trim() === CONFIRMATION_TEXT &&
    !loading.value,
)

const unresolvedPlayers = computed(() =>
  (dryRunResult.value?.audit?.records ?? []).reduce(
    (sum, record) => sum + Number(record.players_without_source_ids ?? 0),
    0,
  ),
)

const unresolvedVenues = computed(() =>
  (dryRunResult.value?.audit?.records ?? []).reduce(
    (sum, record) => sum + (record.venue ? 0 : 1),
    0,
  ),
)

function invalidatePreviewState() {
  dryRunResult.value = null
  applyResult.value = null
  confirmApply.value = false
  confirmationPhrase.value = ''
  error.value = null
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
  invalidatePreviewState()
}

function friendlyError(err: unknown, fallback: string) {
  const message = getErrorMessage(err)
  if (!message || message.includes('Traceback') || message.trim().startsWith('{')) {
    return fallback
  }
  return message
}

async function runDryRun() {
  if (!selectedFile.value) return
  loading.value = true
  loadingStep.value = 'dry-run'
  error.value = null
  applyResult.value = null
  confirmApply.value = false
  confirmationPhrase.value = ''
  try {
    dryRunResult.value = await runCplResetReimportDryRun({
      file: selectedFile.value,
      max_batch_size: Math.max(1, Math.min(25, Number(maxRecords.value) || 1)),
      season: seasonFilter.value,
    })
  } catch (err) {
    dryRunResult.value = null
    error.value = friendlyError(err, 'Unable to run CPL reset/reimport dry-run.')
  } finally {
    loading.value = false
  }
}

async function applyResetReimport() {
  if (!selectedFile.value || !canApply.value || !dryRunResult.value) return
  loading.value = true
  loadingStep.value = 'apply'
  error.value = null
  try {
    const dryRunScope = dryRunResult.value.scope
    applyResult.value = await applyCplResetReimport({
      confirm: true,
      file: selectedFile.value,
      match_ids: dryRunScope.match_ids,
      batch_ids: dryRunScope.batch_ids,
      max_batch_size: dryRunScope.max_batch_size,
      season: seasonFilter.value,
    })
  } catch (err) {
    applyResult.value = null
    error.value = friendlyError(err, 'Unable to apply controlled CPL reset/reimport.')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.hcrr-panel {
  display: grid;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid var(--color-border-soft, #d6d9e0);
  border-radius: 0.75rem;
  background: var(--color-surface, #fff);
}

.hcrr-header,
.hcrr-section,
.hcrr-field {
  display: grid;
  gap: 0.5rem;
}

.hcrr-title,
.hcrr-section-title {
  margin: 0;
}

.hcrr-subtitle,
.hcrr-note {
  margin: 0;
  color: var(--color-text-muted, #5f677a);
}

.hcrr-warning,
.hcrr-error {
  margin: 0;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
}

.hcrr-warning {
  background: rgba(214, 47, 70, 0.12);
  color: #9f1730;
}

.hcrr-error {
  background: rgba(214, 47, 70, 0.12);
  color: #9f1730;
}

.hcrr-actions {
  display: flex;
}

.hcrr-btn {
  border: 1px solid transparent;
  border-radius: 0.5rem;
  padding: 0.65rem 1rem;
  font-weight: 600;
  cursor: pointer;
}

.hcrr-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.hcrr-btn--primary {
  background: #1f5eff;
  color: #fff;
}

.hcrr-btn--danger {
  background: #b4232f;
  color: #fff;
}

.hcrr-list {
  margin: 0;
  padding-left: 1.25rem;
}

.hcrr-confirm {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.hcrr-table-wrap {
  overflow-x: auto;
}

.hcrr-table {
  width: 100%;
  border-collapse: collapse;
}

.hcrr-table th,
.hcrr-table td {
  padding: 0.65rem 0.5rem;
  border-bottom: 1px solid var(--color-border-soft, #d6d9e0);
  text-align: left;
}

.hcrr-links {
  margin: 0;
  padding-left: 1.25rem;
}
</style>

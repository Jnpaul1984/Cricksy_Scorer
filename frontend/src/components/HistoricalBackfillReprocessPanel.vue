<template>
  <div class="hbr-panel">
    <div class="hbr-header">
      <h3 class="hbr-title">Historical Backfill Audit + Reprocess</h3>
      <p class="hbr-subtitle">
        Audit historical CPL imports and apply controlled, idempotent delivery rebuilds with provenance.
      </p>
    </div>

    <p class="hbr-warning-banner">
      Controlled apply only. Do not process all 402 matches at once.
    </p>

    <section class="hbr-section">
      <h4 class="hbr-section-title">Pre-audit scope controls</h4>
      <p class="hbr-idempotency-note">
        Start with 1 record. If successful, continue with 3–5, then 10, then 20–25.
      </p>
      <label class="hbr-field">
        Audit scope
        <select v-model="auditScopeMode" :disabled="loading" data-testid="hbr-audit-scope-mode">
          <option value="first_1">Audit first eligible record (safe default)</option>
          <option value="first_3_5">Audit first 3–5 eligible records</option>
          <option value="first_10">Audit first 10 eligible records</option>
          <option value="first_20_25">Audit first 20–25 eligible records</option>
          <option value="manual_batch_ids">Manual batch IDs</option>
          <option value="manual_match_ids">Manual match IDs</option>
        </select>
      </label>
      <label v-if="isRangeScopeMode" class="hbr-field">
        Records to audit
        <input
          v-model.number="rangeAuditCount"
          type="number"
          :min="rangeScopeBounds.min"
          :max="rangeScopeBounds.max"
          :disabled="loading"
          data-testid="hbr-audit-scope-count"
        />
      </label>
      <label v-if="isManualScopeMode" class="hbr-field">
        {{ auditScopeMode === 'manual_batch_ids' ? 'Batch IDs' : 'Match IDs' }}
        <textarea
          v-model="manualIdsInput"
          rows="4"
          :disabled="loading"
          data-testid="hbr-audit-manual-ids"
          placeholder="Paste IDs (one per line or comma-separated)"
        />
      </label>
      <p v-if="!auditSelectionValid" class="hbr-error" role="alert">
        Audit selection size must be 1, 3–5, 10, or 20–25.
      </p>
    </section>

    <div class="hbr-actions">
      <button
        type="button"
        class="hbr-btn hbr-btn--primary"
        data-testid="hbr-run-audit-btn"
        :disabled="!canRunAudit"
        @click="runAudit"
      >
        {{ loading && loadingStep === 'audit' ? 'Running dry-run audit…' : 'Run dry-run audit' }}
      </button>
    </div>

    <p v-if="error" class="hbr-error" role="alert">{{ error }}</p>

    <section v-if="auditResult" class="hbr-section">
      <h4 class="hbr-section-title">Dry-run audit summary</h4>
      <ul class="hbr-list">
        <li>Total selected records: {{ auditResult.selected_matches }}</li>
        <li>Eligible matches: {{ auditResult.eligible_matches }}</li>
        <li>Blocked matches: {{ auditResult.blocked_matches }}</li>
        <li>Metadata only: {{ getCompletenessCount('metadata_only') }}</li>
        <li>Innings totals only: {{ getCompletenessCount('innings_totals_only') }}</li>
        <li>Delivery data available: {{ getCompletenessCount('delivery_data_available') }}</li>
        <li>Wicket data available: {{ getCompletenessCount('wicket_data_available') }}</li>
        <li>Phase analytics available: {{ getCompletenessCount('phase_analytics_available') }}</li>
        <li>Single JSON imports: {{ getOriginCount('single_json_apply') }}</li>
        <li>Bulk ZIP imports: {{ getOriginCount('bulk_zip_apply') }}</li>
        <li>Unknown origin: {{ getOriginCount('unknown') }}</li>
        <li>Source JSON retained count: {{ sourceJsonRetainedCount }}</li>
        <li>Missing source JSON count: {{ missingSourceJsonCount }}</li>
        <li>registry.people available count: {{ registryPeopleAvailableCount }}</li>
        <li>Expected deliveries: {{ expectedTotals.deliveries }}</li>
        <li>Expected wickets: {{ expectedTotals.wickets }}</li>
        <li>Expected players: {{ expectedTotals.players }}</li>
      </ul>
    </section>

    <section v-if="auditResult" class="hbr-section">
      <h4 class="hbr-section-title">Audit records</h4>
      <div class="hbr-selection-row">
        <button
          type="button"
          class="hbr-btn hbr-btn--ghost"
          :disabled="loading || eligibleRecords.length === 0"
          @click="selectAllEligible"
        >
          Select all eligible
        </button>
        <button
          type="button"
          class="hbr-btn hbr-btn--ghost"
          :disabled="loading || selectedBatchIds.length === 0"
          @click="clearSelection"
        >
          Clear selection
        </button>
      </div>
      <div class="hbr-table-wrap">
        <table class="hbr-table">
          <thead>
            <tr>
              <th>Select</th>
              <th>Match ID</th>
              <th>Batch ID</th>
              <th>Import source</th>
              <th>Completeness</th>
              <th>Eligible</th>
              <th>Blocked reason</th>
              <th>Source JSON retained</th>
              <th>registry.people available</th>
              <th>Expected deliveries</th>
              <th>Expected wickets</th>
              <th>Expected players</th>
              <th>Duplicate delivery risk</th>
              <th>Apply deliveries previously run</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in auditResult.records" :key="record.batch_id">
              <td>
                <input
                  type="checkbox"
                  :checked="selectedBatchIds.includes(record.batch_id)"
                  :disabled="loading || !record.eligible"
                  @change="toggleRecord(record.batch_id, $event)"
                />
              </td>
              <td>{{ record.match_id }}</td>
              <td>{{ record.batch_id }}</td>
              <td>{{ record.import_source }}</td>
              <td>{{ record.completeness }}</td>
              <td>{{ record.eligible ? 'Yes' : 'No' }}</td>
              <td>{{ record.blocked_reason || '—' }}</td>
              <td>{{ record.source_json_retained ? 'Yes' : 'No' }}</td>
              <td>{{ record.registry_people_available ? 'Yes' : 'No' }}</td>
              <td>{{ record.expected_deliveries }}</td>
              <td>{{ record.expected_wickets }}</td>
              <td>{{ record.expected_players }}</td>
              <td>{{ record.duplicate_delivery_risk ? 'Yes' : 'No' }}</td>
              <td>{{ record.apply_deliveries_previously_run ? 'Yes' : 'No' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="missingSourceJsonCount > 0" class="hbr-warning-banner">
        Source JSON missing. This record requires a source-payload reattach workflow before delivery reprocess can run.
      </p>
      <p class="hbr-idempotency-note">
        Apply is idempotent and provenance-aware; reruns must not double-count deliveries.
      </p>
    </section>

    <section v-if="auditResult" class="hbr-section">
      <h4 class="hbr-section-title">Controlled apply</h4>
      <p>Selected records: <strong>{{ selectedBatchIds.length }}</strong></p>
      <p v-if="selectedBatchIds.length > 0 && !selectionSizeAllowed" class="hbr-error" role="alert">
        Selection size must be 1, 3–5, 10, or 20–25.
      </p>
      <label class="hbr-confirm">
        <input v-model="confirmApply" type="checkbox" :disabled="loading" />
        I confirm this controlled apply operation and understand provenance/idempotency requirements.
      </label>
      <button
        type="button"
        class="hbr-btn hbr-btn--primary"
        data-testid="hbr-apply-btn"
        :disabled="!canApply"
        @click="applySelected"
      >
        {{ loading && loadingStep === 'apply' ? 'Applying selected…' : `Apply selected (${selectedBatchIds.length})` }}
      </button>
    </section>

    <section v-if="applyResult" class="hbr-section">
      <h4 class="hbr-section-title">Apply response</h4>
      <ul class="hbr-list">
        <li>Status: {{ applyResult.status }}</li>
        <li>Processed matches: {{ applyResult.processed_matches }}</li>
        <li>Skipped matches: {{ applyResult.skipped_matches }}</li>
        <li>Failed matches: {{ applyResult.failed_matches }}</li>
        <li>Deliveries rebuilt: {{ applyResult.deliveries_rebuilt }}</li>
        <li>Wickets rebuilt: {{ applyResult.wickets_rebuilt }}</li>
        <li>Player mappings updated: {{ applyResult.player_mappings_updated }}</li>
        <li>Unresolved players: {{ applyResult.unresolved_players }}</li>
        <li>Unresolved venues: {{ applyResult.unresolved_venues }}</li>
        <li>Changed match IDs: {{ applyResult.changed_match_ids.length ? applyResult.changed_match_ids.join(', ') : 'None' }}</li>
      </ul>
      <h5 class="hbr-section-title">Completeness before/after (from apply results)</h5>
      <ul class="hbr-list">
        <li v-for="item in applyCompletenessSummary" :key="item.label">{{ item.label }}: {{ item.value }}</li>
      </ul>
      <h5 class="hbr-section-title">Post-apply verification checklist</h5>
      <ul class="hbr-list">
        <li>Open Players tab</li>
        <li>Open Deliveries tab</li>
        <li>Open CPL Dashboard</li>
        <li>Open Case Study</li>
        <li>Verify totals did not double-count after second run</li>
      </ul>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  historicalBackfillReprocessApply,
  historicalBackfillReprocessAudit,
  historicalImportListBatches,
  type HistoricalBackfillApplyResponse,
  type HistoricalBackfillAuditResponse,
} from '@/services/api'

const loading = ref(false)
const loadingStep = ref<'audit' | 'apply'>('audit')
const error = ref<string | null>(null)
const auditResult = ref<HistoricalBackfillAuditResponse | null>(null)
const applyResult = ref<HistoricalBackfillApplyResponse | null>(null)
const selectedBatchIds = ref<string[]>([])
const confirmApply = ref(false)
const auditScopeMode = ref<
  'first_1' | 'first_3_5' | 'first_10' | 'first_20_25' | 'manual_batch_ids' | 'manual_match_ids'
>('first_1')
const rangeAuditCount = ref(3)
const manualIdsInput = ref('')

const eligibleRecords = computed(() =>
  auditResult.value?.records.filter((record) => record.eligible) ?? [],
)

const sourceJsonRetainedCount = computed(() =>
  auditResult.value?.records.filter((record) => record.source_json_retained).length ?? 0,
)

const missingSourceJsonCount = computed(() =>
  auditResult.value?.records.filter((record) => record.missing_source_json).length ?? 0,
)

const registryPeopleAvailableCount = computed(() =>
  auditResult.value?.records.filter((record) => record.registry_people_available).length ?? 0,
)

const expectedTotals = computed(() => {
  const records = auditResult.value?.records ?? []
  return records.reduce(
    (totals, record) => ({
      deliveries: totals.deliveries + record.expected_deliveries,
      wickets: totals.wickets + record.expected_wickets,
      players: totals.players + record.expected_players,
    }),
    { deliveries: 0, wickets: 0, players: 0 },
  )
})

const selectionSizeAllowed = computed(() => {
  const size = selectedBatchIds.value.length
  return size === 1 || (size >= 3 && size <= 5) || size === 10 || (size >= 20 && size <= 25)
})

const canApply = computed(() =>
  Boolean(
    auditResult.value &&
    selectedBatchIds.value.length > 0 &&
    selectionSizeAllowed.value &&
    confirmApply.value &&
    !loading.value,
  ),
)

const isManualScopeMode = computed(
  () => auditScopeMode.value === 'manual_batch_ids' || auditScopeMode.value === 'manual_match_ids',
)

const isRangeScopeMode = computed(
  () => auditScopeMode.value === 'first_3_5' || auditScopeMode.value === 'first_20_25',
)

const rangeScopeBounds = computed(() => {
  if (auditScopeMode.value === 'first_3_5') return { min: 3, max: 5 }
  if (auditScopeMode.value === 'first_20_25') return { min: 20, max: 25 }
  return { min: 1, max: 1 }
})

const parsedManualIds = computed(() =>
  manualIdsInput.value
    .split(/[\n,]/)
    .map((id) => id.trim())
    .filter(Boolean),
)

const requestedAuditCount = computed(() => {
  if (auditScopeMode.value === 'first_1') return 1
  if (auditScopeMode.value === 'first_10') return 10
  if (auditScopeMode.value === 'first_3_5' || auditScopeMode.value === 'first_20_25') return rangeAuditCount.value
  return parsedManualIds.value.length
})

const auditSelectionValid = computed(() => {
  const size = requestedAuditCount.value
  return size === 1 || (size >= 3 && size <= 5) || size === 10 || (size >= 20 && size <= 25)
})

const requestedAuditMaxBatchSize = computed(() => {
  const size = requestedAuditCount.value
  if (size === 1) return 1
  if (size >= 3 && size <= 5) return 5
  if (size === 10) return 10
  if (size >= 20 && size <= 25) return 25
  return null
})

const canRunAudit = computed(
  () => !loading.value && auditSelectionValid.value && requestedAuditMaxBatchSize.value !== null,
)

const applyCompletenessSummary = computed(() => {
  const summary = new Map<string, number>()
  for (const result of applyResult.value?.results ?? []) {
    const key = `${result.completeness_before} → ${result.completeness_after}`
    summary.set(key, (summary.get(key) ?? 0) + 1)
  }
  return [...summary.entries()].map(([label, value]) => ({ label, value }))
})

function getCompletenessCount(key: string): number {
  return auditResult.value?.completeness_counts?.[key] ?? 0
}

function getOriginCount(key: string): number {
  return auditResult.value?.import_origin_counts?.[key] ?? 0
}

function normalizeErrorMessage(err: unknown): string {
  if (!(err instanceof Error)) return 'Historical backfill request failed.'
  try {
    const parsed = JSON.parse(err.message)
    if (typeof parsed === 'string') return parsed
    if (parsed && typeof parsed.detail === 'string') return parsed.detail
  } catch {
    // noop
  }
  return err.message || 'Historical backfill request failed.'
}

function clearSelection() {
  selectedBatchIds.value = []
  confirmApply.value = false
}

function selectAllEligible() {
  selectedBatchIds.value = eligibleRecords.value.map((record) => record.batch_id)
}

function toggleRecord(batchId: string, event: Event) {
  const target = event.target as HTMLInputElement | null
  const nextChecked = Boolean(target?.checked)
  const current = new Set(selectedBatchIds.value)
  if (nextChecked) current.add(batchId)
  else current.delete(batchId)
  selectedBatchIds.value = [...current]
}

async function runAudit() {
  if (!canRunAudit.value || requestedAuditMaxBatchSize.value === null) return
  loading.value = true
  loadingStep.value = 'audit'
  error.value = null
  applyResult.value = null
  clearSelection()
  try {
    const payload = {
      batch_ids: [] as string[],
      match_ids: [] as string[],
      max_batch_size: requestedAuditMaxBatchSize.value,
    }

    if (auditScopeMode.value === 'manual_batch_ids') {
      payload.batch_ids = parsedManualIds.value
    } else if (auditScopeMode.value === 'manual_match_ids') {
      payload.match_ids = parsedManualIds.value
    } else {
      const batches = await historicalImportListBatches(requestedAuditCount.value)
      payload.batch_ids = batches.slice(0, requestedAuditCount.value).map((batch) => batch.id)
      if (payload.batch_ids.length === 0) {
        throw new Error('No import batches available for the selected audit scope.')
      }
    }

    auditResult.value = await historicalBackfillReprocessAudit(payload)
  } catch (err) {
    error.value = normalizeErrorMessage(err)
  } finally {
    loading.value = false
  }
}

async function applySelected() {
  if (!canApply.value) return
  loading.value = true
  loadingStep.value = 'apply'
  error.value = null
  try {
    applyResult.value = await historicalBackfillReprocessApply({
      confirm: true,
      batch_ids: selectedBatchIds.value,
      max_batch_size: 25,
    })
  } catch (err) {
    error.value = normalizeErrorMessage(err)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.hbr-panel {
  display: grid;
  gap: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  background: var(--color-surface-raised, #f8fafc);
}

.hbr-title {
  margin: 0;
  font-size: var(--text-md);
}

.hbr-subtitle {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.hbr-section {
  display: grid;
  gap: var(--space-2);
}

.hbr-section-title {
  margin: 0;
  font-size: var(--text-sm);
}

.hbr-field {
  display: grid;
  gap: 0.35rem;
  font-size: var(--text-sm);
}

.hbr-field textarea,
.hbr-field select,
.hbr-field input[type='number'] {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 0.45rem 0.55rem;
  background: #fff;
}

.hbr-actions,
.hbr-selection-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.hbr-btn {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
}

.hbr-btn--primary {
  background: var(--color-primary);
  color: var(--color-primary-contrast, #fff);
  border-color: var(--color-primary);
}

.hbr-btn--ghost {
  background: transparent;
}

.hbr-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.hbr-warning-banner {
  margin: 0;
  color: var(--color-warning, #92400e);
  font-size: var(--text-sm);
}

.hbr-error {
  margin: 0;
  color: var(--color-danger, #b91c1c);
  font-size: var(--text-sm);
}

.hbr-idempotency-note {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.hbr-confirm {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
}

.hbr-list {
  margin: 0;
  padding-left: 1.1rem;
  display: grid;
  gap: 0.2rem;
}

.hbr-table-wrap {
  overflow-x: auto;
}

.hbr-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 1200px;
}

.hbr-table th,
.hbr-table td {
  border: 1px solid var(--color-border);
  padding: 0.4rem 0.5rem;
  font-size: 0.75rem;
  text-align: left;
  vertical-align: top;
}
</style>

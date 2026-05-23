<template>
  <div class="hmom-panel">
    <div class="hmom-header">
      <h3 class="hmom-title">Metadata-Only Historical Matches</h3>
      <p class="hmom-subtitle">
        Finder for historical imports with match metadata but no usable delivery rows.
      </p>
      <p class="hmom-count" data-testid="hmom-total-count">{{ total }} metadata-only matches found</p>
      <p class="hmom-note">
        Use the Clean Historical CPL Reset + Reimport panel below for controlled repair/reimport.
      </p>
    </div>

    <div class="hmom-controls">
      <label class="hmom-field">
        Competition
        <input v-model="competitionFilter" type="text" data-testid="hmom-competition-filter" />
      </label>
      <label class="hmom-field">
        Season
        <input v-model="seasonFilter" type="text" data-testid="hmom-season-filter" />
      </label>
      <button type="button" class="hmom-btn hmom-btn--primary" :disabled="loading" @click="refresh">
        {{ loading ? 'Refreshing…' : 'Refresh' }}
      </button>
    </div>

    <div class="hmom-actions">
      <button
        type="button"
        class="hmom-btn hmom-btn--ghost"
        data-testid="hmom-copy-match-ids-btn"
        :disabled="items.length === 0"
        @click="copyIds('match_id')"
      >
        Copy match IDs
      </button>
      <button
        type="button"
        class="hmom-btn hmom-btn--ghost"
        data-testid="hmom-copy-batch-ids-btn"
        :disabled="items.length === 0"
        @click="copyIds('batch_id')"
      >
        Copy batch IDs
      </button>
      <button
        type="button"
        class="hmom-btn hmom-btn--ghost"
        data-testid="hmom-export-csv-btn"
        :disabled="items.length === 0"
        @click="exportCsv"
      >
        Export CSV
      </button>
    </div>

    <p v-if="message" class="hmom-message">{{ message }}</p>
    <p v-if="error" class="hmom-error" role="alert">{{ error }}</p>

    <p v-if="!loading && items.length === 0" class="hmom-empty" data-testid="hmom-empty-state">
      No metadata-only historical matches found.
    </p>

    <div v-else class="hmom-table-wrap">
      <table class="hmom-table" data-testid="hmom-table">
        <thead>
          <tr>
            <th>Source file</th>
            <th>Teams</th>
            <th>Date</th>
            <th>Venue</th>
            <th>Competition</th>
            <th>Season</th>
            <th>Expected deliveries</th>
            <th>Actual deliveries</th>
            <th>Expected wickets</th>
            <th>Actual wickets</th>
            <th>Source payload available</th>
            <th>Recommended action</th>
            <th>Batch ID</th>
            <th>Match ID</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="`${item.batch_id}-${item.match_id}`">
            <td>{{ item.source_filename || '—' }}</td>
            <td>{{ [item.team_a, item.team_b].filter(Boolean).join(' vs ') || '—' }}</td>
            <td>{{ item.match_date || '—' }}</td>
            <td>{{ item.venue || '—' }}</td>
            <td>{{ item.competition || '—' }}</td>
            <td>{{ item.season || '—' }}</td>
            <td>{{ item.expected_deliveries ?? '—' }}</td>
            <td>{{ item.actual_deliveries }}</td>
            <td>{{ item.expected_wickets ?? '—' }}</td>
            <td>{{ item.actual_wickets }}</td>
            <td>{{ item.source_payload_available ? 'Yes' : 'No' }}</td>
            <td>{{ item.recommended_action }}</td>
            <td>{{ item.batch_id }}</td>
            <td>{{ item.match_id }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  historicalImportListMetadataOnlyMatches,
  type HistoricalMetadataOnlyMatchItem,
} from '@/services/api'

const loading = ref(false)
const error = ref('')
const message = ref('')
const total = ref(0)
const items = ref<HistoricalMetadataOnlyMatchItem[]>([])
const competitionFilter = ref('')
const seasonFilter = ref('')

async function refresh() {
  loading.value = true
  error.value = ''
  message.value = ''
  try {
    const response = await historicalImportListMetadataOnlyMatches({
      competition: competitionFilter.value,
      season: seasonFilter.value,
      limit: 100,
      offset: 0,
    })
    total.value = response.total
    items.value = response.items
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load metadata-only matches'
  } finally {
    loading.value = false
  }
}

async function copyIds(field: 'match_id' | 'batch_id') {
  const text = items.value.map((row) => row[field]).join('\n')
  if (!text) {
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    message.value = field === 'match_id' ? 'Match IDs copied.' : 'Batch IDs copied.'
  } catch {
    error.value = 'Clipboard copy failed'
  }
}

function exportCsv() {
  const header = [
    'source_file',
    'team_a',
    'team_b',
    'match_date',
    'venue',
    'competition',
    'season',
    'expected_deliveries',
    'actual_deliveries',
    'expected_wickets',
    'actual_wickets',
    'source_payload_available',
    'recommended_action',
    'batch_id',
    'match_id',
  ]
  const rows = items.value.map((item) =>
    [
      item.source_filename || '',
      item.team_a || '',
      item.team_b || '',
      item.match_date || '',
      item.venue || '',
      item.competition || '',
      item.season || '',
      item.expected_deliveries ?? '',
      item.actual_deliveries,
      item.expected_wickets ?? '',
      item.actual_wickets,
      item.source_payload_available ? 'true' : 'false',
      item.recommended_action,
      item.batch_id,
      item.match_id,
    ]
      .map((value) => `"${String(value).replace(/"/g, '""')}"`)
      .join(','),
  )
  const csv = [header.join(','), ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'metadata-only-historical-matches.csv'
  link.click()
  URL.revokeObjectURL(url)
  message.value = 'CSV export ready.'
}

onMounted(async () => {
  await refresh()
})
</script>

<style scoped>
.hmom-panel {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 1rem;
  background: #fff;
}

.hmom-title {
  margin: 0;
}

.hmom-subtitle,
.hmom-note,
.hmom-count {
  margin: 0.4rem 0 0;
  color: #4b5563;
}

.hmom-controls,
.hmom-actions {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
  margin-top: 0.9rem;
}

.hmom-field {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 220px;
}

.hmom-btn {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0.45rem 0.8rem;
  cursor: pointer;
  background: #fff;
}

.hmom-btn--primary {
  background: #1d4ed8;
  border-color: #1d4ed8;
  color: #fff;
}

.hmom-table-wrap {
  margin-top: 0.9rem;
  overflow-x: auto;
}

.hmom-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.hmom-table th,
.hmom-table td {
  border: 1px solid #e5e7eb;
  padding: 0.35rem 0.5rem;
  text-align: left;
  white-space: nowrap;
}

.hmom-error {
  color: #b91c1c;
  margin-top: 0.7rem;
}

.hmom-message,
.hmom-empty {
  margin-top: 0.7rem;
}
</style>

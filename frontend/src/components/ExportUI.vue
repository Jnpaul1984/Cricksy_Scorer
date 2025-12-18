<template>
  <div class="export-ui">
    <!-- Export Button -->
    <BaseButton
      size="sm"
      variant="ghost"
      class="export-trigger-btn"
      @click="showModal = true"
      title="Export data as CSV or JSON"
    >
      📥 Export
    </BaseButton>

    <!-- Export Modal -->
    <div v-if="showModal" class="export-modal-overlay" @click.self="closeModal">
      <BaseCard class="export-modal">
        <div class="export-header">
          <h3 class="export-title">Export Data</h3>
          <button class="export-close" @click="closeModal" title="Close">✕</button>
        </div>

        <div class="export-content">
          <!-- Format Selection -->
          <div class="export-section">
            <h4 class="export-section-title">Format</h4>
            <div class="export-format-options">
              <label v-for="fmt in formats" :key="fmt.value" class="format-option">
                <input v-model="exportFormat" type="radio" :value="fmt.value" />
                <span class="format-label">
                  <span class="format-icon">{{ fmt.icon }}</span>
                  <span class="format-text">
                    <span class="format-name">{{ fmt.label }}</span>
                    <span class="format-desc">{{ fmt.desc }}</span>
                  </span>
                </span>
              </label>
            </div>
          </div>

          <!-- Filters Section -->
          <div class="export-section">
            <h4 class="export-section-title">Filters (Optional)</h4>

            <!-- Date Range -->
            <div class="export-filter-group">
              <label class="filter-label">Date Range</label>
              <div class="date-range-inputs">
                <input
                  v-model="filters.dateFrom"
                  type="date"
                  class="filter-input"
                  placeholder="From"
                />
                <span class="date-separator">→</span>
                <input
                  v-model="filters.dateTo"
                  type="date"
                  class="filter-input"
                  placeholder="To"
                />
              </div>
            </div>

            <!-- Player Filter -->
            <div class="export-filter-group">
              <label class="filter-label">Player</label>
              <input
                v-model="filters.player"
                type="text"
                class="filter-input"
                placeholder="Search by name or ID..."
              />
            </div>

            <!-- Dismissal Type Filter -->
            <div class="export-filter-group">
              <label class="filter-label">Dismissal Type</label>
              <select v-model="filters.dismissalType" class="filter-input">
                <option value="">All Dismissals</option>
                <option value="bowled">Bowled</option>
                <option value="caught">Caught</option>
                <option value="lbw">LBW</option>
                <option value="stumped">Stumped</option>
                <option value="run_out">Run Out</option>
              </select>
            </div>

            <!-- Match Phase Filter -->
            <div class="export-filter-group">
              <label class="filter-label">Match Phase</label>
              <select v-model="filters.phase" class="filter-input">
                <option value="">All Phases</option>
                <option value="powerplay">Powerplay</option>
                <option value="middle">Middle Overs</option>
                <option value="death">Death Overs</option>
              </select>
            </div>

            <!-- Reset Filters Button -->
            <button class="reset-filters-btn" @click="resetFilters" title="Clear all filters">
              ↺ Reset Filters
            </button>
          </div>

          <!-- Preview Section -->
          <div class="export-section">
            <h4 class="export-section-title">Preview</h4>
            <div class="export-preview">
              <div class="preview-stat">
                <span class="preview-label">Rows to export:</span>
                <span class="preview-value">{{ estimatedRows }}</span>
              </div>
              <div class="preview-stat">
                <span class="preview-label">File size:</span>
                <span class="preview-value">~{{ estimatedFileSize }}</span>
              </div>
              <div class="preview-stat">
                <span class="preview-label">Format:</span>
                <span class="preview-value">{{ formatLabel }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Modal Actions -->
        <div class="export-actions">
          <BaseButton variant="ghost" size="sm" @click="closeModal">
            Cancel
          </BaseButton>
          <BaseButton variant="primary" size="sm" @click="downloadData" :loading="isExporting">
            <span v-if="isExporting">Preparing…</span>
            <span v-else>📥 Download</span>
          </BaseButton>
        </div>
      </BaseCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, ref, computed, reactive } from 'vue'
import { BaseButton, BaseCard } from '@/components'

const props = defineProps<{
  data?: any[]
}>()

const showModal = ref(false)
const isExporting = ref(false)

// Export format options
const formats = [
  {
    value: 'csv' as const,
    label: 'CSV',
    icon: '📊',
    desc: 'Comma-separated values, open in Excel',
  },
  {
    value: 'json' as const,
    label: 'JSON',
    icon: '{}',
    desc: 'JSON format for programmatic use',
  },
]

const exportFormat = ref<'csv' | 'json'>('csv')

// Filter state
const filters = reactive({
  dateFrom: '',
  dateTo: '',
  player: '',
  dismissalType: '',
  phase: '',
})

const resetFilters = () => {
  filters.dateFrom = ''
  filters.dateTo = ''
  filters.player = ''
  filters.dismissalType = ''
  filters.phase = ''
}

// Computed properties
const formatLabel = computed(() => {
  const fmt = formats.find((f) => f.value === exportFormat.value)
  return fmt?.label || 'Unknown'
})

// Estimate rows and file size based on filters
const estimatedRows = computed(() => {
  let count = props.data?.length || 0
  // Apply rough filter reduction
  if (filters.player) count = Math.floor(count * 0.5)
  if (filters.dismissalType) count = Math.floor(count * 0.7)
  if (filters.phase) count = Math.floor(count * 0.33)
  return Math.max(0, count)
})

const estimatedFileSize = computed(() => {
  const rowSize = exportFormat.value === 'csv' ? 120 : 180 // bytes per row
  const totalBytes = estimatedRows.value * rowSize
  if (totalBytes < 1024) return totalBytes + ' B'
  if (totalBytes < 1024 * 1024) return (totalBytes / 1024).toFixed(1) + ' KB'
  return (totalBytes / (1024 * 1024)).toFixed(1) + ' MB'
})

// Download handler
async function downloadData() {
  isExporting.value = true

  try {
    // Simulate data preparation
    await new Promise((resolve) => setTimeout(resolve, 500))

    // Generate mock data
    const exportData = generateExportData()

    // Create file and download
    if (exportFormat.value === 'csv') {
      downloadCSV(exportData)
    } else {
      downloadJSON(exportData)
    }

    // Close modal
    showModal.value = false
  } catch (error) {
    console.error('Export failed:', error)
    alert('Export failed. Please try again.')
  } finally {
    isExporting.value = false
  }
}

// Generate mock data based on filters
function generateExportData(): Record<string, any>[] {
  const sampleData = [
    {
      date: '2025-12-18',
      player: 'Player A',
      runs: 45,
      balls: 32,
      strikeRate: 140.6,
      dismissal: 'caught',
      phase: 'powerplay',
    },
    {
      date: '2025-12-18',
      player: 'Player B',
      runs: 28,
      balls: 21,
      strikeRate: 133.3,
      dismissal: 'not_out',
      phase: 'middle',
    },
    {
      date: '2025-12-17',
      player: 'Player C',
      runs: 67,
      balls: 48,
      strikeRate: 139.6,
      dismissal: 'bowled',
      phase: 'death',
    },
  ]

  return sampleData.filter((row) => {
    if (filters.dateFrom && row.date < filters.dateFrom) return false
    if (filters.dateTo && row.date > filters.dateTo) return false
    if (filters.player && !row.player.toLowerCase().includes(filters.player.toLowerCase())) return false
    if (filters.dismissalType && row.dismissal !== filters.dismissalType) return false
    if (filters.phase && row.phase !== filters.phase) return false
    return true
  })
}

// CSV download
function downloadCSV(data: Record<string, any>[]) {
  if (data.length === 0) {
    alert('No data to export with current filters')
    return
  }

  const headers = Object.keys(data[0])
  const csv = [
    headers.join(','),
    ...data.map((row) =>
      headers
        .map((h) => {
          const val = row[h]
          if (typeof val === 'string' && val.includes(',')) {
            return `"${val}"`
          }
          return val
        })
        .join(','),
    ),
  ].join('\n')

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  downloadBlob(blob, `export-${new Date().toISOString().split('T')[0]}.csv`)
}

// JSON download
function downloadJSON(data: Record<string, any>[]) {
  if (data.length === 0) {
    alert('No data to export with current filters')
    return
  }

  const json = JSON.stringify(data, null, 2)
  const blob = new Blob([json], { type: 'application/json;charset=utf-8;' })
  downloadBlob(blob, `export-${new Date().toISOString().split('T')[0]}.json`)
}

// Generic blob download
function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// Close modal
function closeModal() {
  showModal.value = false
}
</script>

<style scoped>
.export-ui {
  display: inline-block;
}

.export-trigger-btn {
  font-weight: 500;
}

/* Modal Overlay */
.export-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--space-4);
}

.export-modal {
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
}

/* Header */
.export-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.export-title {
  margin: 0;
  font-size: var(--h3-size);
  font-weight: var(--h3-weight);
  color: var(--color-text);
}

.export-close {
  background: none;
  border: none;
  font-size: var(--text-lg);
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0;
  transition: color 0.2s ease;
}

.export-close:hover {
  color: var(--color-text);
}

/* Content */
.export-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  margin-bottom: var(--space-6);
}

.export-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.export-section-title {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Format Options */
.export-format-options {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.format-option {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  cursor: pointer;
  transition: all 0.2s ease;
}

.format-option:hover {
  border-color: var(--color-primary);
  background: var(--color-bg-secondary);
}

.format-option input {
  margin-top: 2px;
  cursor: pointer;
  flex-shrink: 0;
}

.format-option input:checked {
  accent-color: var(--color-primary);
}

.format-label {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
}

.format-icon {
  font-size: var(--text-lg);
}

.format-text {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.format-name {
  font-weight: 600;
  color: var(--color-text);
  font-size: var(--text-sm);
}

.format-desc {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* Filter Group */
.export-filter-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.filter-label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text);
}

.filter-input {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: var(--text-sm);
  transition: border-color 0.2s ease;
}

.filter-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.date-range-inputs {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.filter-input {
  flex: 1;
}

.date-separator {
  color: var(--color-text-muted);
  font-weight: 500;
}

.reset-filters-btn {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.reset-filters-btn:hover {
  background: var(--color-bg-secondary);
  border-color: var(--color-primary);
}

/* Preview Section */
.export-preview {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.preview-stat {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  text-align: center;
}

.preview-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: 500;
}

.preview-value {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-text);
}

/* Actions */
.export-actions {
  display: flex;
  gap: var(--space-3);
  justify-content: flex-end;
}

/* Responsive */
@media (max-width: 640px) {
  .export-modal-overlay {
    padding: var(--space-2);
  }

  .export-modal {
    max-width: 100%;
  }

  .export-preview {
    grid-template-columns: 1fr;
  }

  .date-range-inputs {
    flex-direction: column;
  }

  .export-actions {
    flex-direction: column-reverse;
  }
}
</style>

<template>
  <div class="upload-review">
    <h1>Review Upload</h1>

    <div v-if="loading" class="loading">
      <p>Loading upload data...</p>
    </div>

    <div v-else-if="error" class="error-alert">
      <h3>Error</h3>
      <p>{{ error }}</p>
      <button @click="loadUpload">Retry</button>
    </div>

    <div v-else-if="upload" class="review-container">
      <!-- Upload Info -->
      <section class="upload-info-section">
        <h2>Upload Information</h2>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">File:</span>
            <span>{{ upload.filename }}</span>
          </div>
          <div class="info-item">
            <span class="label">Status:</span>
            <span :class="['status-badge', upload.status]">{{ upload.status }}</span>
          </div>
          <div class="info-item">
            <span class="label">Upload ID:</span>
            <span class="mono">{{ upload.upload_id }}</span>
          </div>
          <div v-if="upload.game_id" class="info-item">
            <span class="label">Game ID:</span>
            <span class="mono">{{ upload.game_id }}</span>
          </div>
        </div>
      </section>

      <!-- Parsed Preview -->
      <section v-if="parsedPreview" class="preview-section">
        <h2>Parsed Data Preview</h2>

        <!-- Confidence and Warnings -->
        <div class="confidence-card">
          <div class="confidence-meter">
            <span class="label">Confidence:</span>
            <div class="meter-bar">
              <div
                class="meter-fill"
                :style="{ width: `${parsedPreview.confidence * 100}%` }"
                :class="confidenceClass"
              ></div>
            </div>
            <span class="confidence-value">{{ (parsedPreview.confidence * 100).toFixed(0) }}%</span>
          </div>

          <div v-if="parsedPreview.warnings?.length" class="warnings">
            <h4>⚠️ Warnings:</h4>
            <ul>
              <li v-for="(warning, idx) in parsedPreview.warnings" :key="idx">{{ warning }}</li>
            </ul>
          </div>

          <div v-if="parsedPreview.validation_errors?.length" class="errors">
            <h4>❌ Validation Errors:</h4>
            <ul>
              <li v-for="(error, idx) in parsedPreview.validation_errors" :key="idx">{{ error }}</li>
            </ul>
          </div>
        </div>

        <!-- Metadata -->
        <div v-if="parsedPreview.metadata" class="metadata-section">
          <h3>Match Metadata</h3>
          <div class="metadata-grid">
            <div class="metadata-item">
              <span class="label">Match Type:</span>
              <span>{{ parsedPreview.metadata.match_type || 'Unknown' }}</span>
            </div>
            <div v-if="parsedPreview.metadata.total_runs" class="metadata-item">
              <span class="label">Total Runs:</span>
              <span>{{ parsedPreview.metadata.total_runs }}</span>
            </div>
            <div v-if="parsedPreview.metadata.total_wickets" class="metadata-item">
              <span class="label">Total Wickets:</span>
              <span>{{ parsedPreview.metadata.total_wickets }}</span>
            </div>
            <div v-if="parsedPreview.metadata.overs" class="metadata-item">
              <span class="label">Overs:</span>
              <span>{{ parsedPreview.metadata.overs }}</span>
            </div>
            <div v-if="parsedPreview.metadata.venue" class="metadata-item">
              <span class="label">Venue:</span>
              <span>{{ parsedPreview.metadata.venue }}</span>
            </div>
            <div v-if="parsedPreview.metadata.date" class="metadata-item">
              <span class="label">Date:</span>
              <span>{{ parsedPreview.metadata.date }}</span>
            </div>
          </div>
        </div>

        <!-- Teams -->
        <div v-if="parsedPreview.teams" class="teams-section">
          <h3>Teams</h3>
          <div class="teams-grid">
            <div class="team-item">
              <span class="label">Team A:</span>
              <span>{{ parsedPreview.teams.team_a || 'Not detected' }}</span>
            </div>
            <div class="team-item">
              <span class="label">Team B:</span>
              <span>{{ parsedPreview.teams.team_b || 'Not detected' }}</span>
            </div>
          </div>
        </div>

        <!-- Deliveries -->
        <div v-if="parsedPreview.deliveries?.length" class="deliveries-section">
          <h3>Deliveries ({{ parsedPreview.deliveries.length }})</h3>
          <div class="deliveries-table-container">
            <table class="deliveries-table">
              <thead>
                <tr>
                  <th>Over</th>
                  <th>Ball</th>
                  <th>Batsman</th>
                  <th>Runs</th>
                  <th>Extras</th>
                  <th>Wicket</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(delivery, idx) in parsedPreview.deliveries.slice(0, 50)" :key="idx">
                  <td>{{ delivery.over }}</td>
                  <td>{{ delivery.ball }}</td>
                  <td>{{ delivery.batsman || '-' }}</td>
                  <td>{{ delivery.runs }}</td>
                  <td>{{ delivery.extras || 0 }}</td>
                  <td>{{ delivery.wicket ? '✓' : '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="parsedPreview.deliveries.length > 50" class="truncated-note">
            Showing first 50 of {{ parsedPreview.deliveries.length }} deliveries
          </p>
        </div>

        <!-- Raw OCR (collapsible) -->
        <details class="raw-ocr-section">
          <summary>View Raw OCR Text</summary>
          <pre class="raw-ocr-text">{{ parsedPreview.raw_ocr }}</pre>
        </details>
      </section>

      <!-- Actions -->
      <section class="actions-section">
        <div class="warning-box">
          <h3>⚠️ Important</h3>
          <p>
            This is a PROTOTYPE OCR parser. Please carefully review all parsed data before applying.
            Human verification is required to ensure accuracy.
          </p>
        </div>

        <div class="confirm-checkbox">
          <label>
            <input type="checkbox" v-model="confirmApply" />
            <span>
              I have reviewed the parsed data and confirm it is accurate. I understand this will
              apply the data to the delivery ledger.
            </span>
          </label>
        </div>

        <div class="action-buttons">
          <button @click="handleApply" :disabled="!confirmApply || applying" class="apply-button">
            {{ applying ? 'Applying...' : 'Apply to Game' }}
          </button>
          <button @click="handleCancel" class="cancel-button">Cancel</button>
        </div>

        <div v-if="applyError" class="error-message">
          {{ applyError }}
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUploadStore, type Upload, type ParsedPreview } from '@/stores/uploadStore'

const router = useRouter()
const route = useRoute()
const uploadStore = useUploadStore()

const upload = ref<Upload | null>(null)
const parsedPreview = ref<ParsedPreview | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const confirmApply = ref(false)
const applying = ref(false)
const applyError = ref<string | null>(null)

const uploadId = computed(() => route.params.uploadId as string)

const confidenceClass = computed(() => {
  if (!parsedPreview.value) return ''
  const conf = parsedPreview.value.confidence
  if (conf >= 0.7) return 'high'
  if (conf >= 0.4) return 'medium'
  return 'low'
})

async function loadUpload() {
  loading.value = true
  error.value = null

  try {
    const data = await uploadStore.fetchUploadStatus(uploadId.value)
    upload.value = data
    parsedPreview.value = data.parsed_preview as ParsedPreview | null

    if (data.status !== 'parsed') {
      error.value = `Upload is in '${data.status}' state. Only 'parsed' uploads can be reviewed.`
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load upload'
  } finally {
    loading.value = false
  }
}

async function handleApply() {
  if (!confirmApply.value) return

  applying.value = true
  applyError.value = null

  try {
    await uploadStore.applyUpload(uploadId.value, true)
    
    // Navigate to game or success page
    if (upload.value?.game_id) {
      router.push(`/game/${upload.value.game_id}`)
    } else {
      router.push('/')
    }
  } catch (err) {
    applyError.value = err instanceof Error ? err.message : 'Failed to apply upload'
  } finally {
    applying.value = false
  }
}

function handleCancel() {
  router.back()
}

onMounted(() => {
  loadUpload()
})
</script>

<style scoped>
.upload-review {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.loading,
.error-alert {
  text-align: center;
  padding: 2rem;
}

.error-alert button {
  margin-top: 1rem;
  padding: 0.75rem 1.5rem;
  background: var(--primary-color, #007bff);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.review-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.upload-info-section,
.preview-section,
.actions-section {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

h2 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #333;
}

h3 {
  margin-top: 1rem;
  margin-bottom: 0.75rem;
  color: #555;
}

.info-grid,
.metadata-grid,
.teams-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.info-item,
.metadata-item,
.team-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.label {
  font-weight: 600;
  color: #666;
  font-size: 0.875rem;
}

.mono {
  font-family: monospace;
  font-size: 0.9em;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-weight: 500;
  font-size: 0.875rem;
}

.status-badge.parsed {
  background: #d4edda;
  color: #155724;
}

.confidence-card {
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.confidence-meter {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.meter-bar {
  flex: 1;
  height: 24px;
  background: #e9ecef;
  border-radius: 12px;
  overflow: hidden;
}

.meter-fill {
  height: 100%;
  transition: width 0.3s;
}

.meter-fill.high {
  background: #28a745;
}

.meter-fill.medium {
  background: #ffc107;
}

.meter-fill.low {
  background: #dc3545;
}

.confidence-value {
  font-weight: 600;
  min-width: 50px;
}

.warnings,
.errors {
  margin-top: 1rem;
}

.warnings h4 {
  color: #856404;
  margin-bottom: 0.5rem;
}

.errors h4 {
  color: #721c24;
  margin-bottom: 0.5rem;
}

.warnings ul,
.errors ul {
  margin: 0;
  padding-left: 1.5rem;
}

.deliveries-table-container {
  overflow-x: auto;
  margin: 1rem 0;
}

.deliveries-table {
  width: 100%;
  border-collapse: collapse;
}

.deliveries-table th,
.deliveries-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #dee2e6;
}

.deliveries-table th {
  background: #f8f9fa;
  font-weight: 600;
}

.truncated-note {
  font-style: italic;
  color: #666;
  margin-top: 0.5rem;
}

.raw-ocr-section {
  margin-top: 1.5rem;
}

.raw-ocr-section summary {
  cursor: pointer;
  font-weight: 600;
  padding: 0.5rem;
  background: #f8f9fa;
  border-radius: 4px;
}

.raw-ocr-text {
  margin-top: 1rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 4px;
  font-size: 0.875rem;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 400px;
  overflow-y: auto;
}

.warning-box {
  padding: 1rem;
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.warning-box h3 {
  margin-top: 0;
  color: #856404;
}

.confirm-checkbox {
  margin: 1rem 0;
}

.confirm-checkbox label {
  display: flex;
  align-items: start;
  gap: 0.75rem;
  cursor: pointer;
}

.confirm-checkbox input[type='checkbox'] {
  margin-top: 0.25rem;
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.action-buttons {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.apply-button,
.cancel-button {
  padding: 0.75rem 2rem;
  border: none;
  border-radius: 4px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.apply-button {
  background: var(--primary-color, #007bff);
  color: white;
}

.apply-button:hover:not(:disabled) {
  background: var(--primary-hover, #0056b3);
}

.apply-button:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.cancel-button {
  background: #6c757d;
  color: white;
}

.cancel-button:hover {
  background: #5a6268;
}

.error-message {
  margin-top: 1rem;
  padding: 1rem;
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  color: #721c24;
}
</style>

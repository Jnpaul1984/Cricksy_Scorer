<template>
  <div class="upload-review">
    <div v-if="loading" class="loading">
      <p>Loading upload details...</p>
    </div>

    <div v-else-if="error" class="error-message" role="alert">
      {{ error }}
      <router-link to="/uploads" class="btn">Back to Uploads</router-link>
    </div>

    <div v-else-if="upload" class="review-container">
      <header class="review-header">
        <h2>Review Upload: {{ upload.filename }}</h2>
        <span class="status-badge large" :class="upload.status">
          {{ upload.status }}
        </span>
      </header>

      <div class="metadata">
        <div class="meta-item">
          <strong>Upload ID:</strong> {{ upload.upload_id }}
        </div>
        <div class="meta-item">
          <strong>Created:</strong> {{ formatDate(upload.created_at) }}
        </div>
        <div v-if="upload.processed_at" class="meta-item">
          <strong>Processed:</strong> {{ formatDate(upload.processed_at) }}
        </div>
        <div v-if="upload.applied_at" class="meta-item">
          <strong>Applied:</strong> {{ formatDate(upload.applied_at) }}
        </div>
      </div>

      <div v-if="upload.status === 'processing'" class="processing-notice">
        <div class="spinner"></div>
        <p>Processing with OCR... This may take a few moments.</p>
        <p class="small">This page will automatically update when processing completes.</p>
      </div>

      <div v-if="upload.status === 'failed'" class="error-notice">
        <h3>Processing Failed</h3>
        <p v-if="upload.error_message">{{ upload.error_message }}</p>
        <p>You can try uploading the file again or enter data manually.</p>
        <div class="actions">
          <router-link to="/uploads" class="btn btn-primary">Upload Again</router-link>
        </div>
      </div>

      <div v-if="upload.status === 'parsed' && upload.parsed_data" class="parsed-data">
        <h3>Extracted Data (Please Verify)</h3>

        <div class="verification-warning">
          <strong>⚠️ Manual Verification Required</strong>
          <p>
            This data was extracted using AI/OCR and may contain errors.
            Please carefully review all fields before applying to the game ledger.
          </p>
        </div>

        <!-- Parse Notes -->
        <div v-if="upload.parsed_data.parse_notes" class="parse-notes">
          <h4>Notes:</h4>
          <ul>
            <li v-for="(note, idx) in upload.parsed_data.parse_notes" :key="idx">
              {{ note }}
            </li>
          </ul>
        </div>

        <!-- Teams -->
        <div v-if="upload.parsed_data.teams" class="data-section">
          <h4>Teams</h4>
          <div class="teams-grid">
            <div
              v-for="(team, idx) in upload.parsed_data.teams"
              :key="idx"
              class="team-card"
            >
              <strong>Team {{ idx + 1 }}:</strong> {{ team.name || 'Unknown' }}
            </div>
          </div>
        </div>

        <!-- Innings -->
        <div v-if="upload.parsed_data.innings" class="data-section">
          <h4>Innings</h4>
          <table>
            <thead>
              <tr>
                <th>Innings</th>
                <th>Runs</th>
                <th>Wickets</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(inning, idx) in upload.parsed_data.innings" :key="idx">
                <td>{{ idx + 1 }}</td>
                <td>{{ inning.runs }}</td>
                <td>{{ inning.wickets }}</td>
                <td>
                  <span
                    class="confidence-badge"
                    :class="inning.confidence || 'low'"
                  >
                    {{ inning.confidence || 'low' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Raw Lines (for manual review) -->
        <details v-if="upload.parsed_data.raw_lines" class="raw-data">
          <summary>Raw Extracted Text (for reference)</summary>
          <pre>{{ upload.parsed_data.raw_lines.join('\n') }}</pre>
        </details>

        <!-- Full JSON (for debugging) -->
        <details class="raw-data">
          <summary>Full Parsed Data (JSON)</summary>
          <pre>{{ JSON.stringify(upload.parsed_data, null, 2) }}</pre>
        </details>

        <!-- Actions -->
        <div class="review-actions">
          <button
            @click="handleApply"
            :disabled="applying"
            class="btn btn-primary"
          >
            {{ applying ? 'Applying...' : 'Confirm & Apply to Ledger' }}
          </button>
          <button
            @click="handleReject"
            :disabled="applying"
            class="btn btn-secondary"
          >
            Reject & Re-upload
          </button>
        </div>

        <p class="small terms">
          By clicking "Confirm & Apply", you confirm that you have reviewed the extracted
          data and it is accurate. This data will be permanently added to the game ledger.
        </p>
      </div>

      <div v-if="upload.status === 'applied'" class="success-notice">
        <h3>✓ Successfully Applied</h3>
        <p>This upload has been applied to the game ledger.</p>
        <div v-if="upload.game_id" class="actions">
          <router-link :to="`/games/${upload.game_id}`" class="btn btn-primary">
            View Game
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUploadStore } from '@/stores/uploadStore'
import type { Upload } from '@/stores/uploadStore'

const route = useRoute()
const router = useRouter()
const uploadStore = useUploadStore()

const upload = ref<Upload | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const applying = ref(false)
const pollInterval = ref<number | null>(null)

const uploadId = route.params.id as string

onMounted(async () => {
  await fetchUpload()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})

async function fetchUpload() {
  try {
    loading.value = true
    error.value = null
    upload.value = await uploadStore.fetchUploadStatus(uploadId)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load upload'
  } finally {
    loading.value = false
  }
}

function startPolling() {
  // Poll every 3 seconds if processing
  pollInterval.value = window.setInterval(async () => {
    if (upload.value && ['processing', 'uploaded'].includes(upload.value.status)) {
      await fetchUpload()
    } else {
      stopPolling()
    }
  }, 3000)
}

function stopPolling() {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
    pollInterval.value = null
  }
}

async function handleApply() {
  if (!upload.value) return

  const confirmed = confirm(
    'Are you sure you want to apply this data to the game ledger? ' +
      'Please ensure you have verified all extracted information.'
  )

  if (!confirmed) return

  try {
    applying.value = true
    await uploadStore.applyUpload(uploadId)
    upload.value = await uploadStore.fetchUploadStatus(uploadId)

    // Navigate to game if available
    if (upload.value.game_id) {
      setTimeout(() => {
        router.push(`/games/${upload.value!.game_id}`)
      }, 1500)
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to apply upload'
  } finally {
    applying.value = false
  }
}

function handleReject() {
  const confirmed = confirm(
    'Are you sure you want to reject this upload? ' +
      'You will need to upload the file again.'
  )

  if (confirmed) {
    // TODO: Implement reject endpoint
    router.push('/uploads')
  }
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleString()
}
</script>

<style scoped>
.upload-review {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem;
}

.loading {
  text-align: center;
  padding: 3rem;
}

.review-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid var(--pico-muted-border-color);
}

.status-badge {
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.9rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.large {
  font-size: 1rem;
  padding: 0.75rem 1.5rem;
}

.metadata {
  background: var(--pico-background-color);
  padding: 1rem;
  border-radius: var(--pico-border-radius);
  margin-bottom: 1.5rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.processing-notice {
  text-align: center;
  padding: 2rem;
  background: var(--pico-secondary-background);
  border-radius: var(--pico-border-radius);
  margin: 2rem 0;
}

.spinner {
  border: 4px solid var(--pico-muted-border-color);
  border-top: 4px solid var(--pico-primary);
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-notice,
.success-notice {
  padding: 2rem;
  border-radius: var(--pico-border-radius);
  margin: 2rem 0;
}

.error-notice {
  background: #f8d7da;
  color: #721c24;
}

.success-notice {
  background: #d4edda;
  color: #155724;
}

.verification-warning {
  background: #fff3cd;
  border: 2px solid #ffc107;
  border-radius: var(--pico-border-radius);
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.parse-notes {
  background: var(--pico-background-color);
  padding: 1rem;
  border-radius: var(--pico-border-radius);
  margin-bottom: 1.5rem;
}

.data-section {
  margin-bottom: 2rem;
}

.teams-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.team-card {
  background: var(--pico-background-color);
  padding: 1rem;
  border-radius: var(--pico-border-radius);
}

.confidence-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
}

.confidence-badge.high {
  background: #d4edda;
  color: #155724;
}

.confidence-badge.medium {
  background: #fff3cd;
  color: #856404;
}

.confidence-badge.low {
  background: #f8d7da;
  color: #721c24;
}

.raw-data {
  margin: 2rem 0;
  background: var(--pico-background-color);
  padding: 1rem;
  border-radius: var(--pico-border-radius);
}

.raw-data pre {
  margin-top: 1rem;
  font-size: 0.85rem;
  max-height: 300px;
  overflow-y: auto;
}

.review-actions {
  display: flex;
  gap: 1rem;
  margin: 2rem 0;
}

.terms {
  color: var(--pico-muted-color);
  font-style: italic;
}

.small {
  font-size: 0.9rem;
  margin-top: 0.5rem;
}

.actions {
  margin-top: 1rem;
}

/* Status badge colors */
.status-badge.pending {
  background: var(--pico-secondary-background);
  color: var(--pico-secondary);
}

.status-badge.uploaded,
.status-badge.processing {
  background: var(--pico-primary-background);
  color: var(--pico-primary);
}

.status-badge.parsed {
  background: #d4edda;
  color: #155724;
}

.status-badge.applied {
  background: #cce5ff;
  color: #004085;
}

.status-badge.failed,
.status-badge.rejected {
  background: #f8d7da;
  color: #721c24;
}
</style>

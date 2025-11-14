<template>
  <div class="upload-review">
    <h1>Review Scorecard</h1>

    <!-- Loading State -->
    <div v-if="loading" class="loading-section">
      <div class="spinner"></div>
      <p>Loading scorecard...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-section">
      <p class="error-message">{{ error }}</p>
      <button @click="fetchUpload" class="button button-secondary">Retry</button>
    </div>

    <!-- Upload Info -->
    <div v-else-if="upload" class="review-content">
      <section class="upload-info">
        <h2>Upload Information</h2>
        <div class="info-grid">
          <div><strong>Filename:</strong> {{ upload.filename }}</div>
          <div><strong>Status:</strong> <span :class="`status-${upload.status}`">{{ upload.status }}</span></div>
          <div><strong>Uploaded:</strong> {{ formatDate(upload.created_at) }}</div>
          <div v-if="upload.game_id"><strong>Game ID:</strong> {{ upload.game_id }}</div>
        </div>
      </section>

      <!-- Metadata -->
      <section v-if="parsedPreview?.metadata" class="metadata-section">
        <h3>Processing Details</h3>
        <div class="confidence-bar">
          <label>Confidence: {{ (parsedPreview.metadata.confidence * 100).toFixed(0) }}%</label>
          <div class="bar">
            <div
              class="fill"
              :style="{ width: `${parsedPreview.metadata.confidence * 100}%` }"
              :class="getConfidenceClass(parsedPreview.metadata.confidence)"
            ></div>
          </div>
        </div>

        <div v-if="parsedPreview.metadata.warnings && parsedPreview.metadata.warnings.length" class="warnings">
          <h4>Warnings:</h4>
          <ul>
            <li v-for="(warning, index) in parsedPreview.metadata.warnings" :key="index">
              {{ warning }}
            </li>
          </ul>
        </div>
      </section>

      <!-- Deliveries Table -->
      <section v-if="editableDeliveries.length" class="deliveries-section">
        <h3>Deliveries ({{ editableDeliveries.length }})</h3>
        <p class="instruction">Review and edit the parsed deliveries below. Click a cell to edit.</p>

        <div class="table-wrapper">
          <table class="deliveries-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Over</th>
                <th>Ball</th>
                <th>Batsman</th>
                <th>Bowler</th>
                <th>Runs</th>
                <th>Wicket</th>
                <th>Extra</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(delivery, index) in editableDeliveries" :key="index">
                <td>{{ index + 1 }}</td>
                <td>
                  <input
                    type="number"
                    v-model.number="delivery.over"
                    min="1"
                    class="table-input"
                  />
                </td>
                <td>
                  <input
                    type="number"
                    v-model.number="delivery.ball"
                    min="1"
                    max="6"
                    class="table-input"
                  />
                </td>
                <td>
                  <input
                    type="text"
                    v-model="delivery.batsman"
                    class="table-input"
                  />
                </td>
                <td>
                  <input
                    type="text"
                    v-model="delivery.bowler"
                    class="table-input"
                  />
                </td>
                <td>
                  <input
                    type="number"
                    v-model.number="delivery.runs"
                    min="0"
                    class="table-input"
                  />
                </td>
                <td>
                  <input
                    type="checkbox"
                    v-model="delivery.is_wicket"
                  />
                </td>
                <td>
                  <input
                    type="checkbox"
                    v-model="delivery.is_extra"
                  />
                </td>
                <td>
                  <button @click="removeDelivery(index)" class="button-icon" title="Delete">
                    ❌
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="table-actions">
          <button @click="addDelivery" class="button button-secondary">
            + Add Delivery
          </button>
        </div>
      </section>

      <!-- No Deliveries -->
      <section v-else class="no-deliveries">
        <p>No deliveries were parsed from the scorecard.</p>
        <button @click="addDelivery" class="button button-primary">
          Add Delivery Manually
        </button>
      </section>

      <!-- Actions -->
      <section class="actions-section">
        <div class="warning-box">
          <strong>⚠️ Important:</strong> Review all deliveries carefully before applying.
          OCR is not 100% accurate and errors may occur.
        </div>

        <div class="action-buttons">
          <button
            @click="applyChanges"
            class="button button-primary"
            :disabled="applying || !upload.game_id"
          >
            {{ applying ? 'Applying...' : 'Apply to Game' }}
          </button>
          <button
            @click="resetChanges"
            class="button button-secondary"
            :disabled="applying"
          >
            Reset Changes
          </button>
          <button
            @click="cancel"
            class="button button-secondary"
            :disabled="applying"
          >
            Cancel
          </button>
        </div>

        <p v-if="!upload.game_id" class="error-message">
          This upload is not associated with a game. Please associate it with a game before applying.
        </p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUploadStore, type Delivery, type ParsedPreview } from '../stores/uploadStore'

const route = useRoute()
const router = useRouter()
const uploadStore = useUploadStore()

const uploadId = computed(() => parseInt(route.params.id as string))
const loading = ref(false)
const applying = ref(false)
const error = ref<string | null>(null)
const editableDeliveries = ref<Delivery[]>([])

const upload = computed(() => uploadStore.uploads.get(uploadId.value))
const parsedPreview = computed(() => upload.value?.parsed_preview)

onMounted(async () => {
  await fetchUpload()
})

async function fetchUpload() {
  loading.value = true
  error.value = null

  try {
    await uploadStore.fetchUploadStatus(uploadId.value)
    
    // Initialize editable deliveries
    if (parsedPreview.value?.deliveries) {
      editableDeliveries.value = JSON.parse(
        JSON.stringify(parsedPreview.value.deliveries)
      )
    }
  } catch (err: any) {
    error.value = err.message || 'Failed to load upload'
  } finally {
    loading.value = false
  }
}

function getConfidenceClass(confidence: number): string {
  if (confidence >= 0.7) return 'high'
  if (confidence >= 0.4) return 'medium'
  return 'low'
}

function addDelivery() {
  const lastDelivery = editableDeliveries.value[editableDeliveries.value.length - 1]
  
  let nextOver = 1
  let nextBall = 1
  
  if (lastDelivery) {
    nextOver = lastDelivery.over
    nextBall = lastDelivery.ball + 1
    
    if (nextBall > 6) {
      nextBall = 1
      nextOver += 1
    }
  }

  editableDeliveries.value.push({
    over: nextOver,
    ball: nextBall,
    batsman: 'Unknown Batsman',
    bowler: 'Unknown Bowler',
    runs: 0,
    is_wicket: false,
    is_extra: false,
    extra_type: null
  })
}

function removeDelivery(index: number) {
  if (confirm('Are you sure you want to remove this delivery?')) {
    editableDeliveries.value.splice(index, 1)
  }
}

function resetChanges() {
  if (parsedPreview.value?.deliveries) {
    editableDeliveries.value = JSON.parse(
      JSON.stringify(parsedPreview.value.deliveries)
    )
  }
}

async function applyChanges() {
  if (!upload.value?.game_id) {
    error.value = 'Upload must be associated with a game'
    return
  }

  if (!confirm(`Apply ${editableDeliveries.value.length} deliveries to game ${upload.value.game_id}?`)) {
    return
  }

  applying.value = true
  error.value = null

  try {
    const editedPreview: ParsedPreview = {
      deliveries: editableDeliveries.value,
      metadata: parsedPreview.value?.metadata || {
        confidence: 0,
        parser: 'manual_edit'
      }
    }

    await uploadStore.applyUpload(uploadId.value, editedPreview)

    alert('Deliveries applied successfully!')
    router.push(`/game/${upload.value.game_id}`)
  } catch (err: any) {
    error.value = err.message || 'Failed to apply changes'
  } finally {
    applying.value = false
  }
}

function cancel() {
  router.back()
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString()
}
</script>

<style scoped>
.upload-review {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.loading-section {
  text-align: center;
  padding: 4rem 2rem;
}

.spinner {
  width: 50px;
  height: 50px;
  margin: 0 auto 1rem;
  border: 4px solid var(--pico-muted-border-color);
  border-top-color: var(--pico-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.review-content section {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: var(--pico-card-background-color);
  border-radius: 8px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.status-pending { color: var(--pico-muted-color); }
.status-processing { color: var(--pico-primary); }
.status-ready { color: var(--pico-ins-color); }
.status-failed { color: var(--pico-del-color); }

.confidence-bar {
  margin: 1rem 0;
}

.bar {
  height: 20px;
  background: var(--pico-muted-border-color);
  border-radius: 10px;
  overflow: hidden;
  margin-top: 0.5rem;
}

.fill {
  height: 100%;
  transition: width 0.3s ease;
}

.fill.high { background: var(--pico-ins-color); }
.fill.medium { background: orange; }
.fill.low { background: var(--pico-del-color); }

.warnings {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--pico-code-background-color);
  border-radius: 4px;
}

.warnings ul {
  margin: 0.5rem 0 0 1rem;
}

.instruction {
  color: var(--pico-muted-color);
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.table-wrapper {
  overflow-x: auto;
}

.deliveries-table {
  width: 100%;
  border-collapse: collapse;
}

.deliveries-table th,
.deliveries-table td {
  padding: 0.5rem;
  text-align: left;
  border-bottom: 1px solid var(--pico-muted-border-color);
}

.table-input {
  width: 100%;
  padding: 0.25rem;
  border: 1px solid var(--pico-muted-border-color);
  border-radius: 4px;
  background: var(--pico-background-color);
  color: var(--pico-color);
}

.button-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  padding: 0.25rem;
}

.table-actions {
  margin-top: 1rem;
}

.no-deliveries {
  text-align: center;
  padding: 2rem;
}

.warning-box {
  padding: 1rem;
  background: var(--pico-code-background-color);
  border-left: 4px solid orange;
  margin-bottom: 1rem;
}

.action-buttons {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.error-section,
.error-message {
  color: var(--pico-del-color);
}
</style>

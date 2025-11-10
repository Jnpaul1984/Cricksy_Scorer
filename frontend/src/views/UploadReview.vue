<template>
  <div class="upload-review">
    <h1>Review Uploaded Scorecard</h1>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Loading upload data...</p>
    </div>

    <div v-if="error" class="error-message" role="alert">
      <strong>Error:</strong> {{ error }}
    </div>

    <div v-if="upload && !loading" class="review-container">
      <!-- Upload metadata -->
      <div class="upload-info">
        <h2>Upload Information</h2>
        <div class="info-grid">
          <div class="info-item">
            <strong>Filename:</strong> {{ upload.filename }}
          </div>
          <div class="info-item">
            <strong>Status:</strong> 
            <span :class="'status-badge status-' + upload.status">
              {{ upload.status }}
            </span>
          </div>
          <div class="info-item">
            <strong>Uploaded:</strong> {{ formatDate(upload.created_at) }}
          </div>
          <div class="info-item">
            <strong>Deliveries Found:</strong> {{ deliveriesCount }}
          </div>
        </div>
      </div>

      <!-- Deliveries preview -->
      <div v-if="deliveries.length > 0" class="deliveries-section">
        <div class="section-header">
          <h2>Parsed Deliveries</h2>
          <p class="help-text">
            Review and edit the extracted deliveries below. Make any necessary corrections before applying to the game.
          </p>
        </div>

        <div class="table-container">
          <table class="deliveries-table">
            <thead>
              <tr>
                <th>Over</th>
                <th>Ball</th>
                <th>Bowler</th>
                <th>Batsman</th>
                <th>Runs</th>
                <th>Extras</th>
                <th>Wicket</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(delivery, index) in deliveries"
                :key="index"
                :class="{ editing: editingIndex === index }"
              >
                <td>
                  <input
                    v-if="editingIndex === index"
                    v-model.number="delivery.over"
                    type="number"
                    min="1"
                  />
                  <span v-else>{{ delivery.over }}</span>
                </td>
                <td>
                  <input
                    v-if="editingIndex === index"
                    v-model.number="delivery.ball"
                    type="number"
                    min="1"
                    max="6"
                  />
                  <span v-else>{{ delivery.ball }}</span>
                </td>
                <td>
                  <input
                    v-if="editingIndex === index"
                    v-model="delivery.bowler"
                    type="text"
                  />
                  <span v-else>{{ delivery.bowler }}</span>
                </td>
                <td>
                  <input
                    v-if="editingIndex === index"
                    v-model="delivery.batsman"
                    type="text"
                  />
                  <span v-else>{{ delivery.batsman }}</span>
                </td>
                <td>
                  <input
                    v-if="editingIndex === index"
                    v-model.number="delivery.runs"
                    type="number"
                    min="0"
                  />
                  <span v-else>{{ delivery.runs }}</span>
                </td>
                <td>
                  <input
                    v-if="editingIndex === index"
                    v-model.number="delivery.extras"
                    type="number"
                    min="0"
                  />
                  <span v-else>{{ delivery.extras }}</span>
                </td>
                <td>
                  <input
                    v-if="editingIndex === index"
                    v-model="delivery.is_wicket"
                    type="checkbox"
                  />
                  <span v-else>{{ delivery.is_wicket ? '✓' : '—' }}</span>
                </td>
                <td>
                  <button
                    v-if="editingIndex === index"
                    @click="saveEdit(index)"
                    class="btn-small btn-success"
                  >
                    Save
                  </button>
                  <button
                    v-else
                    @click="startEdit(index)"
                    class="btn-small btn-edit"
                  >
                    Edit
                  </button>
                  <button
                    @click="removeDelivery(index)"
                    class="btn-small btn-danger"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="actions-section">
          <div class="form-group">
            <label for="target-game-id">Target Game ID *</label>
            <input
              id="target-game-id"
              v-model="targetGameId"
              type="text"
              placeholder="Enter game ID to apply deliveries"
              required
            />
            <p class="help-text">
              Enter the ID of the game where these deliveries should be applied.
            </p>
          </div>

          <div class="button-group">
            <button
              @click="handleApply"
              :disabled="!canApply || isApplying"
              class="btn-primary"
            >
              {{ isApplying ? 'Applying...' : 'Apply to Game' }}
            </button>
            <button
              @click="goBack"
              class="btn-secondary"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>

      <div v-else class="no-deliveries">
        <p>No deliveries were extracted from this upload.</p>
        <button @click="goBack" class="btn-secondary">
          Go Back
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUploadStore, type Delivery } from '@/stores/uploadStore'

const route = useRoute()
const router = useRouter()
const uploadStore = useUploadStore()

// Refs
const loading = ref(true)
const error = ref<string | null>(null)
const editingIndex = ref<number | null>(null)
const targetGameId = ref<string>('')
const isApplying = ref(false)

// Computed
const uploadId = computed(() => route.params.uploadId as string)
const upload = computed(() => uploadStore.currentUpload)
const deliveries = computed(() => upload.value?.parsed_preview?.deliveries || [])
const deliveriesCount = computed(() => deliveries.value.length)
const canApply = computed(() => 
  deliveriesCount.value > 0 && targetGameId.value.trim() !== '' && !isApplying.value
)

// Methods
async function loadUpload() {
  loading.value = true
  error.value = null

  try {
    await uploadStore.getUploadStatus(uploadId.value)
  } catch (err: any) {
    error.value = err.message || 'Failed to load upload'
  } finally {
    loading.value = false
  }
}

function startEdit(index: number) {
  editingIndex.value = index
}

function saveEdit(index: number) {
  editingIndex.value = null
  // Deliveries are already updated via v-model
}

function removeDelivery(index: number) {
  if (confirm('Are you sure you want to remove this delivery?')) {
    deliveries.value.splice(index, 1)
  }
}

async function handleApply() {
  if (!canApply.value) return

  const confirmed = confirm(
    `Are you sure you want to apply ${deliveriesCount.value} deliveries to game ${targetGameId.value}?\n\n` +
    'This action will add these deliveries to the match ledger and cannot be easily undone.'
  )

  if (!confirmed) return

  isApplying.value = true
  error.value = null

  try {
    await uploadStore.applyToGame(uploadId.value, targetGameId.value)
    
    alert('Deliveries successfully applied to game!')
    
    // Navigate to game scoring view
    router.push({
      name: 'GameScoringView',
      params: { gameId: targetGameId.value }
    })
  } catch (err: any) {
    error.value = err.message || 'Failed to apply deliveries'
  } finally {
    isApplying.value = false
  }
}

function goBack() {
  router.back()
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleString()
}

// Lifecycle
onMounted(() => {
  loadUpload()
  
  // Pre-fill game ID if it was set during upload
  if (upload.value?.game_id) {
    targetGameId.value = upload.value.game_id
  }
})
</script>

<style scoped>
.upload-review {
  max-width: 1200px;
  margin: 2rem auto;
  padding: 2rem;
}

.loading {
  text-align: center;
  padding: 3rem;
}

.spinner {
  width: 50px;
  height: 50px;
  margin: 0 auto 1rem;
  border: 4px solid #f3f3f3;
  border-top: 4px solid var(--pico-primary-background, #0066cc);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  background-color: #fee;
  border: 1px solid #fcc;
  padding: 1rem;
  margin-bottom: 1rem;
  border-radius: 4px;
}

.upload-info {
  background: var(--pico-background-color, #fff);
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.info-item {
  padding: 0.5rem;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
}

.status-ready {
  background: #d4edda;
  color: #155724;
}

.status-processing {
  background: #fff3cd;
  color: #856404;
}

.status-failed {
  background: #f8d7da;
  color: #721c24;
}

.deliveries-section {
  background: var(--pico-background-color, #fff);
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.section-header {
  margin-bottom: 1.5rem;
}

.help-text {
  color: #666;
  font-size: 0.9rem;
  margin-top: 0.5rem;
}

.table-container {
  overflow-x: auto;
  margin-bottom: 2rem;
}

.deliveries-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.deliveries-table th {
  background: #f5f5f5;
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  border-bottom: 2px solid #ddd;
}

.deliveries-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #eee;
}

.deliveries-table tr.editing {
  background: #fffacd;
}

.deliveries-table input[type="number"],
.deliveries-table input[type="text"] {
  width: 100%;
  padding: 0.25rem 0.5rem;
  border: 1px solid #ccc;
  border-radius: 3px;
}

.deliveries-table input[type="checkbox"] {
  width: auto;
}

.btn-small {
  padding: 0.25rem 0.5rem;
  margin: 0 0.25rem;
  border: none;
  border-radius: 3px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-edit {
  background: #007bff;
  color: white;
}

.btn-edit:hover {
  background: #0056b3;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-success:hover {
  background: #218838;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-danger:hover {
  background: #c82333;
}

.actions-section {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 2px solid #eee;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.form-group input {
  width: 100%;
  max-width: 400px;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 1rem;
}

.button-group {
  display: flex;
  gap: 1rem;
}

.btn-primary,
.btn-secondary {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-primary {
  background: var(--pico-primary-background, #0066cc);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--pico-primary-hover, #0052a3);
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
}

.no-deliveries {
  text-align: center;
  padding: 3rem;
}

.no-deliveries p {
  margin-bottom: 1rem;
  color: #666;
}
</style>

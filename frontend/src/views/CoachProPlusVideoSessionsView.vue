<template>
  <div class="coach-pro-plus-video-sessions">
    <!-- Feature Gate: Not Coach Pro Plus -->
    <div v-if="!authStore.isCoachProPlus" class="feature-gate">
      <div class="upgrade-card">
        <h2>Unlock Video Sessions</h2>
        <p>
          Manage and analyze video recordings of coaching sessions with AI-powered insights.
          Available with Coach Pro Plus ($24.99/month).
        </p>
        <router-link to="/pricing" class="upgrade-button">
          Upgrade to Coach Pro Plus
        </router-link>
      </div>
    </div>

    <!-- Main Content: Coach Pro Plus Users -->
    <div v-else class="sessions-container">
      <header class="sessions-header">
        <h1>Video Sessions</h1>
        <p class="subtitle">
          Upload, manage, and analyze coaching session videos
        </p>
        <button class="btn-primary" @click="showCreateModal = true">
          + New Video Session
        </button>
      </header>

      <!-- Loading State -->
      <div v-if="loading" class="loading">
        <p>Loading sessions...</p>
      </div>

      <!-- Error State -->
      <div v-if="error" class="error-banner">
        <p>{{ error }}</p>
        <button @click="error = null" class="btn-close">Dismiss</button>
      </div>

      <!-- Empty State -->
      <div v-if="!loading && sessions.length === 0" class="empty-state">
        <p>No video sessions yet.</p>
        <p class="hint">Create your first video session to get started.</p>
        <button class="btn-primary" @click="showCreateModal = true">
          Create Session
        </button>
      </div>

      <!-- Sessions List -->
      <div v-if="!loading && sessions.length > 0" class="sessions-list">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="session-card"
          @click="selectSession(session.id)"
        >
          <div class="session-header">
            <h3>{{ session.title }}</h3>
            <span :class="['status-badge', `status-${session.status}`]">
              {{ session.status }}
            </span>
          </div>

          <div class="session-meta">
            <p v-if="session.player_ids.length > 0">
              <strong>Players:</strong> {{ session.player_ids.length }}
            </p>
            <p>
              <strong>Created:</strong> {{ formatDate(session.created_at) }}
            </p>
          </div>

          <div v-if="session.notes" class="session-notes">
            {{ session.notes }}
          </div>

          <div class="session-actions">
            <button class="btn-primary" @click.stop="openUploadModal(session.id)">
              📹 Upload & Analyze
            </button>
            <button class="btn-secondary" @click.stop="editSession(session.id)">
              Edit
            </button>
            <button class="btn-danger" @click.stop="deleteSession(session.id)">
              Delete
            </button>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="sessions.length > 0" class="pagination">
        <button
          :disabled="offset === 0"
          @click="previousPage"
          class="btn-pagination"
        >
          ← Previous
        </button>
        <span class="page-info">
          Page {{ currentPage }} (showing {{ sessions.length }} sessions)
        </span>
        <button @click="nextPage" class="btn-pagination">
          Next →
        </button>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <h2>{{ editingId ? 'Edit' : 'Create' }} Video Session</h2>

        <form @submit.prevent="submitForm">
          <div class="form-group">
            <label for="title">Session Title</label>
            <input
              id="title"
              v-model="formData.title"
              type="text"
              placeholder="e.g., Batting Technique - Session 1"
              required
            />
          </div>

          <div class="form-group">
            <label for="players">Player IDs (comma-separated)</label>
            <textarea
              id="players"
              v-model="playersText"
              placeholder="player1_id, player2_id"
              rows="3"
            ></textarea>
          </div>

          <div class="form-group">
            <label for="notes">Notes</label>
            <textarea
              id="notes"
              v-model="formData.notes"
              placeholder="Additional notes about this session..."
              rows="4"
            ></textarea>
          </div>

          <div class="modal-actions">
            <button type="submit" class="btn-primary">
              {{ editingId ? 'Save Changes' : 'Create Session' }}
            </button>
            <button type="button" class="btn-secondary" @click="closeModal">
              Cancel
            </button>
          </div>
        </form>

        <div class="modal-hint">
          <p>
            <strong>Note:</strong> Video upload is coming soon. For now, you can create
            sessions and add metadata. Video files will be added in the next update.
          </p>
        </div>
      </div>
    </div>

    <!-- Upload Video Modal -->
    <div v-if="showUploadModal" class="modal-overlay" @click="closeUploadModal">
      <div class="modal-content" @click.stop>
        <h2>Upload Video for Analysis</h2>

        <div v-if="videoStore.uploading" class="upload-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: videoStore.uploadProgress + '%' }"></div>
          </div>
          <p class="progress-text">
            {{ videoStore.uploadProgress }}% - {{ videoStore.uploading.status }}
          </p>
        </div>

        <form v-else @submit.prevent="handleVideoUpload">
          <div class="form-group">
            <label for="video-file">Select Video File</label>
            <input
              id="video-file"
              ref="fileInput"
              type="file"
              accept="video/mp4,video/quicktime,video/x-msvideo"
              required
              @change="onFileSelected"
            />
            <p class="file-hint">
              Supported: MP4, MOV, AVI (max 500MB)
            </p>
            <p v-if="selectedFile" class="file-selected">
              ✓ Selected: {{ selectedFile.name }} ({{ (selectedFile.size / 1024 / 1024).toFixed(1) }}MB)
            </p>
          </div>

          <div class="form-group">
            <label for="sample-fps">Sample FPS (frames per second)</label>
            <input
              id="sample-fps"
              v-model.number="uploadSettings.sampleFps"
              type="number"
              min="1"
              max="30"
              value="10"
            />
            <p class="setting-hint">
              Higher = more detailed analysis but slower processing (10 recommended)
            </p>
          </div>

          <div class="form-group checkbox">
            <label>
              <input
                v-model="uploadSettings.includeFrames"
                type="checkbox"
              />
              Include frame data in results
            </label>
            <p class="setting-hint">
              Stores individual frame analysis (increases storage)
            </p>
          </div>

          <div class="modal-actions">
            <button
              type="submit"
              class="btn-primary"
              :disabled="!selectedFile"
            >
              🚀 Upload & Analyze
            </button>
            <button type="button" class="btn-secondary" @click="closeUploadModal">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Results Modal -->
    <div v-if="showResultsModal && selectedJob" class="modal-overlay" @click="closeResultsModal">
      <div class="modal-content modal-large" @click.stop>
        <button class="modal-close-btn" @click="closeResultsModal">✕</button>
        <h2>Analysis Results</h2>

        <div v-if="selectedJob.status === 'completed' && selectedJob.results">
          <!-- Pose Summary -->
          <section class="results-section">
            <h3>📊 Pose Detection Summary</h3>
            <div class="metrics-grid">
              <div class="metric">
                <span class="metric-label">Total Frames</span>
                <span class="metric-value">{{ selectedJob.results.pose_summary.total_frames }}</span>
              </div>
              <div class="metric">
                <span class="metric-label">Sampled Frames</span>
                <span class="metric-value">{{ selectedJob.results.pose_summary.sampled_frames }}</span>
              </div>
              <div class="metric">
                <span class="metric-label">Detection Rate</span>
                <span class="metric-value">{{ (selectedJob.results.pose_summary.detection_rate_percent).toFixed(1) }}%</span>
              </div>
              <div class="metric">
                <span class="metric-label">Video FPS</span>
                <span class="metric-value">{{ selectedJob.results.pose_summary.video_fps.toFixed(1) }}</span>
              </div>
            </div>
          </section>

          <!-- Biomechanical Metrics -->
          <section class="results-section">
            <h3>💪 Biomechanical Metrics</h3>
            <div class="metrics-grid">
              <div class="metric" v-for="(value, key) in selectedJob.results.metrics" :key="key">
                <span class="metric-label">{{ formatMetricName(key) }}</span>
                <span class="metric-value">{{ typeof value === 'number' ? value.toFixed(2) : value }}</span>
              </div>
            </div>
          </section>

          <!-- Coaching Report -->
          <section class="results-section" v-if="selectedJob.results.report">
            <h3>📋 Coaching Report</h3>

            <div class="report-subsection">
              <h4>Summary</h4>
              <p>{{ selectedJob.results.report.summary }}</p>
            </div>

            <div class="report-subsection">
              <h4>🎯 Key Issues to Address</h4>
              <ul>
                <li v-for="(issue, idx) in selectedJob.results.report.key_issues" :key="idx">
                  {{ issue }}
                </li>
              </ul>
            </div>

            <div class="report-subsection">
              <h4>✨ Strength Areas</h4>
              <ul v-if="selectedJob.results.findings.strength_areas">
                <li v-for="(strength, idx) in selectedJob.results.findings.strength_areas" :key="idx">
                  {{ strength }}
                </li>
              </ul>
            </div>

            <div class="report-subsection">
              <h4>🏋️ Recommended Drills</h4>
              <div v-for="(drill, idx) in selectedJob.results.report.drills" :key="idx" class="drill-card">
                <h5>{{ drill.name }}</h5>
                <p>{{ drill.description }}</p>
                <p class="drill-meta">⏱️ {{ drill.duration_minutes }} minutes | Focus: {{ drill.focus_areas.join(', ') }}</p>
              </div>
            </div>

            <div class="report-subsection">
              <h4>📅 One-Week Training Plan</h4>
              <p class="training-plan">{{ selectedJob.results.report.one_week_plan }}</p>
            </div>
          </section>
        </div>

        <div v-else class="results-loading">
          <p>⏳ Analysis in progress...</p>
          <p class="status-text">Status: {{ selectedJob.status }}</p>
        </div>

        <div class="modal-actions">
          <button type="button" class="btn-secondary" @click="closeResultsModal">
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useAuthStore } from '@/stores/authStore'
import { useCoachPlusVideoStore } from '@/stores/coachPlusVideoStore'
import { ApiError } from '@/services/coachPlusVideoService'
import type { VideoAnalysisJob } from '@/services/coachPlusVideoService'

// ============================================================================
// State
// ============================================================================

const authStore = useAuthStore()
const videoStore = useCoachPlusVideoStore()

const sessions = ref<any[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const showCreateModal = ref(false)
const showUploadModal = ref(false)
const showResultsModal = ref(false)
const editingId = ref<string | null>(null)
const uploadingSessionId = ref<string | null>(null)

const selectedFile = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

const offset = ref(0)
const limit = ref(10)

const formData = ref({
  title: '',
  player_ids: [] as string[],
  notes: '',
})

const uploadSettings = ref({
  sampleFps: 10,
  includeFrames: false,
})

const playersText = ref('')

// Watch store errors and display them
watch(() => videoStore.error, (newError) => {
  if (newError) {
    error.value = newError
  }
})

// Watch for completed jobs and show results
const selectedJob = ref<VideoAnalysisJob | null>(null)

watch(() => videoStore.processingJobs, (jobs) => {
  // If we have a job that's completed, show results
  if (jobs.length === 0 && uploadingSessionId.value) {
    const completedJob = videoStore.jobStatusMap.get(videoStore.allJobs[0]?.id || '')
    if (completedJob && completedJob.status === 'completed') {
      selectedJob.value = completedJob
      showResultsModal.value = true
    }
  }
})

// ============================================================================
// Computed
// ============================================================================

const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1)

// ============================================================================
// Methods
// ============================================================================

async function fetchSessions() {
  loading.value = true
  error.value = null

  try {
    await videoStore.fetchSessions(limit.value, offset.value)
    sessions.value = videoStore.sessions
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load sessions'
    console.error(err)
  } finally {
    loading.value = false
  }
}

async function submitForm() {
  try {
    // Parse player IDs
    formData.value.player_ids = playersText.value
      .split(',')
      .map((id) => id.trim())
      .filter((id) => id.length > 0)

    if (!formData.value.title.trim()) {
      error.value = 'Session title is required'
      return
    }

    if (editingId.value) {
      // TODO: Update session via API
      console.log('Update session:', editingId.value, formData.value)
    } else {
      // Create new session via store
      const session = await videoStore.createSession(formData.value)
      if (!session) {
        error.value = videoStore.error || 'Failed to create session'
        return
      }
    }

    closeModal()
    await fetchSessions()
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Operation failed'
    error.value = msg
    console.error(err)
  }
}

function onFileSelected(event: Event) {
  const target = event.target as HTMLInputElement
  const files = target.files
  if (files && files.length > 0) {
    selectedFile.value = files[0]
  }
}

async function handleVideoUpload() {
  if (!selectedFile.value || !uploadingSessionId.value) {
    error.value = 'Please select a video file'
    return
  }

  // Reset results modal
  showResultsModal.value = false
  selectedJob.value = null

  try {
    // Start upload
    const jobId = await videoStore.startUpload(
      selectedFile.value,
      uploadingSessionId.value,
      uploadSettings.value.sampleFps,
      uploadSettings.value.includeFrames
    )

    if (!jobId) {
      error.value = videoStore.error || 'Failed to start upload'
      return
    }

    // Close upload modal
    closeUploadModal()

    // Watch for completion
    const checkCompletion = setInterval(() => {
      const job = videoStore.jobStatusMap.get(jobId)
      if (job && (job.status === 'completed' || job.status === 'failed')) {
        clearInterval(checkCompletion)
        selectedJob.value = job
        showResultsModal.value = true
      }
    }, 1000)
  } catch (err) {
    let msg = 'Upload failed'
    if (err instanceof ApiError) {
      if (err.isFeatureDisabled()) {
        msg = `Video upload feature is not enabled on your plan. ${err.detail || 'Please upgrade to use this feature.'}`
      } else if (err.isUnauthorized()) {
        msg = 'Your session expired. Please log in again.'
      } else {
        msg = err.detail || err.message
      }
    } else if (err instanceof Error) {
      msg = err.message
    }
    error.value = msg
    console.error(err)
  }
}

function openUploadModal(sessionId: string) {
  uploadingSessionId.value = sessionId
  selectedFile.value = null
  showUploadModal.value = true
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function closeUploadModal() {
  showUploadModal.value = false
  uploadingSessionId.value = null
  selectedFile.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function closeResultsModal() {
  showResultsModal.value = false
  selectedJob.value = null
}

function selectSession(sessionId: string) {
  console.log('Selected session:', sessionId)
  // TODO: Navigate to session detail view
}

function editSession(sessionId: string) {
  editingId.value = sessionId
  showCreateModal.value = true
}

async function deleteSession(sessionId: string) {
  if (!confirm('Are you sure you want to delete this session?')) {
    return
  }

  try {
    console.log('Delete session:', sessionId)
    // TODO: Delete via API
    await fetchSessions()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to delete session'
    console.error(err)
  }
}

function closeModal() {
  showCreateModal.value = false
  editingId.value = null
  formData.value = { title: '', player_ids: [], notes: '' }
  playersText.value = ''
}

function previousPage() {
  offset.value = Math.max(0, offset.value - limit.value)
  fetchSessions()
}

function nextPage() {
  offset.value += limit.value
  fetchSessions()
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatMetricName(key: string): string {
  return key
    .replace(/_/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

// ============================================================================
// Lifecycle
// ============================================================================

onMounted(() => {
  if (authStore.isCoachProPlus) {
    fetchSessions()
  }
})

onBeforeUnmount(() => {
  videoStore.cleanup()
})
</script>

<style scoped>
.coach-pro-plus-video-sessions {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

/* Feature Gate */
.feature-gate {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.upgrade-card {
  text-align: center;
  padding: 3rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px;
  max-width: 500px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}

.upgrade-card h2 {
  font-size: 1.75rem;
  margin-bottom: 1rem;
}

.upgrade-card p {
  font-size: 1rem;
  line-height: 1.6;
  margin-bottom: 2rem;
  opacity: 0.95;
}

.upgrade-button {
  display: inline-block;
  padding: 0.75rem 2rem;
  background: white;
  color: #667eea;
  text-decoration: none;
  border-radius: 6px;
  font-weight: bold;
  transition: transform 0.2s;
}

.upgrade-button:hover {
  transform: translateY(-2px);
}

/* Main Container */
.sessions-container {
  padding: 1rem;
}

.sessions-header {
  margin-bottom: 2rem;
}

.sessions-header h1 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #666;
  margin-bottom: 1.5rem;
}

/* Loading & Error */
.loading,
.error-banner {
  padding: 1.5rem;
  text-align: center;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.loading {
  background: #f0f0f0;
}

.error-banner {
  background: #fee;
  color: #c33;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.btn-close {
  background: none;
  border: none;
  color: #c33;
  cursor: pointer;
  font-weight: bold;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 3rem;
  background: #f9f9f9;
  border-radius: 8px;
  margin: 2rem 0;
}

.empty-state p {
  margin: 0.5rem 0;
  color: #666;
}

.hint {
  font-size: 0.95rem;
  color: #999;
}

/* Sessions List */
.sessions-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.session-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.session-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 1rem;
}

.session-header h3 {
  margin: 0;
  font-size: 1.1rem;
  flex: 1;
}

.status-badge {
  display: inline-block;
  padding: 0.35rem 0.75rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: bold;
  text-transform: uppercase;
  margin-left: 0.5rem;
}

.status-pending {
  background: #ffeaa7;
  color: #d63031;
}

.status-uploaded {
  background: #81ecec;
  color: #0984e3;
}

.status-processing {
  background: #dfe6e9;
  color: #2d3436;
}

.status-ready {
  background: #55efc4;
  color: #00b894;
}

.session-meta {
  font-size: 0.9rem;
  color: #666;
  margin-bottom: 1rem;
}

.session-meta p {
  margin: 0.3rem 0;
}

.session-notes {
  background: #f9f9f9;
  padding: 0.75rem;
  border-left: 3px solid #667eea;
  margin: 1rem 0;
  font-size: 0.9rem;
  color: #333;
}

.session-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.session-actions button {
  flex: 1;
  padding: 0.5rem;
  font-size: 0.85rem;
}

/* Buttons */
.btn-primary,
.btn-secondary,
.btn-danger,
.btn-pagination {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.2s;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover {
  background: #5568d3;
}

.btn-secondary {
  background: #e0e0e0;
  color: #333;
}

.btn-secondary:hover {
  background: #d0d0d0;
}

.btn-danger {
  background: #ff6b6b;
  color: white;
}

.btn-danger:hover {
  background: #ee5a52;
}

.btn-pagination {
  padding: 0.5rem 1rem;
  background: #f0f0f0;
  color: #333;
}

.btn-pagination:hover:not(:disabled) {
  background: #e0e0e0;
}

.btn-pagination:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #ddd;
}

.page-info {
  color: #666;
  font-size: 0.95rem;
}

/* Modal */
.modal-overlay {
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
}

.modal-content {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  position: relative;
}

.modal-large {
  max-width: 900px;
}

.modal-close-btn {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #999;
}

.modal-close-btn:hover {
  color: #333;
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  font-weight: bold;
  margin-bottom: 0.5rem;
  color: #333;
}

.form-group input[type="text"],
.form-group input[type="file"],
.form-group input[type="number"],
.form-group textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: inherit;
  font-size: 1rem;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-group input[type="checkbox"] {
  margin-right: 0.5rem;
}

.form-group.checkbox label {
  display: flex;
  align-items: center;
}

.file-hint,
.setting-hint {
  font-size: 0.85rem;
  color: #999;
  margin-top: 0.3rem;
}

.file-selected {
  color: #00b894;
  font-weight: bold;
}

.upload-progress {
  margin-bottom: 1.5rem;
}

.progress-bar {
  width: 100%;
  height: 30px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  font-size: 0.9rem;
  transition: width 0.3s ease;
}

.progress-text {
  margin-top: 0.5rem;
  text-align: center;
  color: #666;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
}

.modal-actions button {
  flex: 1;
}

/* Results Modal */
.results-loading {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.status-text {
  color: #999;
  font-size: 0.95rem;
}

.results-section {
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid #eee;
}

.results-section h3 {
  margin-top: 0;
  margin-bottom: 1.2rem;
  font-size: 1.3rem;
  color: #333;
}

.results-section h4 {
  margin: 1.2rem 0 0.8rem;
  font-size: 1.1rem;
  color: #555;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.metric {
  background: #f9f9f9;
  padding: 1rem;
  border-radius: 6px;
  text-align: center;
  border: 1px solid #eee;
}

.metric-label {
  display: block;
  font-size: 0.85rem;
  color: #999;
  margin-bottom: 0.3rem;
  font-weight: 500;
}

.metric-value {
  display: block;
  font-size: 1.5rem;
  font-weight: bold;
  color: #667eea;
}

.report-subsection {
  margin-bottom: 1.2rem;
}

.report-subsection ul {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}

.report-subsection li {
  margin: 0.3rem 0;
  color: #555;
}

.drill-card {
  background: #f9f9f9;
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 0.8rem;
  border-left: 3px solid #667eea;
}

.drill-card h5 {
  margin: 0 0 0.5rem;
  color: #333;
}

.drill-card p {
  margin: 0.3rem 0;
  color: #666;
  font-size: 0.95rem;
}

.drill-meta {
  color: #999;
  font-size: 0.85rem !important;
  margin-top: 0.5rem;
}

.training-plan {
  background: #f9f9f9;
  padding: 1rem;
  border-radius: 6px;
  line-height: 1.6;
  color: #555;
}

/* Responsive */
@media (max-width: 768px) {
  .coach-pro-plus-video-sessions {
    padding: 1rem;
  }

  .sessions-list {
    grid-template-columns: 1fr;
  }

  .sessions-header h1 {
    font-size: 1.5rem;
  }

  .modal-content {
    width: 95%;
  }

  .pagination {
    flex-direction: column;
    gap: 0.5rem;
  }

  .session-actions {
    flex-direction: column;
  }

  .session-actions button {
    width: 100%;
  }
}
</style>

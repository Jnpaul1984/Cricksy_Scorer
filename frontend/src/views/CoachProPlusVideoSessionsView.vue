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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useAuthStore } from '@/stores/authStore'
import { useCoachPlusVideoStore } from '@/stores/coachPlusVideoStore'

// ============================================================================
// Types
// ============================================================================

interface VideoSession {
  id: string
  coach_id: string
  title: string
  player_ids: string[]
  status: 'pending' | 'uploaded' | 'processing' | 'ready'
  notes?: string
  created_at: string
  updated_at: string
}

// ============================================================================
// State
// ============================================================================

const authStore = useAuthStore()

const sessions = ref<VideoSession[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const showCreateModal = ref(false)
const editingId = ref<string | null>(null)

const offset = ref(0)
const limit = ref(10)

const formData = ref({
  title: '',
  player_ids: [] as string[],
  notes: '',
})

const playersText = ref('')

// ============================================================================
// Computed Properties
// ============================================================================

const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1)

// ============================================================================
// Methods
// ============================================================================

async function fetchSessions() {
  loading.value = true
  error.value = null

  try {
    // TODO: Replace with actual API call
    // const response = await fetch(
    //   `/api/coaches/plus/sessions?limit=${limit.value}&offset=${offset.value}`,
    //   {
    //     headers: {
    //       'Authorization': `Bearer ${authStore.token}`,
    //     },
    //   }
    // )
    // sessions.value = await response.json()

    // Mock data for scaffolding
    sessions.value = [
      {
        id: 'mock-1',
        coach_id: authStore.userId,
        title: 'Batting Technique - Opener Training',
        player_ids: ['player1', 'player2'],
        status: 'ready',
        notes: 'Focus on front foot technique',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]
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
      // TODO: Update session
      console.log('Update session:', editingId.value, formData.value)
    } else {
      // TODO: Create session
      // const response = await fetch('/api/coaches/plus/sessions', {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json',
      //     'Authorization': `Bearer ${authStore.token}`,
      //   },
      //   body: JSON.stringify(formData.value),
      // })
      // if (!response.ok) throw new Error('Failed to create session')

      console.log('Create session:', formData.value)
    }

    closeModal()
    await fetchSessions()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Operation failed'
    console.error(err)
  }
}

function selectSession(sessionId: string) {
  // TODO: Navigate to session detail/edit view
  console.log('Selected session:', sessionId)
}

function editSession(sessionId: string) {
  // TODO: Load session data and open modal
  editingId.value = sessionId
  showCreateModal.value = true
}

async function deleteSession(sessionId: string) {
  if (!confirm('Are you sure you want to delete this session?')) {
    return
  }

  try {
    // TODO: Delete session
    // const response = await fetch(`/api/coaches/plus/sessions/${sessionId}`, {
    //   method: 'DELETE',
    //   headers: {
    //     'Authorization': `Bearer ${authStore.token}`,
    //   },
    // })
    // if (!response.ok) throw new Error('Failed to delete session')

    console.log('Delete session:', sessionId)
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

// ============================================================================
// Lifecycle
// ============================================================================

const videoStore = useCoachPlusVideoStore()

onMounted(() => {
  if (authStore.isCoachProPlus) {
    fetchSessions()
  }
})

onBeforeUnmount(() => {
  // Stop all polling intervals when leaving the page
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

.form-group input,
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

.modal-actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
}

.modal-actions button {
  flex: 1;
}

.modal-hint {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #f0f7ff;
  border-left: 3px solid #667eea;
  border-radius: 4px;
  color: #333;
  font-size: 0.9rem;
}

.modal-hint p {
  margin: 0;
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

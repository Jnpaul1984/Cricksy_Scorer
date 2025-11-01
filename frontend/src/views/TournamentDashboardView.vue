<template>
  <div class="tournament-dashboard">
    <div class="header">
      <h1>Tournament Dashboard</h1>
      <button @click="showCreateModal = true" class="btn-primary">Create Tournament</button>
    </div>

    <div v-if="loading" class="loading">Loading tournaments...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else class="tournaments-grid">
      <div
        v-for="tournament in tournaments"
        :key="tournament.id"
        class="tournament-card"
        @click="goToTournament(tournament.id)"
      >
        <h3>{{ tournament.name }}</h3>
        <p v-if="tournament.description" class="description">{{ tournament.description }}</p>
        <div class="meta">
          <span class="badge" :class="`status-${tournament.status}`">{{ tournament.status }}</span>
          <span class="type">{{ tournament.tournament_type }}</span>
        </div>
        <div v-if="tournament.start_date" class="dates">
          {{ formatDate(tournament.start_date) }}
          <span v-if="tournament.end_date"> - {{ formatDate(tournament.end_date) }}</span>
        </div>
        <div class="teams-count">{{ tournament.teams?.length || 0 }} teams</div>
      </div>

      <div v-if="tournaments.length === 0" class="empty-state">
        <p>No tournaments yet. Create your first tournament to get started!</p>
      </div>
    </div>

    <!-- Create Tournament Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <h2>Create Tournament</h2>
        <form @submit.prevent="createTournament">
          <div class="form-group">
            <label>Name *</label>
            <input v-model="newTournament.name" type="text" required placeholder="e.g., Premier League 2024" />
          </div>
          <div class="form-group">
            <label>Description</label>
            <textarea v-model="newTournament.description" placeholder="Tournament description"></textarea>
          </div>
          <div class="form-group">
            <label>Type</label>
            <select v-model="newTournament.tournament_type">
              <option value="league">League</option>
              <option value="knockout">Knockout</option>
              <option value="round-robin">Round Robin</option>
            </select>
          </div>
          <div class="form-group">
            <label>Start Date</label>
            <input v-model="newTournament.start_date" type="date" />
          </div>
          <div class="form-group">
            <label>End Date</label>
            <input v-model="newTournament.end_date" type="date" />
          </div>
          <div class="modal-actions">
            <button type="button" @click="showCreateModal = false" class="btn-secondary">Cancel</button>
            <button type="submit" class="btn-primary">Create</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import apiService from '@/utils/api'

const router = useRouter()
const tournaments = ref<any[]>([])
const loading = ref(true)
const error = ref('')
const showCreateModal = ref(false)
const newTournament = ref({
  name: '',
  description: '',
  tournament_type: 'league',
  start_date: '',
  end_date: '',
})

async function loadTournaments() {
  try {
    loading.value = true
    error.value = ''
    tournaments.value = await apiService.getTournaments()
  } catch (e: any) {
    error.value = e.message || 'Failed to load tournaments'
  } finally {
    loading.value = false
  }
}

async function createTournament() {
  try {
    const body = {
      name: newTournament.value.name,
      description: newTournament.value.description || null,
      tournament_type: newTournament.value.tournament_type,
      start_date: newTournament.value.start_date || null,
      end_date: newTournament.value.end_date || null,
    }
    const created = await apiService.createTournament(body)
    showCreateModal.value = false
    newTournament.value = {
      name: '',
      description: '',
      tournament_type: 'league',
      start_date: '',
      end_date: '',
    }
    await loadTournaments()
    router.push(`/tournaments/${created.id}`)
  } catch (e: any) {
    alert(e.message || 'Failed to create tournament')
  }
}

function goToTournament(id: string) {
  router.push(`/tournaments/${id}`)
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString()
}

onMounted(() => {
  loadTournaments()
})
</script>

<style scoped>
.tournament-dashboard {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.tournaments-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.tournament-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.tournament-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.tournament-card h3 {
  margin: 0 0 0.5rem 0;
  color: #333;
}

.description {
  color: #666;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.meta {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
}

.status-upcoming {
  background: #e3f2fd;
  color: #1976d2;
}

.status-ongoing {
  background: #e8f5e9;
  color: #388e3c;
}

.status-completed {
  background: #f5f5f5;
  color: #757575;
}

.type {
  color: #666;
  font-size: 0.9rem;
}

.dates {
  color: #666;
  font-size: 0.85rem;
  margin-top: 0.5rem;
}

.teams-count {
  color: #999;
  font-size: 0.85rem;
  margin-top: 0.5rem;
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 3rem;
  color: #999;
}

.loading,
.error {
  padding: 2rem;
  text-align: center;
}

.error {
  color: #d32f2f;
}

.btn-primary {
  background: #1976d2;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.btn-primary:hover {
  background: #1565c0;
}

.btn-secondary {
  background: #f5f5f5;
  color: #333;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

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

.modal {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal h2 {
  margin-top: 0;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #333;
  font-weight: 500;
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group textarea {
  min-height: 100px;
  resize: vertical;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}
</style>

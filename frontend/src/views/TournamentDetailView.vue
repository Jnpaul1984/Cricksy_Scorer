<template>
  <div class="tournament-detail">
    <div v-if="loading" class="loading">Loading tournament...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <template v-else-if="tournament">
      <div class="header">
        <button @click="goBack" class="btn-back">← Back</button>
        <div class="title-section">
          <h1>{{ tournament.name }}</h1>
          <span class="badge" :class="`status-${tournament.status}`">{{ tournament.status }}</span>
        </div>
      </div>

      <div class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab"
          @click="activeTab = tab"
          :class="{ active: activeTab === tab }"
          class="tab"
        >
          {{ tab }}
        </button>
      </div>

      <!-- Overview Tab -->
      <div v-if="activeTab === 'Overview'" class="tab-content">
        <div class="info-section">
          <p v-if="tournament.description">{{ tournament.description }}</p>
          <div class="meta-info">
            <div class="info-item">
              <strong>Type:</strong> {{ tournament.tournament_type }}
            </div>
            <div v-if="tournament.start_date" class="info-item">
              <strong>Start:</strong> {{ formatDate(tournament.start_date) }}
            </div>
            <div v-if="tournament.end_date" class="info-item">
              <strong>End:</strong> {{ formatDate(tournament.end_date) }}
            </div>
          </div>
        </div>
      </div>

      <!-- Teams Tab -->
      <div v-if="activeTab === 'Teams'" class="tab-content">
        <div class="section-header">
          <h2>Teams</h2>
          <button @click="showAddTeamModal = true" class="btn-primary">Add Team</button>
        </div>
        <div v-if="teams.length === 0" class="empty-state">
          No teams added yet
        </div>
        <div v-else class="teams-list">
          <div v-for="team in teams" :key="team.id" class="team-card">
            <h3>{{ team.team_name }}</h3>
            <div class="team-stats">
              <span>Played: {{ team.matches_played }}</span>
              <span>Won: {{ team.matches_won }}</span>
              <span>Lost: {{ team.matches_lost }}</span>
              <span>Points: {{ team.points }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Points Table Tab -->
      <div v-if="activeTab === 'Points Table'" class="tab-content">
        <h2>Points Table</h2>
        <div v-if="pointsTable.length === 0" class="empty-state">
          No standings yet
        </div>
        <table v-else class="points-table">
          <thead>
            <tr>
              <th>Pos</th>
              <th>Team</th>
              <th>P</th>
              <th>W</th>
              <th>L</th>
              <th>D</th>
              <th>Pts</th>
              <th>NRR</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(entry, index) in pointsTable" :key="index">
              <td>{{ index + 1 }}</td>
              <td>{{ entry.team_name }}</td>
              <td>{{ entry.matches_played }}</td>
              <td>{{ entry.matches_won }}</td>
              <td>{{ entry.matches_lost }}</td>
              <td>{{ entry.matches_drawn }}</td>
              <td><strong>{{ entry.points }}</strong></td>
              <td>{{ entry.net_run_rate.toFixed(3) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Fixtures Tab -->
      <div v-if="activeTab === 'Fixtures'" class="tab-content">
        <div class="section-header">
          <h2>Fixtures</h2>
          <button @click="showAddFixtureModal = true" class="btn-primary">Add Fixture</button>
        </div>
        <div v-if="fixtures.length === 0" class="empty-state">
          No fixtures scheduled
        </div>
        <div v-else class="fixtures-list">
          <div v-for="fixture in fixtures" :key="fixture.id" class="fixture-card">
            <div class="fixture-header">
              <span v-if="fixture.match_number" class="match-number">Match {{ fixture.match_number }}</span>
              <span class="badge" :class="`status-${fixture.status}`">{{ fixture.status }}</span>
            </div>
            <div class="fixture-teams">
              <span>{{ fixture.team_a_name }}</span>
              <span class="vs">vs</span>
              <span>{{ fixture.team_b_name }}</span>
            </div>
            <div v-if="fixture.venue" class="fixture-venue">📍 {{ fixture.venue }}</div>
            <div v-if="fixture.scheduled_date" class="fixture-date">
              {{ formatDateTime(fixture.scheduled_date) }}
            </div>
            <div v-if="fixture.result" class="fixture-result">{{ fixture.result }}</div>
          </div>
        </div>
      </div>

      <!-- Add Team Modal -->
      <div v-if="showAddTeamModal" class="modal-overlay" @click.self="showAddTeamModal = false">
        <div class="modal">
          <h2>Add Team</h2>
          <form @submit.prevent="addTeam">
            <div class="form-group">
              <label>Team Name *</label>
              <input v-model="newTeam.name" type="text" required placeholder="e.g., Mumbai Indians" />
            </div>
            <div class="modal-actions">
              <button type="button" @click="showAddTeamModal = false" class="btn-secondary">Cancel</button>
              <button type="submit" class="btn-primary">Add</button>
            </div>
          </form>
        </div>
      </div>

      <!-- Add Fixture Modal -->
      <div v-if="showAddFixtureModal" class="modal-overlay" @click.self="showAddFixtureModal = false">
        <div class="modal">
          <h2>Add Fixture</h2>
          <form @submit.prevent="addFixture">
            <div class="form-group">
              <label>Match Number</label>
              <input v-model.number="newFixture.match_number" type="number" placeholder="Optional" />
            </div>
            <div class="form-group">
              <label>Team A *</label>
              <input v-model="newFixture.team_a_name" type="text" required />
            </div>
            <div class="form-group">
              <label>Team B *</label>
              <input v-model="newFixture.team_b_name" type="text" required />
            </div>
            <div class="form-group">
              <label>Venue</label>
              <input v-model="newFixture.venue" type="text" placeholder="Stadium name" />
            </div>
            <div class="form-group">
              <label>Scheduled Date</label>
              <input v-model="newFixture.scheduled_date" type="datetime-local" />
            </div>
            <div class="modal-actions">
              <button type="button" @click="showAddFixtureModal = false" class="btn-secondary">Cancel</button>
              <button type="submit" class="btn-primary">Add</button>
            </div>
          </form>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import apiService from '@/utils/api'

const router = useRouter()
const route = useRoute()
const tournamentId = route.params.tournamentId as string

const tournament = ref<any>(null)
const teams = ref<any[]>([])
const pointsTable = ref<any[]>([])
const fixtures = ref<any[]>([])
const loading = ref(true)
const error = ref('')

const activeTab = ref('Overview')
const tabs = ['Overview', 'Teams', 'Points Table', 'Fixtures']

const showAddTeamModal = ref(false)
const newTeam = ref({ name: '' })

const showAddFixtureModal = ref(false)
const newFixture = ref({
  match_number: null as number | null,
  team_a_name: '',
  team_b_name: '',
  venue: '',
  scheduled_date: '',
})

async function loadTournament() {
  try {
    loading.value = true
    error.value = ''
    tournament.value = await apiService.getTournament(tournamentId)
    await Promise.all([loadTeams(), loadPointsTable(), loadFixtures()])
  } catch (e: any) {
    error.value = e.message || 'Failed to load tournament'
  } finally {
    loading.value = false
  }
}

async function loadTeams() {
  try {
    teams.value = await apiService.getTournamentTeams(tournamentId)
  } catch (e: any) {
    console.error('Failed to load teams:', e)
  }
}

async function loadPointsTable() {
  try {
    pointsTable.value = await apiService.getPointsTable(tournamentId)
  } catch (e: any) {
    console.error('Failed to load points table:', e)
  }
}

async function loadFixtures() {
  try {
    fixtures.value = await apiService.getTournamentFixtures(tournamentId)
  } catch (e: any) {
    console.error('Failed to load fixtures:', e)
  }
}

async function addTeam() {
  try {
    await apiService.addTeamToTournament(tournamentId, {
      team_name: newTeam.value.name,
      team_data: {},
    })
    showAddTeamModal.value = false
    newTeam.value = { name: '' }
    await Promise.all([loadTeams(), loadPointsTable()])
  } catch (e: any) {
    alert(e.message || 'Failed to add team')
  }
}

async function addFixture() {
  try {
    const body = {
      tournament_id: tournamentId,
      match_number: newFixture.value.match_number || null,
      team_a_name: newFixture.value.team_a_name,
      team_b_name: newFixture.value.team_b_name,
      venue: newFixture.value.venue || null,
      scheduled_date: newFixture.value.scheduled_date || null,
    }
    await apiService.createFixture(body)
    showAddFixtureModal.value = false
    newFixture.value = {
      match_number: null,
      team_a_name: '',
      team_b_name: '',
      venue: '',
      scheduled_date: '',
    }
    await loadFixtures()
  } catch (e: any) {
    alert(e.message || 'Failed to add fixture')
  }
}

function goBack() {
  router.push('/tournaments')
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString()
}

function formatDateTime(dateStr: string) {
  return new Date(dateStr).toLocaleString()
}

onMounted(() => {
  loadTournament()
})
</script>

<style scoped>
.tournament-detail {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  margin-bottom: 2rem;
}

.btn-back {
  background: none;
  border: none;
  color: #1976d2;
  cursor: pointer;
  font-size: 1rem;
  padding: 0.5rem 0;
  margin-bottom: 1rem;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.title-section h1 {
  margin: 0;
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

.status-scheduled {
  background: #fff3e0;
  color: #f57c00;
}

.status-in_progress {
  background: #e8f5e9;
  color: #388e3c;
}

.status-cancelled {
  background: #ffebee;
  color: #c62828;
}

.tabs {
  display: flex;
  gap: 0.5rem;
  border-bottom: 2px solid #e0e0e0;
  margin-bottom: 2rem;
}

.tab {
  background: none;
  border: none;
  padding: 1rem 1.5rem;
  cursor: pointer;
  font-size: 1rem;
  color: #666;
  position: relative;
}

.tab.active {
  color: #1976d2;
  font-weight: 500;
}

.tab.active::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  right: 0;
  height: 2px;
  background: #1976d2;
}

.tab-content {
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-header h2 {
  margin: 0;
}

.info-section {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.5rem;
}

.meta-info {
  display: flex;
  gap: 2rem;
  margin-top: 1rem;
}

.info-item {
  color: #666;
}

.teams-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
}

.team-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1rem;
}

.team-card h3 {
  margin: 0 0 1rem 0;
}

.team-stats {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  color: #666;
  font-size: 0.9rem;
}

.points-table {
  width: 100%;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  border-collapse: collapse;
  overflow: hidden;
}

.points-table th,
.points-table td {
  padding: 1rem;
  text-align: left;
}

.points-table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #333;
}

.points-table tbody tr:hover {
  background: #f9f9f9;
}

.points-table tbody tr {
  border-top: 1px solid #e0e0e0;
}

.fixtures-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.fixture-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.5rem;
}

.fixture-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.match-number {
  font-weight: 600;
  color: #666;
}

.fixture-teams {
  display: flex;
  align-items: center;
  gap: 1rem;
  font-size: 1.1rem;
  font-weight: 500;
  margin-bottom: 0.5rem;
}

.vs {
  color: #999;
  font-size: 0.9rem;
}

.fixture-venue,
.fixture-date {
  color: #666;
  font-size: 0.9rem;
  margin-top: 0.5rem;
}

.fixture-result {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: #f5f5f5;
  border-radius: 4px;
  font-size: 0.9rem;
}

.empty-state {
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
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}
</style>

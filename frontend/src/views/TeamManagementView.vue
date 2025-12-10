<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

import TeamFormModal from '@/components/TeamFormModal.vue'
import type { Team, Player, Coach } from '@/components/TeamFormModal.vue'
import { API_BASE, getStoredToken } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'

const auth = useAuthStore()

// State
const teams = ref<Team[]>([])
const availablePlayers = ref<Player[]>([])
const availableCoaches = ref<Coach[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const showTeamModal = ref(false)
const editingTeam = ref<Team | null>(null)

// Auth checks
const isLoggedIn = computed(() => !!auth.token)
const canManageTeams = computed(() => {
  const role = auth.role?.toLowerCase() || ''
  return ['org_pro', 'superuser', 'coach_pro'].includes(role)
})

const managementHint = computed(() => {
  if (!isLoggedIn.value) return 'Sign in to manage teams'
  if (!canManageTeams.value) return 'Requires Org Pro, Coach Pro, or Superuser role'
  return ''
})

// API functions
async function fetchTeams() {
  loading.value = true
  error.value = null
  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    const token = getStoredToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const res = await fetch(`${API_BASE}/api/teams`, { headers })
    if (!res.ok) {
      if (res.status === 401) {
        // Return empty for unauthenticated
        teams.value = []
        return
      }
      throw new Error(`Failed to fetch teams: ${res.statusText}`)
    }
    teams.value = await res.json()
  } catch (err: any) {
    error.value = err.message || 'Failed to load teams'
    console.error('Error fetching teams:', err)
  } finally {
    loading.value = false
  }
}

async function saveTeam(team: Team) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getStoredToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  try {
    const isNew = !team.id
    const url = isNew ? `${API_BASE}/api/teams` : `${API_BASE}/api/teams/${team.id}`
    const method = isNew ? 'POST' : 'PUT'

    const res = await fetch(url, {
      method,
      headers,
      body: JSON.stringify(team)
    })

    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || `Failed to save team: ${res.statusText}`)
    }

    await fetchTeams()
  } catch (err: any) {
    error.value = err.message || 'Failed to save team'
    console.error('Error saving team:', err)
  }
}

async function deleteTeam(team: Team) {
  if (!confirm(`Are you sure you want to delete "${team.name}"?`)) return

  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getStoredToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  try {
    const res = await fetch(`${API_BASE}/api/teams/${team.id}`, {
      method: 'DELETE',
      headers
    })

    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || `Failed to delete team: ${res.statusText}`)
    }

    await fetchTeams()
  } catch (err: any) {
    error.value = err.message || 'Failed to delete team'
    console.error('Error deleting team:', err)
  }
}

// Actions
function openCreateModal() {
  editingTeam.value = null
  showTeamModal.value = true
}

function openEditModal(team: Team) {
  editingTeam.value = { ...team }
  showTeamModal.value = true
}

function handleTeamSaved(team: Team) {
  saveTeam(team)
}

// Fetch available players for the multi-select
async function fetchAvailablePlayers() {
  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    const token = getStoredToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const res = await fetch(`${API_BASE}/api/players`, { headers })
    if (res.ok) {
      const data = await res.json()
      availablePlayers.value = data.map((p: any) => ({
        id: p.player_id || p.id,
        name: p.player_name || p.name
      }))
    }
  } catch (err) {
    console.warn('Could not fetch players:', err)
  }
}

// Fetch available coaches for the select
async function fetchAvailableCoaches() {
  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    const token = getStoredToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    // Fetch users with coach_pro role
    const res = await fetch(`${API_BASE}/api/users?role=coach_pro`, { headers })
    if (res.ok) {
      const data = await res.json()
      availableCoaches.value = data.map((u: any) => ({
        id: u.id,
        name: u.username || u.email || u.id
      }))
    }
  } catch (err) {
    console.warn('Could not fetch coaches:', err)
  }
}

onMounted(() => {
  fetchTeams()
  fetchAvailablePlayers()
  fetchAvailableCoaches()
})
</script>

<template>
  <div class="team-management">
    <!-- Auth banner -->
    <div v-if="!isLoggedIn" class="team-banner info">
      View-only mode. Sign in with an Org Pro or Coach Pro account to manage teams.
      <RouterLink to="/login" class="link-inline">Sign in</RouterLink>
    </div>
    <div v-else-if="!canManageTeams" class="team-banner warn">
      Team management requires Org Pro, Coach Pro, or Superuser role.
    </div>
    <div v-else class="team-banner success">
      Managing teams as {{ auth.role || 'org_pro' }}.
    </div>

    <!-- Header -->
    <div class="header">
      <h1>Team Management</h1>
      <div class="header-actions">
        <button
          class="btn-primary"
          :disabled="!canManageTeams"
          :title="!canManageTeams ? managementHint : 'Create a new team'"
          @click="openCreateModal"
        >
          + Create Team
        </button>
        <small v-if="!canManageTeams && isLoggedIn" class="hint-inline">
          {{ managementHint }}
        </small>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading">
      <div class="spinner" />
      Loading teams...
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error-banner">
      {{ error }}
      <button class="btn-link" @click="fetchTeams">Retry</button>
    </div>

    <!-- Teams grid -->
    <div v-else class="teams-grid">
      <div
        v-for="team in teams"
        :key="team.id"
        class="team-card"
      >
        <div class="card-header">
          <h3 class="team-name">{{ team.name }}</h3>
          <div v-if="canManageTeams" class="card-actions">
            <button
              class="btn-icon"
              title="Edit team"
              @click="openEditModal(team)"
            >
              ✏️
            </button>
            <button
              class="btn-icon btn-icon-danger"
              title="Delete team"
              @click="deleteTeam(team)"
            >
              🗑️
            </button>
          </div>
        </div>

        <div class="card-body">
          <!-- Home Ground -->
          <div v-if="team.home_ground" class="stat-row">
            <span class="stat-icon">🏟️</span>
            <span class="stat-label">Home Ground</span>
            <span class="stat-value">{{ team.home_ground }}</span>
          </div>

          <!-- Season -->
          <div v-if="team.season" class="stat-row">
            <span class="stat-icon">📅</span>
            <span class="stat-label">Season</span>
            <span class="stat-value">{{ team.season }}</span>
          </div>

          <!-- Players count -->
          <div class="stat-row">
            <span class="stat-icon">👥</span>
            <span class="stat-label">Players</span>
            <span class="stat-value">{{ team.players?.length || 0 }}</span>
          </div>

          <!-- Linked coach -->
          <div class="stat-row">
            <span class="stat-icon">🎯</span>
            <span class="stat-label">Coach</span>
            <span class="stat-value">{{ team.coach_name || 'None assigned' }}</span>
          </div>

          <!-- Current competitions -->
          <div class="stat-row">
            <span class="stat-icon">🏆</span>
            <span class="stat-label">Competitions</span>
            <span class="stat-value">{{ team.competitions?.length || 0 }}</span>
          </div>

          <!-- Competition tags if any -->
          <div v-if="team.competitions?.length" class="competitions-tags">
            <span
              v-for="comp in team.competitions.slice(0, 3)"
              :key="comp.id"
              class="competition-tag"
            >
              {{ comp.name }}
            </span>
            <span v-if="team.competitions.length > 3" class="competition-tag more">
              +{{ team.competitions.length - 3 }} more
            </span>
          </div>
        </div>

        <!-- Players preview -->
        <div v-if="team.players?.length" class="players-preview">
          <div class="players-avatars">
            <div
              v-for="(player, idx) in team.players.slice(0, 5)"
              :key="player.id"
              class="player-avatar"
              :title="player.name"
              :style="{ '--index': idx }"
            >
              {{ player.name.charAt(0).toUpperCase() }}
            </div>
            <div v-if="team.players.length > 5" class="player-avatar more">
              +{{ team.players.length - 5 }}
            </div>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="teams.length === 0" class="empty-state">
        <div class="empty-icon">🏏</div>
        <h3>No teams yet</h3>
        <p>Create your first team to get started managing players and competitions.</p>
        <button
          v-if="canManageTeams"
          class="btn-primary"
          @click="openCreateModal"
        >
          + Create Team
        </button>
      </div>
    </div>

    <!-- Team Form Modal -->
    <TeamFormModal
      v-model:visible="showTeamModal"
      :team="editingTeam"
      :available-players="availablePlayers"
      :available-coaches="availableCoaches"
      @saved="handleTeamSaved"
    />
  </div>
</template>

<style scoped>
.team-management {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

/* Banners */
.team-banner {
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
}

.team-banner.info {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.team-banner.warn {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.team-banner.success {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.link-inline {
  color: inherit;
  font-weight: 600;
  text-decoration: underline;
  margin-left: 0.5rem;
}

/* Header */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.header h1 {
  margin: 0;
  font-size: 1.75rem;
  color: var(--color-text, #fff);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.hint-inline {
  color: var(--color-text-muted, #888);
  font-size: 0.75rem;
}

/* Buttons */
.btn-primary {
  background: var(--color-primary, #4f46e5);
  color: #fff;
  border: none;
  padding: 0.75rem 1.25rem;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover, #4338ca);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-icon {
  background: transparent;
  border: none;
  font-size: 1rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 6px;
  transition: background 0.2s;
}

.btn-icon:hover {
  background: var(--color-surface-hover, #252540);
}

.btn-icon-danger:hover {
  background: rgba(239, 68, 68, 0.2);
}

.btn-link {
  background: none;
  border: none;
  color: var(--color-primary, #4f46e5);
  cursor: pointer;
  text-decoration: underline;
  margin-left: 0.5rem;
}

/* Loading */
.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 3rem;
  color: var(--color-text-muted, #888);
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border, #333);
  border-top-color: var(--color-primary, #4f46e5);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error */
.error-banner {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
  padding: 1rem;
  border-radius: 8px;
  text-align: center;
}

/* Teams Grid */
.teams-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.25rem;
}

/* Team Card */
.team-card {
  background: var(--color-surface, #1a1a2e);
  border: 1px solid var(--color-border, #333);
  border-radius: 12px;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
}

.team-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--color-border, #333);
}

.team-name {
  margin: 0;
  font-size: 1.125rem;
  color: var(--color-text, #fff);
}

.card-actions {
  display: flex;
  gap: 0.25rem;
}

.card-body {
  padding: 1rem 1.25rem;
}

/* Stat rows */
.stat-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--color-border-light, rgba(255,255,255,0.05));
}

.stat-row:last-of-type {
  border-bottom: none;
}

.stat-icon {
  font-size: 1rem;
  width: 1.5rem;
}

.stat-label {
  color: var(--color-text-muted, #888);
  font-size: 0.875rem;
  flex: 1;
}

.stat-value {
  color: var(--color-text, #fff);
  font-weight: 500;
}

/* Competition tags */
.competitions-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.competition-tag {
  background: var(--color-primary-light, rgba(79, 70, 229, 0.2));
  color: var(--color-primary, #4f46e5);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
}

.competition-tag.more {
  background: var(--color-surface-hover, #252540);
  color: var(--color-text-muted, #888);
}

/* Players preview */
.players-preview {
  padding: 0.75rem 1.25rem;
  background: var(--color-background, #0f0f1a);
  border-top: 1px solid var(--color-border, #333);
}

.players-avatars {
  display: flex;
  align-items: center;
}

.player-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-primary, #4f46e5);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
  margin-left: calc(var(--index, 0) * -8px);
  border: 2px solid var(--color-background, #0f0f1a);
  position: relative;
  z-index: calc(10 - var(--index, 0));
}

.player-avatar.more {
  background: var(--color-surface-hover, #252540);
  color: var(--color-text-muted, #888);
  font-size: 0.625rem;
  margin-left: -8px;
}

/* Empty state */
.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 3rem 1.5rem;
  background: var(--color-surface, #1a1a2e);
  border: 1px dashed var(--color-border, #333);
  border-radius: 12px;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-state h3 {
  margin: 0 0 0.5rem;
  color: var(--color-text, #fff);
}

.empty-state p {
  color: var(--color-text-muted, #888);
  margin: 0 0 1.5rem;
}

/* Responsive */
@media (max-width: 640px) {
  .team-management {
    padding: 1rem;
  }

  .header {
    flex-direction: column;
    align-items: flex-start;
  }

  .teams-grid {
    grid-template-columns: 1fr;
  }
}
</style>

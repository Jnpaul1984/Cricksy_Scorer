<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

import { API_BASE, getStoredToken } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'

const auth = useAuthStore()

// Types
interface SeatInfo {
  role: string
  label: string
  used: number
  limit: number | null // null = unlimited
}

interface UserSeat {
  id: string
  email: string
  role: string
  created_at: string
}

interface OrgTeam {
  id: string
  name: string
  players_count: number
  coach_name?: string
  season?: string
}

// State
const loading = ref(true)
const error = ref<string | null>(null)
const seats = ref<SeatInfo[]>([])
const users = ref<UserSeat[]>([])
const teams = ref<OrgTeam[]>([])
const showAssignModal = ref(false)
const selectedUserId = ref<string | null>(null)
const selectedRole = ref<string>('free')
const isExporting = ref(false)

// Auth checks
const isLoggedIn = computed(() => !!auth.token)
const canManageOrg = computed(() => {
  const role = auth.role?.toLowerCase() || ''
  return ['org_pro', 'superuser'].includes(role)
})

// Seat definitions with friendly labels
const seatDefinitions = [
  { role: 'coach_pro', label: 'Coach Pro', icon: '🎯' },
  { role: 'analyst_pro', label: 'Analyst Pro', icon: '📊' },
  { role: 'player_pro', label: 'Player Pro', icon: '🏏' },
  { role: 'org_pro', label: 'Org Pro', icon: '🏢' },
]

// API functions
async function fetchOrgData() {
  loading.value = true
  error.value = null

  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    const token = getStoredToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    // Fetch users to count seats
    const usersRes = await fetch(`${API_BASE}/api/users`, { headers })
    if (usersRes.ok) {
      users.value = await usersRes.json()
    }

    // Fetch teams
    const teamsRes = await fetch(`${API_BASE}/api/teams`, { headers })
    if (teamsRes.ok) {
      const teamsData = await teamsRes.json()
      teams.value = teamsData.map((t: any) => ({
        id: t.id,
        name: t.name,
        players_count: t.players?.length || 0,
        coach_name: t.coach_name,
        season: t.season
      }))
    }

    // Calculate seat usage
    calculateSeats()
  } catch (err: any) {
    error.value = err.message || 'Failed to load organization data'
    console.error('Error fetching org data:', err)
  } finally {
    loading.value = false
  }
}

function calculateSeats() {
  seats.value = seatDefinitions.map(def => {
    const usedCount = users.value.filter(u => u.role === def.role).length
    return {
      role: def.role,
      label: def.label,
      used: usedCount,
      limit: null // No hard limit for now, can be configured
    }
  })
}

function getUsersForRole(role: string): UserSeat[] {
  return users.value.filter(u => u.role === role)
}

async function assignRole(userId: string, newRole: string) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = getStoredToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  try {
    const res = await fetch(`${API_BASE}/api/users/${userId}/role`, {
      method: 'PUT',
      headers,
      body: JSON.stringify({ role: newRole })
    })

    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || 'Failed to update role')
    }

    await fetchOrgData()
    showAssignModal.value = false
  } catch (err: any) {
    error.value = err.message || 'Failed to assign role'
  }
}

async function revokeRole(userId: string) {
  if (!confirm('Are you sure you want to revoke this user\'s role? They will be set to Free tier.')) {
    return
  }
  await assignRole(userId, 'free')
}

function openAssignModal(userId?: string) {
  selectedUserId.value = userId || null
  selectedRole.value = 'coach_pro'
  showAssignModal.value = true
}

// PDF Export
async function exportToPDF() {
  isExporting.value = true

  try {
    // Create a printable version of the dashboard
    const printContent = generatePrintContent()

    // Open print dialog
    const printWindow = window.open('', '_blank')
    if (!printWindow) {
      throw new Error('Could not open print window. Please allow popups.')
    }

    printWindow.document.write(printContent)
    printWindow.document.close()

    // Wait for content to load then print
    printWindow.onload = () => {
      printWindow.print()
      printWindow.close()
    }
  } catch (err: any) {
    error.value = err.message || 'Failed to export PDF'
  } finally {
    isExporting.value = false
  }
}

function generatePrintContent(): string {
  const date = new Date().toLocaleDateString()
  const seatsHtml = seats.value.map(s => `
    <tr>
      <td>${s.label}</td>
      <td>${s.used}</td>
      <td>${s.limit ?? 'Unlimited'}</td>
    </tr>
  `).join('')

  const teamsHtml = teams.value.map(t => `
    <tr>
      <td>${t.name}</td>
      <td>${t.players_count}</td>
      <td>${t.coach_name || 'None'}</td>
      <td>${t.season || '-'}</td>
    </tr>
  `).join('')

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <title>Organization Report - ${date}</title>
      <style>
        body { font-family: Arial, sans-serif; padding: 20px; color: #333; }
        h1 { color: #1a1a2e; border-bottom: 2px solid #4f46e5; padding-bottom: 10px; }
        h2 { color: #4f46e5; margin-top: 30px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background: #f5f5f5; font-weight: 600; }
        tr:nth-child(even) { background: #fafafa; }
        .summary { display: flex; gap: 20px; margin: 20px 0; }
        .stat-box { background: #f5f5f5; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #4f46e5; }
        .stat-label { font-size: 12px; color: #666; }
        .footer { margin-top: 40px; font-size: 12px; color: #888; text-align: center; }
        @media print { body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
      </style>
    </head>
    <body>
      <h1>🏢 Organization Management Report</h1>
      <p>Generated on ${date}</p>

      <div class="summary">
        <div class="stat-box">
          <div class="stat-value">${teams.value.length}</div>
          <div class="stat-label">Total Teams</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${users.value.length}</div>
          <div class="stat-label">Total Users</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${seats.value.reduce((sum, s) => sum + s.used, 0)}</div>
          <div class="stat-label">Assigned Seats</div>
        </div>
      </div>

      <h2>📊 Seat Allocation</h2>
      <table>
        <thead>
          <tr>
            <th>Seat Type</th>
            <th>Used</th>
            <th>Limit</th>
          </tr>
        </thead>
        <tbody>
          ${seatsHtml || '<tr><td colspan="3">No seat data</td></tr>'}
        </tbody>
      </table>

      <h2>🏏 Teams</h2>
      <table>
        <thead>
          <tr>
            <th>Team Name</th>
            <th>Players</th>
            <th>Coach</th>
            <th>Season</th>
          </tr>
        </thead>
        <tbody>
          ${teamsHtml || '<tr><td colspan="4">No teams</td></tr>'}
        </tbody>
      </table>

      <div class="footer">
        Cricksy Scorer - Organization Management Report
      </div>
    </body>
    </html>
  `
}

onMounted(() => {
  fetchOrgData()
})
</script>

<template>
  <div class="org-management">
    <!-- Access banner -->
    <div v-if="!isLoggedIn" class="org-banner info">
      Sign in with an Org Pro account to manage your organization.
      <RouterLink to="/login" class="link-inline">Sign in</RouterLink>
    </div>
    <div v-else-if="!canManageOrg" class="org-banner warn">
      Organization management requires Org Pro or Superuser role.
    </div>

    <!-- Header -->
    <div class="header">
      <div class="header-text">
        <h1>Organization Management</h1>
        <p class="subtitle">Manage seats, teams, and user access across your organization.</p>
      </div>
      <div class="header-actions">
        <button
          class="btn-secondary"
          :disabled="isExporting || !canManageOrg"
          @click="exportToPDF"
        >
          {{ isExporting ? 'Exporting...' : '📄 Export PDF' }}
        </button>
        <button
          class="btn-primary"
          :disabled="!canManageOrg"
          @click="openAssignModal()"
        >
          + Assign Seat
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading">
      <div class="spinner" />
      Loading organization data...
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-banner">
      {{ error }}
      <button class="btn-link" @click="fetchOrgData">Retry</button>
    </div>

    <!-- Content -->
    <div v-else class="org-content">
      <!-- Seats Overview -->
      <section class="seats-section">
        <h2>Seat Allocation</h2>
        <div class="seats-grid">
          <div
            v-for="seat in seats"
            :key="seat.role"
            class="seat-card"
          >
            <div class="seat-icon">
              {{ seatDefinitions.find(d => d.role === seat.role)?.icon || '👤' }}
            </div>
            <div class="seat-info">
              <h3 class="seat-label">{{ seat.label }}</h3>
              <div class="seat-usage">
                <span class="seat-count">{{ seat.used }}</span>
                <span class="seat-limit">/ {{ seat.limit ?? '∞' }}</span>
              </div>
            </div>
            <button
              v-if="canManageOrg && seat.used > 0"
              class="btn-ghost btn-sm"
              @click="openAssignModal()"
            >
              Manage
            </button>
          </div>
        </div>
      </section>

      <!-- Seat Users Details -->
      <section class="users-section">
        <h2>Assigned Users</h2>
        <div class="users-by-role">
          <div
            v-for="def in seatDefinitions"
            :key="def.role"
            class="role-group"
          >
            <h3 class="role-title">
              {{ def.icon }} {{ def.label }}
              <span class="role-count">({{ getUsersForRole(def.role).length }})</span>
            </h3>
            <div v-if="getUsersForRole(def.role).length === 0" class="no-users">
              No users assigned
            </div>
            <ul v-else class="user-list">
              <li
                v-for="user in getUsersForRole(def.role)"
                :key="user.id"
                class="user-item"
              >
                <span class="user-email">{{ user.email }}</span>
                <button
                  v-if="canManageOrg"
                  class="btn-icon btn-icon-danger"
                  title="Revoke seat"
                  @click="revokeRole(user.id)"
                >
                  ✕
                </button>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <!-- Teams Section -->
      <section class="teams-section">
        <div class="section-header">
          <h2>Teams Under Organization</h2>
          <RouterLink v-if="canManageOrg" to="/teams" class="btn-link">
            Manage Teams →
          </RouterLink>
        </div>

        <div v-if="teams.length === 0" class="empty-state">
          <p>No teams created yet.</p>
          <RouterLink v-if="canManageOrg" to="/teams" class="btn-primary">
            + Create Team
          </RouterLink>
        </div>

        <div v-else class="teams-table-wrapper">
          <table class="teams-table">
            <thead>
              <tr>
                <th>Team Name</th>
                <th>Players</th>
                <th>Coach</th>
                <th>Season</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="team in teams" :key="team.id">
                <td class="team-name">{{ team.name }}</td>
                <td>{{ team.players_count }}</td>
                <td>{{ team.coach_name || '—' }}</td>
                <td>{{ team.season || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <!-- Assign Seat Modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="showAssignModal"
          class="modal-backdrop"
          @click.self="showAssignModal = false"
        >
          <div class="modal-content">
            <header class="modal-header">
              <h3>Assign Seat</h3>
              <button aria-label="Close" class="close-btn" @click="showAssignModal = false">×</button>
            </header>

            <div class="modal-body">
              <div class="form-group">
                <label class="field-label">Select User</label>
                <select v-model="selectedUserId" class="ds-input">
                  <option :value="null">-- Select User --</option>
                  <option
                    v-for="user in users.filter(u => u.role === 'free')"
                    :key="user.id"
                    :value="user.id"
                  >
                    {{ user.email }}
                  </option>
                </select>
              </div>

              <div class="form-group">
                <label class="field-label">Assign Role</label>
                <select v-model="selectedRole" class="ds-input">
                  <option
                    v-for="def in seatDefinitions"
                    :key="def.role"
                    :value="def.role"
                  >
                    {{ def.icon }} {{ def.label }}
                  </option>
                </select>
              </div>
            </div>

            <footer class="modal-footer">
              <button class="btn-secondary" @click="showAssignModal = false">
                Cancel
              </button>
              <button
                class="btn-primary"
                :disabled="!selectedUserId"
                @click="assignRole(selectedUserId!, selectedRole)"
              >
                Assign Seat
              </button>
            </footer>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.org-management {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

/* Banners */
.org-banner {
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
}

.org-banner.info {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.org-banner.warn {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.3);
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
  align-items: flex-start;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.header h1 {
  margin: 0;
  font-size: 1.75rem;
  color: var(--color-text, #fff);
}

.subtitle {
  margin: 0.25rem 0 0;
  color: var(--color-text-muted, #888);
}

.header-actions {
  display: flex;
  gap: 0.75rem;
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

.btn-secondary {
  background: var(--color-surface, #1a1a2e);
  color: var(--color-text, #fff);
  border: 1px solid var(--color-border, #333);
  padding: 0.75rem 1.25rem;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-surface-hover, #252540);
}

.btn-ghost {
  background: transparent;
  color: var(--color-primary, #4f46e5);
  border: none;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
}

.btn-ghost:hover {
  background: rgba(79, 70, 229, 0.1);
}

.btn-sm {
  padding: 0.375rem 0.5rem;
  font-size: 0.75rem;
}

.btn-link {
  background: none;
  border: none;
  color: var(--color-primary, #4f46e5);
  cursor: pointer;
  text-decoration: underline;
}

.btn-icon {
  background: transparent;
  border: none;
  font-size: 0.875rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.btn-icon-danger:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
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

/* Content */
.org-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* Seats Section */
.seats-section h2,
.users-section h2,
.teams-section h2 {
  margin: 0 0 1rem;
  font-size: 1.25rem;
  color: var(--color-text, #fff);
}

.seats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1rem;
}

.seat-card {
  background: var(--color-surface, #1a1a2e);
  border: 1px solid var(--color-border, #333);
  border-radius: 12px;
  padding: 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.seat-icon {
  font-size: 2rem;
}

.seat-info {
  flex: 1;
}

.seat-label {
  margin: 0;
  font-size: 0.875rem;
  color: var(--color-text-muted, #888);
}

.seat-usage {
  margin-top: 0.25rem;
}

.seat-count {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text, #fff);
}

.seat-limit {
  color: var(--color-text-muted, #888);
  font-size: 0.875rem;
}

/* Users Section */
.users-by-role {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.25rem;
}

.role-group {
  background: var(--color-surface, #1a1a2e);
  border: 1px solid var(--color-border, #333);
  border-radius: 12px;
  padding: 1rem;
}

.role-title {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  color: var(--color-text, #fff);
}

.role-count {
  color: var(--color-text-muted, #888);
  font-weight: normal;
}

.no-users {
  color: var(--color-text-muted, #888);
  font-size: 0.875rem;
  font-style: italic;
}

.user-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.user-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--color-border-light, rgba(255,255,255,0.05));
}

.user-item:last-child {
  border-bottom: none;
}

.user-email {
  color: var(--color-text, #fff);
  font-size: 0.875rem;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Teams Section */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h2 {
  margin: 0;
}

.teams-table-wrapper {
  background: var(--color-surface, #1a1a2e);
  border: 1px solid var(--color-border, #333);
  border-radius: 12px;
  overflow: hidden;
}

.teams-table {
  width: 100%;
  border-collapse: collapse;
}

.teams-table th,
.teams-table td {
  padding: 0.875rem 1rem;
  text-align: left;
}

.teams-table th {
  background: var(--color-background, #0f0f1a);
  color: var(--color-text-muted, #888);
  font-weight: 500;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.teams-table td {
  border-top: 1px solid var(--color-border, #333);
  color: var(--color-text, #fff);
}

.team-name {
  font-weight: 500;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 2rem;
  background: var(--color-surface, #1a1a2e);
  border: 1px dashed var(--color-border, #333);
  border-radius: 12px;
}

.empty-state p {
  margin: 0 0 1rem;
  color: var(--color-text-muted, #888);
}

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: var(--color-surface, #1a1a2e);
  border-radius: 12px;
  width: 100%;
  max-width: 420px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--color-border, #333);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--color-text, #fff);
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: var(--color-text-muted, #888);
  cursor: pointer;
}

.close-btn:hover {
  color: var(--color-text, #fff);
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.field-label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: var(--color-text, #fff);
}

.ds-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--color-border, #333);
  border-radius: 8px;
  background: var(--color-background, #0f0f1a);
  color: var(--color-text, #fff);
  font-size: 1rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--color-border, #333);
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Responsive */
@media (max-width: 640px) {
  .org-management {
    padding: 1rem;
  }

  .header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    flex-direction: column;
  }

  .seats-grid,
  .users-by-role {
    grid-template-columns: 1fr;
  }
}
</style>

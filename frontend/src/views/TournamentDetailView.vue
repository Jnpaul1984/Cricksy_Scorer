<template>
  <section class="tournament-detail">
    <header class="td-header">
      <div class="td-header-main">
        <button class="td-back" type="button" @click="goBack">
          ⬅ Back to tournaments
        </button>

        <div v-if="tournament" class="td-title-block">
          <h1 class="td-title">
            {{ tournament.name }}
          </h1>
          <p class="td-subtitle">
            <span class="td-type-pill">
              {{ formatType(tournament.tournament_type || 'league') }}
            </span>
            <span
              class="td-status-pill"
              :data-status="tournament.status || 'upcoming'"
            >
              {{ formatStatus(tournament.status || 'upcoming') }}
            </span>
          </p>
        </div>
      </div>

      <!-- Management actions (Org Pro / Super only) -->
      <div v-if="canManageTournaments && tournament" class="td-actions">
        <span class="td-role-label">
          Management access: {{ accessLabel }}
        </span>
        <div class="td-actions-buttons">
          <button type="button" class="td-btn td-btn-outline" @click="reload">
            Refresh
          </button>
          <button type="button" class="td-btn td-btn-primary" @click="openEditModal">
            Edit tournament
          </button>
          <button type="button" class="td-btn td-btn-danger" @click="openDeleteConfirm">
            Delete tournament
          </button>
        </div>
      </div>

      <!-- Read-only banner for non-managers -->
      <div
        v-else-if="tournament && canViewDetail"
        class="td-banner td-banner-info"
      >
        <p>
          You are viewing this tournament in
          <strong>read-only mode</strong>.
          Only Organization Pro and Superuser accounts can manage tournaments.
        </p>
      </div>
    </header>

    <!-- Toast notification -->
    <Teleport to="body">
      <div v-if="toast" class="td-toast" :class="`td-toast-${toast.type}`">
        {{ toast.message }}
      </div>
    </Teleport>

    <!-- Loading state -->
    <div v-if="loading && !loaded" class="td-state td-state-loading">
      <div class="spinner" aria-hidden="true"></div>
      <p>Loading tournament details...</p>
    </div>

    <!-- Not found -->
    <div v-else-if="notFound" class="td-state td-state-empty">
      <h2>We couldn’t find that tournament.</h2>
      <p>
        It may have been removed, renamed, or you might have an outdated link.
      </p>
      <button type="button" class="td-btn td-btn-outline" @click="goBack">
        Back to tournaments
      </button>
    </div>

    <!-- Auth / RBAC block -->
    <div v-else-if="!canViewDetail" class="td-state td-state-locked">
      <h2>Access restricted</h2>
      <p>
        Your current account does not have permission to view tournament details
        on this device.
      </p>
      <p class="td-muted">
        Sign in with an <strong>Organization Pro</strong>, <strong>Coach Pro</strong>,
        or <strong>Analyst Pro</strong> account to unlock full access.
      </p>
      <button
        type="button"
        class="td-btn td-btn-primary"
        @click="goToLogin"
      >
        Go to login
      </button>
    </div>

    <!-- Generic error -->
    <div v-else-if="errorMessage" class="td-state td-state-error">
      <h2>Something went wrong.</h2>
      <p>{{ errorMessage }}</p>
      <div class="td-state-actions">
        <button type="button" class="td-btn td-btn-outline" @click="reload">
          Try again
        </button>
        <button type="button" class="td-btn td-btn-ghost" @click="goBack">
          Back to tournaments
        </button>
      </div>
    </div>

    <!-- Edit Tournament Modal -->
    <div v-if="showEditModal && canManageTournaments && tournament" class="td-modal-overlay" @click.self="showEditModal = false">
      <div class="td-modal">
        <h2>Edit Tournament</h2>
        <form @submit.prevent="submitEdit">
          <div class="td-form-group">
            <label>Name *</label>
            <input v-model="editForm.name" type="text" required placeholder="e.g., Premier League 2024" />
          </div>
          <div class="td-form-group">
            <label>Description</label>
            <textarea v-model="editForm.description" placeholder="Tournament description"></textarea>
          </div>
          <div class="td-form-group">
            <label>Type</label>
            <select v-model="editForm.tournament_type">
              <option value="league">League</option>
              <option value="knockout">Knockout</option>
              <option value="round-robin">Round Robin</option>
            </select>
          </div>
          <div class="td-form-group">
            <label>Status</label>
            <select v-model="editForm.status">
              <option value="upcoming">Upcoming</option>
              <option value="ongoing">Ongoing</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
          <div class="td-form-group">
            <label>Start Date</label>
            <input v-model="editForm.start_date" type="date" />
          </div>
          <div class="td-form-group">
            <label>End Date</label>
            <input v-model="editForm.end_date" type="date" />
          </div>
          <div class="td-modal-actions">
            <button type="button" class="td-btn td-btn-outline" @click="showEditModal = false">Cancel</button>
            <button type="submit" class="td-btn td-btn-primary" :disabled="editSubmitting">
              {{ editSubmitting ? 'Saving...' : 'Save Changes' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteConfirm && canManageTournaments && tournament" class="td-modal-overlay" @click.self="showDeleteConfirm = false">
      <div class="td-modal td-modal-confirm">
        <h2>Delete Tournament?</h2>
        <p class="td-confirm-text">
          Are you sure you want to delete <strong>{{ tournament.name }}</strong>?
          This will permanently remove the tournament, its fixtures, and points table.
        </p>
        <div class="td-modal-actions">
          <button type="button" class="td-btn td-btn-outline" :disabled="deleteSubmitting" @click="showDeleteConfirm = false">
            Cancel
          </button>
          <button type="button" class="td-btn td-btn-danger" :disabled="deleteSubmitting" @click="confirmDelete">
            {{ deleteSubmitting ? 'Deleting...' : 'Delete Tournament' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Sponsor Create/Edit Modal -->
    <div v-if="showSponsorModal && canManageTournaments" class="td-modal-overlay" @click.self="closeSponsorModal">
      <div class="td-modal">
        <h2>{{ editingSponsor ? 'Edit Sponsor' : 'Add Sponsor' }}</h2>
        <form @submit.prevent="submitSponsor">
          <div class="td-form-group">
            <label>Name *</label>
            <input v-model="sponsorForm.name" type="text" required placeholder="Sponsor name" />
          </div>
          <div v-if="!editingSponsor" class="td-form-group">
            <label>Logo File *</label>
            <input type="file" accept=".png,.svg,.webp,image/png,image/svg+xml,image/webp" required @change="onLogoFileChange" />
            <small class="td-muted">Upload a PNG, SVG, or WebP logo (max 5MB)</small>
          </div>
          <div v-else class="td-form-group">
            <label>Current Logo</label>
            <img v-if="editingSponsor?.logoUrl" :src="resolveSponsorLogo(editingSponsor.logoUrl)" alt="Current logo" class="td-current-logo" />
            <small class="td-muted">Logo cannot be changed after creation</small>
          </div>
          <div class="td-form-group">
            <label>Click URL</label>
            <input v-model="sponsorForm.click_url" type="url" placeholder="https://sponsor-website.com" />
          </div>
          <div class="td-form-group">
            <label>Weight (1-5)</label>
            <input v-model.number="sponsorForm.weight" type="number" min="1" max="5" />
            <small class="td-muted">Higher weight = more prominent placement</small>
          </div>
          <div class="td-form-group td-checkbox-group">
            <label>
              <input v-model="sponsorForm.is_active" type="checkbox" />
              Active
            </label>
          </div>
          <div class="td-modal-actions">
            <button type="button" class="td-btn td-btn-outline" @click="closeSponsorModal">Cancel</button>
            <button type="submit" class="td-btn td-btn-primary" :disabled="sponsorSubmitting">
              {{ sponsorSubmitting ? 'Saving...' : (editingSponsor ? 'Update' : 'Create') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Sponsor Delete Confirmation Modal -->
    <div v-if="showSponsorDeleteConfirm && canManageTournaments" class="td-modal-overlay" @click.self="showSponsorDeleteConfirm = false">
      <div class="td-modal td-modal-confirm">
        <h2>Delete Sponsor?</h2>
        <p class="td-confirm-text">
          Are you sure you want to delete <strong>{{ sponsorToDelete?.name }}</strong>?
          This cannot be undone.
        </p>
        <div class="td-modal-actions">
          <button type="button" class="td-btn td-btn-outline" :disabled="sponsorDeleting" @click="showSponsorDeleteConfirm = false">
            Cancel
          </button>
          <button type="button" class="td-btn td-btn-danger" :disabled="sponsorDeleting" @click="confirmDeleteSponsor">
            {{ sponsorDeleting ? 'Deleting...' : 'Delete Sponsor' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Main content -->
    <div v-else-if="tournament" class="td-layout">
      <!-- Left column: overview + points -->
      <div class="td-column">
        <section class="td-card">
          <h2>Overview</h2>
          <dl class="td-meta">
            <div>
              <dt>Format</dt>
              <dd>{{ formatType(tournament.tournament_type || 'league') }}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{{ formatStatus(tournament.status || 'upcoming') }}</dd>
            </div>
            <div v-if="tournament.start_date || tournament.end_date">
              <dt>Dates</dt>
              <dd>
                <span v-if="tournament.start_date">
                  {{ formatDate(tournament.start_date) }}
                </span>
                <span v-if="tournament.start_date && tournament.end_date"> – </span>
                <span v-if="tournament.end_date">
                  {{ formatDate(tournament.end_date) }}
                </span>
              </dd>
            </div>
            <div v-if="tournament.description">
              <dt>Description</dt>
              <dd>{{ tournament.description }}</dd>
            </div>
          </dl>
        </section>

        <section class="td-card">
          <div class="td-card-header">
            <h2>Points Table</h2>
            <p v-if="pointsTable.length === 0" class="td-card-subtitle">
              No teams have been added yet.
            </p>
          </div>

          <table v-if="pointsTable.length" class="td-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Team</th>
                <th>Played</th>
                <th>Won</th>
                <th>Lost</th>
                <th>Tied</th>
                <th>NR</th>
                <th>Points</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, idx) in pointsTable"
                :key="row.id || row.team_name || idx"
              >
                <td>{{ idx + 1 }}</td>
                <td>{{ row.team_name || '—' }}</td>
                <td>{{ row.matches_played ?? row.played ?? 0 }}</td>
                <td>{{ row.wins ?? 0 }}</td>
                <td>{{ row.losses ?? 0 }}</td>
                <td>{{ row.ties ?? 0 }}</td>
                <td>{{ row.no_results ?? 0 }}</td>
                <td>{{ row.points ?? 0 }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <!-- Sponsors Section (Org Pro / Super only) -->
        <section v-if="canManageTournaments" class="td-card">
          <div class="td-card-header td-card-header-row">
            <div>
              <h2>Sponsors</h2>
              <p v-if="sponsors.length === 0" class="td-card-subtitle">
                No sponsors configured yet.
              </p>
            </div>
            <button type="button" class="td-btn td-btn-primary td-btn-sm" @click="openCreateSponsor">
              + Add Sponsor
            </button>
          </div>

          <div v-if="sponsorsLoading" class="td-state td-state-loading td-state-inline">
            <div class="spinner spinner-sm" aria-hidden="true"></div>
            <span>Loading sponsors...</span>
          </div>

          <table v-else-if="sponsors.length" class="td-table td-table-sponsors">
            <thead>
              <tr>
                <th>Logo</th>
                <th>Name</th>
                <th>Click URL</th>
                <th>Weight</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="sponsor in sponsors" :key="sponsor.id">
                <td>
                  <img
                    v-if="sponsor.logoUrl"
                    :src="resolveSponsorLogo(sponsor.logoUrl)"
                    :alt="sponsor.name"
                    class="td-sponsor-logo"
                  />
                  <span v-else class="td-muted">No logo</span>
                </td>
                <td>{{ sponsor.name }}</td>
                <td>
                  <a v-if="sponsor.clickUrl" :href="sponsor.clickUrl" target="_blank" rel="noopener" class="td-link-truncate">
                    {{ truncateUrl(sponsor.clickUrl) }}
                  </a>
                  <span v-else class="td-muted">—</span>
                </td>
                <td>{{ sponsor.weight }}</td>
                <td>
                  <span class="td-status-badge" :class="sponsor.is_active !== false ? 'td-status-active' : 'td-status-inactive'">
                    {{ sponsor.is_active !== false ? 'Active' : 'Inactive' }}
                  </span>
                </td>
                <td class="td-actions-cell">
                  <button type="button" class="td-btn td-btn-ghost td-btn-sm" @click="openEditSponsor(sponsor)">
                    Edit
                  </button>
                  <button type="button" class="td-btn td-btn-ghost td-btn-sm td-btn-danger-text" @click="openDeleteSponsor(sponsor)">
                    Delete
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>

      <!-- Right column: teams + fixtures -->
      <div class="td-column">
        <section class="td-card">
          <div class="td-card-header">
            <h2>Teams</h2>
            <p v-if="teams.length === 0" class="td-card-subtitle">
              No teams registered yet.
            </p>
          </div>

          <ul v-if="teams.length" class="td-list">
            <li v-for="team in teams" :key="team.id || team.team_name">
              <div class="td-list-main">
                <strong>{{ team.team_name }}</strong>
                <button
                  v-if="authStore.currentUser && team.id != null"
                  type="button"
                  class="td-team-fav-btn"
                  :class="{ 'td-team-fav-active': isTeamFavorite(team.id) }"
                  :disabled="togglingTeamFavorite.has(String(team.id))"
                  :title="isTeamFavorite(team.id) ? 'Remove from favorites' : 'Add to favorites'"
                  @click.stop="toggleTeamFavorite(team.id)"
                >
                  {{ isTeamFavorite(team.id) ? '★' : '☆' }}
                </button>
                <span class="td-list-secondary">
                  {{ (team.matches_played ?? 0) }} matches •
                  {{ (team.points ?? 0) }} pts
                </span>
              </div>
            </li>
          </ul>

          <p v-if="teams.length && !canManageTournaments" class="td-muted td-footnote">
            Teams are managed by Organization Pro accounts.
          </p>
        </section>

        <section class="td-card">
          <div class="td-card-header">
            <h2>Fixtures</h2>
            <p v-if="fixtures.length === 0" class="td-card-subtitle">
              No fixtures have been scheduled yet.
            </p>
          </div>

          <ul v-if="fixtures.length" class="td-list">
            <li v-for="fixture in fixtures" :key="fixture.id">
              <div class="td-list-main">
                <strong>
                  {{ fixture.team_a_name }} vs {{ fixture.team_b_name }}
                </strong>
                <span class="td-list-secondary">
                  <span v-if="fixture.venue">
                    {{ fixture.venue }}
                  </span>
                  <span v-if="fixture.scheduled_date">
                    • {{ formatDate(fixture.scheduled_date) }}
                  </span>
                  <span>
                    • {{ formatFixtureStatus(fixture.status || 'scheduled') }}
                  </span>
                </span>
              </div>
            </li>
          </ul>

          <p v-if="fixtures.length && !canManageTournaments" class="td-muted td-footnote">
            Fixtures are managed by Organization Pro accounts.
          </p>
        </section>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import apiService, { API_BASE, getErrorMessage, type FanFavoriteRead } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'

type Tournament = Record<string, any>
type TournamentTeam = Record<string, any>
type TournamentFixture = Record<string, any>
type PointsRow = Record<string, any>

// ================== Team favorites state ==================
// Map of team.id (as string) -> favorite record id (for quick lookup and deletion)
const teamFavoritesMap = ref<Map<string, string>>(new Map())
const togglingTeamFavorite = ref<Set<string>>(new Set())

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const tournamentId = computed(() => String(route.params.tournamentId ?? ''))

const loading = ref(true)
const loaded = ref(false)
const notFound = ref(false)
const errorMessage = ref<string | null>(null)

const tournament = ref<Tournament | null>(null)
const teams = ref<TournamentTeam[]>([])
const fixtures = ref<TournamentFixture[]>([])
const pointsTable = ref<PointsRow[]>([])

// Edit modal state
const showEditModal = ref(false)
const editSubmitting = ref(false)
const editForm = ref({
  name: '',
  description: '',
  tournament_type: 'league',
  status: 'upcoming',
  start_date: '',
  end_date: '',
})

// Delete confirmation state
const showDeleteConfirm = ref(false)
const deleteSubmitting = ref(false)

// ================== Sponsor management state ==================
type Sponsor = {
  id: string
  name: string
  logoUrl?: string | null
  clickUrl?: string | null
  weight: number
  is_active?: boolean
  surfaces?: string[]
}

const sponsors = ref<Sponsor[]>([])
const sponsorsLoading = ref(false)
const showSponsorModal = ref(false)
const editingSponsor = ref<Sponsor | null>(null)
const sponsorSubmitting = ref(false)
const sponsorLogoFile = ref<File | null>(null)
const sponsorForm = ref({
  name: '',
  logo_url: '',
  click_url: '',
  weight: 1,
  is_active: true,
})

const showSponsorDeleteConfirm = ref(false)
const sponsorToDelete = ref<Sponsor | null>(null)
const sponsorDeleting = ref(false)

// Toast state
type ToastType = 'success' | 'error' | 'info'
const toast = ref<{ message: string; type: ToastType } | null>(null)
let toastTimer: number | null = null

function showToast(message: string, type: ToastType = 'success', ms = 2500): void {
  toast.value = { message, type }
  if (toastTimer) window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => (toast.value = null), ms) as unknown as number
}

const canViewDetail = computed(() =>
  authStore.hasAnyRole([
    'free',
    'player_pro',
    'coach_pro',
    'analyst_pro',
    'org_pro',
    'superuser',
  ]),
)

const canManageTournaments = computed(() => authStore.canManageTournaments)

const accessLabel = computed(() => {
  const role = authStore.currentUser?.role
  if (!role) return 'Not signed in'
  if (role === 'org_pro') return 'Organization Pro'
  if (role === 'superuser') return 'Superuser'
  if (role === 'analyst_pro') return 'Analyst (read-only)'
  if (role === 'coach_pro') return 'Coach (read-only)'
  if (role === 'player_pro') return 'Player (read-only)'
  return 'Free (view-only)'
})

function goBack() {
  router.push({ name: 'tournaments' })
}

function goToLogin() {
  const redirect = router.currentRoute.value.fullPath
  router.push({ name: 'login', query: { redirect } })
}

async function loadTournament() {
  if (!tournamentId.value) {
    notFound.value = true
    loading.value = false
    loaded.value = true
    return
  }

  loading.value = true
  errorMessage.value = null
  notFound.value = false

  try {
    const [t, pts, teamRows, fixtureRows] = await Promise.all([
      apiService.getTournament(tournamentId.value),
      apiService.getPointsTable(tournamentId.value),
      apiService.getTournamentTeams(tournamentId.value),
      apiService.getTournamentFixtures(tournamentId.value),
    ])

    tournament.value = t
    pointsTable.value = Array.isArray(pts) ? pts : []
    teams.value = Array.isArray(teamRows) ? teamRows : []
    fixtures.value = Array.isArray(fixtureRows) ? fixtureRows : []
  } catch (err: any) {
    const status = (err as any)?.status
    if (status === 404) {
      notFound.value = true
      tournament.value = null
      pointsTable.value = []
      teams.value = []
      fixtures.value = []
    } else if (status === 401) {
      errorMessage.value =
        'Your session has expired or you are not authorized. Please sign in again.'
    } else {
      errorMessage.value = getErrorMessage(err)
    }
  } finally {
    loading.value = false
    loaded.value = true
  }
}

function reload() {
  loadTournament()
}

// ================== Team favorites functions ==================
async function loadTeamFavorites() {
  if (!authStore.currentUser) return

  try {
    const favorites: FanFavoriteRead[] = await apiService.getFanFavorites()
    const newMap = new Map<string, string>()
    for (const fav of favorites) {
      if (fav.favorite_type === 'team' && fav.team_id != null) {
        newMap.set(fav.team_id, String(fav.id))
      }
    }
    teamFavoritesMap.value = newMap
  } catch {
    // Silently fail – favorites are non-critical
  }
}

function isTeamFavorite(teamId: number | string | undefined): boolean {
  if (teamId == null) return false
  return teamFavoritesMap.value.has(String(teamId))
}

async function toggleTeamFavorite(teamId: number | string | undefined): Promise<void> {
  if (teamId == null || !authStore.currentUser) return
  const teamIdStr = String(teamId)
  if (togglingTeamFavorite.value.has(teamIdStr)) return

  togglingTeamFavorite.value.add(teamIdStr)
  try {
    const existingFavoriteId = teamFavoritesMap.value.get(teamIdStr)
    if (existingFavoriteId) {
      // Remove favorite
      await apiService.deleteFanFavorite(existingFavoriteId)
      teamFavoritesMap.value.delete(teamIdStr)
    } else {
      // Add favorite
      const created = await apiService.createFanFavorite({
        favorite_type: 'team',
        team_id: teamIdStr,
      })
      teamFavoritesMap.value.set(teamIdStr, String(created.id))
    }
  } catch (err) {
    showToast(getErrorMessage(err) || 'Failed to update favorite', 'error')
  } finally {
    togglingTeamFavorite.value.delete(teamIdStr)
  }
}

// Edit functions
function openEditModal() {
  if (!tournament.value || !canManageTournaments.value) return

  // Pre-fill form with current tournament data
  editForm.value = {
    name: tournament.value.name || '',
    description: tournament.value.description || '',
    tournament_type: tournament.value.tournament_type || 'league',
    status: tournament.value.status || 'upcoming',
    start_date: tournament.value.start_date ? tournament.value.start_date.split('T')[0] : '',
    end_date: tournament.value.end_date ? tournament.value.end_date.split('T')[0] : '',
  }
  showEditModal.value = true
}

async function submitEdit() {
  if (!tournament.value || !canManageTournaments.value) return

  editSubmitting.value = true
  try {
    const payload = {
      name: editForm.value.name,
      description: editForm.value.description || null,
      tournament_type: editForm.value.tournament_type,
      status: editForm.value.status,
      start_date: editForm.value.start_date || null,
      end_date: editForm.value.end_date || null,
    }
    await apiService.updateTournament(tournamentId.value, payload)
    showEditModal.value = false
    await loadTournament()
  } catch (err: any) {
    alert(getErrorMessage(err) || 'Failed to update tournament')
  } finally {
    editSubmitting.value = false
  }
}

// Delete functions
function openDeleteConfirm() {
  if (!tournament.value || !canManageTournaments.value) return
  showDeleteConfirm.value = true
}

async function confirmDelete() {
  if (!tournament.value || !canManageTournaments.value) return

  deleteSubmitting.value = true
  try {
    await apiService.deleteTournament(tournamentId.value)
    showDeleteConfirm.value = false
    router.push({ name: 'tournaments' })
  } catch (err: any) {
    alert(getErrorMessage(err) || 'Failed to delete tournament')
  } finally {
    deleteSubmitting.value = false
  }
}

// ================== Sponsor functions ==================

async function loadSponsors() {
  if (!canManageTournaments.value) return
  sponsorsLoading.value = true
  try {
    const data = await apiService.getSponsors()
    sponsors.value = Array.isArray(data) ? data : []
  } catch (err: any) {
    console.error('Failed to load sponsors:', err)
    sponsors.value = []
  } finally {
    sponsorsLoading.value = false
  }
}

function resolveSponsorLogo(logoUrl: string | null | undefined): string {
  if (!logoUrl) return ''
  // If it's already an absolute URL, use it
  if (logoUrl.startsWith('http://') || logoUrl.startsWith('https://')) {
    return logoUrl
  }
  // Otherwise, prepend the API base
  return `${API_BASE}${logoUrl.startsWith('/') ? '' : '/'}${logoUrl}`
}

function truncateUrl(url: string): string {
  try {
    const u = new URL(url)
    return u.hostname + (u.pathname !== '/' ? u.pathname.slice(0, 20) + '...' : '')
  } catch {
    return url.length > 30 ? url.slice(0, 30) + '...' : url
  }
}

function openCreateSponsor() {
  editingSponsor.value = null
  sponsorLogoFile.value = null
  sponsorForm.value = {
    name: '',
    logo_url: '',
    click_url: '',
    weight: 1,
    is_active: true,
  }
  showSponsorModal.value = true
}

function openEditSponsor(sponsor: Sponsor) {
  editingSponsor.value = sponsor
  sponsorLogoFile.value = null
  sponsorForm.value = {
    name: sponsor.name,
    logo_url: sponsor.logoUrl || '',
    click_url: sponsor.clickUrl || '',
    weight: sponsor.weight,
    is_active: sponsor.is_active !== false,
  }
  showSponsorModal.value = true
}

function closeSponsorModal() {
  showSponsorModal.value = false
  editingSponsor.value = null
  sponsorLogoFile.value = null
}

function onLogoFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    sponsorLogoFile.value = file
  }
}

async function submitSponsor() {
  if (!canManageTournaments.value) return
  sponsorSubmitting.value = true

  try {
    if (editingSponsor.value) {
      // Update existing sponsor
      await apiService.updateSponsor(editingSponsor.value.id, {
        name: sponsorForm.value.name,
        click_url: sponsorForm.value.click_url || null,
        weight: sponsorForm.value.weight,
        is_active: sponsorForm.value.is_active,
      })
      showToast('Sponsor updated successfully', 'success')
    } else {
      // Create new sponsor with file upload
      if (!sponsorLogoFile.value) {
        showToast('Please select a logo file', 'error')
        sponsorSubmitting.value = false
        return
      }
      await apiService.uploadSponsor({
        name: sponsorForm.value.name,
        logo: sponsorLogoFile.value,
        click_url: sponsorForm.value.click_url || null,
        weight: sponsorForm.value.weight,
      })
      showToast('Sponsor created successfully', 'success')
    }
    closeSponsorModal()
    await loadSponsors()
  } catch (err: any) {
    showToast(getErrorMessage(err) || 'Failed to save sponsor', 'error', 3000)
  } finally {
    sponsorSubmitting.value = false
  }
}

function openDeleteSponsor(sponsor: Sponsor) {
  sponsorToDelete.value = sponsor
  showSponsorDeleteConfirm.value = true
}

async function confirmDeleteSponsor() {
  if (!sponsorToDelete.value || !canManageTournaments.value) return
  sponsorDeleting.value = true

  try {
    await apiService.deleteSponsor(sponsorToDelete.value.id)
    showToast('Sponsor deleted', 'success')
    showSponsorDeleteConfirm.value = false
    sponsorToDelete.value = null
    await loadSponsors()
  } catch (err: any) {
    showToast(getErrorMessage(err) || 'Failed to delete sponsor', 'error', 3000)
  } finally {
    sponsorDeleting.value = false
  }
}

onMounted(() => {
  loadTournament()
  loadSponsors()
  loadTeamFavorites()
})

watch(
  () => tournamentId.value,
  (next, prev) => {
    if (next && next !== prev) {
      loadTournament()
    }
  },
)

function formatDate(value: string | null | undefined): string {
  if (!value) return ''
  try {
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return String(value)
    return d.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return String(value)
  }
}

function formatType(raw: string): string {
  const v = (raw || '').toLowerCase()
  if (v === 'league') return 'League'
  if (v === 'knockout') return 'Knockout'
  if (v === 'round_robin') return 'Round robin'
  return v || 'League'
}

function formatStatus(raw: string): string {
  const v = (raw || '').toLowerCase()
  if (v === 'upcoming') return 'Upcoming'
  if (v === 'ongoing') return 'Ongoing'
  if (v === 'completed') return 'Completed'
  if (v === 'cancelled') return 'Cancelled'
  return v || 'Upcoming'
}

function formatFixtureStatus(raw: string): string {
  const v = (raw || '').toLowerCase()
  if (v === 'scheduled') return 'Scheduled'
  if (v === 'in_progress') return 'In progress'
  if (v === 'completed') return 'Completed'
  if (v === 'abandoned') return 'Abandoned'
  return v || 'Scheduled'
}
</script>

<style scoped>
.tournament-detail {
  max-width: 1200px;
  margin: 1.5rem auto 3rem;
  padding: 0 1rem 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.td-header {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.td-header-main {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.td-back {
  border: none;
  background: transparent;
  padding: 0;
  color: var(--pico-primary, #2563eb);
  cursor: pointer;
  font-size: 0.95rem;
}

.td-title-block {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.td-title {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
}

.td-subtitle {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.9rem;
  margin: 0;
}

.td-type-pill,
.td-status-pill {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: 0.8rem;
}

.td-type-pill {
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
}

.td-status-pill[data-status='upcoming'] {
  background: rgba(234, 179, 8, 0.1);
  color: #854d0e;
}

.td-status-pill[data-status='ongoing'] {
  background: rgba(22, 163, 74, 0.1);
  color: #166534;
}

.td-status-pill[data-status='completed'] {
  background: rgba(55, 65, 81, 0.1);
  color: #111827;
}

.td-status-pill[data-status='cancelled'] {
  background: rgba(248, 113, 113, 0.1);
  color: #b91c1c;
}

.td-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  background: rgba(15, 23, 42, 0.04);
}

.td-actions-buttons {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.td-role-label {
  font-size: 0.85rem;
  color: var(--pico-muted-border-color, #6b7280);
}

.td-btn {
  border-radius: 999px;
  padding: 0.35rem 0.85rem;
  font-size: 0.85rem;
  cursor: pointer;
}

.td-btn-primary {
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #fff;
}

.td-btn-outline {
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: #fff;
}

.td-btn-danger {
  border: 1px solid #b91c1c;
  background: #b91c1c;
  color: #fff;
}

.td-btn-ghost {
  border: none;
  background: transparent;
  color: var(--pico-primary, #2563eb);
}

.td-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr);
  gap: 1.5rem;
}

@media (max-width: 900px) {
  .td-layout {
    grid-template-columns: minmax(0, 1fr);
  }
}

.td-column {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.td-card {
  border-radius: 0.75rem;
  background: var(--pico-card-background-color, #fff);
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.06);
  padding: 1rem 1.1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.td-card-header {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.td-card-subtitle {
  font-size: 0.85rem;
  color: var(--pico-muted-border-color, #6b7280);
  margin: 0;
}

.td-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.75rem 1.5rem;
  margin: 0;
}

.td-meta div {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.td-meta dt {
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--pico-muted-border-color, #6b7280);
}

.td-meta dd {
  margin: 0;
  font-size: 0.95rem;
}

.td-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.td-table th,
.td-table td {
  padding: 0.45rem 0.35rem;
  text-align: left;
}

.td-table thead {
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.td-table tbody tr:nth-child(even) {
  background: rgba(15, 23, 42, 0.015);
}

.td-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.td-list-main {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.td-list-secondary {
  font-size: 0.85rem;
  color: var(--pico-muted-border-color, #6b7280);
}

/* Team favorite button (star icon) */
.td-team-fav-btn {
  background: transparent;
  border: none;
  padding: 0 0.25rem;
  font-size: 1rem;
  cursor: pointer;
  color: var(--pico-muted-border-color, #6b7280);
  transition: color 0.15s, transform 0.15s;
  vertical-align: middle;
  margin-left: 0.35rem;
}

.td-team-fav-btn:hover:not(:disabled) {
  color: #facc15;
  transform: scale(1.15);
}

.td-team-fav-btn.td-team-fav-active {
  color: #facc15;
}

.td-team-fav-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.td-muted {
  font-size: 0.85rem;
  color: var(--pico-muted-border-color, #6b7280);
}

.td-footnote {
  margin-top: 0.5rem;
}

.td-state {
  border-radius: 0.75rem;
  padding: 2rem 1.5rem;
  text-align: center;
  background: var(--pico-card-background-color, #fff);
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.06);
}

.td-state-loading .spinner {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  border: 3px solid rgba(37, 99, 235, 0.25);
  border-top-color: #2563eb;
  margin: 0 auto 0.75rem;
  animation: spin 0.9s linear infinite;
}

.td-state-empty h2,
.td-state-error h2,
.td-state-locked h2 {
  margin-bottom: 0.4rem;
}

.td-state-actions {
  margin-top: 1rem;
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.td-banner {
  border-radius: 0.75rem;
  padding: 0.75rem 1rem;
  font-size: 0.9rem;
}

.td-banner-info {
  background: rgba(59, 130, 246, 0.08);
  color: #1d4ed8;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Modal styles */
.td-modal-overlay {
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

.td-modal {
  background: white;
  padding: 2rem;
  border-radius: 0.75rem;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.15);
}

.td-modal h2 {
  margin: 0 0 1.5rem 0;
  font-size: 1.25rem;
}

.td-modal-confirm {
  max-width: 400px;
}

.td-confirm-text {
  color: #4b5563;
  margin: 0 0 1.5rem 0;
  line-height: 1.5;
}

.td-form-group {
  margin-bottom: 1rem;
}

.td-form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #333;
  font-weight: 500;
  font-size: 0.9rem;
}

.td-form-group input,
.td-form-group textarea,
.td-form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.375rem;
  font-size: 1rem;
}

.td-form-group textarea {
  min-height: 80px;
  resize: vertical;
}

.td-modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

/* Sponsor-related styles */
.td-card-header-row {
  flex-direction: row;
  justify-content: space-between;
  align-items: flex-start;
}

.td-btn-sm {
  padding: 0.25rem 0.65rem;
  font-size: 0.8rem;
}

.td-btn-danger-text {
  color: #b91c1c;
}

.td-btn-danger-text:hover {
  background: rgba(185, 28, 28, 0.08);
}

.td-table-sponsors {
  font-size: 0.85rem;
}

.td-table-sponsors th,
.td-table-sponsors td {
  padding: 0.5rem 0.4rem;
  vertical-align: middle;
}

.td-sponsor-logo {
  width: 48px;
  height: 32px;
  object-fit: contain;
  border-radius: 4px;
  background: #f9fafb;
}

.td-link-truncate {
  color: var(--pico-primary, #2563eb);
  text-decoration: none;
  font-size: 0.8rem;
}

.td-link-truncate:hover {
  text-decoration: underline;
}

.td-status-badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 500;
}

.td-status-active {
  background: rgba(22, 163, 74, 0.1);
  color: #166534;
}

.td-status-inactive {
  background: rgba(107, 114, 128, 0.1);
  color: #4b5563;
}

.td-actions-cell {
  white-space: nowrap;
}

.td-state-inline {
  padding: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  justify-content: center;
  background: transparent;
  box-shadow: none;
}

.spinner-sm {
  width: 18px;
  height: 18px;
  border-width: 2px;
}

.td-checkbox-group label {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.td-checkbox-group input[type="checkbox"] {
  width: auto;
}

.td-current-logo {
  display: block;
  width: 80px;
  height: 50px;
  object-fit: contain;
  border-radius: 4px;
  background: #f9fafb;
  margin-bottom: 0.5rem;
}

/* Toast notification */
.td-toast {
  position: fixed;
  bottom: 1.5rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.75rem 1.5rem;
  border-radius: 0.5rem;
  font-size: 0.9rem;
  font-weight: 500;
  z-index: 2000;
  animation: toast-in 0.2s ease-out;
}

.td-toast-success {
  background: #166534;
  color: white;
}

.td-toast-error {
  background: #b91c1c;
  color: white;
}

.td-toast-info {
  background: #1d4ed8;
  color: white;
}

@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}
</style>

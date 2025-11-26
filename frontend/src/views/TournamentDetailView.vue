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
          <button type="button" class="td-btn td-btn-primary" disabled>
            Edit tournament (coming soon)
          </button>
          <button type="button" class="td-btn td-btn-danger" disabled>
            Delete tournament (locked in beta)
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

import apiService, { getErrorMessage } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'

type Tournament = Record<string, any>
type TournamentTeam = Record<string, any>
type TournamentFixture = Record<string, any>
type PointsRow = Record<string, any>

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

onMounted(() => {
  loadTournament()
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
</style>

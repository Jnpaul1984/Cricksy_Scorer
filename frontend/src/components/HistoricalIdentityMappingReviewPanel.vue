<template>
  <div class="himr-panel">
    <div class="himr-header">
      <h3 class="himr-title">Historical Identity Mapping Review</h3>
      <p class="himr-subtitle">
        Review and resolve unresolved source player and venue identities from historical backfill.
        All actions are auditable and idempotent.
      </p>
    </div>

    <!-- Load button -->
    <div class="himr-actions">
      <button
        type="button"
        class="himr-btn himr-btn--primary"
        data-testid="himr-load-btn"
        :disabled="loading"
        @click="loadUnresolved"
      >
        {{ loading ? 'Loading…' : 'Load Unresolved' }}
      </button>
      <span v-if="lastLoaded" class="himr-meta">
        {{ totalUnresolvedPlayers }} unresolved players · {{ totalUnresolvedVenues }} unresolved venues
      </span>
    </div>

    <!-- Error banner -->
    <div v-if="loadError" class="himr-error-banner" role="alert" data-testid="himr-load-error">
      {{ loadError }}
    </div>

    <!-- Success banner -->
    <div v-if="actionSuccess" class="himr-success-banner" role="status" data-testid="himr-action-success">
      {{ actionSuccess }}
    </div>

    <!-- Action error -->
    <div v-if="actionError" class="himr-error-banner" role="alert" data-testid="himr-action-error">
      {{ actionError }}
    </div>

    <!-- Filters -->
    <div v-if="lastLoaded" class="himr-filters">
      <input
        v-model="filterText"
        type="search"
        class="himr-filter-input"
        placeholder="Filter by name, competition, reason…"
        data-testid="himr-filter-input"
      />
      <select v-model="filterStatus" class="himr-filter-select" data-testid="himr-filter-status">
        <option value="">All statuses</option>
        <option value="unresolved">Unresolved</option>
        <option value="ambiguous">Ambiguous</option>
        <option value="deferred">Deferred</option>
      </select>
    </div>

    <!-- Unresolved Players Table -->
    <section v-if="lastLoaded" class="himr-section">
      <h4 class="himr-section-title">
        Unresolved Players
        <span class="himr-count">{{ filteredPlayers.length }}</span>
      </h4>

      <div v-if="filteredPlayers.length === 0" class="himr-empty">
        No unresolved players matching filter.
      </div>

      <div v-else class="himr-table-wrapper">
        <table class="himr-table" data-testid="himr-players-table">
          <thead>
            <tr>
              <th>Source Name</th>
              <th>Source ID</th>
              <th>State</th>
              <th>Reason</th>
              <th>Queue</th>
              <th>Candidates</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="player in filteredPlayers"
              :key="player.source_player_id"
              :data-testid="`himr-player-row-${player.source_player_id}`"
            >
              <td>{{ player.source_player_name }}</td>
              <td class="himr-mono">{{ player.source_player_id.slice(0, 12) }}…</td>
              <td>
                <span :class="`himr-badge himr-badge--${player.resolution_state}`">
                  {{ player.resolution_state }}
                </span>
              </td>
              <td class="himr-reason">{{ player.reason || '—' }}</td>
              <td>
                <span :class="`himr-badge himr-badge--queue-${player.queue_state}`">
                  {{ player.queue_state }}
                </span>
              </td>
              <td>
                <span v-if="player.candidates.length === 0" class="himr-muted">none</span>
                <span v-else class="himr-candidates">
                  {{ player.candidates.map(c => c.canonical_player_name).join(', ') }}
                </span>
              </td>
              <td class="himr-actions-cell">
                <button
                  type="button"
                  class="himr-btn himr-btn--sm himr-btn--link"
                  :data-testid="`himr-link-player-${player.source_player_id}`"
                  :disabled="actionLoading"
                  @click="openPlayerLinkModal(player)"
                >
                  Link
                </button>
                <button
                  type="button"
                  class="himr-btn himr-btn--sm himr-btn--create"
                  :data-testid="`himr-create-player-${player.source_player_id}`"
                  :disabled="actionLoading"
                  @click="openPlayerCreateModal(player)"
                >
                  Create
                </button>
                <button
                  type="button"
                  class="himr-btn himr-btn--sm himr-btn--defer"
                  :data-testid="`himr-defer-player-${player.source_player_id}`"
                  :disabled="actionLoading"
                  @click="deferPlayer(player)"
                >
                  Defer
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Unresolved Venues Table -->
    <section v-if="lastLoaded" class="himr-section">
      <h4 class="himr-section-title">
        Unresolved Venues
        <span class="himr-count">{{ filteredVenues.length }}</span>
      </h4>

      <div v-if="filteredVenues.length === 0" class="himr-empty">
        No unresolved venues matching filter.
      </div>

      <div v-else class="himr-table-wrapper">
        <table class="himr-table" data-testid="himr-venues-table">
          <thead>
            <tr>
              <th>Source Venue</th>
              <th>Reason</th>
              <th>Competition</th>
              <th>Season</th>
              <th>Queue</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="venue in filteredVenues"
              :key="venue.queue_id"
              :data-testid="`himr-venue-row-${venue.queue_id}`"
            >
              <td>{{ venue.raw_imported_value }}</td>
              <td class="himr-reason">{{ venue.reason }}</td>
              <td>{{ venue.competition_name || '—' }}</td>
              <td>{{ venue.season || '—' }}</td>
              <td>
                <span :class="`himr-badge himr-badge--queue-${venue.queue_state}`">
                  {{ venue.queue_state }}
                </span>
              </td>
              <td class="himr-actions-cell">
                <button
                  type="button"
                  class="himr-btn himr-btn--sm himr-btn--link"
                  :data-testid="`himr-link-venue-${venue.queue_id}`"
                  :disabled="actionLoading"
                  @click="openVenueLinkModal(venue)"
                >
                  Link
                </button>
                <button
                  type="button"
                  class="himr-btn himr-btn--sm himr-btn--create"
                  :data-testid="`himr-create-venue-${venue.queue_id}`"
                  :disabled="actionLoading"
                  @click="openVenueCreateModal(venue)"
                >
                  Create
                </button>
                <button
                  type="button"
                  class="himr-btn himr-btn--sm himr-btn--defer"
                  :data-testid="`himr-defer-venue-${venue.queue_id}`"
                  :disabled="actionLoading"
                  @click="deferVenue(venue)"
                >
                  Defer
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Player Link Modal -->
    <div v-if="playerLinkModal.visible" class="himr-modal-overlay" data-testid="himr-player-link-modal">
      <div class="himr-modal">
        <h4>Link Player: {{ playerLinkModal.player?.source_player_name }}</h4>
        <p class="himr-modal-info">
          Enter the canonical Player ID to link this source player to.
          This action is auditable and idempotent.
        </p>
        <label class="himr-field">
          Canonical Player ID
          <input
            v-model.number="playerLinkModal.canonicalPlayerId"
            type="number"
            placeholder="e.g. 42"
            data-testid="himr-player-link-id-input"
          />
        </label>
        <div v-if="playerLinkModal.candidates?.length" class="himr-candidates-list">
          <p class="himr-candidates-label">Suggested candidates:</p>
          <div
            v-for="c in playerLinkModal.candidates"
            :key="c.canonical_player_id"
            class="himr-candidate-item"
          >
            <button
              type="button"
              class="himr-btn himr-btn--sm himr-btn--candidate"
              @click="playerLinkModal.canonicalPlayerId = c.canonical_player_id"
            >
              Use
            </button>
            <span>{{ c.canonical_player_name }} (id={{ c.canonical_player_id }}, {{ c.role || 'unknown role' }})</span>
          </div>
        </div>
        <div class="himr-modal-footer">
          <button
            type="button"
            class="himr-btn himr-btn--primary"
            :disabled="!playerLinkModal.canonicalPlayerId || actionLoading"
            data-testid="himr-player-link-confirm-btn"
            @click="confirmPlayerLink"
          >
            {{ actionLoading ? 'Linking…' : 'Confirm Link' }}
          </button>
          <button type="button" class="himr-btn" @click="closeModals">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Player Create Modal -->
    <div v-if="playerCreateModal.visible" class="himr-modal-overlay" data-testid="himr-player-create-modal">
      <div class="himr-modal">
        <h4>Create Player from: {{ playerCreateModal.player?.source_player_name }}</h4>
        <p class="himr-modal-info">
          This will create a new internal Player. Source provenance is preserved.
          Check for duplicate names before confirming.
        </p>
        <label class="himr-field">
          Name *
          <input
            v-model="playerCreateModal.name"
            type="text"
            placeholder="Full canonical name"
            data-testid="himr-player-create-name-input"
          />
        </label>
        <label class="himr-field">
          Country
          <input v-model="playerCreateModal.country" type="text" placeholder="e.g. West Indies" />
        </label>
        <label class="himr-field">
          Role
          <input v-model="playerCreateModal.role" type="text" placeholder="e.g. Batter" />
        </label>
        <div class="himr-modal-footer">
          <button
            type="button"
            class="himr-btn himr-btn--primary"
            :disabled="!playerCreateModal.name?.trim() || actionLoading"
            data-testid="himr-player-create-confirm-btn"
            @click="confirmPlayerCreate"
          >
            {{ actionLoading ? 'Creating…' : 'Confirm Create' }}
          </button>
          <button type="button" class="himr-btn" @click="closeModals">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Venue Link Modal -->
    <div v-if="venueLinkModal.visible" class="himr-modal-overlay" data-testid="himr-venue-link-modal">
      <div class="himr-modal">
        <h4>Link Venue: {{ venueLinkModal.venue?.raw_imported_value }}</h4>
        <p class="himr-modal-info">
          Enter the canonical Venue ID to link this source venue to.
          An alias will be created automatically.
        </p>
        <label class="himr-field">
          Canonical Venue ID (UUID)
          <input
            v-model="venueLinkModal.canonicalVenueId"
            type="text"
            placeholder="e.g. 3f2504e0-4f89-11d3-9a0c-0305e82c3301"
            data-testid="himr-venue-link-id-input"
          />
        </label>
        <div class="himr-modal-footer">
          <button
            type="button"
            class="himr-btn himr-btn--primary"
            :disabled="!venueLinkModal.canonicalVenueId?.trim() || actionLoading"
            data-testid="himr-venue-link-confirm-btn"
            @click="confirmVenueLink"
          >
            {{ actionLoading ? 'Linking…' : 'Confirm Link' }}
          </button>
          <button type="button" class="himr-btn" @click="closeModals">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Venue Create Modal -->
    <div v-if="venueCreateModal.visible" class="himr-modal-overlay" data-testid="himr-venue-create-modal">
      <div class="himr-modal">
        <h4>Create Venue from: {{ venueCreateModal.venue?.raw_imported_value }}</h4>
        <p class="himr-modal-info">
          This will create a new internal Venue record preserving source provenance.
        </p>
        <label class="himr-field">
          Canonical Name *
          <input
            v-model="venueCreateModal.canonicalName"
            type="text"
            placeholder="e.g. Kensington Oval"
            data-testid="himr-venue-create-name-input"
          />
        </label>
        <label class="himr-field">
          City
          <input v-model="venueCreateModal.city" type="text" placeholder="e.g. Bridgetown" />
        </label>
        <label class="himr-field">
          Country
          <input v-model="venueCreateModal.country" type="text" placeholder="e.g. Barbados" />
        </label>
        <div class="himr-modal-footer">
          <button
            type="button"
            class="himr-btn himr-btn--primary"
            :disabled="!venueCreateModal.canonicalName?.trim() || actionLoading"
            data-testid="himr-venue-create-confirm-btn"
            @click="confirmVenueCreate"
          >
            {{ actionLoading ? 'Creating…' : 'Confirm Create' }}
          </button>
          <button type="button" class="himr-btn" @click="closeModals">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import {
  getIdentityReviewUnresolved,
  identityReviewPlayerLink,
  identityReviewPlayerCreate,
  identityReviewPlayerDefer,
  identityReviewVenueLink,
  identityReviewVenueCreate,
  identityReviewVenueDefer,
  type HistoricalPlayerReviewItem,
  type HistoricalVenueReviewItem,
} from '@/services/api'

// State
const loading = ref(false)
const actionLoading = ref(false)
const loadError = ref<string | null>(null)
const actionSuccess = ref<string | null>(null)
const actionError = ref<string | null>(null)
const lastLoaded = ref(false)

const players = ref<HistoricalPlayerReviewItem[]>([])
const venues = ref<HistoricalVenueReviewItem[]>([])
const totalUnresolvedPlayers = ref(0)
const totalUnresolvedVenues = ref(0)

// Filters
const filterText = ref('')
const filterStatus = ref('')

const filteredPlayers = computed(() => {
  let result = players.value
  if (filterText.value.trim()) {
    const q = filterText.value.trim().toLowerCase()
    result = result.filter(
      p =>
        p.source_player_name.toLowerCase().includes(q) ||
        (p.reason || '').toLowerCase().includes(q) ||
        p.competition_references.some(c =>
          JSON.stringify(c).toLowerCase().includes(q),
        ),
    )
  }
  if (filterStatus.value) {
    result = result.filter(
      p => p.resolution_state === filterStatus.value || p.queue_state === filterStatus.value,
    )
  }
  return result
})

const filteredVenues = computed(() => {
  let result = venues.value
  if (filterText.value.trim()) {
    const q = filterText.value.trim().toLowerCase()
    result = result.filter(
      v =>
        v.raw_imported_value.toLowerCase().includes(q) ||
        v.reason.toLowerCase().includes(q) ||
        (v.competition_name || '').toLowerCase().includes(q),
    )
  }
  if (filterStatus.value) {
    result = result.filter(v => v.queue_state === filterStatus.value)
  }
  return result
})

// Modals
const playerLinkModal = reactive<{
  visible: boolean
  player: HistoricalPlayerReviewItem | null
  canonicalPlayerId: number | null
  candidates: HistoricalPlayerReviewItem['candidates']
}>({
  visible: false,
  player: null,
  canonicalPlayerId: null,
  candidates: [],
})

const playerCreateModal = reactive<{
  visible: boolean
  player: HistoricalPlayerReviewItem | null
  name: string
  country: string
  role: string
}>({
  visible: false,
  player: null,
  name: '',
  country: '',
  role: '',
})

const venueLinkModal = reactive<{
  visible: boolean
  venue: HistoricalVenueReviewItem | null
  canonicalVenueId: string
}>({ visible: false, venue: null, canonicalVenueId: '' })

const venueCreateModal = reactive<{
  visible: boolean
  venue: HistoricalVenueReviewItem | null
  canonicalName: string
  city: string
  country: string
}>({ visible: false, venue: null, canonicalName: '', city: '', country: '' })

function closeModals() {
  playerLinkModal.visible = false
  playerLinkModal.player = null
  playerLinkModal.canonicalPlayerId = null
  playerLinkModal.candidates = []

  playerCreateModal.visible = false
  playerCreateModal.player = null
  playerCreateModal.name = ''
  playerCreateModal.country = ''
  playerCreateModal.role = ''

  venueLinkModal.visible = false
  venueLinkModal.venue = null
  venueLinkModal.canonicalVenueId = ''

  venueCreateModal.visible = false
  venueCreateModal.venue = null
  venueCreateModal.canonicalName = ''
  venueCreateModal.city = ''
  venueCreateModal.country = ''

  actionSuccess.value = null
  actionError.value = null
}

// Load unresolved
async function loadUnresolved() {
  loading.value = true
  loadError.value = null
  actionSuccess.value = null
  actionError.value = null
  try {
    const data = await getIdentityReviewUnresolved()
    players.value = data.unresolved_players
    venues.value = data.unresolved_venues
    totalUnresolvedPlayers.value = data.total_unresolved_players
    totalUnresolvedVenues.value = data.total_unresolved_venues
    lastLoaded.value = true
  } catch (err: unknown) {
    loadError.value = err instanceof Error ? err.message : 'Failed to load identity review data.'
  } finally {
    loading.value = false
  }
}

// Player modals
function openPlayerLinkModal(player: HistoricalPlayerReviewItem) {
  playerLinkModal.player = player
  playerLinkModal.canonicalPlayerId = player.candidates[0]?.canonical_player_id ?? null
  playerLinkModal.candidates = player.candidates
  playerLinkModal.visible = true
}

function openPlayerCreateModal(player: HistoricalPlayerReviewItem) {
  playerCreateModal.player = player
  playerCreateModal.name = player.source_player_name
  playerCreateModal.country = ''
  playerCreateModal.role = ''
  playerCreateModal.visible = true
}

// Venue modals
function openVenueLinkModal(venue: HistoricalVenueReviewItem) {
  venueLinkModal.venue = venue
  venueLinkModal.canonicalVenueId = ''
  venueLinkModal.visible = true
}

function openVenueCreateModal(venue: HistoricalVenueReviewItem) {
  venueCreateModal.venue = venue
  venueCreateModal.canonicalName = venue.raw_imported_value
  venueCreateModal.city = ''
  venueCreateModal.country = ''
  venueCreateModal.visible = true
}

// Actions
async function confirmPlayerLink() {
  if (!playerLinkModal.player || !playerLinkModal.canonicalPlayerId) return
  actionLoading.value = true
  actionError.value = null
  actionSuccess.value = null
  try {
    const result = await identityReviewPlayerLink(playerLinkModal.player.source_player_id, {
      canonical_player_id: playerLinkModal.canonicalPlayerId,
    })
    actionSuccess.value = result.message || `Linked to player id=${result.canonical_player_id}.`
    closeModals()
    await loadUnresolved()
  } catch (err: unknown) {
    actionError.value = err instanceof Error ? err.message : 'Link action failed.'
  } finally {
    actionLoading.value = false
  }
}

async function confirmPlayerCreate() {
  if (!playerCreateModal.player || !playerCreateModal.name.trim()) return
  actionLoading.value = true
  actionError.value = null
  actionSuccess.value = null
  try {
    const result = await identityReviewPlayerCreate(playerCreateModal.player.source_player_id, {
      name: playerCreateModal.name.trim(),
      country: playerCreateModal.country.trim() || null,
      role: playerCreateModal.role.trim() || null,
    })
    actionSuccess.value = result.message || `Created player '${result.canonical_player_name}'.`
    closeModals()
    await loadUnresolved()
  } catch (err: unknown) {
    actionError.value = err instanceof Error ? err.message : 'Create action failed.'
  } finally {
    actionLoading.value = false
  }
}

async function deferPlayer(player: HistoricalPlayerReviewItem) {
  if (!confirm(`Defer '${player.source_player_name}'? They will remain in the registry.`)) return
  actionLoading.value = true
  actionError.value = null
  actionSuccess.value = null
  try {
    const result = await identityReviewPlayerDefer(player.source_player_id, {
      reason: 'deferred',
    })
    actionSuccess.value = result.message || `Player '${player.source_player_name}' deferred.`
    await loadUnresolved()
  } catch (err: unknown) {
    actionError.value = err instanceof Error ? err.message : 'Defer action failed.'
  } finally {
    actionLoading.value = false
  }
}

async function confirmVenueLink() {
  if (!venueLinkModal.venue || !venueLinkModal.canonicalVenueId.trim()) return
  actionLoading.value = true
  actionError.value = null
  actionSuccess.value = null
  try {
    const result = await identityReviewVenueLink({
      queue_id: venueLinkModal.venue.queue_id,
      canonical_venue_id: venueLinkModal.canonicalVenueId.trim(),
    })
    actionSuccess.value = result.message || `Linked to venue '${result.canonical_venue_name}'.`
    closeModals()
    await loadUnresolved()
  } catch (err: unknown) {
    actionError.value = err instanceof Error ? err.message : 'Link action failed.'
  } finally {
    actionLoading.value = false
  }
}

async function confirmVenueCreate() {
  if (!venueCreateModal.venue || !venueCreateModal.canonicalName.trim()) return
  actionLoading.value = true
  actionError.value = null
  actionSuccess.value = null
  try {
    const result = await identityReviewVenueCreate({
      queue_id: venueCreateModal.venue.queue_id,
      canonical_name: venueCreateModal.canonicalName.trim(),
      city: venueCreateModal.city.trim() || null,
      country: venueCreateModal.country.trim() || null,
    })
    actionSuccess.value = result.message || `Created venue '${result.canonical_venue_name}'.`
    closeModals()
    await loadUnresolved()
  } catch (err: unknown) {
    actionError.value = err instanceof Error ? err.message : 'Create action failed.'
  } finally {
    actionLoading.value = false
  }
}

async function deferVenue(venue: HistoricalVenueReviewItem) {
  if (!confirm(`Defer venue '${venue.raw_imported_value}'? It will remain in the queue.`)) return
  actionLoading.value = true
  actionError.value = null
  actionSuccess.value = null
  try {
    const result = await identityReviewVenueDefer({
      queue_id: venue.queue_id,
      reason: 'deferred',
    })
    actionSuccess.value = result.message || `Venue '${venue.raw_imported_value}' deferred.`
    await loadUnresolved()
  } catch (err: unknown) {
    actionError.value = err instanceof Error ? err.message : 'Defer action failed.'
  } finally {
    actionLoading.value = false
  }
}
</script>

<style scoped>
.himr-panel {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 1.5rem;
  background: var(--aw-card-bg, #fff);
  border: 1px solid var(--aw-border, #e5e7eb);
  border-radius: 8px;
}

.himr-header {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.himr-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0;
}

.himr-subtitle {
  font-size: 0.875rem;
  color: var(--aw-muted, #6b7280);
  margin: 0;
}

.himr-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.himr-meta {
  font-size: 0.875rem;
  color: var(--aw-muted, #6b7280);
}

.himr-error-banner {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 4px;
  padding: 0.625rem 0.875rem;
  color: #b91c1c;
  font-size: 0.875rem;
}

.himr-success-banner {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 4px;
  padding: 0.625rem 0.875rem;
  color: #166534;
  font-size: 0.875rem;
}

.himr-filters {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.himr-filter-input,
.himr-filter-select {
  padding: 0.375rem 0.625rem;
  border: 1px solid var(--aw-border, #e5e7eb);
  border-radius: 4px;
  font-size: 0.875rem;
  min-width: 220px;
}

.himr-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.himr-section-title {
  font-size: 0.95rem;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.himr-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--aw-primary, #2563eb);
  color: #fff;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 700;
  min-width: 1.4rem;
  height: 1.4rem;
  padding: 0 0.4rem;
}

.himr-table-wrapper {
  overflow-x: auto;
  border: 1px solid var(--aw-border, #e5e7eb);
  border-radius: 6px;
}

.himr-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

.himr-table th {
  background: var(--aw-table-header-bg, #f9fafb);
  padding: 0.5rem 0.75rem;
  text-align: left;
  font-weight: 600;
  border-bottom: 1px solid var(--aw-border, #e5e7eb);
  white-space: nowrap;
}

.himr-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--aw-border, #e5e7eb);
  vertical-align: middle;
}

.himr-table tr:last-child td {
  border-bottom: none;
}

.himr-mono {
  font-family: monospace;
  font-size: 0.75rem;
  color: var(--aw-muted, #6b7280);
}

.himr-reason {
  font-size: 0.75rem;
  color: var(--aw-muted, #6b7280);
  max-width: 160px;
}

.himr-muted {
  color: var(--aw-muted, #6b7280);
  font-size: 0.75rem;
}

.himr-candidates {
  font-size: 0.75rem;
  color: var(--aw-primary, #2563eb);
}

.himr-actions-cell {
  white-space: nowrap;
  display: flex;
  gap: 0.25rem;
  align-items: center;
}

.himr-empty {
  color: var(--aw-muted, #6b7280);
  font-size: 0.875rem;
  padding: 0.5rem 0;
}

.himr-btn {
  padding: 0.375rem 0.75rem;
  border-radius: 4px;
  border: 1px solid var(--aw-border, #e5e7eb);
  background: var(--aw-btn-bg, #fff);
  font-size: 0.875rem;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.15s, color 0.15s;
}

.himr-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.himr-btn--primary {
  background: var(--aw-primary, #2563eb);
  color: #fff;
  border-color: var(--aw-primary, #2563eb);
}

.himr-btn--sm {
  padding: 0.2rem 0.5rem;
  font-size: 0.75rem;
}

.himr-btn--link {
  background: #eff6ff;
  color: #1d4ed8;
  border-color: #bfdbfe;
}

.himr-btn--create {
  background: #f0fdf4;
  color: #15803d;
  border-color: #bbf7d0;
}

.himr-btn--defer {
  background: #fefce8;
  color: #a16207;
  border-color: #fde68a;
}

.himr-btn--candidate {
  background: #f0f9ff;
  color: #0369a1;
  border-color: #bae6fd;
}

.himr-badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.himr-badge--unresolved { background: #fef9c3; color: #854d0e; }
.himr-badge--ambiguous { background: #fce7f3; color: #9d174d; }
.himr-badge--blocked { background: #fee2e2; color: #991b1b; }
.himr-badge--auto_resolved { background: #dcfce7; color: #166534; }
.himr-badge--manually_resolved { background: #d1fae5; color: #065f46; }
.himr-badge--queue-pending { background: #fef3c7; color: #92400e; }
.himr-badge--queue-deferred { background: #e0f2fe; color: #0369a1; }
.himr-badge--queue-resolved { background: #dcfce7; color: #166534; }
.himr-badge--queue-no_queue_entry { background: #f1f5f9; color: #64748b; }

.himr-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.himr-modal {
  background: #fff;
  border-radius: 8px;
  padding: 1.5rem;
  max-width: 480px;
  width: 100%;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.himr-modal h4 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.himr-modal-info {
  font-size: 0.875rem;
  color: var(--aw-muted, #6b7280);
  margin: 0;
}

.himr-field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.875rem;
  font-weight: 500;
}

.himr-field input {
  padding: 0.375rem 0.625rem;
  border: 1px solid var(--aw-border, #e5e7eb);
  border-radius: 4px;
  font-size: 0.875rem;
}

.himr-modal-footer {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

.himr-candidates-list {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.himr-candidates-label {
  font-size: 0.8125rem;
  font-weight: 600;
  margin: 0;
}

.himr-candidate-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
}
</style>

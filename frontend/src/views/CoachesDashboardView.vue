<!-- frontend/src/views/CoachesDashboardView.vue -->
<template>
  <div class="coaches-page">
    <BaseCard as="section" padding="lg" class="coaches-dashboard">
      <header class="dashboard-header">
        <div class="title-block">
          <h1>Coaches Dashboard</h1>
          <p class="subtitle">Quick view of team performance and current match state.</p>
        </div>
        <div class="header-actions">
          <BaseInput
            v-model="selectedTeam"
            placeholder="Select team..."
            class="team-selector"
          />
          <BaseButton variant="secondary" size="sm" @click="openScoring">
            Open Scoring Console
          </BaseButton>
          <BaseButton variant="ghost" size="sm" @click="openAnalyst">
            Analyst Workspace
          </BaseButton>
        </div>
      </header>

      <div class="grid">
        <!-- Left column: match snapshot + key players -->
        <div class="grid-main">
          <!-- Match Snapshot -->
          <BaseCard as="section" padding="md" class="match-snapshot">
            <div class="section-header">
              <h2>Current Match</h2>
              <BaseBadge :variant="matchStatusVariant">{{ matchStatus }}</BaseBadge>
            </div>

            <div v-if="hasActiveMatch" class="scoreboard-container">
              <LiveMatchCardCoach
                :game-id="currentGameId"
                :can-action="true"
              />
            </div>
            <div v-else class="empty-state">
              <p>No active match. Start a new match from the Setup screen.</p>
              <BaseButton variant="primary" size="sm" @click="goToSetup">
                Go to Setup
              </BaseButton>
            </div>
          </BaseCard>

          <!-- Key Players -->
          <BaseCard as="section" padding="md" class="key-players">
            <div class="section-header">
              <h2>Key Players</h2>
            </div>

            <div class="players-grid">
              <div
                v-for="player in keyPlayers"
                :key="player.id"
                class="player-card"
              >
                <div class="player-info">
                  <span class="player-name">{{ player.name }}</span>
                  <div class="player-roles">
                    <BaseBadge
                      v-for="role in player.roles"
                      :key="role"
                      variant="neutral"
                      condensed
                    >
                      {{ role }}
                    </BaseBadge>
                  </div>
                </div>
                <div class="player-stats">
                  <div class="stat">
                    <span class="stat-value">{{ player.runs }}</span>
                    <span class="stat-label">Runs</span>
                  </div>
                  <div class="stat">
                    <span class="stat-value">{{ player.wickets }}</span>
                    <span class="stat-label">Wkts</span>
                  </div>
                  <div class="stat">
                    <span class="stat-value">{{ player.avg }}</span>
                    <span class="stat-label">Avg</span>
                  </div>
                </div>
              </div>
            </div>
          </BaseCard>
        </div>

        <!-- Right column: quick stats + notes -->
        <aside class="grid-side">
          <!-- Quick Stats -->
          <BaseCard as="section" padding="md" class="quick-stats">
            <h3>Season Overview</h3>
            <div class="stats-grid">
              <div class="stat-tile">
                <span class="stat-value">{{ seasonStats.matches }}</span>
                <span class="stat-label">Matches</span>
              </div>
              <div class="stat-tile">
                <span class="stat-value">{{ seasonStats.wins }}</span>
                <span class="stat-label">Wins</span>
              </div>
              <div class="stat-tile">
                <span class="stat-value">{{ seasonStats.losses }}</span>
                <span class="stat-label">Losses</span>
              </div>
              <div class="stat-tile">
                <span class="stat-value">{{ seasonStats.nrr }}</span>
                <span class="stat-label">NRR</span>
              </div>
            </div>
          </BaseCard>

          <!-- Coach Notes -->
          <BaseCard as="section" padding="md" class="coach-notes">
            <h3>Coach Notes</h3>
            <textarea
              v-model="coachNote"
              class="notes-input"
              placeholder="Add notes about tactics, player form, or upcoming match prep..."
              rows="6"
            />
            <div class="notes-actions">
              <BaseButton
                variant="primary"
                size="sm"
                :disabled="!coachNote.trim()"
                @click="saveNote"
              >
                Save Note
              </BaseButton>
              <span v-if="noteSaved" class="note-saved">✓ Saved</span>
            </div>
            <!-- TODO: Persist notes to backend / local storage -->
          </BaseCard>

          <!-- Quick Links -->
          <BaseCard as="section" padding="md" class="quick-links">
            <h3>Quick Links</h3>
            <div class="links-list">
              <BaseButton variant="ghost" size="sm" full-width @click="goToLeaderboard">
                View Leaderboard
              </BaseButton>
              <BaseButton variant="ghost" size="sm" full-width @click="goToAnalytics">
                Team Analytics
              </BaseButton>
              <BaseButton variant="ghost" size="sm" full-width @click="goToVideoSessions">
                Video Sessions (Plus)
              </BaseButton>
            </div>
          </BaseCard>
        </aside>
      </div>

      <!-- Development Dashboard -->
      <div class="dev-dashboard-section" style="margin-top: 2rem">
        <DevDashboardWidget />
      </div>
    </BaseCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

import { BaseCard, BaseButton, BaseBadge, BaseInput } from '@/components'
import DevDashboardWidget from '@/components/DevDashboardWidget.vue'
import LiveMatchCardCoach from '@/components/LiveMatchCardCoach.vue'
import { useGameStore } from '@/stores/gameStore'

const router = useRouter()
const gameStore = useGameStore()

// --- Selectors (readonly) ---
const selectedTeam = ref('')

// Pull current game ID from store if available
const currentGameId = computed(() => gameStore.currentGame?.id ?? '')
const hasActiveMatch = computed(() => !!currentGameId.value)

const matchStatus = computed(() => {
  if (!hasActiveMatch.value) return 'NO MATCH'
  const status = gameStore.currentGame?.status
  if (status === 'IN_PROGRESS') return 'LIVE'
  if (status === 'COMPLETED') return 'COMPLETED'
  return status ?? 'PENDING'
})

const matchStatusVariant = computed(() => {
  switch (matchStatus.value) {
    case 'LIVE':
      return 'success'
    case 'COMPLETED':
      return 'neutral'
    case 'NO MATCH':
      return 'warning'
    default:
      return 'neutral'
  }
})

// --- Key Players (FIX A5: Use real scorecard data) ---
const keyPlayers = computed(() => {
  const battingScorecard = gameStore.currentGame?.batting_scorecard ?? {}
  const bowlingScorecard = gameStore.currentGame?.bowling_scorecard ?? {}
  
  // Combine batting and bowling stats for players
  const playerStats: Record<string, any> = {}
  
  // Add batting stats
  Object.entries(battingScorecard).forEach(([id, stats]) => {
    playerStats[id] = {
      id,
      name: stats.player_name,
      runs: stats.runs,
      ballsFaced: stats.balls_faced,
      wickets: 0,
      roles: [] as string[]
    }
  })
  
  // Add bowling stats
  Object.entries(bowlingScorecard).forEach(([id, stats]) => {
    if (playerStats[id]) {
      playerStats[id].wickets = stats.wickets_taken
    } else {
      playerStats[id] = {
        id,
        name: stats.player_name,
        runs: 0,
        ballsFaced: 0,
        wickets: stats.wickets_taken,
        roles: [] as string[]
      }
    }
  })
  
  // Calculate average and sort by impact
  return Object.values(playerStats)
    .map(p => ({
      ...p,
      avg: p.ballsFaced > 0 ? (p.runs / p.ballsFaced * 100) : 0,  // Strike rate
    }))
    .sort((a, b) => (b.runs + b.wickets * 20) - (a.runs + a.wickets * 20))  // Simple impact score
    .slice(0, 6)
})

// --- Season Stats (TODO: Wire to API when org endpoints ready) ---
const seasonStats = ref({
  matches: 0,
  wins: 0,
  losses: 0,
  nrr: '—',
})
// Note: Blocked by backend - needs GET /organizations/{orgId}/stats

// --- Coach Notes (local only for now) ---
const coachNote = ref('')
const noteSaved = ref(false)

function saveNote() {
  // TODO: Persist to backend or local storage
  noteSaved.value = true
  setTimeout(() => {
    noteSaved.value = false
  }, 2000)
}

// --- Navigation Actions ---
function openScoring() {
  if (currentGameId.value) {
    router.push({ name: 'GameScoringView', params: { gameId: currentGameId.value } })
  } else {
    router.push({ name: 'setup' })
  }
}

function openAnalyst() {
  router.push({ name: 'AnalystWorkspace' })
}

function goToSetup() {
  router.push({ name: 'setup' })
}

function goToLeaderboard() {
  router.push({ name: 'leaderboard' })
}

function goToAnalytics() {
  router.push({ name: 'AnalyticsView' })
}

function goToVideoSessions() {
  router.push({ name: 'CoachProPlusVideoSessions' })
}
</script>

<style scoped>
.coaches-page {
  min-height: 100vh;
  padding: var(--space-lg);
  background: var(--color-background, var(--color-surface));
}

.coaches-dashboard {
  max-width: 1200px;
  margin: 0 auto;
}

/* Header */
.dashboard-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-md);
  margin-bottom: var(--space-xl);
}

.title-block h1 {
  margin: 0 0 var(--space-xs);
  font-size: var(--text-2xl);
}

.subtitle {
  margin: 0;
  color: var(--color-muted);
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-sm);
}

.team-selector {
  min-width: 180px;
}

/* Grid Layout */
.grid {
  display: grid;
  gap: var(--space-lg);
  grid-template-columns: 1fr;
}

@media (min-width: 768px) {
  .grid {
    grid-template-columns: 2fr 1fr;
  }
}

.grid-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.grid-side {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

/* Section Headers */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
}

.section-header h2 {
  margin: 0;
  font-size: var(--text-lg);
}

/* Match Snapshot */
.scoreboard-container {
  margin-top: var(--space-sm);
}

.empty-state {
  text-align: center;
  padding: var(--space-xl) var(--space-md);
  color: var(--color-muted);
}

.empty-state p {
  margin: 0 0 var(--space-md);
}

/* Key Players */
.players-grid {
  display: grid;
  gap: var(--space-sm);
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}

.player-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  padding: var(--space-md);
  background: var(--color-surface-alt);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.player-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.player-name {
  font-weight: 600;
  font-size: var(--text-md);
}

.player-roles {
  display: flex;
  gap: var(--space-xs);
}

.player-stats {
  display: flex;
  gap: var(--space-md);
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-weight: 700;
  font-size: var(--text-lg);
  color: var(--color-primary);
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--color-muted);
}

/* Quick Stats */
.quick-stats h3,
.coach-notes h3,
.quick-links h3 {
  margin: 0 0 var(--space-md);
  font-size: var(--text-md);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-sm);
}

.stat-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-md);
  background: var(--color-surface-alt);
  border-radius: var(--radius-md);
  text-align: center;
}

.stat-tile .stat-value {
  font-size: var(--text-xl);
}

.stat-tile .stat-label {
  font-size: var(--text-sm);
}

/* Coach Notes */
.notes-input {
  width: 100%;
  padding: var(--space-md);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-alt);
  color: var(--color-on-surface);
  font-family: inherit;
  font-size: var(--text-sm);
  resize: vertical;
}

.notes-input::placeholder {
  color: var(--color-muted);
}

.notes-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-top: var(--space-sm);
}

.note-saved {
  color: var(--color-success);
  font-size: var(--text-sm);
}

/* Quick Links */
.links-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}
</style>

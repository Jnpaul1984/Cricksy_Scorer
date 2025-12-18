<template>
  <div class="dev-dashboard">
    <div class="dashboard-header">
      <h2 class="dashboard-title">👥 Development Dashboard</h2>
      <p class="dashboard-subtitle">Track your players' progress and development focus</p>
    </div>

    <!-- Filters -->
    <div class="dashboard-filters">
      <div class="filter-group">
        <label class="filter-label">Filter by Role</label>
        <div class="filter-buttons">
          <button
            v-for="role in roles"
            :key="role.value"
            class="filter-btn"
            :class="{ active: selectedRole === role.value }"
            @click="selectedRole = role.value"
          >
            {{ role.icon }} {{ role.label }}
          </button>
        </div>
      </div>
      <div class="filter-group">
        <label class="filter-label">Sort by</label>
        <select v-model="sortBy" class="sort-select">
          <option value="form">Recent Form</option>
          <option value="name">Player Name</option>
          <option value="matches">Matches Played</option>
          <option value="focus">Development Focus</option>
        </select>
      </div>
    </div>

    <!-- Players Grid -->
    <div class="dashboard-grid">
      <div v-if="filteredPlayers.length === 0" class="empty-state">
        <p class="empty-message">No players found with selected filters</p>
      </div>

      <div v-for="player in filteredPlayers" :key="player.player_id" class="player-card">
        <!-- Card Header -->
        <div class="card-header">
          <div class="player-identity">
            <div class="player-avatar">{{ playerInitials(player) }}</div>
            <div class="player-meta">
              <h3 class="player-name">{{ player.player_name }}</h3>
              <p class="player-role">{{ player.role || 'Player' }}</p>
            </div>
          </div>
          <div class="player-status" :class="`status-${getFormStatus(player)}`">
            {{ getFormLabel(player) }}
          </div>
        </div>

        <!-- Card Body -->
        <div class="card-body">
          <!-- Recent Form -->
          <section class="card-section">
            <h4 class="section-title">📈 Recent Form</h4>
            <div class="form-indicator">
              <div v-for="(match, idx) in player.recentMatches.slice(0, 5)" :key="`match-${idx}`" class="form-dot" :class="getFormColor(match.performance)" :title="`Match ${idx + 1}: ${match.performance}`" />
            </div>
            <p class="form-stats">
              <span class="stat">Avg: {{ player.batting_average.toFixed(1) }}</span>
              <span class="stat">SR: {{ player.strike_rate.toFixed(0) }}</span>
            </p>
          </section>

          <!-- Next Match -->
          <section class="card-section">
            <h4 class="section-title">🏏 Next Match</h4>
            <div v-if="player.nextMatch" class="next-match">
              <p class="match-info">
                <strong>{{ player.nextMatch.opponent }}</strong>
              </p>
              <p class="match-date">{{ formatDate(player.nextMatch.date) }}</p>
              <div class="match-format">{{ player.nextMatch.format }}</div>
            </div>
            <div v-else class="no-match">
              <p>No upcoming matches scheduled</p>
            </div>
          </section>

          <!-- Development Focus -->
          <section class="card-section">
            <h4 class="section-title">🎯 Focus Areas</h4>
            <div class="focus-items">
              <div v-for="(focus, idx) in player.developmentFocus" :key="`focus-${idx}`" class="focus-item">
                <span class="focus-icon">{{ focus.icon }}</span>
                <span class="focus-text">{{ focus.name }}</span>
                <span class="focus-priority" :class="`priority-${focus.priority}`">{{ focus.priority }}</span>
              </div>
            </div>
          </section>

          <!-- Stats Row -->
          <section class="card-section stats-section">
            <div class="stat-box">
              <span class="stat-label">Matches</span>
              <span class="stat-value">{{ player.total_matches }}</span>
            </div>
            <div class="stat-box">
              <span class="stat-label">Runs</span>
              <span class="stat-value">{{ player.total_runs_scored }}</span>
            </div>
            <div class="stat-box">
              <span class="stat-label">Wickets</span>
              <span class="stat-value">{{ player.total_wickets }}</span>
            </div>
          </section>
        </div>

        <!-- Card Footer -->
        <div class="card-footer">
          <BaseButton variant="ghost" size="sm" @click="viewPlayerProfile(player.player_id)">
            View Profile →
          </BaseButton>
        </div>
      </div>
    </div>

    <!-- Summary Stats -->
    <div v-if="filteredPlayers.length > 0" class="dashboard-summary">
      <div class="summary-box">
        <span class="summary-label">Total Players</span>
        <span class="summary-value">{{ filteredPlayers.length }}</span>
      </div>
      <div class="summary-box">
        <span class="summary-label">Avg Form</span>
        <span class="summary-value">{{ averageForm }}%</span>
      </div>
      <div class="summary-box">
        <span class="summary-label">Focus Areas</span>
        <span class="summary-value">{{ topFocusArea }}</span>
      </div>
      <div class="summary-box">
        <span class="summary-label">Total Matches</span>
        <span class="summary-value">{{ totalMatches }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { BaseButton } from '@/components'
import type { PlayerProfile } from '@/types/player'

interface PlayerMetadata {
  recentMatches: Array<{ performance: 'excellent' | 'good' | 'average' | 'poor' }>
  nextMatch?: { opponent: string; date: string; format: string }
  developmentFocus: Array<{ icon: string; name: string; priority: 'high' | 'medium' | 'low' }>
  role?: string
}

interface PlayerWithMetadata extends PlayerProfile, PlayerMetadata {}

const props = defineProps<{
  players?: PlayerProfile[]
}>()

const router = useRouter()

const selectedRole = ref<'all' | 'batter' | 'bowler' | 'all-rounder'>('all')
const sortBy = ref<'form' | 'name' | 'matches' | 'focus'>('form')

const roles = [
  { value: 'all' as const, label: 'All Players', icon: '👥' },
  { value: 'batter' as const, label: 'Batters', icon: '🏏' },
  { value: 'bowler' as const, label: 'Bowlers', icon: '⚾' },
  { value: 'all-rounder' as const, label: 'All-Rounders', icon: '⭐' },
]

// Generate mock metadata for players
function enrichPlayerData(player: PlayerProfile): PlayerWithMetadata {
  const recentMatches = Array.from({ length: 5 }, () => {
    const rand = Math.random()
    if (rand > 0.7) return { performance: 'excellent' as const }
    if (rand > 0.4) return { performance: 'good' as const }
    if (rand > 0.15) return { performance: 'average' as const }
    return { performance: 'poor' as const }
  })

  const nextMatch =
    Math.random() > 0.3
      ? {
          opponent: ['India', 'Australia', 'England', 'Pakistan', 'South Africa'][Math.floor(Math.random() * 5)],
          date: new Date(Date.now() + Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
          format: ['T20', 'ODI', 'Test'][Math.floor(Math.random() * 3)],
        }
      : undefined

  const allFocusAreas = [
    { icon: '⚔️', name: 'Strike Rate Improvement', priority: 'high' as const },
    { icon: '🎯', name: 'Consistency', priority: 'medium' as const },
    { icon: '🛡️', name: 'Defensive Batting', priority: 'low' as const },
    { icon: '📈', name: 'Bowling Accuracy', priority: 'high' as const },
    { icon: '🔄', name: 'Rotation Play', priority: 'medium' as const },
    { icon: '⏱️', name: 'Death Bowling', priority: 'high' as const },
  ]

  const developmentFocus = allFocusAreas.slice(Math.floor(Math.random() * 3), Math.floor(Math.random() * 3) + 2)

  return {
    ...player,
    recentMatches,
    nextMatch,
    developmentFocus,
  }
}

// Generate enriched players list
const enrichedPlayers = computed((): PlayerWithMetadata[] => {
  if (!props.players || props.players.length === 0) {
    // Generate sample players if none provided
    return [
      {
        player_id: '1',
        player_name: 'Virat Kohli',
        role: 'batter',
        total_matches: 120,
        total_runs_scored: 5500,
        total_wickets: 0,
        batting_average: 55.2,
        strike_rate: 142.5,
        recentMatches: [
          { performance: 'excellent' },
          { performance: 'good' },
          { performance: 'excellent' },
          { performance: 'average' },
          { performance: 'good' },
        ],
        nextMatch: {
          opponent: 'India',
          date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          format: 'T20',
        },
        developmentFocus: [
          { icon: '⚔️', name: 'Strike Rate', priority: 'high' },
          { icon: '🎯', name: 'Consistency', priority: 'medium' },
        ],
      } as PlayerWithMetadata,
      {
        player_id: '2',
        player_name: 'Jasprit Bumrah',
        role: 'bowler',
        total_matches: 95,
        total_runs_scored: 150,
        total_wickets: 120,
        batting_average: 2.5,
        strike_rate: 0,
        recentMatches: [
          { performance: 'good' },
          { performance: 'good' },
          { performance: 'excellent' },
          { performance: 'good' },
          { performance: 'average' },
        ],
        nextMatch: {
          opponent: 'Australia',
          date: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString(),
          format: 'ODI',
        },
        developmentFocus: [
          { icon: '📈', name: 'Yorker Accuracy', priority: 'high' },
          { icon: '⏱️', name: 'Death Bowling', priority: 'high' },
        ],
      } as PlayerWithMetadata,
      {
        player_id: '3',
        player_name: 'MS Dhoni',
        role: 'all-rounder',
        total_matches: 135,
        total_runs_scored: 6200,
        total_wickets: 50,
        batting_average: 50.8,
        strike_rate: 138.2,
        recentMatches: [
          { performance: 'excellent' },
          { performance: 'poor' },
          { performance: 'good' },
          { performance: 'excellent' },
          { performance: 'good' },
        ],
        nextMatch: {
          opponent: 'Pakistan',
          date: new Date(Date.now() + 21 * 24 * 60 * 60 * 1000).toISOString(),
          format: 'T20',
        },
        developmentFocus: [
          { icon: '🎯', name: 'Consistency', priority: 'medium' },
          { icon: '🛡️', name: 'Defensive Batting', priority: 'low' },
        ],
      } as PlayerWithMetadata,
    ]
  }

  return (props.players || []).map(enrichPlayerData) as PlayerWithMetadata[]
})

// Filtered and sorted players
const filteredPlayers = computed((): PlayerWithMetadata[] => {
  let result = enrichedPlayers.value

  // Filter by role
  if (selectedRole.value !== 'all') {
    result = result.filter((p) => (p.role || '').toLowerCase() === selectedRole.value)
  }

  // Sort
  if (sortBy.value === 'name') {
    result.sort((a, b) => a.player_name.localeCompare(b.player_name))
  } else if (sortBy.value === 'matches') {
    result.sort((a, b) => b.total_matches - a.total_matches)
  } else if (sortBy.value === 'focus') {
    result.sort((a, b) => b.developmentFocus.length - a.developmentFocus.length)
  } else {
    // form - sort by recent performance
    result.sort((a, b) => getFormScore(b) - getFormScore(a))
  }

  return result
})

// Helper functions
function playerInitials(player: PlayerProfile): string {
  return player.player_name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

function getFormScore(player: PlayerWithMetadata): number {
  const scores = { excellent: 4, good: 3, average: 2, poor: 1 }
  return player.recentMatches.reduce((sum, m) => sum + scores[m.performance], 0) / player.recentMatches.length
}

function getFormStatus(player: PlayerWithMetadata): 'excellent' | 'good' | 'average' | 'poor' {
  const score = getFormScore(player)
  if (score >= 3.5) return 'excellent'
  if (score >= 2.5) return 'good'
  if (score >= 1.5) return 'average'
  return 'poor'
}

function getFormLabel(player: PlayerWithMetadata): string {
  const status = getFormStatus(player)
  return `Form: ${status.charAt(0).toUpperCase() + status.slice(1)}`
}

function getFormColor(performance: string): string {
  const map: Record<string, string> = {
    excellent: 'form-excellent',
    good: 'form-good',
    average: 'form-average',
    poor: 'form-poor',
  }
  return map[performance] || 'form-average'
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
}

function viewPlayerProfile(playerId: string) {
  router.push({ name: 'PlayerProfile', params: { id: playerId } })
}

// Summary computations
const averageForm = computed(() => {
  if (filteredPlayers.value.length === 0) return 0
  const avg =
    (filteredPlayers.value.reduce((sum, p) => sum + getFormScore(p) * 25, 0) /
      filteredPlayers.value.length) |
    0
  return Math.max(0, Math.min(100, avg))
})

const topFocusArea = computed(() => {
  const allFocusAreas = filteredPlayers.value.flatMap((p) => p.developmentFocus.map((f) => f.name))
  if (allFocusAreas.length === 0) return 'None'
  const counts: Record<string, number> = {}
  allFocusAreas.forEach((area) => {
    counts[area] = (counts[area] || 0) + 1
  })
  const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]
  return top ? top[0] : 'None'
})

const totalMatches = computed(() => {
  return filteredPlayers.value.reduce((sum, p) => sum + p.total_matches, 0)
})
</script>

<style scoped>
.dev-dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding: var(--space-4);
}

/* Header */
.dashboard-header {
  margin-bottom: var(--space-2);
}

.dashboard-title {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--h2-size);
  font-weight: var(--h2-weight);
  color: var(--color-text);
}

.dashboard-subtitle {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Filters */
.dashboard-filters {
  display: flex;
  gap: var(--space-4);
  flex-wrap: wrap;
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.filter-label {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text);
}

.filter-buttons {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.filter-btn {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.filter-btn:hover {
  border-color: var(--color-primary);
  background: var(--color-bg-secondary);
}

.filter-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.sort-select {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: border-color 0.2s ease;
}

.sort-select:focus {
  outline: none;
  border-color: var(--color-primary);
}

/* Grid */
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--space-4);
}

.empty-state {
  grid-column: 1 / -1;
  padding: var(--space-8) var(--space-4);
  text-align: center;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px dashed var(--color-border);
}

.empty-message {
  margin: 0;
  font-size: var(--text-base);
  color: var(--color-text-muted);
}

/* Card */
.player-card {
  display: flex;
  flex-direction: column;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: all 0.3s ease;
}

.player-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
}

/* Card Header */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
}

.player-identity {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  flex: 1;
}

.player-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: white;
  font-weight: 700;
  font-size: var(--text-sm);
  flex-shrink: 0;
}

.player-meta {
  min-width: 0;
}

.player-name {
  margin: 0;
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.player-role {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-transform: capitalize;
}

.player-status {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}

.status-excellent {
  background: #dcfce7;
  color: #166534;
}

.status-good {
  background: #fef3c7;
  color: #92400e;
}

.status-average {
  background: #fed7aa;
  color: #92400e;
}

.status-poor {
  background: #fee2e2;
  color: #991b1b;
}

/* Card Body */
.card-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  flex: 1;
}

.card-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.section-title {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text);
}

/* Recent Form */
.form-indicator {
  display: flex;
  gap: 4px;
}

.form-dot {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.form-dot:hover {
  transform: scale(1.15);
}

.form-excellent {
  background: #10b981;
}

.form-good {
  background: #84cc16;
}

.form-average {
  background: #f59e0b;
}

.form-poor {
  background: #ef4444;
}

.form-stats {
  display: flex;
  gap: var(--space-3);
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.stat {
  display: inline-block;
}

/* Next Match */
.next-match {
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--color-primary);
}

.match-info {
  margin: 0 0 var(--space-1) 0;
  font-size: var(--text-sm);
  color: var(--color-text);
  font-weight: 500;
}

.match-date {
  margin: 0 0 var(--space-1) 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.match-format {
  display: inline-block;
  padding: 2px var(--space-2);
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: 600;
}

.no-match {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  font-style: italic;
}

/* Focus Items */
.focus-items {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.focus-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  border-left: 2px solid var(--color-primary);
  font-size: var(--text-sm);
}

.focus-icon {
  font-size: var(--text-base);
  flex-shrink: 0;
}

.focus-text {
  flex: 1;
  color: var(--color-text);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.focus-priority {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 2px;
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  flex-shrink: 0;
}

.priority-high {
  background: #fee2e2;
  color: #991b1b;
}

.priority-medium {
  background: #fed7aa;
  color: #92400e;
}

.priority-low {
  background: #dcfce7;
  color: #166534;
}

/* Stats Section */
.stats-section {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
}

.stat-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-2);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  text-align: center;
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: 500;
}

.stat-value {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-text);
  margin-top: 2px;
}

/* Card Footer */
.card-footer {
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--color-border);
  background: var(--color-bg);
  text-align: right;
}

/* Summary Stats */
.dashboard-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}

.summary-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: var(--space-1);
}

.summary-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.summary-value {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-primary);
}

/* Responsive */
@media (max-width: 768px) {
  .dashboard-filters {
    flex-direction: column;
  }

  .filter-buttons {
    width: 100%;
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .dashboard-summary {
    grid-template-columns: repeat(2, 1fr);
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .stats-section {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>

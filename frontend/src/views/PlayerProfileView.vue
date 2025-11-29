<template>
  <div class="player-profile-view">
    <div class="container">
      <!-- Loading State -->
      <div v-if="loading" class="loading-container">
        <div class="loading-spinner" aria-busy="true"></div>
        <p>Loading player profile…</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="error-container">
        <div class="error-card">
          <div class="error-icon">⚠️</div>
          <h2>Unable to Load Profile</h2>
          <p>{{ error }}</p>
          <button class="retry-btn" @click="loadProfile">Try Again</button>
        </div>
      </div>

      <!-- Profile Content -->
      <div v-else-if="profile" class="profile-content">
        <!-- Player Header -->
        <header class="player-header">
          <div class="player-avatar">{{ playerInitials }}</div>
          <div class="player-info">
            <div class="player-name-row">
              <h1>{{ profile.player_name }}</h1>
              <span class="role-badge" :class="roleClass">{{ playerRole }}</span>
              <button
                class="follow-btn"
                :class="{ following: isFavorite, loading: isTogglingFavorite }"
                :disabled="isTogglingFavorite"
                :title="isFavorite ? 'Unfollow this player' : 'Follow this player'"
                @click="toggleFavorite"
              >
                <span v-if="isTogglingFavorite" class="btn-spinner"></span>
                <span v-else-if="isFavorite">★ Following</span>
                <span v-else>☆ Follow</span>
              </button>
            </div>
            <div v-if="favoriteError" class="favorite-error">{{ favoriteError }}</div>
            <div class="player-meta">
              <span class="meta-item">🏏 {{ profile.total_matches }} matches</span>
              <span class="meta-item subdued">ID: {{ profile.player_id.slice(0, 8) }}…</span>
            </div>
          </div>
        </header>

        <!-- Tab Navigation -->
        <nav class="tabs-nav">
          <button
            :class="['tab-btn', { active: activeTab === 'overview' }]"
            data-tab="overview"
            @click="activeTab = 'overview'"
          >
            Overview
          </button>
          <button
            :class="['tab-btn', { active: activeTab === 'batting' }]"
            data-tab="batting"
            @click="activeTab = 'batting'"
          >
            Batting
          </button>
          <button
            :class="['tab-btn', { active: activeTab === 'bowling' }]"
            data-tab="bowling"
            @click="activeTab = 'bowling'"
          >
            Bowling
          </button>
        </nav>

        <!-- Tab Content -->
        <div class="tab-content">
          <!-- Overview Tab -->
          <div v-if="activeTab === 'overview'" class="tab-panel">
            <!-- Key Stats Grid -->
            <div class="overview-stats-grid">
              <div class="stat-card">
                <div class="stat-value">{{ profile.total_matches }}</div>
                <div class="stat-label">Matches</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">{{ profile.total_runs_scored.toLocaleString() }}</div>
                <div class="stat-label">Runs</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">{{ profile.total_wickets }}</div>
                <div class="stat-label">Wickets</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">{{ formatStat(profile.strike_rate) }}</div>
                <div class="stat-label">Strike Rate</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">{{ formatStat(profile.batting_average) }}</div>
                <div class="stat-label">Batting Avg</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">{{ formatStat(profile.economy_rate) }}</div>
                <div class="stat-label">Economy</div>
              </div>
            </div>

            <!-- Fielding Summary -->
            <div class="fielding-summary">
              <h3>🧤 Fielding</h3>
              <div class="fielding-stats">
                <span><strong>{{ profile.catches }}</strong> catches</span>
                <span><strong>{{ profile.stumpings }}</strong> stumpings</span>
                <span><strong>{{ profile.run_outs }}</strong> run outs</span>
              </div>
            </div>

            <!-- Achievements Section -->
            <section v-if="profile.achievements && profile.achievements.length > 0" class="achievements-section">
              <h3>🏆 Achievements</h3>
              <div class="achievements-list">
                <span
                  v-for="achievement in profile.achievements"
                  :key="achievement.id"
                  class="achievement-pill"
                  :title="achievement.description"
                >
                  {{ achievement.badge_icon || '🏅' }} {{ achievement.title }}
                </span>
              </div>
            </section>
            <p v-else class="no-achievements">No achievements yet. Keep playing to earn badges!</p>
          </div>

          <!-- Batting Tab -->
          <div v-else-if="activeTab === 'batting'" class="tab-panel">
            <h3>🏏 Batting Statistics</h3>
            <dl class="stats-list">
              <div class="stats-row">
                <dt>Innings</dt>
                <dd>{{ profile.total_innings_batted }}</dd>
              </div>
              <div class="stats-row">
                <dt>Runs</dt>
                <dd>{{ profile.total_runs_scored.toLocaleString() }}</dd>
              </div>
              <div class="stats-row">
                <dt>Average</dt>
                <dd>{{ formatStat(profile.batting_average) }}</dd>
              </div>
              <div class="stats-row">
                <dt>Strike Rate</dt>
                <dd>{{ formatStat(profile.strike_rate) }}</dd>
              </div>
              <div class="stats-row">
                <dt>Highest Score</dt>
                <dd>{{ profile.highest_score }}</dd>
              </div>
              <div class="stats-row">
                <dt>Centuries (100s)</dt>
                <dd>{{ profile.centuries }}</dd>
              </div>
              <div class="stats-row">
                <dt>Half-Centuries (50s)</dt>
                <dd>{{ profile.half_centuries }}</dd>
              </div>
              <div class="stats-row">
                <dt>Fours</dt>
                <dd>{{ profile.total_fours }}</dd>
              </div>
              <div class="stats-row">
                <dt>Sixes</dt>
                <dd>{{ profile.total_sixes }}</dd>
              </div>
              <div class="stats-row">
                <dt>Balls Faced</dt>
                <dd>{{ profile.total_balls_faced.toLocaleString() }}</dd>
              </div>
              <div class="stats-row">
                <dt>Times Out</dt>
                <dd>{{ profile.times_out }}</dd>
              </div>
            </dl>
          </div>

          <!-- Bowling Tab -->
          <div v-else-if="activeTab === 'bowling'" class="tab-panel">
            <h3>⚾ Bowling Statistics</h3>
            <dl class="stats-list">
              <div class="stats-row">
                <dt>Innings</dt>
                <dd>{{ profile.total_innings_bowled }}</dd>
              </div>
              <div class="stats-row">
                <dt>Overs</dt>
                <dd>{{ formatStat(profile.total_overs_bowled, 1) }}</dd>
              </div>
              <div class="stats-row">
                <dt>Wickets</dt>
                <dd>{{ profile.total_wickets }}</dd>
              </div>
              <div class="stats-row">
                <dt>Average</dt>
                <dd>{{ formatStat(profile.bowling_average) }}</dd>
              </div>
              <div class="stats-row">
                <dt>Economy</dt>
                <dd>{{ formatStat(profile.economy_rate) }}</dd>
              </div>
              <div class="stats-row">
                <dt>Best Figures</dt>
                <dd>{{ profile.best_bowling_figures || '—' }}</dd>
              </div>
              <div class="stats-row">
                <dt>5-Wicket Hauls</dt>
                <dd>{{ profile.five_wicket_hauls }}</dd>
              </div>
              <div class="stats-row">
                <dt>Maidens</dt>
                <dd>{{ profile.maidens }}</dd>
              </div>
              <div class="stats-row">
                <dt>Runs Conceded</dt>
                <dd>{{ profile.total_runs_conceded.toLocaleString() }}</dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'

import { apiService, getErrorMessage } from '@/services/api'
import type { FanFavoriteRead } from '@/services/api'
import { getPlayerProfile } from '@/services/playerApi'
import type { PlayerProfile } from '@/types/player'

type TabName = 'overview' | 'batting' | 'bowling'

const route = useRoute()
const loading = ref(true)
const error = ref<string | null>(null)
const profile = ref<PlayerProfile | null>(null)
const activeTab = ref<TabName>('overview')

// Fan favorites state
const isFavorite = ref(false)
const favoriteId = ref<string | null>(null)
const isTogglingFavorite = ref(false)
const favoriteError = ref<string | null>(null)

// Derive player role from stats
const playerRole = computed<string>(() => {
  if (!profile.value) return 'Player'
  const { total_wickets, total_runs_scored } = profile.value
  if (total_wickets > 10 && total_runs_scored > 200) return 'All-rounder'
  if (total_wickets >= 10) return 'Bowler'
  if (total_runs_scored >= 200) return 'Batter'
  return 'Player'
})

// Role badge class for styling
const roleClass = computed<string>(() => {
  switch (playerRole.value) {
    case 'All-rounder': return 'role-allrounder'
    case 'Bowler': return 'role-bowler'
    case 'Batter': return 'role-batter'
    default: return 'role-default'
  }
})

// Player initials for avatar
const playerInitials = computed<string>(() => {
  if (!profile.value) return '?'
  const parts = profile.value.player_name.trim().split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  }
  return parts[0].slice(0, 2).toUpperCase()
})

// Format numeric stats with fallback
const formatStat = (value: number | null | undefined, decimals = 2): string => {
  if (value === null || value === undefined || isNaN(value)) return '—'
  return value.toFixed(decimals)
}

const loadProfile = async () => {
  loading.value = true
  error.value = null

  try {
    const playerId = route.params.playerId as string
    if (!playerId) {
      throw new Error('No player ID provided')
    }
    profile.value = await getPlayerProfile(playerId)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load player profile'
  } finally {
    loading.value = false
  }
}

// Load current user's favorites and check if this player is followed
const loadFavorites = async () => {
  if (!profile.value) return

  try {
    const favorites: FanFavoriteRead[] = await apiService.getFanFavorites()
    const match = favorites.find(
      (f) => f.favorite_type === 'player' && f.player_profile_id === profile.value?.player_id
    )
    if (match) {
      isFavorite.value = true
      favoriteId.value = match.id
    } else {
      isFavorite.value = false
      favoriteId.value = null
    }
  } catch (err) {
    // Silently fail - user may not be logged in
    console.warn('Failed to load favorites:', getErrorMessage(err))
  }
}

// Toggle follow/unfollow for current player
const toggleFavorite = async () => {
  if (!profile.value || isTogglingFavorite.value) return

  isTogglingFavorite.value = true
  favoriteError.value = null

  try {
    if (isFavorite.value && favoriteId.value) {
      // Unfollow
      await apiService.deleteFanFavorite(favoriteId.value)
      isFavorite.value = false
      favoriteId.value = null
    } else {
      // Follow
      const newFavorite = await apiService.createFanFavorite({
        favorite_type: 'player',
        player_profile_id: profile.value.player_id,
      })
      isFavorite.value = true
      favoriteId.value = newFavorite.id
    }
  } catch (err) {
    favoriteError.value = getErrorMessage(err)
    console.error('Failed to toggle favorite:', err)
  } finally {
    isTogglingFavorite.value = false
  }
}

onMounted(async () => {
  await loadProfile()
  await loadFavorites()
})
</script>

<style scoped>
/* =====================================================
   PLAYER PROFILE VIEW - Using Design System Tokens
   ===================================================== */

.player-profile-view {
  padding: var(--space-5) 0;
  min-height: 100vh;
  background: var(--color-bg);
}

.container {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 var(--space-4);
}

/* Loading State */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-10) 0;
  gap: var(--space-4);
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: var(--radius-pill);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error State */
.error-container {
  display: flex;
  justify-content: center;
  padding: var(--space-8) 0;
}

.error-card {
  text-align: center;
  padding: var(--space-6);
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  max-width: 400px;
}

.error-icon {
  font-size: var(--text-4xl);
  margin-bottom: var(--space-4);
}

.error-card h2 {
  margin: 0 0 var(--space-2);
  font-size: var(--h3-size);
  font-weight: var(--h3-weight);
  color: var(--color-text);
}

.error-card p {
  color: var(--color-text-muted);
  margin-bottom: var(--space-5);
}

.retry-btn {
  padding: var(--space-3) var(--space-5);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-weight: var(--font-semibold);
  transition: background var(--transition-fast);
}

.retry-btn:hover {
  background: var(--color-primary-hover);
}

/* Player Header */
.player-header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-5);
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  margin-bottom: var(--space-4);
}

.player-avatar {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-pill);
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
  color: var(--color-text-inverse);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  flex-shrink: 0;
}

.player-info {
  flex: 1;
  min-width: 0;
}

.player-name-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.player-name-row h1 {
  margin: 0;
  font-size: var(--h2-size);
  font-weight: var(--h2-weight);
  line-height: var(--h2-leading);
  color: var(--color-text);
}

.role-badge {
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-pill);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.role-allrounder {
  background: var(--color-success-soft);
  color: var(--color-success);
}

.role-bowler {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}

.role-batter {
  background: var(--color-info-soft);
  color: var(--color-info);
}

.role-default {
  background: var(--color-surface-hover);
  color: var(--color-text-muted);
}

/* Follow Button */
.follow-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--color-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.follow-btn:hover:not(:disabled) {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.follow-btn.following {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.follow-btn.following:hover:not(:disabled) {
  background: var(--color-error);
  border-color: var(--color-error);
}

.follow-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.follow-btn .btn-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: var(--radius-pill);
  animation: spin 0.8s linear infinite;
}

.favorite-error {
  color: var(--color-error);
  font-size: var(--text-xs);
  margin-top: var(--space-1);
}

.player-meta {
  display: flex;
  gap: var(--space-4);
  margin-top: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.meta-item.subdued {
  opacity: 0.7;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

/* Tab Navigation */
.tabs-nav {
  display: flex;
  gap: var(--space-2);
  background: var(--color-surface);
  padding: var(--space-2);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  margin-bottom: var(--space-4);
}

.tab-btn {
  flex: 1;
  padding: var(--space-3) var(--space-4);
  border: none;
  background: transparent;
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tab-btn:hover {
  background: var(--color-surface-hover);
}

.tab-btn.active {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

/* Tab Content */
.tab-content {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  padding: var(--space-5);
}

.tab-panel h3 {
  margin: 0 0 var(--space-4);
  font-size: var(--h4-size);
  font-weight: var(--h4-weight);
  color: var(--color-text);
}

/* Overview Stats Grid */
.overview-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-5);
}

.stat-card {
  text-align: center;
  padding: var(--space-4) var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  transition: transform var(--transition-fast);
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-card .stat-value {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-primary);
  line-height: var(--leading-tight);
}

.stat-card .stat-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: var(--space-1);
}

/* Fielding Summary */
.fielding-summary {
  padding: var(--space-4);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-5);
}

.fielding-summary h3 {
  margin: 0 0 var(--space-3) !important;
  font-size: var(--text-base) !important;
}

.fielding-stats {
  display: flex;
  gap: var(--space-5);
  flex-wrap: wrap;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.fielding-stats strong {
  color: var(--color-text);
}

/* Achievements */
.achievements-section h3 {
  margin-bottom: var(--space-3) !important;
}

.achievements-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.achievement-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: linear-gradient(135deg, var(--color-accent), var(--color-warning));
  color: #5d4037;
  border-radius: var(--radius-pill);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: default;
  transition: transform var(--transition-fast);
}

.achievement-pill:hover {
  transform: scale(1.05);
}

.no-achievements {
  text-align: center;
  color: var(--color-text-muted);
  padding: var(--space-6) 0;
  font-style: italic;
}

/* Stats List (Batting/Bowling tabs) */
.stats-list {
  margin: 0;
  padding: 0;
}

.stats-row {
  display: flex;
  justify-content: space-between;
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-border);
}

.stats-row:last-child {
  border-bottom: none;
}

.stats-row dt {
  color: var(--color-text-muted);
  font-weight: var(--font-normal);
}

.stats-row dd {
  margin: 0;
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

/* Responsive */
@media (max-width: 600px) {
  .player-header {
    flex-direction: column;
    text-align: center;
  }

  .player-name-row {
    justify-content: center;
  }

  .player-meta {
    justify-content: center;
    flex-wrap: wrap;
  }

  .overview-stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .stat-card .stat-value {
    font-size: var(--text-xl);
  }

  .tabs-nav {
    flex-wrap: wrap;
  }

  .tab-btn {
    flex: none;
    min-width: calc(33% - var(--space-2));
  }
}
</style>

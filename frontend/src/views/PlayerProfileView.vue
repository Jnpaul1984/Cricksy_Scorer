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
            </div>
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

import { getPlayerProfile } from '@/services/playerApi'
import type { PlayerProfile } from '@/types/player'

type TabName = 'overview' | 'batting' | 'bowling'

const route = useRoute()
const loading = ref(true)
const error = ref<string | null>(null)
const profile = ref<PlayerProfile | null>(null)
const activeTab = ref<TabName>('overview')

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

onMounted(() => {
  loadProfile()
})
</script>

<style scoped>
.player-profile-view {
  padding: 1.5rem 0;
  min-height: 100vh;
  background: var(--background-color, #f5f5f5);
}

.container {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 1rem;
}

/* Loading State */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 0;
  gap: 1rem;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--muted-border-color, #e0e0e0);
  border-top-color: var(--primary, #1976d2);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error State */
.error-container {
  display: flex;
  justify-content: center;
  padding: 3rem 0;
}

.error-card {
  text-align: center;
  padding: 2rem;
  background: var(--card-background-color, #fff);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  max-width: 400px;
}

.error-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.error-card h2 {
  margin: 0 0 0.5rem;
  font-size: 1.25rem;
}

.error-card p {
  color: var(--muted-color, #666);
  margin-bottom: 1.5rem;
}

.retry-btn {
  padding: 0.75rem 1.5rem;
  background: var(--primary, #1976d2);
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.2s;
}

.retry-btn:hover {
  background: var(--primary-hover, #1565c0);
}

/* Player Header */
.player-header {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 1.5rem;
  background: var(--card-background-color, #fff);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-bottom: 1rem;
}

.player-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary, #1976d2), #42a5f5);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  font-weight: 700;
  flex-shrink: 0;
}

.player-info {
  flex: 1;
  min-width: 0;
}

.player-name-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.player-name-row h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color, #222);
}

.role-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.role-allrounder {
  background: #e8f5e9;
  color: #2e7d32;
}

.role-bowler {
  background: #fff3e0;
  color: #e65100;
}

.role-batter {
  background: #e3f2fd;
  color: #1565c0;
}

.role-default {
  background: #f5f5f5;
  color: #666;
}

.player-meta {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
  font-size: 0.9rem;
  color: var(--muted-color, #666);
}

.meta-item.subdued {
  opacity: 0.7;
  font-family: monospace;
  font-size: 0.8rem;
}

/* Tab Navigation */
.tabs-nav {
  display: flex;
  gap: 0.5rem;
  background: var(--card-background-color, #fff);
  padding: 0.5rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-bottom: 1rem;
}

.tab-btn {
  flex: 1;
  padding: 0.75rem 1rem;
  border: none;
  background: transparent;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--muted-color, #666);
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  background: var(--muted-border-color, #f0f0f0);
}

.tab-btn.active {
  background: var(--primary, #1976d2);
  color: #fff;
}

/* Tab Content */
.tab-content {
  background: var(--card-background-color, #fff);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 1.5rem;
}

.tab-panel h3 {
  margin: 0 0 1rem;
  font-size: 1.1rem;
  color: var(--color, #222);
}

/* Overview Stats Grid */
.overview-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  text-align: center;
  padding: 1.25rem 1rem;
  background: var(--background-color, #f8f9fa);
  border-radius: 10px;
  transition: transform 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-card .stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--primary, #1976d2);
  line-height: 1.2;
}

.stat-card .stat-label {
  font-size: 0.8rem;
  color: var(--muted-color, #666);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 0.25rem;
}

/* Fielding Summary */
.fielding-summary {
  padding: 1rem;
  background: var(--background-color, #f8f9fa);
  border-radius: 10px;
  margin-bottom: 1.5rem;
}

.fielding-summary h3 {
  margin: 0 0 0.75rem !important;
  font-size: 1rem !important;
}

.fielding-stats {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
  font-size: 0.9rem;
  color: var(--muted-color, #666);
}

.fielding-stats strong {
  color: var(--color, #222);
}

/* Achievements */
.achievements-section h3 {
  margin-bottom: 0.75rem !important;
}

.achievements-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.achievement-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.8rem;
  background: linear-gradient(135deg, #ffd54f, #ffb300);
  color: #5d4037;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: default;
  transition: transform 0.2s;
}

.achievement-pill:hover {
  transform: scale(1.05);
}

.no-achievements {
  text-align: center;
  color: var(--muted-color, #888);
  padding: 2rem 0;
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
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--muted-border-color, #eee);
}

.stats-row:last-child {
  border-bottom: none;
}

.stats-row dt {
  color: var(--muted-color, #666);
  font-weight: 400;
}

.stats-row dd {
  margin: 0;
  font-weight: 600;
  color: var(--color, #222);
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
    font-size: 1.4rem;
  }

  .tabs-nav {
    flex-wrap: wrap;
  }

  .tab-btn {
    flex: none;
    min-width: calc(33% - 0.5rem);
  }
}
</style>

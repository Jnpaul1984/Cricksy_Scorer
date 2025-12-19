<script setup lang="ts">
import { computed, ref, watch } from 'vue'

export interface PlayerCareerSummary {
  player_id: string
  player_name: string
  career_summary: string
  batting_stats: {
    matches: number
    total_runs: number
    average: number
    consistency_score: number
    strike_rate: number
    boundary_percentage: number
    fours: number
    sixes: number
    best_score: number
    worst_score: number
    fifties: number
    centuries: number
    out_percentage: number
    dismissal_rate: number
  }
  bowling_stats: {
    matches: number
    total_wickets: number
    total_overs: number
    runs_conceded: number
    economy_rate: number
    average_wickets_per_match: number
    maiden_percentage: number
    maidens: number
  }
  specialization: string
  specialization_confidence: number
  recent_form: {
    recent_matches: number
    recent_runs: number
    recent_average: number
    recent_strike_rate: number
    recent_wickets: number
    trend: 'improving' | 'declining' | 'stable'
    last_match_performance: string
  }
  best_performances: {
    best_batting?: {
      runs: number
      balls_faced: number
      fours: number
      sixes: number
      date: string
    }
    best_bowling?: {
      wickets: number
      overs: number
      runs_conceded: number
      economy: number
      date: string
    }
  }
  career_highlights: string[]
}

interface Props {
  summary: PlayerCareerSummary | null
  loading?: boolean
  error?: string | null
  compact?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
  compact: false,
})

const showFullStats = ref(false)

// Specialization badge styling
const specializationColor = computed(() => {
  if (!props.summary) return '#9ca3af'
  const spec = props.summary.specialization.toLowerCase()
  const colors: Record<string, string> = {
    'opener': '#3b82f6',        // Blue
    'finisher': '#f59e0b',      // Amber
    'bowler': '#ef4444',        // Red
    'all-rounder': '#8b5cf6',   // Purple
    'batter': '#10b981',        // Green
  }
  return colors[spec] || '#9ca3af'
})

const specializationBgColor = computed(() => {
  if (!props.summary) return 'rgba(156, 163, 175, 0.1)'
  const spec = props.summary.specialization.toLowerCase()
  const colors: Record<string, string> = {
    'opener': 'rgba(59, 130, 246, 0.1)',      // Blue
    'finisher': 'rgba(245, 158, 11, 0.1)',    // Amber
    'bowler': 'rgba(239, 68, 68, 0.1)',       // Red
    'all-rounder': 'rgba(139, 92, 246, 0.1)', // Purple
    'batter': 'rgba(16, 185, 129, 0.1)',      // Green
  }
  return colors[spec] || 'rgba(156, 163, 175, 0.1)'
})

// Trend arrow indicator
const trendArrow = computed(() => {
  if (!props.summary) return '→'
  const trend = props.summary.recent_form.trend
  if (trend === 'improving') return '📈'
  if (trend === 'declining') return '📉'
  return '→'
})

const trendText = computed(() => {
  if (!props.summary) return 'No data'
  return props.summary.recent_form.trend.charAt(0).toUpperCase() + 
         props.summary.recent_form.trend.slice(1)
})
</script>

<template>
  <div class="player-career-summary" :class="{ compact }">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading player career data...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <p>⚠️ {{ error }}</p>
    </div>

    <!-- Main Content -->
    <div v-else-if="summary" class="summary-content">
      <!-- Header Section -->
      <div class="summary-header">
        <div class="player-info">
          <h2 class="player-name">{{ summary.player_name }}</h2>
          <div
            class="specialization-badge"
            :style="{ backgroundColor: specializationBgColor, borderColor: specializationColor }"
          >
            <span class="badge-label">{{ summary.specialization }}</span>
            <span class="badge-confidence">{{ (summary.specialization_confidence * 100).toFixed(0) }}%</span>
          </div>
        </div>

        <!-- Quick Stats -->
        <div class="quick-stats">
          <div v-if="summary.batting_stats.matches" class="stat-pill">
            <span class="stat-value">{{ summary.batting_stats.matches }}</span>
            <span class="stat-label">Matches</span>
          </div>
          <div v-if="summary.batting_stats.total_runs" class="stat-pill">
            <span class="stat-value">{{ summary.batting_stats.total_runs }}</span>
            <span class="stat-label">Runs</span>
          </div>
          <div v-if="summary.batting_stats.average" class="stat-pill">
            <span class="stat-value">{{ summary.batting_stats.average }}</span>
            <span class="stat-label">Avg</span>
          </div>
        </div>
      </div>

      <!-- Career Summary Text -->
      <div class="summary-text">
        <p>{{ summary.career_summary }}</p>
      </div>

      <!-- Career Highlights -->
      <div class="highlights-section">
        <h3>Career Highlights</h3>
        <ul class="highlights-list">
          <li v-for="(highlight, idx) in summary.career_highlights" :key="idx">
            {{ highlight }}
          </li>
        </ul>
      </div>

      <!-- Recent Form -->
      <div class="recent-form-section">
        <h3>Recent Form</h3>
        <div class="form-metrics">
          <div class="form-metric">
            <span class="form-label">Trend</span>
            <div class="trend-indicator">
              <span class="trend-arrow">{{ trendArrow }}</span>
              <span class="trend-text">{{ trendText }}</span>
            </div>
          </div>
          <div class="form-metric">
            <span class="form-label">Recent Avg</span>
            <span class="form-value">{{ summary.recent_form.recent_average.toFixed(1) }}</span>
          </div>
          <div class="form-metric">
            <span class="form-label">Last Match</span>
            <span class="form-value">{{ summary.recent_form.last_match_performance }}</span>
          </div>
        </div>
      </div>

      <!-- Batting Stats Section -->
      <div v-if="summary.batting_stats.matches" class="stats-section">
        <div class="stats-header">
          <h3>🏏 Batting Statistics</h3>
          <button @click="showFullStats = !showFullStats" class="toggle-btn">
            {{ showFullStats ? '▼' : '▶' }}
          </button>
        </div>

        <!-- Summary Row -->
        <div class="stats-summary">
          <div class="stat-item">
            <span class="label">Average</span>
            <span class="value">{{ summary.batting_stats.average }}</span>
          </div>
          <div class="stat-item">
            <span class="label">Strike Rate</span>
            <span class="value">{{ summary.batting_stats.strike_rate }}</span>
          </div>
          <div class="stat-item">
            <span class="label">Consistency</span>
            <div class="consistency-bar">
              <div
                class="consistency-fill"
                :style="{ width: summary.batting_stats.consistency_score + '%' }"
              ></div>
            </div>
            <span class="value-small">{{ summary.batting_stats.consistency_score.toFixed(0) }}%</span>
          </div>
        </div>

        <!-- Full Stats (Expandable) -->
        <div v-show="showFullStats" class="stats-grid">
          <div class="stat-box">
            <span class="label">Matches</span>
            <span class="large-value">{{ summary.batting_stats.matches }}</span>
          </div>
          <div class="stat-box">
            <span class="label">Total Runs</span>
            <span class="large-value">{{ summary.batting_stats.total_runs }}</span>
          </div>
          <div class="stat-box">
            <span class="label">Best Score</span>
            <span class="large-value">{{ summary.batting_stats.best_score }}</span>
          </div>
          <div class="stat-box">
            <span class="label">Centuries</span>
            <span class="large-value">{{ summary.batting_stats.centuries }}</span>
          </div>
          <div class="stat-box">
            <span class="label">Fifties</span>
            <span class="large-value">{{ summary.batting_stats.fifties }}</span>
          </div>
          <div class="stat-box">
            <span class="label">Fours</span>
            <span class="large-value">{{ summary.batting_stats.fours }}</span>
          </div>
          <div class="stat-box">
            <span class="label">Sixes</span>
            <span class="large-value">{{ summary.batting_stats.sixes }}</span>
          </div>
          <div class="stat-box">
            <span class="label">Boundary %</span>
            <span class="large-value">{{ summary.batting_stats.boundary_percentage.toFixed(1) }}%</span>
          </div>
          <div class="stat-box">
            <span class="label">Dismissal Rate</span>
            <span class="large-value">{{ summary.batting_stats.dismissal_rate.toFixed(0) }}%</span>
          </div>
        </div>

        <!-- Best Performance -->
        <div v-if="summary.best_performances.best_batting" class="best-performance">
          <h4>Best Batting Performance</h4>
          <div class="performance-details">
            <div>
              <strong>{{ summary.best_performances.best_batting.runs }}</strong> runs off
              <strong>{{ summary.best_performances.best_batting.balls_faced }}</strong> balls
            </div>
            <div>
              <strong>{{ summary.best_performances.best_batting.fours }}</strong> fours,
              <strong>{{ summary.best_performances.best_batting.sixes }}</strong> sixes
            </div>
          </div>
        </div>
      </div>

      <!-- Bowling Stats Section -->
      <div v-if="summary.bowling_stats.matches" class="stats-section bowling">
        <h3>🎱 Bowling Statistics</h3>
        <div class="bowling-stats">
          <div class="stat-item">
            <span class="label">Wickets</span>
            <span class="value">{{ summary.bowling_stats.total_wickets }}</span>
          </div>
          <div class="stat-item">
            <span class="label">Economy</span>
            <span class="value">{{ summary.bowling_stats.economy_rate }}</span>
          </div>
          <div class="stat-item">
            <span class="label">Avg/Match</span>
            <span class="value">{{ summary.bowling_stats.average_wickets_per_match.toFixed(2) }}</span>
          </div>
          <div class="stat-item">
            <span class="label">Maidens %</span>
            <span class="value">{{ summary.bowling_stats.maiden_percentage.toFixed(1) }}%</span>
          </div>
        </div>

        <!-- Best Bowling Performance -->
        <div v-if="summary.best_performances.best_bowling" class="best-performance">
          <h4>Best Bowling Performance</h4>
          <div class="performance-details">
            <div>
              <strong>{{ summary.best_performances.best_bowling.wickets }}</strong> wickets for
              <strong>{{ summary.best_performances.best_bowling.runs_conceded }}</strong> runs
            </div>
            <div>
              <strong>{{ summary.best_performances.best_bowling.overs }}</strong> overs at
              <strong>{{ summary.best_performances.best_bowling.economy }}</strong> economy
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <p>No player data available</p>
    </div>
  </div>
</template>

<style scoped>
.player-career-summary {
  background: var(--pico-card-background-color);
  border: 1px solid var(--pico-card-border-color);
  border-radius: var(--pico-border-radius);
  padding: 1.5rem;
  margin: 1rem 0;
}

.player-career-summary.compact {
  padding: 1rem;
}

/* Loading & Error States */
.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  min-height: 200px;
  color: var(--pico-muted-color);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--pico-card-border-color);
  border-top: 3px solid var(--pico-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Header Section */
.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--pico-card-border-color);
}

.player-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.player-name {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--pico-color);
}

.specialization-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  border: 2px solid;
  border-radius: 0.5rem;
  background-color: var(--pico-background-color);
}

.badge-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.badge-confidence {
  font-size: 0.65rem;
  color: var(--pico-muted-color);
}

.quick-stats {
  display: flex;
  gap: 0.75rem;
}

.stat-pill {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: var(--pico-background-color);
  border-radius: 0.5rem;
  font-size: 0.85rem;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--pico-color);
}

.stat-label {
  font-size: 0.7rem;
  color: var(--pico-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

/* Summary Text */
.summary-text {
  margin: 1rem 0;
  padding: 1rem;
  background: var(--pico-background-color);
  border-radius: var(--pico-border-radius);
  line-height: 1.6;
  color: var(--pico-color);
}

.summary-text p {
  margin: 0;
}

/* Highlights Section */
.highlights-section {
  margin: 1.5rem 0;
}

.highlights-section h3,
.recent-form-section h3,
.stats-section h3 {
  margin: 0 0 0.75rem 0;
  font-size: 1rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--pico-color);
}

.highlights-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 0.75rem;
}

.highlights-list li {
  padding: 0.75rem;
  background: var(--pico-background-color);
  border-left: 3px solid var(--pico-form-element-focus-border-color);
  border-radius: 0.25rem;
  font-size: 0.9rem;
  line-height: 1.4;
}

/* Recent Form Section */
.recent-form-section {
  margin: 1.5rem 0;
  padding: 1rem;
  background: var(--pico-background-color);
  border-radius: var(--pico-border-radius);
}

.form-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
}

.form-metric {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.form-label {
  font-size: 0.75rem;
  color: var(--pico-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.trend-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
}

.trend-arrow {
  font-size: 1.5rem;
}

.trend-text {
  color: var(--pico-color);
}

.form-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--pico-color);
}

/* Stats Section */
.stats-section {
  margin: 1.5rem 0;
  padding: 1rem;
  background: var(--pico-background-color);
  border-radius: var(--pico-border-radius);
  border-left: 3px solid var(--pico-form-element-focus-border-color);
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.toggle-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  padding: 0.25rem 0.5rem;
  color: var(--pico-muted-color);
}

.toggle-btn:hover {
  color: var(--pico-color);
}

.stats-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat-item .label {
  font-size: 0.75rem;
  color: var(--pico-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.stat-item .value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--pico-color);
}

.consistency-bar {
  width: 100%;
  height: 6px;
  background: var(--pico-card-border-color);
  border-radius: 3px;
  overflow: hidden;
}

.consistency-fill {
  height: 100%;
  background: linear-gradient(90deg, #ef4444, #f97316, #eab308, #84cc16, #22c55e);
  border-radius: 3px;
}

.value-small {
  font-size: 0.75rem;
  color: var(--pico-muted-color);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 0.75rem;
  margin: 1rem 0;
}

.stat-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.75rem;
  background: var(--pico-card-background-color);
  border: 1px solid var(--pico-card-border-color);
  border-radius: 0.5rem;
  text-align: center;
}

.stat-box .label {
  font-size: 0.7rem;
  color: var(--pico-muted-color);
  text-transform: uppercase;
  margin-bottom: 0.5rem;
}

.large-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--pico-color);
}

.best-performance {
  margin-top: 1rem;
  padding: 0.75rem;
  background: var(--pico-card-background-color);
  border: 1px dashed var(--pico-card-border-color);
  border-radius: 0.5rem;
}

.best-performance h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.85rem;
  color: var(--pico-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.performance-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.9rem;
  color: var(--pico-color);
}

.bowling-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
}

@media (max-width: 768px) {
  .summary-header {
    flex-direction: column;
  }

  .quick-stats {
    width: 100%;
    justify-content: space-around;
  }

  .highlights-list {
    grid-template-columns: 1fr;
  }

  .player-name {
    font-size: 1.5rem;
  }
}
</style>

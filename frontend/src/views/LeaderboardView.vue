<template>
  <div class="leaderboard-view">
    <div class="container">
      <header class="page-header">
        <h1>🏆 Leaderboards</h1>
        <p>Top performers across all matches</p>
      </header>

      <!-- Metric Selector -->
      <div class="metric-selector">
        <label for="metric-select">Select Metric:</label>
        <select id="metric-select" v-model="selectedMetric" @change="loadLeaderboard">
          <option value="total_runs">Most Runs</option>
          <option value="batting_average">Best Batting Average</option>
          <option value="strike_rate">Highest Strike Rate</option>
          <option value="centuries">Most Centuries</option>
          <option value="total_wickets">Most Wickets</option>
          <option value="bowling_average">Best Bowling Average</option>
          <option value="economy_rate">Best Economy Rate</option>
          <option value="five_wickets">Most 5-Wicket Hauls</option>
        </select>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="loading-container">
        <div aria-busy="true">Loading leaderboard...</div>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="error-container">
        <article>
          <header>Error</header>
          <p>{{ error }}</p>
          <footer>
            <button @click="loadLeaderboard">Retry</button>
          </footer>
        </article>
      </div>

      <!-- Leaderboard Table -->
      <div v-else-if="leaderboard" class="leaderboard-content">
        <article>
          <header>
            <h2>{{ metricTitle }}</h2>
            <small>Updated: {{ formatDate(leaderboard.updated_at) }}</small>
          </header>

          <div class="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Player</th>
                  <th>{{ metricLabel }}</th>
                  <th>Additional Stats</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="entry in leaderboard.entries"
                  :key="entry.player_id"
                  :class="{ 'top-three': entry.rank <= 3 }"
                >
                  <td>
                    <span class="rank-badge" :class="getRankClass(entry.rank)">
                      {{ getRankDisplay(entry.rank) }}
                    </span>
                  </td>
                  <td>
                    <a :href="`/players/${entry.player_id}/profile`" class="player-link">
                      {{ entry.player_name }}
                    </a>
                  </td>
                  <td class="metric-value">{{ formatValue(entry.value) }}</td>
                  <td class="additional-stats">
                    <small>{{ formatAdditionalStats(entry.additional_stats) }}</small>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="leaderboard.entries.length === 0" class="no-data">
            <p>No data available for this metric yet.</p>
          </div>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getLeaderboard } from '@/services/playerApi'
import type { Leaderboard, LeaderboardMetric } from '@/types/player'

const selectedMetric = ref<LeaderboardMetric>('total_runs')
const loading = ref(true)
const error = ref<string | null>(null)
const leaderboard = ref<Leaderboard | null>(null)

const metricTitles: Record<LeaderboardMetric, string> = {
  total_runs: 'Most Runs Scored',
  batting_average: 'Best Batting Average',
  strike_rate: 'Highest Strike Rate',
  centuries: 'Most Centuries',
  total_wickets: 'Most Wickets Taken',
  bowling_average: 'Best Bowling Average',
  economy_rate: 'Best Economy Rate',
  five_wickets: 'Most 5-Wicket Hauls',
}

const metricLabels: Record<LeaderboardMetric, string> = {
  total_runs: 'Runs',
  batting_average: 'Average',
  strike_rate: 'SR',
  centuries: '100s',
  total_wickets: 'Wickets',
  bowling_average: 'Average',
  economy_rate: 'Economy',
  five_wickets: '5W',
}

const metricTitle = computed(() => metricTitles[selectedMetric.value])
const metricLabel = computed(() => metricLabels[selectedMetric.value])

const loadLeaderboard = async () => {
  loading.value = true
  error.value = null

  try {
    leaderboard.value = await getLeaderboard(selectedMetric.value, 10)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load leaderboard'
  } finally {
    loading.value = false
  }
}

const getRankClass = (rank: number): string => {
  if (rank === 1) return 'gold'
  if (rank === 2) return 'silver'
  if (rank === 3) return 'bronze'
  return ''
}

const getRankDisplay = (rank: number): string => {
  if (rank === 1) return '🥇'
  if (rank === 2) return '🥈'
  if (rank === 3) return '🥉'
  return `#${rank}`
}

const formatValue = (value: number | string): string => {
  if (typeof value === 'number') {
    return value.toFixed(2)
  }
  return String(value)
}

const formatAdditionalStats = (stats: Record<string, unknown>): string => {
  return Object.entries(stats)
    .map(([key, value]) => {
      const label = key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
      return `${label}: ${formatValue(value as number)}`
    })
    .join(' | ')
}

const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(() => {
  loadLeaderboard()
})
</script>

<style scoped>
.leaderboard-view {
  padding: 2rem 0;
  min-height: 100vh;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.page-header {
  text-align: center;
  margin-bottom: 2rem;
}

.page-header h1 {
  margin-bottom: 0.5rem;
  color: var(--primary);
}

.page-header p {
  color: var(--muted-color);
}

.metric-selector {
  margin-bottom: 2rem;
  text-align: center;
}

.metric-selector label {
  margin-right: 1rem;
  font-weight: 600;
}

.metric-selector select {
  min-width: 250px;
}

.loading-container,
.error-container {
  text-align: center;
  padding: 3rem 0;
}

.leaderboard-content article header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.leaderboard-content article header h2 {
  margin: 0;
}

.table-responsive {
  overflow-x: auto;
}

table {
  width: 100%;
  margin-top: 1rem;
}

th {
  text-align: left;
  font-weight: 600;
  color: var(--primary);
}

td {
  vertical-align: middle;
}

.rank-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-weight: 600;
  font-size: 1.1rem;
}

.rank-badge.gold {
  background-color: #ffd700;
  color: #000;
}

.rank-badge.silver {
  background-color: #c0c0c0;
  color: #000;
}

.rank-badge.bronze {
  background-color: #cd7f32;
  color: #fff;
}

.top-three {
  background-color: var(--card-background-color);
}

.player-link {
  text-decoration: none;
  color: var(--primary);
  font-weight: 600;
}

.player-link:hover {
  text-decoration: underline;
}

.metric-value {
  font-weight: 600;
  font-size: 1.1rem;
  color: var(--primary);
}

.additional-stats {
  color: var(--muted-color);
  font-size: 0.9rem;
}

.no-data {
  text-align: center;
  padding: 2rem 0;
  color: var(--muted-color);
}

@media (max-width: 768px) {
  .leaderboard-content article header {
    flex-direction: column;
    align-items: flex-start;
  }

  .metric-selector {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .metric-selector label {
    margin-right: 0;
  }

  .metric-selector select {
    width: 100%;
  }

  table {
    font-size: 0.9rem;
  }

  .additional-stats {
    font-size: 0.75rem;
  }
}
</style>

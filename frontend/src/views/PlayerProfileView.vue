<template>
  <div class="player-profile-view">
    <div class="container">
      <!-- Loading State -->
      <div v-if="loading" class="loading-container">
        <div aria-busy="true">Loading player profile...</div>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="error-container">
        <article>
          <header>Error</header>
          <p>{{ error }}</p>
          <footer>
            <button @click="loadProfile">Retry</button>
          </footer>
        </article>
      </div>

      <!-- Profile Content -->
      <div v-else-if="profile" class="profile-content">
        <!-- Player Header -->
        <header class="player-header">
          <h1>{{ profile.player_name }}</h1>
          <p>Player ID: {{ profile.player_id }}</p>
        </header>

        <!-- Statistics Grid -->
        <div class="stats-grid">
          <!-- Batting Stats Card -->
          <article class="stats-card">
            <header>
              <h2>🏏 Batting Statistics</h2>
            </header>
            <div class="stats-content">
              <div class="stat-row">
                <span class="stat-label">Matches:</span>
                <span class="stat-value">{{ profile.total_matches }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">Innings:</span>
                <span class="stat-value">{{ profile.total_innings_batted }}</span>
              </div>
              <div class="stat-row highlight">
                <span class="stat-label">Total Runs:</span>
                <span class="stat-value">{{ profile.total_runs_scored }}</span>
              </div>
              <div class="stat-row highlight">
                <span class="stat-label">Average:</span>
                <span class="stat-value">{{ profile.batting_average.toFixed(2) }}</span>
              </div>
              <div class="stat-row highlight">
                <span class="stat-label">Strike Rate:</span>
                <span class="stat-value">{{ profile.strike_rate.toFixed(2) }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">Highest Score:</span>
                <span class="stat-value">{{ profile.highest_score }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">Centuries:</span>
                <span class="stat-value">{{ profile.centuries }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">Half Centuries:</span>
                <span class="stat-value">{{ profile.half_centuries }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">Fours:</span>
                <span class="stat-value">{{ profile.total_fours }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">Sixes:</span>
                <span class="stat-value">{{ profile.total_sixes }}</span>
              </div>
            </div>
          </article>

          <!-- Bowling Stats Card -->
          <article class="stats-card">
            <header>
              <h2>⚾ Bowling Statistics</h2>
            </header>
            <div class="stats-content">
              <div class="stat-row">
                <span class="stat-label">Innings:</span>
                <span class="stat-value">{{ profile.total_innings_bowled }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">Overs:</span>
                <span class="stat-value">{{ profile.total_overs_bowled.toFixed(1) }}</span>
              </div>
              <div class="stat-row highlight">
                <span class="stat-label">Wickets:</span>
                <span class="stat-value">{{ profile.total_wickets }}</span>
              </div>
              <div class="stat-row highlight">
                <span class="stat-label">Average:</span>
                <span class="stat-value">{{ profile.bowling_average.toFixed(2) }}</span>
              </div>
              <div class="stat-row highlight">
                <span class="stat-label">Economy:</span>
                <span class="stat-value">{{ profile.economy_rate.toFixed(2) }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">Best Figures:</span>
                <span class="stat-value">{{ profile.best_bowling_figures || 'N/A' }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">5-Wicket Hauls:</span>
                <span class="stat-value">{{ profile.five_wicket_hauls }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">Maidens:</span>
                <span class="stat-value">{{ profile.maidens }}</span>
              </div>
            </div>
          </article>

          <!-- Fielding Stats Card -->
          <article class="stats-card">
            <header>
              <h2>🧤 Fielding Statistics</h2>
            </header>
            <div class="stats-content">
              <div class="stat-row">
                <span class="stat-label">Catches:</span>
                <span class="stat-value">{{ profile.catches }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">Stumpings:</span>
                <span class="stat-value">{{ profile.stumpings }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">Run Outs:</span>
                <span class="stat-value">{{ profile.run_outs }}</span>
              </div>
            </div>
          </article>
        </div>

        <!-- Achievements Section -->
        <section class="achievements-section">
          <header>
            <h2>🏆 Achievements & Badges</h2>
          </header>
          <div v-if="profile.achievements && profile.achievements.length > 0" class="achievements-grid">
            <article
              v-for="achievement in profile.achievements"
              :key="achievement.id"
              class="achievement-card"
            >
              <div class="achievement-icon">{{ achievement.badge_icon || '🏅' }}</div>
              <div class="achievement-content">
                <h3>{{ achievement.title }}</h3>
                <p>{{ achievement.description }}</p>
                <small>Earned: {{ formatDate(achievement.earned_at) }}</small>
              </div>
            </article>
          </div>
          <p v-else class="no-achievements">No achievements yet. Keep playing to earn badges!</p>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getPlayerProfile } from '@/services/playerApi'
import type { PlayerProfile } from '@/types/player'

const route = useRoute()
const loading = ref(true)
const error = ref<string | null>(null)
const profile = ref<PlayerProfile | null>(null)

const loadProfile = async () => {
  loading.value = true
  error.value = null

  try {
    const playerId = route.params.playerId as string
    profile.value = await getPlayerProfile(playerId)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load player profile'
  } finally {
    loading.value = false
  }
}

const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

onMounted(() => {
  loadProfile()
})
</script>

<style scoped>
.player-profile-view {
  padding: 2rem 0;
  min-height: 100vh;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.loading-container,
.error-container {
  text-align: center;
  padding: 3rem 0;
}

.player-header {
  margin-bottom: 2rem;
  text-align: center;
}

.player-header h1 {
  margin-bottom: 0.5rem;
  color: var(--primary);
}

.player-header p {
  color: var(--muted-color);
  font-size: 0.9rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stats-card {
  margin-bottom: 0;
}

.stats-card header h2 {
  font-size: 1.2rem;
  margin: 0;
}

.stats-content {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--muted-border-color);
}

.stat-row:last-child {
  border-bottom: none;
}

.stat-row.highlight {
  font-weight: bold;
  color: var(--primary);
}

.stat-label {
  color: var(--muted-color);
}

.stat-value {
  font-weight: 600;
}

.achievements-section {
  margin-top: 2rem;
}

.achievements-section header h2 {
  margin-bottom: 1rem;
}

.achievements-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.achievement-card {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem;
  background: var(--card-background-color);
  border-radius: 0.5rem;
  border: 1px solid var(--card-border-color);
  margin-bottom: 0;
}

.achievement-icon {
  font-size: 2.5rem;
  line-height: 1;
}

.achievement-content h3 {
  margin: 0 0 0.25rem 0;
  font-size: 1rem;
}

.achievement-content p {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  color: var(--muted-color);
}

.achievement-content small {
  font-size: 0.75rem;
  color: var(--muted-color);
}

.no-achievements {
  text-align: center;
  color: var(--muted-color);
  padding: 2rem 0;
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .achievements-grid {
    grid-template-columns: 1fr;
  }
}
</style>

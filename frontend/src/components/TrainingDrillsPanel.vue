<template>
  <div class="training-drills-panel">
    <div class="panel-header">
      <h2>📚 Training Drills</h2>
      <p v-if="playerName" class="player-name">for {{ playerName }}</p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="state-message">
      <p>Loading recommended drills...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="state-message error">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="refresh">Retry</button>
    </div>

    <!-- Empty State -->
    <div v-else-if="!drills || drills.length === 0" class="state-message">
      <p>No training drills recommended at this time.</p>
      <p class="text-sm">Player performance is excellent! Continue current training routine.</p>
    </div>

    <!-- Drills Display -->
    <div v-else class="drills-container">
      <!-- Summary Stats -->
      <div class="summary-stats">
        <div class="stat-card">
          <div class="stat-value">{{ drills.length }}</div>
          <div class="stat-label">Total Drills</div>
        </div>
        <div class="stat-card high">
          <div class="stat-value">{{ highPriorityCount }}</div>
          <div class="stat-label">High Priority</div>
        </div>
        <div class="stat-card medium">
          <div class="stat-value">{{ mediumPriorityCount }}</div>
          <div class="stat-label">Medium Priority</div>
        </div>
        <div class="stat-card low">
          <div class="stat-value">{{ lowPriorityCount }}</div>
          <div class="stat-label">Low Priority</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ totalWeeklyHours }}</div>
          <div class="stat-label">Weekly Hours</div>
        </div>
      </div>

      <!-- Focus Areas -->
      <div v-if="focusAreas.length > 0" class="focus-areas">
        <h3>Focus Areas</h3>
        <div class="focus-tags">
          <span
            v-for="area in focusAreas"
            :key="area"
            class="focus-tag"
          >
            🎯 {{ area }}
          </span>
        </div>
      </div>

      <!-- Drills Grid -->
      <div class="drills-grid">
        <div
          v-for="drill in drills"
          :key="drill.drill_id"
          :class="['drill-card', `severity-${drill.severity.toLowerCase()}`]"
        >
          <!-- Severity Badge -->
          <div class="severity-badge">
            <span v-if="drill.severity === 'high'" class="badge high">⚠️ HIGH</span>
            <span v-else-if="drill.severity === 'medium'" class="badge medium">⚡ MEDIUM</span>
            <span v-else class="badge low">✓ LOW</span>
          </div>

          <!-- Drill Info -->
          <div class="drill-info">
            <h3 class="drill-name">{{ drill.name }}</h3>
            <p class="drill-category">{{ drill.category }}</p>
            <p class="drill-description">{{ drill.description }}</p>

            <!-- Drill Details -->
            <div class="drill-details">
              <div class="detail-item">
                <span class="detail-label">📊 Reps:</span>
                <span class="detail-value">{{ drill.reps_or_count }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">⏱️ Duration:</span>
                <span class="detail-value">{{ drill.duration_minutes }} min</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">📌 Focus:</span>
                <span class="detail-value">{{ drill.focus_area }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">💪 Difficulty:</span>
                <span class="difficulty-bar">
                  <span
                    class="difficulty-fill"
                    :style="{ width: (drill.difficulty * 10) + '%' }"
                  ></span>
                  {{ drill.difficulty }}/10
                </span>
              </div>
            </div>

            <!-- Reason -->
            <div v-if="drill.reason" class="drill-reason">
              <strong>Why this drill:</strong> {{ drill.reason }}
            </div>

            <!-- Frequency -->
            <div v-if="drill.recommended_frequency" class="drill-frequency">
              <strong>Frequency:</strong> {{ drill.recommended_frequency }}
            </div>

            <!-- Expected Improvement -->
            <div v-if="drill.expected_improvement" class="drill-improvement">
              <strong>Expected Improvement:</strong> {{ drill.expected_improvement }}
            </div>

            <!-- Action Button -->
            <button class="start-drill-btn">Start Drill</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Auto-refresh Footer -->
    <div class="footer-info">
      <p class="refresh-info">
        Auto-refreshes every 10 seconds
        <button class="refresh-btn" @click="refresh">🔄 Refresh Now</button>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

import { useTrainingDrills } from '../composables/useTrainingDrills'

interface Drill {
  drill_id: string
  name: string
  description: string
  category: string
  severity: string
  reason?: string
  reps_or_count: number
  duration_minutes: number
  focus_area: string
  difficulty: number
  recommended_frequency?: string
  expected_improvement?: string
}

const props = withDefaults(
  defineProps<{
    playerId?: string
    gameId?: string
    teamSide?: 'a' | 'b'
    autoRefresh?: boolean
    refreshIntervalSeconds?: number
  }>(),
  {
    autoRefresh: true,
    refreshIntervalSeconds: 10,
  }
)

const emit = defineEmits<{
  drillsLoaded: [drills: Drill[]]
  error: [error: string]
}>()

const {
  fetchPlayerDrills,
  fetchTeamDrills,
  loading,
  error: composableError,
} = useTrainingDrills()

const drills = ref<Drill[]>([])
const playerName = ref<string>('')
const error = ref<string>('')
let refreshInterval: number | null = null

const highPriorityCount = computed(() =>
  drills.value.filter((d) => d.severity === 'high').length
)

const mediumPriorityCount = computed(() =>
  drills.value.filter((d) => d.severity === 'medium').length
)

const lowPriorityCount = computed(() =>
  drills.value.filter((d) => d.severity === 'low').length
)

const totalWeeklyHours = computed(() => {
  const total = drills.value.reduce((sum, d) => {
    const frequency = d.recommended_frequency || 'weekly'
    let multiplier = 1
    if (frequency === 'daily') multiplier = 7
    else if (frequency === '3x/week') multiplier = 3
    else multiplier = 1 // weekly
    return sum + (d.duration_minutes * multiplier) / 60
  }, 0)
  return total.toFixed(1)
})

const focusAreas = computed(() => {
  const areas = new Set(drills.value.map((d) => d.focus_area))
  return Array.from(areas).sort()
})

async function loadDrills() {
  error.value = ''
  try {
    if (props.playerId) {
      const data = await fetchPlayerDrills(props.playerId)
      if (data) {
        playerName.value = (data as any).player_name || ''
        if (data.drill_plan?.drills) {
          drills.value = data.drill_plan.drills
        } else if ((data as any).drills) {
          drills.value = (data as any).drills
        } else {
          drills.value = []
        }
      }
    } else if (props.gameId && props.teamSide) {
      const data = await fetchTeamDrills(props.gameId, props.teamSide)
      if (data && data.team_drills && data.team_drills.length > 0) {
        // For team drills, show drills from first player
        drills.value = data.team_drills[0]?.drill_plan?.drills || []
      } else {
        drills.value = []
      }
    } else {
      error.value = 'No player or game ID provided'
      return
    }

    emit('drillsLoaded', drills.value)
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : 'Failed to load training drills'
    emit('error', error.value)
  }
}

function refresh() {
  loadDrills()
}

function startAutoRefresh() {
  if (props.autoRefresh && refreshInterval === null) {
    refreshInterval = window.setInterval(() => {
      loadDrills()
    }, props.refreshIntervalSeconds * 1000)
  }
}

function stopAutoRefresh() {
  if (refreshInterval !== null) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
}

onMounted(() => {
  loadDrills()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.training-drills-panel {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 12px;
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.panel-header {
  margin-bottom: 24px;
  text-align: center;
}

.panel-header h2 {
  font-size: 28px;
  color: #1a202c;
  margin: 0 0 8px 0;
  font-weight: 700;
}

.player-name {
  color: #666;
  font-size: 14px;
  margin: 0;
}

/* State Messages */
.state-message {
  text-align: center;
  padding: 40px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 8px;
  color: #666;
  font-size: 16px;
}

.state-message.error {
  color: #e53e3e;
  background: rgba(255, 229, 229, 0.5);
}

.state-message .text-sm {
  font-size: 13px;
  color: #999;
  margin-top: 8px;
}

.retry-btn {
  margin-top: 12px;
  padding: 8px 16px;
  background: #4299e1;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.retry-btn:hover {
  background: #3182ce;
}

/* Summary Stats */
.summary-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}

.stat-card {
  background: white;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: transform 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-card.high {
  border-left: 4px solid #e53e3e;
}

.stat-card.medium {
  border-left: 4px solid #ed8936;
}

.stat-card.low {
  border-left: 4px solid #48bb78;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1a202c;
}

.stat-label {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Focus Areas */
.focus-areas {
  margin-bottom: 24px;
  background: white;
  padding: 16px;
  border-radius: 8px;
}

.focus-areas h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #1a202c;
}

.focus-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.focus-tag {
  display: inline-block;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

/* Drills Grid */
.drills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.drill-card {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  position: relative;
}

.drill-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
}

.drill-card.severity-high {
  border-top: 4px solid #e53e3e;
}

.drill-card.severity-medium {
  border-top: 4px solid #ed8936;
}

.drill-card.severity-low {
  border-top: 4px solid #48bb78;
}

/* Severity Badge */
.severity-badge {
  padding: 12px;
  display: flex;
  justify-content: flex-end;
}

.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.badge.high {
  background: rgba(229, 62, 62, 0.1);
  color: #e53e3e;
}

.badge.medium {
  background: rgba(237, 137, 54, 0.1);
  color: #ed8936;
}

.badge.low {
  background: rgba(72, 187, 120, 0.1);
  color: #48bb78;
}

/* Drill Info */
.drill-info {
  padding: 16px;
}

.drill-name {
  font-size: 18px;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 4px 0;
}

.drill-category {
  font-size: 12px;
  color: #999;
  margin: 0 0 8px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.drill-description {
  font-size: 14px;
  color: #666;
  margin: 0 0 12px 0;
  line-height: 1.4;
}

/* Drill Details */
.drill-details {
  background: #f9fafb;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 13px;
}

.detail-label {
  color: #999;
  font-weight: 600;
}

.detail-value {
  color: #1a202c;
  font-weight: 500;
}

.difficulty-bar {
  display: inline-flex;
  align-items: center;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
  height: 20px;
  width: 60px;
  padding: 2px;
  font-size: 10px;
  color: #666;
  font-weight: 700;
}

.difficulty-fill {
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  height: 100%;
  border-radius: 2px;
}

/* Additional Info */
.drill-reason,
.drill-frequency,
.drill-improvement {
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
  padding: 8px;
  background: #f9fafb;
  border-radius: 4px;
  border-left: 3px solid #cbd5e0;
}

.drill-reason strong,
.drill-frequency strong,
.drill-improvement strong {
  color: #1a202c;
  display: block;
  margin-bottom: 2px;
}

/* Start Drill Button */
.start-drill-btn {
  width: 100%;
  padding: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.start-drill-btn:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.start-drill-btn:active {
  transform: scale(0.98);
}

/* Footer Info */
.footer-info {
  text-align: center;
  color: #999;
  font-size: 12px;
  margin-top: 16px;
}

.refresh-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin: 0;
}

.refresh-btn {
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid #cbd5e0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  transition: all 0.2s;
}

.refresh-btn:hover {
  background: white;
  border-color: #a0aec0;
}

/* Responsive */
@media (max-width: 768px) {
  .training-drills-panel {
    padding: 16px;
  }

  .panel-header h2 {
    font-size: 22px;
  }

  .drills-grid {
    grid-template-columns: 1fr;
  }

  .summary-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .training-drills-panel {
    padding: 12px;
  }

  .panel-header h2 {
    font-size: 18px;
  }

  .summary-stats {
    grid-template-columns: 1fr;
  }

  .drill-card {
    border-radius: 6px;
  }
}
</style>

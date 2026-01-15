<template>
  <div class="tactical-suggestions-panel">
    <div class="panel-header">
      <h2 class="panel-title">
        🧠 Coach's Tactical Suggestions
      </h2>
      <button
        v-if="gameId"
        :disabled="loading"
        class="refresh-btn"
        title="Refresh suggestions"
        @click="refreshSuggestions"
      >
        🔄
      </button>
    </div>

    <div v-if="error" class="error-message">
      ⚠️ {{ error }}
    </div>

    <div v-else-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Analyzing match situation...</p>
    </div>

    <div v-else-if="!suggestions" class="empty-state">
      <p>No game data available for suggestions</p>
    </div>

    <div v-else class="suggestions-grid">
      <!-- Best Bowler Card -->
      <div v-if="suggestions.best_bowler" class="suggestion-card bowler-card">
        <h3 class="card-title">
          🎯 Best Bowler Now
        </h3>
        <div class="card-content">
          <div class="bowler-name">{{ suggestions.best_bowler.bowler_name }}</div>
          <div class="confidence-badge" :class="confidenceClass(suggestions.best_bowler.confidence)">
            {{ (suggestions.best_bowler.confidence * 100).toFixed(0) }}% confidence
          </div>
          <div class="bowler-stats">
            <div class="stat">
              <span class="label">Effectiveness</span>
              <span class="value">{{ suggestions.best_bowler.effectiveness_vs_batter.toFixed(1) }}</span>
            </div>
            <div class="stat">
              <span class="label">Economy</span>
              <span class="value">{{ suggestions.best_bowler.expected_economy.toFixed(2) }}</span>
            </div>
          </div>
          <p class="reason">{{ suggestions.best_bowler.reason }}</p>
        </div>
      </div>

      <!-- Weakness Analysis Card -->
      <div v-if="suggestions.weakness" class="suggestion-card weakness-card">
        <h3 class="card-title">
          ⚡ Batter's Weakness
        </h3>
        <div class="card-content">
          <div class="weakness-type">{{ formatWeakness(suggestions.weakness.primary_weakness) }}</div>
          <div class="weakness-score-bar">
            <div class="bar-fill" :style="{ width: suggestions.weakness.weakness_score + '%' }"></div>
          </div>
          <div class="weakness-score">{{ suggestions.weakness.weakness_score.toFixed(1) }}% exposed</div>

          <div class="recommendation-box">
            <div class="rec-item">
              <span class="rec-label">Line:</span>
              <span class="rec-value">{{ formatLine(suggestions.weakness.recommended_line) }}</span>
            </div>
            <div class="rec-item">
              <span class="rec-label">Length:</span>
              <span class="rec-value">{{ suggestions.weakness.recommended_length }}</span>
            </div>
            <div v-if="suggestions.weakness.recommended_speed" class="rec-item">
              <span class="rec-label">Speed:</span>
              <span class="rec-value">{{ suggestions.weakness.recommended_speed }} km/h</span>
            </div>
          </div>

          <div v-if="suggestions.weakness.secondary_weakness" class="secondary-weakness">
            <p class="label">Secondary weakness:</p>
            <p class="value">{{ suggestions.weakness.secondary_weakness }}</p>
          </div>
        </div>
      </div>

      <!-- Fielding Setup Card -->
      <div v-if="suggestions.fielding && suggestions.fielding.recommended_positions.length" class="suggestion-card fielding-card">
        <h3 class="card-title">
          👥 Recommended Field Setup
        </h3>
        <div class="card-content">
          <div class="primary-zone">Block: {{ suggestions.fielding.primary_zone }}</div>

          <div class="positions-list">
            <div
              v-for="pos in suggestions.fielding.recommended_positions"
              :key="pos.position"
              class="position-item"
              :class="{ [`priority-${pos.priority}`]: true }"
            >
              <div class="priority-badge">{{ pos.priority }}</div>
              <div class="position-details">
                <div class="position-name">{{ pos.position }}</div>
                <div class="coverage-reason">{{ pos.coverage_reason }}</div>
              </div>
            </div>
          </div>

          <p class="fielding-reasoning">{{ suggestions.fielding.reasoning }}</p>
        </div>
      </div>
    </div>

    <div v-if="suggestions" class="timestamp">
      Updated: {{ lastUpdated }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'

import { useTacticalSuggestions } from '@/composables/useTacticalSuggestions'
import type { TacticalSuggestions } from '@/composables/useTacticalSuggestions'

interface Props {
  gameId?: string
}

const props = withDefaults(defineProps<Props>(), {
  gameId: undefined,
})

const { suggestions, loading, error, fetchSuggestions } = useTacticalSuggestions()
const lastUpdated = ref<string>('')

// Auto-refresh every 10 seconds if game ID is set
onMounted(async () => {
  if (props.gameId) {
    await refreshSuggestions()
    // Poll for updates
    setInterval(() => {
      if (props.gameId) {
        refreshSuggestions()
      }
    }, 10000)
  }
})

watch(
  () => props.gameId,
  async (newGameId) => {
    if (newGameId) {
      await refreshSuggestions()
    }
  },
)

async function refreshSuggestions() {
  if (props.gameId) {
    await fetchSuggestions(props.gameId)
    lastUpdated.value = new Date().toLocaleTimeString()
  }
}

function confidenceClass(confidence: number): string {
  if (confidence >= 0.8) return 'confidence-high'
  if (confidence >= 0.6) return 'confidence-medium'
  return 'confidence-low'
}

function formatWeakness(weakness: string): string {
  // Convert "DeliveryType.PACE" to "Pace" or just "pace" to "Pace"
  const match = weakness.match(/(?:DeliveryType\.)?(\w+)/i)
  return match ? match[1].charAt(0).toUpperCase() + match[1].slice(1).toLowerCase() : weakness
}

function formatLine(line: string): string {
  // Convert "off_stump" to "Off stump"
  return line
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}
</script>

<style scoped>
.tactical-suggestions-panel {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 12px;
  padding: 20px;
  color: #e0e0e0;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  border-bottom: 2px solid #0f3460;
  padding-bottom: 12px;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: #00d4ff;
}

.header-icon {
  font-size: 1.8rem;
}

.refresh-btn {
  background: #0f3460;
  border: 1px solid #00d4ff;
  color: #00d4ff;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.refresh-btn:hover:not(:disabled) {
  background: #00d4ff;
  color: #1a1a2e;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.error-message {
  background: #8b0000;
  border-left: 4px solid #ff4444;
  padding: 12px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #ffcccc;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 15px;
  padding: 40px 20px;
  color: #888;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #0f3460;
  border-top: 4px solid #00d4ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.empty-state {
  text-align: center;
  padding: 30px;
  color: #666;
  font-size: 0.95rem;
}

.suggestions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 15px;
  margin-bottom: 15px;
}

.suggestion-card {
  background: linear-gradient(135deg, #0f3460 0%, #163355 100%);
  border: 1px solid #00d4ff;
  border-radius: 8px;
  padding: 15px;
  transition: all 0.3s ease;
}

.suggestion-card:hover {
  box-shadow: 0 0 15px rgba(0, 212, 255, 0.3);
  transform: translateY(-2px);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #00d4ff;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* Bowler Card Styles */
.bowler-card {
  border-top: 3px solid #ff6b6b;
}

.bowler-name {
  font-size: 1.2rem;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 8px;
}

.confidence-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
  width: fit-content;
}

.confidence-high {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
  border: 1px solid #22c55e;
}

.confidence-medium {
  background: rgba(234, 179, 8, 0.2);
  color: #eab308;
  border: 1px solid #eab308;
}

.confidence-low {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  border: 1px solid #ef4444;
}

.bowler-stats {
  display: flex;
  gap: 15px;
  padding: 8px 0;
  border-top: 1px solid #0f3460;
  border-bottom: 1px solid #0f3460;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat .label {
  font-size: 0.8rem;
  color: #888;
  text-transform: uppercase;
}

.stat .value {
  font-size: 1.1rem;
  font-weight: 600;
  color: #ffb700;
}

.reason {
  font-size: 0.9rem;
  color: #aaa;
  font-style: italic;
  margin: 8px 0 0 0;
}

/* Weakness Card Styles */
.weakness-card {
  border-top: 3px solid #ffd700;
}

.weakness-type {
  font-size: 1.1rem;
  font-weight: 600;
  color: #ffd700;
  margin-bottom: 8px;
}

.weakness-score-bar {
  width: 100%;
  height: 8px;
  background: #0f3460;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 4px;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #ffd700 0%, #ff6b6b 100%);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.weakness-score {
  font-size: 0.9rem;
  color: #ffd700;
  font-weight: 600;
  margin-bottom: 10px;
}

.recommendation-box {
  background: rgba(0, 212, 255, 0.05);
  border-left: 3px solid #00d4ff;
  padding: 10px;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rec-item {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 0.9rem;
}

.rec-label {
  color: #888;
  font-weight: 600;
}

.rec-value {
  color: #00d4ff;
  font-weight: 600;
}

.secondary-weakness {
  background: rgba(139, 0, 0, 0.1);
  border-left: 3px solid #ff4444;
  padding: 8px;
  border-radius: 4px;
  font-size: 0.85rem;
}

.secondary-weakness .label {
  color: #888;
  margin: 0 0 4px 0;
}

.secondary-weakness .value {
  color: #ff8888;
  font-weight: 600;
}

/* Fielding Card Styles */
.fielding-card {
  border-top: 3px solid #4dff4d;
}

.primary-zone {
  font-size: 1rem;
  font-weight: 600;
  color: #4dff4d;
  padding: 8px;
  background: rgba(77, 255, 77, 0.05);
  border-radius: 4px;
  margin-bottom: 10px;
}

.positions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 10px 0;
}

.position-item {
  display: flex;
  gap: 10px;
  padding: 8px;
  background: #0f3460;
  border-radius: 4px;
  border-left: 3px solid #00d4ff;
}

.position-item.priority-1 {
  border-left-color: #22c55e;
  background: rgba(34, 197, 94, 0.1);
}

.position-item.priority-2 {
  border-left-color: #eab308;
  background: rgba(234, 179, 8, 0.1);
}

.position-item.priority-3 {
  border-left-color: #f97316;
  background: rgba(249, 115, 22, 0.1);
}

.priority-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #00d4ff;
  color: #1a1a2e;
  font-weight: 700;
  font-size: 0.8rem;
  flex-shrink: 0;
}

.position-item.priority-1 .priority-badge {
  background: #22c55e;
}

.position-item.priority-2 .priority-badge {
  background: #eab308;
}

.position-item.priority-3 .priority-badge {
  background: #f97316;
}

.position-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.position-name {
  font-weight: 600;
  color: #ffffff;
  font-size: 0.95rem;
}

.coverage-reason {
  font-size: 0.8rem;
  color: #888;
}

.fielding-reasoning {
  font-size: 0.85rem;
  color: #aaa;
  font-style: italic;
  margin: 8px 0 0 0;
}

.timestamp {
  text-align: center;
  font-size: 0.8rem;
  color: #555;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #0f3460;
}

/* Responsive Design */
@media (max-width: 768px) {
  .tactical-suggestions-panel {
    padding: 15px;
  }

  .suggestions-grid {
    grid-template-columns: 1fr;
  }

  .panel-title {
    font-size: 1.2rem;
  }
}
</style>

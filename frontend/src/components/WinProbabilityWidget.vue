<script setup lang="ts">
import { computed } from 'vue'

import WinProbabilityChart from '@/components/analytics/WinProbabilityChart.vue'

export interface WinProbability {
  batting_team_win_prob: number
  bowling_team_win_prob: number
  confidence: number
  batting_team?: string
  bowling_team?: string
  factors?: {
    runs_needed?: number
    balls_remaining?: number
    required_run_rate?: number
    current_run_rate?: number
    wickets_remaining?: number
    projected_score?: number
    par_score?: number
  }
}

interface Props {
  prediction: WinProbability | null
  battingTeam?: string
  bowlingTeam?: string
  theme?: 'dark' | 'light' | 'auto'
  showChart?: boolean
  compact?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  battingTeam: undefined,
  bowlingTeam: undefined,
  theme: 'dark',
  showChart: true,
  compact: false,
})

const battingColor = computed(() => {
  if (!props.prediction) return '#9ca3af'
  const prob = props.prediction.batting_team_win_prob
  if (prob >= 70) return '#22c55e' // Green
  if (prob >= 50) return '#eab308' // Yellow
  return '#ef4444' // Red
})

const bowlingColor = computed(() => {
  if (!props.prediction) return '#9ca3af'
  const prob = props.prediction.bowling_team_win_prob
  if (prob >= 70) return '#22c55e' // Green
  if (prob >= 50) return '#eab308' // Yellow
  return '#ef4444' // Red
})

const battingBarWidth = computed(() => {
  if (!props.prediction) return '50%'
  return `${props.prediction.batting_team_win_prob}%`
})

const bowlingBarWidth = computed(() => {
  if (!props.prediction) return '50%'
  return `${props.prediction.bowling_team_win_prob}%`
})

const formattedBattingTeam = computed(() => {
  return props.prediction?.batting_team || props.battingTeam || 'Batting Team'
})

const formattedBowlingTeam = computed(() => {
  return props.prediction?.bowling_team || props.bowlingTeam || 'Bowling Team'
})

const resolvedTheme = computed<'dark' | 'light'>(() => {
  if (props.theme === 'dark') return 'dark'
  return 'light'
})
</script>

<template>
  <div class="win-probability-widget" :class="{ compact }">
    <div v-if="prediction && prediction.confidence > 0" class="prediction-display">
      <div class="header">
        <h3>Win Probability</h3>
        <span class="confidence" :title="`Confidence: ${prediction.confidence}%`">
          Confidence: {{ prediction.confidence.toFixed(0) }}%
        </span>
      </div>

      <div class="probability-bars">
        <div class="team-row">
          <div class="team-name batting">{{ formattedBattingTeam }}</div>
          <div class="bar-container">
            <div
              class="bar batting-bar"
              :style="{ width: battingBarWidth, backgroundColor: battingColor }"
            />
          </div>
          <div class="percentage batting">{{ prediction.batting_team_win_prob.toFixed(1) }}%</div>
        </div>

        <div class="team-row">
          <div class="team-name bowling">{{ formattedBowlingTeam }}</div>
          <div class="bar-container">
            <div
              class="bar bowling-bar"
              :style="{ width: bowlingBarWidth, backgroundColor: bowlingColor }"
            />
          </div>
          <div class="percentage bowling">{{ prediction.bowling_team_win_prob.toFixed(1) }}%</div>
        </div>
      </div>

      <div v-if="prediction.factors && !compact" class="factors">
        <div v-if="prediction.factors.runs_needed !== undefined" class="factor">
          <span class="label">Runs Needed:</span>
          <span class="value">{{ prediction.factors.runs_needed }}</span>
        </div>
        <div v-if="prediction.factors.balls_remaining !== undefined" class="factor">
          <span class="label">Balls Remaining:</span>
          <span class="value">{{ prediction.factors.balls_remaining }}</span>
        </div>
        <div v-if="prediction.factors.required_run_rate !== undefined" class="factor">
          <span class="label">Required RR:</span>
          <span class="value">{{ prediction.factors.required_run_rate.toFixed(2) }}</span>
        </div>
        <div v-if="prediction.factors.wickets_remaining !== undefined" class="factor">
          <span class="label">Wickets Remaining:</span>
          <span class="value">{{ prediction.factors.wickets_remaining }}</span>
        </div>
        <div v-if="prediction.factors.projected_score !== undefined" class="factor">
          <span class="label">Projected Score:</span>
          <span class="value">{{ prediction.factors.projected_score }}</span>
        </div>
      </div>

      <div v-if="showChart && !compact" class="chart-section">
        <WinProbabilityChart
          :current-prediction="prediction"
          :batting-team="formattedBattingTeam"
          :bowling-team="formattedBowlingTeam"
          :theme="resolvedTheme"
        />
      </div>
    </div>

    <div v-else class="no-prediction">
      <p>🎯 AI predictions will appear as the match progresses</p>
    </div>
  </div>
</template>

<style scoped>
.win-probability-widget {
  background: var(--pico-card-background-color);
  border: 1px solid var(--pico-card-border-color);
  border-radius: var(--pico-border-radius);
  padding: 1rem;
  margin: 1rem 0;
}

.win-probability-widget.compact {
  padding: 0.75rem;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.confidence {
  font-size: 0.85rem;
  color: var(--pico-muted-color);
}

.probability-bars {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.team-row {
  display: grid;
  grid-template-columns: 140px 1fr 80px;
  gap: 0.75rem;
  align-items: center;
}

.team-name {
  font-weight: 600;
  font-size: 0.95rem;
}

.team-name.batting {
  color: var(--pico-primary-color);
}

.team-name.bowling {
  color: var(--pico-secondary-color);
}

.bar-container {
  background: var(--pico-background-color);
  border-radius: 8px;
  height: 24px;
  overflow: hidden;
  position: relative;
}

.bar {
  height: 100%;
  border-radius: 8px;
  transition: width 0.5s ease, background-color 0.3s ease;
}

.percentage {
  text-align: right;
  font-weight: 700;
  font-size: 1rem;
}

.percentage.batting {
  color: var(--pico-primary-color);
}

.percentage.bowling {
  color: var(--pico-secondary-color);
}

.factors {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.75rem;
  padding: 1rem;
  background: var(--pico-background-color);
  border-radius: var(--pico-border-radius);
  margin-bottom: 1rem;
}

.factor {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.factor .label {
  font-size: 0.8rem;
  color: var(--pico-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.factor .value {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--pico-color);
}

.chart-section {
  margin-top: 1.5rem;
  height: 250px;
}

.no-prediction {
  text-align: center;
  padding: 2rem;
  color: var(--pico-muted-color);
}

.no-prediction p {
  margin: 0;
  font-size: 0.95rem;
}

@media (max-width: 768px) {
  .team-row {
    grid-template-columns: 100px 1fr 60px;
    gap: 0.5rem;
  }

  .factors {
    grid-template-columns: 1fr;
  }

  .chart-section {
    height: 200px;
  }
}
</style>

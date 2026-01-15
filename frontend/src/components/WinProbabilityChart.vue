<template>
  <BaseCard class="win-prob-chart" padding="md">
    <div class="header">
      <h3 class="title">{{ isFirstInnings ? 'Score Prediction' : 'Win Probability' }}</h3>
      <BaseBadge v-if="prediction" variant="neutral" size="sm">
        {{ prediction.confidence.toFixed(0) }}% confidence
      </BaseBadge>
    </div>

    <!-- Score Prediction (First Innings) -->
    <div v-if="prediction && isFirstInnings && prediction.factors?.projected_score" class="score-prediction">
      <div class="projected-score">
        <div class="score-label">Projected Final Score</div>
        <div class="score-value">{{ Math.round(prediction.factors.projected_score) }}</div>
        <div class="score-details">
          Par Score: {{ Math.round(prediction.factors.par_score || 0) }}
          <span :class="{'above-par': prediction.factors.projected_score > (prediction.factors.par_score || 0), 'below-par': prediction.factors.projected_score < (prediction.factors.par_score || 0)}">
            ({{ prediction.factors.projected_score > (prediction.factors.par_score || 0) ? '+' : '' }}{{ Math.round(prediction.factors.projected_score - (prediction.factors.par_score || 0)) }})
          </span>
        </div>
      </div>
    </div>

    <!-- Win Probability (Second Innings) -->
    <div v-if="prediction && !isFirstInnings" class="probability-bars">
      <div class="team-prob batting">
        <div class="team-name">{{ prediction.batting_team || 'Batting' }}</div>
        <div class="prob-bar-container">
          <div
            class="prob-bar"
            :style="{ width: `${prediction.batting_team_win_prob}%` }"
          />
        </div>
        <div class="prob-value">{{ prediction.batting_team_win_prob.toFixed(1) }}%</div>
      </div>

      <div class="team-prob bowling">
        <div class="team-name">{{ prediction.bowling_team || 'Bowling' }}</div>
        <div class="prob-bar-container">
          <div
            class="prob-bar"
            :style="{ width: `${prediction.bowling_team_win_prob}%` }"
          />
        </div>
        <div class="prob-value">{{ prediction.bowling_team_win_prob.toFixed(1) }}%</div>
      </div>
    </div>

    <!-- Factors breakdown -->
    <div v-if="prediction?.factors" class="factors">
      <div class="factors-title">Key Factors</div>
      <div class="factors-grid">
        <!-- Second Innings Factors -->
        <template v-if="!isFirstInnings">
          <div v-if="prediction.factors.required_run_rate != null" class="factor">
            <span class="factor-label">Required RR:</span>
            <span class="factor-value">{{ prediction.factors.required_run_rate.toFixed(2) }}</span>
          </div>
          <div v-if="prediction.factors.current_run_rate != null" class="factor">
            <span class="factor-label">Current RR:</span>
            <span class="factor-value">{{ prediction.factors.current_run_rate.toFixed(2) }}</span>
          </div>
          <div v-if="prediction.factors.runs_needed != null" class="factor">
            <span class="factor-label">Runs Needed:</span>
            <span class="factor-value">{{ prediction.factors.runs_needed }}</span>
          </div>
          <div v-if="prediction.factors.balls_remaining != null" class="factor">
            <span class="factor-label">Balls Left:</span>
            <span class="factor-value">{{ prediction.factors.balls_remaining }}</span>
          </div>
          <div v-if="prediction.factors.wickets_remaining != null" class="factor">
            <span class="factor-label">Wickets Left:</span>
            <span class="factor-value">{{ prediction.factors.wickets_remaining }}</span>
          </div>
        </template>

        <!-- First Innings Factors -->
        <template v-else>
          <div v-if="currentRunRate != null" class="factor">
            <span class="factor-label">Current RR:</span>
            <span class="factor-value">{{ currentRunRate.toFixed(2) }}</span>
          </div>
          <div v-if="prediction.factors.wickets_remaining != null" class="factor">
            <span class="factor-label">Wickets Left:</span>
            <span class="factor-value">{{ prediction.factors.wickets_remaining }}</span>
          </div>
          <div v-if="prediction.factors.balls_remaining != null" class="factor">
            <span class="factor-label">Balls Left:</span>
            <span class="factor-value">{{ prediction.factors.balls_remaining }}</span>
          </div>
        </template>
      </div>
    </div>

    <!-- Chart canvas (optional - for historical trend) -->
    <div v-if="showChart && chartData.labels && chartData.labels.length > 0" class="chart-container">
      <Line :data="chartData" :options="chartOptions" />
    </div>

    <div v-if="!prediction" class="no-data">
      <p>Predictions will appear once scoring begins</p>
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  type ChartData,
  type ChartOptions,
} from 'chart.js'
import { storeToRefs } from 'pinia'
import { computed, ref, watch } from 'vue'
import { Line } from 'vue-chartjs'

import { BaseCard, BaseBadge } from '@/components'
import { useGameStore } from '@/stores/gameStore'


// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

interface Props {
  showChart?: boolean
  maxHistory?: number
}

const props = withDefaults(defineProps<Props>(), {
  showChart: false,
  maxHistory: 50,
})

const gameStore = useGameStore()
const { currentPrediction, currentGame } = storeToRefs(gameStore)

const prediction = computed(() => currentPrediction.value)

// Check if we're in first innings (no target means first innings)
const isFirstInnings = computed(() => {
  return !currentGame.value?.target
})

// Get current run rate from game state
const currentRunRate = computed(() => {
  return (currentGame.value as any)?.current_run_rate || 0
})

// Historical data for chart
const predictionHistory = ref<Array<{
  over: string
  battingProb: number
  bowlingProb: number
}>>([])

// Watch for prediction updates and add to history
watch(
  () => currentPrediction.value,
  (newPred) => {
    if (newPred && props.showChart) {
      // Get current over from game state
      const currentGame = gameStore.currentGame
      const oversCompleted = currentGame?.overs_completed ?? 0
      const ballsThisOver = currentGame?.balls_this_over ?? 0
      const currentOver = `${oversCompleted}.${ballsThisOver}`

      predictionHistory.value.push({
        over: currentOver,
        battingProb: newPred.batting_team_win_prob,
        bowlingProb: newPred.bowling_team_win_prob,
      })

      // Keep only last N predictions
      if (predictionHistory.value.length > props.maxHistory) {
        predictionHistory.value = predictionHistory.value.slice(-props.maxHistory)
      }
    }
  }
)

const chartData = computed<ChartData<'line'>>(() => ({
  labels: predictionHistory.value.map(p => p.over),
  datasets: [
    {
      label: prediction.value?.batting_team || 'Batting',
      data: predictionHistory.value.map(p => p.battingProb),
      borderColor: '#3b82f6',
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      tension: 0.3,
      fill: true,
    },
    {
      label: prediction.value?.bowling_team || 'Bowling',
      data: predictionHistory.value.map(p => p.bowlingProb),
      borderColor: '#ef4444',
      backgroundColor: 'rgba(239, 68, 68, 0.1)',
      tension: 0.3,
      fill: true,
    },
  ],
}))

const chartOptions = computed<ChartOptions<'line'>>(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: 'top',
    },
    tooltip: {
      callbacks: {
        label: (context) => {
          const value = context.parsed.y ?? 0
          return `${context.dataset.label}: ${value.toFixed(1)}%`
        },
      },
    },
  },
  scales: {
    y: {
      min: 0,
      max: 100,
      ticks: {
        callback: (value) => `${value}%`,
      },
    },
    x: {
      title: {
        display: true,
        text: 'Overs',
      },
    },
  },
}))
</script>

<style scoped>
.win-prob-chart {
  background: var(--ds-bg-surface, #fff);
  border-radius: var(--ds-radius-lg, 12px);
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--ds-text-primary, #1f2937);
  margin: 0;
}

/* Score Prediction Styles (First Innings) */
.score-prediction {
  margin-bottom: 1.5rem;
}

.projected-score {
  text-align: center;
  padding: 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: var(--ds-radius-lg, 12px);
  color: white;
}

.score-label {
  font-size: 0.875rem;
  opacity: 0.9;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.score-value {
  font-size: 3rem;
  font-weight: 700;
  margin: 0.25rem 0;
}

.score-details {
  font-size: 0.9375rem;
  margin-top: 0.5rem;
  opacity: 0.95;
}

.above-par {
  color: #86efac;
  font-weight: 600;
}

.below-par {
  color: #fca5a5;
  font-weight: 600;
}

/* Probability Bars (Second Innings) */
.probability-bars {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.team-prob {
  display: grid;
  grid-template-columns: 120px 1fr 80px;
  align-items: center;
  gap: 0.75rem;
}

.team-name {
  font-weight: 500;
  color: var(--ds-text-secondary, #6b7280);
  font-size: 0.875rem;
}

.prob-bar-container {
  height: 32px;
  background: var(--ds-bg-muted, #f3f4f6);
  border-radius: var(--ds-radius-md, 8px);
  overflow: hidden;
  position: relative;
}

.prob-bar {
  height: 100%;
  border-radius: var(--ds-radius-md, 8px);
  transition: width 0.5s ease;
}

.batting .prob-bar {
  background: linear-gradient(90deg, #3b82f6 0%, #60a5fa 100%);
}

.bowling .prob-bar {
  background: linear-gradient(90deg, #ef4444 0%, #f87171 100%);
}

.prob-value {
  font-weight: 600;
  color: var(--ds-text-primary, #1f2937);
  text-align: right;
  font-size: 1rem;
}

.factors {
  padding: 1rem;
  background: var(--ds-bg-muted, #f9fafb);
  border-radius: var(--ds-radius-md, 8px);
  margin-bottom: 1rem;
}

.factors-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--ds-text-secondary, #6b7280);
  margin-bottom: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.factors-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.75rem;
}

.factor {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background: var(--ds-bg-surface, #fff);
  border-radius: var(--ds-radius-sm, 6px);
}

.factor-label {
  font-size: 0.8125rem;
  color: var(--ds-text-tertiary, #9ca3af);
}

.factor-value {
  font-weight: 600;
  color: var(--ds-text-primary, #1f2937);
  font-size: 0.9375rem;
}

.chart-container {
  height: 200px;
  margin-top: 1.5rem;
}

.no-data {
  padding: 2rem;
  text-align: center;
  color: var(--ds-text-tertiary, #9ca3af);
  font-size: 0.875rem;
}

.no-data p {
  margin: 0;
}
</style>

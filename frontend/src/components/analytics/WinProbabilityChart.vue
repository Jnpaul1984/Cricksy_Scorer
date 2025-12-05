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
  type ChartOptions,
} from 'chart.js'
import { computed, ref, watch } from 'vue'
import { Line } from 'vue-chartjs'

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

export interface WinProbability {
  batting_team_win_prob: number
  bowling_team_win_prob: number
  confidence: number
  batting_team?: string
  bowling_team?: string
}

interface Props {
  currentPrediction: WinProbability | null
  battingTeam?: string
  bowlingTeam?: string
  theme?: 'dark' | 'light'
}

const props = withDefaults(defineProps<Props>(), {
  battingTeam: undefined,
  bowlingTeam: undefined,
  theme: 'dark',
})

// Store history of predictions
const predictionHistory = ref<Array<{ over: string; battingProb: number; bowlingProb: number }>>([])

watch(
  () => props.currentPrediction,
  (newPred) => {
    if (newPred && newPred.confidence > 0) {
      // For now, use a simple counter for overs (in real scenario, get from game state)
      const over = `${predictionHistory.value.length + 1}`
      predictionHistory.value.push({
        over,
        battingProb: newPred.batting_team_win_prob,
        bowlingProb: newPred.bowling_team_win_prob,
      })

      // Keep only last 50 data points
      if (predictionHistory.value.length > 50) {
        predictionHistory.value.shift()
      }
    }
  },
  { deep: true }
)

const chartData = computed(() => {
  const labels = predictionHistory.value.map((p) => p.over)

  return {
    labels,
    datasets: [
      {
        label: props.battingTeam || 'Batting Team',
        data: predictionHistory.value.map((p) => p.battingProb),
        borderColor: props.theme === 'dark' ? '#4ade80' : '#22c55e',
        backgroundColor: props.theme === 'dark' ? 'rgba(74, 222, 128, 0.1)' : 'rgba(34, 197, 94, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 2,
        pointHoverRadius: 5,
      },
      {
        label: props.bowlingTeam || 'Bowling Team',
        data: predictionHistory.value.map((p) => p.bowlingProb),
        borderColor: props.theme === 'dark' ? '#f87171' : '#ef4444',
        backgroundColor: props.theme === 'dark' ? 'rgba(248, 113, 113, 0.1)' : 'rgba(239, 68, 68, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 2,
        pointHoverRadius: 5,
      },
    ],
  }
})

const chartOptions = computed<ChartOptions<'line'>>(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false,
  },
  plugins: {
    legend: {
      display: true,
      position: 'top',
      labels: {
        color: props.theme === 'dark' ? '#e5e7eb' : '#374151',
        font: {
          size: 12,
        },
      },
    },
    title: {
      display: false,
    },
    tooltip: {
      backgroundColor: props.theme === 'dark' ? '#1f2937' : '#ffffff',
      titleColor: props.theme === 'dark' ? '#f3f4f6' : '#111827',
      bodyColor: props.theme === 'dark' ? '#e5e7eb' : '#374151',
      borderColor: props.theme === 'dark' ? '#374151' : '#e5e7eb',
      borderWidth: 1,
      callbacks: {
        label: function (context) {
          const yValue = context.parsed?.y
          if (typeof yValue !== 'number') {
            return context.dataset.label ?? ''
          }
          const label = context.dataset.label ?? 'Value'
          return `${label}: ${yValue.toFixed(1)}%`
        },
      },
    },
  },
  scales: {
    x: {
      display: true,
      title: {
        display: true,
        text: 'Progress',
        color: props.theme === 'dark' ? '#9ca3af' : '#6b7280',
      },
      ticks: {
        color: props.theme === 'dark' ? '#9ca3af' : '#6b7280',
      },
      grid: {
        color: props.theme === 'dark' ? '#374151' : '#e5e7eb',
      },
    },
    y: {
      display: true,
      min: 0,
      max: 100,
      title: {
        display: true,
        text: 'Win Probability (%)',
        color: props.theme === 'dark' ? '#9ca3af' : '#6b7280',
      },
      ticks: {
        color: props.theme === 'dark' ? '#9ca3af' : '#6b7280',
        callback: function (value) {
          return value + '%'
        },
      },
      grid: {
        color: props.theme === 'dark' ? '#374151' : '#e5e7eb',
      },
    },
  },
}))
</script>

<template>
  <div class="win-probability-chart">
    <div v-if="currentPrediction && currentPrediction.confidence > 0" class="chart-container">
      <Line :data="chartData" :options="chartOptions" />
    </div>
    <div v-else class="no-data">
      <p>Win probability will be displayed as the match progresses...</p>
    </div>
  </div>
</template>

<style scoped>
.win-probability-chart {
  width: 100%;
  height: 100%;
  min-height: 200px;
}

.chart-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.no-data {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  color: var(--pico-muted-color);
  font-size: 0.9rem;
}
</style>

<template>
  <div class="season-graphs-widget">
    <div class="season-graphs-header">
      <h3 class="season-graphs-title">📊 Season Statistics</h3>
      <div class="season-controls">
        <button
          v-for="stat in ['runs', 'wickets', 'average']"
          :key="stat"
          class="stat-tab-btn"
          :class="{ active: activeStat === stat }"
          @click="activeStat = stat as StatType"
        >
          {{ stat === 'runs' ? '🏃 Runs' : stat === 'wickets' ? '⚾ Wickets' : '📈 Average' }}
        </button>
      </div>
    </div>

    <div class="charts-container">
      <!-- Runs Stats -->
      <div v-if="activeStat === 'runs'" class="chart-section">
        <div class="chart-wrapper">
          <h4>Cumulative Runs (Season)</h4>
          <Line v-if="cumulativeRunsChart" :data="cumulativeRunsChart.data" :options="cumulativeRunsChart.options" />
          <p v-else class="no-data">No match data available</p>
        </div>
        <div class="chart-wrapper">
          <h4>Runs per Innings</h4>
          <Bar v-if="runsPerInningsChart" :data="runsPerInningsChart.data" :options="runsPerInningsChart.options" />
          <p v-else class="no-data">No match data available</p>
        </div>
      </div>

      <!-- Wickets Stats -->
      <div v-if="activeStat === 'wickets'" class="chart-section">
        <div class="chart-wrapper">
          <h4>Cumulative Wickets (Season)</h4>
          <Line v-if="cumulativeWicketsChart" :data="cumulativeWicketsChart.data" :options="cumulativeWicketsChart.options" />
          <p v-else class="no-data">No bowling data available</p>
        </div>
        <div class="chart-wrapper">
          <h4>Wickets per Innings</h4>
          <Bar v-if="wicketsPerInningsChart" :data="wicketsPerInningsChart.data" :options="wicketsPerInningsChart.options" />
          <p v-else class="no-data">No bowling data available</p>
        </div>
      </div>

      <!-- Average Stats -->
      <div v-if="activeStat === 'average'" class="chart-section">
        <div class="chart-wrapper full-width">
          <h4>Rolling Average (Last 5 Matches)</h4>
          <Line v-if="rollingAverageChart" :data="rollingAverageChart.data" :options="rollingAverageChart.options" />
          <p v-else class="no-data">No average data available</p>
        </div>
      </div>
    </div>

    <!-- Season Highlights -->
    <div class="season-highlights">
      <div class="highlight-item">
        <span class="highlight-label">Peak Performance:</span>
        <span class="highlight-value">{{ peakMatch }}</span>
      </div>
      <div class="highlight-item">
        <span class="highlight-label">Total Matches:</span>
        <span class="highlight-value">{{ profile?.total_matches || 0 }}</span>
      </div>
      <div class="highlight-item">
        <span class="highlight-label">Career Average:</span>
        <span class="highlight-value">{{ formatStat(profile?.batting_average) }}</span>
      </div>
      <div class="highlight-item">
        <span class="highlight-label">Strike Rate:</span>
        <span class="highlight-value">{{ formatStat(profile?.strike_rate) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, ref, computed } from 'vue'
import { Line, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import type { PlayerProfile } from '@/types/player'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, Filler)

type StatType = 'runs' | 'wickets' | 'average'

const props = defineProps<{
  profile: PlayerProfile | null
}>()

const activeStat = ref<StatType>('runs')

// Format stat with fallback
const formatStat = (value: number | null | undefined, decimals = 2): string => {
  if (value === null || value === undefined || isNaN(value)) return '—'
  return value.toFixed(decimals)
}

// Generate simulated match data (in production, would fetch from API)
const generateMatchData = (totalMatches: number) => {
  const matches: Array<{ matchNum: number; runs: number; wickets: number }> = []
  let cumulativeRuns = 0
  let cumulativeWickets = 0

  for (let i = 1; i <= Math.min(totalMatches, 20); i++) {
    const runs = Math.floor(Math.random() * 80) + 10 // 10-90 runs per match
    const wickets = Math.random() > 0.7 ? Math.floor(Math.random() * 3) : 0 // Sometimes no wickets

    cumulativeRuns += runs
    cumulativeWickets += wickets

    matches.push({
      matchNum: i,
      runs,
      wickets,
    })
  }

  return matches
}

const matchData = computed(() => generateMatchData(props.profile?.total_matches || 0))

// Cumulative runs chart
const cumulativeRunsChart = computed(() => {
  if (matchData.value.length === 0) return null

  let cumulative = 0
  const labels = matchData.value.map((m) => `M${m.matchNum}`)
  const data = matchData.value.map((m) => {
    cumulative += m.runs
    return cumulative
  })

  return {
    data: {
      labels,
      datasets: [
        {
          label: 'Cumulative Runs',
          data,
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointHoverRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: true, labels: { font: { size: 12 } } },
      },
      scales: {
        y: { beginAtZero: true, ticks: { font: { size: 11 } } },
        x: { ticks: { font: { size: 11 } } },
      },
    },
  }
})

// Runs per innings chart
const runsPerInningsChart = computed(() => {
  if (matchData.value.length === 0) return null

  const labels = matchData.value.map((m) => `M${m.matchNum}`)
  const data = matchData.value.map((m) => m.runs)

  return {
    data: {
      labels,
      datasets: [
        {
          label: 'Runs per Innings',
          data,
          backgroundColor: 'rgba(34, 197, 94, 0.7)',
          borderColor: 'rgb(34, 197, 94)',
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: true, labels: { font: { size: 12 } } },
      },
      scales: {
        y: { beginAtZero: true, ticks: { font: { size: 11 } } },
        x: { ticks: { font: { size: 11 } } },
      },
    },
  }
})

// Cumulative wickets chart
const cumulativeWicketsChart = computed(() => {
  if (matchData.value.length === 0) return null

  let cumulative = 0
  const labels = matchData.value.map((m) => `M${m.matchNum}`)
  const data = matchData.value.map((m) => {
    cumulative += m.wickets
    return cumulative
  })

  return {
    data: {
      labels,
      datasets: [
        {
          label: 'Cumulative Wickets',
          data,
          borderColor: 'rgb(239, 68, 68)',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointHoverRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: true, labels: { font: { size: 12 } } },
      },
      scales: {
        y: { beginAtZero: true, ticks: { font: { size: 11 } } },
        x: { ticks: { font: { size: 11 } } },
      },
    },
  }
})

// Wickets per innings chart
const wicketsPerInningsChart = computed(() => {
  if (matchData.value.length === 0) return null

  const labels = matchData.value.map((m) => `M${m.matchNum}`)
  const data = matchData.value.map((m) => m.wickets)

  return {
    data: {
      labels,
      datasets: [
        {
          label: 'Wickets per Innings',
          data,
          backgroundColor: 'rgba(249, 115, 22, 0.7)',
          borderColor: 'rgb(249, 115, 22)',
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: true, labels: { font: { size: 12 } } },
      },
      scales: {
        y: { beginAtZero: true, ticks: { font: { size: 11 } } },
        x: { ticks: { font: { size: 11 } } },
      },
    },
  }
})

// Rolling average chart
const rollingAverageChart = computed(() => {
  if (matchData.value.length < 5) return null

  const labels: string[] = []
  const data: number[] = []

  for (let i = 4; i < matchData.value.length; i++) {
    const window = matchData.value.slice(i - 4, i + 1)
    const avg = window.reduce((sum, m) => sum + m.runs, 0) / window.length
    labels.push(`M${matchData.value[i].matchNum}`)
    data.push(Math.round(avg * 10) / 10)
  }

  return {
    data: {
      labels,
      datasets: [
        {
          label: 'Rolling Average (5-match)',
          data,
          borderColor: 'rgb(168, 85, 247)',
          backgroundColor: 'rgba(168, 85, 247, 0.1)',
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointHoverRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: true, labels: { font: { size: 12 } } },
      },
      scales: {
        y: { beginAtZero: true, ticks: { font: { size: 11 } } },
        x: { ticks: { font: { size: 11 } } },
      },
    },
  }
})

// Peak performance
const peakMatch = computed(() => {
  if (matchData.value.length === 0) return '—'
  const max = matchData.value.reduce((prev, current) => (prev.runs > current.runs ? prev : current))
  return `${max.runs} runs (Match ${max.matchNum})`
})
</script>

<style scoped>
.season-graphs-widget {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
}

/* Header */
.season-graphs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
}

.season-graphs-title {
  margin: 0;
  font-size: var(--h3-size);
  font-weight: var(--h3-weight);
  color: var(--color-text);
}

/* Controls */
.season-controls {
  display: flex;
  gap: var(--space-2);
}

.stat-tab-btn {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.stat-tab-btn:hover {
  background: var(--color-bg-secondary);
}

.stat-tab-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

/* Charts Container */
.charts-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.chart-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}

.chart-wrapper {
  padding: var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.chart-wrapper h4 {
  margin: 0;
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text);
}

.chart-wrapper.full-width {
  grid-column: 1 / -1;
}

.no-data {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  text-align: center;
  padding: var(--space-6) 0;
  margin: 0;
}

/* Highlights */
.season-highlights {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}

.highlight-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.highlight-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: 600;
  text-transform: uppercase;
}

.highlight-value {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-primary);
}

/* Responsive */
@media (max-width: 768px) {
  .season-graphs-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .season-controls {
    width: 100%;
    flex-wrap: wrap;
  }

  .chart-section {
    grid-template-columns: 1fr;
  }

  .season-highlights {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>

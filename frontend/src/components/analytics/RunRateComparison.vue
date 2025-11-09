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
} from 'chart.js'
import { computed } from 'vue'
import { Line } from 'vue-chartjs'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend)

const props = defineProps<{
  currentRunRate: number
  requiredRunRate?: number | null
  oversData?: Array<{ over: number; runRate: number }>
  targetScore?: number | null
  currentScore: number
  ballsBowled: number
  oversLimit: number
}>()

const runRateHistory = computed(() => {
  if (!props.oversData || props.oversData.length === 0) {
    // Calculate run rate over the current innings
    const data: Array<{ over: number; runRate: number }> = []
    const completedOvers = Math.floor(props.ballsBowled / 6)
    
    if (completedOvers === 0) {
      return data
    }
    
    // For each over, calculate cumulative run rate
    // Run rate = total runs / total overs at that point
    for (let i = 1; i <= completedOvers; i++) {
      const runRate = (props.currentScore / i)
      data.push({ over: i, runRate })
    }
    
    return data
  }
  return props.oversData
})

const chartData = computed(() => {
  const labels = runRateHistory.value.map(d => `Over ${d.over}`)
  const datasets = []
  
  // Current run rate line
  datasets.push({
    label: 'Current Run Rate',
    data: runRateHistory.value.map(d => d.runRate),
    borderColor: '#2563eb',
    backgroundColor: '#2563eb',
    tension: 0.3,
    pointRadius: 3,
    pointHoverRadius: 5,
    fill: false,
  })
  
  // Required run rate line (if chasing)
  if (props.requiredRunRate != null && props.requiredRunRate > 0) {
    const rrr = props.requiredRunRate
    datasets.push({
      label: 'Required Run Rate',
      data: runRateHistory.value.map(() => rrr),
      borderColor: '#f97316',
      backgroundColor: '#f97316',
      borderDash: [5, 5],
      pointRadius: 0,
      pointHoverRadius: 3,
      fill: false,
    })
  }
  
  return {
    labels,
    datasets,
  }
})

const options = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index' as const,
    intersect: false,
  },
  plugins: {
    legend: { 
      position: 'bottom' as const,
      labels: {
        padding: 12,
        usePointStyle: true,
      }
    },
    tooltip: { 
      mode: 'index' as const, 
      intersect: false,
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      padding: 12,
      titleFont: {
        size: 14,
        weight: 'bold' as const,
      },
      bodyFont: {
        size: 13,
      },
      callbacks: {
        label: function(context: { dataset: { label?: string }; parsed: { y: number | null } }) {
          const label = context.dataset.label || '';
          const value = context.parsed.y ?? 0;
          return `${label}: ${value.toFixed(2)} rpo`;
        }
      }
    },
    title: {
      display: true,
      text: 'Run Rate Comparison',
      font: {
        size: 16,
        weight: 'bold' as const,
      }
    }
  },
  scales: {
    x: { 
      display: true,
      grid: {
        display: true,
        color: 'rgba(0, 0, 0, 0.05)',
      },
      title: {
        display: true,
        text: 'Overs',
      }
    },
    y: { 
      beginAtZero: true,
      title: {
        display: true,
        text: 'Run Rate (runs per over)',
      },
      ticks: {
        precision: 1,
      }
    },
  },
}
</script>

<template>
  <div class="run-rate-comparison">
    <div v-if="runRateHistory.length > 0" class="chart">
      <Line :data="chartData" :options="options" />
    </div>
    <div v-else class="empty-state">
      No run rate data available yet. Data will appear as overs are completed.
    </div>
    
    <div class="stats-summary">
      <div class="stat-item">
        <span class="stat-label">Current Run Rate:</span>
        <span class="stat-value current">{{ currentRunRate.toFixed(2) }} rpo</span>
      </div>
      <div v-if="requiredRunRate != null && requiredRunRate > 0" class="stat-item">
        <span class="stat-label">Required Run Rate:</span>
        <span class="stat-value required">{{ requiredRunRate.toFixed(2) }} rpo</span>
      </div>
      <div v-if="requiredRunRate != null && requiredRunRate > 0" class="stat-item">
        <span class="stat-label">Difference:</span>
        <span 
          class="stat-value" 
          :class="currentRunRate >= requiredRunRate ? 'ahead' : 'behind'"
        >
          {{ Math.abs(currentRunRate - requiredRunRate).toFixed(2) }} rpo
          {{ currentRunRate >= requiredRunRate ? '(ahead)' : '(behind)' }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.run-rate-comparison {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chart {
  height: 280px;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: #6b7280;
  font-size: 14px;
  background: #f9fafb;
  border-radius: 8px;
}

.stats-summary {
  display: grid;
  gap: 12px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
}

.stat-value.current {
  color: #2563eb;
}

.stat-value.required {
  color: #f97316;
}

.stat-value.ahead {
  color: #22c55e;
}

.stat-value.behind {
  color: #dc2626;
}
</style>

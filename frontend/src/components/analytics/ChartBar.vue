<script setup lang="ts">
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const props = defineProps<{
  labels: string[]
  series: Array<{ label: string; data: (number | null)[] }>
}>()

const colors = ['#2563eb', '#f97316', '#22c55e', '#a855f7']

const chartData = computed(() => ({
  labels: props.labels,
  datasets: props.series.map((s, idx) => ({
    label: s.label,
    data: s.data,
    backgroundColor: colors[idx % colors.length],
    borderRadius: 4,
  })),
}))

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
        label: function(context: any) {
          const label = context.dataset.label || '';
          const value = context.parsed.y;
          return `${label}: ${value} runs`;
        }
      }
    },
  },
  scales: {
    x: { 
      stacked: false,
      grid: {
        display: false,
      }
    },
    y: { 
      beginAtZero: true,
      title: {
        display: true,
        text: 'Runs per Over',
      },
      ticks: {
        precision: 0,
      }
    },
  },
}
</script>

<template>
  <div class="chart"><Bar :data="chartData" :options="options" /></div>
</template>

<style scoped>
.chart {
  height: 220px;
}
</style>

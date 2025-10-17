<script setup lang="ts">
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
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

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend)

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
    borderColor: colors[idx % colors.length],
    backgroundColor: colors[idx % colors.length],
    tension: 0.3,
    spanGaps: true,
    pointRadius: 3,
    pointHoverRadius: 5,
    fill: false,
  })),
}))

const options = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom' as const },
    tooltip: { mode: 'index' as const, intersect: false },
  },
  scales: {
    x: { display: true },
    y: { beginAtZero: true },
  },
}
</script>

<template>
  <div class="chart"><Line :data="chartData" :options="options" /></div>
</template>

<style scoped>
.chart {
  height: 220px;
}
</style>

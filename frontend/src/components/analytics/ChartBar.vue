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
  plugins: {
    legend: { position: 'bottom' as const },
    tooltip: { mode: 'index' as const, intersect: false },
  },
  scales: {
    x: { stacked: false },
    y: { beginAtZero: true },
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

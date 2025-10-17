<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ series: Array<{ name: string; values: number[] }>; width?: number; height?: number }>()
const width = computed(()=> props.width ?? 520)
const height = computed(()=> props.height ?? 180)
const padding = 24
const maxVal = computed(()=> Math.max(1, ...props.series.flatMap(s=>s.values)))
const maxLen = computed(()=> Math.max(0, ...props.series.map(s=>s.values.length)))
const xStep = computed(()=> maxLen.value > 1 ? (width.value - padding*2) / (maxLen.value - 1) : 0)
const colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
function pathFor(vals: number[]): string {
  if (!vals.length) return ''
  const pts = vals.map((v, i) => {
    const x = padding + i * xStep.value
    const y = (height.value - padding) - ((v / maxVal.value) * (height.value - padding))
    return `${i===0?'M':'L'}${x},${y}`
  })
  return pts.join(' ')
}
</script>

<template>
  <svg :width="width" :height="height" role="img" aria-label="Line chart">
    <g>
      <template v-for="(s, si) in series" :key="si">
        <path :d="pathFor(s.values)" :stroke="colors[si % colors.length]" stroke-width="2" fill="none" />
      </template>
    </g>
  </svg>
</template>

<style scoped>
svg { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; }
</style>

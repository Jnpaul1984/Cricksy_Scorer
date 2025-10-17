<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ series: Array<{ name: string; values: number[] }>; width?: number; height?: number }>()
const width = computed(()=> props.width ?? 520)
const height = computed(()=> props.height ?? 180)
const padding = 24
const allVals = computed(()=> props.series.flatMap(s=>s.values))
const maxVal = computed(()=> Math.max(1, ...allVals.value))
const maxLen = computed(()=> Math.max(0, ...props.series.map(s=>s.values.length)))
const barW = computed(()=> maxLen.value ? (width.value - padding*2) / (maxLen.value * props.series.length + (maxLen.value+1)) : 0)
const colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
</script>

<template>
  <svg :width="width" :height="height" role="img" aria-label="Bar chart">
    <g :transform="`translate(${padding},${padding/2})`">
      <template v-for="(s, si) in series" :key="si">
        <template v-for="(v, i) in s.values" :key="i">
          <rect
            :x="barW * (i * (series.length + 1) + si + 1) + (i * barW)"
            :y="(height - padding) - ((v / maxVal) * (height - padding))"
            :width="barW"
            :height="((v / maxVal) * (height - padding))"
            :fill="colors[si % colors.length]"
            opacity="0.9"
          />
        </template>
      </template>
    </g>
  </svg>
</template>

<style scoped>
svg { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; }
</style>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  strokes: Array<{ angleDeg: number; runs: number; kind?: '4'|'6'|'other' }>
  size?: number
  showLegend?: boolean
}>()

const size = computed(() => props.size ?? 220)
const r = computed(() => (size.value / 2) - 8)
const hoveredStroke = ref<number | null>(null)

function polar(angleDeg: number, radius: number) {
  const a = (angleDeg - 90) * Math.PI / 180
  return { x: (size.value / 2) + Math.cos(a) * radius, y: (size.value / 2) + Math.sin(a) * radius }
}

function getStrokeColor(kind?: '4' | '6' | 'other'): string {
  return kind === '6' ? '#22c55e' : (kind === '4' ? '#2563eb' : '#94a3b8')
}

function getStrokeWidth(index: number): number {
  return hoveredStroke.value === index ? 3 : 2
}

const strokeCounts = computed(() => {
  const counts = { sixes: 0, fours: 0, other: 0 }
  props.strokes.forEach(s => {
    if (s.kind === '6') counts.sixes++
    else if (s.kind === '4') counts.fours++
    else counts.other++
  })
  return counts
})
</script>

<template>
  <div class="wagon-wheel-container">
    <svg
      :width="size"
      :height="size"
      role="img"
      aria-label="Wagon wheel"
      class="wagon-wheel-svg"
    >
      <!-- outer circle -->
      <circle :cx="size/2" :cy="size/2" :r="r" fill="#fafafa" stroke="#e5e7eb" />

      <!-- guidelines every 30deg -->
      <template v-for="a in 12" :key="a">
        <line
          :x1="size/2"
          :y1="size/2"
          :x2="polar((a-1)*30, r).x"
          :y2="polar((a-1)*30, r).y"
          stroke="#eee"
        />
      </template>

      <!-- strokes -->
      <template v-for="(s, i) in strokes" :key="i">
        <line
          :x1="size/2"
          :y1="size/2"
          :x2="polar(s.angleDeg, r).x"
          :y2="polar(s.angleDeg, r).y"
          :stroke="getStrokeColor(s.kind)"
          :stroke-width="getStrokeWidth(i)"
          class="stroke-line"
          @mouseenter="hoveredStroke = i"
          @mouseleave="hoveredStroke = null"
        >
          <title>{{ s.runs }} run{{ s.runs !== 1 ? 's' : '' }} at {{ s.angleDeg.toFixed(0) }}°</title>
        </line>
      </template>
    </svg>

    <div v-if="showLegend !== false" class="legend">
      <div class="legend-item">
        <span class="legend-dot six"></span>
        <span class="legend-text">Sixes ({{ strokeCounts.sixes }})</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot four"></span>
        <span class="legend-text">Fours ({{ strokeCounts.fours }})</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot other"></span>
        <span class="legend-text">Other runs ({{ strokeCounts.other }})</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wagon-wheel-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.wagon-wheel-svg {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.stroke-line {
  cursor: pointer;
  transition: stroke-width 0.2s ease;
}

.stroke-line:hover {
  opacity: 0.8;
}

.legend {
  display: flex;
  gap: 16px;
  align-items: center;
  font-size: 13px;
  flex-wrap: wrap;
  justify-content: center;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 12px;
  height: 3px;
  border-radius: 1px;
}

.legend-dot.six {
  background-color: #22c55e;
}

.legend-dot.four {
  background-color: #2563eb;
}

.legend-dot.other {
  background-color: #94a3b8;
}

.legend-text {
  color: #475569;
}
</style>

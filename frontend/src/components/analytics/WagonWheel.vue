<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ strokes: Array<{ angleDeg: number; runs: number; kind?: '4'|'6'|'other' }>; size?: number }>()
const size = computed(()=> props.size ?? 220)
const r = computed(()=> (size.value/2) - 8)
function polar(angleDeg: number, radius: number){
  const a = (angleDeg - 90) * Math.PI/180
  return { x: (size.value/2) + Math.cos(a)*radius, y: (size.value/2) + Math.sin(a)*radius }
}
</script>

<template>
  <svg :width="size" :height="size" role="img" aria-label="Wagon wheel">
    <!-- outer circle -->
    <circle :cx="size/2" :cy="size/2" :r="r" fill="#fafafa" stroke="#e5e7eb" />
    <!-- guidelines every 30deg -->
    <template v-for="a in 12" :key="a">
      <line :x1="size/2" :y1="size/2" :x2="polar((a-1)*30, r).x" :y2="polar((a-1)*30, r).y" stroke="#eee" />
    </template>
    <!-- strokes -->
    <template v-for="(s,i) in strokes" :key="i">
      <line
:x1="size/2" :y1="size/2" :x2="polar(s.angleDeg, r).x" :y2="polar(s.angleDeg, r).y"
            :stroke="s.kind==='6' ? '#22c55e' : (s.kind==='4' ? '#2563eb' : '#94a3b8')" stroke-width="2" />
    </template>
  </svg>
</template>

<style scoped>
svg { background:#fff; border:1px solid #e5e7eb; border-radius:8px; }
</style>

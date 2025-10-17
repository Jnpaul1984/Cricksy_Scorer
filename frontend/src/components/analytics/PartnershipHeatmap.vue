<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  players: Array<{ id: string; name: string }>
  matrix: number[][]
}>()

const maxVal = computed(() => {
  const flat = props.matrix.flat()
  return flat.length ? Math.max(...flat, 0) : 0
})

function cellBackground(value: number): string {
  if (!maxVal.value) return '#f8fafc'
  const alpha = Math.min(0.9, value / maxVal.value)
  return `rgba(37, 99, 235, ${alpha})`
}
</script>

<template>
  <div v-if="players.length" class="heatmap">
    <table class="tbl">
      <thead>
        <tr>
          <th></th>
          <th v-for="p in players" :key="p.id">{{ p.name }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, i) in matrix" :key="players[i]?.id || i">
          <th>{{ players[i]?.name }}</th>
          <td
            v-for="(value, j) in row"
            :key="j"
            :style="{ background: cellBackground(value) }"
          >
            <span class="cell">{{ value || '' }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <div v-else class="empty">No partnership data.</div>
</template>

<style scoped>
.heatmap {
  overflow: auto;
  max-height: 320px;
}
.tbl {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 12px;
}
.tbl th,
.tbl td {
  border: 1px solid #e5e7eb;
  padding: 4px;
  text-align: center;
  min-width: 48px;
}
.tbl thead th {
  position: sticky;
  top: 0;
  background: #f8fafc;
}
.cell {
  display: block;
  color: #1f2937;
  mix-blend-mode: difference;
}
.empty {
  color: #6b7280;
  font-size: 13px;
}
</style>

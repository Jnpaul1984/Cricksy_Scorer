<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ players: Array<{ id: string; name: string }>; matrix: number[][] }>()
const maxVal = computed(()=> Math.max(1, ...props.matrix.flat()))
</script>

<template>
  <div class="heat">
    <table class="tbl">
      <thead>
        <tr>
          <th></th>
          <th v-for="p in players" :key="p.id">{{ p.name }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row,i) in matrix" :key="i">
          <th>{{ players[i]?.name }}</th>
          <td v-for="(v,j) in row" :key="j" :style="{ background: `rgba(37,99,235,${Math.min(0.95, v/maxVal)})` }">
            <span class="cell">{{ v || '' }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <small class="hint">Values represent total runs scored while each pair batted together (includes extras).</small>
</template>

<style scoped>
.tbl { width: 100%; border-collapse: collapse; table-layout: fixed; }
.tbl th, .tbl td { border: 1px solid #eee; padding: 4px; text-align: center; font-size: 12px; }
.tbl thead th { position: sticky; top: 0; background: #f8fafc; }
.cell { display:block; color:#111827; mix-blend-mode: difference; }
.heat { overflow:auto; max-height: 360px; }
</style>

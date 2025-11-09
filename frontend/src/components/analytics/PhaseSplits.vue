<script setup lang="ts">
const { splits } = defineProps<{ splits: Array<{ name:string; runs:number; overs:number; wkts:number }> }>()
</script>

<template>
  <table class="tbl">
    <thead><tr><th>Phase</th><th>Runs</th><th>Overs</th><th>Wkts</th><th>RPO</th></tr></thead>
    <tbody>
      <tr v-for="p in splits" :key="p.name">
        <td>{{ p.name }}</td>
        <td>{{ p.runs }}</td>
        <td>{{ p.overs.toFixed(1) }}</td>
        <td>{{ p.wkts }}</td>
        <td>{{ (p.overs>0 ? (p.runs/p.overs) : 0).toFixed(2) }}</td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.tbl { width:100%; border-collapse: collapse; }
.tbl th, .tbl td { border-bottom:1px solid #eee; padding:6px 8px; text-align:left; }
</style>

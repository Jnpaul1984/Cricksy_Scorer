<template>
  <div class="fan-stats-view">
    <FanStatsWidget />
  </div>
</template>

<script setup lang="ts">
import FanStatsWidget from '@/components/FanStatsWidget.vue'
</script>

<style scoped>
.fan-stats-view {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}
</style>

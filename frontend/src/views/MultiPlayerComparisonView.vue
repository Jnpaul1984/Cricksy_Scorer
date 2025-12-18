<template>
  <div class="multi-player-comparison-view">
    <MultiPlayerComparisonWidget />
  </div>
</template>

<script setup lang="ts">
import MultiPlayerComparisonWidget from '@/components/MultiPlayerComparisonWidget.vue'
</script>

<style scoped>
.multi-player-comparison-view {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}
</style>

<template>
  <div class="phase-analysis-view">
    <PhaseAnalysisWidget />
  </div>
</template>

<script setup lang="ts">
import PhaseAnalysisWidget from '@/components/PhaseAnalysisWidget.vue'
</script>

<style scoped>
.phase-analysis-view {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}
</style>

<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'

import ScoreboardWidget from '@/components/ScoreboardWidget.vue'
import { useGameStore } from '@/stores/gameStore'

// Provide a test-only hook on this route to inject a match fixture
// into the Pinia store so the widget can render the result banner.
function applyMatch(match: any) {
  const store = useGameStore()
  store.currentGame = {
    id: 'e2e',
    team_a: { name: match?.teams?.[0] ?? 'Team A', players: [] },
    team_b: { name: match?.teams?.[1] ?? 'Team B', players: [] },
    status: 'completed',
    current_inning: 2,
    result: { result_text: match?.result?.summary ?? '' },
  } as any
}

;(window as any).loadMatch = (match: any) => applyMatch(match)

function onE2eMatch() {
  const pending: any = (window as any).__pendingMatch
  if (pending) applyMatch(pending)
}

onMounted(() => {
  // If Cypress pushed a match before this view loaded, apply it now
  onE2eMatch()
  // Listen for future pushes
  window.addEventListener('e2e:match', onE2eMatch)
})

onBeforeUnmount(() => {
  window.removeEventListener('e2e:match', onE2eMatch)
})
</script>

<template>
  <div style="padding: 1rem">
    <ScoreboardWidget :game-id="'e2e'" />
  </div>
  
</template>

<style scoped>
</style>

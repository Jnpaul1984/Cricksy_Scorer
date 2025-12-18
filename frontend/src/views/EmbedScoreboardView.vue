<template>
  <div class="embed-wrap" :style="rootStyle">
    <ScoreboardWidget
      :theme="theme"
      :title="title"
      :logo="logo"
      :api-base="apiBase"
      :game-id="gameId"
      :sponsors-url="sponsorsUrl"
      :sponsor-rotate-ms="sponsorRotateMs"
      :sponsor-clickable="sponsorClickable"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'

import ScoreboardWidget from '@/components/ScoreboardWidget.vue'
import { useProjectorMode } from '@/composables/useProjectorMode'
import { useGameStore } from '@/stores/gameStore'
import { API_BASE } from '@/utils/api'

const route = useRoute()
const gameId = computed(() => String(route.params.gameId))
const gameStore = useGameStore()

const q = route.query as Record<string, string | undefined>
const theme = (q.theme as string) === 'dark' ? 'dark'
  : (q.theme as string) === 'light' ? 'light'
  : 'auto'

const title = (q.title as string) || ''
const logo = (q.logo as string) || ''
const sponsorsUrl = (q.sponsorsUrl as string) || ''
const sponsorRotateMs = Number(q.sponsorRotateMs ?? 8000)
const sponsorClickable = String(q.sponsorClickable ?? 'false') === 'true'

const fallbackOrigin = typeof window !== 'undefined' ? window.location.origin : ''
const apiBase = ((q.apiBase as string) || API_BASE || fallbackOrigin).replace(/\/$/, '')

/**
 * Projector mode config
 */
const projectorMode = useProjectorMode(q)
const rootStyle = computed(() => 
  projectorMode.cssVariables.value as Record<string, string>
)

onMounted(() => {
  gameStore.setPublicViewerMode(true)
})

onBeforeUnmount(() => {
  gameStore.setPublicViewerMode(false)
})
</script>

<style scoped>
/* =====================================================
   EMBED SCOREBOARD VIEW - Minimal iframe-friendly wrapper
   Uses Design System Tokens
   ===================================================== */

.embed-wrap {
  /* Fill the entire iframe viewport */
  width: 100%;
  min-height: 100dvh;

  /* Center the widget */
  display: grid;
  place-items: center;

  /* Use design system background */
  background: var(--color-bg);

  /* Minimal padding to prevent edge clipping */
  padding: var(--space-2);
  box-sizing: border-box;

  /* Prevent scrollbars from iframe sizing issues */
  overflow: hidden;
}

/* ScoreboardWidget sizing */
.embed-wrap > :deep(*) {
  width: min(100%, 780px);
  max-width: 100%;
}
</style>

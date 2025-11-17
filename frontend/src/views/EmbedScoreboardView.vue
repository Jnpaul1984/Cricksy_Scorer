<template>
  <div class="embed-wrap">
    <div class="embed-card">
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'

import ScoreboardWidget from '@/components/ScoreboardWidget.vue'
import { API_BASE } from '@/utils/api'
import { useGameStore } from '@/stores/gameStore'

const route = useRoute()
const gameId = computed(() => String(route.params.gameId))
const gameStore = useGameStore()

const q = route.query
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

onMounted(() => {
  gameStore.setPublicViewerMode(true)
})

onBeforeUnmount(() => {
  gameStore.setPublicViewerMode(false)
})
</script>

<style scoped>
.embed-wrap { min-height: 100dvh; display: grid; place-items: center; background: #000; }
.embed-card { width: min(92vw, 780px); }
</style>

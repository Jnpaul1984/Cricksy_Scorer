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
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import ScoreboardWidget from '@/components/ScoreboardWidget.vue'

const route = useRoute()
const gameId = computed(() => String(route.params.gameId))

const q = route.query
const theme = (q.theme as string) === 'dark' ? 'dark'
  : (q.theme as string) === 'light' ? 'light'
  : 'auto'

const title = (q.title as string) || ''
const logo = (q.logo as string) || ''
const sponsorsUrl = (q.sponsorsUrl as string) || ''
const sponsorRotateMs = Number(q.sponsorRotateMs ?? 8000)
const sponsorClickable = String(q.sponsorClickable ?? 'false') === 'true'

// allow override; default to local dev backend
const apiBase = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'
</script>

<style scoped>
.embed-wrap { min-height: 100dvh; display: grid; place-items: center; background: #000; }
.embed-card { width: min(92vw, 780px); }
</style>

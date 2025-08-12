<template>
  <main class="view-wrap">
    <ScoreboardWidget
      :game-id="gameId"
      :title="`Match ${gameId.slice(0,8)}…`"
      :theme="prefTheme"
      :api-base="apiBase"
    />
  </main>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import ScoreboardWidget from '@/components/ScoreboardWidget.vue'

const route = useRoute()
const gameId = computed(() => String(route.params.gameId))
const apiBase = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'

// Honor OS preference here; you can swap to a user setting if you have one.
const prefTheme = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
</script>

<style scoped>
.view-wrap { min-height: 100dvh; display: grid; place-items: center; padding: 20px; }
</style>

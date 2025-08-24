<template>
  <main class="view-wrap">
    <header class="bar">
      <div class="left">
        <h2 class="title">Scoreboard Viewer</h2>
        <span v-if="gameId" class="meta">Game: {{ gameId }}</span>
      </div>
      <div class="right">
        <button class="btn" @click="openInNewTab">Open in new tab</button>
        <a class="btn btn-ghost" :href="viewerUrl" target="_blank" rel="noopener">Share link</a>
      </div>
    </header>

    <ScoreboardWidget
      :game-id="gameId"
      :title="`Match ${gameId.slice(0, 8)}…`"
      :theme="prefTheme"
      :api-base="apiBase"
      interruptions-mode="auto"  
      :poll-ms="5000"
    />
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import ScoreboardWidget from '@/components/ScoreboardWidget.vue'

const route = useRoute()
const gameId = computed(() => String(route.params.gameId || ''))

// Use the same base your API expects; falls back to localhost for dev
const apiBase = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'

// Safer theme detection that won’t blow up in SSR/build
const prefTheme = ref<'dark' | 'light'>('light')
onMounted(() => {
  if (typeof window !== 'undefined' && window.matchMedia) {
    prefTheme.value = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
})

// Public URL to this viewer (hash-mode by default). If you use history mode, drop the '/#'.
const viewerUrl = computed(() => {
  const origin = typeof window !== 'undefined' ? window.location.origin : ''
  return `${origin}/#/viewer/${encodeURIComponent(gameId.value)}`
})

function openInNewTab() {
  if (!gameId.value) return
  window.open(viewerUrl.value, '_blank', 'noopener')
}
</script>

<style scoped>
.view-wrap { min-height: 100dvh; display: grid; gap: 12px; padding: 16px; align-content: start; }
.bar { display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 8px; }
.left { display: flex; align-items: baseline; gap: 10px; }
.title { margin: 0; font-size: 16px; font-weight: 800; }
.meta { font-size: 12px; color: #6b7280; }
.right { display: inline-flex; gap: 8px; }
.btn { appearance: none; border-radius: 10px; padding: 8px 12px; font-weight: 700; font-size: 14px; cursor: pointer; border: 1px solid #e5e7eb; background: #fff; color: #111827; text-decoration: none; }
.btn-ghost { background: #fff; color: #111827; border: 1px solid #e5e7eb; }
</style>
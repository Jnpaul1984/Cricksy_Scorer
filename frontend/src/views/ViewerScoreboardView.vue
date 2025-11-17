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

    <!-- Decorative stage that keeps rails visible and looks nice in OBS/embeds -->
    <section class="stage">
      <ScoreboardWidget
        :game-id="gameId"
        :title="resolvedTitle"
        :theme="resolvedTheme"
        :logo="resolvedLogo"
        :api-base="apiBase"
        :sponsors-url="sponsorsUrl"
        interruptions-mode="auto"
        :poll-ms="5000"
      />
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useRoute } from 'vue-router'

import ScoreboardWidget from '@/components/ScoreboardWidget.vue'
import { API_BASE } from '@/utils/api'
import { useGameStore } from '@/stores/gameStore'

/**
 * Route & params
 */
const route = useRoute()
const gameId = computed(() => String(route.params.gameId || ''))

/**
 * Query param helpers (allow overrides from the URL)
 * e.g.  /#/viewer/123?apiBase=https://api.example.com&sponsorsUrl=https://…/sponsors.json
 *       &title=My%20Match&logo=https://…/logo.png&theme=dark
 */
const q = route.query as Record<string, string | undefined>

const fallbackOrigin = typeof window !== 'undefined' ? window.location.origin : ''
const apiBase = computed<string>(() =>
  ((q.apiBase as string) || API_BASE || fallbackOrigin).replace(/\/$/, '')
)

const gameStore = useGameStore()

const sponsorsUrl = computed<string>(() =>
  (q.sponsorsUrl as string) ||
  `${apiBase.value}/games/${encodeURIComponent(gameId.value)}/sponsors`
)

const resolvedTitle = computed<string>(() =>
  (q.title as string) || `Match ${gameId.value.slice(0, 8)}…`
)

const resolvedLogo = computed<string>(() =>
  (q.logo as string) || ''
)

type ThemeOpt = 'auto' | 'dark' | 'light'
const resolvedTheme = ref<ThemeOpt>(
  (q.theme as ThemeOpt) || 'auto'
)

/**
 * If theme=auto, pick one based on prefers-color-scheme
 */
onMounted(() => {
  gameStore.setPublicViewerMode(true)
  if (resolvedTheme.value === 'auto' && typeof window !== 'undefined' && window.matchMedia) {
    resolvedTheme.value = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
})

onBeforeUnmount(() => {
  gameStore.setPublicViewerMode(false)
})

/**
 * Shareable viewer URL that keeps current overrides
 */
const viewerUrl = computed(() => {
  const origin = typeof window !== 'undefined' ? window.location.origin : ''
  const params = new URLSearchParams()
  if (q.apiBase)      params.set('apiBase', String(q.apiBase))
  if (q.sponsorsUrl)  params.set('sponsorsUrl', String(q.sponsorsUrl))
  if (q.title)        params.set('title', String(q.title))
  if (q.logo)         params.set('logo', String(q.logo))
  if (q.theme)        params.set('theme', String(q.theme))
  const qs = params.toString()
  return `${origin}/#/viewer/${encodeURIComponent(gameId.value)}${qs ? `?${qs}` : ''}`
})

function openInNewTab() {
  if (!gameId.value) return
  window.open(viewerUrl.value, '_blank', 'noopener')
}
</script>

<style scoped>
/* Page shell */
.view-wrap {
  min-height: 100dvh;
  display: grid;
  gap: 16px;
  padding: 16px;
  align-content: start;
  background:
    radial-gradient(1200px 600px at 10% -10%, rgba(34,211,238,.12), transparent 60%),
    radial-gradient(900px 480px at 100% 0%, rgba(16,185,129,.10), transparent 55%),
    linear-gradient(180deg, rgba(2,6,23,1) 0%, rgba(2,6,23,.94) 240px, rgba(2,6,23,.94) 100%);
  color: #e5e7eb;
  overflow: visible; /* keep any child abs-pos content safe */
}

/* Header bar */
.bar {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 10px;
}
.left { display: flex; align-items: baseline; gap: 10px; }
.title { margin: 0; font-size: 18px; font-weight: 900; letter-spacing: .01em; }
.meta { font-size: 12px; color: #9ca3af; }
.right { display: inline-flex; gap: 8px; }

/* Buttons */
.btn, .btn-ghost {
  appearance: none;
  border-radius: 10px;
  padding: 8px 12px;
  font-weight: 800;
  font-size: 14px;
  cursor: pointer;
  text-decoration: none;
}
.btn {
  border: 1px solid rgba(255,255,255,.12);
  background: rgba(255,255,255,.08);
  color: #e5e7eb;
  backdrop-filter: blur(8px);
}
.btn:hover { background: rgba(255,255,255,.12); }
.btn-ghost {
  border: 1px solid rgba(255,255,255,.16);
  background: transparent;
  color: #e5e7eb;
}
.btn-ghost:hover { background: rgba(255,255,255,.06); }

/* Decorative stage around the widget */
.stage {
  position: relative;
  width: min(1100px, 96vw);
  margin: 0 auto;
  padding: 16px;
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02));
  border: 1px solid rgba(255,255,255,.10);
  box-shadow:
    0 10px 30px rgba(0,0,0,.35),
    inset 0 1px 0 rgba(255,255,255,.06);
  overflow: visible; /* <- important so ScoreboardWidget side rails are never clipped */
}

/* Light-mode polish for the page shell (not the widget) */
@media (prefers-color-scheme: light) {
  .view-wrap {
    background:
      radial-gradient(1200px 600px at 10% -10%, rgba(34,211,238,.10), transparent 60%),
      radial-gradient(900px 480px at 100% 0%, rgba(16,185,129,.08), transparent 55%),
      linear-gradient(180deg, #f8fafc 0%, #ffffff 240px, #ffffff 100%);
    color: #0b0f1a;
  }
  .btn, .btn-ghost { color: #0b0f1a; border-color: #e5e7eb; }
  .btn { background: #ffffff; }
  .btn:hover { background: #f3f4f6; }
  .stage {
    background: linear-gradient(180deg, #ffffff, #f9fafb);
    border-color: #e5e7eb;
    box-shadow:
      0 10px 30px rgba(2,6,23,.08),
      inset 0 1px 0 #fff;
  }
}
</style>

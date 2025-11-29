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
import { useGameStore } from '@/stores/gameStore'
import { API_BASE } from '@/utils/api'

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
/* =====================================================
   VIEWER SCOREBOARD VIEW - Using Design System Tokens
   ===================================================== */

/* Page shell */
.view-wrap {
  min-height: 100dvh;
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4);
  align-content: start;
  background:
    radial-gradient(1200px 600px at 10% -10%, var(--color-primary-soft), transparent 60%),
    radial-gradient(900px 480px at 100% 0%, var(--color-secondary-soft), transparent 55%),
    linear-gradient(180deg, var(--color-bg) 0%, var(--color-bg) 240px, var(--color-bg) 100%);
  color: var(--color-text);
  overflow: visible;
}

/* Header bar */
.bar {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: var(--space-3);
}

.left {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.title {
  margin: 0;
  font-size: var(--h3-size);
  font-weight: var(--font-extrabold);
  letter-spacing: 0.01em;
}

.meta {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.right {
  display: inline-flex;
  gap: var(--space-2);
}

/* Buttons */
.btn, .btn-ghost {
  appearance: none;
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  font-weight: var(--font-extrabold);
  font-size: var(--text-sm);
  cursor: pointer;
  text-decoration: none;
  transition: background var(--transition-fast);
}

.btn {
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  backdrop-filter: blur(8px);
}

.btn:hover {
  background: var(--color-surface-hover);
}

.btn-ghost {
  border: 1px solid var(--color-border-strong);
  background: transparent;
  color: var(--color-text);
}

.btn-ghost:hover {
  background: var(--color-surface-hover);
}

/* Decorative stage around the widget */
.stage {
  position: relative;
  width: min(1100px, 96vw);
  margin: 0 auto;
  padding: var(--space-4);
  border-radius: var(--radius-xl);
  background: linear-gradient(180deg, var(--color-surface), var(--color-bg));
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-lg);
  overflow: visible;
}

/* Dark mode adjustments */
@media (prefers-color-scheme: dark) {
  .view-wrap {
    background:
      radial-gradient(1200px 600px at 10% -10%, var(--color-primary-soft), transparent 60%),
      radial-gradient(900px 480px at 100% 0%, var(--color-secondary-soft), transparent 55%),
      linear-gradient(180deg, var(--color-bg) 0%, var(--color-bg) 240px, var(--color-bg) 100%);
    color: var(--color-text);
  }

  .btn, .btn-ghost {
    color: var(--color-text);
    border-color: var(--color-border);
  }

  .btn {
    background: var(--color-surface);
  }

  .btn:hover {
    background: var(--color-surface-hover);
  }

  .stage {
    background: linear-gradient(180deg, var(--color-surface), var(--color-bg));
    border-color: var(--color-border);
    box-shadow: var(--shadow-lg);
  }
}
</style>

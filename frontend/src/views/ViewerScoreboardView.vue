<template>
  <main class="view-wrap">
    <BaseCard as="header" padding="sm" class="bar">
      <div class="left">
        <h2 class="title">Scoreboard Viewer</h2>
        <BaseBadge v-if="gameId" variant="neutral" :uppercase="false">
          Game: {{ gameId.slice(0, 8) }}…
        </BaseBadge>
      </div>

      <div class="right">
        <BaseButton variant="secondary" size="sm" @click="openInNewTab">
          Open in new tab
        </BaseButton>
        <a
          class="ds-btn ds-btn--ghost ds-btn--sm"
          :href="viewerUrl"
          target="_blank"
          rel="noopener"
        >
          Share link
        </a>
      </div>
    </BaseCard>

    <!-- Decorative stage that keeps rails visible and looks nice in OBS/embeds -->
    <BaseCard as="section" padding="lg" class="stage">
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
    </BaseCard>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useRoute } from 'vue-router'

import { BaseButton, BaseCard, BaseBadge } from '@/components'
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
  align-items: center;
  gap: var(--space-3);
}

.title {
  margin: 0;
  font-size: var(--h3-size);
  font-weight: var(--font-extrabold);
  letter-spacing: 0.01em;
}

.right {
  display: inline-flex;
  gap: var(--space-2);
}

/* Decorative stage around the widget */
.stage {
  position: relative;
  width: min(1100px, 96vw);
  margin: 0 auto;
  background: linear-gradient(180deg, var(--color-surface), var(--color-bg));
  overflow: visible;
}

/* Responsive adjustments */
@media (max-width: 640px) {
  .bar {
    grid-template-columns: 1fr;
    gap: var(--space-3);
  }

  .left {
    flex-wrap: wrap;
  }

  .right {
    justify-content: flex-start;
  }
}
</style>

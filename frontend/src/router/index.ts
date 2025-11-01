import { createRouter, createWebHistory, createWebHashHistory } from 'vue-router'

// Choose routing strategy at build/deploy time
// - history (default): clean URLs like /game/123/scoring (needs server fallback to index.html)
// - hash: URLs like /#/game/123/scoring (works on any static host)
const ROUTER_MODE = (import.meta as any).env?.VITE_ROUTER_MODE || 'history'
const history = ROUTER_MODE === 'hash'
  ? createWebHashHistory(import.meta.env.BASE_URL)
  : createWebHistory(import.meta.env.BASE_URL)

const router = createRouter({
  history,
  routes: [
    {
      path: '/',
      name: 'setup',
      component: () => import('@/views/MatchSetupView.vue'),
    },
    {
      path: '/analytics',
      name: 'AnalyticsView',
      component: () => import('@/views/AnalyticsView.vue'),
    },
    {
      path: '/players/:playerId/profile',
      name: 'player-profile',
      component: () => import('@/views/PlayerProfileView.vue'),
      props: true,
    },
    {
      path: '/leaderboard',
      name: 'leaderboard',
      component: () => import('@/views/LeaderboardView.vue'),
    },
    {
      path: '/e2e',
      name: 'e2e-view',
      component: () => import('@/views/E2EView.vue'),
    },
    {
      path: '/game/:gameId/select-xi',
      name: 'team-select',
      component: () => import('@/views/TeamSelectionView.vue'),
    },
    {
      path: '/game/:gameId/scoring',
      name: 'GameScoringView',
      component: () => import('@/views/GameScoringView.vue'),
      props: true,
    },

    // --- Viewer routes ---
    {
      path: '/view/:gameId',
      name: 'viewer-scoreboard',
      component: () => import('@/views/ViewerScoreboardView.vue'),
      props: route => ({ gameId: String(route.params.gameId) }),
    },
    {
      path: '/embed/:gameId',
      name: 'embed-scoreboard',
      component: () => import('@/views/EmbedScoreboardView.vue'),
      // pass query params (theme/title/logo...) through as props too
      props: route => ({ gameId: String(route.params.gameId), ...route.query }),
    },

    // Catch-all → setup
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

// ---------------------------------------------------------------------------
// Legacy hash-link fallback when running in HISTORY mode
// If someone visits a URL like "/#/embed/<id>?theme=dark" (older share links),
// transparently redirect to the proper route so they don't land on the Setup page.
// ---------------------------------------------------------------------------
if (ROUTER_MODE !== 'hash') {
  router.beforeEach((to, _from, next) => {
    // Only intervene on the very first navigation to "/" when a hash is present
    if ((to.fullPath === '/' || to.name === 'setup') && typeof window !== 'undefined') {
      const raw = window.location.hash || '' // e.g. "#/embed/abc?theme=dark"
      if (raw.startsWith('#/')) {
        const hashPath = raw.slice(1) // "/embed/abc?theme=dark"
        // Extract path and query from the hash
        const [pathOnly, queryString = ''] = hashPath.split('?')
        const params = Object.fromEntries(new URLSearchParams(queryString))

        // Match legacy patterns and redirect
        const embedMatch = pathOnly.match(/^\/embed\/([^/?#]+)/)
        const viewMatch = pathOnly.match(/^\/view\/([^/?#]+)/)
        if (embedMatch) {
          return next({ name: 'embed-scoreboard', params: { gameId: embedMatch[1] }, query: params })
        }
        if (viewMatch) {
          return next({ name: 'viewer-scoreboard', params: { gameId: viewMatch[1] }, query: params })
        }
      }
    }
    next()
  })
}

export default router

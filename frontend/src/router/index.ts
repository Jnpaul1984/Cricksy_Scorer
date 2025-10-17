import { createRouter, createWebHistory, createWebHashHistory } from 'vue-router'

// Choose routing strategy at build/deploy time
// - history (default): clean URLs like /game/123/scoring (needs server fallback to index.html)
// - hash: URLs like /#/game/123/scoring (works on any static host)
const ROUTER_MODE = (import.meta as any).env?.VITE_ROUTER_MODE || 'history'
const history = ROUTER_MODE === 'hash'
  ? createWebHashHistory(import.meta.env.BASE_URL)
  : createWebHistory(import.meta.env.BASE_URL)

// Check if public landing page is enabled
const PUBLIC_LANDING = (import.meta as any).env?.VITE_PUBLIC_LANDING === 'true'

const router = createRouter({
  history,
  routes: [
    {
      path: '/',
      name: 'setup',
      component: () => PUBLIC_LANDING
        ? import('@/views/LandingView.vue')
        : import('@/views/MatchSetupView.vue'),
    },
    {
      path: '/analytics',
      name: 'AnalyticsView',
      component: () => import('@/views/AnalyticsView.vue'),
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

// ---------------------------------------------------------------------------
// Route Guards: Resume last match, validate game existence
// ---------------------------------------------------------------------------
router.beforeEach(async (to, from, next) => {
  // 1. Resume last match: redirect from "/" to last game if conditions are met
  if (!PUBLIC_LANDING && (to.name === 'setup' || to.fullPath === '/')) {
    const forceNew = to.query.new === '1'
    
    if (!forceNew && typeof window !== 'undefined') {
      try {
        const lastGameId = localStorage.getItem('lastGameId')
        if (lastGameId && lastGameId.trim()) {
          // Redirect to the scoring view for the last game
          return next({ 
            name: 'GameScoringView', 
            params: { gameId: lastGameId.trim() } 
          })
        }
      } catch (err) {
        console.warn('Failed to read lastGameId from localStorage:', err)
      }
    }
  }

  // 2. Validate game existence for scoring and team-select routes
  if (to.name === 'GameScoringView' || to.name === 'team-select') {
    const gameId = to.params.gameId as string
    
    if (gameId && typeof window !== 'undefined') {
      try {
        // Check if game data exists using a simple localStorage convention
        // The actual game state is managed by Pinia, but we can check for XI data
        // as a proxy for game existence, or we could try to load it
        const xiKey = `cricksy.xi.${gameId}`
        const xiExists = localStorage.getItem(xiKey) !== null
        
        // Alternatively, we could check if the game can be loaded from the API
        // For now, we'll allow navigation and let the view handle loading errors
        // If you want stricter validation, you'd need to:
        // 1. Import the game store
        // 2. Try to load the game
        // 3. Redirect on failure
        
        // For this implementation, we'll be lenient and let views handle it
        // but clear lastGameId if it matches an invalid game
        if (!xiExists) {
          const lastGameId = localStorage.getItem('lastGameId')
          if (lastGameId === gameId) {
            localStorage.removeItem('lastGameId')
          }
        }
      } catch (err) {
        console.warn('Failed to validate game existence:', err)
      }
    }
  }

  next()
})

export default router

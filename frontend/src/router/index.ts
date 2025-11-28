import { createRouter, createWebHistory, createWebHashHistory } from 'vue-router'

import { getStoredToken } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'

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
      redirect: '/login',
    },
    {
      path: '/setup',
      name: 'setup',
      component: () => import('@/views/MatchSetupView.vue'),
    },
    {
      path: '/analytics',
      name: 'AnalyticsView',
      component: () => import('@/views/AnalyticsView.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
    },
    {
      path: '/player/:playerId',
      name: 'PlayerProfile',
      component: () => import('@/views/PlayerProfileView.vue'),
      props: true,
    },
    {
      // Legacy route - kept for backwards compatibility
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

    // --- Tournament routes ---
    {
      path: '/tournaments',
      name: 'tournaments',
      component: () => import('@/views/TournamentDashboardView.vue'),
    },
    {
      path: '/tournaments/:tournamentId',
      name: 'tournament-detail',
      component: () => import('@/views/TournamentDetailView.vue'),
    },

    // Catch-all → setup
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

// ---------------------------------------------------------------------------
// Legacy hash-link fallback when running in HISTORY mode + RBAC protections
// ---------------------------------------------------------------------------
router.beforeEach(async (to, _from, next) => {
  if (ROUTER_MODE !== 'hash') {
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
  }

  const auth = useAuthStore()

  if (!auth.token) {
    const storedToken = getStoredToken()
    if (storedToken) {
      auth.$patch({ token: storedToken })
    }
  }

  if (!auth.user && auth.token) {
    await auth.loadUser()
  }

  // --- General auth guard -------------------------------------------------
  // Public: /login and viewer/embed routes
  const publicPaths = ['/login']
  const publicNames = ['viewer-scoreboard', 'embed-scoreboard']

  const isPublic = publicPaths.includes(to.path) || (to.name != null && publicNames.includes(String(to.name)))

  // If not public and not logged in -> redirect to login with return path
  if (!isPublic && !auth.isLoggedIn) {
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }

  // If logged in and trying to reach login, send to setup
  if (to.path === '/login' && auth.isLoggedIn) {
    return next('/setup')
  }

  const orgProtected = ['/tournaments', '/analytics']
  const isOrgProtected = orgProtected.some(prefix => to.path.startsWith(prefix))

  if (isOrgProtected) {
    if (!auth.isLoggedIn) {
      return next({ path: '/login', query: { redirect: to.fullPath } })
    }
    if (!auth.isOrg && !auth.isSuper) {
      return next('/')
    }
  }

  return next()
})

export default router

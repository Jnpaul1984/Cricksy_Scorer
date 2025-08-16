import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'setup',
      component: () => import('@/views/MatchSetupView.vue'),
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
    // --- New: Viewer routes ---
    {
      path: '/view/:gameId',
      name: 'viewer-scoreboard',
      component: () => import('@/views/ViewerScoreboardView.vue'),
      props: true,
    },
    {
      path: '/embed/:gameId',
      name: 'embed-scoreboard',
      component: () => import('@/views/EmbedScoreboardView.vue'),
      // pass query params (theme/title/logo) through as props too
      props: route => ({ gameId: route.params.gameId, ...route.query }),
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router

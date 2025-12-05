/**
 * Main Application Entry Point for Cricksy Scorer
 */

import { createApp } from 'vue'

import App from './App.vue'
import router from './router'

import { API_BASE, setUnauthorizedHandler } from '@/services/api';
import pinia from '@/stores'
import { useAuthStore } from '@/stores/authStore';

/**
 * Global CSS Import Order (do not change):
 * 1. Pico CSS — base framework styles
 * 2. designSystem.css — single source of truth for all CSS tokens
 * 3. main.css — global tweaks that CONSUME tokens (no definitions)
 */
import '@picocss/pico/css/pico.min.css'
import './assets/designSystem.css'
import './assets/main.css'

// Mount target with a guard so we never double-mount
const mountEl = document.getElementById('app') as (HTMLElement & { __vue_app__?: any })

if (!mountEl.__vue_app__) {
  const app = createApp(App)

  // Plugins
  app.use(pinia)
  app.use(router)

  const authStore = useAuthStore(pinia)
  setUnauthorizedHandler(() => {
    authStore.logout()
    if (router.currentRoute.value.path !== '/login') {
      router.push('/login')
    }
  })

  // Global error handler
  app.config.errorHandler = (error, instance, info) => {
    console.error('Global error:', error)
    console.error('Component instance:', instance)
    console.error('Error info:', info)
  }

  // Dev warnings
  if (import.meta.env.DEV) {
    app.config.warnHandler = (msg, instance, trace) => {
      console.warn('Vue warning:', msg)
      console.warn('Component trace:', trace)
    }
  }

  // Mount once
  const vm = app.mount('#app')
  mountEl.__vue_app__ = vm

  // Expose app for Cypress E2E tests
  if (typeof window !== 'undefined') {
    ;(window as any).app = app
  }

  // Logs
  console.log('🔧 Vue app mounted to #app element')
  console.log('📱 App element:', document.getElementById('app'))

  if (import.meta.env.DEV) {
    console.log('🏏 Cricksy Scorer application initialized successfully')
    console.log('Environment:', import.meta.env.MODE)
    console.log('API Base URL:', API_BASE || '(not set)')
  }
  if (import.meta.env.DEV) {
    ;(window as any).loadMatch = (match: any) => {
      import('@/stores/gameStore')
        .then((mod) => {
          const store = (mod as any).useGameStore()
          store.currentGame = {
            id: 'e2e',
            team_a: { name: match?.teams?.[0] ?? 'Team A', players: [] },
            team_b: { name: match?.teams?.[1] ?? 'Team B', players: [] },
            status: 'completed',
            current_inning: 2,
            result: { result_text: match?.result?.summary ?? '' },
          } as any
        })
        .catch((e) => console.warn('loadMatch failed:', e))
    }
  }
} else {
  console.warn('App already mounted — skipping duplicate mount')
}

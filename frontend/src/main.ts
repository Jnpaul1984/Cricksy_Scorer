/**
 * Main Application Entry Point for Cricksy Scorer
 */

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import pinia from '@/stores'

// Global styles first (safe to keep here)
import '@picocss/pico/css/pico.min.css'
import './assets/main.css'

// Mount target with a guard so we never double-mount
const mountEl = document.getElementById('app') as (HTMLElement & { __vue_app__?: any })

if (!mountEl.__vue_app__) {
  const app = createApp(App)

  // Plugins
  app.use(pinia)
  app.use(router)

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

  // Logs
  console.log('🔧 Vue app mounted to #app element')
  console.log('📱 App element:', document.getElementById('app'))

  if (import.meta.env.DEV) {
    console.log('🏏 Cricksy Scorer application initialized successfully')
    console.log('Environment:', import.meta.env.MODE)
    console.log('API Base URL:', import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000')
  }
} else {
  console.warn('App already mounted — skipping duplicate mount')
}

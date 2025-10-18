import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)), // enables "@/..." imports
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['tests/**/*.{test,spec}.{ts,tsx,js,jsx}'],
  },
  server: {
    // helps avoid duplicate reloads on some Windows setups
    watch: {
      awaitWriteFinish: {
        stabilityThreshold: 300,
        pollInterval: 100,
      },
    },
  },
})

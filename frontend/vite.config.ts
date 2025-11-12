import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import viteImagemin from 'vite-plugin-imagemin'
import { defineConfig } from 'vitest/config'

const imageOptimizationPlugin = viteImagemin({
  gifsicle: { optimizationLevel: 3 },
  optipng: { optimizationLevel: 5 },
  mozjpeg: { quality: 72 },
  pngquant: { quality: [0.65, 0.8], speed: 3 },
  svgo: { plugins: [{ name: 'removeViewBox', active: false }] },
  webp: { quality: 72 },
  avif: { quality: 50 },
} as Parameters<typeof viteImagemin>[0])

export default defineConfig({
  plugins: [vue(), imageOptimizationPlugin],
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

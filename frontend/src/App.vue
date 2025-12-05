<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

import logoAvif1024 from '@/assets/optimized/logo-w1024.avif'
import logoWebp1024 from '@/assets/optimized/logo-w1024.webp'
import logoAvif1440 from '@/assets/optimized/logo-w1440.avif'
import logoWebp1440 from '@/assets/optimized/logo-w1440.webp'
import logoAvif480 from '@/assets/optimized/logo-w480.avif'
import logoWebp480 from '@/assets/optimized/logo-w480.webp'
import logoAvif768 from '@/assets/optimized/logo-w768.avif'
import logoWebp768 from '@/assets/optimized/logo-w768.webp'
import { useAuthStore } from '@/stores/authStore'

const isDev = computed(() => import.meta.env.DEV)
const auth = useAuthStore()
const showCoachesLink = computed(() => auth.isLoggedIn || isDev.value)

onMounted(() => {
  // hide the tiny fallback text from index.html once Vue is mounted
  const el = document.getElementById('app')
  if (el) el.classList.add('loaded')
})
const logoSources = [
  { width: 480, avif: logoAvif480, webp: logoWebp480 },
  { width: 768, avif: logoAvif768, webp: logoWebp768 },
  { width: 1024, avif: logoAvif1024, webp: logoWebp1024 },
  { width: 1440, avif: logoAvif1440, webp: logoWebp1440 },
] as const

const logoAvifSrcset = logoSources.map((src) => `${src.avif} ${src.width}w`).join(', ')
const logoWebpSrcset = logoSources.map((src) => `${src.webp} ${src.width}w`).join(', ')
const logoFallbackSrc = logoSources.find((src) => src.width === 768)?.webp ?? logoSources[0].webp
const logoSizes = '32px'
</script>

<template>
  <div class="app">
    <header class="app-header">
      <RouterLink to="/" class="brand">
        <picture class="brand-logo">
          <source :srcset="logoAvifSrcset" :sizes="logoSizes" type="image/avif" />
          <source :srcset="logoWebpSrcset" :sizes="logoSizes" type="image/webp" />
          <img
            :src="logoFallbackSrc"
            :sizes="logoSizes"
            alt="Cricksy Mascot"
            loading="eager"
            decoding="async"
            width="32"
            height="32"
          />
        </picture>
        <span>Cricksy Scorer</span>
      </RouterLink>

      <nav class="nav">
        <RouterLink to="/">Setup</RouterLink>
        <RouterLink v-if="showCoachesLink" :to="{ name: 'CoachesDashboard' }">Coaches</RouterLink>
        <RouterLink v-if="showCoachesLink" :to="{ name: 'AnalystWorkspace' }">Analyst Workspace</RouterLink>
        <RouterLink v-if="isDev" to="/design-system" class="nav-dev">Design System</RouterLink>
      </nav>
    </header>

    <main class="app-main">
      <RouterView />
    </main>

    <footer class="app-footer">
      © {{ new Date().getFullYear() }} Cricksy Scorer. All rights reserved.
    </footer>
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
  display: grid;
  grid-template-rows: auto 1fr auto;
  background: linear-gradient(135deg, #0f1115, #151926 35%, #1c2340);
}

/* Header */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: rgba(16, 22, 36, 0.85);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(8px);
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  text-decoration: none;
  color: #fff;
  font-weight: 700;
  letter-spacing: 0.2px;
}
.brand-logo,
.brand-logo img {
  width: 32px;
  height: 32px;
  display: inline-flex;
}
.brand-logo img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.nav {
  display: inline-flex;
  gap: 0.75rem;
}
.nav a {
  color: #c9d1e6;
  text-decoration: none;
  font-weight: 500;
  opacity: 0.9;
}
.nav a.router-link-active {
  color: #fff;
}
.nav-dev {
  opacity: 0.6;
  font-size: 0.85em;
}

/* Main */
.app-main {
  padding: 0;
}

/* Footer */
.app-footer {
  padding: 0.85rem 1rem;
  color: #aab2c0;
  text-align: center;
  background: rgba(16, 22, 36, 0.85);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
</style>

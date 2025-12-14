<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

import logoAvif1024 from '@/assets/optimized/logo-w1024.avif'
import logoWebp1024 from '@/assets/optimized/logo-w1024.webp'
import logoAvif1440 from '@/assets/optimized/logo-w1440.avif'
import logoWebp1440 from '@/assets/optimized/logo-w1440.webp'
import logoAvif480 from '@/assets/optimized/logo-w480.avif'
import logoWebp480 from '@/assets/optimized/logo-w480.webp'
import logoAvif768 from '@/assets/optimized/logo-w768.avif'
import logoWebp768 from '@/assets/optimized/logo-w768.webp'
import BetaChecklistModal from '@/components/BetaChecklistModal.vue'
import FeedbackModal from '@/components/FeedbackModal.vue'
import QuotaWarningBanner from '@/components/QuotaWarningBanner.vue'
import { useAuthStore } from '@/stores/authStore'

const isDev = computed(() => import.meta.env.DEV)
const showFeedbackModal = ref(false)
const showBetaChecklist = ref(false)
const auth = useAuthStore()
const showBetaGuide = computed(() => Boolean(auth.user && auth.user.beta_tag))

function handleFeedbackSubmit(payload: { text: string; email?: string }) {
  // TODO: Send feedback to backend API
  console.log('Feedback submitted:', payload)
  // For now, just log it - will integrate with backend later
}

// Keyboard shortcut: "F" to open feedback modal
function handleKeydown(e: KeyboardEvent) {
  // Don't trigger if user is typing in an input/textarea
  const target = e.target as HTMLElement
  if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
    return
  }
  // "F" key opens feedback modal
  if (e.key.toLowerCase() === 'f' && !e.ctrlKey && !e.metaKey && !e.altKey) {
    e.preventDefault()
    showFeedbackModal.value = true
  }
}

onMounted(() => {
  // hide the tiny fallback text from index.html once Vue is mounted
  const el = document.getElementById('app')
  if (el) el.classList.add('loaded')

  // Add keyboard listener
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
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

// Auth store for role-based navigation
const showCoachNav = computed(() => auth.isCoach || auth.isOrg || auth.isSuper)
const showAnalystNav = computed(() => auth.isAnalyst || auth.isOrg || auth.isSuper)
const showAdminNav = computed(() => auth.isSuper)
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
        <RouterLink to="/landing">Home</RouterLink>
        <RouterLink to="/setup">Setup</RouterLink>
        <RouterLink v-if="showCoachNav" to="/coach/dashboard">Coach</RouterLink>
        <RouterLink v-if="showAnalystNav" to="/analyst/workspace">Analyst</RouterLink>
        <RouterLink v-if="showAdminNav" to="/admin/beta-users" class="nav-admin">Admin</RouterLink>
        <RouterLink to="/pricing">Pricing</RouterLink>
        <RouterLink v-if="isDev" to="/design-system" class="nav-dev">Design System</RouterLink>
        <button
          v-if="showBetaGuide"
          class="beta-guide-btn"
          style="font-size: 0.95em; margin-right: 0.5em; color: #fbbf24; background: none; border: none; cursor: pointer;"
          title="Open Beta Checklist"
          @click="showBetaChecklist = true"
        >
          📝 Beta Guide
        </button>
        <button class="feedback-btn" title="Send Feedback (F)" @click="showFeedbackModal = true">
          💬 Feedback
        </button>
        <div v-if="auth.isLoggedIn" class="user-menu">
          <RouterLink to="/profile" class="user-menu-item" title="Profile">👤 Profile</RouterLink>
          <RouterLink to="/settings" class="user-menu-item" title="Settings">⚙️ Settings</RouterLink>
          <button class="user-menu-item logout-btn" @click="auth.logout(); $router.push('/login')" title="Log out">
            🚪 Logout
          </button>
        </div>
      </nav>
    </header>

    <!-- AI Quota Warning Banner -->
    <QuotaWarningBanner />

    <main class="app-main">
      <RouterView />
    </main>

    <footer class="app-footer">
      © {{ new Date().getFullYear() }} Cricksy Scorer. All rights reserved.
    </footer>

    <!-- Feedback Modal -->
    <FeedbackModal
      v-model:visible="showFeedbackModal"
      @submitted="handleFeedbackSubmit"
    />
    <BetaChecklistModal v-model:visible="showBetaChecklist" />
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
  align-items: center;
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
.nav-admin {
  color: #f59e0b !important;
  font-weight: 600;
}
.nav-admin:hover {
  color: #fbbf24 !important;
}

/* User Menu */
.user-menu {
  display: inline-flex;
  gap: 0.5rem;
  align-items: center;
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  padding-left: 0.75rem;
}

.user-menu-item {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.5rem;
  color: #c9d1e6;
  text-decoration: none;
  font-weight: 500;
  font-size: 0.85rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  transition: all 0.2s;
  cursor: pointer;
}

.user-menu-item:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.logout-btn {
  margin-left: 0.25rem;
}

.logout-btn:hover {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.3);
  color: #fca5a5;
}

/* Feedback button */
.feedback-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.75rem;
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  color: #93c5fd;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.feedback-btn:hover {
  background: rgba(59, 130, 246, 0.25);
  border-color: rgba(59, 130, 246, 0.5);
  color: #bfdbfe;
}

/* Beta Guide button */
.beta-guide-btn {
  padding: 0 0.5em;
  background: none;
  border: none;
  color: #fbbf24;
  cursor: pointer;
  font-weight: 500;
  text-decoration: underline;
  margin-right: 0.5em;
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

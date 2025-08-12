<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import logoUrl from '@/assets/logo.png' // make sure the file exists: src/assets/logo.png

onMounted(() => {
  // hide the tiny fallback text from index.html once Vue is mounted
  const el = document.getElementById('app')
  if (el) el.classList.add('loaded')
})
</script>

<template>
  <div class="app">
    <header class="app-header">
      <RouterLink to="/" class="brand">
        <img :src="logoUrl" alt="Cricksy Mascot" />
        <span>Cricksy Scorer</span>
      </RouterLink>

      <nav class="nav">
        <RouterLink to="/">Setup</RouterLink>
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
.brand img {
  width: 32px;
  height: 32px;
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

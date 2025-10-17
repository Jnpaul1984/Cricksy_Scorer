<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// Check if there's a last game ID stored
const lastGameId = computed<string | null>(() => {
  try {
    return localStorage.getItem('lastGameId')
  } catch {
    return null
  }
})

const appName = (import.meta as any).env?.VITE_APP_NAME || 'Cricksy Scorer'

function startNewMatch() {
  router.push({ name: 'setup', query: { new: '1' } })
}

function resumeLastMatch() {
  if (lastGameId.value) {
    router.push({ name: 'GameScoringView', params: { gameId: lastGameId.value } })
  }
}
</script>

<template>
  <div class="landing">
    <div class="container">
      <header class="header">
        <h1 class="title">{{ appName }}</h1>
        <p class="subtitle">Professional Cricket Scoring Application</p>
      </header>

      <main class="actions">
        <button class="btn btn-primary" @click="startNewMatch">
          Start New Match
        </button>
        
        <button 
          v-if="lastGameId" 
          class="btn btn-secondary" 
          @click="resumeLastMatch"
        >
          Resume Last Match
        </button>
      </main>

      <footer class="footer">
        <p>
          <a href="/view/" class="link">View a match</a> · 
          <a href="https://github.com/Jnpaul1984/Cricksy_Scorer" target="_blank" rel="noopener" class="link">GitHub</a>
        </p>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.landing {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: linear-gradient(135deg, #0f1115 0%, #151926 35%, #1c2340 100%);
  color: #fff;
}

.container {
  max-width: 600px;
  width: 100%;
  text-align: center;
  padding: 2rem;
}

.header {
  margin-bottom: 3rem;
}

.title {
  font-size: 3rem;
  font-weight: 900;
  margin: 0 0 0.5rem;
  background: linear-gradient(135deg, #22d3ee 0%, #3b82f6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.subtitle {
  font-size: 1.25rem;
  color: #9ca3af;
  margin: 0;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 3rem;
}

.btn {
  appearance: none;
  border: none;
  border-radius: 12px;
  padding: 1rem 2rem;
  font-weight: 700;
  font-size: 1.125rem;
  cursor: pointer;
  transition: all 0.2s ease;
  width: 100%;
}

.btn-primary {
  background: linear-gradient(135deg, #22d3ee 0%, #3b82f6 100%);
  color: #0b0f1a;
  box-shadow: 0 4px 20px rgba(34, 211, 238, 0.3);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 25px rgba(34, 211, 238, 0.4);
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
}

.footer {
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  color: #6b7280;
  font-size: 0.875rem;
}

.link {
  color: #22d3ee;
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

@media (max-width: 640px) {
  .title {
    font-size: 2rem;
  }
  
  .subtitle {
    font-size: 1rem;
  }
  
  .btn {
    font-size: 1rem;
  }
}
</style>

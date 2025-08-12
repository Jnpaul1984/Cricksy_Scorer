<template>
  <div class="home-view">
    <div class="container">
      <!-- Hero Section -->
      <section class="hero-section">
        <div class="hero-content">
          <h1 class="hero-title">🏏 Cricksy Scorer</h1>
          <p class="hero-subtitle">
            Professional cricket scoring for 25-over school matches
          </p>
          
          <!-- Game Creation Form -->
          <div class="game-form" v-if="!gameStore.isLoading">
            <div class="form-row">
              <input 
                v-model="gameForm.team_a_name" 
                placeholder="Team A Name (e.g., Lions)"
                class="team-input"
              />
              <input 
                v-model="gameForm.team_b_name" 
                placeholder="Team B Name (e.g., Tigers)"
                class="team-input"
              />
            </div>
            
            <div class="toss-section">
              <label class="toss-label">Toss Winner:</label>
              <select v-model="gameForm.toss_winner_team" class="toss-select">
                <option value="">Select toss winner</option>
                <option :value="gameForm.team_a_name" v-if="gameForm.team_a_name">
                  {{ gameForm.team_a_name }}
                </option>
                <option :value="gameForm.team_b_name" v-if="gameForm.team_b_name">
                  {{ gameForm.team_b_name }}
                </option>
              </select>
              
              <select v-model="gameForm.decision" class="decision-select">
                <option value="">Choose to...</option>
                <option value="bat">Bat First</option>
                <option value="bowl">Bowl First</option>
              </select>
            </div>
            
            <button 
              @click="createNewGame" 
              :disabled="!canCreateGame"
              class="cta-button"
              :class="{ 'disabled': !canCreateGame }"
            >
              🏏 Create New Match
            </button>
          </div>
          
          <!-- Loading State -->
          <div v-if="gameStore.isLoading" class="loading-state">
            <div class="spinner"></div>
            <p>Creating your cricket match...</p>
          </div>
          
          <!-- Error State -->
          <div v-if="gameStore.error" class="error-state">
            <p>❌ {{ gameStore.error }}</p>
            <button @click="gameStore.clearError" class="retry-button">Try Again</button>
          </div>
        </div>
      </section>

      <!-- Features Section -->
      <section class="features-section">
        <h2 class="section-title">Features</h2>
        <div class="features-grid">
          <div class="feature-card">
            <div class="feature-icon">⚡</div>
            <h3>Real-time Scoring</h3>
            <p>Score deliveries instantly with intuitive controls</p>
          </div>
          
          <div class="feature-card">
            <div class="feature-icon">📊</div>
            <h3>Detailed Statistics</h3>
            <p>Complete batting and bowling scorecards</p>
          </div>
          
          <div class="feature-card">
            <div class="feature-icon">🎯</div>
            <h3>School-Focused</h3>
            <p>Designed specifically for 25-over school cricket</p>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '@/stores/gameStore'

const router = useRouter()
const gameStore = useGameStore()

// Form data
const gameForm = ref({
  team_a_name: '',
  team_b_name: '',
  players_a: ['Player 1', 'Player 2', 'Player 3', 'Player 4', 'Player 5', 'Player 6'],
  players_b: ['Player 1', 'Player 2', 'Player 3', 'Player 4', 'Player 5', 'Player 6'],
  toss_winner_team: '',
  decision: ''
})

// Computed properties
const canCreateGame = computed(() => {
  return gameForm.value.team_a_name.trim() !== '' &&
         gameForm.value.team_b_name.trim() !== '' &&
         gameForm.value.toss_winner_team !== '' &&
         gameForm.value.decision !== '' &&
         !gameStore.isLoading
})

// Create new game
const createNewGame = async () => {
  if (!canCreateGame.value) return
  
  try {
    console.log('🎮 Creating new game with data:', gameForm.value)
    
    await gameStore.createNewGame(gameForm.value)
    
    if (gameStore.currentGame) {
      console.log('✅ Game created successfully:', gameStore.currentGame.game_id)
      router.push(`/game/${gameStore.currentGame.game_id}`)
    }
  } catch (error) {
    console.error('❌ Failed to create game:', error)
  }
}

console.log('🏠 HomeView component loaded')
</script>

<style scoped>
.home-view {
  min-height: 100vh;
  padding: 2rem 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
}

.hero-section {
  text-align: center;
  margin-bottom: 4rem;
}

.hero-content {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 3rem 2rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  max-width: 600px;
  margin: 0 auto;
}

.hero-title {
  font-size: 3rem;
  font-weight: bold;
  color: white;
  margin-bottom: 1rem;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.hero-subtitle {
  font-size: 1.2rem;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 2rem;
  line-height: 1.6;
}

.game-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.form-row {
  display: flex;
  gap: 1rem;
}

.team-input {
  flex: 1;
  padding: 0.75rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  font-size: 1rem;
  backdrop-filter: blur(5px);
}

.team-input::placeholder {
  color: rgba(255, 255, 255, 0.7);
}

.team-input:focus {
  outline: none;
  border-color: rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.2);
}

.toss-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.toss-label {
  color: rgba(255, 255, 255, 0.9);
  font-weight: 500;
  text-align: left;
}

.toss-select,
.decision-select {
  padding: 0.75rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  font-size: 1rem;
  backdrop-filter: blur(5px);
}

.toss-select option,
.decision-select option {
  background: #2c3e50;
  color: white;
}

.cta-button {
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
  color: white;
  border: none;
  padding: 1rem 2rem;
  border-radius: 50px;
  font-weight: bold;
  font-size: 1.1rem;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
}

.cta-button:hover:not(.disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
}

.cta-button.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  color: white;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top: 3px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-state {
  color: #ff6b6b;
  text-align: center;
}

.retry-button {
  background: transparent;
  border: 2px solid #ff6b6b;
  color: #ff6b6b;
  padding: 0.5rem 1rem;
  border-radius: 25px;
  cursor: pointer;
  margin-top: 1rem;
}

.features-section {
  margin-top: 4rem;
}

.section-title {
  font-size: 2rem;
  font-weight: bold;
  color: white;
  text-align: center;
  margin-bottom: 2rem;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
}

.feature-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 2rem;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: transform 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-5px);
}

.feature-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.feature-card h3 {
  font-size: 1.3rem;
  font-weight: bold;
  color: white;
  margin-bottom: 1rem;
}

.feature-card p {
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.6;
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 2rem;
  }
  
  .hero-content {
    padding: 2rem 1rem;
  }
  
  .form-row {
    flex-direction: column;
  }
  
  .features-grid {
    grid-template-columns: 1fr;
  }
  
  .container {
    padding: 0 1rem;
  }
}
</style>

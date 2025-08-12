<template>
  <div class="current-players">
    <h3 class="section-title">Current Players</h3>
    
    <div class="players-grid">
      <!-- Striker -->
      <div class="player-card striker">
        <div class="player-role">
          <span class="role-icon">🏏</span>
          <span class="role-text">Striker</span>
        </div>
        <div class="player-info">
          <div class="player-name">
            {{ strikerName || 'Not selected' }}
          </div>
          <div v-if="strikerStats" class="player-stats">
            {{ strikerStats.runs }} runs ({{ strikerStats.balls_faced }} balls)
          </div>
        </div>
      </div>
      
      <!-- Non-Striker -->
      <div class="player-card non-striker">
        <div class="player-role">
          <span class="role-icon">🏃</span>
          <span class="role-text">Non-Striker</span>
        </div>
        <div class="player-info">
          <div class="player-name">
            {{ nonStrikerName || 'Not selected' }}
          </div>
          <div v-if="nonStrikerStats" class="player-stats">
            {{ nonStrikerStats.runs }} runs ({{ nonStrikerStats.balls_faced }} balls)
          </div>
        </div>
      </div>
      
      <!-- Bowler -->
      <div class="player-card bowler">
        <div class="player-role">
          <span class="role-icon">⚾</span>
          <span class="role-text">Bowler</span>
        </div>
        <div class="player-info">
          <div class="player-name">
            {{ bowlerName || 'Not selected' }}
          </div>
          <div v-if="bowlerStats" class="player-stats">
            {{ bowlerStats.overs_bowled }} overs, {{ bowlerStats.runs_conceded }} runs
          </div>
        </div>
      </div>
    </div>
    
    <!-- Swap Batsmen Button -->
    <div class="actions" v-if="canSwapBatsmen">
      <button 
        @click="handleSwapBatsmen"
        class="swap-button"
        :disabled="loading"
        type="button"
      >
        🔄 Swap Batsmen
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useGameStore } from '@/stores/gameStore';
import type { BattingScorecardEntry, BowlingScorecardEntry } from '@/types/api';

const gameStore = useGameStore();

// Computed properties
const strikerName = computed(() => 
  gameStore.currentStriker?.name || null
);

const nonStrikerName = computed(() => 
  gameStore.currentNonStriker?.name || null
);

const bowlerName = computed(() => 
  gameStore.selectedBowler?.name || null
);

const strikerStats = computed((): BattingScorecardEntry | null => {
  if (!gameStore.currentGame?.current_striker_id) return null;
  return gameStore.currentGame.batting_scorecard[gameStore.currentGame.current_striker_id] || null;
});

const nonStrikerStats = computed((): BattingScorecardEntry | null => {
  if (!gameStore.currentGame?.current_non_striker_id) return null;
  return gameStore.currentGame.batting_scorecard[gameStore.currentGame.current_non_striker_id] || null;
});

const bowlerStats = computed((): BowlingScorecardEntry | null => {
  if (!gameStore.uiState.selectedBowlerId) return null;
  return gameStore.currentGame?.bowling_scorecard[gameStore.uiState.selectedBowlerId] || null;
});

const canSwapBatsmen = computed(() => 
  strikerName.value && nonStrikerName.value && gameStore.isGameActive
);

const loading = computed(() => 
  gameStore.uiState.loading
);

// Methods
const handleSwapBatsmen = () => {
  gameStore.swapBatsmen();
};
</script>

<style scoped>
.current-players {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.section-title {
  font-size: 1.4rem;
  font-weight: bold;
  color: #2c3e50;
  margin: 0 0 1.5rem 0;
  text-align: center;
}

.players-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.player-card {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 1rem;
  border-left: 4px solid #ddd;
  transition: all 0.3s ease;
}

.player-card.striker {
  border-left-color: #2ecc71;
  background: linear-gradient(135deg, #f8fff9 0%, #f0fff4 100%);
}

.player-card.non-striker {
  border-left-color: #3498db;
  background: linear-gradient(135deg, #f8fcff 0%, #f0f8ff 100%);
}

.player-card.bowler {
  border-left-color: #e74c3c;
  background: linear-gradient(135deg, #fff8f8 0%, #fff0f0 100%);
}

.player-role {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.role-icon {
  font-size: 1.2rem;
}

.role-text {
  font-weight: 600;
  color: #2c3e50;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.player-info {
  min-height: 3rem;
}

.player-name {
  font-size: 1.1rem;
  font-weight: bold;
  color: #2c3e50;
  margin-bottom: 0.25rem;
}

.player-stats {
  font-size: 0.9rem;
  color: #6c757d;
  font-style: italic;
}

.actions {
  text-align: center;
  padding-top: 1rem;
  border-top: 1px solid #e9ecef;
}

.swap-button {
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(52, 152, 219, 0.3);
}

.swap-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #2980b9 0%, #21618c 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(52, 152, 219, 0.4);
}

.swap-button:active {
  transform: translateY(0);
}

.swap-button:disabled {
  background: #95a5a6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

@media (max-width: 768px) {
  .current-players {
    padding: 1rem;
  }
  
  .players-grid {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }
  
  .player-card {
    padding: 0.75rem;
  }
  
  .section-title {
    font-size: 1.2rem;
  }
}
</style>


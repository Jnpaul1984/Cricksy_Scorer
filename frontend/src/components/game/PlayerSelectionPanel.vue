<template>
  <div class="player-selection-panel">
    <h3 class="panel-title">Player Selection</h3>
    
    <div class="selection-grid">
      <!-- Striker Selection -->
      <PlayerSelector
        :players="availableBatsmen"
        :selected-player-id="gameStore.uiState.selectedStrikerId"
        label="Striker"
        :required="true"
        :exclude-player-ids="gameStore.uiState.selectedNonStrikerId ? [gameStore.uiState.selectedNonStrikerId] : []"
        :disabled="!gameStore.isGameActive"
        :loading="gameStore.operationLoading.scoreDelivery"
        hint="The batsman currently facing the bowler"
        @update:selected-player-id="gameStore.setSelectedStriker"
        @player-selected="handleStrikerSelected"
      />
      
      <!-- Non-Striker Selection -->
      <PlayerSelector
        :players="availableBatsmen"
        :selected-player-id="gameStore.uiState.selectedNonStrikerId"
        label="Non-Striker"
        :required="true"
        :exclude-player-ids="gameStore.uiState.selectedStrikerId ? [gameStore.uiState.selectedStrikerId] : []"
        :disabled="!gameStore.isGameActive"
        :loading="gameStore.operationLoading.scoreDelivery"
        hint="The batsman at the non-striker's end"
        @update:selected-player-id="gameStore.setSelectedNonStriker"
        @player-selected="handleNonStrikerSelected"
      />
      
      <!-- Bowler Selection -->
      <PlayerSelector
        :players="availableBowlers"
        :selected-player-id="gameStore.uiState.selectedBowlerId"
        label="Bowler"
        :required="true"
        :disabled="!gameStore.isGameActive"
        :loading="gameStore.operationLoading.scoreDelivery"
        hint="The player bowling this over"
        @update:selected-player-id="gameStore.setSelectedBowler"
        @player-selected="handleBowlerSelected"
      />
    </div>
    
    <!-- Validation Messages -->
    <div v-if="validationErrors.length > 0" class="validation-errors">
      <h4 class="errors-title">Please fix the following:</h4>
      <ul class="errors-list">
        <li v-for="error in validationErrors" :key="error" class="error-item">
          {{ error }}
        </li>
      </ul>
    </div>
    
    <!-- Selection Status -->
    <div class="selection-status" :class="statusClass">
      <div class="status-icon">
        {{ statusIcon }}
      </div>
      <div class="status-text">
        {{ statusMessage }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

import PlayerSelector from './PlayerSelector.vue';

import { useGameStore } from '@/stores/gameStore';
import type { Player } from '@/types/api';

const gameStore = useGameStore();

// Computed properties
const availableBatsmen = computed(() => 
  gameStore.availableBatsmen || []
);

const availableBowlers = computed(() => 
  gameStore.availableBowlers || []
);

const validationErrors = computed(() => {
  const errors: string[] = [];
  
  if (!gameStore.uiState.selectedStrikerId) {
    errors.push('Please select a striker');
  }
  
  if (!gameStore.uiState.selectedNonStrikerId) {
    errors.push('Please select a non-striker');
  }
  
  if (!gameStore.uiState.selectedBowlerId) {
    errors.push('Please select a bowler');
  }
  
  if (gameStore.uiState.selectedStrikerId === gameStore.uiState.selectedNonStrikerId) {
    errors.push('Striker and non-striker cannot be the same player');
  }
  
  return errors;
});

const statusClass = computed(() => ({
  'status-ready': gameStore.canScoreDelivery,
  'status-incomplete': !gameStore.canScoreDelivery && validationErrors.value.length > 0,
  'status-disabled': !gameStore.isGameActive,
}));

const statusIcon = computed(() => {
  if (!gameStore.isGameActive) return '⏸️';
  if (gameStore.canScoreDelivery) return '✅';
  return '⚠️';
});

const statusMessage = computed(() => {
  if (!gameStore.isGameActive) {
    return 'Game is not active';
  }
  
  if (gameStore.canScoreDelivery) {
    return 'Ready to score deliveries';
  }
  
  if (validationErrors.value.length > 0) {
    return `${validationErrors.value.length} selection${validationErrors.value.length > 1 ? 's' : ''} required`;
  }
  
  return 'Complete player selection';
});

// Event handlers
const handleStrikerSelected = (player: Player | null) => {
  console.log('Striker selected:', player?.name || 'None');
};

const handleNonStrikerSelected = (player: Player | null) => {
  console.log('Non-striker selected:', player?.name || 'None');
};

const handleBowlerSelected = (player: Player | null) => {
  console.log('Bowler selected:', player?.name || 'None');
};
</script>

<style scoped>
.player-selection-panel {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.panel-title {
  font-size: 1.4rem;
  font-weight: bold;
  color: #2c3e50;
  margin: 0 0 1.5rem 0;
  text-align: center;
}

.selection-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.validation-errors {
  background: #fff5f5;
  border: 1px solid #fed7d7;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.errors-title {
  color: #e53e3e;
  font-size: 1rem;
  font-weight: 600;
  margin: 0 0 0.75rem 0;
}

.errors-list {
  margin: 0;
  padding-left: 1.5rem;
  color: #e53e3e;
}

.error-item {
  margin-bottom: 0.25rem;
  font-size: 0.9rem;
}

.selection-status {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.3s ease;
}

.status-ready {
  background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
  color: #155724;
  border: 1px solid #c3e6cb;
}

.status-incomplete {
  background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
  color: #856404;
  border: 1px solid #ffeaa7;
}

.status-disabled {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  color: #6c757d;
  border: 1px solid #dee2e6;
}

.status-icon {
  font-size: 1.2rem;
}

.status-text {
  font-size: 1rem;
}

@media (max-width: 768px) {
  .player-selection-panel {
    padding: 1rem;
  }
  
  .selection-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
  
  .panel-title {
    font-size: 1.2rem;
  }
  
  .selection-status {
    padding: 0.75rem;
    font-size: 0.9rem;
  }
}
</style>


<template>
  <div class="player-selector">
    <label :for="selectId" class="selector-label">
      {{ label }}
      <span v-if="required" class="required-indicator">*</span>
    </label>
    
    <select
      :id="selectId"
      :value="selectedPlayerId"
      @change="handleSelectionChange"
      :disabled="disabled || loading"
      :class="selectorClass"
      class="player-select"
      :aria-describedby="errorId"
    >
      <option value="">-- Select {{ label }} --</option>
      <option
        v-for="player in availablePlayers"
        :key="player.id"
        :value="player.id"
        :disabled="isPlayerDisabled(player.id)"
      >
        {{ player.name }}
        <span v-if="isPlayerDisabled(player.id)" class="disabled-reason">
          ({{ getDisabledReason(player.id) }})
        </span>
      </option>
    </select>
    
    <div v-if="error" :id="errorId" class="error-message" role="alert">
      {{ error }}
    </div>
    
    <div v-if="hint" class="hint-message">
      {{ hint }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { Player } from '@/types/api';

// Props
interface Props {
  players: Player[];
  selectedPlayerId: string | null;
  label: string;
  disabled?: boolean;
  loading?: boolean;
  required?: boolean;
  excludePlayerIds?: string[];
  error?: string;
  hint?: string;
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  loading: false,
  required: false,
  excludePlayerIds: () => [],
  error: '',
  hint: '',
});

// Emits
interface Emits {
  (e: 'update:selectedPlayerId', playerId: string | null): void;
  (e: 'player-selected', player: Player | null): void;
}

const emit = defineEmits<Emits>();

// Computed
const selectId = computed(() => 
  `player-select-${props.label.toLowerCase().replace(/\s+/g, '-')}`
);

const errorId = computed(() => 
  `${selectId.value}-error`
);

const availablePlayers = computed(() => 
  props.players.filter(player => !props.excludePlayerIds.includes(player.id))
);

const selectorClass = computed(() => ({
  'has-error': !!props.error,
  'is-disabled': props.disabled || props.loading,
  'is-loading': props.loading,
}));

// Methods
const handleSelectionChange = (event: Event) => {
  const target = event.target as HTMLSelectElement;
  const playerId = target.value || null;
  
  emit('update:selectedPlayerId', playerId);
  
  const selectedPlayer = playerId 
    ? props.players.find(p => p.id === playerId) || null
    : null;
  emit('player-selected', selectedPlayer);
};

const isPlayerDisabled = (playerId: string): boolean => {
  return props.excludePlayerIds.includes(playerId);
};

const getDisabledReason = (playerId: string): string => {
  if (props.excludePlayerIds.includes(playerId)) {
    return 'Already selected';
  }
  return '';
};
</script>

<style scoped>
.player-selector {
  margin-bottom: 1.5rem;
}

.selector-label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--color-text-primary, #2c3e50);
  font-size: 1rem;
}

.required-indicator {
  color: #e74c3c;
  margin-left: 0.25rem;
}

.player-select {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 2px solid #ddd;
  border-radius: 8px;
  font-size: 1rem;
  background-color: white;
  transition: all 0.3s ease;
  cursor: pointer;
}

.player-select:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
}

.player-select:hover:not(:disabled) {
  border-color: #bbb;
}

.player-select.has-error {
  border-color: #e74c3c;
}

.player-select.has-error:focus {
  border-color: #e74c3c;
  box-shadow: 0 0 0 3px rgba(231, 76, 60, 0.1);
}

.player-select.is-disabled {
  background-color: #f8f9fa;
  color: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

.player-select.is-loading {
  background-image: url("data:image/svg+xml,%3csvg width='20' height='20' viewBox='0 0 20 20' xmlns='http://www.w3.org/2000/svg'%3e%3cpath d='M10 2v2a6 6 0 0 1 0 12v2a8 8 0 0 0 0-16z' fill='%23666'/%3e%3c/svg%3e");
  background-repeat: no-repeat;
  background-position: right 1rem center;
  background-size: 1rem;
  animation: spin 1s linear infinite;
}

.error-message {
  color: #e74c3c;
  font-size: 0.875rem;
  margin-top: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.error-message::before {
  content: '⚠';
  font-size: 1rem;
}

.hint-message {
  color: #6c757d;
  font-size: 0.875rem;
  margin-top: 0.5rem;
  font-style: italic;
}

.disabled-reason {
  color: #6c757d;
  font-size: 0.875rem;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .player-select {
    padding: 1rem;
    font-size: 1.1rem;
  }
  
  .selector-label {
    font-size: 1.1rem;
  }
}
</style>


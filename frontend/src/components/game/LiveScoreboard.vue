<template>
  <div class="live-scoreboard">
    <div class="scoreboard-header">
      <h2 class="team-name">{{ battingTeamName }}</h2>
      <div v-if="currentInning > 1" class="innings-indicator">
        2nd Innings
      </div>
    </div>

    <div class="score-display">
      <div class="main-score">
        <span class="runs">{{ totalRuns }}</span>
        <span class="separator">/</span>
        <span class="wickets">{{ totalWickets }}</span>
      </div>

      <div class="overs-display">
        <span class="overs-label">Overs:</span>
        <span class="overs-value">{{ oversDisplay }}</span>
      </div>
    </div>

    <!-- Current batters with role badges -->
    <div v-if="strikerName || nonStrikerName" class="batters-display">
      <span v-if="strikerName" class="batter striker">
        {{ strikerName }}<span class="role-badge">{{ roleBadge(strikerId) }}</span>*
      </span>
      <span v-if="strikerName && nonStrikerName" class="separator-dot">·</span>
      <span v-if="nonStrikerName" class="batter">
        {{ nonStrikerName }}<span class="role-badge">{{ roleBadge(nonStrikerId) }}</span>
      </span>
    </div>

    <div v-if="targetRuns" class="target-display">
      <span class="target-label">Target:</span>
      <span class="target-value">{{ targetRuns }}</span>
      <span v-if="runsRequired" class="required-info">
        ({{ runsRequired }} runs needed)
      </span>
    </div>

    <div class="game-status" :class="statusClass">
      {{ gameStatusText }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

import { useRoleBadge } from '@/composables/useRoleBadge';
import { useGameStore } from '@/stores/gameStore';

const gameStore = useGameStore();

// Captain/Keeper badge composable
const currentGame = computed(() => gameStore.currentGame as any);
const teamAName = computed(() => String(currentGame.value?.team_a?.name ?? ''));
// Note: battingTeamName is defined below in "Computed properties" section
const isBattingTeamA = computed(() => String(currentGame.value?.batting_team_name ?? '') === teamAName.value);
const { roleBadge } = useRoleBadge({ currentGame, isBattingTeamA });

// Props (none needed - component reads from store)

// Current striker/non-striker
const strikerId = computed(() => String(currentGame.value?.current_striker_id ?? ''));
const nonStrikerId = computed(() => String(currentGame.value?.current_non_striker_id ?? ''));

const strikerName = computed(() => {
  const id = strikerId.value;
  if (!id || !currentGame.value) return '';
  const players = [
    ...(currentGame.value.team_a?.players || []),
    ...(currentGame.value.team_b?.players || []),
  ];
  return players.find((p: any) => String(p.id) === id)?.name || '';
});

const nonStrikerName = computed(() => {
  const id = nonStrikerId.value;
  if (!id || !currentGame.value) return '';
  const players = [
    ...(currentGame.value.team_a?.players || []),
    ...(currentGame.value.team_b?.players || []),
  ];
  return players.find((p: any) => String(p.id) === id)?.name || '';
});

// Computed properties
const battingTeamName = computed(() =>
  gameStore.currentGame?.batting_team_name || 'Team'
);

const totalRuns = computed(() =>
  gameStore.currentGame?.total_runs || 0
);

const totalWickets = computed(() =>
  gameStore.currentGame?.total_wickets || 0
);

const currentInning = computed(() =>
  gameStore.currentGame?.current_inning || 1
);

const oversDisplay = computed(() => {
  if (!gameStore.currentGame) return '0.0';
  const { overs_completed, balls_this_over } = gameStore.currentGame;
  return `${overs_completed}.${balls_this_over}`;
});

const targetRuns = computed(() =>
  gameStore.currentGame?.target || null
);

const runsRequired = computed(() => {
  if (!targetRuns.value || !gameStore.currentGame) return null;
  const required = targetRuns.value - gameStore.currentGame.total_runs;
  return required > 0 ? required : null;
});

const gameStatusText = computed(() => {
  const status = String(gameStore.currentGame?.status || '').toLowerCase();
  switch (status) {
    case 'in_progress':
      return 'Live';
    case 'innings_break':
      return 'Innings Break';
    case 'completed':
      return gameStore.currentGame?.result || 'Match Completed';
    default:
      return 'Waiting';
  }
});

const statusClass = computed(() => {
  const status = String(gameStore.currentGame?.status || '').toLowerCase();
  return {
    'status-live': status === 'in_progress',
    'status-break': status === 'innings_break',
    'status-completed': status === 'completed',
  };
});
</script>

<style scoped>
.live-scoreboard {
  background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
  color: white;
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  text-align: center;
  margin-bottom: 2rem;
}

.scoreboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.team-name {
  font-size: 1.8rem;
  font-weight: bold;
  margin: 0;
  color: #ecf0f1;
}

.innings-indicator {
  background: #e74c3c;
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: bold;
}

.score-display {
  margin-bottom: 1.5rem;
}

.main-score {
  font-size: 4rem;
  font-weight: bold;
  line-height: 1;
  margin-bottom: 0.5rem;
}

.runs {
  color: #2ecc71;
}

.separator {
  color: #bdc3c7;
  margin: 0 0.2rem;
}

.wickets {
  color: #e74c3c;
}

.overs-display {
  font-size: 1.4rem;
  color: #bdc3c7;
}

.overs-label {
  margin-right: 0.5rem;
}

.overs-value {
  font-weight: bold;
  color: #ecf0f1;
}

.target-display {
  background: rgba(255, 255, 255, 0.1);
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 1.2rem;
}

.target-label {
  color: #bdc3c7;
  margin-right: 0.5rem;
}

.target-value {
  font-weight: bold;
  color: #f39c12;
}

.required-info {
  color: #e74c3c;
  font-weight: bold;
  margin-left: 0.5rem;
}

.game-status {
  padding: 0.75rem 1.5rem;
  border-radius: 25px;
  font-weight: bold;
  font-size: 1.1rem;
  display: inline-block;
}

.status-live {
  background: #27ae60;
  color: white;
  animation: pulse 2s infinite;
}

.status-break {
  background: #f39c12;
  color: white;
}

.status-completed {
  background: #95a5a6;
  color: white;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.7; }
  100% { opacity: 1; }
}

/* Current batters display */
.batters-display {
  margin-bottom: 1rem;
  font-size: 1.1rem;
  color: #ecf0f1;
}

.batter {
  font-weight: 600;
}

.batter.striker {
  color: #2ecc71;
}

.separator-dot {
  margin: 0 0.5rem;
  color: #bdc3c7;
}

/* Captain / Keeper role badge */
.role-badge {
  font-size: 0.75em;
  font-weight: 700;
  color: #f39c12;
  opacity: 0.9;
  margin-left: 2px;
}

@media (max-width: 768px) {
  .live-scoreboard {
    padding: 1.5rem;
  }

  .main-score {
    font-size: 3rem;
  }

  .team-name {
    font-size: 1.4rem;
  }

  .scoreboard-header {
    flex-direction: column;
    gap: 1rem;
  }
}
</style>

<script setup lang="ts">
type Player = { id: string; name: string; disabled?: boolean };

defineProps<{
  mode?: 'official' | 'practice';
  gameMeta?: string;
  teamName: string;
  runs: number;
  wickets: number;
  overs: string;
  primaryStatLabel?: string;
  secondaryStatLabel?: string;
  striker: string;
  nonStriker: string;
  bowler: string;
  battingPlayers?: Player[];
  strikerPlayers?: Player[];
  nonStrikerPlayers?: Player[];
  bowlingPlayers?: Player[];
  editable?: boolean;
  showBowlerActions?: boolean;
}>();

const emit = defineEmits<{
  (event: 'update:striker', value: string): void;
  (event: 'update:nonStriker', value: string): void;
  (event: 'update:bowler', value: string): void;
}>();
</script>

<template>
  <header class="broadcast-header">
    <div class="header-left">
      <div class="brand">CRICKSY</div>
      <div v-if="mode === 'practice'" class="practice-tag">PRIVATE PRACTICE</div>
      <div v-else-if="gameMeta" class="game-meta">{{ gameMeta }}</div>
    </div>
    <div class="header-center dense-stats">
      <div class="stat-group main-score">
        <span class="team-name">{{ teamName }}</span>
        <span class="score-display"><span data-testid="scoreboard-runs">{{ runs }}</span>/{{ wickets }}</span>
        <span class="overs-display">(<span data-testid="scoreboard-overs">{{ overs }}</span>)</span>
      </div>
      <div class="stat-divider" />
      <div class="stat-group rates">
        <span v-if="primaryStatLabel" class="rate-item">{{ primaryStatLabel }}</span>
        <span v-if="secondaryStatLabel" class="rate-item">{{ secondaryStatLabel }}</span>
      </div>
    </div>
    <div class="header-right"><slot name="header-actions" /></div>
  </header>

  <section class="player-bar">
    <div class="player-box striker-box">
      <div class="pb-label">STRIKER</div>
      <select v-if="battingPlayers" :value="striker" class="pb-select-full" data-testid="scorer-striker-select" :disabled="!editable" @change="emit('update:striker', ($event.target as HTMLSelectElement).value)">
        <option disabled value="">Select...</option><option v-for="player in (strikerPlayers || battingPlayers)" :key="player.id" :value="player.id" :disabled="player.disabled">{{ player.name }}</option>
      </select>
      <div v-else class="pb-select-full">{{ striker }}</div>
    </div>
    <div class="player-box non-striker-box">
      <div class="pb-label">NON-STRIKER</div>
      <select v-if="battingPlayers" :value="nonStriker" class="pb-select-full" data-testid="scorer-nonstriker-select" :disabled="!editable" @change="emit('update:nonStriker', ($event.target as HTMLSelectElement).value)">
        <option disabled value="">Select...</option><option v-for="player in (nonStrikerPlayers || battingPlayers)" :key="player.id" :value="player.id" :disabled="player.disabled">{{ player.name }}</option>
      </select>
      <div v-else class="pb-select-full">{{ nonStriker }}</div>
    </div>
    <div class="player-box bowler-box">
      <div class="pb-label"><span>BOWLER</span><div v-if="showBowlerActions" class="bowler-actions"><slot name="bowler-actions" /></div></div>
      <select v-if="bowlingPlayers" :value="bowler" class="pb-select-full" data-testid="scorer-bowler-select" :disabled="!editable" @change="emit('update:bowler', ($event.target as HTMLSelectElement).value)">
        <option disabled value="">Select...</option><option v-for="player in bowlingPlayers" :key="player.id" :value="player.id">{{ player.name }}</option>
      </select>
      <div v-else class="pb-select-full">{{ bowler }}</div>
    </div>
  </section>
</template>

<style scoped>
.broadcast-header{background:#1a237e;color:#fff;padding:0 16px;min-height:48px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 4px #0003;z-index:10}.header-left{display:flex;align-items:baseline;gap:8px;min-width:0}.brand{font-weight:900;letter-spacing:1px;font-size:18px}.game-meta,.practice-tag{font-size:12px;opacity:.9}.header-center{flex:1;min-width:0;display:flex;justify-content:center}.dense-stats{display:flex;align-items:center;gap:16px;white-space:nowrap}.stat-group{display:flex;align-items:baseline;gap:6px}.main-score{font-size:20px;font-weight:700}.team-name{font-weight:400;opacity:.9;margin-right:4px;font-size:16px}.overs-display{font-size:14px;opacity:.9;font-weight:400}.stat-divider{width:1px;height:24px;background:#ffffff55}.rates{font-size:13px;gap:12px;opacity:.95}.header-right{display:flex;gap:8px;min-width:0;justify-content:flex-end}.player-bar{background:#283593;padding:8px 16px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;align-items:stretch}.player-box{background:#00000040;border:1px solid #ffffff33;border-radius:6px;padding:6px 12px;display:flex;flex-direction:column;gap:2px}.pb-label{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#fff;font-weight:700;display:flex;justify-content:space-between;align-items:center}.bowler-actions{display:flex;gap:6px}.pb-select-full{background:transparent;border:0;color:#fff;font-size:14px;font-weight:600;width:100%;cursor:pointer;outline:0;padding:0;margin:0}.pb-select-full option{background:#333;color:#fff}@media(max-width:768px){.broadcast-header{padding:8px;display:grid;grid-template-columns:1fr auto;gap:5px}.header-left{align-items:center}.header-center{grid-column:1/-1;justify-content:flex-start}.dense-stats{gap:8px;max-width:100%;overflow:hidden}.main-score{font-size:17px;min-width:0}.team-name{font-size:13px;overflow:hidden;text-overflow:ellipsis}.rates,.stat-divider{display:none}.game-meta,.practice-tag{font-size:10px;white-space:nowrap}.player-bar{padding:6px;gap:6px}.player-box{padding:5px 7px}.pb-select-full{font-size:12px}}
</style>

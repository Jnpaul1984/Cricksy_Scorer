<template>
  <div class="multi-player-comparison">
    <div class="comp-header">
      <h2 class="comp-title">🔄 Player Comparison</h2>
      <p class="comp-subtitle">Compare stats side-by-side</p>
    </div>

    <!-- Player Selection -->
    <div v-if="allPlayers.length === 0" class="empty-state-no-players">
      <div class="empty-icon">📊</div>
      <p class="empty-message">Player Database Unavailable</p>
      <p class="empty-hint">Player comparison will be available once the feature is fully implemented</p>
    </div>

    <div v-else class="player-selection">
      <div v-for="(slot, idx) in 3" :key="idx" class="player-slot">
        <div v-if="selectedPlayers[idx]" class="player-selected">
          <div class="player-header">
            <div class="player-avatar">{{ selectedPlayers[idx].initials }}</div>
            <div>
              <p class="player-name">{{ selectedPlayers[idx].name }}</p>
              <p class="player-team">{{ selectedPlayers[idx].team }}</p>
            </div>
          </div>
          <button class="remove-btn" @click="removePlayer(idx)">✕ Remove</button>
        </div>
        <div v-else class="player-selector">
          <select v-model="playerSearch[idx]" class="player-select" @change="addPlayer(idx)">
            <option value="">Select Player {{ idx + 1 }}</option>
            <option v-for="p in availablePlayers" :key="p.id" :value="p.id">
              {{ p.name }} ({{ p.team }})
            </option>
          </select>
        </div>
      </div>
    </div>

    <!-- Stat Comparison -->
    <div v-if="selectedPlayers.length > 0" class="comparison-container">
      <!-- Tabs -->
      <div class="comp-tabs">
        <button
          v-for="tab in compTabs"
          :key="tab.id"
          class="comp-tab"
          :class="{ active: activeCompTab === tab.id }"
          @click="activeCompTab = tab.id"
        >
          {{ tab.icon }} {{ tab.label }}
        </button>
      </div>

      <!-- Batting Stats -->
      <div v-if="activeCompTab === 'batting'" class="stat-comparison">
        <div class="comparison-grid">
          <div class="comp-label">Stat</div>
          <div v-for="player in selectedPlayers" :key="player.id" class="comp-label">
            {{ player.name }}
          </div>

          <div v-for="(stat, label) in battingStats" :key="label" class="comp-row">
            <div class="comp-row-label">{{ label }}</div>
            <div v-for="player in selectedPlayers" :key="player.id" class="comp-value">
              <div class="value-display">{{ stat(player) }}</div>
              <div v-if="selectedPlayers.length > 1" class="value-rank">
                {{ getRank(selectedPlayers, stat, player) }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Bowling Stats -->
      <div v-else-if="activeCompTab === 'bowling'" class="stat-comparison">
        <div class="comparison-grid">
          <div class="comp-label">Stat</div>
          <div v-for="player in selectedPlayers" :key="player.id" class="comp-label">
            {{ player.name }}
          </div>

          <div v-for="(stat, label) in bowlingStats" :key="label" class="comp-row">
            <div class="comp-row-label">{{ label }}</div>
            <div v-for="player in selectedPlayers" :key="player.id" class="comp-value">
              <div class="value-display">{{ stat(player) }}</div>
              <div v-if="selectedPlayers.length > 1" class="value-rank">
                {{ getRank(selectedPlayers, stat, player) }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Form & Consistency -->
      <div v-else-if="activeCompTab === 'form'" class="form-comparison">
        <div v-for="player in selectedPlayers" :key="player.id" class="player-form">
          <h4 class="form-player-name">{{ player.name }}</h4>
          <div class="form-dots">
            <span v-for="(result, idx) in getPlayerForm(player)" :key="idx" class="form-dot" :class="`result-${result}`" :title="result" />
          </div>
          <p class="form-summary">{{ getFormSummary(player) }}</p>
        </div>
      </div>

      <!-- Radar Chart -->
      <div v-else-if="activeCompTab === 'radar'" class="radar-comparison">
        <div class="radar-chart">
          <svg viewBox="0 0 400 400" class="radar-svg">
            <!-- Hexagon grid -->
            <circle cx="200" cy="200" r="40" class="radar-grid" />
            <circle cx="200" cy="200" r="80" class="radar-grid" />
            <circle cx="200" cy="200" r="120" class="radar-grid" />

            <!-- Axes labels -->
            <text x="200" y="30" class="radar-label" text-anchor="middle">Batting</text>
            <text x="345" y="110" class="radar-label" text-anchor="middle">Bowling</text>
            <text x="345" y="290" class="radar-label" text-anchor="middle">Fielding</text>
            <text x="55" y="290" class="radar-label" text-anchor="middle">Experience</text>
            <text x="55" y="110" class="radar-label" text-anchor="middle">Form</text>

            <!-- Player polygons -->
            <polygon
              v-for="(player, idx) in selectedPlayers"
              :key="player.id"
              :points="getRadarPoints(player)"
              :class="`radar-polygon player-${idx}`"
            />
          </svg>

          <!-- Legend -->
          <div class="radar-legend">
            <div v-for="(player, idx) in selectedPlayers" :key="player.id" class="legend-item">
              <span class="legend-color" :class="`player-${idx}`"></span>
              <span class="legend-label">{{ player.name }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Head-to-Head -->
      <div v-else-if="activeCompTab === 'h2h'" class="h2h-comparison">
        <div v-for="(matchup, idx) in headToHeadRecords" :key="idx" class="h2h-record">
          <div class="h2h-teams">
            <span class="h2h-name">{{ matchup.player1 }}</span>
            <span class="h2h-vs">vs</span>
            <span class="h2h-name">{{ matchup.player2 }}</span>
          </div>
          <div class="h2h-stats">
            <div class="h2h-stat">
              <span class="h2h-label">{{ matchup.player1 }}</span>
              <span class="h2h-value">{{ matchup.p1Wins }}-{{ matchup.p2Wins }}</span>
            </div>
            <div class="h2h-stat">
              <span class="h2h-label">Head-to-Head</span>
              <span class="h2h-text">{{ matchup.p1Wins + matchup.p2Wins }} Matches</span>
            </div>
            <div class="h2h-stat">
              <span class="h2h-label">{{ matchup.player2 }}</span>
              <span class="h2h-win-rate">{{ ((matchup.p2Wins / (matchup.p1Wins + matchup.p2Wins)) * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p class="empty-icon">🏏</p>
      <p class="empty-text">Select players to compare</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Player {
  id: string
  name: string
  team: string
  initials: string
  batting: {
    runs: number
    average: number
    strikeRate: number
    centuries: number
    fifties: number
  }
  bowling: {
    wickets: number
    economy: number
    average: number
    bestFigures: string
  }
  form: string[]
  consistency: number // 0-100
  experience: number // years
}

const activeCompTab = ref<'batting' | 'bowling' | 'form' | 'radar' | 'h2h'>('batting')
const selectedPlayers = ref<Player[]>([])
const playerSearch = ref<(string | null)[]>([null, null, null])

const compTabs = [
  { id: 'batting' as const, icon: '🏏', label: 'Batting' },
  { id: 'bowling' as const, icon: '🎯', label: 'Bowling' },
  { id: 'form' as const, icon: '📈', label: 'Form' },
  { id: 'radar' as const, icon: '🎲', label: 'Radar' },
  { id: 'h2h' as const, icon: '⚡', label: 'H2H' },
]

// Player database (empty - should be provided via API or props)
const allPlayers = computed<Player[]>(() => [])

const availablePlayers = computed(() =>
  allPlayers.value.filter((p) => !selectedPlayers.value.find((sp) => sp.id === p.id))
)

const battingStats: Record<string, (p: Player) => string | number> = {
  Runs: (p) => p.batting.runs,
  Average: (p) => p.batting.average.toFixed(2),
  'Strike Rate': (p) => p.batting.strikeRate.toFixed(1),
  Centuries: (p) => p.batting.centuries,
  Fifties: (p) => p.batting.fifties,
}

const bowlingStats: Record<string, (p: Player) => string | number> = {
  Wickets: (p) => p.bowling.wickets,
  Economy: (p) => p.bowling.economy.toFixed(2),
  Average: (p) => p.bowling.average.toFixed(2),
  'Best Figures': (p) => p.bowling.bestFigures,
}

const headToHeadRecords = computed(() => {
  const records = []
  for (let i = 0; i < selectedPlayers.value.length; i++) {
    for (let j = i + 1; j < selectedPlayers.value.length; j++) {
      const p1 = selectedPlayers.value[i]
      const p2 = selectedPlayers.value[j]
      records.push({
        player1: p1.name,
        player2: p2.name,
        p1Wins: Math.floor(Math.random() * 5) + 2,
        p2Wins: Math.floor(Math.random() * 5) + 2,
      })
    }
  }
  return records
})

function addPlayer(slotIdx: number) {
  if (!playerSearch.value[slotIdx]) return
  const player = allPlayers.value.find((p) => p.id === playerSearch.value[slotIdx])
  if (player && !selectedPlayers.value.find((sp) => sp.id === player.id)) {
    selectedPlayers.value.push(player)
  }
  playerSearch.value[slotIdx] = null
}

function removePlayer(slotIdx: number) {
  selectedPlayers.value.splice(slotIdx, 1)
}

function getRank(players: Player[], statFn: (p: Player) => string | number, player: Player): string {
  const values = players.map((p) => {
    const v = statFn(p)
    return typeof v === 'number' ? v : parseFloat(v as string)
  })
  const playerValue = values.find((_, i) => players[i].id === player.id) || 0
  const rank = values.filter((v) => v > playerValue).length + 1
  return `#${rank}`
}

function getPlayerForm(player: Player): string[] {
  return player.form.slice(-10)
}

function getFormSummary(player: Player): string {
  const wins = player.form.filter((f) => f === 'W').length
  return `${wins}/10 matches won`
}

function getRadarPoints(player: Player): string {
  const center = 200
  const radius = 100
  const angles = [0, 72, 144, 216, 288] // 5 points
  const values = [
    player.batting.average / 50,
    player.bowling.wickets / 50,
    80 / 100,
    player.experience / 10,
    player.form.filter((f) => f === 'W').length / 10,
  ]

  return angles
    .map((angle, i) => {
      const rad = (angle * Math.PI) / 180
      const x = center + Math.cos(rad - Math.PI / 2) * radius * Math.min(values[i], 1)
      const y = center + Math.sin(rad - Math.PI / 2) * radius * Math.min(values[i], 1)
      return `${x},${y}`
    })
    .join(' ')
}
</script>

<style scoped>
.multi-player-comparison {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding: var(--space-4);
}

/* Header */
.comp-header {
  margin-bottom: var(--space-2);
}

.comp-title {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--h2-size);
  font-weight: var(--h2-weight);
  color: var(--color-text);
}

.comp-subtitle {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Empty State */
.empty-state-no-players {
  padding: var(--space-12) var(--space-4);
  text-align: center;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 2px dashed var(--color-border);
  margin: var(--space-6) 0;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: var(--space-4);
  opacity: 0.3;
}

.empty-state-no-players .empty-message {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-2);
}

.empty-hint {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Player Selection */
.player-selection {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}

.player-slot {
  display: flex;
  flex-direction: column;
}

.player-selected {
  padding: var(--space-3);
  background: var(--color-bg);
  border: 2px solid var(--color-primary);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.player-header {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.player-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  flex-shrink: 0;
}

.player-name {
  margin: 0;
  font-weight: 600;
  color: var(--color-text);
  font-size: var(--text-sm);
}

.player-team {
  margin: var(--space-1) 0 0 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.remove-btn {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text);
  cursor: pointer;
  font-size: var(--text-xs);
  font-weight: 600;
  transition: all 0.2s ease;
}

.remove-btn:hover {
  background: var(--color-bg-secondary);
  border-color: #ef4444;
  color: #ef4444;
}

.player-selector {
  display: flex;
  flex-direction: column;
}

.player-select {
  padding: var(--space-3);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text);
  cursor: pointer;
  font-size: var(--text-sm);
  transition: all 0.2s ease;
}

.player-select:hover,
.player-select:focus {
  outline: none;
  border-color: var(--color-primary);
  background: var(--color-bg-secondary);
}

/* Comparison Container */
.comparison-container {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-secondary);
  overflow: hidden;
}

.comp-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg);
}

.comp-tab {
  flex: 1;
  padding: var(--space-3);
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.comp-tab:hover {
  background: var(--color-bg-secondary);
  color: var(--color-text);
}

.comp-tab.active {
  background: var(--color-bg-secondary);
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

/* Stat Comparison Grid */
.stat-comparison {
  padding: var(--space-4);
}

.comparison-grid {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: 120px repeat(auto-fit, minmax(150px, 1fr));
}

.comp-label {
  font-weight: 600;
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  text-transform: uppercase;
  padding: var(--space-2);
}

.comp-row {
  display: contents;
}

.comp-row-label {
  font-weight: 600;
  color: var(--color-text);
  padding: var(--space-2);
  border-right: 1px solid var(--color-border);
}

.comp-value {
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
}

.value-display {
  font-weight: 600;
  color: var(--color-primary);
  font-size: var(--text-base);
}

.value-rank {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin-top: var(--space-1);
}

/* Form Comparison */
.form-comparison {
  padding: var(--space-4);
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-4);
}

.player-form {
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.form-player-name {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text);
}

.form-dots {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.form-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: 600;
  color: white;
}

.form-dot.result-w {
  background: #22c55e;
}

.form-dot.result-l {
  background: #ef4444;
}

.form-summary {
  margin: var(--space-2) 0 0 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* Radar Chart */
.radar-comparison {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
}

.radar-chart {
  width: 100%;
  max-width: 500px;
}

.radar-svg {
  width: 100%;
  height: auto;
}

.radar-grid {
  stroke: var(--color-border);
  stroke-width: 1;
  fill: none;
}

.radar-label {
  font-size: 12px;
  font-weight: 600;
  fill: var(--color-text-muted);
}

.radar-polygon {
  fill-opacity: 0.15;
  stroke-width: 2;
  pointer-events: none;
}

.radar-polygon.player-0 {
  fill: #3b82f6;
  stroke: #3b82f6;
}

.radar-polygon.player-1 {
  fill: #ef4444;
  stroke: #ef4444;
}

.radar-polygon.player-2 {
  fill: #10b981;
  stroke: #10b981;
}

.radar-legend {
  display: flex;
  gap: var(--space-4);
  justify-content: center;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 50%;
}

.legend-color.player-0 {
  background: #3b82f6;
}

.legend-color.player-1 {
  background: #ef4444;
}

.legend-color.player-2 {
  background: #10b981;
}

.legend-label {
  color: var(--color-text);
  font-weight: 500;
}

/* Head-to-Head */
.h2h-comparison {
  padding: var(--space-4);
  display: grid;
  gap: var(--space-4);
}

.h2h-record {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  background: var(--color-bg);
}

.h2h-teams {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
  font-weight: 600;
}

.h2h-name {
  flex: 1;
  text-align: center;
}

.h2h-vs {
  margin: 0 var(--space-2);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.h2h-stats {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: var(--space-3);
}

.h2h-stat {
  text-align: center;
  padding: var(--space-2);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
}

.h2h-label {
  display: block;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin-bottom: var(--space-1);
}

.h2h-value,
.h2h-win-rate,
.h2h-text {
  display: block;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-primary);
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: var(--space-8) var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px dashed var(--color-border);
}

.empty-icon {
  font-size: 3rem;
  margin: 0;
}

.empty-text {
  margin: var(--space-2) 0 0 0;
  font-size: var(--text-base);
  color: var(--color-text-muted);
}

/* Responsive */
@media (max-width: 768px) {
  .player-selection {
    grid-template-columns: 1fr;
  }

  .comp-tabs {
    flex-wrap: wrap;
  }

  .comp-tab {
    flex: 0 1 auto;
  }

  .comparison-grid {
    grid-template-columns: 100px 1fr;
  }

  .h2h-stats {
    grid-template-columns: 1fr;
  }
}
</style>

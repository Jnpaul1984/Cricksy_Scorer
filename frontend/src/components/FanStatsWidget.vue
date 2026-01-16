<template>
  <div class="fan-stats">
    <!-- Unavailable State -->
    <div v-if="!backendEndpointAvailable" class="stats-unavailable">
      <div class="unavailable-icon">📊</div>
      <h3 class="unavailable-title">Tournament Leaderboards Unavailable</h3>
      <p class="unavailable-message">
        This widget requires backend endpoint: <code>{{ requiredEndpoint }}</code>
      </p>
      <p class="unavailable-hint">Once implemented, real tournament statistics will display here.</p>
    </div>

    <!-- Ready State (when backend available) -->
    <div v-else>
      <div class="stats-header">
        <h2 class="stats-title">📊 Cricket Stats Hub</h2>
        <p class="stats-subtitle">Aggregated statistics from followed teams and players</p>
      </div>

      <!-- Stat Tabs -->
      <div class="stats-tabs">
        <button
          v-for="tab in statTabs"
          :key="tab.id"
          class="stat-tab"
          :class="{ active: activeStat === tab.id }"
          @click="activeStat = tab.id"
        >
          {{ tab.icon }} {{ tab.label }}
        </button>
      </div>

      <!-- Stats Content -->
      <div class="stats-container">
      <!-- Top Batters -->
      <div v-if="activeStat === 'batters'" class="stat-section">
        <div class="section-header">
          <h3>🏏 Top Batters (Last 10 Matches)</h3>
          <select v-model="bitterSort" class="sort-select">
            <option value="runs">Most Runs</option>
            <option value="avg">Highest Average</option>
            <option value="sr">Highest SR</option>
          </select>
        </div>

        <div class="stats-table">
          <div class="table-header">
            <div class="col col-rank">#</div>
            <div class="col col-name">Player</div>
            <div class="col col-stat">Runs</div>
            <div class="col col-stat">Avg</div>
            <div class="col col-stat">SR</div>
            <div class="col col-stat">Matches</div>
          </div>

          <div v-for="(batter, idx) in sortedBatters" :key="batter.id" class="table-row">
            <div class="col col-rank">{{ idx + 1 }}</div>
            <div class="col col-name">
              <div class="player-info">
                <div class="player-avatar">{{ batter.initials }}</div>
                <div>
                  <p class="player-name">{{ batter.name }}</p>
                  <p class="player-team">{{ batter.team }}</p>
                </div>
              </div>
            </div>
            <div class="col col-stat">
              <span class="stat-value">{{ batter.runs }}</span>
            </div>
            <div class="col col-stat">
              <span class="stat-value">{{ batter.average.toFixed(2) }}</span>
            </div>
            <div class="col col-stat">
              <span class="stat-value" :class="`sr-${batter.strikeRate > 130 ? 'high' : batter.strikeRate > 100 ? 'normal' : 'low'}`">
                {{ batter.strikeRate.toFixed(1) }}
              </span>
            </div>
            <div class="col col-stat">{{ batter.matches }}</div>
          </div>
        </div>
      </div>

      <!-- Top Bowlers -->
      <div v-else-if="activeStat === 'bowlers'" class="stat-section">
        <div class="section-header">
          <h3>🎯 Top Bowlers (Last 10 Matches)</h3>
          <select v-model="bowlerSort" class="sort-select">
            <option value="wickets">Most Wickets</option>
            <option value="economy">Best Economy</option>
            <option value="avg">Best Average</option>
          </select>
        </div>

        <div class="stats-table">
          <div class="table-header">
            <div class="col col-rank">#</div>
            <div class="col col-name">Player</div>
            <div class="col col-stat">Wickets</div>
            <div class="col col-stat">Runs</div>
            <div class="col col-stat">Economy</div>
            <div class="col col-stat">Matches</div>
          </div>

          <div v-for="(bowler, idx) in sortedBowlers" :key="bowler.id" class="table-row">
            <div class="col col-rank">{{ idx + 1 }}</div>
            <div class="col col-name">
              <div class="player-info">
                <div class="player-avatar">{{ bowler.initials }}</div>
                <div>
                  <p class="player-name">{{ bowler.name }}</p>
                  <p class="player-team">{{ bowler.team }}</p>
                </div>
              </div>
            </div>
            <div class="col col-stat">
              <span class="stat-value wickets">{{ bowler.wickets }}</span>
            </div>
            <div class="col col-stat">
              <span class="stat-value">{{ bowler.runs }}</span>
            </div>
            <div class="col col-stat">
              <span class="stat-value" :class="`economy-${bowler.economy < 6 ? 'excellent' : bowler.economy < 8 ? 'good' : 'poor'}`">
                {{ bowler.economy.toFixed(2) }}
              </span>
            </div>
            <div class="col col-stat">{{ bowler.matches }}</div>
          </div>
        </div>
      </div>

      <!-- Team Stats -->
      <div v-else-if="activeStat === 'teams'" class="stat-section">
        <div class="section-header">
          <h3>👥 Team Performance (Last 10 Matches)</h3>
          <select v-model="teamSort" class="sort-select">
            <option value="wins">Most Wins</option>
            <option value="avgRuns">Avg Runs</option>
            <option value="winRate">Win Rate</option>
          </select>
        </div>

        <div class="team-stats-grid">
          <div v-for="team in sortedTeams" :key="team.id" class="team-card">
            <div class="team-header">
              <h4 class="team-name">{{ team.name }}</h4>
              <span class="team-badge" :class="`badge-${team.wins > team.losses ? 'winning' : 'struggling'}`">
                {{ team.wins }}-{{ team.losses }}
              </span>
            </div>

            <div class="team-stats">
              <div class="stat">
                <span class="stat-label">Avg Runs</span>
                <span class="stat-val">{{ team.avgRuns }}</span>
              </div>
              <div class="stat">
                <span class="stat-label">Win Rate</span>
                <span class="stat-val">{{ ((team.wins / (team.wins + team.losses)) * 100).toFixed(0) }}%</span>
              </div>
              <div class="stat">
                <span class="stat-label">Matches</span>
                <span class="stat-val">{{ team.wins + team.losses }}</span>
              </div>
            </div>

            <div class="team-form">
              <p class="form-label">Form</p>
              <div class="form-dots">
                <span
                  v-for="(result, idx) in team.form"
                  :key="idx"
                  class="form-dot"
                  :class="`result-${result.toLowerCase()}`"
                  :title="result"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Records -->
      <div v-else-if="activeStat === 'records'" class="stat-section">
        <div class="section-header">
          <h3>🏆 Records & Milestones</h3>
        </div>

        <div class="records-grid">
          <div v-for="record in records" :key="record.id" class="record-card">
            <div class="record-icon">{{ record.icon }}</div>
            <div class="record-content">
              <p class="record-title">{{ record.title }}</p>
              <p class="record-value">{{ record.value }}</p>
              <p class="record-holder">{{ record.holder }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Batter {
  id: string
  name: string
  team: string
  initials: string
  runs: number
  average: number
  strikeRate: number
  matches: number
}

interface Bowler {
  id: string
  name: string
  team: string
  initials: string
  wickets: number
  runs: number
  economy: number
  matches: number
}

interface Team {
  id: string
  name: string
  wins: number
  losses: number
  avgRuns: number
  form: string[]
}

interface Record {
  id: string
  icon: string
  title: string
  value: string
  holder: string
}

const activeStat = ref<'batters' | 'bowlers' | 'teams' | 'records'>('batters')
const bitterSort = ref<'runs' | 'avg' | 'sr'>('runs')
const bowlerSort = ref<'wickets' | 'economy' | 'avg'>('wickets')
const teamSort = ref<'wins' | 'avgRuns' | 'winRate'>('wins')

const statTabs = [
  { id: 'batters' as const, icon: '🏏', label: 'Batters' },
  { id: 'bowlers' as const, icon: '🎯', label: 'Bowlers' },
  { id: 'teams' as const, icon: '👥', label: 'Teams' },
  { id: 'records' as const, icon: '🏆', label: 'Records' },
]

// Backend endpoint availability
const backendEndpointAvailable = false
const requiredEndpoint = 'GET /tournaments/{tournamentId}/leaderboards'

// All generator functions removed - these created celebrity mock data
// When backend available, populate from real tournament leaderboard data
const batters = computed<Batter[]>(() => backendEndpointAvailable ? [] : [])
const bowlers = computed<Bowler[]>(() => backendEndpointAvailable ? [] : [])
const teams = computed<Team[]>(() => backendEndpointAvailable ? [] : [])
const records = computed<Record[]>(() => backendEndpointAvailable ? [] : [])

const sortedBatters = computed(() => {
  const sorted = [...batters.value]
  switch (bitterSort.value) {
    case 'runs':
      return sorted.sort((a, b) => b.runs - a.runs)
    case 'avg':
      return sorted.sort((a, b) => b.average - a.average)
    case 'sr':
      return sorted.sort((a, b) => b.strikeRate - a.strikeRate)
  }
})

const sortedBowlers = computed(() => {
  const sorted = [...bowlers.value]
  switch (bowlerSort.value) {
    case 'wickets':
      return sorted.sort((a, b) => b.wickets - a.wickets)
    case 'economy':
      return sorted.sort((a, b) => a.economy - b.economy)
    case 'avg':
      return sorted.sort((a, b) => a.runs / a.wickets - (b.runs / b.wickets))
  }
})

const sortedTeams = computed(() => {
  const sorted = [...teams.value]
  switch (teamSort.value) {
    case 'wins':
      return sorted.sort((a, b) => b.wins - a.wins)
    case 'avgRuns':
      return sorted.sort((a, b) => b.avgRuns - a.avgRuns)
    case 'winRate':
      return sorted.sort(
        (a, b) => b.wins / (b.wins + b.losses) - a.wins / (a.wins + a.losses)
      )
  }
})
</script>

<style scoped>
.fan-stats {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding: var(--space-4);
}

/* Unavailable State */
.stats-unavailable {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) var(--space-6);
  text-align: center;
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-secondary);
}

.unavailable-icon {
  font-size: 3rem;
  margin-bottom: var(--space-4);
  opacity: 0.5;
}

.unavailable-title {
  margin: 0 0 var(--space-3) 0;
  font-size: var(--h3-size);
  font-weight: var(--h3-weight);
  color: var(--color-text);
}

.unavailable-message {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--text-base);
  color: var(--color-text-secondary);
  max-width: 500px;
}

.unavailable-message code {
  padding: var(--space-1) var(--space-2);
  background: var(--color-surface);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--color-accent);
}

.unavailable-hint {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  font-style: italic;
}

/* Header */
.stats-header {
  margin-bottom: var(--space-2);
}

.stats-title {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--h2-size);
  font-weight: var(--h2-weight);
  color: var(--color-text);
}

.stats-subtitle {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Tabs */
.stats-tabs {
  display: flex;
  gap: var(--space-3);
  overflow-x: auto;
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.stat-tab {
  padding: var(--space-3) var(--space-4);
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.3s ease;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.stat-tab:hover {
  color: var(--color-text);
}

.stat-tab.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

/* Container */
.stats-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.stat-section {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-secondary);
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
}

.section-header h3 {
  margin: 0;
  font-size: var(--h3-size);
  color: var(--color-text);
}

.sort-select {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: var(--text-sm);
  cursor: pointer;
}

/* Table */
.stats-table {
  display: flex;
  flex-direction: column;
}

.table-header {
  display: grid;
  grid-template-columns: 40px 200px 80px 80px 80px 80px;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.table-row {
  display: grid;
  grid-template-columns: 40px 200px 80px 80px 80px 80px;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  align-items: center;
  transition: background 0.2s ease;
}

.table-row:hover {
  background: var(--color-bg);
}

.col {
  font-size: var(--text-sm);
  color: var(--color-text);
}

.col-rank {
  font-weight: 600;
  color: var(--color-text-muted);
  text-align: center;
}

.col-name {
  min-width: 0;
}

.player-info {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.player-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: var(--text-xs);
  flex-shrink: 0;
}

.player-name {
  margin: 0;
  font-weight: 600;
  color: var(--color-text);
}

.player-team {
  margin: var(--space-1) 0 0 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.stat-value {
  font-weight: 600;
  color: var(--color-text);
}

.stat-value.wickets {
  color: var(--color-primary);
}

.sr-high {
  color: #22c55e;
}

.sr-normal {
  color: var(--color-text);
}

.sr-low {
  color: #ef4444;
}

.economy-excellent {
  color: #22c55e;
}

.economy-good {
  color: var(--color-text);
}

.economy-poor {
  color: #ef4444;
}

/* Team Stats */
.team-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
  padding: var(--space-4);
}

.team-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  background: var(--color-bg);
  transition: all 0.3s ease;
}

.team-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
}

.team-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
}

.team-name {
  margin: 0;
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text);
}

.team-badge {
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: 600;
}

.badge-winning {
  background: #dcfce7;
  color: #166534;
}

.badge-struggling {
  background: #fee2e2;
  color: #991b1b;
}

.team-stats {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  padding: var(--space-3);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

.stat {
  text-align: center;
}

.stat-label {
  display: block;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin-bottom: var(--space-1);
}

.stat-val {
  display: block;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-primary);
}

.form-label {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
}

.form-dots {
  display: flex;
  gap: var(--space-2);
}

.form-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: var(--text-xs);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  color: white;
}

.result-w {
  background: #22c55e;
}

.result-l {
  background: #ef4444;
}

.result-n {
  background: var(--color-border);
  color: var(--color-text-muted);
}

/* Records */
.records-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--space-4);
  padding: var(--space-4);
}

.record-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  background: var(--color-bg);
  display: flex;
  gap: var(--space-3);
  transition: all 0.3s ease;
}

.record-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
  transform: translateY(-2px);
}

.record-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.record-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.record-title {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  font-weight: 500;
}

.record-value {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-primary);
}

.record-holder {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text);
  font-weight: 600;
}

/* Responsive */
@media (max-width: 768px) {
  .table-header,
  .table-row {
    grid-template-columns: 30px 140px 60px 60px 60px 60px;
  }

  .team-stats-grid {
    grid-template-columns: 1fr;
  }

  .records-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  }

  .stats-tabs {
    flex-wrap: wrap;
  }

  .record-card {
    flex-direction: column;
  }
}
</style>

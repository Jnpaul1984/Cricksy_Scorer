<template>
  <div class="phase-analysis">
    <div class="phase-header">
      <h2 class="phase-title">🎯 Phase Analysis</h2>
      <p class="phase-subtitle">Performance breakdown by match phases</p>
    </div>

    <!-- Phase Selection -->
    <div class="phase-tabs">
      <button
        v-for="phase in phases"
        :key="phase.id"
        class="phase-tab"
        :class="{ active: activePhase === phase.id }"
        @click="activePhase = phase.id"
      >
        {{ phase.icon }} {{ phase.name }}
        <span class="phase-badge">{{ phase.count }}</span>
      </button>
    </div>

    <!-- Phase Metrics -->
    <div class="phase-metrics">
      <div class="metric-card">
        <div class="metric-label">Avg Runs</div>
        <div class="metric-value">{{ phaseData.avgRuns }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Strike Rate</div>
        <div class="metric-value" :class="`sr-${getSRClass(phaseData.strikeRate)}`">
          {{ phaseData.strikeRate }}
        </div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Boundaries</div>
        <div class="metric-value">{{ phaseData.boundaries }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Wickets Lost</div>
        <div class="metric-value danger">{{ phaseData.wicketsLost }}</div>
      </div>
    </div>

    <!-- Detailed Stats -->
    <div class="phase-details">
      <div class="details-section">
        <h3 class="details-title">Performance Trend</h3>
        <div class="trend-chart">
          <svg viewBox="0 0 400 200" class="trend-svg">
            <!-- Grid lines -->
            <g class="grid">
              <line x1="0" y1="50" x2="400" y2="50" class="grid-line" />
              <line x1="0" y1="100" x2="400" y2="100" class="grid-line" />
              <line x1="0" y1="150" x2="400" y2="150" class="grid-line" />
            </g>

            <!-- Trend line -->
            <polyline :points="getTrendPoints()" class="trend-line" />

            <!-- Data points -->
            <circle
              v-for="(point, idx) in phaseData.trend"
              :key="`point-${idx}`"
              :cx="20 + idx * 40"
              :cy="160 - point"
              r="4"
              class="trend-point"
            />

            <!-- Axes -->
            <line x1="0" y1="160" x2="400" y2="160" class="axis" />
            <line x1="0" y1="0" x2="0" y2="160" class="axis" />
          </svg>
        </div>
      </div>

      <div class="details-section">
        <h3 class="details-title">Batting Order Impact</h3>
        <div class="batting-order">
          <div v-for="(player, idx) in phaseData.battingOrder" :key="`player-${idx}`" class="order-row">
            <div class="order-position">{{ idx + 1 }}</div>
            <div class="order-player">
              <p class="player-name">{{ player.name }}</p>
              <p class="player-role">{{ player.role }}</p>
            </div>
            <div class="order-stats">
              <span class="stat">{{ player.runs }} runs</span>
              <span class="stat">{{ player.sr }} SR</span>
            </div>
          </div>
        </div>
      </div>

      <div class="details-section">
        <h3 class="details-title">Key Moments</h3>
        <div class="key-moments">
          <div v-for="(moment, idx) in phaseData.keyMoments" :key="`moment-${idx}`" class="moment-item">
            <div class="moment-icon">{{ moment.icon }}</div>
            <div class="moment-content">
              <p class="moment-title">{{ moment.title }}</p>
              <p class="moment-time">{{ moment.time }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Phase Comparison -->
    <div class="phase-comparison">
      <h3 class="comparison-title">Phase Comparison</h3>
      <div class="comparison-chart">
        <div v-for="phase in phases" :key="phase.id" class="comparison-bar">
          <div class="bar-label">{{ phase.name }}</div>
          <div class="bar-container">
            <div
              class="bar-fill"
              :style="{ width: `${(phase.avgRuns / 20) * 100}%` }"
              :class="`phase-${phase.id}`"
            ></div>
          </div>
          <div class="bar-value">{{ phase.avgRuns }}</div>
        </div>
      </div>
    </div>

    <!-- Statistics Table -->
    <div class="phase-stats-table">
      <h3 class="table-title">Detailed Statistics</h3>
      <div class="table-scroll">
        <table class="stats-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Powerplay</th>
              <th>Middle</th>
              <th>Death</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="label">Total Runs</td>
              <td>{{ phaseStats.powerplay.totalRuns }}</td>
              <td>{{ phaseStats.middle.totalRuns }}</td>
              <td>{{ phaseStats.death.totalRuns }}</td>
            </tr>
            <tr>
              <td class="label">Avg Per Over</td>
              <td>{{ phaseStats.powerplay.avgPerOver }}</td>
              <td>{{ phaseStats.middle.avgPerOver }}</td>
              <td>{{ phaseStats.death.avgPerOver }}</td>
            </tr>
            <tr>
              <td class="label">Fours</td>
              <td>{{ phaseStats.powerplay.fours }}</td>
              <td>{{ phaseStats.middle.fours }}</td>
              <td>{{ phaseStats.death.fours }}</td>
            </tr>
            <tr>
              <td class="label">Sixes</td>
              <td>{{ phaseStats.powerplay.sixes }}</td>
              <td>{{ phaseStats.middle.sixes }}</td>
              <td>{{ phaseStats.death.sixes }}</td>
            </tr>
            <tr>
              <td class="label">Wickets Lost</td>
              <td>{{ phaseStats.powerplay.wickets }}</td>
              <td>{{ phaseStats.middle.wickets }}</td>
              <td>{{ phaseStats.death.wickets }}</td>
            </tr>
            <tr>
              <td class="label">Strike Rate</td>
              <td>{{ phaseStats.powerplay.sr }}</td>
              <td>{{ phaseStats.middle.sr }}</td>
              <td>{{ phaseStats.death.sr }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Insights -->
    <div class="phase-insights">
      <h3 class="insights-title">📊 Insights</h3>
      <div class="insights-grid">
        <div class="insight-card">
          <div class="insight-icon">💡</div>
          <p class="insight-text">Strongest in {{ strongestPhase }}, averaging {{ getPhaseAvg(strongestPhase) }} runs</p>
        </div>
        <div class="insight-card">
          <div class="insight-icon">⚠️</div>
          <p class="insight-text">Loses wickets frequently in {{ weakestPhase }}, causing momentum loss</p>
        </div>
        <div class="insight-card">
          <div class="insight-icon">🎯</div>
          <p class="insight-text">Strike rate increases as innings progresses - aggressive playing style</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface PhaseData {
  avgRuns: number
  strikeRate: number
  boundaries: number
  wicketsLost: number
  trend: number[]
  battingOrder: Array<{ name: string; role: string; runs: number; sr: number }>
  keyMoments: Array<{ icon: string; title: string; time: string }>
}

interface PhaseStats {
  totalRuns: number
  avgPerOver: number
  fours: number
  sixes: number
  wickets: number
  sr: number
}

const activePhase = ref<'powerplay' | 'middle' | 'death'>('powerplay')

const phases = [
  { id: 'powerplay' as const, name: 'Powerplay (0-6)', icon: '⚡', count: '6 overs', avgRuns: 12 },
  { id: 'middle' as const, name: 'Middle (7-16)', icon: '🎯', count: '10 overs', avgRuns: 9 },
  { id: 'death' as const, name: 'Death (17-20)', icon: '💥', count: '4 overs', avgRuns: 14 },
]

const phaseDataMap: Record<'powerplay' | 'middle' | 'death', PhaseData> = {
  powerplay: {
    avgRuns: 72,
    strikeRate: 154.3,
    boundaries: 8,
    wicketsLost: 1,
    trend: [8, 10, 12, 15, 14, 13],
    battingOrder: [
      { name: 'Rohit Sharma', role: 'Opener', runs: 28, sr: 162 },
      { name: 'Virat Kohli', role: 'Batter', runs: 44, sr: 147 },
    ],
    keyMoments: [
      { icon: '🎯', title: 'Boundary over mid-wicket', time: 'Over 1' },
      { icon: '⚡', title: 'Two sixes in succession', time: 'Over 3' },
      { icon: '💀', title: 'Opener dismissed', time: 'Over 5' },
    ],
  },
  middle: {
    avgRuns: 90,
    strikeRate: 128.6,
    boundaries: 10,
    wicketsLost: 2,
    trend: [9, 8, 9, 10, 9, 8, 9, 10, 9, 8],
    battingOrder: [
      { name: 'Virat Kohli', role: 'Batter', runs: 68, sr: 134 },
      { name: 'KL Rahul', role: 'Batter', runs: 22, sr: 122 },
    ],
    keyMoments: [
      { icon: '🎯', title: 'Partnership 50 run stand', time: 'Over 10' },
      { icon: '⚠️', title: 'Miscommunication run-out attempt', time: 'Over 14' },
      { icon: '4️⃣', title: 'Boundary to reach 50', time: 'Over 16' },
    ],
  },
  death: {
    avgRuns: 56,
    strikeRate: 186.7,
    boundaries: 5,
    wicketsLost: 1,
    trend: [18, 14, 15, 9],
    battingOrder: [
      { name: 'Hardik Pandya', role: 'All-rounder', runs: 27, sr: 225 },
      { name: 'MS Dhoni', role: 'Finisher', runs: 29, sr: 169 },
    ],
    keyMoments: [
      { icon: '💥', title: 'Two sixes in Death over', time: 'Over 18' },
      { icon: '4️⃣', title: 'Yorker conceded boundary', time: 'Over 19' },
      { icon: '🎉', title: 'Winning boundary', time: 'Over 20' },
    ],
  },
}

const phaseData = computed(() => phaseDataMap[activePhase.value])

const phaseStats: Record<'powerplay' | 'middle' | 'death', PhaseStats> = {
  powerplay: { totalRuns: 72, avgPerOver: 12, fours: 6, sixes: 2, wickets: 1, sr: 154.3 },
  middle: { totalRuns: 90, avgPerOver: 9, fours: 8, sixes: 2, wickets: 2, sr: 128.6 },
  death: { totalRuns: 56, avgPerOver: 14, fours: 3, sixes: 4, wickets: 1, sr: 186.7 },
}

const strongestPhase = computed(() => {
  const phaseRuns = phases.map((p) => phaseStats[p.id].totalRuns)
  const maxIdx = phaseRuns.indexOf(Math.max(...phaseRuns))
  return phases[maxIdx].name.split(' ')[0]
})

const weakestPhase = computed(() => {
  const phaseWickets = phases.map((p) => phaseStats[p.id].wickets)
  const maxIdx = phaseWickets.indexOf(Math.max(...phaseWickets))
  return phases[maxIdx].name.split(' ')[0]
})

function getSRClass(sr: number): string {
  if (sr > 150) return 'sr-high'
  if (sr > 120) return 'sr-normal'
  return 'sr-low'
}

function getTrendPoints(): string {
  return phaseData.value.trend
    .map((val, i) => `${20 + i * 40},${160 - val}`)
    .join(' ')
}

function getPhaseAvg(phaseName: string): number {
  const phase = phases.find((p) => p.name.includes(phaseName))
  return phase ? phaseStats[phase.id].avgPerOver : 0
}
</script>

<style scoped>
.phase-analysis {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding: var(--space-4);
}

/* Header */
.phase-header {
  margin-bottom: var(--space-2);
}

.phase-title {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--h2-size);
  font-weight: var(--h2-weight);
  color: var(--color-text);
}

.phase-subtitle {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Phase Tabs */
.phase-tabs {
  display: flex;
  gap: var(--space-3);
  overflow-x: auto;
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.phase-tab {
  display: flex;
  align-items: center;
  gap: var(--space-2);
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

.phase-tab:hover {
  color: var(--color-text);
}

.phase-tab.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.phase-badge {
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* Metrics */
.phase-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}

.metric-card {
  text-align: center;
  padding: var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.metric-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin-bottom: var(--space-2);
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.metric-value {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-primary);
}

.metric-value.sr-high {
  color: #22c55e;
}

.metric-value.sr-normal {
  color: var(--color-text);
}

.metric-value.sr-low {
  color: #ef4444;
}

.metric-value.danger {
  color: #ef4444;
}

/* Details */
.phase-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-4);
}

.details-section {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  background: var(--color-bg-secondary);
}

.details-title {
  margin: 0 0 var(--space-3) 0;
  font-size: var(--h3-size);
  color: var(--color-text);
  font-weight: 600;
}

/* Trend Chart */
.trend-chart {
  width: 100%;
}

.trend-svg {
  width: 100%;
  height: auto;
}

.grid-line {
  stroke: var(--color-border);
  stroke-width: 1;
  stroke-dasharray: 4 4;
}

.axis {
  stroke: var(--color-text-muted);
  stroke-width: 2;
}

.trend-line {
  fill: none;
  stroke: var(--color-primary);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.trend-point {
  fill: var(--color-primary);
  stroke: white;
  stroke-width: 2;
}

/* Batting Order */
.batting-order {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.order-row {
  display: grid;
  grid-template-columns: 40px 1fr auto;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-2);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.order-position {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--color-primary);
  color: white;
  font-weight: 700;
  font-size: var(--text-sm);
}

.order-player {
  min-width: 0;
}

.player-name {
  margin: 0;
  font-weight: 600;
  color: var(--color-text);
  font-size: var(--text-sm);
}

.player-role {
  margin: var(--space-1) 0 0 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.order-stats {
  display: flex;
  gap: var(--space-2);
}

.stat {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-primary);
  white-space: nowrap;
}

/* Key Moments */
.key-moments {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.moment-item {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-2);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.moment-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.moment-content {
  min-width: 0;
}

.moment-title {
  margin: 0;
  font-weight: 600;
  color: var(--color-text);
  font-size: var(--text-sm);
}

.moment-time {
  margin: var(--space-1) 0 0 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* Phase Comparison */
.phase-comparison {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  background: var(--color-bg-secondary);
}

.comparison-title {
  margin: 0 0 var(--space-4) 0;
  font-size: var(--h3-size);
  color: var(--color-text);
  font-weight: 600;
}

.comparison-chart {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.comparison-bar {
  display: grid;
  grid-template-columns: 100px 1fr 60px;
  gap: var(--space-3);
  align-items: center;
}

.bar-label {
  font-weight: 600;
  color: var(--color-text);
  font-size: var(--text-sm);
}

.bar-container {
  height: 32px;
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  transition: width 0.3s ease;
}

.bar-fill.phase-powerplay {
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
}

.bar-fill.phase-middle {
  background: linear-gradient(90deg, #f59e0b, #fbbf24);
}

.bar-fill.phase-death {
  background: linear-gradient(90deg, #ef4444, #f87171);
}

.bar-value {
  text-align: right;
  font-weight: 600;
  color: var(--color-primary);
  font-size: var(--text-sm);
}

/* Stats Table */
.phase-stats-table {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  background: var(--color-bg-secondary);
}

.table-title {
  margin: 0 0 var(--space-3) 0;
  font-size: var(--h3-size);
  color: var(--color-text);
  font-weight: 600;
}

.table-scroll {
  overflow-x: auto;
}

.stats-table {
  width: 100%;
  border-collapse: collapse;
}

.stats-table thead {
  background: var(--color-bg);
  border-bottom: 2px solid var(--color-border);
}

.stats-table th {
  padding: var(--space-3);
  text-align: left;
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stats-table td {
  padding: var(--space-3);
  border-bottom: 1px solid var(--color-border);
  font-size: var(--text-sm);
  color: var(--color-text);
}

.stats-table td.label {
  font-weight: 600;
  background: var(--color-bg);
  color: var(--color-text-muted);
}

.stats-table tbody tr:hover {
  background: var(--color-bg);
}

/* Insights */
.phase-insights {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  background: linear-gradient(135deg, var(--color-primary-light), var(--color-bg-secondary));
}

.insights-title {
  margin: 0 0 var(--space-3) 0;
  font-size: var(--h3-size);
  color: var(--color-text);
  font-weight: 600;
}

.insights-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-4);
}

.insight-card {
  padding: var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
}

.insight-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.insight-text {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text);
  line-height: 1.6;
}

/* Responsive */
@media (max-width: 768px) {
  .phase-metrics {
    grid-template-columns: repeat(2, 1fr);
  }

  .phase-details {
    grid-template-columns: 1fr;
  }

  .order-row {
    grid-template-columns: 40px 1fr;
  }

  .order-stats {
    grid-column: 1 / -1;
    flex-direction: column;
  }

  .comparison-bar {
    grid-template-columns: 80px 1fr 50px;
  }
}
</style>

<template>
  <div class="analytics-tables-widget">
    <div class="analytics-header">
      <h3 class="analytics-title">📊 Analytics Tables</h3>
      <div class="analytics-controls">
        <button
          v-for="chart in chartTypes"
          :key="chart.id"
          class="chart-tab"
          :class="{ active: activeChart === chart.id }"
          :title="chart.description"
          @click="activeChart = chart.id"
        >
          {{ chart.label }}
        </button>
      </div>
    </div>

    <!-- Manhattan Plot -->
    <div v-if="activeChart === 'manhattan'" class="chart-container">
      <div class="chart-info">
        <h4>Manhattan Plot</h4>
        <p>Runs scored per delivery in the innings</p>
      </div>
      <div class="manhattan-plot">
        <div class="manhattan-axis-y">
          <span v-for="i in 5" :key="`y-${i}`" class="y-label">{{ (5 - i) * 2 }}</span>
        </div>
        <div class="manhattan-area">
          <div v-for="(delivery, idx) in manhattan" :key="`delivery-${idx}`" class="delivery-bar-wrapper">
            <div
              class="delivery-bar"
              :style="{
                height: (delivery.runs / 10) * 100 + '%',
                backgroundColor: getRunColor(delivery.runs),
              }"
              :title="`Ball ${idx + 1}: ${delivery.runs} runs (${delivery.type})`"
              @mouseenter="hoverDelivery = idx"
              @mouseleave="hoverDelivery = null"
            >
              <span v-if="hoverDelivery === idx" class="hover-label">{{ delivery.runs }}</span>
            </div>
          </div>
        </div>
        <div class="manhattan-axis-x">Deliveries</div>
      </div>
      <div class="chart-legend">
        <div class="legend-item">
          <span class="color-dot" style="background: #10b981"></span>
          <span>0-1 runs (singles)</span>
        </div>
        <div class="legend-item">
          <span class="color-dot" style="background: #f59e0b"></span>
          <span>2 runs (doubles)</span>
        </div>
        <div class="legend-item">
          <span class="color-dot" style="background: #ef4444"></span>
          <span>3-6 runs (boundaries)</span>
        </div>
        <div class="legend-item">
          <span class="color-dot" style="background: #8b5cf6"></span>
          <span>Wicket</span>
        </div>
      </div>
    </div>

    <!-- Worm Chart -->
    <div v-else-if="activeChart === 'worm'" class="chart-container">
      <div class="chart-info">
        <h4>Worm Chart</h4>
        <p>Cumulative runs progression throughout the innings</p>
      </div>
      <div class="worm-chart-wrapper">
        <svg class="worm-chart" :viewBox="`0 0 ${wormChartWidth} ${wormChartHeight}`">
          <!-- Grid lines -->
          <g class="grid">
            <line
v-for="i in 5" :key="`grid-h-${i}`" :x1="0" :y1="(i / 5) * wormChartHeight"
                  :x2="wormChartWidth" :y2="(i / 5) * wormChartHeight" stroke="#e5e7eb" stroke-width="1" />
            <line
v-for="i in 10" :key="`grid-v-${i}`" :x1="(i / 10) * wormChartWidth" :y1="0"
                  :x2="(i / 10) * wormChartWidth" :y2="wormChartHeight" stroke="#e5e7eb" stroke-width="1" />
          </g>

          <!-- Cumulative runs line -->
          <polyline :points="wormLinePoints" class="worm-line" />

          <!-- Data points -->
          <circle
v-for="(point, idx) in wormPoints" :key="`point-${idx}`" :cx="point.x" :cy="point.y"
                  r="3" class="worm-point" :class="{ 'worm-point-wicket': point.isWicket }"
                  :title="`Ball ${idx + 1}: ${point.cumulativeRuns} runs (${point.deliveryType})`"
                  @mouseenter="hoverWormBall = idx"
                  @mouseleave="hoverWormBall = null" />

          <!-- Hover label -->
          <g v-if="hoverWormBall !== null" class="hover-info">
            <circle
:cx="wormPoints[hoverWormBall].x" :cy="wormPoints[hoverWormBall].y" r="5"
                    fill="none" stroke="#3b82f6" stroke-width="2" />
            <text
:x="wormPoints[hoverWormBall].x" :y="wormPoints[hoverWormBall].y - 15"
                  text-anchor="middle" class="worm-hover-text">
              {{ wormPoints[hoverWormBall].cumulativeRuns }}
            </text>
          </g>

          <!-- Axes labels -->
          <text x="10" y="20" class="axis-label">Runs</text>
          <text :x="wormChartWidth - 50" :y="wormChartHeight - 5" class="axis-label">Deliveries</text>
        </svg>
      </div>
      <div class="worm-stats">
        <div class="stat">
          <span class="stat-label">Total Runs:</span>
          <span class="stat-value">{{ totalRuns }}</span>
        </div>
        <div class="stat">
          <span class="stat-label">Deliveries:</span>
          <span class="stat-value">{{ totalDeliveries }}</span>
        </div>
        <div class="stat">
          <span class="stat-label">Run Rate:</span>
          <span class="stat-value">{{ runRate.toFixed(2) }}</span>
        </div>
        <div class="stat">
          <span class="stat-label">Wickets:</span>
          <span class="stat-value">{{ totalWickets }}</span>
        </div>
      </div>
    </div>

    <!-- Scatter Plot: Runs vs Balls -->
    <div v-else-if="activeChart === 'scatter'" class="chart-container">
      <div class="chart-info">
        <h4>Performance Scatter</h4>
        <p>Strike rate and consistency analysis</p>
      </div>
      <div class="scatter-wrapper">
        <svg class="scatter-chart" :viewBox="`0 0 ${scatterWidth} ${scatterHeight}`">
          <!-- Grid -->
          <g class="grid">
            <line
v-for="i in 4" :key="`sgrid-h-${i}`" :x1="0" :y1="(i / 4) * scatterHeight"
                  :x2="scatterWidth" :y2="(i / 4) * scatterHeight" stroke="#e5e7eb" stroke-width="1" />
            <line
v-for="i in 4" :key="`sgrid-v-${i}`" :x1="(i / 4) * scatterWidth" :y1="0"
                  :x2="(i / 4) * scatterWidth" :y2="scatterHeight" stroke="#e5e7eb" stroke-width="1" />
          </g>

          <!-- Dots -->
          <circle
v-for="(point, idx) in scatterPoints" :key="`scatter-${idx}`" :cx="point.x"
                  :cy="point.y" :r="4" :class="['scatter-dot', point.colorClass]"
                  :title="`Match ${idx + 1}: ${point.balls} balls, ${point.runs} runs (SR: ${point.sr.toFixed(0)})`"
                  @mouseenter="hoverScatterMatch = idx"
                  @mouseleave="hoverScatterMatch = null" />

          <!-- Hover info -->
          <g v-if="hoverScatterMatch !== null" class="scatter-hover">
            <circle
:cx="scatterPoints[hoverScatterMatch].x"
                    :cy="scatterPoints[hoverScatterMatch].y" r="6"
                    fill="none" stroke="#3b82f6" stroke-width="2" />
            <text
:x="scatterPoints[hoverScatterMatch].x" :y="scatterPoints[hoverScatterMatch].y - 15"
                  text-anchor="middle" class="scatter-hover-text">
              SR: {{ scatterPoints[hoverScatterMatch].sr.toFixed(0) }}
            </text>
          </g>

          <!-- Axis labels -->
          <text x="10" y="20" class="axis-label">Runs</text>
          <text :x="scatterWidth - 50" :y="scatterHeight - 5" class="axis-label">Balls</text>
        </svg>
      </div>
      <div class="chart-legend">
        <div class="legend-item">
          <span class="color-dot" style="background: #10b981"></span>
          <span>High SR (&gt; 120)</span>
        </div>
        <div class="legend-item">
          <span class="color-dot" style="background: #f59e0b"></span>
          <span>Normal SR (90-120)</span>
        </div>
        <div class="legend-item">
          <span class="color-dot" style="background: #ef4444"></span>
          <span>Low SR (&lt; 90)</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, ref, computed } from 'vue'

import type { PlayerProfile } from '@/types/player'

interface DeliveryData {
  runs: number
  type: string // 'dot', 'single', 'double', 'boundary', 'wicket'
}

interface WormPoint {
  x: number
  y: number
  cumulativeRuns: number
  deliveryType: string
  isWicket: boolean
}

interface ScatterPoint {
  x: number
  y: number
  balls: number
  runs: number
  sr: number
  colorClass: string
}

const props = defineProps<{
  profile: PlayerProfile | null
}>()

const activeChart = ref<'manhattan' | 'worm' | 'scatter'>('manhattan')
const hoverDelivery = ref<number | null>(null)
const hoverWormBall = ref<number | null>(null)
const hoverScatterMatch = ref<number | null>(null)

// Chart type options
const chartTypes = [
  { id: 'manhattan' as const, label: '📊 Manhattan', description: 'Runs per delivery' },
  { id: 'worm' as const, label: '🐛 Worm', description: 'Cumulative progression' },
  { id: 'scatter' as const, label: '⚡ Scatter', description: 'Strike rate analysis' },
]

// Generate mock cricket data
const generateManhattanData = (): DeliveryData[] => {
  const types = ['dot', 'single', 'double', 'boundary', 'wicket']
  const weights = [0.25, 0.35, 0.2, 0.15, 0.05]
  return Array.from({ length: 120 }, () => {
    const rand = Math.random()
    let cumWeight = 0
    for (let i = 0; i < types.length; i++) {
      cumWeight += weights[i]
      if (rand <= cumWeight) {
        const type = types[i]
        const runs =
          type === 'dot' ? 0 : type === 'single' ? 1 : type === 'double' ? 2 : type === 'wicket' ? 0 : Math.random() > 0.5 ? 4 : 6
        return { runs, type }
      }
    }
    return { runs: 0, type: 'dot' }
  })
}

const manhattan = ref(generateManhattanData())

// Worm chart data (cumulative)
const wormChartWidth = 600
const wormChartHeight = 250
const maxRuns = computed(() => {
  const total = manhattan.value.reduce((sum, d) => sum + d.runs, 0)
  return Math.ceil(total / 10) * 10
})

const wormPoints = computed((): WormPoint[] => {
  let cumulativeRuns = 0
  return manhattan.value.map((delivery, idx) => {
    cumulativeRuns += delivery.runs
    const x = ((idx + 1) / manhattan.value.length) * wormChartWidth
    const y = wormChartHeight - (cumulativeRuns / maxRuns.value) * wormChartHeight * 0.85
    return {
      x,
      y,
      cumulativeRuns,
      deliveryType: delivery.type,
      isWicket: delivery.type === 'wicket',
    }
  })
})

const wormLinePoints = computed(() => {
  return wormPoints.value.map((p) => `${p.x},${p.y}`).join(' ')
})

const totalRuns = computed(() => manhattan.value.reduce((sum, d) => sum + d.runs, 0))
const totalDeliveries = computed(() => manhattan.value.length)
const totalWickets = computed(() => manhattan.value.filter((d) => d.type === 'wicket').length)
const runRate = computed(() => (totalRuns.value / totalDeliveries.value) * 6)

// Scatter chart data (strike rate per match)
const scatterWidth = 500
const scatterHeight = 300
const matches = 20

const generateScatterData = (): ScatterPoint[] => {
  return Array.from({ length: matches }, () => {
    const balls = Math.floor(Math.random() * 60) + 20
    const maxRuns = Math.floor(balls * 1.2)
    const runs = Math.floor(Math.random() * maxRuns)
    const sr = (runs / balls) * 100

    const x = (balls / 100) * scatterWidth
    const y = scatterHeight - (runs / 100) * scatterHeight

    const colorClass = sr > 120 ? 'high' : sr > 90 ? 'normal' : 'low'

    return { x, y, balls, runs, sr, colorClass }
  })
}

const scatterPoints = ref(generateScatterData())

// Color mapping
function getRunColor(runs: number): string {
  if (runs === 0) return '#6b7280' // gray for dot
  if (runs === 1) return '#10b981' // green for single
  if (runs === 2) return '#f59e0b' // amber for double
  return '#ef4444' // red for boundary/wicket
}
</script>

<style scoped>
.analytics-tables-widget {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
}

/* Header */
.analytics-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
}

.analytics-title {
  margin: 0;
  font-size: var(--h3-size);
  font-weight: var(--h3-weight);
  color: var(--color-text);
}

.analytics-controls {
  display: flex;
  gap: var(--space-2);
}

.chart-tab {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.chart-tab:hover {
  border-color: var(--color-primary);
  background: var(--color-bg-secondary);
}

.chart-tab.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

/* Container */
.chart-container {
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-secondary);
}

.chart-info {
  margin-bottom: var(--space-4);
}

.chart-info h4 {
  margin: 0 0 var(--space-1) 0;
  font-size: var(--h4-size);
  font-weight: 600;
  color: var(--color-text);
}

.chart-info p {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Manhattan Plot */
.manhattan-plot {
  display: flex;
  gap: var(--space-2);
  height: 200px;
  align-items: flex-end;
  margin: var(--space-4) 0;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.manhattan-axis-y {
  display: flex;
  flex-direction: column-reverse;
  justify-content: space-around;
  width: 40px;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  padding-right: var(--space-2);
  border-right: 1px solid var(--color-border);
}

.y-label {
  text-align: right;
}

.manhattan-area {
  flex: 1;
  display: flex;
  gap: 2px;
  align-items: flex-end;
  max-height: 180px;
}

.delivery-bar-wrapper {
  flex: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  position: relative;
  min-width: 2px;
}

.delivery-bar {
  width: 100%;
  min-height: 2px;
  border-radius: var(--radius-sm);
  transition: all 0.2s ease;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.delivery-bar:hover {
  filter: brightness(1.2);
}

.hover-label {
  font-size: var(--text-xs);
  font-weight: 700;
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.manhattan-axis-x {
  position: absolute;
  bottom: -25px;
  left: 50%;
  transform: translateX(-50%);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* Worm Chart */
.worm-chart-wrapper {
  margin: var(--space-4) 0;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.worm-chart {
  width: 100%;
  height: auto;
  max-height: 300px;
}

.worm-line {
  fill: none;
  stroke: var(--color-primary);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.worm-point {
  fill: var(--color-primary);
  opacity: 0.6;
  cursor: pointer;
  transition: opacity 0.2s ease;
}

.worm-point:hover {
  opacity: 1;
}

.worm-point-wicket {
  fill: #ef4444;
}

.worm-hover-text {
  font-size: 12px;
  font-weight: 600;
  fill: var(--color-primary);
}

.axis-label {
  font-size: 12px;
  fill: var(--color-text-muted);
  font-weight: 500;
}

.worm-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding: var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.stat {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: 500;
}

.stat-value {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-text);
}

/* Scatter Chart */
.scatter-wrapper {
  margin: var(--space-4) 0;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.scatter-chart {
  width: 100%;
  height: auto;
  max-height: 350px;
}

.scatter-dot {
  cursor: pointer;
  transition: r 0.2s ease;
}

.scatter-dot.high {
  fill: #10b981;
  opacity: 0.7;
}

.scatter-dot.normal {
  fill: #f59e0b;
  opacity: 0.7;
}

.scatter-dot.low {
  fill: #ef4444;
  opacity: 0.7;
}

.scatter-dot:hover {
  r: 6;
  opacity: 1;
}

.scatter-hover-text {
  font-size: 12px;
  font-weight: 600;
  fill: var(--color-primary);
}

/* Legend */
.chart-legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  padding: var(--space-3);
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-text);
}

.color-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 2px;
  flex-shrink: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .analytics-controls {
    flex-wrap: wrap;
  }

  .chart-tab {
    padding: var(--space-1) var(--space-2);
    font-size: var(--text-xs);
  }

  .manhattan-plot {
    height: 150px;
  }

  .worm-stats {
    grid-template-columns: repeat(2, 1fr);
  }

  .chart-legend {
    flex-direction: column;
    gap: var(--space-2);
  }
}
</style>

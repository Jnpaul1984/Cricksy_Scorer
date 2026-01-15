<template>
  <div class="pitch-map-viewer">
    <div class="viewer-header">
      <h3>📍 Pitch Map</h3>
      <div class="filter-controls">
        <select v-model="lengthFilter" class="filter-select">
          <option value="">All Lengths</option>
          <option value="yorker">Yorker</option>
          <option value="full">Full</option>
          <option value="good_length">Good Length</option>
          <option value="short">Short</option>
          <option value="bouncer">Bouncer</option>
        </select>
        <select v-model="lineFilter" class="filter-select">
          <option value="">All Lines</option>
          <option value="wide_leg">Wide Leg</option>
          <option value="leg_stump">Leg Stump</option>
          <option value="middle">Middle</option>
          <option value="off_stump">Off Stump</option>
          <option value="wide_off">Wide Off</option>
        </select>
      </div>
    </div>

    <!-- Stats summary -->
    <div class="stats-summary">
      <div class="stat-card">
        <span class="stat-label">Total Deliveries</span>
        <span class="stat-value">{{ filteredPoints.length }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">Avg Length</span>
        <span class="stat-value">{{ averageLength.toFixed(1) }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">Avg Line</span>
        <span class="stat-value">{{ averageLine.toFixed(1) }}</span>
      </div>
    </div>

    <!-- Pitch visualization -->
    <div class="pitch-container">
      <svg class="pitch-svg" viewBox="0 0 100 100">
        <!-- Pitch background -->
        <rect x="0" y="0" width="100" height="100" fill="#0d5a2c" />

        <!-- Grid lines (subtle) -->
        <g opacity="0.2">
          <line v-for="i in 9" :key="`h-${i}`" :x1="0" :y1="i * 10" :x2="100" :y2="i * 10" stroke="white" stroke-width="0.1" />
          <line v-for="i in 9" :key="`v-${i}`" :x1="i * 10" :y1="0" :x2="i * 10" :y2="100" stroke="white" stroke-width="0.1" />
        </g>

        <!-- Length zones (background) -->
        <g opacity="0.15">
          <rect x="0" y="0" width="100" height="10" fill="#ff6b6b" />
          <text x="50" y="6" text-anchor="middle" font-size="3" fill="white">Yorker (0-10)</text>

          <rect x="0" y="10" width="100" height="20" fill="#feca57" />
          <text x="50" y="21" text-anchor="middle" font-size="3" fill="white">Full (10-30)</text>

          <rect x="0" y="30" width="100" height="30" fill="#48dbfb" />
          <text x="50" y="46" text-anchor="middle" font-size="3" fill="white">Good Length (30-60)</text>

          <rect x="0" y="60" width="100" height="25" fill="#1dd1a1" />
          <text x="50" y="73" text-anchor="middle" font-size="3" fill="white">Short (60-85)</text>

          <rect x="0" y="85" width="100" height="15" fill="#ee5a6f" />
          <text x="50" y="93" text-anchor="middle" font-size="3" fill="white">Bouncer (85-100)</text>
        </g>

        <!-- Line zones (vertical) -->
        <g opacity="0.1">
          <line x1="25" y1="0" x2="25" y2="100" stroke="white" stroke-width="0.3" />
          <line x1="40" y1="0" x2="40" y2="100" stroke="white" stroke-width="0.3" />
          <line x1="60" y1="0" x2="60" y2="100" stroke="white" stroke-width="0.3" />
          <line x1="75" y1="0" x2="75" y2="100" stroke="white" stroke-width="0.3" />
        </g>

        <!-- Stumps -->
        <g>
          <circle cx="50" cy="5" r="1" fill="yellow" stroke="orange" stroke-width="0.3" />
          <circle cx="50" cy="95" r="1" fill="yellow" stroke="orange" stroke-width="0.3" />
        </g>

        <!-- Creases -->
        <line x1="20" y1="10" x2="80" y2="10" stroke="white" stroke-width="0.3" opacity="0.5" />
        <line x1="20" y1="90" x2="80" y2="90" stroke="white" stroke-width="0.3" opacity="0.5" />

        <!-- Pitch map points -->
        <g v-for="(point, idx) in filteredPoints" :key="`point-${idx}`">
          <circle
            :cx="point.x_coordinate"
            :cy="point.y_coordinate"
            :r="hoveredPoint === idx ? 2 : 1.5"
            :fill="getPointColor(point)"
            :stroke="hoveredPoint === idx ? 'white' : getPointStroke(point)"
            stroke-width="0.4"
            :opacity="hoveredPoint === idx ? 1 : 0.8"
            class="pitch-point"
            @mouseenter="hoveredPoint = idx"
            @mouseleave="hoveredPoint = null"
          />
        </g>

        <!-- Tooltip -->
        <g v-if="hoveredPoint !== null && filteredPoints[hoveredPoint]">
          <rect
            :x="filteredPoints[hoveredPoint].x_coordinate + 3"
            :y="filteredPoints[hoveredPoint].y_coordinate - 8"
            width="30"
            height="15"
            fill="rgba(0, 0, 0, 0.9)"
            rx="1"
          />
          <text
            :x="filteredPoints[hoveredPoint].x_coordinate + 5"
            :y="filteredPoints[hoveredPoint].y_coordinate - 3"
            font-size="2.5"
            fill="white"
            font-weight="600"
          >
            {{ filteredPoints[hoveredPoint].length }}
          </text>
          <text
            :x="filteredPoints[hoveredPoint].x_coordinate + 5"
            :y="filteredPoints[hoveredPoint].y_coordinate + 1"
            font-size="2.5"
            fill="white"
          >
            {{ filteredPoints[hoveredPoint].line }}
          </text>
          <text
            :x="filteredPoints[hoveredPoint].x_coordinate + 5"
            :y="filteredPoints[hoveredPoint].y_coordinate + 5"
            font-size="2"
            fill="#aaa"
          >
            ({{ filteredPoints[hoveredPoint].x_coordinate.toFixed(1) }}, {{ filteredPoints[hoveredPoint].y_coordinate.toFixed(1) }})
          </text>
        </g>
      </svg>
    </div>

    <!-- Length distribution -->
    <div class="distribution-panel">
      <h4>Length Distribution</h4>
      <div class="distribution-bars">
        <div
          v-for="(count, length) in lengthDistribution"
          :key="length"
          class="bar-item"
        >
          <span class="bar-label">{{ length }}</span>
          <div class="bar-container">
            <div
              class="bar-fill"
              :style="{ width: `${(count / filteredPoints.length) * 100}%` }"
            ></div>
          </div>
          <span class="bar-count">{{ count }}</span>
        </div>
      </div>
    </div>

    <!-- Line distribution -->
    <div class="distribution-panel">
      <h4>Line Distribution</h4>
      <div class="distribution-bars">
        <div
          v-for="(count, line) in lineDistribution"
          :key="line"
          class="bar-item"
        >
          <span class="bar-label">{{ line }}</span>
          <div class="bar-container">
            <div
              class="bar-fill"
              :style="{ width: `${(count / filteredPoints.length) * 100}%` }"
            ></div>
          </div>
          <span class="bar-count">{{ count }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

interface PitchPoint {
  x_coordinate: number
  y_coordinate: number
  length: string
  line: string
  value: number
}

const props = defineProps<{
  sessionId: string
}>()

const pitchPoints = ref<PitchPoint[]>([])
const lengthFilter = ref('')
const lineFilter = ref('')
const hoveredPoint = ref<number | null>(null)

const filteredPoints = computed(() => {
  return pitchPoints.value.filter(point => {
    if (lengthFilter.value && point.length !== lengthFilter.value) return false
    if (lineFilter.value && point.line !== lineFilter.value) return false
    return true
  })
})

const averageLength = computed(() => {
  if (filteredPoints.value.length === 0) return 0
  const sum = filteredPoints.value.reduce((acc, p) => acc + p.y_coordinate, 0)
  return sum / filteredPoints.value.length
})

const averageLine = computed(() => {
  if (filteredPoints.value.length === 0) return 0
  const sum = filteredPoints.value.reduce((acc, p) => acc + p.x_coordinate, 0)
  return sum / filteredPoints.value.length
})

const lengthDistribution = computed(() => {
  const dist: Record<string, number> = {
    yorker: 0,
    full: 0,
    good_length: 0,
    short: 0,
    bouncer: 0
  }

  filteredPoints.value.forEach(point => {
    if (point.length in dist) {
      dist[point.length]++
    }
  })

  return dist
})

const lineDistribution = computed(() => {
  const dist: Record<string, number> = {
    wide_leg: 0,
    leg_stump: 0,
    middle: 0,
    off_stump: 0,
    wide_off: 0
  }

  filteredPoints.value.forEach(point => {
    if (point.line in dist) {
      dist[point.line]++
    }
  })

  return dist
})

function getPointColor(point: PitchPoint): string {
  const lengthColors: Record<string, string> = {
    yorker: '#ff6b6b',
    full: '#feca57',
    good_length: '#48dbfb',
    short: '#1dd1a1',
    bouncer: '#ee5a6f'
  }
  return lengthColors[point.length] || '#ffffff'
}

function getPointStroke(point: PitchPoint): string {
  const lengthStrokes: Record<string, string> = {
    yorker: '#d63031',
    full: '#fdcb6e',
    good_length: '#0984e3',
    short: '#00b894',
    bouncer: '#d63031'
  }
  return lengthStrokes[point.length] || '#cccccc'
}

async function loadPitchMap() {
  try {
    const response = await fetch(`/api/coaches/plus/sessions/${props.sessionId}/pitch-map`)

    if (!response.ok) {
      throw new Error('Failed to load pitch map')
    }

    const data = await response.json()
    pitchPoints.value = data.points || []
  } catch (err) {
    console.error('Failed to load pitch map:', err)
  }
}

onMounted(() => {
  loadPitchMap()
})
</script>

<style scoped>
.pitch-map-viewer {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.viewer-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.filter-controls {
  display: flex;
  gap: 8px;
}

.filter-select {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
  background: white;
  cursor: pointer;
}

.filter-select:focus {
  outline: none;
  border-color: #3b82f6;
}

.stats-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  background: #f9fafb;
  border-radius: 6px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #6b7280;
  text-transform: uppercase;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
}

.pitch-container {
  position: relative;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 16px;
}

.pitch-svg {
  width: 100%;
  height: auto;
  display: block;
}

.pitch-point {
  cursor: pointer;
  transition: all 0.2s;
}

.distribution-panel {
  margin-bottom: 16px;
}

.distribution-panel h4 {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 12px;
}

.distribution-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bar-item {
  display: grid;
  grid-template-columns: 100px 1fr 40px;
  align-items: center;
  gap: 12px;
}

.bar-label {
  font-size: 12px;
  color: #6b7280;
  text-transform: capitalize;
}

.bar-container {
  background: #e5e7eb;
  border-radius: 4px;
  height: 20px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #2563eb);
  transition: width 0.3s;
}

.bar-count {
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
  text-align: right;
}
</style>

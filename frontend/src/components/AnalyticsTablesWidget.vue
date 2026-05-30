<template>
  <div class="analytics-tables-widget">
    <div class="analytics-header">
      <div>
        <h3 class="analytics-title">Analytics Lab</h3>
        <p class="analytics-subtitle">Registry-selected match analysis with completeness-aware fallbacks.</p>
      </div>
      <div class="analytics-controls" role="tablist" aria-label="Select analytics chart">
        <button
          v-for="chart in chartTypes"
          :key="chart.id"
          class="chart-tab"
          :class="{ active: activeChart === chart.id }"
          :title="chart.description"
          :aria-selected="activeChart === chart.id"
          role="tab"
          @click="activeChart = chart.id"
        >
          {{ chart.label }}
        </button>
      </div>
    </div>

    <div class="analytics-filter-row">
      <label class="analytics-filter">
        <span class="analytics-filter__label">Innings</span>
        <select v-model="inningsFilter" class="analytics-select" aria-label="Select innings">
          <option value="all">All innings</option>
          <option
            v-for="innings in inningsFilterOptions"
            :key="`innings-option-${innings}`"
            :value="String(innings)"
            :disabled="!availableInningsSet.has(innings)"
          >
            Innings {{ innings }}
          </option>
        </select>
      </label>

      <label class="analytics-filter">
        <span class="analytics-filter__label">Color theme</span>
        <select v-model="colorTheme" class="analytics-select" aria-label="Select chart color theme">
          <option value="default">Default</option>
          <option value="high_contrast">High contrast</option>
          <option value="podcast_bright">Podcast bright</option>
        </select>
      </label>

      <label v-if="activeChart === 'manhattan'" class="analytics-filter">
        <span class="analytics-filter__label">Manhattan mode</span>
        <select v-model="manhattanViewMode" class="analytics-select" aria-label="Select Manhattan mode">
          <option value="over">Runs by over</option>
          <option value="delivery" :disabled="manhattanMode !== 'delivery_complete'">Runs by delivery</option>
        </select>
      </label>

      <label v-if="activeChart === 'scatter'" class="analytics-filter">
        <span class="analytics-filter__label">Scatter mode</span>
        <select v-model="scatterViewMode" class="analytics-select" aria-label="Select Scatter mode">
          <option
            v-for="option in scatterModeOptions"
            :key="option.value"
            :value="option.value"
            :disabled="option.disabled"
          >
            {{ option.label }}
          </option>
        </select>
      </label>
    </div>

    <div class="analytics-context" role="status" aria-live="polite">
      <div>
        <p class="analytics-context-label">Selected match</p>
        <h4 class="analytics-context-title">{{ displayMatchTitle }}</h4>
        <p class="analytics-context-meta">
          {{ displayMatchDate }} · {{ sourceLabel }} · {{ completenessLabel(displayCompleteness) }}
        </p>
      </div>
      <p v-if="result" class="analytics-context-result">{{ result }}</p>
    </div>

    <p v-if="statusMessage" class="analytics-status" :class="{ 'analytics-status--error': Boolean(error) }">
      {{ statusMessage }}
    </p>

    <div class="analytics-summary-grid">
      <article v-for="metric in summaryMetrics" :key="metric.label" class="analytics-summary-card">
        <p class="analytics-summary-label">{{ metric.label }}</p>
        <p class="analytics-summary-value">{{ metric.value }}</p>
        <p class="analytics-summary-note">{{ metric.note }}</p>
      </article>
    </div>

    <div class="chart-container">
      <div class="chart-info">
        <h4>{{ currentChartMeta.title }}</h4>
        <p>{{ currentChartMeta.description }}</p>
      </div>

      <div v-if="loading" class="analytics-state" role="status">Loading selected-match analytics…</div>
      <div v-else-if="currentChartMode === 'metadata_only'" class="analytics-state" role="status">
        This registry entry only has metadata. Import deliveries, phases, or innings totals to render this graph.
      </div>

      <template v-else-if="activeChart === 'manhattan'">
        <div class="analytics-chart-frame">
          <div class="analytics-chart-scale">
            <span>{{ chartMaxValue(manhattanBars) }}</span>
            <span>0</span>
          </div>
          <div class="analytics-bar-chart" aria-label="Manhattan plot">
            <div
              v-for="bar in manhattanBars"
              :key="bar.key"
              class="analytics-bar-chart__column"
              :title="bar.tooltip"
            >
              <span v-if="bar.wickets > 0" class="analytics-bar-chart__marker">W{{ bar.wickets }}</span>
              <div class="analytics-bar-chart__track">
                <div
                  class="analytics-bar-chart__bar"
                  :style="{
                    height: `${barHeight(bar.value, manhattanBars)}%`,
                    background: bar.color,
                  }"
                />
              </div>
              <span class="analytics-bar-chart__label">{{ bar.shortLabel }}</span>
            </div>
          </div>
        </div>
        <div class="analytics-legend">
          <div v-if="manhattanViewMode === 'delivery'" class="analytics-legend__item">
            <span class="analytics-legend__hint">Delivery mode plots runs ball-by-ball.</span>
          </div>
          <div v-else class="analytics-legend__item">
            <span class="analytics-legend__hint">Over mode plots total runs scored each over.</span>
          </div>
          <div class="analytics-legend__item">
            <span class="analytics-legend__hint">W markers indicate wickets in that period.</span>
          </div>
        </div>
        <p class="analytics-howto">
          How to read this: Manhattan shows runs in each period with wicket markers for collapse pressure.
        </p>
        <p class="analytics-fallback-note">{{ currentModeNote('manhattan') }}</p>
      </template>

      <template v-else-if="activeChart === 'worm'">
        <template v-if="wormSeries.length > 0">
          <div class="analytics-svg-frame">
            <svg class="analytics-svg" viewBox="0 0 640 240" aria-label="Worm chart">
              <g class="analytics-grid">
                <line v-for="i in 5" :key="`worm-h-${i}`" :x1="48" :y1="20 + i * 36" x2="612" :y2="20 + i * 36" />
                <line v-for="i in 5" :key="`worm-v-${i}`" :x1="48 + i * 112.8" y1="20" :x2="48 + i * 112.8" y2="200" />
              </g>

              <g class="analytics-axis-ticks">
                <text
                  v-for="tick in wormYAxisTicks"
                  :key="`worm-y-${tick.value}`"
                  x="42"
                  :y="tick.y + 4"
                  class="analytics-axis-tick"
                  text-anchor="end"
                >
                  {{ tick.label }}
                </text>
                <text
                  v-for="tick in wormXAxisTicks"
                  :key="`worm-x-${tick.key}`"
                  :x="tick.x"
                  y="216"
                  class="analytics-axis-tick"
                  text-anchor="middle"
                >
                  {{ tick.label }}
                </text>
              </g>

              <template v-for="series in wormSeries" :key="series.key">
                <polyline :points="series.path" class="analytics-line" :style="{ stroke: series.color }" />
                <circle
                  v-for="point in series.points"
                  :key="point.key"
                  :cx="point.x"
                  :cy="point.y"
                  r="4"
                  :fill="series.color"
                >
                  <title>{{ point.tooltip }}</title>
                </circle>
                <text
                  :x="series.finalLabelX"
                  :y="series.finalLabelY"
                  class="analytics-final-label"
                  text-anchor="start"
                >
                  {{ series.finalLabel }}
                </text>
              </template>

              <text x="48" y="14" class="analytics-axis-label">Cumulative runs</text>
              <text x="612" y="224" class="analytics-axis-label" text-anchor="end">{{ wormXAxisLabel }}</text>
            </svg>
          </div>

          <div class="analytics-legend">
            <div v-for="series in wormSeries" :key="series.key" class="analytics-legend__item">
              <span class="analytics-legend__swatch" :style="{ background: series.color }" />
              <span>{{ series.label }}</span>
            </div>
          </div>
          <p class="analytics-howto">
            How to read this: Worm tracks cumulative runs over time to compare control, pressure, and chase shape.
          </p>
        </template>
        <div v-else class="analytics-state" role="status">
          No cumulative progression is available for this match yet.
        </div>
        <p class="analytics-fallback-note">{{ currentModeNote('worm') }}</p>
      </template>

      <template v-else>
        <template v-if="scatterPoints.length > 0">
          <div class="analytics-svg-frame">
            <svg class="analytics-svg" viewBox="0 0 640 240" aria-label="Scatter plot">
              <g class="analytics-grid">
                <line v-for="i in 5" :key="`scatter-h-${i}`" :x1="48" :y1="20 + i * 36" x2="612" :y2="20 + i * 36" />
                <line v-for="i in 5" :key="`scatter-v-${i}`" :x1="48 + i * 112.8" y1="20" :x2="48 + i * 112.8" y2="200" />
              </g>

              <g class="analytics-axis-ticks">
                <text
                  v-for="tick in scatterYAxisTicks"
                  :key="`scatter-y-${tick.value}`"
                  x="42"
                  :y="tick.y + 4"
                  class="analytics-axis-tick"
                  text-anchor="end"
                >
                  {{ tick.label }}
                </text>
                <text
                  v-for="tick in scatterXAxisTicks"
                  :key="`scatter-x-${tick.value}`"
                  :x="tick.x"
                  y="216"
                  class="analytics-axis-tick"
                  text-anchor="middle"
                >
                  {{ tick.label }}
                </text>
              </g>

              <circle
                v-for="point in scatterPoints"
                :key="point.key"
                :cx="point.x"
                :cy="point.y"
                :r="point.radius"
                :fill="point.color"
                fill-opacity="0.82"
              >
                <title>{{ point.tooltip }}</title>
              </circle>

              <text x="48" y="14" class="analytics-axis-label">{{ scatterYAxisLabel }}</text>
              <text x="612" y="224" class="analytics-axis-label" text-anchor="end">{{ scatterXAxisLabel }}</text>
            </svg>
          </div>

          <div class="analytics-legend">
            <div v-for="item in scatterLegend" :key="item.label" class="analytics-legend__item">
              <span class="analytics-legend__swatch" :style="{ background: item.color }" />
              <span>{{ item.label }}</span>
            </div>
            <div class="analytics-legend__item">
              <span class="analytics-legend__hint">Larger points indicate higher wicket impact.</span>
            </div>
          </div>
          <p class="analytics-howto">
            How to read this: Scatter highlights scoring bursts and pressure clusters by selected axis mode.
          </p>
        </template>
        <div v-else class="analytics-state" role="status">
          No scatter points are available for this match yet.
        </div>
        <p class="analytics-fallback-note">{{ currentModeNote('scatter') }}</p>
      </template>
    </div>

    <section class="analytics-insights" aria-label="Deterministic match insights">
      <article v-for="insight in deterministicInsights" :key="insight.title" class="analytics-insight-card">
        <p class="analytics-insight-title">{{ insight.title }}</p>
        <p class="analytics-insight-value">{{ insight.value }}</p>
        <p class="analytics-summary-note">{{ insight.note }}</p>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import {
  getAnalystDeliveries,
  getMatchCaseStudy,
  type AnalystDeliveryRow,
  type AnalystRegistryEntry,
  type MatchCaseStudyResponse,
} from '@/services/api'
import type { PlayerProfile } from '@/types/player'

type AnalyticsChart = 'manhattan' | 'worm' | 'scatter'
type AnalyticsCompleteness = 'delivery_complete' | 'phase_level' | 'innings_totals' | 'metadata_only'
type InningsFilter = 'all' | `${number}`
type ColorTheme = 'default' | 'high_contrast' | 'podcast_bright'
type ManhattanViewMode = 'over' | 'delivery'
type ScatterViewMode = 'over_vs_runs' | 'run_rate_vs_wickets' | 'delivery_index_vs_runs'

interface SummaryMetric {
  label: string
  value: string
  note: string
}

interface ChartBar {
  key: string
  shortLabel: string
  value: number
  wickets: number
  tooltip: string
  color: string
}

interface WormPoint {
  key: string
  x: number
  y: number
  tooltip: string
}

interface WormSeries {
  key: string
  label: string
  color: string
  path: string
  points: WormPoint[]
  finalLabel: string
  finalLabelX: number
  finalLabelY: number
}

interface ScatterPoint {
  key: string
  x: number
  y: number
  xValue: number
  yValue: number
  radius: number
  tooltip: string
  color: string
}

interface DeliveryBucket {
  key: string
  innings: number
  over: number
  label: string
  shortLabel: string
  runs: number
  wickets: number
  legalBalls: number
}

interface ScatterLegendItem {
  label: string
  color: string
}

interface InsightCard {
  title: string
  value: string
  note: string
}

interface PhaseBucket {
  key: string
  label: string
  runs: number
  wickets: number
  overs: number
}

interface InningsBucket {
  key: string
  innings: number
  label: string
  runs: number
  wickets: number
  overs: number | null
}

const props = defineProps<{
  profile: PlayerProfile | null
  matchId: string
  matchSource?: 'historical' | 'live'
  matchTitle?: string | null
  matchDate?: string | null
  result?: string | null
  dataCompleteness?: string | null
  registryEntry?: AnalystRegistryEntry | null
}>()

const chartTypes = [
  { id: 'manhattan' as const, label: '📊 Manhattan', description: 'Runs by delivery/over with fallbacks' },
  { id: 'worm' as const, label: '🐛 Worm', description: 'Cumulative progression' },
  { id: 'scatter' as const, label: '⚡ Scatter', description: 'Performance scatter analysis' },
]

const activeChart = ref<AnalyticsChart>('manhattan')
const inningsFilter = ref<InningsFilter>('all')
const colorTheme = ref<ColorTheme>('default')
const manhattanViewMode = ref<ManhattanViewMode>('over')
const scatterViewMode = ref<ScatterViewMode>('over_vs_runs')
const loading = ref(false)
const error = ref<string | null>(null)
const deliveries = ref<AnalystDeliveryRow[]>([])
const deliveryCompleteness = ref<AnalyticsCompleteness>('metadata_only')
const caseStudy = ref<MatchCaseStudyResponse | null>(null)
const isTestMultiDay = computed(() => caseStudy.value?.analysis_mode === 'test_multi_day')

const displayMatchTitle = computed(() => props.matchTitle || props.registryEntry?.match_title || 'Selected match')
const displayMatchDate = computed(() => props.matchDate || props.registryEntry?.match_date || 'Date unavailable')
const result = computed(() => props.result || props.registryEntry?.result || null)
const sourceLabel = computed(() => (props.matchSource === 'live' ? 'Live / scored' : 'Historical import'))

function normalizeCompleteness(value: string | null | undefined): AnalyticsCompleteness {
  if (value === 'delivery_complete' || value === 'phase_level' || value === 'innings_totals') {
    return value
  }
  return 'metadata_only'
}

function completenessLabel(value: AnalyticsCompleteness): string {
  return value.replace(/_/g, ' ')
}

function phaseOvers(startOver?: number | null, endOver?: number | null): number {
  if (typeof startOver !== 'number' || typeof endOver !== 'number' || endOver < startOver) return 0
  return endOver - startOver + 1
}

function oversToBalls(overs: number | null | undefined): number | null {
  if (typeof overs !== 'number' || Number.isNaN(overs)) return null
  const wholeOvers = Math.trunc(overs)
  const partialBalls = Math.round((overs - wholeOvers) * 10)
  return wholeOvers * 6 + Math.max(partialBalls, 0)
}

const themePalette = computed(() => {
  if (colorTheme.value === 'high_contrast') {
    return {
      innings1: '#22d3ee',
      innings2: '#f97316',
      phase: '#facc15',
      neutral: '#c084fc',
    }
  }
  if (colorTheme.value === 'podcast_bright') {
    return {
      innings1: '#60a5fa',
      innings2: '#f472b6',
      phase: '#34d399',
      neutral: '#f59e0b',
    }
  }
  return {
    innings1: '#38bdf8',
    innings2: '#34d399',
    phase: '#f59e0b',
    neutral: '#a78bfa',
  }
})

function inningsColor(innings: number): string {
  if (innings === 2) return themePalette.value.innings2
  if (innings === 3) return themePalette.value.phase
  if (innings === 4) return themePalette.value.neutral
  return themePalette.value.innings1
}

function phaseColor(label: string): string {
  const normalized = label.toLowerCase()
  if (normalized.includes('power')) return themePalette.value.phase
  if (normalized.includes('death')) return themePalette.value.neutral
  return '#2dd4bf'
}

function isLegalDelivery(row: AnalystDeliveryRow): boolean {
  const extraType = (row.extra_type || '').toLowerCase()
  return !['wd', 'wide', 'nb', 'noball', 'no_ball', 'no ball'].includes(extraType)
}

const inningsTotals = computed<InningsBucket[]>(() =>
  (caseStudy.value?.match.innings || []).map((innings, index) => ({
    key: `innings-${index + 1}`,
    innings: index + 1,
    label: innings.team || `Innings ${index + 1}`,
    runs: innings.runs ?? 0,
    wickets: innings.wickets ?? 0,
    overs: typeof innings.overs === 'number' ? innings.overs : null,
  })),
)

const availableInningsSet = computed(() => {
  const inningsSet = new Set<number>()
  deliveries.value.forEach((row) => {
    if (typeof row.innings === 'number' && row.innings > 0) inningsSet.add(row.innings)
  })
  inningsTotals.value.forEach((innings) => {
    if (innings.innings > 0) inningsSet.add(innings.innings)
  })
  return inningsSet
})

const inningsFilterOptions = computed(() =>
  [...availableInningsSet.value].sort((a, b) => a - b)
)

const selectedInnings = computed<number | null>(() => {
  if (inningsFilter.value !== 'all') {
    const parsed = Number.parseInt(inningsFilter.value, 10)
    if (Number.isFinite(parsed) && parsed > 0) return parsed
  }
  return null
})

const filteredInningsTotals = computed<InningsBucket[]>(() => {
  if (!selectedInnings.value) return inningsTotals.value
  return inningsTotals.value.filter(innings => innings.innings === selectedInnings.value)
})

const phaseBuckets = computed<PhaseBucket[]>(() => {
  if (isTestMultiDay.value) return []
  return (caseStudy.value?.phases || [])
    .filter(phase => (phase.runs ?? 0) > 0 || (phase.wickets ?? 0) > 0)
    .map(phase => ({
      key: phase.id,
      label: phase.label,
      runs: phase.runs ?? 0,
      wickets: phase.wickets ?? 0,
      overs: phase.run_rate && phase.run_rate > 0
        ? Number((phase.runs / phase.run_rate).toFixed(2))
        : phaseOvers(phase.start_over, phase.end_over),
    }))
})

const filteredDeliveries = computed<AnalystDeliveryRow[]>(() => {
  if (!selectedInnings.value) return deliveries.value
  return deliveries.value.filter(row => row.innings === selectedInnings.value)
})

const deliveryBuckets = computed<DeliveryBucket[]>(() => {
  const grouped = new Map<string, DeliveryBucket>()
  const rows = [...filteredDeliveries.value].sort((a, b) => {
    const inningsDelta = (a.innings ?? 0) - (b.innings ?? 0)
    if (inningsDelta !== 0) return inningsDelta
    const overDelta = (a.over_number ?? 0) - (b.over_number ?? 0)
    if (overDelta !== 0) return overDelta
    return (a.ball_number ?? 0) - (b.ball_number ?? 0)
  })

  rows.forEach((row) => {
    const innings = row.innings ?? 1
    const over = row.over_number ?? 0
    const key = `${innings}-${over}`
    const label = `Innings ${innings} · Over ${over || 1}`
    const shortLabel = `I${innings} O${over || 1}`
    if (!grouped.has(key)) {
      grouped.set(key, {
        key,
        innings,
        over: over || 1,
        label,
        shortLabel,
        runs: 0,
        wickets: 0,
        legalBalls: 0,
      })
    }
    const bucket = grouped.get(key)!
    bucket.runs += row.total_runs ?? 0
    bucket.wickets += row.wicket ? 1 : 0
    if (isLegalDelivery(row)) bucket.legalBalls += 1
  })

  return [...grouped.values()]
})

const availableCompleteness = computed<AnalyticsCompleteness>(() => {
  if (deliveryBuckets.value.length > 0) return 'delivery_complete'
  if (phaseBuckets.value.length > 0) return 'phase_level'
  if (filteredInningsTotals.value.length > 0) return 'innings_totals'
  return 'metadata_only'
})

const displayCompleteness = computed<AnalyticsCompleteness>(() => {
  const declared = normalizeCompleteness(
    props.dataCompleteness || props.registryEntry?.data_completeness || deliveryCompleteness.value,
  )
  const rank: Record<AnalyticsCompleteness, number> = {
    metadata_only: 0,
    innings_totals: 1,
    phase_level: 2,
    delivery_complete: 3,
  }
  return rank[availableCompleteness.value] >= rank[declared] ? availableCompleteness.value : declared
})

const summaryTotals = computed(() => {
  if (deliveryBuckets.value.length > 0) {
    const totalRuns = deliveryBuckets.value.reduce((sum, bucket) => sum + bucket.runs, 0)
    const wickets = deliveryBuckets.value.reduce((sum, bucket) => sum + bucket.wickets, 0)
    const legalBalls = deliveryBuckets.value.reduce((sum, bucket) => sum + bucket.legalBalls, 0)
    const deliveriesCount = filteredDeliveries.value.length
    return {
      totalRuns,
      wickets,
      legalBalls,
      deliveriesCount,
      source: 'From delivery records',
    }
  }

  if (phaseBuckets.value.length > 0) {
    const totalRuns = phaseBuckets.value.reduce((sum, phase) => sum + phase.runs, 0)
    const wickets = phaseBuckets.value.reduce((sum, phase) => sum + phase.wickets, 0)
    const legalBalls = phaseBuckets.value.reduce((sum, phase) => sum + Math.round(phase.overs * 6), 0)
    return {
      totalRuns,
      wickets,
      legalBalls,
      deliveriesCount: legalBalls,
      source: 'Derived from phase summaries',
    }
  }

  if (filteredInningsTotals.value.length > 0) {
    const totalRuns = filteredInningsTotals.value.reduce((sum, innings) => sum + innings.runs, 0)
    const wickets = filteredInningsTotals.value.reduce((sum, innings) => sum + innings.wickets, 0)
    const legalBalls = filteredInningsTotals.value.reduce((sum, innings) => sum + (oversToBalls(innings.overs) ?? 0), 0)
    return {
      totalRuns,
      wickets,
      legalBalls,
      deliveriesCount: legalBalls,
      source: 'Derived from innings totals',
    }
  }

  return {
    totalRuns: null,
    wickets: null,
    legalBalls: null,
    deliveriesCount: null,
    source: 'Unavailable',
  }
})

const runRate = computed<number | null>(() => {
  const totalRuns = summaryTotals.value.totalRuns
  const legalBalls = summaryTotals.value.legalBalls
  if (typeof totalRuns !== 'number' || typeof legalBalls !== 'number' || legalBalls <= 0) return null
  return (totalRuns * 6) / legalBalls
})

const summaryMetrics = computed<SummaryMetric[]>(() => [
  {
    label: 'Total Runs',
    value: typeof summaryTotals.value.totalRuns === 'number' ? String(summaryTotals.value.totalRuns) : 'Unavailable',
    note: summaryTotals.value.source,
  },
  {
    label: 'Deliveries',
    value: typeof summaryTotals.value.deliveriesCount === 'number' ? String(summaryTotals.value.deliveriesCount) : 'Unavailable',
    note: deliveryBuckets.value.length > 0 ? 'Recorded deliveries' : summaryTotals.value.source,
  },
  {
    label: 'Run Rate',
    value: typeof runRate.value === 'number' ? runRate.value.toFixed(2) : 'Unavailable',
    note: typeof runRate.value === 'number' ? summaryTotals.value.source : 'Not enough overs data',
  },
  {
    label: 'Wickets',
    value: typeof summaryTotals.value.wickets === 'number' ? String(summaryTotals.value.wickets) : 'Unavailable',
    note: summaryTotals.value.source,
  },
])

const manhattanMode = computed<AnalyticsCompleteness>(() => {
  if (deliveryBuckets.value.length > 0) return 'delivery_complete'
  if (phaseBuckets.value.length > 0) return 'phase_level'
  if (filteredInningsTotals.value.length > 0) return 'innings_totals'
  return 'metadata_only'
})

const wormMode = computed<AnalyticsCompleteness>(() => manhattanMode.value)
const scatterMode = computed<AnalyticsCompleteness>(() => manhattanMode.value)

const manhattanBars = computed<ChartBar[]>(() => {
  if (manhattanMode.value === 'delivery_complete') {
    if (manhattanViewMode.value === 'delivery') {
      return filteredDeliveries.value
        .slice()
        .sort((a, b) => {
          const inningsDelta = (a.innings ?? 0) - (b.innings ?? 0)
          if (inningsDelta !== 0) return inningsDelta
          const overDelta = (a.over_number ?? 0) - (b.over_number ?? 0)
          if (overDelta !== 0) return overDelta
          return (a.ball_number ?? 0) - (b.ball_number ?? 0)
        })
        .map((row, index) => {
          const innings = row.innings ?? 1
          const over = row.over_number ?? 1
          const ball = row.ball_number ?? 1
          return {
            key: `delivery-${innings}-${over}-${ball}-${index}`,
            shortLabel: `${over}.${ball}`,
            value: row.total_runs ?? 0,
            wickets: row.wicket ? 1 : 0,
            tooltip: `Innings ${innings} · Over ${over}.${ball}: ${row.total_runs ?? 0} runs, wicket ${row.wicket ? 'yes' : 'no'}`,
            color: inningsColor(innings),
          }
        })
    }

    return deliveryBuckets.value.map((bucket, index) => ({
      key: bucket.key,
      shortLabel: bucket.shortLabel,
      value: bucket.runs,
      wickets: bucket.wickets,
      tooltip: `${bucket.label}: ${bucket.runs} runs, ${bucket.wickets} wickets, RR ${bucket.legalBalls > 0 ? ((bucket.runs * 6) / bucket.legalBalls).toFixed(2) : 'n/a'}`,
      color: inningsColor(bucket.innings || index + 1),
    }))
  }

  if (manhattanMode.value === 'phase_level') {
    return phaseBuckets.value.map(phase => ({
      key: phase.key,
      shortLabel: phase.label,
      value: phase.runs,
      wickets: phase.wickets,
      tooltip: `${phase.label}: ${phase.runs} runs, ${phase.wickets} wickets`,
      color: phaseColor(phase.label),
    }))
  }

  if (manhattanMode.value === 'innings_totals') {
    return filteredInningsTotals.value.map((innings, index) => ({
      key: innings.key,
      shortLabel: `Inn ${innings.innings}`,
      value: innings.runs,
      wickets: innings.wickets,
      tooltip: `${innings.label}: ${innings.runs}/${innings.wickets}, RR ${innings.overs && innings.overs > 0 ? (innings.runs / innings.overs).toFixed(2) : 'n/a'}`,
      color: inningsColor(innings.innings || index + 1),
    }))
  }

  return []
})

const wormSeries = computed<WormSeries[]>(() => {
  if (wormMode.value === 'delivery_complete') {
    const seriesMap = new Map<number, DeliveryBucket[]>()
    deliveryBuckets.value.forEach((bucket) => {
      if (!seriesMap.has(bucket.innings)) seriesMap.set(bucket.innings, [])
      seriesMap.get(bucket.innings)!.push(bucket)
    })

    const maxRuns = Math.max(1, ...[...seriesMap.values()].map(series => series.reduce((sum, bucket) => sum + bucket.runs, 0)))
    const maxOver = Math.max(1, ...deliveryBuckets.value.map(bucket => bucket.over))

    return [...seriesMap.entries()].map(([innings, buckets]) => {
      let cumulativeRuns = 0
      let cumulativeWickets = 0
      const points = buckets.map((bucket, index) => {
        cumulativeRuns += bucket.runs
        cumulativeWickets += bucket.wickets
        const x = 48 + (bucket.over / maxOver) * 564
        const y = 200 - (cumulativeRuns / maxRuns) * 160
        return {
          key: `${bucket.key}-worm`,
          x,
          y,
          tooltip: `${bucket.label}: ${cumulativeRuns} cumulative runs, ${cumulativeWickets} wickets`,
        }
      })
      const lastPoint = points[points.length - 1]
      const finalRuns = buckets.reduce((sum, bucket) => sum + bucket.runs, 0)
      const finalWickets = buckets.reduce((sum, bucket) => sum + bucket.wickets, 0)

      return {
        key: `innings-${innings}`,
        label: `Innings ${innings}`,
        color: inningsColor(innings),
        path: points.map(point => `${point.x},${point.y}`).join(' '),
        points,
        finalLabel: `${finalRuns}/${finalWickets}`,
        finalLabelX: Math.min(610, (lastPoint?.x ?? 600) + 6),
        finalLabelY: Math.max(16, (lastPoint?.y ?? 30) - 6),
      }
    })
  }

  if (wormMode.value === 'phase_level') {
    let cumulativeRuns = 0
    const maxRuns = Math.max(1, phaseBuckets.value.reduce((sum, phase) => sum + phase.runs, 0))
    const points = phaseBuckets.value.map((phase, index) => {
      cumulativeRuns += phase.runs
      const denominator = Math.max(phaseBuckets.value.length - 1, 1)
      const x = 48 + (index / denominator) * 564
      const y = 200 - (cumulativeRuns / maxRuns) * 160
      return {
        key: `${phase.key}-worm`,
        x,
        y,
        tooltip: `${phase.label}: ${cumulativeRuns} cumulative runs`,
      }
    })
    return [{
      key: 'phases',
      label: 'Phase progression',
      color: themePalette.value.phase,
      path: points.map(point => `${point.x},${point.y}`).join(' '),
      points,
      finalLabel: `${cumulativeRuns} runs`,
      finalLabelX: 606,
      finalLabelY: points.length ? Math.max(16, points[points.length - 1].y - 6) : 24,
    }]
  }

  if (wormMode.value === 'innings_totals') {
    let cumulativeRuns = 0
    const maxRuns = Math.max(1, filteredInningsTotals.value.reduce((sum, innings) => sum + innings.runs, 0))
    const points = filteredInningsTotals.value.map((innings, index) => {
      cumulativeRuns += innings.runs
      const denominator = Math.max(filteredInningsTotals.value.length - 1, 1)
      const x = 48 + (index / denominator) * 564
      const y = 200 - (cumulativeRuns / maxRuns) * 160
      return {
        key: `${innings.key}-worm`,
        x,
        y,
        tooltip: `${innings.label}: ${cumulativeRuns} cumulative runs`,
      }
    })
    return [{
      key: 'innings',
      label: 'Innings totals progression',
      color: themePalette.value.neutral,
      path: points.map(point => `${point.x},${point.y}`).join(' '),
      points,
      finalLabel: `${cumulativeRuns} runs`,
      finalLabelX: 606,
      finalLabelY: points.length ? Math.max(16, points[points.length - 1].y - 6) : 24,
    }]
  }

  return []
})

const wormXAxisLabel = computed(() => {
  if (wormMode.value === 'delivery_complete') return 'Overs'
  if (wormMode.value === 'phase_level') return 'Phases'
  if (wormMode.value === 'innings_totals') return 'Innings'
  return 'Unavailable'
})

const wormMaxYValue = computed(() => {
  if (wormMode.value === 'delivery_complete') {
    const bySeries = new Map<number, number>()
    deliveryBuckets.value.forEach((bucket) => {
      bySeries.set(bucket.innings, (bySeries.get(bucket.innings) || 0) + bucket.runs)
    })
    return Math.max(1, ...bySeries.values())
  }
  if (wormMode.value === 'phase_level') return Math.max(1, phaseBuckets.value.reduce((sum, phase) => sum + phase.runs, 0))
  if (wormMode.value === 'innings_totals') return Math.max(1, filteredInningsTotals.value.reduce((sum, innings) => sum + innings.runs, 0))
  return 1
})

function buildTicks(max: number, count = 4): number[] {
  return Array.from({ length: count + 1 }, (_, index) => (max / count) * index)
}

const wormYAxisTicks = computed(() =>
  buildTicks(wormMaxYValue.value).map((value) => ({
    value,
    label: Math.round(value).toString(),
    y: 200 - (value / wormMaxYValue.value) * 160,
  })),
)

const wormXAxisTicks = computed(() => {
  if (wormMode.value === 'delivery_complete') {
    const maxOver = Math.max(1, ...deliveryBuckets.value.map(bucket => bucket.over))
    return buildTicks(maxOver).map((value, index) => ({
      key: `over-${index}`,
      label: `Ov ${Math.round(value)}`,
      x: 48 + (value / maxOver) * 564,
    }))
  }
  if (wormMode.value === 'phase_level') {
    return phaseBuckets.value.map((phase, index) => ({
      key: phase.key,
      label: phase.label,
      x: 48 + (index / Math.max(phaseBuckets.value.length - 1, 1)) * 564,
    }))
  }
  if (wormMode.value === 'innings_totals') {
    return filteredInningsTotals.value.map((innings, index) => ({
      key: innings.key,
      label: `Inn ${innings.innings}`,
      x: 48 + (index / Math.max(filteredInningsTotals.value.length - 1, 1)) * 564,
    }))
  }
  return []
})

const scatterModeOptions = computed(() => [
  {
    value: 'over_vs_runs' as const,
    label: 'Over vs runs',
    disabled: scatterMode.value !== 'delivery_complete',
  },
  {
    value: 'run_rate_vs_wickets' as const,
    label: 'Run rate vs wickets',
    disabled: scatterMode.value === 'metadata_only',
  },
  {
    value: 'delivery_index_vs_runs' as const,
    label: 'Delivery index vs runs',
    disabled: scatterMode.value !== 'delivery_complete',
  },
])

const scatterPoints = computed<ScatterPoint[]>(() => {
  if (scatterMode.value === 'metadata_only') return []

  if (scatterViewMode.value === 'delivery_index_vs_runs' && scatterMode.value === 'delivery_complete') {
    const maxRuns = Math.max(1, ...filteredDeliveries.value.map(row => row.total_runs ?? 0))
    const maxIndex = Math.max(1, filteredDeliveries.value.length)
    return filteredDeliveries.value.map((row, index) => {
      const innings = row.innings ?? 1
      const over = row.over_number ?? 1
      const ball = row.ball_number ?? 1
      const runs = row.total_runs ?? 0
      return {
        key: `scatter-delivery-${innings}-${over}-${ball}-${index}`,
        x: 48 + ((index + 1) / maxIndex) * 540,
        y: 200 - (runs / maxRuns) * 160,
        xValue: index + 1,
        yValue: runs,
        radius: row.wicket ? 9 : 6,
        tooltip: `Innings ${innings} · Over ${over}.${ball}: ${runs} runs${row.wicket ? ', wicket' : ''}`,
        color: inningsColor(innings),
      }
    })
  }

  if (scatterViewMode.value === 'over_vs_runs' && scatterMode.value === 'delivery_complete') {
    const maxRuns = Math.max(1, ...deliveryBuckets.value.map(bucket => bucket.runs))
    const maxOver = Math.max(1, ...deliveryBuckets.value.map(bucket => bucket.over))
    return deliveryBuckets.value.map((bucket) => ({
      key: `${bucket.key}-scatter-over`,
      x: 48 + (bucket.over / maxOver) * 540,
      y: 200 - (bucket.runs / maxRuns) * 160,
      xValue: bucket.over,
      yValue: bucket.runs,
      radius: 6 + bucket.wickets * 2,
      tooltip: `${bucket.label}: ${bucket.runs} runs, ${bucket.wickets} wickets`,
      color: inningsColor(bucket.innings),
    }))
  }

  if (scatterMode.value === 'delivery_complete') {
    const overStats = deliveryBuckets.value.map(bucket => ({
      key: bucket.key,
      innings: bucket.innings,
      label: bucket.label,
      runRate: bucket.legalBalls > 0 ? (bucket.runs * 6) / bucket.legalBalls : 0,
      wickets: bucket.wickets,
    }))
    const maxRunRate = Math.max(1, ...overStats.map(stat => stat.runRate))
    const maxWickets = Math.max(1, ...overStats.map(stat => stat.wickets))
    return overStats.map((stat) => ({
      key: `${stat.key}-scatter-rr`,
      x: 48 + (stat.runRate / maxRunRate) * 540,
      y: 200 - ((stat.wickets || 0) / maxWickets) * 160,
      xValue: stat.runRate,
      yValue: stat.wickets,
      radius: 7,
      tooltip: `${stat.label}: RR ${stat.runRate.toFixed(2)}, ${stat.wickets} wickets`,
      color: inningsColor(stat.innings),
    }))
  }

  if (scatterMode.value === 'phase_level') {
    const maxRunRate = Math.max(1, ...phaseBuckets.value.map(phase => (phase.overs > 0 ? phase.runs / phase.overs : 0)))
    const maxWickets = Math.max(1, ...phaseBuckets.value.map(phase => phase.wickets))
    return phaseBuckets.value.map((phase) => {
      const runRateValue = phase.overs > 0 ? phase.runs / phase.overs : 0
      return {
        key: `${phase.key}-scatter`,
        x: 48 + (runRateValue / maxRunRate) * 540,
        y: 200 - ((phase.wickets || 0) / maxWickets) * 160,
        xValue: runRateValue,
        yValue: phase.wickets,
        radius: 7,
        tooltip: `${phase.label}: ${runRateValue.toFixed(2)} run rate, ${phase.wickets} wickets`,
        color: themePalette.value.phase,
      }
    })
  }

  const maxRunRate = Math.max(
    1,
    ...filteredInningsTotals.value.map(innings => (innings.overs && innings.overs > 0 ? innings.runs / innings.overs : 0)),
  )
  const maxWickets = Math.max(1, ...filteredInningsTotals.value.map(innings => innings.wickets))
  return filteredInningsTotals.value.map((innings, index) => {
    const runRateValue = innings.overs && innings.overs > 0 ? innings.runs / innings.overs : 0
    return {
      key: `${innings.key}-scatter`,
      x: 48 + (runRateValue / maxRunRate) * 540,
      y: 200 - ((innings.wickets || 0) / maxWickets) * 160,
      xValue: runRateValue,
      yValue: innings.wickets,
      radius: 7,
      tooltip: `${innings.label}: RR ${runRateValue.toFixed(2)}, ${innings.wickets} wickets`,
      color: inningsColor(innings.innings || index + 1),
    }
  })
})

const scatterXAxisLabel = computed(() => {
  if (scatterViewMode.value === 'delivery_index_vs_runs') return 'Delivery index'
  if (scatterViewMode.value === 'over_vs_runs') return 'Over'
  return 'Run rate'
})

const scatterYAxisLabel = computed(() => {
  if (scatterViewMode.value === 'delivery_index_vs_runs' || scatterViewMode.value === 'over_vs_runs') return 'Runs'
  return 'Wickets'
})

const scatterLegend = computed<ScatterLegendItem[]>(() => {
  if (scatterMode.value === 'phase_level') {
    return [{ label: 'Phase points', color: themePalette.value.phase }]
  }
  if (scatterMode.value === 'innings_totals') {
    return filteredInningsTotals.value.map((innings) => ({
      label: `Innings ${innings.innings}`,
      color: inningsColor(innings.innings),
    }))
  }
  return [
    { label: 'Innings 1', color: inningsColor(1) },
    { label: 'Innings 2', color: inningsColor(2) },
  ]
})

const scatterAxisExtents = computed(() => {
  const maxX = Math.max(1, ...scatterPoints.value.map(point => point.xValue))
  const maxY = Math.max(1, ...scatterPoints.value.map(point => point.yValue))
  return { maxX, maxY }
})

const scatterXAxisTicks = computed(() =>
  buildTicks(scatterAxisExtents.value.maxX).map((value) => ({
    value,
    label: Number.isInteger(value) ? String(value) : value.toFixed(1),
    x: 48 + (value / scatterAxisExtents.value.maxX) * 540,
  })),
)

const scatterYAxisTicks = computed(() =>
  buildTicks(scatterAxisExtents.value.maxY).map((value) => ({
    value,
    label: Number.isInteger(value) ? String(value) : value.toFixed(1),
    y: 200 - (value / scatterAxisExtents.value.maxY) * 160,
  })),
)

const currentChartMode = computed<AnalyticsCompleteness>(() => {
  if (activeChart.value === 'worm') return wormMode.value
  if (activeChart.value === 'scatter') return scatterMode.value
  return manhattanMode.value
})

const currentChartMeta = computed(() => {
  if (activeChart.value === 'worm') {
    return {
      title: 'Worm Chart',
      description: 'Cumulative run progression from deliveries, phases, or innings totals.',
    }
  }
  if (activeChart.value === 'scatter') {
    return {
      title: 'Performance Scatter',
      description: 'Runs, run rate, and wickets rendered from the best available selected-match data.',
    }
  }
  return {
    title: 'Manhattan Plot',
    description: 'Runs by over, phase, or innings total depending on selected-match completeness.',
  }
})

const statusMessage = computed(() => {
  if (loading.value) return 'Loading deterministic match data…'
  if (error.value && availableCompleteness.value !== 'metadata_only') {
    return `${error.value} Showing the best available fallback from selected-match summary data.`
  }
  if (error.value) return error.value
  if (displayCompleteness.value !== availableCompleteness.value) {
    return `Registry marked this match as ${completenessLabel(displayCompleteness.value)}; rendering ${completenessLabel(availableCompleteness.value)} data that is currently available.`
  }
  return null
})

function currentModeNote(chart: AnalyticsChart): string {
  const mode = chart === 'worm' ? wormMode.value : chart === 'scatter' ? scatterMode.value : manhattanMode.value
  const inningsNote = selectedInnings.value ? ` for innings ${selectedInnings.value}` : ''
  if (mode === 'delivery_complete') {
    if (chart === 'manhattan' && manhattanViewMode.value === 'delivery') {
      return `Using delivery-by-delivery records${inningsNote} for full graph rendering.`
    }
    return `Using over-level delivery records${inningsNote} for full graph rendering.`
  }
  if (mode === 'phase_level') return `Using phase summaries${inningsNote} because delivery records are unavailable.`
  if (mode === 'innings_totals') return `Using innings totals${inningsNote} because only innings-level scoring is available.`
  return 'Insufficient data for graph rendering.'
}

const deterministicInsights = computed<InsightCard[]>(() => {
  const insights: InsightCard[] = []
  if (manhattanBars.value.length > 0) {
    const best = [...manhattanBars.value].sort((a, b) => b.value - a.value)[0]
    const slowest = [...manhattanBars.value].sort((a, b) => a.value - b.value)[0]
    const wicketHeavy = [...manhattanBars.value].sort((a, b) => b.wickets - a.wickets)[0]

    insights.push({
      title: 'Best scoring period',
      value: `${best.shortLabel} · ${best.value} runs`,
      note: 'Derived from visible Manhattan bars.',
    })
    insights.push({
      title: 'Slowest scoring period',
      value: `${slowest.shortLabel} · ${slowest.value} runs`,
      note: 'Derived from visible Manhattan bars.',
    })
    insights.push({
      title: 'Wicket-heavy period',
      value: wicketHeavy.wickets > 0 ? `${wicketHeavy.shortLabel} · ${wicketHeavy.wickets} wickets` : 'No wickets recorded',
      note: 'Derived from period wicket markers.',
    })
  } else {
    insights.push({
      title: 'Best scoring period',
      value: 'Unavailable',
      note: 'Insufficient data for deterministic period ranking.',
    })
  }

  if (deliveryBuckets.value.length >= 2) {
    let accelerationLabel = 'Unavailable'
    let maxLift = Number.NEGATIVE_INFINITY
    for (let index = 1; index < deliveryBuckets.value.length; index += 1) {
      const prev = deliveryBuckets.value[index - 1]
      const current = deliveryBuckets.value[index]
      const lift = current.runs - prev.runs
      if (lift > maxLift) {
        maxLift = lift
        accelerationLabel = `${current.shortLabel} · Δ ${lift >= 0 ? '+' : ''}${lift}`
      }
    }
    insights.push({
      title: 'Acceleration period',
      value: accelerationLabel,
      note: 'Largest over-to-over run jump in selected innings filter.',
    })
  } else {
    insights.push({
      title: 'Acceleration period',
      value: 'Unavailable',
      note: 'Need at least two over buckets.',
    })
  }

  const inningsOne = deliveryBuckets.value.filter(bucket => bucket.innings === 1)
  const inningsTwo = deliveryBuckets.value.filter(bucket => bucket.innings === 2)
  if (!selectedInnings.value && inningsOne.length > 0 && inningsTwo.length > 0) {
    const cumulativeByOver = new Map<number, { first: number; second: number }>()
    let firstTotal = 0
    inningsOne.forEach((bucket) => {
      firstTotal += bucket.runs
      cumulativeByOver.set(bucket.over, { first: firstTotal, second: cumulativeByOver.get(bucket.over)?.second ?? 0 })
    })
    let secondTotal = 0
    inningsTwo.forEach((bucket) => {
      secondTotal += bucket.runs
      const existing = cumulativeByOver.get(bucket.over)
      cumulativeByOver.set(bucket.over, { first: existing?.first ?? firstTotal, second: secondTotal })
    })
    const turningOver = [...cumulativeByOver.entries()]
      .sort((a, b) => a[0] - b[0])
      .find(([, totals]) => totals.second >= totals.first)
    insights.push({
      title: 'Chase turning point',
      value: turningOver ? `Over ${turningOver[0]} · chase caught up` : 'No catch-up point in available overs',
      note: 'Compares cumulative innings 2 vs innings 1 over progression.',
    })
  } else {
    insights.push({
      title: 'Chase turning point',
      value: 'Unavailable',
      note: 'Needs both innings in over-level data with all-innings view.',
    })
  }

  return insights
})

function chartMaxValue(bars: ChartBar[]): number {
  return Math.max(1, ...bars.map(bar => bar.value))
}

function barHeight(value: number, bars: ChartBar[]): number {
  return Math.max(6, (value / chartMaxValue(bars)) * 100)
}

async function loadAnalytics() {
  if (!props.matchId) {
    deliveries.value = []
    caseStudy.value = null
    deliveryCompleteness.value = 'metadata_only'
    error.value = null
    return
  }

  loading.value = true
  error.value = null

  const [deliveriesResult, caseStudyResult] = await Promise.allSettled([
    getAnalystDeliveries(props.matchId),
    getMatchCaseStudy(props.matchId),
  ])

  if (deliveriesResult.status === 'fulfilled') {
    deliveries.value = deliveriesResult.value.items || []
    deliveryCompleteness.value = normalizeCompleteness(deliveriesResult.value.data_completeness)
  } else {
    deliveries.value = []
    deliveryCompleteness.value = 'metadata_only'
  }

  if (caseStudyResult.status === 'fulfilled') {
    caseStudy.value = caseStudyResult.value
  } else {
    caseStudy.value = null
  }

  if (deliveriesResult.status === 'rejected' && caseStudyResult.status === 'rejected') {
    error.value = 'Unable to load selected-match analytics data.'
  } else if (deliveriesResult.status === 'rejected') {
    error.value = 'Delivery data could not be loaded.'
  } else if (caseStudyResult.status === 'rejected') {
    error.value = 'Match summary data could not be loaded.'
  }

  loading.value = false
}

watch(
  availableInningsSet,
  (set) => {
    if (inningsFilter.value !== 'all' && !set.has(Number(inningsFilter.value))) {
      inningsFilter.value = 'all'
    }
  },
  { immediate: true },
)

watch(manhattanMode, (mode) => {
  if (mode !== 'delivery_complete' && manhattanViewMode.value === 'delivery') {
    manhattanViewMode.value = 'over'
  }
})

watch(
  scatterModeOptions,
  (options) => {
    if (!options.some(option => option.value === scatterViewMode.value && !option.disabled)) {
      const fallback = options.find(option => !option.disabled)
      scatterViewMode.value = fallback?.value ?? 'run_rate_vs_wickets'
    }
  },
  { immediate: true },
)

watch(
  () => props.matchId,
  () => {
    void loadAnalytics()
  },
  { immediate: true },
)
</script>

<style scoped>
.analytics-tables-widget {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
}

.analytics-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.analytics-title,
.analytics-context-title {
  margin: 0;
  color: var(--color-text);
}

.analytics-subtitle,
.analytics-context-meta,
.analytics-summary-note,
.analytics-fallback-note {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.analytics-controls {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.analytics-filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.analytics-filter {
  display: inline-flex;
  flex-direction: column;
  gap: 4px;
}

.analytics-filter__label {
  color: var(--color-text-muted);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.analytics-select {
  min-width: 160px;
  border: 1px solid rgba(148, 163, 184, 0.32);
  border-radius: var(--radius-sm);
  background: rgba(15, 23, 42, 0.85);
  color: var(--color-text);
  padding: 6px 8px;
}

.chart-tab {
  padding: var(--space-2) var(--space-3);
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: var(--radius-sm);
  background: rgba(15, 23, 42, 0.75);
  color: var(--color-text);
  cursor: pointer;
}

.chart-tab.active {
  border-color: rgba(56, 189, 248, 0.9);
  background: rgba(14, 116, 144, 0.35);
}

.analytics-context,
.analytics-summary-card,
.chart-container {
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: var(--radius-lg);
  background: rgba(15, 23, 42, 0.72);
  box-shadow: 0 18px 40px rgba(2, 6, 23, 0.2);
}

.analytics-context {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4);
  align-items: flex-start;
  flex-wrap: wrap;
}

.analytics-context-label,
.analytics-summary-label {
  margin: 0 0 var(--space-1) 0;
  color: #7dd3fc;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.75rem;
}

.analytics-context-result {
  margin: 0;
  color: var(--color-text);
  font-weight: 600;
}

.analytics-status,
.analytics-state {
  margin: 0;
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: rgba(15, 23, 42, 0.56);
  color: var(--color-text-muted);
}

.analytics-status--error {
  border: 1px solid rgba(248, 113, 113, 0.32);
}

.analytics-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: var(--space-3);
}

.analytics-summary-card {
  padding: var(--space-4);
}

.analytics-summary-value {
  margin: 0;
  color: var(--color-text);
  font-size: 1.8rem;
  font-weight: 700;
}

.chart-container {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.chart-info h4 {
  margin: 0 0 var(--space-1) 0;
  color: var(--color-text);
}

.chart-info p {
  margin: 0;
  color: var(--color-text-muted);
}

.analytics-chart-frame {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-3);
  align-items: stretch;
}

.analytics-chart-scale {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  color: var(--color-text-muted);
  font-size: 0.75rem;
}

.analytics-bar-chart {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(52px, 1fr);
  gap: var(--space-2);
  overflow-x: auto;
  align-items: end;
  min-height: 220px;
}

.analytics-bar-chart__column {
  display: flex;
  flex-direction: column;
  justify-content: end;
  gap: var(--space-2);
  min-width: 52px;
}

.analytics-bar-chart__marker {
  align-self: center;
  color: #fda4af;
  font-size: 0.75rem;
  font-weight: 700;
}

.analytics-bar-chart__track {
  height: 168px;
  border-radius: var(--radius-md);
  background: rgba(30, 41, 59, 0.9);
  display: flex;
  align-items: end;
  overflow: hidden;
}

.analytics-bar-chart__bar {
  width: 100%;
  min-height: 10px;
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

.analytics-bar-chart__label {
  color: var(--color-text-muted);
  font-size: 0.75rem;
  text-align: center;
}

.analytics-svg-frame {
  padding: var(--space-2);
  border-radius: var(--radius-md);
  background: rgba(15, 23, 42, 0.8);
}

.analytics-svg {
  width: 100%;
  height: auto;
}

.analytics-grid line {
  stroke: rgba(148, 163, 184, 0.22);
  stroke-width: 1;
}

.analytics-line {
  fill: none;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.analytics-axis-label {
  fill: var(--color-text-muted);
  font-size: 12px;
}

.analytics-axis-tick {
  fill: rgba(226, 232, 240, 0.82);
  font-size: 11px;
}

.analytics-final-label {
  fill: var(--color-text);
  font-size: 11px;
  font-weight: 600;
}

.analytics-legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.analytics-legend__item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text);
  font-size: var(--text-sm);
}

.analytics-legend__swatch {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  display: inline-block;
}

.analytics-legend__hint {
  color: var(--color-text-muted);
}

.analytics-howto {
  margin: 0;
  color: #cbd5e1;
  font-size: var(--text-sm);
}

.analytics-insights {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: var(--space-3);
}

.analytics-insight-card {
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  background: rgba(15, 23, 42, 0.62);
}

.analytics-insight-title {
  margin: 0 0 var(--space-1) 0;
  color: #7dd3fc;
  font-size: 0.75rem;
  text-transform: uppercase;
}

.analytics-insight-value {
  margin: 0;
  color: var(--color-text);
  font-weight: 700;
}

@media (max-width: 768px) {
  .analytics-chart-frame {
    grid-template-columns: 1fr;
  }

  .analytics-chart-scale {
    flex-direction: row;
  }
}
</style>

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
            <div class="analytics-legend__item">
              <span class="analytics-legend__swatch" style="background: #38bdf8" />
              <span>Innings 1 / attacking</span>
            </div>
            <div class="analytics-legend__item">
              <span class="analytics-legend__swatch" style="background: #34d399" />
              <span>Innings 2 / stable</span>
            </div>
            <div class="analytics-legend__item">
              <span class="analytics-legend__swatch" style="background: #f59e0b" />
              <span>Phase fallback</span>
            </div>
          </div>
        </template>
        <div v-else class="analytics-state" role="status">
          No scatter points are available for this match yet.
        </div>
        <p class="analytics-fallback-note">{{ currentModeNote('scatter') }}</p>
      </template>
    </div>
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
}

interface ScatterPoint {
  key: string
  x: number
  y: number
  radius: number
  tooltip: string
  color: string
}

interface DeliveryBucket {
  key: string
  innings: number
  label: string
  shortLabel: string
  runs: number
  wickets: number
  legalBalls: number
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
const loading = ref(false)
const error = ref<string | null>(null)
const deliveries = ref<AnalystDeliveryRow[]>([])
const deliveryCompleteness = ref<AnalyticsCompleteness>('metadata_only')
const caseStudy = ref<MatchCaseStudyResponse | null>(null)

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

function runsColor(index: number, innings: number): string {
  if (innings === 2) return '#34d399'
  return index % 2 === 0 ? '#38bdf8' : '#60a5fa'
}

function phaseColor(label: string): string {
  const normalized = label.toLowerCase()
  if (normalized.includes('power')) return '#f59e0b'
  if (normalized.includes('death')) return '#f472b6'
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

const phaseBuckets = computed<PhaseBucket[]>(() =>
  (caseStudy.value?.phases || [])
    .filter(phase => (phase.runs ?? 0) > 0 || (phase.wickets ?? 0) > 0)
    .map(phase => ({
      key: phase.id,
      label: phase.label,
      runs: phase.runs ?? 0,
      wickets: phase.wickets ?? 0,
      overs: phase.run_rate && phase.run_rate > 0
        ? Number((phase.runs / phase.run_rate).toFixed(2))
        : phaseOvers(phase.start_over, phase.end_over),
    })),
)

const deliveryBuckets = computed<DeliveryBucket[]>(() => {
  const grouped = new Map<string, DeliveryBucket>()
  const rows = [...deliveries.value].sort((a, b) => {
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
  if (inningsTotals.value.length > 0) return 'innings_totals'
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
    const deliveriesCount = deliveries.value.length
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

  if (inningsTotals.value.length > 0) {
    const totalRuns = inningsTotals.value.reduce((sum, innings) => sum + innings.runs, 0)
    const wickets = inningsTotals.value.reduce((sum, innings) => sum + innings.wickets, 0)
    const legalBalls = inningsTotals.value.reduce((sum, innings) => sum + (oversToBalls(innings.overs) ?? 0), 0)
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
  if (inningsTotals.value.length > 0) return 'innings_totals'
  return 'metadata_only'
})

const wormMode = computed<AnalyticsCompleteness>(() => manhattanMode.value)
const scatterMode = computed<AnalyticsCompleteness>(() => manhattanMode.value)

const manhattanBars = computed<ChartBar[]>(() => {
  if (manhattanMode.value === 'delivery_complete') {
    return deliveryBuckets.value.map((bucket, index) => ({
      key: bucket.key,
      shortLabel: bucket.shortLabel,
      value: bucket.runs,
      wickets: bucket.wickets,
      tooltip: `${bucket.label}: ${bucket.runs} runs, ${bucket.wickets} wickets`,
      color: runsColor(index, bucket.innings),
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
    return inningsTotals.value.map((innings, index) => ({
      key: innings.key,
      shortLabel: `Inn ${innings.innings}`,
      value: innings.runs,
      wickets: innings.wickets,
      tooltip: `${innings.label}: ${innings.runs}/${innings.wickets}`,
      color: runsColor(index, innings.innings),
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

    const maxRuns = Math.max(
      1,
      ...[...seriesMap.values()].flatMap(series => {
        let cumulative = 0
        return series.map(bucket => {
          cumulative += bucket.runs
          return cumulative
        })
      }),
    )

    return [...seriesMap.entries()].map(([innings, buckets]) => {
      let cumulativeRuns = 0
      const points = buckets.map((bucket, index) => {
        cumulativeRuns += bucket.runs
        const denominator = Math.max(buckets.length - 1, 1)
        const x = 48 + (index / denominator) * 564
        const y = 200 - (cumulativeRuns / maxRuns) * 160
        return {
          key: `${bucket.key}-worm`,
          x,
          y,
          tooltip: `${bucket.label}: ${cumulativeRuns} cumulative runs`,
        }
      })

      return {
        key: `innings-${innings}`,
        label: `Innings ${innings}`,
        color: innings === 2 ? '#34d399' : '#38bdf8',
        path: points.map(point => `${point.x},${point.y}`).join(' '),
        points,
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
      color: '#f59e0b',
      path: points.map(point => `${point.x},${point.y}`).join(' '),
      points,
    }]
  }

  if (wormMode.value === 'innings_totals') {
    let cumulativeRuns = 0
    const maxRuns = Math.max(1, inningsTotals.value.reduce((sum, innings) => sum + innings.runs, 0))
    const points = inningsTotals.value.map((innings, index) => {
      cumulativeRuns += innings.runs
      const denominator = Math.max(inningsTotals.value.length - 1, 1)
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
      color: '#a78bfa',
      path: points.map(point => `${point.x},${point.y}`).join(' '),
      points,
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

const scatterPoints = computed<ScatterPoint[]>(() => {
  if (scatterMode.value === 'delivery_complete') {
    const maxRuns = Math.max(1, ...deliveryBuckets.value.map(bucket => bucket.runs))
    const maxOver = Math.max(1, deliveryBuckets.value.length)
    return deliveryBuckets.value.map((bucket, index) => ({
      key: `${bucket.key}-scatter`,
      x: 48 + ((index + 1) / maxOver) * 540,
      y: 200 - (bucket.runs / maxRuns) * 160,
      radius: 5 + bucket.wickets * 2,
      tooltip: `${bucket.label}: ${bucket.runs} runs, ${bucket.wickets} wickets`,
      color: bucket.innings === 2 ? '#34d399' : '#38bdf8',
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
        radius: 7,
        tooltip: `${phase.label}: ${runRateValue.toFixed(2)} run rate, ${phase.wickets} wickets`,
        color: '#f59e0b',
      }
    })
  }

  if (scatterMode.value === 'innings_totals') {
    const maxRuns = Math.max(1, ...inningsTotals.value.map(innings => innings.runs))
    const maxWickets = Math.max(1, ...inningsTotals.value.map(innings => innings.wickets))
    return inningsTotals.value.map((innings, index) => ({
      key: `${innings.key}-scatter`,
      x: 48 + (innings.runs / maxRuns) * 540,
      y: 200 - ((innings.wickets || 0) / maxWickets) * 160,
      radius: 7,
      tooltip: `${innings.label}: ${innings.runs} runs, ${innings.wickets} wickets`,
      color: index === 0 ? '#38bdf8' : '#34d399',
    }))
  }

  return []
})

const scatterXAxisLabel = computed(() => {
  if (scatterMode.value === 'delivery_complete') return 'Over bins'
  if (scatterMode.value === 'phase_level') return 'Run rate'
  if (scatterMode.value === 'innings_totals') return 'Runs'
  return 'Unavailable'
})

const scatterYAxisLabel = computed(() => {
  if (scatterMode.value === 'delivery_complete') return 'Runs'
  return 'Wickets'
})

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
  if (mode === 'delivery_complete') return 'Using over-level delivery records for full graph rendering.'
  if (mode === 'phase_level') return 'Using phase summaries because delivery records are unavailable.'
  if (mode === 'innings_totals') return 'Using innings totals because only innings-level scoring is available.'
  return 'Insufficient data for graph rendering.'
}

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

@media (max-width: 768px) {
  .analytics-chart-frame {
    grid-template-columns: 1fr;
  }

  .analytics-chart-scale {
    flex-direction: row;
  }
}
</style>

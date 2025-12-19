import { ref, computed } from 'vue'
import type { Ref, ComputedRef } from 'vue'
import { API_BASE } from '@/services/api'

export interface ImprovementMetrics {
  metric_name: string
  previous_value: number
  current_value: number
  absolute_change: number
  percentage_change: number
  trend: 'improving' | 'declining' | 'stable'
  confidence: number
}

export interface PeriodComparison {
  from_month: string
  to_month: string
  metrics: Record<string, ImprovementMetrics>
}

export interface LatestStats {
  batting_average: number
  strike_rate: number
  consistency_score: number
  matches_played: number
  innings_played: number
  role: string
}

export interface ImprovementSummaryData {
  status: 'success' | 'insufficient_data'
  overall_trend: 'improving' | 'declining' | 'stable' | 'accelerating'
  improvement_score: number
  latest_month: string
  months_analyzed: number
  latest_stats: LatestStats
  latest_improvements: Record<string, ImprovementMetrics>
  historical_improvements: PeriodComparison[]
  highlights: string[]
}

export interface UsePlayerImprovement {
  summaryData: Ref<ImprovementSummaryData | null>
  monthlyStatsData: Ref<any | null>
  trendData: Ref<any | null>
  loading: Ref<boolean>
  error: Ref<string | null>
  fetchImprovementSummary: (playerId: string, months?: number) => Promise<void>
  fetchMonthlyStats: (playerId: string, limit?: number) => Promise<void>
  fetchTrends: (playerId: string, months?: number) => Promise<void>
  getTrendIndicator: (trend: string) => string
  formatTrendValue: (value: number) => string
  refetch: () => Promise<void>
}

/**
 * Build full API URL with base
 */
function buildApiUrl(path: string): string {
  const basePath = `${API_BASE || ''}`
  return `${basePath}${path}`.replace(/\/+/g, '/').replace('https:/', 'https://').replace('http:/', 'http://')
}

export const usePlayerImprovement = (): UsePlayerImprovement => {
  const summaryData: Ref<ImprovementSummaryData | null> = ref(null)
  const monthlyStatsData: Ref<any | null> = ref(null)
  const trendData: Ref<any | null> = ref(null)
  const loading: Ref<boolean> = ref(false)
  const error: Ref<string | null> = ref(null)

  const currentPlayerId = ref<string>('')
  const currentMonths = ref<number>(6)

  /**
   * Fetch comprehensive improvement summary
   */
  const fetchImprovementSummary = async (
    playerId: string,
    months: number = 6,
  ): Promise<void> => {
    loading.value = true
    error.value = null
    currentPlayerId.value = playerId
    currentMonths.value = months

    try {
      const endpoint = buildApiUrl(
        `/api/player-analytics/players/${playerId}/improvement-summary?months=${months}`,
      )
      const response = await fetch(endpoint)

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Player not found')
        }
        throw new Error(`Failed to fetch improvement summary: ${response.statusText}`)
      }

      const data: ImprovementSummaryData = await response.json()
      summaryData.value = data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'An error occurred'
      summaryData.value = null
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch monthly statistics breakdown
   */
  const fetchMonthlyStats = async (
    playerId: string,
    limit: number = 12,
  ): Promise<void> => {
    loading.value = true
    error.value = null

    try {
      const endpoint = buildApiUrl(
        `/api/player-analytics/players/${playerId}/monthly-stats?limit_months=${limit}`,
      )
      const response = await fetch(endpoint)

      if (!response.ok) {
        throw new Error('Failed to fetch monthly statistics')
      }

      const data = await response.json()
      monthlyStatsData.value = data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'An error occurred'
      monthlyStatsData.value = null
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch month-to-month trends
   */
  const fetchTrends = async (
    playerId: string,
    months: number = 3,
  ): Promise<void> => {
    loading.value = true
    error.value = null

    try {
      const endpoint = buildApiUrl(
        `/api/player-analytics/players/${playerId}/improvement-trend?months=${months}`,
      )
      const response = await fetch(endpoint)

      if (!response.ok) {
        throw new Error('Failed to fetch improvement trends')
      }

      const data = await response.json()
      trendData.value = data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'An error occurred'
      trendData.value = null
    } finally {
      loading.value = false
    }
  }

  /**
   * Get visual indicator for trend
   */
  const getTrendIndicator = (trend: string): string => {
    const indicators: Record<string, string> = {
      improving: '📈',
      declining: '📉',
      stable: '➡️',
      accelerating: '🚀',
    }
    return indicators[trend] || '❓'
  }

  /**
   * Format trend value for display
   */
  const formatTrendValue = (value: number): string => {
    const sign = value > 0 ? '+' : ''
    return `${sign}${value.toFixed(2)}%`
  }

  /**
   * Refetch current data
   */
  const refetch = async (): Promise<void> => {
    if (currentPlayerId.value) {
      await fetchImprovementSummary(currentPlayerId.value, currentMonths.value)
    }
  }

  /**
   * Computed properties for convenience
   */
  const hasData = computed(() => summaryData.value !== null)

  const overallTrend = computed(() => summaryData.value?.overall_trend || null)

  const improvementScore = computed(
    () => summaryData.value?.improvement_score ?? 0,
  )

  const isImproving = computed(
    () =>
      summaryData.value?.overall_trend === 'improving' ||
      summaryData.value?.overall_trend === 'accelerating',
  )

  const latestStats = computed(() => summaryData.value?.latest_stats || null)

  const highlights = computed(() => summaryData.value?.highlights || [])

  return {
    summaryData,
    monthlyStatsData,
    trendData,
    loading,
    error,
    fetchImprovementSummary,
    fetchMonthlyStats,
    fetchTrends,
    getTrendIndicator,
    formatTrendValue,
    refetch,
  }
}

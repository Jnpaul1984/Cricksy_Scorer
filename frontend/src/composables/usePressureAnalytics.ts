import { ref } from 'vue'
import { useApi } from './useApi'

export interface PressurePoint {
  delivery_num: number
  over_num: number
  pressure_score: number
  pressure_level: string
  factors: Record<string, number>
  rates: {
    required_run_rate: number
    actual_run_rate: number
  }
  cumulative_stats: {
    runs: number
    wickets: number
    dot_count: number
    strike_rate: number
    balls_remaining: number
    overs_remaining: number
  }
}

export interface PressureSummary {
  total_deliveries: number
  average_pressure: number
  peak_pressure: number
  peak_pressure_at_delivery: number
  critical_moments: number
  high_pressure_count: number
}

export interface PressurePhases {
  powerplay: PressurePoint[]
  middle: PressurePoint[]
  death: PressurePoint[]
  powerplay_stats?: Record<string, number>
  middle_stats?: Record<string, number>
  death_stats?: Record<string, number>
}

export interface PressureData {
  pressure_points: PressurePoint[]
  summary: PressureSummary
  peak_moments: PressurePoint[]
  phases: PressurePhases
}

export const usePressureAnalytics = () => {
  const { get } = useApi()

  const pressureData = ref<PressureData | null>(null)
  const criticalMoments = ref<PressurePoint[]>([])
  const phases = ref<PressurePhases | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Fetch pressure map for a specific game and inning
   */
  const fetchPressureMap = async (gameId: string, inningNum?: number): Promise<PressureData | null> => {
    loading.value = true
    error.value = null

    try {
      const url = inningNum
        ? `/analytics/games/${gameId}/pressure-map?inning_num=${inningNum}`
        : `/analytics/games/${gameId}/pressure-map`

      const response = await get<PressureData>(url)

      if (response.success && response.data) {
        pressureData.value = response.data
        phases.value = response.data.phases
        criticalMoments.value = response.data.peak_moments || []
        return response.data
      } else {
        // Silently handle errors - feature may not be fully implemented
        error.value = null
        return null
      }
    } catch (err) {
      // Silently handle errors - analytics features may not be fully implemented
      error.value = null
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch critical moments (high-pressure deliveries) for a game
   */
  const fetchCriticalMoments = async (
    gameId: string,
    threshold: number = 70,
    inningNum?: number
  ): Promise<PressurePoint[]> => {
    loading.value = true
    error.value = null

    try {
      const params = new URLSearchParams()
      params.append('threshold', threshold.toString())
      if (inningNum) params.append('inning_num', inningNum.toString())

      const url = `/analytics/games/${gameId}/critical-moments?${params.toString()}`
      const response = await get<{ critical_moments: PressurePoint[] }>(url)

      if (response.success && response.data) {
        criticalMoments.value = response.data.critical_moments || []
        return response.data.critical_moments || []
      } else {
        error.value = response.error || 'Failed to fetch critical moments'
        return []
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'An error occurred'
      return []
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch pressure phases breakdown for a game
   */
  const fetchPressurePhases = async (
    gameId: string,
    inningNum?: number
  ): Promise<PressurePhases | null> => {
    loading.value = true
    error.value = null

    try {
      const url = inningNum
        ? `/analytics/games/${gameId}/pressure-phases?inning_num=${inningNum}`
        : `/analytics/games/${gameId}/pressure-phases`

      const response = await get<PressurePhases>(url)

      if (response.success && response.data) {
        phases.value = response.data
        return response.data
      } else {
        error.value = response.error || 'Failed to fetch pressure phases'
        return null
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'An error occurred'
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Calculate pressure statistics from raw data
   */
  const calculatePressureStats = (pressurePoints: PressurePoint[]) => {
    if (!pressurePoints.length) {
      return {
        averagePressure: 0,
        peakPressure: 0,
        minPressure: 0,
        highPressureCount: 0,
        extremePressureCount: 0
      }
    }

    const scores = pressurePoints.map(p => p.pressure_score)
    const averagePressure = scores.reduce((a, b) => a + b, 0) / scores.length
    const peakPressure = Math.max(...scores)
    const minPressure = Math.min(...scores)
    const highPressureCount = scores.filter(s => s >= 60).length
    const extremePressureCount = scores.filter(s => s >= 80).length

    return {
      averagePressure,
      peakPressure,
      minPressure,
      highPressureCount,
      extremePressureCount
    }
  }

  /**
   * Get pressure level description
   */
  const getPressureLevel = (score: number): string => {
    if (score < 20) return 'low'
    if (score < 40) return 'moderate'
    if (score < 60) return 'building'
    if (score < 80) return 'high'
    return 'extreme'
  }

  /**
   * Get pressure level with emoji
   */
  const getPressureLevelWithEmoji = (score: number): string => {
    if (score < 20) return '🟢 Low'
    if (score < 40) return '🟡 Moderate'
    if (score < 60) return '🟠 Building'
    if (score < 80) return '🔴 High'
    return '🟣 Extreme'
  }

  /**
   * Refresh pressure data from server
   */
  const refresh = async (gameId: string, inningNum?: number): Promise<void> => {
    await fetchPressureMap(gameId, inningNum)
  }

  /**
   * Clear cached data
   */
  const clear = (): void => {
    pressureData.value = null
    criticalMoments.value = []
    phases.value = null
    error.value = null
  }

  return {
    // State
    pressureData,
    criticalMoments,
    phases,
    loading,
    error,

    // Methods
    fetchPressureMap,
    fetchCriticalMoments,
    fetchPressurePhases,
    calculatePressureStats,
    getPressureLevel,
    getPressureLevelWithEmoji,
    refresh,
    clear
  }
}

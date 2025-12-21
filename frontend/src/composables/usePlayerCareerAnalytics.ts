import { ref, computed } from 'vue'
import { useApi } from './useApi'

export interface PlayerCareerSummary {
  player_id: string
  player_name: string
  career_summary: string
  batting_stats: {
    matches: number
    total_runs: number
    average: number
    consistency_score: number
    strike_rate: number
    boundary_percentage: number
    fours: number
    sixes: number
    best_score: number
    worst_score: number
    fifties: number
    centuries: number
    out_percentage: number
    dismissal_rate: number
  }
  bowling_stats: {
    matches: number
    total_wickets: number
    total_overs: number
    runs_conceded: number
    economy_rate: number
    average_wickets_per_match: number
    maiden_percentage: number
    maidens: number
  }
  specialization: string
  specialization_confidence: number
  recent_form: {
    recent_matches: number
    recent_runs: number
    recent_average: number
    recent_strike_rate: number
    recent_wickets: number
    trend: 'improving' | 'declining' | 'stable'
    last_match_performance: string
  }
  best_performances: {
    best_batting?: {
      runs: number
      balls_faced: number
      fours: number
      sixes: number
      date: string
    }
    best_bowling?: {
      wickets: number
      overs: number
      runs_conceded: number
      economy: number
      date: string
    }
  }
  career_highlights: string[]
}

export interface YearlyStats {
  player_id: string
  player_name: string
  yearly_breakdown: Array<{
    year: number | string
    matches: number
    runs: number
    average: number
    strike_rate: number
    centuries: number
    fifties: number
  }>
}

export function usePlayerCareerAnalytics() {
  const apiService = useApi()

  const summary = ref<PlayerCareerSummary | null>(null)
  const yearlyStats = ref<YearlyStats | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const specialization = computed(() => summary.value?.specialization || '')
  const totalMatches = computed(() => summary.value?.batting_stats.matches || 0)
  const totalRuns = computed(() => summary.value?.batting_stats.total_runs || 0)
  const careerAverage = computed(() => summary.value?.batting_stats.average || 0)

  /**
   * Fetch career summary for a player
   */
  async function fetchCareerSummary(playerId: string) {
    try {
      loading.value = true
      error.value = null

      const response = await apiService.get<PlayerCareerSummary>(
        `/analytics/players/players/${playerId}/career-summary`
      )

      if (response && response.data) {
        summary.value = response.data as PlayerCareerSummary
      }
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch career summary'
      console.error('Failed to fetch career summary:', err)
      summary.value = null
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch yearly statistics for a player
   */
  async function fetchYearlyStats(playerId: string) {
    try {
      const response = await apiService.get<YearlyStats>(
        `/analytics/players/players/${playerId}/year-stats`
      )

      if (response && response.data) {
        yearlyStats.value = response.data as YearlyStats
      }
    } catch (err: any) {
      console.warn('Failed to fetch yearly stats:', err)
      yearlyStats.value = null
    }
  }

  /**
   * Fetch career summary with yearly breakdown
   */
  async function fetchFullProfile(playerId: string) {
    await Promise.all([
      fetchCareerSummary(playerId),
      fetchYearlyStats(playerId),
    ])
  }

  /**
   * Compare two players
   */
  async function comparePlayers(playerId1: string, playerId2: string) {
    try {
      loading.value = true
      error.value = null

      const response = await apiService.get(
        `/analytics/players/players/${playerId1}/comparison?comparison_player_id=${playerId2}`
      )

      return response?.data || null
    } catch (err: any) {
      error.value = err.message || 'Failed to compare players'
      console.error('Failed to compare players:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Clear cached data
   */
  function clear() {
    summary.value = null
    yearlyStats.value = null
    error.value = null
  }

  return {
    // State
    summary,
    yearlyStats,
    loading,
    error,

    // Computed
    specialization,
    totalMatches,
    totalRuns,
    careerAverage,

    // Methods
    fetchCareerSummary,
    fetchYearlyStats,
    fetchFullProfile,
    comparePlayers,
    clear,
  }
}

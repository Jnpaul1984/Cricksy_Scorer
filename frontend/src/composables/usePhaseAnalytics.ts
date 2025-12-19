/**
 * usePhaseAnalytics Composable
 *
 * State management and API integration for match phase analysis.
 * Provides functions to fetch and manage phase data for interactive visualizations.
 */

import { ref, computed } from 'vue'

// Type definitions for phase analysis
export interface PhaseData {
  phase_name: string
  phase_number: number
  start_over: number
  end_over: number
  total_runs: number
  total_wickets: number
  total_deliveries: number
  run_rate: number
  expected_runs_in_phase: number
  actual_vs_expected_pct: number
  wicket_rate: number
  boundary_count: number
  dot_ball_count: number
  aggressive_index: number
  acceleration_rate: number
}

export interface PhaseSummary {
  total_runs: number
  total_wickets: number
  overall_run_rate: number
  overall_expected_runs: number
  acceleration_trend: 'increasing' | 'decreasing' | 'stable'
}

export interface PhasePrediction {
  powerplay_actual?: number
  powerplay_efficiency?: number
  total_expected_runs?: number
  win_probability?: number
}

export interface PhasePerformance {
  [phaseName: string]: {
    actual_runs: number
    expected_runs: number
    performance_pct: number
  }
}

export interface PhaseAnalysisData {
  game_id: string
  inning_number: number
  overs_limit: number
  phases: PhaseData[]
  current_phase: string
  phase_index: number
  summary: PhaseSummary
  predictions: PhasePrediction
  phase_performance: PhasePerformance
}

export interface PhasePredictionData {
  game_id: string
  inning_number: number
  phase_predictions: {
    [phaseName: string]: {
      actual_runs: number
      expected_runs: number
      efficiency: number
      run_rate: number
      wickets_lost: number
      aggressive_index: number
    }
  }
  match_prediction: {
    projected_total: number
    confidence: number
    win_probability?: number
  }
}

export interface PhaseTrendsData {
  game_id: string
  inning_number: number
  trends: {
    run_rate_trend: number[]
    wicket_rate_trend: number[]
    acceleration: 'increasing' | 'decreasing' | 'stable'
    phase_comparison: {
      vs_powerplay: number[]
      vs_benchmark: number[]
    }
  }
}

export function usePhaseAnalytics() {
  // State
  const phaseData = ref<PhaseAnalysisData | null>(null)
  const predictions = ref<PhasePredictionData | null>(null)
  const trends = ref<PhaseTrendsData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const currentPhase = computed(() => phaseData.value?.current_phase || 'powerplay')
  const phaseIndex = computed(() => phaseData.value?.phase_index || 0)
  const isChasing = computed(() => (predictions.value?.match_prediction.win_probability ?? 0) > 0)

  /**
   * Fetch phase map for a game
   */
  async function fetchPhaseMap(gameId: string, inningNum?: number) {
    try {
      loading.value = true
      error.value = null

      const params = new URLSearchParams()
      if (inningNum) params.append('inning_num', inningNum.toString())

      const response = await fetch(
        `/api/analytics/games/${gameId}/phase-map?${params.toString()}`
      )
      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      phaseData.value = await response.json()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch phase map'
      console.error('Phase map error:', err)
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch phase predictions for a game
   */
  async function fetchPredictions(gameId: string, inningNum?: number) {
    try {
      loading.value = true
      error.value = null

      const params = new URLSearchParams()
      if (inningNum) params.append('inning_num', inningNum.toString())

      const response = await fetch(
        `/api/analytics/games/${gameId}/phase-predictions?${params.toString()}`
      )
      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      predictions.value = await response.json()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch predictions'
      console.error('Predictions error:', err)
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch phase trends for a game
   */
  async function fetchTrends(gameId: string, inningNum?: number) {
    try {
      loading.value = true
      error.value = null

      const params = new URLSearchParams()
      if (inningNum) params.append('inning_num', inningNum.toString())

      const response = await fetch(
        `/api/analytics/games/${gameId}/phase-trends?${params.toString()}`
      )
      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      trends.value = await response.json()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch trends'
      console.error('Trends error:', err)
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch all phase data for a game
   */
  async function fetchAllPhaseData(gameId: string, inningNum?: number) {
    loading.value = true
    try {
      await Promise.all([
        fetchPhaseMap(gameId, inningNum),
        fetchPredictions(gameId, inningNum),
        fetchTrends(gameId, inningNum),
      ])
    } finally {
      loading.value = false
    }
  }

  /**
   * Get phase statistics by name
   */
  function getPhaseStats(phaseName: string): PhaseData | undefined {
    return phaseData.value?.phases.find((p) => p.phase_name === phaseName)
  }

  /**
   * Get phase efficiency percentage
   */
  function getPhaseEfficiency(phaseName: string): number {
    const phase = getPhaseStats(phaseName)
    return phase?.actual_vs_expected_pct || 0
  }

  /**
   * Get phase performance rating
   */
  function getPhaseRating(phaseName: string): 'excellent' | 'good' | 'average' | 'poor' {
    const efficiency = getPhaseEfficiency(phaseName)
    if (efficiency >= 100) return 'excellent'
    if (efficiency >= 85) return 'good'
    if (efficiency >= 70) return 'average'
    return 'poor'
  }

  /**
   * Get acceleration phase name
   */
  function getAccelerationPhase(): string {
    if (!phaseData.value?.phases || phaseData.value.phases.length === 0) return 'N/A'
    let maxRR = -1
    let maxPhase = ''
    for (const phase of phaseData.value.phases) {
      if (phase.run_rate > maxRR) {
        maxRR = phase.run_rate
        maxPhase = phase.phase_name
      }
    }
    return maxPhase
  }

  /**
   * Clear all phase data
   */
  function clear() {
    phaseData.value = null
    predictions.value = null
    trends.value = null
    error.value = null
  }

  /**
   * Refresh phase data
   */
  async function refresh(gameId: string, inningNum?: number) {
    clear()
    await fetchAllPhaseData(gameId, inningNum)
  }

  return {
    // State
    phaseData,
    predictions,
    trends,
    loading,
    error,

    // Computed
    currentPhase,
    phaseIndex,
    isChasing,

    // Methods
    fetchPhaseMap,
    fetchPredictions,
    fetchTrends,
    fetchAllPhaseData,
    getPhaseStats,
    getPhaseEfficiency,
    getPhaseRating,
    getAccelerationPhase,
    clear,
    refresh,
  }
}

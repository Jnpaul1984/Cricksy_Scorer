import { ref } from 'vue'
import { API_BASE } from '@/services/api'

export interface BestBowlerSuggestion {
  bowler_id: string
  bowler_name: string
  reason: string
  effectiveness_vs_batter: number
  expected_economy: number
  confidence: number
}

export interface WeaknessAnalysis {
  primary_weakness: string
  weakness_score: number
  secondary_weakness?: string | null
  recommended_line: string
  recommended_length: string
  recommended_speed?: number | null
  confidence: number
}

export interface FieldingZone {
  position: string
  priority: number
  coverage_reason: string
}

export interface FieldingSetup {
  bowler_id: string
  batter_id: string
  primary_zone: string
  recommended_positions: FieldingZone[]
  confidence: number
  reasoning: string
}

export interface TacticalSuggestions {
  game_id: string
  timestamp?: string
  suggestions?: {
    best_bowler?: BestBowlerSuggestion
    weakness_analysis?: WeaknessAnalysis
    fielding_setup?: FieldingSetup
  }
  best_bowler?: BestBowlerSuggestion
  weakness?: WeaknessAnalysis
  fielding?: FieldingSetup
}

export const useTacticalSuggestions = () => {
  const suggestions = ref<TacticalSuggestions | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Fetch all tactical suggestions for a game
   */
  async function fetchSuggestions(gameId: string) {
    loading.value = true
    error.value = null

    try {
      const apiUrl = `${API_BASE}/tactical/games/${gameId}/suggestions/all`
      const response = await fetch(apiUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()

      // Normalize response structure
      const normalized: TacticalSuggestions = {
        game_id: data.game_id || gameId,
        timestamp: data.timestamp,
      }

      // Handle both nested and flat response structures
      if (data.suggestions) {
        // Nested structure from /all endpoint
        normalized.best_bowler = data.suggestions.best_bowler
        normalized.weakness = data.suggestions.weakness_analysis
        normalized.fielding = data.suggestions.fielding_setup
      } else {
        // Flat structure from individual endpoints
        normalized.best_bowler = data.best_bowler || data.recommendation
        normalized.weakness = data.weakness_analysis || data.weakness
        normalized.fielding = data.fielding_setup || data.fielding
      }

      suggestions.value = normalized
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to fetch suggestions'
      error.value = errorMsg
      suggestions.value = null
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch best bowler recommendation only
   */
  async function fetchBestBowler(gameId: string) {
    loading.value = true
    error.value = null

    try {
      const apiUrl = `${API_BASE}/tactical/games/${gameId}/suggestions/best-bowler`
      const response = await fetch(apiUrl)

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const data = await response.json()

      if (!suggestions.value) {
        suggestions.value = {
          game_id: gameId,
        }
      }

      suggestions.value.best_bowler = data.recommendation || data.best_bowler
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch bowler suggestion'
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch weakness analysis only
   */
  async function fetchWeaknessAnalysis(gameId: string) {
    loading.value = true
    error.value = null

    try {
      const apiUrl = `${API_BASE}/tactical/games/${gameId}/suggestions/weakness-analysis`
      const response = await fetch(apiUrl)

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const data = await response.json()

      if (!suggestions.value) {
        suggestions.value = {
          game_id: gameId,
        }
      }

      suggestions.value.weakness = data.weakness_analysis || data.weakness
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch weakness analysis'
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch fielding setup recommendation only
   */
  async function fetchFieldingSetup(gameId: string) {
    loading.value = true
    error.value = null

    try {
      const apiUrl = `${API_BASE}/tactical/games/${gameId}/suggestions/fielding-setup`
      const response = await fetch(apiUrl)

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const data = await response.json()

      if (!suggestions.value) {
        suggestions.value = {
          game_id: gameId,
        }
      }

      suggestions.value.fielding = data.fielding_setup || data.fielding
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch fielding setup'
    } finally {
      loading.value = false
    }
  }

  /**
   * Clear all suggestions and errors
   */
  function clearSuggestions() {
    suggestions.value = null
    error.value = null
  }

  return {
    suggestions,
    loading,
    error,
    fetchSuggestions,
    fetchBestBowler,
    fetchWeaknessAnalysis,
    fetchFieldingSetup,
    clearSuggestions,
  }
}

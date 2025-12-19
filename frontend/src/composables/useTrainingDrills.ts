import { ref } from 'vue'

interface TrainingDrill {
  drill_id: string
  name: string
  description: string
  category: string
  severity: string
  reason?: string
  reps_or_count: number
  duration_minutes: number
  focus_area: string
  difficulty: number
  recommended_frequency?: string
  expected_improvement?: string
}

interface DrillPlan {
  player_id: string
  player_name?: string
  drills: TrainingDrill[]
  high_priority_count?: number
  medium_priority_count?: number
  low_priority_count?: number
  total_weekly_hours?: number
  focus_areas?: string[]
}

interface DrillCategory {
  category: string
  templates: Array<{
    name: string
    description: string
    duration_minutes: number
    reps_or_count: number
    focus_area: string
    difficulty: number
  }>
}

const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000'

export function useTrainingDrills() {
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Fetch suggested drills for a specific player
   */
  async function fetchPlayerDrills(
    playerId: string
  ): Promise<{ drill_plan: DrillPlan } | null> {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(
        `${API_BASE}/training/players/${playerId}/suggested-drills`
      )

      if (!response.ok) {
        throw new Error(`Failed to fetch player drills: ${response.statusText}`)
      }

      const data = await response.json()
      return data as { drill_plan: DrillPlan }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      console.error('Error fetching player drills:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch suggested drills for a team post-match
   */
  async function fetchTeamDrills(
    gameId: string,
    teamSide: 'a' | 'b'
  ): Promise<{ team_drills: Array<{ player_name: string; drill_plan: DrillPlan }> } | null> {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(
        `${API_BASE}/training/games/${gameId}/team-${teamSide}/suggested-drills`
      )

      if (!response.ok) {
        throw new Error(`Failed to fetch team drills: ${response.statusText}`)
      }

      const data = await response.json()
      return data as {
        team_drills: Array<{ player_name: string; drill_plan: DrillPlan }>
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      console.error('Error fetching team drills:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch available drill categories and templates
   */
  async function fetchDrillCategories(): Promise<
    { categories: DrillCategory[] } | null
  > {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE}/training/drills/categories`)

      if (!response.ok) {
        throw new Error(`Failed to fetch drill categories: ${response.statusText}`)
      }

      const data = await response.json()
      return data as { categories: DrillCategory[] }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      console.error('Error fetching drill categories:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Get severity color for drill display
   */
  function getSeverityColor(severity: string): string {
    const severityMap: Record<string, string> = {
      high: '#e53e3e',
      medium: '#ed8936',
      low: '#48bb78',
    }
    return severityMap[severity.toLowerCase()] || '#cbd5e0'
  }

  /**
   * Get difficulty color for drill display
   */
  function getDifficultyColor(difficulty: number): string {
    if (difficulty <= 3) return '#48bb78' // Easy - green
    if (difficulty <= 6) return '#ed8936' // Medium - orange
    return '#e53e3e' // Hard - red
  }

  /**
   * Format duration for display
   */
  function formatDuration(minutes: number): string {
    if (minutes < 60) {
      return `${minutes}m`
    }
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
  }

  /**
   * Format frequency for display
   */
  function formatFrequency(frequency: string): string {
    const frequencyMap: Record<string, string> = {
      daily: '🔴 Daily',
      '3x/week': '🟠 3x/week',
      weekly: '🟡 Weekly',
    }
    return frequencyMap[frequency] || frequency
  }

  return {
    loading,
    error,
    fetchPlayerDrills,
    fetchTeamDrills,
    fetchDrillCategories,
    getSeverityColor,
    getDifficultyColor,
    formatDuration,
    formatFrequency,
  }
}

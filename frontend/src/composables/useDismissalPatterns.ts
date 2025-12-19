import { ref } from 'vue'

interface DismissalPattern {
  pattern_name: string
  pattern_type: string
  dismissal_count: number
  dismissal_percentage: number
  severity: string
  context: string
  recommendation: string
  confidence?: number
}

interface CriticalSituation {
  situation_type: string
  dismissal_count: number
  risk_level: string
  scenario_description: string
}

interface PlayerAnalysis {
  player_id: string
  player_name: string
  analysis: {
    total_dismissals: number
    dismissals_by_type: Record<string, number>
    dismissals_by_phase: Record<string, number>
    dismissals_by_delivery: Record<string, number>
    overall_vulnerability_score: number
    primary_vulnerability: string
    secondary_vulnerabilities: string[]
    top_patterns: DismissalPattern[]
    critical_situations: CriticalSituation[]
    improvement_areas: string[]
  }
}

interface TeamAnalysis {
  status: string
  game_id: string
  team_side: string
  team_analysis: {
    total_team_dismissals: number
    vulnerable_players: Array<{ player_name: string; vulnerability_score: number }>
    phase_vulnerability: Record<string, number>
    team_recommendations: string[]
  }
  player_details: Array<{
    player_name: string
    total_dismissals: number
    vulnerability_score: number
    primary_vulnerability: string
    top_patterns: DismissalPattern[]
  }>
}

interface VulnerabilityScore {
  status: string
  player_id: string
  player_name: string
  vulnerability_score: number
  risk_level: string
  primary_vulnerability: string
  total_dismissals: number
}

interface DismissalTrend {
  status: string
  player_id: string
  player_name: string
  trend: {
    period: string
    dismissal_count: number
    average_runs_at_dismissal: number
    average_deliveries_faced: number
    trend_direction: string
  }
}

const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000'

export function useDismissalPatterns() {
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Fetch comprehensive dismissal pattern analysis for a player
   */
  async function fetchPlayerAnalysis(playerId: string): Promise<PlayerAnalysis | null> {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(
        `${API_BASE}/dismissal-patterns/players/${playerId}/analysis`
      )

      if (!response.ok) {
        throw new Error(`Failed to fetch analysis: ${response.statusText}`)
      }

      const data = await response.json()
      return data as PlayerAnalysis
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      console.error('Error fetching player analysis:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch team-level dismissal pattern analysis
   */
  async function fetchTeamAnalysis(
    gameId: string,
    teamSide: 'a' | 'b'
  ): Promise<TeamAnalysis | null> {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(
        `${API_BASE}/dismissal-patterns/games/${gameId}/team-${teamSide}/analysis`
      )

      if (!response.ok) {
        throw new Error(`Failed to fetch team analysis: ${response.statusText}`)
      }

      const data = await response.json()
      return data as TeamAnalysis
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      console.error('Error fetching team analysis:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Get quick vulnerability score for a player
   */
  async function fetchVulnerabilityScore(
    playerId: string
  ): Promise<VulnerabilityScore | null> {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(
        `${API_BASE}/dismissal-patterns/players/${playerId}/vulnerability-score`
      )

      if (!response.ok) {
        throw new Error(`Failed to fetch vulnerability score: ${response.statusText}`)
      }

      const data = await response.json()
      return data as VulnerabilityScore
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      console.error('Error fetching vulnerability score:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Get dismissal trend for a player
   */
  async function fetchDismissalTrend(
    playerId: string,
    period: 'last_5' | 'last_10' | 'last_20' = 'last_10'
  ): Promise<DismissalTrend | null> {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(
        `${API_BASE}/dismissal-patterns/players/${playerId}/trend?period=${period}`
      )

      if (!response.ok) {
        throw new Error(`Failed to fetch trend: ${response.statusText}`)
      }

      const data = await response.json()
      return data as DismissalTrend
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Unknown error occurred'
      console.error('Error fetching dismissal trend:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Get risk color for severity/risk level
   */
  function getRiskColor(riskLevel: string): string {
    const colorMap: Record<string, string> = {
      critical: '#e53e3e',
      high: '#ed8936',
      medium: '#ecc94b',
      low: '#48bb78',
    }
    return colorMap[riskLevel.toLowerCase()] || '#cbd5e0'
  }

  /**
   * Format dismissal type for display
   */
  function formatDismissalType(dismissalType: string): string {
    return dismissalType
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  /**
   * Get severity icon
   */
  function getSeverityIcon(severity: string): string {
    const iconMap: Record<string, string> = {
      high: '🔴',
      medium: '🟠',
      low: '🟢',
    }
    return iconMap[severity.toLowerCase()] || '⚪'
  }

  /**
   * Get risk level text
   */
  function getRiskLevelText(score: number): string {
    if (score >= 70) return 'CRITICAL'
    if (score >= 50) return 'HIGH'
    if (score >= 30) return 'MEDIUM'
    return 'LOW'
  }

  return {
    loading,
    error,
    fetchPlayerAnalysis,
    fetchTeamAnalysis,
    fetchVulnerabilityScore,
    fetchDismissalTrend,
    getRiskColor,
    formatDismissalType,
    getSeverityIcon,
    getRiskLevelText,
  }
}

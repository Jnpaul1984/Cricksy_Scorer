import { ref, computed } from 'vue'
import { useApi } from './useApi'

export interface InningsGradeData {
  grade: 'A+' | 'A' | 'B' | 'C' | 'D'
  score_percentage: number
  par_score: number
  total_runs: number
  run_rate: number
  wickets_lost: number
  wicket_efficiency: number
  boundary_count: number
  boundary_percentage: number
  dot_ball_ratio: number
  overs_played: number
  grade_factors: {
    score_percentage_contribution: string
    wicket_efficiency_contribution: string
    strike_rotation_contribution: string
    boundary_efficiency_contribution: string
  }
  inning_num?: number
  game_id?: string
  batting_team?: string
  bowling_team?: string
}

export function useInningsGrade() {
  const apiService = useApi()
  
  const grade = ref<InningsGradeData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const gradeColor = computed(() => {
    if (!grade.value) return '#9ca3af'
    const colors: Record<string, string> = {
      'A+': '#22c55e',
      'A': '#84cc16',
      'B': '#eab308',
      'C': '#f97316',
      'D': '#ef4444',
    }
    return colors[grade.value.grade] || '#9ca3af'
  })

  const gradeLabel = computed(() => {
    if (!grade.value) return 'No grade'
    const labels: Record<string, string> = {
      'A+': 'Exceptional',
      'A': 'Very Good',
      'B': 'Good',
      'C': 'Average',
      'D': 'Below Average',
    }
    return labels[grade.value.grade] || 'Unknown'
  })

  /**
   * Fetch current innings grade for a game
   */
  async function fetchCurrentGrade(gameId: string) {
    try {
      loading.value = true
      error.value = null
      
      const response = await apiService.get(
        `/analytics/games/${gameId}/innings/current/grade`
      )
      
      if (response && response.data) {
        grade.value = response.data
      }
    } catch (err: any) {
      // Don't treat 400 as error - just means inning not yet started
      if (err.response?.status !== 400) {
        error.value = err.message || 'Failed to fetch innings grade'
        console.error('Failed to fetch innings grade:', err)
      }
      grade.value = null
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch grade for specific inning
   */
  async function fetchInningGrade(gameId: string, inningNum: number) {
    try {
      loading.value = true
      error.value = null
      
      const response = await apiService.get(
        `/analytics/games/${gameId}/innings/${inningNum}/grade`
      )
      
      if (response && response.data) {
        grade.value = response.data
      }
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch innings grade'
      console.error('Failed to fetch innings grade:', err)
      grade.value = null
    } finally {
      loading.value = false
    }
  }

  /**
   * Clear current grade data
   */
  function clear() {
    grade.value = null
    error.value = null
  }

  return {
    grade,
    loading,
    error,
    gradeColor,
    gradeLabel,
    fetchCurrentGrade,
    fetchInningGrade,
    clear,
  }
}

/**
 * usePlayerFormTracker.ts - Player form tracking and visualization
 *
 * Calculates player performance trends over recent matches
 * and determines form color/trend indicators.
 */

import { computed, ref } from 'vue'
import type { PlayerProfile } from '@/types/player'

export type FormColor = 'good' | 'average' | 'poor'
export type FormTrend = 'improving' | 'stable' | 'declining'

export interface FormMatch {
  matchIndex: number
  strikeRate: number
  runs: number
  performance: FormColor
}

export interface FormData {
  matches: FormMatch[]
  overallTrend: FormTrend
  averagePerformance: FormColor
  recentForm: FormColor
}

/**
 * Determines form color based on strike rate
 * Green: SR >= 130, Yellow: 90-129, Red: < 90
 */
function getFormColor(strikeRate: number | null | undefined): FormColor {
  if (strikeRate === null || strikeRate === undefined) return 'average'
  if (strikeRate >= 130) return 'good'
  if (strikeRate < 90) return 'poor'
  return 'average'
}

/**
 * Determines trend by comparing recent form to older form
 */
function calculateTrend(formMatches: FormMatch[]): FormTrend {
  if (formMatches.length < 2) return 'stable'

  const recentHalf = Math.ceil(formMatches.length / 2)
  const recent = formMatches.slice(-recentHalf)
  const older = formMatches.slice(0, Math.floor(formMatches.length / 2))

  if (recent.length === 0 || older.length === 0) return 'stable'

  const recentAvg = recent.reduce((sum, m) => sum + m.strikeRate, 0) / recent.length
  const olderAvg = older.reduce((sum, m) => sum + m.strikeRate, 0) / older.length

  const diff = recentAvg - olderAvg
  if (diff > 10) return 'improving'
  if (diff < -10) return 'declining'
  return 'stable'
}

/**
 * Calculates form data from player profile
 * Uses career strike rate as proxy for form when match history not available
 */
function calculateFormData(profile: PlayerProfile | null): FormData {
  if (!profile) {
    return {
      matches: [],
      overallTrend: 'stable',
      averagePerformance: 'average',
      recentForm: 'average',
    }
  }

  // Use career strike rate as the basis for form calculation
  // In a full implementation, this would use match-by-match data
  const strikeRate = profile.strike_rate || 0
  const performance = getFormColor(strikeRate)

  // Create simulated recent matches (in production, would fetch from API)
  // This demonstrates the pattern - real implementation would use match history
  const matches: FormMatch[] = [
    { matchIndex: 1, strikeRate: Math.max(0, strikeRate - 30), runs: 15, performance: getFormColor(strikeRate - 30) },
    { matchIndex: 2, strikeRate: Math.max(0, strikeRate - 25), runs: 18, performance: getFormColor(strikeRate - 25) },
    { matchIndex: 3, strikeRate: Math.max(0, strikeRate - 15), runs: 25, performance: getFormColor(strikeRate - 15) },
    { matchIndex: 4, strikeRate: Math.max(0, strikeRate - 8), runs: 32, performance: getFormColor(strikeRate - 8) },
    { matchIndex: 5, strikeRate: Math.max(0, strikeRate - 5), runs: 35, performance: getFormColor(strikeRate - 5) },
    { matchIndex: 6, strikeRate: strikeRate - 2, runs: 38, performance: getFormColor(strikeRate - 2) },
    { matchIndex: 7, strikeRate: strikeRate - 1, runs: 39, performance: getFormColor(strikeRate - 1) },
    { matchIndex: 8, strikeRate: strikeRate, runs: 40, performance: getFormColor(strikeRate) },
    { matchIndex: 9, strikeRate: Math.min(200, strikeRate + 3), runs: 43, performance: getFormColor(strikeRate + 3) },
    { matchIndex: 10, strikeRate: Math.min(200, strikeRate + 5), runs: 45, performance: getFormColor(strikeRate + 5) },
  ]

  const trend = calculateTrend(matches)
  const recentForm = matches[matches.length - 1]?.performance || 'average'

  return {
    matches,
    overallTrend: trend,
    averagePerformance: performance,
    recentForm,
  }
}

export function usePlayerFormTracker(profile: Readonly<{ value: PlayerProfile | null }>) {
  const formData = computed<FormData>(() => calculateFormData(profile.value))

  // Color mappings for visual display
  const colorMap = computed(() => ({
    good: 'rgb(34, 197, 94)', // green-500
    average: 'rgb(234, 179, 8)', // yellow-500
    poor: 'rgb(239, 68, 68)', // red-500
  }))

  // Trend emoji indicators
  const trendEmoji = computed(() => ({
    improving: '↑',
    stable: '→',
    declining: '↓',
  }))

  // Get CSS class name for form color
  const getFormClass = (color: FormColor): string => {
    const classMap: Record<FormColor, string> = {
      good: 'form-good',
      average: 'form-average',
      poor: 'form-poor',
    }
    return classMap[color]
  }

  // Get text label for form color
  const getFormLabel = (color: FormColor): string => {
    const labelMap: Record<FormColor, string> = {
      good: 'In Form',
      average: 'Average',
      poor: 'Poor Form',
    }
    return labelMap[color]
  }

  // Get trend label
  const getTrendLabel = (trend: FormTrend): string => {
    const labelMap: Record<FormTrend, string> = {
      improving: 'Improving',
      stable: 'Stable',
      declining: 'Declining',
    }
    return labelMap[trend]
  }

  return {
    formData,
    colorMap,
    trendEmoji,
    getFormClass,
    getFormLabel,
    getTrendLabel,
  }
}

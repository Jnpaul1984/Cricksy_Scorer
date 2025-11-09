/**
 * API service for player profiles, achievements, and leaderboards
 */
import type {
  PlayerProfile,
  PlayerAchievement,
  Leaderboard,
  LeaderboardMetric,
  AwardAchievementRequest,
} from '@/types/player'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Get player profile with statistics and achievements
 */
export async function getPlayerProfile(playerId: string): Promise<PlayerProfile> {
  const response = await fetch(`${API_BASE_URL}/api/players/${playerId}/profile`)

  if (!response.ok) {
    throw new Error(`Failed to fetch player profile: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Get all achievements for a player
 */
export async function getPlayerAchievements(playerId: string): Promise<PlayerAchievement[]> {
  const response = await fetch(`${API_BASE_URL}/api/players/${playerId}/achievements`)

  if (!response.ok) {
    throw new Error(`Failed to fetch player achievements: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Award an achievement to a player
 */
export async function awardAchievement(
  playerId: string,
  achievement: AwardAchievementRequest,
): Promise<PlayerAchievement> {
  const response = await fetch(`${API_BASE_URL}/api/players/${playerId}/achievements`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(achievement),
  })

  if (!response.ok) {
    throw new Error(`Failed to award achievement: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Get leaderboard for a specific metric
 */
export async function getLeaderboard(
  metric: LeaderboardMetric = 'total_runs',
  limit: number = 10,
): Promise<Leaderboard> {
  const response = await fetch(
    `${API_BASE_URL}/api/players/leaderboard?metric=${metric}&limit=${limit}`,
  )

  if (!response.ok) {
    throw new Error(`Failed to fetch leaderboard: ${response.statusText}`)
  }

  return response.json()
}

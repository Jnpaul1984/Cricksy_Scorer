/**
 * API service for player profiles, achievements, and leaderboards
 */
import { apiRequest } from '@/services/api';
import type {
  PlayerProfile,
  PlayerAchievement,
  Leaderboard,
  LeaderboardMetric,
  AwardAchievementRequest,
} from "@/types/player"

/**
 * Get player profile with statistics and achievements
 */
export async function getPlayerProfile(playerId: string): Promise<PlayerProfile> {
  return apiRequest<PlayerProfile>(`/api/players/${playerId}/profile`)
}

/**
 * Get all achievements for a player
 */
export async function getPlayerAchievements(playerId: string): Promise<PlayerAchievement[]> {
  return apiRequest<PlayerAchievement[]>(`/api/players/${playerId}/achievements`)
}

/**
 * Award an achievement to a player
 */
export async function awardAchievement(
  playerId: string,
  achievement: AwardAchievementRequest,
): Promise<PlayerAchievement> {
  return apiRequest<PlayerAchievement>(`/api/players/${playerId}/achievements`, {
    method: 'POST',
    body: JSON.stringify(achievement),
  })
}

/**
 * Get leaderboard for a specific metric
 */
export async function getLeaderboard(
  metric: LeaderboardMetric = 'total_runs',
  limit: number = 10,
): Promise<Leaderboard> {
  return apiRequest<Leaderboard>(`/api/players/leaderboard?metric=${metric}&limit=${limit}`)
}

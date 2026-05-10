import type { PlayerProfile, PlayerAchievement, Leaderboard, LeaderboardMetric, AwardAchievementRequest } from "@/types/player";
/**
 * Get player profile with statistics and achievements
 */
export declare function getPlayerProfile(playerId: string): Promise<PlayerProfile>;
/**
 * Get all achievements for a player
 */
export declare function getPlayerAchievements(playerId: string): Promise<PlayerAchievement[]>;
/**
 * Award an achievement to a player
 */
export declare function awardAchievement(playerId: string, achievement: AwardAchievementRequest): Promise<PlayerAchievement>;
/**
 * Get leaderboard for a specific metric
 */
export declare function getLeaderboard(metric?: LeaderboardMetric, limit?: number): Promise<Leaderboard>;

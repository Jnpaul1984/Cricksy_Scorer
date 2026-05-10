/**
 * API service for player profiles, achievements, and leaderboards
 */
import { apiRequest } from '@/services/api';
/**
 * Get player profile with statistics and achievements
 */
export async function getPlayerProfile(playerId) {
    return apiRequest(`/api/players/${playerId}/profile`);
}
/**
 * Get all achievements for a player
 */
export async function getPlayerAchievements(playerId) {
    return apiRequest(`/api/players/${playerId}/achievements`);
}
/**
 * Award an achievement to a player
 */
export async function awardAchievement(playerId, achievement) {
    return apiRequest(`/api/players/${playerId}/achievements`, {
        method: 'POST',
        body: JSON.stringify(achievement),
    });
}
/**
 * Get leaderboard for a specific metric
 */
export async function getLeaderboard(metric = 'total_runs', limit = 10) {
    return apiRequest(`/api/players/leaderboard?metric=${metric}&limit=${limit}`);
}

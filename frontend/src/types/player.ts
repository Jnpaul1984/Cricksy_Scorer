/**
 * Type definitions for player profiles, achievements, and leaderboards
 */

export interface PlayerProfile {
  player_id: string
  player_name: string

  // Batting statistics
  total_matches: number
  total_innings_batted: number
  total_runs_scored: number
  total_balls_faced: number
  total_fours: number
  total_sixes: number
  times_out: number
  highest_score: number
  centuries: number
  half_centuries: number
  batting_average: number
  strike_rate: number

  // Bowling statistics
  total_innings_bowled: number
  total_overs_bowled: number
  total_runs_conceded: number
  total_wickets: number
  best_bowling_figures: string | null
  five_wicket_hauls: number
  maidens: number
  bowling_average: number
  economy_rate: number

  // Fielding statistics
  catches: number
  stumpings: number
  run_outs: number

  // Timestamps
  created_at: string
  updated_at: string

  // Achievements
  achievements?: PlayerAchievement[]
}

export interface PlayerAchievement {
  id: number
  player_id: string
  game_id: string | null
  achievement_type: string
  title: string
  description: string
  badge_icon: string | null
  earned_at: string
  metadata: Record<string, unknown>
}

export interface LeaderboardEntry {
  rank: number
  player_id: string
  player_name: string
  value: number | string
  additional_stats: Record<string, unknown>
}

export interface Leaderboard {
  metric: string
  entries: LeaderboardEntry[]
  updated_at: string
}

export type LeaderboardMetric =
  | 'batting_average'
  | 'strike_rate'
  | 'total_runs'
  | 'centuries'
  | 'bowling_average'
  | 'economy_rate'
  | 'total_wickets'
  | 'five_wickets'

export interface AwardAchievementRequest {
  achievement_type: string
  title: string
  description: string
  badge_icon?: string | null
  game_id?: string | null
  metadata?: Record<string, unknown>
}

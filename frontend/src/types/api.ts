/**
 * API Type Definitions for Cricksy Scorer
 * 
 * These interfaces match the exact JSON schemas from the FastAPI backend
 * documentation to ensure type safety throughout the application.
 */

// ============================================================================
// REQUEST TYPES (Data sent TO the backend)
// ============================================================================

/**
 * Request body for POST /games - Creating a new 25-over cricket match
 */
export interface CreateGameRequest {
  team_a_name: string;
  team_b_name: string;
  players_a: string[];
  players_b: string[];
  toss_winner_team: string;
  decision: string; // "bat" or "bowl"
}

/**
 * Request body for POST /games/{game_id}/score - Scoring a delivery
 */
export interface ScoreDeliveryRequest {
  striker_id: string;
  non_striker_id: string;
  bowler_id: string;
  runs_scored: number;
  extra: string | null; // "wd" (wide) or "nb" (no ball) or null
  is_wicket: boolean;
}

// ============================================================================
// RESPONSE TYPES (Data received FROM the backend)
// ============================================================================

/**
 * Individual player structure
 */
export interface Player {
  id: string;
  name: string;
}

/**
 * Team structure containing name and list of players
 */
export interface Team {
  name: string;
  players: Player[];
}

/**
 * Individual delivery record with complete ball-by-ball information
 */
export interface Delivery {
  over_number: number;
  ball_number: number;
  bowler_id: string;
  striker_id: string;
  non_striker_id: string;
  runs_scored: number;
  is_extra: boolean;
  extra_type: string | null; // "wd", "nb", or null
  is_wicket: boolean;
  dismissal_type: string | null; // Type of dismissal if is_wicket is true
}

/**
 * Individual batting scorecard entry with player statistics
 */
export interface BattingScorecardEntry {
  player_id: string;
  player_name: string;
  runs: number;
  balls_faced: number;
  is_out: boolean;
}

/**
 * Individual bowling scorecard entry with bowler statistics
 */
export interface BowlingScorecardEntry {
  player_id: string;
  player_name: string;
  overs_bowled: number;
  runs_conceded: number;
  wickets_taken: number;
}

/**
 * First innings summary structure
 */
export interface FirstInningsSummary {
  runs: number;
  wickets: number;
  overs: number;
  balls: number;
}

/**
 * Complete game state - the main response type for all game-related endpoints
 * This represents the full state of a cricket match at any point in time
 */
export interface GameState {
  /** Unique identifier for the game */
  game_id: string;
  
  /** Team A details */
  team_a: Team;
  
  /** Team B details */
  team_b: Team;
  
  /** Number of overs per innings (always 25 for school matches) */
  overs_limit: number;
  
  /** Name of the team that won the toss */
  toss_winner_team: string;
  
  /** Toss decision: "bat" or "bowl" */
  decision: string;
  
  /** Name of the team currently batting */
  batting_team_name: string;
  
  /** Name of the team currently bowling */
  bowling_team_name: string;
  
  /** Current game status */
  status: string; // "in_progress" | "innings_break" | "completed"
  
  /** Current innings number (1 or 2) */
  current_inning: number;
  
  /** Total runs scored in current innings */
  total_runs: number;
  
  /** Total wickets fallen in current innings */
  total_wickets: number;
  
  /** Number of completed overs in current innings */
  overs_completed: number;
  
  /** Number of balls bowled in the current over (0-5) */
  balls_this_over: number;
  
  /** ID of the current striker (batsman on strike) */
  current_striker_id: string | null;
  
  /** ID of the current non-striker */
  current_non_striker_id: string | null;
  
  /** Summary of the first innings (null if first innings not complete) */
  first_inning_summary: FirstInningsSummary | null;
  
  /** Target runs for the second innings (first innings total + 1) */
  target: number | null;
  
  /** Final result of the match (null if not completed) */
  result: string | null;
  
  /** Complete ball-by-ball record of all deliveries */
  deliveries: Delivery[];
  
  /** Batting statistics for all players who have batted */
  batting_scorecard: Record<string, BattingScorecardEntry>;
  
  /** Bowling statistics for all players who have bowled */
  bowling_scorecard: Record<string, BowlingScorecardEntry>;
}

// ============================================================================
// UNION TYPES AND CONSTANTS
// ============================================================================

/**
 * Valid game status values
 */
export type GameStatusType = 'in_progress' | 'innings_break' | 'completed';

/**
 * Valid toss decision values
 */
export type TossDecision = 'bat' | 'bowl';

/**
 * Valid extra types
 */
export type ExtraType = 'wd' | 'nb';

/**
 * Valid dismissal types
 */
export type DismissalType = 
  | 'bowled'
  | 'caught'
  | 'lbw'
  | 'runout'
  | 'hit_wicket'
  | 'handled_the_ball'
  | 'retired_hurt';

// ============================================================================
// API RESPONSE WRAPPERS
// ============================================================================

/**
 * Standard API response wrapper for successful responses
 */
export interface ApiSuccessResponse<T> {
  data: T;
  success: true;
  message?: string;
}

/**
 * Standard API response wrapper for error responses
 */
export interface ApiErrorResponse {
  success: false;
  message: string;
  details?: any;
}

/**
 * Union type for all possible API responses
 */
export type ApiResponse<T> = ApiSuccessResponse<T> | ApiErrorResponse;

// ============================================================================
// HELPER TYPES FOR TYPE GUARDS
// ============================================================================

/**
 * Type guard to check if an API response is successful
 */
export function isApiSuccess<T>(response: ApiResponse<T>): response is ApiSuccessResponse<T> {
  return response.success === true;
}

/**
 * Type guard to check if an API response is an error
 */
export function isApiError<T>(response: ApiResponse<T>): response is ApiErrorResponse {
  return response.success === false;
}

/**
 * Type guard to check if a game is in progress
 */
export function isGameInProgress(game: GameState): boolean {
  return game.status === 'in_progress';
}

/**
 * Type guard to check if a game is at innings break
 */
export function isGameAtInningsBreak(game: GameState): boolean {
  return game.status === 'innings_break';
}

/**
 * Type guard to check if a game is completed
 */
export function isGameCompleted(game: GameState): boolean {
  return game.status === 'completed';
}


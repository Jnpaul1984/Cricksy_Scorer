// frontend/src/types/index.ts

/** Core domain types */
export type ID = string;

export type MatchType = 'limited' | 'multi_day' | 'custom';
export type MatchStatus = 'not_started' | 'in_progress' | 'innings_break' | 'completed';

export type ExtraCode = 'wd' | 'nb' | 'b' | 'lb';

/** Player & Team */
export interface Player {
  id: ID;
  name: string;
}

export interface Team {
  name: string;
  players: Player[];
}

/** Scorecard entries (snake_case to match current store usage) */
export interface BattingScorecardEntry {
  player_id: ID;
  player_name: string;

  runs: number;
  balls: number;
  fours: number;
  sixes: number;
  strike_rate: number;

  how_out?: string; // e.g. "c Smith b Khan", "lbw", "run out", etc.
  is_out: boolean;
}

export interface BowlingScorecardEntry {
  player_id: ID;
  player_name: string;

  // Overs can be "3.4" – represent as string for safety, but number is ok too
  overs: string | number;
  maidens: number;

  runs_conceded: number;
  wickets: number;
  economy: number;
}

export interface Delivery {
  over: number        // or string if you display "10.3"
  ball: number        // 1..6 (or 0..5)
  striker_id: string
  non_striker_id: string
  bowler_id: string
  runs: number
  extra?: 'wd' | 'nb' | 'b' | 'lb'
  is_wicket?: boolean
  dismissal_type?: string
  dismissed_player_id?: string | null
  commentary?: string
  at_utc?: string     // optional timestamp
}
/** Full game state stored in the store */
export interface GameState {
  id: ID;

  match_type: MatchType;
  status: MatchStatus;

  // teams
  team_a: Team;
  team_b: Team;

  // batting/bowling context
  batting_team_name: string;
  bowling_team_name: string;

  deliveries?: Delivery[];
  // current innings and score
  current_inning: number; // 1 | 2 | 3 | 4 (support multi-day)
  total_runs: number;
  total_wickets: number;
  overs_completed: number; // if you store "10.3" as string, change to string | number
  balls_this_over: number;

  // chase context (optional)
  target?: number | null;

  // per-player scorecards (keyed by player_id or any stable key)
  batting_scorecard: Record<string, BattingScorecardEntry>;
  bowling_scorecard: Record<string, BowlingScorecardEntry>;
}

/** Live snapshot payload that comes over the socket */
export interface Snapshot {
  // mirror only the fields you actually use in GameStore.applySnapshotToGame
  total_runs: number;
  total_wickets: number;
  overs_completed: number;
  balls_this_over: number;
  current_inning: number;
  status?: MatchStatus;
  target?: number | null;
  deliveries?: Delivery[];
  current_striker_id?: ID;
  current_non_striker_id?: ID;
  current_bowler_id?: ID;
  batting_team_name: string;
  bowling_team_name: string;

  batting_scorecard: Record<string, BattingScorecardEntry>;
  bowling_scorecard: Record<string, BowlingScorecardEntry>;
}

/** State update envelope from the server */
export interface StateUpdatePayload {
  id: ID;           // game id
  snapshot: Snapshot;
}

/** UI state kept in the store (used by GameStore.ts) */
export interface UIState {
  loading: boolean;
  error: string | null;

  selectedStrikerId: ID | null;
  selectedNonStrikerId: ID | null;
  selectedBowlerId: ID | null;

  scoringDisabled: boolean;
  activeScorecardTab: 'batting' | 'bowling';
}

/** Requests sent to the backend */
export interface CreateGameRequest {
  match_type: MatchType;

  team_a: {
    name: string;
    players: { id: ID; name: string }[];
  };
  team_b: {
    name: string;
    players: { id: ID; name: string }[];
  };

  // optional match setup fields — include/omit based on your backend
  overs?: number;                 // for limited overs
  days?: number;                  // for multi-day
  toss_winner?: 'A' | 'B';
  elected_to_bat?: 'A' | 'B';
  start_time_utc?: string;        // ISO string
}


export interface ScoreDeliveryRequest {
  striker_id: ID;
  non_striker_id: ID;
  bowler_id: ID;

  runs_scored: number;
  is_wicket: boolean;

  // optional fields depending on event
  extra?: ExtraCode;                  // 'wd' | 'nb' | 'b' | 'lb'
  dismissal_type?: string;            // e.g., 'bowled', 'lbw', 'run_out'
  dismissed_player_id?: ID | null;
  commentary?: string;
}

/** API error normalizer shape (if you need it elsewhere) */
export interface ApiErrorShape {
  message: string;
  code?: string | number;
  details?: unknown;
}

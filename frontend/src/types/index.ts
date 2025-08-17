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
  player_id: string
  player_name: string
  runs: number
  balls_faced: number
  is_out: boolean
  // optional UI fields if you compute them client-side
  fours?: number
  sixes?: number
  strike_rate?: number
}


export interface BowlingScorecardEntry {
  player_id: string
  player_name: string
  overs_bowled: number
  runs_conceded: number
  wickets_taken: number
  // optional UI fields if you compute them client-side
  maidens?: number
  economy?: number
}

export interface Delivery {
  over_number: number
  ball_number: number
  bowler_id: string
  striker_id: string
  non_striker_id: string
  runs_scored: number
  is_wicket: boolean
  dismissal_type: string | null
  dismissed_player_id: string | null
  commentary: string | null
  fielder_id: string | null
  // NEW optional fields for live appending
  extra_type?: 'wd' | 'nb' | 'b' | 'lb' | null
  at_utc?: string | null
}
/** Full game state stored in the store */
export interface GameState {
  id: string

  // config
  match_type: MatchType
  overs_limit: number | null
  days_limit: number | null
  overs_per_day?: number | null
  dls_enabled: boolean
  interruptions: Array<Record<string, string | null>>

  // toss & innings selection
  toss_winner_team: string
  decision: TossDecision

  // teams
  team_a: Team
  team_b: Team
  batting_team_name: string
  bowling_team_name: string

  // live status / progression
  status: MatchStatus
  current_inning: number
  total_runs: number
  total_wickets: number
  overs_completed: number
  balls_this_over: number
  current_striker_id: string | null
  current_non_striker_id: string | null
  target: number | null
  result: string | null

  // roles
  team_a_captain_id: string | null
  team_a_keeper_id: string | null
  team_b_captain_id: string | null
  team_b_keeper_id: string | null

  // ledger & scorecards
  deliveries: Array<Delivery>
  batting_scorecard: Record<string, BattingScorecardEntry>
  bowling_scorecard: Record<string, BowlingScorecardEntry>
}

/** Live snapshot payload that comes over the socket */
export interface Snapshot {
  total_runs?: number
  total_wickets?: number
  overs_completed?: number
  balls_this_over?: number
  current_inning?: number
  batting_team_name?: string
  bowling_team_name?: string

  current_striker_id?: string | null
  current_non_striker_id?: string | null
  target?: number | null
  status?: MatchStatus

  batting_scorecard?: Record<string, BattingScorecardEntry>
  bowling_scorecard?: Record<string, BowlingScorecardEntry>
  last_delivery?: Delivery | null

  // allow extra keys without breaking the UI
  [k: string]: any
}


/** State update envelope from the server */
export interface StateUpdatePayload {
  id: ID;           // game id
  snapshot: Snapshot;
}

export type TossDecision = 'bat' | 'bowl'

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
/** API error normalizer shape (if you need it elsewhere) */
export interface ApiErrorShape {
  message: string;
  code?: string | number;
  details?: unknown;
}

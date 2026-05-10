/** Core domain types */
export type ID = string;
export type MatchType = 'limited' | 'multi_day' | 'custom';
export type MatchStatus = 'not_started' | 'in_progress' | 'innings_break' | 'completed' | 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'ABANDONED';
export type ExtraCode = 'wd' | 'nb' | 'b' | 'lb';
/** Extras breakdown for scoreboard display */
export interface ExtrasBreakdown {
    total: number;
    wides: number;
    no_balls: number;
    byes: number;
    leg_byes: number;
}
export interface MatchResult {
    winner_team_id?: string | null;
    winner_team_name?: string | null;
    method?: 'by runs' | 'by wickets' | 'tie' | 'no result' | null;
    margin?: number | null;
    result_text?: string | null;
    completed_at?: string | null;
}
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
    player_id: string;
    player_name: string;
    runs: number;
    balls_faced: number;
    is_out: boolean;
    fours?: number;
    sixes?: number;
    strike_rate?: number;
}
export interface BowlingScorecardEntry {
    player_id: string;
    player_name: string;
    overs_bowled: number;
    runs_conceded: number;
    wickets_taken: number;
    maidens?: number;
    economy?: number;
}
export interface Delivery {
    over_number: number;
    ball_number: number;
    bowler_id: string;
    striker_id: string;
    non_striker_id: string;
    runs_scored: number;
    is_wicket: boolean;
    dismissal_type: string | null;
    dismissed_player_id: string | null;
    commentary: string | null;
    fielder_id: string | null;
    shot_angle_deg?: number | null;
    shot_map?: string | null;
    extra_type?: 'wd' | 'nb' | 'b' | 'lb' | null;
    at_utc?: string | null;
}
/** Full game state stored in the store */
export interface GameState {
    id: string;
    match_type: MatchType;
    overs_limit: number | null;
    days_limit: number | null;
    overs_per_day?: number | null;
    dls_enabled: boolean;
    interruptions: Array<Record<string, string | null>>;
    toss_winner_team: string;
    decision: TossDecision;
    team_a: Team;
    team_b: Team;
    batting_team_name: string;
    bowling_team_name: string;
    status: MatchStatus;
    current_inning: number;
    total_runs: number;
    total_wickets: number;
    overs_completed: number;
    balls_this_over: number;
    current_run_rate?: number;
    required_run_rate?: number;
    current_striker_id: string | null;
    current_non_striker_id: string | null;
    target: number | null;
    result: MatchResult | string | null;
    is_game_over?: boolean;
    completed_at?: string | null;
    team_a_captain_id: string | null;
    team_a_keeper_id: string | null;
    team_b_captain_id: string | null;
    team_b_keeper_id: string | null;
    deliveries: Array<Delivery>;
    batting_scorecard: Record<string, BattingScorecardEntry>;
    bowling_scorecard: Record<string, BowlingScorecardEntry>;
}
/** Live snapshot payload that comes over the socket */
export interface Snapshot {
    total_runs?: number;
    total_wickets?: number;
    overs_completed?: number;
    balls_this_over?: number;
    current_run_rate?: number;
    required_run_rate?: number;
    current_inning?: number;
    batting_team_name?: string;
    bowling_team_name?: string;
    current_striker_id?: string | null;
    current_non_striker_id?: string | null;
    target?: number | null;
    status?: MatchStatus;
    batting_scorecard?: Record<string, BattingScorecardEntry>;
    bowling_scorecard?: Record<string, BowlingScorecardEntry>;
    last_delivery?: Delivery | null;
    balls_remaining?: number;
    extras?: ExtrasBreakdown;
    last_updated?: string;
    needs_new_batter?: boolean;
    needs_new_over?: boolean;
    is_game_over?: boolean;
    result?: MatchResult | null;
    match_status?: MatchStatus;
    [k: string]: any;
}
/** State update envelope from the server */
export interface StateUpdatePayload {
    id: ID;
    snapshot: Snapshot;
}
export type TossDecision = 'bat' | 'bowl';
/** Requests sent to the backend */
export interface CreateGameRequest {
    match_type: MatchType;
    team_a: {
        name: string;
        players: {
            id: ID;
            name: string;
        }[];
    };
    team_b: {
        name: string;
        players: {
            id: ID;
            name: string;
        }[];
    };
    overs?: number;
    days?: number;
    toss_winner?: 'A' | 'B';
    elected_to_bat?: 'A' | 'B';
    start_time_utc?: string;
}
export interface ScoreDeliveryRequest {
    striker_id: ID;
    non_striker_id: ID;
    bowler_id: ID;
    runs_scored: number;
    is_wicket: boolean;
    extra?: ExtraCode;
    dismissal_type?: string;
    dismissed_player_id?: ID | null;
    commentary?: string;
    shot_angle_deg?: number | null;
    shot_map?: string | null;
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

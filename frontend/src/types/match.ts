// Generated match types based on complete match data structure

export interface Player {
  id: string;
  name: string;
}

export interface Team {
  name: string;
  players: Player[];
}

export interface Delivery {
  over_number: number;
  ball_number: number;
  bowler_id: string;
  striker_id: string;
  non_striker_id: string;
  runs_off_bat: number;
  extra_type: string | null;
  extra_runs: number;
  runs_scored: number;
  is_extra: boolean;
  is_wicket: boolean;
  dismissal_type: "caught" | "lbw" | "bowled" | null;
  dismissed_player_id: string | null;
  commentary: string | null;
  fielder_id: string | null;
  shot_map: any | null;
}

export interface Innings {
  innings_number: number;
  batting_team: string;
  bowling_team: string;
  deliveries: Delivery[];
}

export interface BattingEntry {
  player_id: string;
  player_name: string;
  runs: number;
  balls_faced: number;
  is_out: boolean;
}

export interface BowlingEntry {
  player_id: string;
  player_name: string;
  overs_bowled: number;
  runs_conceded: number;
  wickets_taken: number;
}

export interface InningsSummary {
  runs: number;
  wickets: number;
  overs: number;
  balls: number;
}

export interface Result {
  winner_team_id: string | null;
  winner_team_name: string;
  method: string;
  margin: number;
  result_text: string;
  completed_at: string | null;
}

export interface Match {
  id: string;
  team_a: Team;
  team_b: Team;
  match_type: string;
  overs_limit: number;
  days_limit: number | null;
  dls_enabled: boolean;
  interruptions: any[];
  toss_winner_team: string;
  decision: string;
  batting_team_name: string;
  bowling_team_name: string;
  status: string;
  current_inning: number;
  total_runs: number;
  total_wickets: number;
  overs_completed: number;
  balls_this_over: number;
  current_striker_id: string | null;
  current_non_striker_id: string | null;
  current_bowler_id: string | null;
  first_inning_summary: InningsSummary;
  target: number;
  result: Result;
  is_game_over: boolean;
  completed_at: string | null;
  team_a_captain_id: string | null;
  team_a_keeper_id: string | null;
  team_b_captain_id: string | null;
  team_b_keeper_id: string | null;
  innings: Innings[];
  batting_scorecard: Record<string, BattingEntry>;
  bowling_scorecard: Record<string, BowlingEntry>;
}

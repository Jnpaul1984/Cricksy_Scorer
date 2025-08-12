// src/types/index.ts

export type Player = { id: string; name: string }

export type Team = {
  name: string
  players: Player[]
}

export type BattingScorecardEntry = {
  player_id: string
  player_name: string
  runs: number
  balls_faced: number
  is_out: boolean
}

export type BowlingScorecardEntry = {
  player_id: string
  player_name: string
  overs_bowled: number
  runs_conceded: number
  wickets_taken: number
}

export type ExtraCode = 'wd' | 'nb' | 'b' | 'lb' // wide, no-ball, byes, leg byes
export type DismissalCode =
  | 'bowled'
  | 'caught'
  | 'lbw'
  | 'stumped'
  | 'run_out'
  | 'hit_wicket'
  | 'obstructing_the_field'
  | 'hit_ball_twice'
  | 'timed_out'
  | 'retired_out'
  | 'handled_ball'

export type Delivery = {
  over_number: number
  ball_number: number
  bowler_id: string
  striker_id: string
  non_striker_id: string
  runs_scored: number
  is_extra?: boolean
  extra_type?: ExtraCode | null
  is_wicket?: boolean
  dismissal_type?: DismissalCode | null
  dismissed_player_id?: string | null
  commentary?: string | null
  fielder_id?: string | null // backend may or may not send this yet
}

export type GameState = {
  id: string // ✅ fixes created.id usage
  // teams
  team_a: Team
  team_b: Team

  // config
  match_type: 'limited' | 'multi_day' | 'custom'
  overs_limit: number | null
  days_limit: number | null
  overs_per_day?: number | null
  dls_enabled: boolean
  interruptions: Array<Record<string, string | null>>

  toss_winner_team: string
  decision: 'bat' | 'bowl'
  batting_team_name: string
  bowling_team_name: string

  // status
  status: string
  current_inning: number
  total_runs: number
  total_wickets: number
  overs_completed: number
  balls_this_over: number
  current_striker_id: string | null
  current_non_striker_id: string | null
  target: number | null
  result: string | null

  // timelines & scorecards
  deliveries: Delivery[]
  batting_scorecard: Record<string, BattingScorecardEntry>
  bowling_scorecard: Record<string, BowlingScorecardEntry>
}

export type CreateGameRequest = {
  team_a_name: string
  team_b_name: string
  players_a: string[]
  players_b: string[]
  match_type: 'limited' | 'multi_day' | 'custom'
  overs_limit?: number | null
  days_limit?: number | null
  overs_per_day?: number | null
  dls_enabled: boolean
  interruptions: Array<Record<string, string | null>>
  toss_winner_team: string
  decision: 'bat' | 'bowl'
}

export type ScoreDeliveryRequest = {
  striker_id: string
  non_striker_id: string
  bowler_id: string
  runs_scored: number
  is_wicket: boolean
  extra?: ExtraCode
  dismissal_type?: DismissalCode
  dismissed_player_id?: string
  commentary?: string
  fielder_id?: string
}

/** Socket snapshot payloads from backend `state:update` */
export type Snapshot = {
  id: string
  status: string
  score: { runs: number; wickets: number; overs: number }
  batsmen: {
    striker: { id: string | null; name: string; runs: number; balls: number; is_out: boolean }
    non_striker: { id: string | null; name: string; runs: number; balls: number; is_out: boolean }
  }
  over: { completed: number; balls_this_over: number }
  last_delivery: Delivery
}

export type StateUpdatePayload = { id: string; snapshot: Snapshot }

/** UI-only shape the store uses */
export type UIState = {
  loading: boolean
  error: string | null
  selectedStrikerId: string | null
  selectedNonStrikerId: string | null
  selectedBowlerId: string | null
  scoringDisabled: boolean
  activeScorecardTab: 'batting' | 'bowling'
}

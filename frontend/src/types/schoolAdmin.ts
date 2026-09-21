export type SchoolMembershipRole = 'owner' | 'admin' | 'coach' | 'scorer' | 'viewer';
export type SchoolRosterStatus = 'active' | 'inactive';

export interface SchoolOrganization {
  id: string;
  name: string;
  organization_type: 'school';
  status: 'active' | 'suspended' | 'archived';
  membership_role: SchoolMembershipRole;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}
export interface SchoolCreateInput {
  name: string;
  organization_type?: 'school';
}

export interface SchoolMembership {
  id: string;
  organization_id: string;
  user_id: string;
  role: SchoolMembershipRole;
  status: 'active' | 'disabled';
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface SchoolEntitlement {
  id: string;
  organization_id: string;
  plan_key: 'school_free';
  status: 'active' | 'disabled';
  source: 'system' | 'admin' | 'billing';
  effective_from: string;
  effective_until: string | null;
  capabilities: string[];
  excluded_capabilities: string[];
  created_at: string;
  updated_at: string;
}

export interface SchoolTeam {
  id: string;
  organization_id: string;
  name: string;
  status: 'active' | 'archived';
  home_ground: string | null;
  season: string | null;
  owner_user_id: string | null;
  coach_user_id: string | null;
  coach_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface SchoolTeamInput {
  name: string;
  home_ground?: string | null;
  season?: string | null;
  coach_name?: string | null;
}

export interface SchoolRosterPlayer {
  id: string;
  organization_id: string;
  player_profile_id: string;
  player_name: string;
  status: SchoolRosterStatus;
  student_identifier: string | null;
  year_group: string | null;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface SchoolTeamRosterPlayer {
  id: string;
  organization_id: string;
  team_id: string;
  school_player_membership_id: string;
  player_profile_id: string;
  player_name: string;
  status: SchoolRosterStatus;
  school_player_status: SchoolRosterStatus;
  team_status: 'active' | 'archived';
  operationally_available: boolean;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface SchoolMatchSideSelection {
  team_id: string;
  playing_xi_membership_ids: string[];
  captain_membership_id: string;
  wicketkeeper_membership_id: string;
}

export interface SchoolMatchCreate {
  mode: 'school_vs_school' | 'school_vs_external';
  school_side: 'team_a' | 'team_b' | null;
  team_a: SchoolMatchSideSelection | null;
  team_b: SchoolMatchSideSelection | null;
  external_opponent: {
    team_name: string;
    player_names: string[];
    captain_index: number;
    wicketkeeper_index: number;
  } | null;
  match_type: 'limited' | 'multi_day' | 'custom';
  overs_limit: number | null;
  days_limit: number | null;
  overs_per_day: number | null;
  dls_enabled: boolean;
  toss_winner_side: 'team_a' | 'team_b';
  decision: 'bat' | 'bowl';
}

export interface SchoolMatchCreateResult {
  game_id: string;
  organization_id: string;
  team_a_id: string | null;
  team_b_id: string | null;
  team_a_name: string;
  team_b_name: string;
  team_a_player_profile_ids: string[];
  team_b_player_profile_ids: string[];
}

export interface SchoolPlayerStatistics {
  player_profile_id: string;
  player_name: string;
  roster_status: SchoolRosterStatus;
  matches: number;
  innings: number;
  runs: number;
  highest_score: number;
  batting_average: number | null;
  balls_faced: number;
  strike_rate: number;
  fours: number;
  sixes: number;
  bowling_innings: number;
  balls_bowled: number;
  overs: string;
  runs_conceded: number;
  wickets: number;
  bowling_average: number | null;
  economy: number | null;
  best_bowling: string | null;
}

export interface SchoolTeamStatistics {
  team_id: string;
  team_name: string;
  team_status: 'active' | 'archived';
  matches: number;
  wins: number;
  losses: number;
  ties: number;
  draws: number;
  no_results: number;
  runs_scored: number;
  runs_conceded: number;
  wickets_taken: number;
  wickets_lost: number;
}

export type SchoolPublicationState = 'private' | 'published_live' | 'published_final';

export interface SchoolMatchResult {
  game_id: string;
  team_a_id: string | null;
  team_a_name: string;
  team_b_id: string | null;
  team_b_name: string;
  status: string;
  result: string | null;
  publication_state: SchoolPublicationState;
  current_inning: number;
  team_a_runs: number;
  team_a_wickets: number;
  team_b_runs: number;
  team_b_wickets: number;
  public_scorecard_available: boolean;
}

export interface SchoolCompetition {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  tournament_type: 'league' | 'knockout' | 'round-robin';
  start_date: string | null;
  end_date: string | null;
  status: 'upcoming' | 'ongoing' | 'completed';
  created_at: string;
  updated_at: string;
}

export interface SchoolCompetitionTeam {
  id: number;
  tournament_id: string;
  team_id: string;
  team_name: string;
}

export interface SchoolFixture {
  id: string;
  tournament_id: string;
  team_a_id: string;
  team_b_id: string;
  team_a_name: string;
  team_b_name: string;
  match_number: number | null;
  venue: string | null;
  scheduled_date: string | null;
  game_id: string | null;
  status: 'scheduled' | 'in_progress' | 'completed' | 'cancelled';
  created_at: string;
  updated_at: string;
}

export interface SchoolFixtureSummary {
  fixture_id: string;
  competition_id: string;
  competition_name: string;
  team_a_id: string;
  team_a_name: string;
  team_b_id: string;
  team_b_name: string;
  match_number: number | null;
  venue: string | null;
  scheduled_date: string | null;
  fixture_status: string;
  game_id: string | null;
  game_status: string | null;
  result: string | null;
  publication_state: SchoolPublicationState | null;
  public_scorecard_available: boolean;
}

export interface SchoolStandingEntry {
  team_id: string;
  team_name: string;
  matches_played: number;
  matches_won: number;
  matches_lost: number;
  matches_drawn: number;
  points: number;
}

export interface SchoolStandings {
  competition_id: string;
  entries: SchoolStandingEntry[];
  unresolved_completed_games: number;
}

export interface PublicSchoolScorecard {
  game_id: string;
  publication_state: Exclude<SchoolPublicationState, 'private'>;
  status: string;
  team_a: { name: string; players: Array<{ name: string }> };
  team_b: { name: string; players: Array<{ name: string }> };
  match_type: string;
  overs_limit: number | null;
  days_limit: number | null;
  overs_per_day: number | null;
  toss_winner_team: string | null;
  decision: string | null;
  batting_team_name: string | null;
  bowling_team_name: string | null;
  total_runs: number;
  total_wickets: number;
  overs_completed: number;
  balls_this_over: number;
  current_inning: number;
  result: string | null;
  batting_scorecard: PublicScorecardEntry[];
  bowling_scorecard: PublicScorecardEntry[];
}

export interface PublicScorecardEntry {
  player_name: string;
  runs?: number | null;
  balls_faced?: number | null;
  fours?: number | null;
  sixes?: number | null;
  is_out?: boolean | null;
  how_out?: string | null;
  overs_bowled?: number | null;
  runs_conceded?: number | null;
  wickets_taken?: number | null;
}

export type ImportClassification =
  | 'create_new'
  | 'duplicate_existing_school_membership'
  | 'ambiguous_needs_review'
  | 'invalid'
  | 'team_assignment_only';

export type ImportResolutionAction = 'create_new' | 'use_existing' | 'reactivate_existing' | 'skip';

export interface PlayerImportCandidate {
  school_player_membership_id: string;
  player_name: string;
  status: SchoolRosterStatus;
}

export interface PlayerImportTeamCandidate {
  team_id: string;
  team_name: string;
}

export interface PlayerImportPreviewRow {
  source_row_number: number;
  values: {
    player_name: string | null;
    student_identifier: string | null;
    year_group: string | null;
    team_name: string | null;
  };
  classification: ImportClassification;
  validation_errors: string[];
  warnings: string[];
  ambiguity_reason: string | null;
  resolution_required: boolean;
  candidate_memberships: PlayerImportCandidate[];
  resolved_school_player_membership_id: string | null;
  team_candidates: PlayerImportTeamCandidate[];
  resolved_team_id: string | null;
}

export interface PlayerImportPreview {
  import_id: string;
  file_type: 'csv' | 'xlsx';
  original_filename: string;
  content_sha256: string;
  row_count: number;
  column_mapping: Record<string, string>;
  expires_at: string;
  rows: PlayerImportPreviewRow[];
}

export interface PlayerImportResolution {
  source_row_number: number;
  action: ImportResolutionAction;
  school_player_membership_id?: string;
  team_id?: string;
}

export interface PlayerImportResult {
  import_id: string;
  status: 'applied';
  applied_at: string;
  summary: {
    created_players: number;
    linked_existing_players: number;
    reactivated_memberships: number;
    team_assignments_created: number;
    team_assignments_reactivated: number;
    no_op_rows: number;
    skipped_rows: number;
    failed_rows: number;
  };
  rows: Array<{
    source_row_number: number;
    outcome:
      | 'created'
      | 'linked_existing'
      | 'reactivated'
      | 'team_assigned'
      | 'no_op'
      | 'skipped'
      | 'failed';
    school_player_membership_id: string | null;
    player_profile_id: string | null;
    team_id: string | null;
    detail: string;
  }>;
}

export interface SchoolApiError extends Error {
  status?: number;
  detail?: unknown;
}

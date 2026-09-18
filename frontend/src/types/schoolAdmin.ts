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
  team_a: SchoolMatchSideSelection;
  team_b: SchoolMatchSideSelection;
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
  team_a_id: string;
  team_b_id: string;
  team_a_name: string;
  team_b_name: string;
  team_a_player_profile_ids: string[];
  team_b_player_profile_ids: string[];
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

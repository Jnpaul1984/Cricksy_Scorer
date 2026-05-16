/**
 * frontend/src/services/playerDevelopmentApi.ts
 *
 * Phase 9D — API client for Phase 9C player development endpoints.
 *
 * Consumes:
 *   POST /api/player-development/players/{player_id}/draft-plan
 *   GET  /api/player-development/plans/{plan_id}
 *   GET  /api/player-development/players/{player_id}/plans
 *
 * All plans returned are advisory/draft only. No activation or approval
 * mutation is supported here. This file must not be used on player-facing
 * or public surfaces.
 */

import { API_BASE, getStoredToken } from './api';

// ---------------------------------------------------------------------------
// Error class
// ---------------------------------------------------------------------------

export class PlayerDevelopmentApiError extends Error {
  constructor(
    message: string,
    public readonly status: number = 500,
    public readonly code?: string,
  ) {
    super(message);
    this.name = 'PlayerDevelopmentApiError';
  }

  isUnauthenticated(): boolean {
    return this.status === 401;
  }

  isUnauthorized(): boolean {
    return this.status === 403;
  }

  isNotFound(): boolean {
    return this.status === 404;
  }

  isValidationError(): boolean {
    return this.status === 422;
  }

  isInsufficientData(): boolean {
    return this.code === 'insufficient_data';
  }
}

// ---------------------------------------------------------------------------
// Shared/internal helpers
// ---------------------------------------------------------------------------

async function fetchWithAuth<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  if (!token) {
    throw new PlayerDevelopmentApiError(
      'No authentication token. Please log in.',
      401,
      '401_UNAUTHENTICATED',
    );
  }

  const headers = new Headers(options.headers);
  headers.set('Authorization', `Bearer ${token}`);
  if (options.method && options.method !== 'GET') {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 204) return undefined as T;

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const detail =
      typeof data?.detail === 'string' ? data.detail : `${res.status} ${res.statusText}`;
    const code = res.headers.get('X-Error-Code') ?? undefined;
    throw new PlayerDevelopmentApiError(detail, res.status, code);
  }

  return data as T;
}

// ---------------------------------------------------------------------------
// Response types — mirrors backend schemas.py Phase 9B/9C definitions
// ---------------------------------------------------------------------------

export type PlanStatus = 'draft' | 'active' | 'paused' | 'completed' | 'archived';
export type ApprovalState = 'not_required' | 'pending_review' | 'approved' | 'rejected' | 'changes_requested';
export type SourceType = 'match_data' | 'video_analysis' | 'coach_note' | 'ai_insight' | 'manual';
export type Severity = 'low' | 'medium' | 'high';

export interface EvidenceRef {
  type: string;
  id: string;
  label: string;
}

export interface AiMetadata {
  output_type?: string;
  is_official_truth?: boolean;
  requires_review?: boolean;
  confidence_score?: number | null;
  limitations?: string[];
  source_refs?: EvidenceRef[];
  [key: string]: unknown;
}

export interface PlayerDevelopmentPlanRead {
  id: string;
  player_profile_id: string;
  coach_user_id: string;
  org_id: string;
  title: string;
  summary: string | null;
  status: PlanStatus;
  source_type: SourceType;
  coach_approved: boolean;
  approval_state: ApprovalState;
  confidence_score: number | null;
  evidence_refs: EvidenceRef[];
  ai_metadata: AiMetadata;
  activated_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlayerDevelopmentGoalRead {
  id: string;
  plan_id: string;
  title: string;
  description: string | null;
  target_metric: string | null;
  baseline_value: number | null;
  target_value: number | null;
  current_value: number | null;
  unit: string | null;
  status: PlanStatus;
  due_date: string | null;
  evidence_refs: EvidenceRef[];
  created_at: string;
  updated_at: string;
}

export interface PlayerWeaknessTagRead {
  id: string;
  plan_id: string;
  player_profile_id: string;
  category: string;
  /** Internal label — do NOT display directly; use safe_display_label instead. */
  label: string;
  /** Youth-safe display label for coach UI. Always prefer this over label. */
  safe_display_label: string;
  severity: Severity;
  confidence_score: number | null;
  source_type: SourceType;
  evidence_refs: EvidenceRef[];
  ai_metadata: AiMetadata;
  created_at: string;
  updated_at: string;
}

export interface PlayerStrengthTagRead {
  id: string;
  plan_id: string;
  player_profile_id: string;
  category: string;
  label: string;
  confidence_score: number | null;
  source_type: SourceType;
  evidence_refs: EvidenceRef[];
  ai_metadata: AiMetadata;
  created_at: string;
  updated_at: string;
}

export interface PlayerDrillAssignmentRead {
  id: string;
  plan_id: string;
  player_profile_id: string;
  coach_user_id: string;
  drill_category: string;
  drill_name: string;
  drill_description: string | null;
  frequency: string | null;
  status: PlanStatus;
  assigned_at: string | null;
  due_date: string | null;
  completed_at: string | null;
  evidence_refs: EvidenceRef[];
  created_at: string;
  updated_at: string;
}

export interface PlayerProgressCheckpointRead {
  id: string;
  plan_id: string;
  player_profile_id: string;
  coach_user_id: string;
  checkpoint_date: string;
  summary: string;
  progress_status: string;
  confidence_score: number | null;
  evidence_refs: EvidenceRef[];
  ai_metadata: AiMetadata;
  coach_notes: string | null;
  created_at: string;
  updated_at: string;
}

/** Full plan bundle returned by GET /plans/{plan_id} and GET /players/{id}/plans */
export interface PlayerDevelopmentPlanDraftBundle {
  plan: PlayerDevelopmentPlanRead;
  goals: PlayerDevelopmentGoalRead[];
  weakness_tags: PlayerWeaknessTagRead[];
  strength_tags: PlayerStrengthTagRead[];
  drill_assignments: PlayerDrillAssignmentRead[];
  progress_checkpoints: PlayerProgressCheckpointRead[];
}

/** Response returned by POST /players/{id}/draft-plan */
export interface DraftPlanGenerationResponse {
  status: 'draft_created' | 'insufficient_data';
  player_profile_id: string;
  plan: PlayerDevelopmentPlanDraftBundle | null;
  evidence_refs: EvidenceRef[];
  confidence_score: number | null;
  limitations: string[];
  /** Always true from the backend — plans are always draft and require coach review. */
  coach_review_required: boolean;
}

/** Optional payload for draft plan generation */
export interface DraftPlanGeneratePayload {
  additional_evidence_refs?: EvidenceRef[];
}

/** Minimal coach player assignment record for listing assigned players */
export interface CoachPlayerAssignmentRead {
  id: string;
  coach_user_id: string;
  player_profile_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Public API functions
// ---------------------------------------------------------------------------

/**
 * Generate a new draft player development plan for the given player.
 *
 * Returns a `DraftPlanGenerationResponse` where:
 * - `status === "draft_created"` means a plan bundle is present.
 * - `status === "insufficient_data"` means the backend could not produce a plan
 *   because player evidence was too thin. No fake plan is fabricated.
 *
 * Throws `PlayerDevelopmentApiError` on permission (403), not-found (404),
 * validation (422), or network errors.
 */
export async function generateDraftPlayerDevelopmentPlan(
  playerId: string,
  payload?: DraftPlanGeneratePayload,
): Promise<DraftPlanGenerationResponse> {
  return fetchWithAuth<DraftPlanGenerationResponse>(
    `/api/player-development/players/${encodeURIComponent(playerId)}/draft-plan`,
    {
      method: 'POST',
      body: payload ? JSON.stringify(payload) : JSON.stringify({}),
    },
  );
}

/**
 * Retrieve a single draft plan bundle by plan ID.
 *
 * Throws `PlayerDevelopmentApiError` (404) when the plan does not exist,
 * and (403) when the caller is not permitted to view it.
 */
export async function getPlayerDevelopmentPlan(
  planId: string,
): Promise<PlayerDevelopmentPlanDraftBundle> {
  return fetchWithAuth<PlayerDevelopmentPlanDraftBundle>(
    `/api/player-development/plans/${encodeURIComponent(planId)}`,
  );
}

/**
 * List all visible draft plan bundles for a player.
 *
 * Returns an empty array when no plans exist (never throws for empty).
 * Throws `PlayerDevelopmentApiError` on permission (403) or not-found (404).
 */
export async function listPlayerDevelopmentPlans(
  playerId: string,
): Promise<PlayerDevelopmentPlanDraftBundle[]> {
  return fetchWithAuth<PlayerDevelopmentPlanDraftBundle[]>(
    `/api/player-development/players/${encodeURIComponent(playerId)}/plans`,
  );
}

/**
 * List the coach's currently assigned players.
 * Uses GET /api/coaches/me/players (coach_pro / org_pro only).
 */
export async function listCoachAssignedPlayers(): Promise<CoachPlayerAssignmentRead[]> {
  return fetchWithAuth<CoachPlayerAssignmentRead[]>('/api/coaches/me/players');
}

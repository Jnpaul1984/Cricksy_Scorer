// src/services/api.ts
// Single, canonical API client aligned with FastAPI backend & the Pinia game store.

import type { MatchResult } from '@/types';

export type ScoreUpdatePayload = any;

const VITE_BASE = typeof import.meta !== 'undefined' ? import.meta.env?.VITE_API_BASE : '';
const LEGACY_BASE =
  typeof import.meta !== 'undefined' ? import.meta.env?.VITE_API_BASE_URL : '';

const RUNTIME_ORIGIN =
  typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.host}` : '';

// Parse ?apiBase= from the URL as a runtime override
function getApiBaseFromUrl(): string {
  if (typeof window === 'undefined') return '';
  try {
    const params = new URLSearchParams(window.location.search);
    // Check hash-based routing (#/route?apiBase=...)
    const hashParams = window.location.hash.includes('?')
      ? new URLSearchParams(window.location.hash.split('?')[1])
      : null;
    return (params.get('apiBase') || hashParams?.get('apiBase') || '').replace(/\/+$/, '');
  } catch {
    return '';
  }
}

const URL_OVERRIDE = getApiBaseFromUrl();

export const API_BASE = (URL_OVERRIDE || VITE_BASE || LEGACY_BASE || RUNTIME_ORIGIN || '').replace(/\/+$/, '');

// Production-grade logging for API_BASE resolution
const isProduction = import.meta.env.PROD;
if (isProduction && API_BASE === RUNTIME_ORIGIN && !URL_OVERRIDE) {
  console.warn(
    '⚠️ PRODUCTION WARNING: API_BASE fell back to window.origin.',
    'This means VITE_API_BASE and VITE_API_BASE_URL are not set.',
    'Expected: API endpoint URL. Got:', API_BASE
  );
}
console.info('API_BASE resolved to:', API_BASE, '| Source:',
  URL_OVERRIDE ? '?apiBase override' :
  VITE_BASE ? 'VITE_API_BASE' :
  LEGACY_BASE ? 'VITE_API_BASE_URL' :
  'window.origin (fallback)'
);

export const TOKEN_STORAGE_KEY = 'cricksy_token';

type UnauthorizedHandler = (error: Error) => void;
let unauthorizedHandler: UnauthorizedHandler | null = null;

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
  unauthorizedHandler = handler;
}

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token: string | null) {
  if (typeof window === 'undefined') return;
  try {
    if (!token) {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    } else {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    }
  } catch {
    // ignore storage errors (Safari private mode, etc.)
  }
}

function getAuthHeader(): Record<string, string> | null {
  const token = getStoredToken();
  if (!token) return null;
  return { Authorization: `Bearer ${token}` };
}

function notifyUnauthorized(err: Error) {
  if (unauthorizedHandler) {
    unauthorizedHandler(err);
    return;
  }
  console.warn('[api] 401 unauthorized', err.message);
}

function url(path: string) {
  if (!API_BASE) return path;
  const base = API_BASE.replace(/\/+$/, '');
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${base}${p}`;
}

export function getErrorMessage(err: unknown): string {
  if (!err) return 'Unknown error';
  if (typeof err === 'string') return err;
  if (err instanceof Error) return err.message || 'Error';
  try {
    const anyErr = err as any;
    if (anyErr?.detail) return String(anyErr.detail);
    if (anyErr?.message) return String(anyErr.message);
    if (anyErr?.response?.data?.detail) return String(anyErr.response.data.detail);
    if (anyErr?.status && anyErr?.statusText) return `${anyErr.status} ${anyErr.statusText}`;
  } catch {
    // ignore JSON parsing issues when mining error metadata
  }
  return 'Request failed';
}

export type TossDecision = 'bat' | 'bowl';

type ApiRequestOptions = RequestInit & {
  /** If true, do NOT attach the Authorization header even if a token is present. */
  noAuth?: boolean;
};

/** Low-level fetch wrapper that preserves JSON errors from FastAPI. */
async function request<T>(path: string, init?: ApiRequestOptions): Promise<T> {
  const method = (init?.method || 'GET').toUpperCase()
  const hasBody = init?.body !== undefined && init?.body !== null
  const isForm = typeof FormData !== 'undefined' && init?.body instanceof FormData
  const isUrlParams = typeof URLSearchParams !== 'undefined' && init?.body instanceof URLSearchParams
  const isJSONish = hasBody && !isForm && !isUrlParams && typeof init?.body === 'string'
  const authHeader = init?.noAuth ? null : getAuthHeader()

  const res = await fetch(url(path), {
    // For GETs, make results uncacheable so live UI always sees fresh data.
    cache: method === 'GET' ? 'no-store' : init?.cache,
    // If you use cookie/session auth, uncomment the next line:
    // credentials: 'include',
    headers: {
      ...(isJSONish ? { 'Content-Type': 'application/json' } : {}),
      ...(method === 'GET' ? { 'Cache-Control': 'no-store' } : {}),
      ...(authHeader || {}),
      ...(init?.headers || {}),
    },
    ...init,
  })

  if (!res.ok) {
    let detail: any = undefined
    try { detail = await res.json() } catch {
      // ignore body parsing errors when building error info
    }
    const msg = detail?.detail || `${res.status} ${res.statusText}`
    const err = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    // @ts-expect-error  attach HTTP status for downstream handlers
    err.status = res.status
    // @ts-expect-error  attach API error payload when available
    err.detail = detail?.detail ?? null
    if (res.status === 401) {
      notifyUnauthorized(err)
    }
    throw err
  }

  if (res.status === 204) return undefined as unknown as T
  return (await res.json()) as T
}

export function apiRequestPublic<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const base: ApiRequestOptions = init ? { ...init } : {}
  base.noAuth = true
  return request<T>(path, base)
}

export { request as apiRequest };


/* ----------------------------- Types (client) ----------------------------- */

// Create game  mirrors backend CreateGameRequest in main.py
export type MatchType = 'limited' | 'multi_day' | 'custom';
export type Decision = 'bat' | 'bowl';
export type ExtraCode = 'nb' | 'wd' | 'b' | 'lb';

export interface CreateGameRequest {
  team_a_name: string;
  team_b_name: string;
  players_a: string[]; // names
  players_b: string[]; // names
  match_type?: MatchType;
  overs_limit?: number | null;
  days_limit?: number | null;
  overs_per_day?: number | null;
  dls_enabled?: boolean;
  interruptions?: Array<Record<string, string | null>>;
  toss_winner_team: string; // must equal team_a_name or team_b_name
  decision: TossDecision; // 'bat' or 'bowl'
}

export interface GameMinimal {
  id: string;
  team_a_name: string;
  team_b_name: string;
  match_type: MatchType;
  overs_limit: number | null;
  days_limit: number | null;
  dls_enabled: boolean;
  decision: TossDecision;
  // plus many more fields the backend returns; we keep it loose for UI
  [k: string]: any;
}

// Score a delivery  mirrors backend schemas.ScoreDelivery in main.py
export interface ScoreDeliveryRequest {
  striker_id: string;
  non_striker_id: string;
  bowler_id: string;

  // scoring
  runs_off_bat?: number;    // use ONLY for no-balls (off-the-bat runs; server adds +1 penalty)
  runs_scored?: number;     // legal balls (total off bat), or the EXTRA COUNT for wd/b/lb
  extra?: 'wd' | 'nb' | 'b' | 'lb';

  // wicket
  is_wicket: boolean;
  dismissal_type?: string | null;
  dismissed_player_id?: string | null;
  // UX: optional name instead of ID; backend resolves
  dismissed_player_name?: string | null;
  commentary?: string;
  fielder_id?: string | null;
  shot_angle_deg?: number | null;
  shot_map?: string | null;
}

// Delivery correction payload - mirrors backend DeliveryCorrection model
export interface DeliveryCorrectionRequest {
  runs_scored?: number;
  runs_off_bat?: number;
  extra?: 'wd' | 'nb' | 'b' | 'lb' | null;
  is_wicket?: boolean;
  dismissal_type?: string | null;
  dismissed_player_id?: string | null;
  fielder_id?: string | null;
  shot_map?: string | null;
  shot_angle_deg?: number | null;
  commentary?: string | null;
}

// Snapshot  shape can vary; we keep it open but document common fields
export interface Snapshot {
  id?: string;
  status?: string;
  score?: { runs: number; wickets: number; overs: number | string };
  batsmen: {
    striker: { id: string | null; name: string; runs: number; balls: number; is_out: boolean };
    non_striker: { id: string | null; name: string; runs: number; balls: number; is_out: boolean };
  };
  current_bowler: { id: string | null; name: string | null };
  overs: string;
  total_runs?: number;
  total_wickets?: number;
  overs_completed?: number;
  balls_this_over?: number;
  current_inning?: number;
  batting_team_name?: string;
  bowling_team_name?: string;
  batting_scorecard?: Record<string, any>;
  bowling_scorecard?: Record<string, any>;
  last_delivery?: {
    over_number: number;
    ball_number: number;
    bowler_id: string;
    striker_id: string;
    non_striker_id: string;
    // NEW fields coming from backend snapshot
    runs_off_bat?: number;
    extra_type?: ExtraCode | null;
    extra_runs?: number;
    runs_scored?: number; // total for this ball
    shot_map?: string | null;
  } | null;
    // NEW from backend
  dls?: { method: 'DLS'; par?: number; target?: number; ahead_by?: number };
  extras_totals?: {
    wides: number; no_balls: number; byes: number; leg_byes: number; penalty: number; total: number;
  };
  fall_of_wickets?: Array<{
    score: number; wicket: number; batter_id: string; batter_name: string;
    over: string; dismissal_type?: string | null;
    bowler_id?: string | null; bowler_name?: string | null;
    fielder_id?: string | null;
    shot_angle_deg?: number | null;
    fielder_name?: string | null;
  }>;
  last_ball_bowler_id?: string | null;
  current_bowler_id?: string | null;
  balls_bowled_total?: number;
  needs_new_innings?: boolean;
  teams?: { batting: { name: string }; bowling: { name: string } };
  players?: {
    batting: Array<{ id: string; name: string }>;
    bowling: Array<{ id: string; name: string }>;
  };
  interruptions?: Interruption[];
  mini_batting_card?: any[];
  mini_bowling_card?: any[];

  // Gate flags (NEW)
  needs_new_batter?: boolean;
  needs_new_over?: boolean;

  [k: string]: any;
}

export interface OversLimitBody {
  overs_limit: number;
}

export type TeamSide = 'A' | 'B';
export interface TeamRoleUpdate {
  side: TeamSide;
  captain_id?: string | null;
  wicket_keeper_id?: string | null;
}

export interface ContributorIn {
  user_id: string;
  role: 'SCORER' | 'COMMENTATOR' | 'ANALYST' | 'VIEWER';
  display_name?: string | null;
}
export interface Contributor {
  id: number;
  game_id: string;
  user_id: string;
  role: ContributorIn['role'];
  display_name?: string | null;
}

export interface SponsorCreateBody {
  name: string;
  logo: File; // svg/png/webp, <=5MB
  click_url?: string | null;
  weight?: number; // 1..5
  surfaces?: string[]; // defaults to ["all"]
  start_at?: string | null; // ISO-8601
  end_at?: string | null;   // ISO-8601
}
export interface SponsorRow {
  id: string;
  name: string;
  logoUrl: string;
  clickUrl?: string | null;
  weight: number;
  surfaces: string[];
  is_active?: boolean;
  start_at?: string | null;
  end_at?: string | null;
}
export interface SponsorImpressionIn {
  game_id: string;
  sponsor_id: string | number;
  at?: string | null; // ISO time
}
export interface SponsorImpressionsOut {
  inserted: number;
  ids: number[];
}

// New endpoint bodies (minimal)
export interface StartOverBody {
  bowler_id: string;
}
export interface ReplaceBatterBody {
  new_batter_id: string;
}
export interface MidOverChangeBody {
  new_bowler_id: string;
  reason?: 'injury' | 'other';
}
export interface OpenersBody {
  striker_id: string;
  non_striker_id: string;
}
export interface NextBatterBody {
  batter_id: string;
}

// below other endpoint bodies
export interface StartNextInningsBody {
  striker_id?: string | null;
  non_striker_id?: string | null;
  opening_bowler_id?: string | null;
}

// --- interruptions (robust) ---

export type Interruption = {
  id: string
  kind: 'weather' | 'injury' | 'light' | string
  note?: string | null
  started_at: string
  ended_at?: string | null
}

async function getInterruptions(gameId: string): Promise<Interruption[]> {
  const r = await request<any>(`/games/${encodeURIComponent(gameId)}/interruptions`)
  return Array.isArray(r) ? r
    : Array.isArray(r?.items) ? r.items
    : Array.isArray(r?.interruptions) ? r.interruptions
    : []
}

/** POST /interruptions/start with best-effort encoding */
async function openInterruption(
  gameId: string,
  kind: 'weather' | 'injury' | 'light' | 'other' | string = 'weather',
  note?: string
): Promise<Interruption> {
  const path = `/games/${encodeURIComponent(gameId)}/interruptions/start`

  // try JSON {kind, note}
  try {
    const r = await request<any>(path, { method: 'POST', body: JSON.stringify({ kind, note }) })
    return Array.isArray(r?.interruptions) ? r.interruptions.at(-1) : (r as Interruption)
  } catch (e: any) {
    // then form-encoded
    if (e?.status === 400 || e?.status === 422) {
      try {
        const body = new URLSearchParams()
        body.set('kind', kind)
        if (note) body.set('note', note)
        const res = await fetch(url(path), {
          method: 'POST',
          body,
          headers: {
            ...(getAuthHeader() || {}),
          },
        }) // browser sets proper header
        if (!res.ok) throw res
        const j = await res.json()
        return Array.isArray(j?.interruptions) ? j.interruptions.at(-1) : (j as Interruption)
      } catch {
        // ignoring fallback failure; we attempt querystring next
      }
      // finally querystring (no body)
      const qs = new URLSearchParams({ kind, ...(note ? { note } : {}) }).toString()
      const res = await fetch(url(`${path}?${qs}`), {
        method: 'POST',
        headers: {
          ...(getAuthHeader() || {}),
        },
      })
      if (!res.ok) {
        let detail: any; try { detail = await res.json() } catch {
          // ignore parse failure for error handling
        }
        const err = new Error(detail?.detail || `${res.status} ${res.statusText}`)
        // @ts-expect-error  expose HTTP status for UI messaging
        err.status = res.status
        // @ts-expect-error  attach API detail payload for callers
        err.detail = detail?.detail ?? null
        throw err
      }
      const j = await res.json()
      return Array.isArray(j?.interruptions) ? j.interruptions.at(-1) : (j as Interruption)
    }
    throw e
  }
}

/** POST /interruptions/stop  omit {"kind": null}. Accepts JSON, falls back to empty body. */
async function stopInterruption(
  gameId: string,
  kind?: 'weather' | 'injury' | 'light' | 'other'
): Promise<{ ok: true; interruptions: Interruption[] }> {
  const path = `/games/${encodeURIComponent(gameId)}/interruptions/stop`
  try {
    if (kind) {
      return await request(path, { method: 'POST', body: JSON.stringify({ kind }) }) as any
    }
    // empty body
    return await request(path, { method: 'POST' }) as any
  } catch (e: any) {
    const msg = (e?.detail || e?.message || '').toString().toLowerCase()
    // treat no active interruption as success
    if (e?.status === 400 && (msg.includes('no active') || msg.includes('already stopped'))) {
      return { ok: true, interruptions: [] }
    }
    // try one more time with no body
    if (kind && (e?.status === 400 || e?.status === 422)) {
      return await request(path, { method: 'POST' }) as any
    }
    throw e
  }
}

export { getInterruptions, openInterruption, stopInterruption }


/* ----------------------------- DLS helpers (optional routes enabled on server) ----------------------------- */

export type DLSPreviewOut = {
  team1_score: number;
  team1_resources: number;
  team2_resources: number;
  target: number;
  format_overs: 20 | 50;
  G50: number;
};

// 1) Add these helper types near the other DLS bits (optional but tidy)
export interface DlsRevisedTargetIn {
  kind: 'odi' | 't20';
  innings: 1 | 2;
  max_overs?: number;
}
export interface DlsRevisedTargetOut {
  R1_total: number;
  R2_total: number;
  S1: number;
  target: number;
}

export interface DlsParNowIn {
  kind: 'odi' | 't20';
  innings: 1 | 2;
  max_overs?: number;
}
export interface DlsParNowOut {
  R1_total: number;
  R2_used: number;
  S1: number;
  par: number;
  ahead_by: number;
}

export async function getDlsPreview(gameId: string, G50 = 245): Promise<DLSPreviewOut> {
  return request<DLSPreviewOut>(`/games/${encodeURIComponent(gameId)}/dls/preview?G50=${G50}`)
}

export async function postDlsApply(
  gameId: string,
  G50 = 245
): Promise<DLSPreviewOut & { applied: boolean }> {
  return request<DLSPreviewOut & { applied: boolean }>(
    `/games/${encodeURIComponent(gameId)}/dls/apply?G50=${G50}`,
    { method: 'POST' }
  )
}

export async function patchReduceOvers(gameId: string, innings: 1 | 2, newOvers: number) {
  return request<{ innings: number; new_overs: number; new_balls_limit: number }>(
    `/games/${encodeURIComponent(gameId)}/overs/reduce`,
    {
      method: 'PATCH',
      body: JSON.stringify({ innings, new_overs: newOvers }),
    }
  )
}


/* ----------------------------- Case Study Types ----------------------------- */

export interface CaseStudyInningsSummary {
  team: string;
  runs: number;
  wickets: number;
  overs: number;
  run_rate: number;
}

export type CaseStudyPhaseImpact = "positive" | "negative" | "neutral";

export interface CaseStudyPhase {
  id: "powerplay" | "middle" | "death" | "custom";
  label: string;
  start_over: number;
  end_over: number;
  runs: number;
  wickets: number;
  run_rate: number;
  net_swing_vs_par: number;
  impact: CaseStudyPhaseImpact;
  impact_label: string;
  innings_index?: number | null;
  team?: string | null;
  level?: "innings" | "match";
}

export type CaseStudyAnalysisMode = "limited_overs" | "odi_limited_overs" | "t20_limited_overs" | "test_multi_day" | "unknown";

export interface CaseStudyKeyPlayer {
  id: string;
  name: string;
  team: string;
  role: string;
  batting?: {
    innings: number;
    runs: number;
    balls: number;
    strike_rate: number;
    boundaries: {
      fours: number;
      sixes: number;
    };
  } | null;
  bowling?: {
    overs: number;
    maidens: number;
    runs: number;
    wickets: number;
    economy: number;
  } | null;
  fielding?: {
    catches: number;
    run_outs: number;
    drops: number;
  } | null;
  impact: "high" | "medium" | "low";
  impact_label: string;
  impact_score?: number | null;
}

export interface CaseStudyMatch {
  id: string;
  date: string;
  format: "T20" | "ODI" | "TEST" | "CUSTOM" | string;
  home_team?: string | null;
  away_team?: string | null;
  teams_label: string;
  venue?: string | null;
  event_name?: string | null;
  season?: string | null;
  match_number?: number | null;
  source_dates?: string[];
  result: string;
  overs_per_side?: number | null;
  innings: CaseStudyInningsSummary[];
}

export interface CaseStudyMomentumSummary {
  title: string;
  subtitle: string;
  winning_side?: string | null;
  innings_index?: number | null;
  phase_id?: string | null;
  level?: "innings" | "match";
  swing_metric?: {
    runs_above_par?: number | null;
    win_probability_shift?: number | null;
  } | null;
}

export interface CaseStudyKeyPhase {
  title: string;
  detail: string;
  innings_index?: number | null;
  team?: string | null;
  level?: "innings" | "match";
  overs_range?: {
    start_over: number;
    end_over: number;
  } | null;
  reason_codes?: string[];
}

export interface CaseStudyDismissalPatterns {
  level?: "innings" | "match";
  innings_index?: number | null;
  summary?: string | null;
  total_wickets?: number;
  wickets_by_phase?: { phase_id: string; wickets: number }[];
  wickets_by_over_band?: { band: string; wickets: number }[];
  dismissal_types?: { type: string; wickets: number }[];
  bowler_involvement?: { name: string; wickets: number }[];
  fielding_involvement?: { name: string; dismissals: number }[];
  dismissed_batters?: string[];
  wicket_timeline?: Array<{
    wicket_number: number;
    over: number;
    ball?: number;
    phase?: string | null;
    dismissal_type?: string | null;
    batter?: string | null;
    bowler?: string | null;
    fielder?: string | null;
  }>;
  wicket_cluster_callout?: string | null;
  fallback_reason?: string | null;
  by_bowler_type?: { type: string; wickets: number }[];
  by_shot_type?: { shot: string; wickets: number }[];
  by_zone?: { zone: string; wickets: number }[];
}

export interface CaseStudyStoryBlocks {
  opening_story: string;
  middle_overs_story: string;
  death_overs_story: string;
  scoring_acceleration: string;
  wickets_by_phase: string;
  strongest_phase: string;
  weakest_phase: string;
  innings_outcome_contribution: string;
}

export interface CaseStudyAnalystCallout {
  title: string;
  level: "innings" | "match";
  innings?: number | null;
  phase: string;
  category: "batting" | "bowling" | "player" | "dismissal" | "momentum" | "outcome";
  severity: "positive" | "warning" | "info";
  explanation: string;
  source_metrics: string[];
  confidence: number;
  why_it_matters: string;
}

export interface CaseStudyInningsAnalysis {
  innings_index: number;
  team: string;
  deterministic_summary: string;
  momentum_summary: CaseStudyMomentumSummary;
  key_phase: CaseStudyKeyPhase;
  phases: CaseStudyPhase[];
  key_players: CaseStudyKeyPlayer[];
  key_players_scope: "innings" | "match";
  dismissal_patterns: CaseStudyDismissalPatterns;
  story_blocks: CaseStudyStoryBlocks;
  callouts: CaseStudyAnalystCallout[];
}

export interface CaseStudyMultiDayInningsContext {
  innings_number: number;
  team: string;
  runs: number;
  wickets: number;
  overs: number;
  deliveries?: number | null;
  lead_deficit_after_innings?: number | null;
}

export interface CaseStudyFourthInningsChase {
  target: number;
  chasing_team: string;
  runs_scored: number;
  wickets_lost: number;
  wickets_in_hand: number;
  chase_result: "completed" | "fell_short" | "unknown";
  runs_margin?: number | null;
  pressure_note?: string | null;
}

export interface CaseStudyWicketCluster {
  innings_number: number;
  overs_start: number;
  overs_end: number;
  wickets: number;
  label: string;
}

export interface CaseStudyRecoveryWindow {
  innings_number: number;
  overs_start: number;
  overs_end: number;
  runs_scored: number;
  wickets_fell: number;
  label: string;
}

export interface CaseStudyMultiDaySummary {
  match_status: "won" | "lost" | "draw" | "tie" | "no_result" | "unknown";
  innings: CaseStudyMultiDayInningsContext[];
  fourth_innings_chase_note?: string | null;
  first_innings_lead_note?: string | null;
  lead_swing_notes?: string[];
  fourth_innings_chase?: CaseStudyFourthInningsChase | null;
  wicket_clusters?: CaseStudyWicketCluster[];
  recovery_windows?: CaseStudyRecoveryWindow[];
  match_turning_point?: string | null;
  notice: string;
}

export interface CaseStudyODIRequiredRateSnapshot {
  over: number;
  label: string;
  runs_needed: number;
  overs_remaining: number;
  required_rate: number;
}

export interface CaseStudyODIChaseIntelligence {
  target: number;
  chasing_team: string;
  initial_required_rate: number;
  required_rate_snapshots: CaseStudyODIRequiredRateSnapshot[];
  final_10_overs_summary?: string | null;
  chase_pressure_note?: string | null;
  chase_result: "completed" | "fell_short" | "in_progress" | "unknown";
  runs_margin?: number | null;
  wickets_in_hand?: number | null;
  pressure_windows: string[];
  data_quality: "full" | "partial" | "unavailable";
}

export interface CaseStudyODIPartnershipRecord {
  batter_1: string;
  batter_2: string;
  runs: number;
  balls: number;
  run_rate: number;
  start_over?: number | null;
  end_over?: number | null;
}

export interface CaseStudyODIPartnershipIntelligence {
  innings_number: number;
  highest_partnership?: CaseStudyODIPartnershipRecord | null;
  best_run_rate_partnership?: CaseStudyODIPartnershipRecord | null;
  rebuilding_partnership?: CaseStudyODIPartnershipRecord | null;
  summary: string;
  data_quality: "full" | "partial" | "unavailable";
}

export interface CaseStudyODIScoreboardComparison {
  team_1: string;
  team_1_runs: number;
  team_1_wickets: number;
  team_1_run_rate: number;
  team_1_strongest_phase?: string | null;
  team_1_weakest_phase?: string | null;
  team_1_death_runs?: number | null;
  team_1_death_wickets?: number | null;
  team_2: string;
  team_2_runs: number;
  team_2_wickets: number;
  team_2_run_rate: number;
  team_2_strongest_phase?: string | null;
  team_2_weakest_phase?: string | null;
  team_2_death_runs?: number | null;
  team_2_death_wickets?: number | null;
  run_differential: number;
  final_margin?: string | null;
}

export interface CaseStudyODIIntelligence {
  chase_intelligence?: CaseStudyODIChaseIntelligence | null;
  partnerships: CaseStudyODIPartnershipIntelligence[];
  scoreboard_comparison?: CaseStudyODIScoreboardComparison | null;
  turning_point_candidate?: string | null;
}

export interface CaseStudyAIBlock {
  match_summary: string;
  generated_at?: string | null;
  model_version?: string | null;
  tokens_used?: number | null;
}

export interface MatchCaseStudyResponse {
  analysis_mode: CaseStudyAnalysisMode;
  match: CaseStudyMatch;
  momentum_summary: CaseStudyMomentumSummary;
  key_phase: CaseStudyKeyPhase;
  phases: CaseStudyPhase[];
  key_players: CaseStudyKeyPlayer[];
  dismissal_patterns?: CaseStudyDismissalPatterns | null;
  innings_analysis?: CaseStudyInningsAnalysis[];
  match_callouts?: CaseStudyAnalystCallout[];
  match_level_summary?: string | null;
  multi_day_summary?: CaseStudyMultiDaySummary | null;
  odi_intelligence?: CaseStudyODIIntelligence | null;
  ai?: CaseStudyAIBlock | null;
}

export async function getMatchCaseStudy(matchId: string): Promise<MatchCaseStudyResponse> {
  return request<MatchCaseStudyResponse>(
    `/analytics/matches/${encodeURIComponent(matchId)}/case-study`
  );
}

/* ----------------------------- AI Match Summary ----------------------------- */

export interface MatchAiSummaryTeam {
  team_id: string;
  team_name: string;
  result: 'won' | 'lost' | 'tied' | 'no_result';
  total_runs: number;
  wickets_lost: number;
  overs_faced: number;
  key_stats: string[];
}

export interface DecisivePhaseSummary {
  phase_id: string;
  innings: number;
  label: string;
  over_range: [number, number];
  impact_score: number;
  narrative: string;
}

export interface MomentumShiftSummary {
  shift_id: string;
  innings: number;
  over: number;
  description: string;
  impact_delta: number;
  team_benefiting_id: string;
}

export interface PlayerHighlightSummary {
  player_id: string;
  player_name: string;
  team_id: string;
  role: string;
  highlight_type: string;
  summary: string;
}

export interface AiOutputMetadata {
  output_type: string;
  is_official_truth: boolean;
  requires_review?: boolean;
  grounded_in_data?: boolean;
  confidence_score?: number | null;
  limitations?: string[];
  source_refs?: Array<{
    type: string;
    id: string;
    label: string;
  }>;
  grounding_summary?: string | null;
}

export interface MatchAiSummary {
  match_id: string;
  format: string;
  teams: MatchAiSummaryTeam[];
  key_themes: string[];
  decisive_phases: DecisivePhaseSummary[];
  momentum_shifts: MomentumShiftSummary[];
  player_highlights: PlayerHighlightSummary[];
  overall_summary: string;
  created_at: string;
  // Legacy fields for backward compatibility
  headline?: string;
  narrative?: string;
  tactical_themes?: string[];
  tags?: string[];
  generated_at?: string;
  ai_metadata?: AiOutputMetadata;
}

export async function getMatchAiSummary(matchId: string): Promise<MatchAiSummary> {
  return request<MatchAiSummary>(
    `/analyst/matches/${encodeURIComponent(matchId)}/ai-summary`
  );
}

/* ----------------------------- Analyst Workspace Matches ----------------------------- */

export interface AnalystMatchListItem {
  id: string;
  date: string; // ISO date string
  format: string; // e.g. "T20", "ODI", "TEST", "CUSTOM"
  teams: string; // e.g. "Lions vs Falcons"
  result: string; // e.g. "Lions won by 18 runs"
  run_rate: number; // overall match run rate
  phase_swing: string; // e.g. "+18 in death", "-12 in powerplay"
  status: string;
  venue?: string | null;
  event_name?: string | null; // competition/event name from historical import
  season?: string | null; // season identifier from historical import
  match_number?: number | null; // match number within event
  source_dates?: string[]; // original source date strings from historical import
  match_datetime?: string | null;
  is_historical?: boolean;
  source?: string;
  historical_batch_id?: string | null;
}

export interface AnalystMatchListResponse {
  items: AnalystMatchListItem[];
  total: number;
}

export async function getAnalystMatches(): Promise<AnalystMatchListResponse> {
  return request<AnalystMatchListResponse>('/analytics/matches');
}

export interface AnalystPlayerAggregateItem {
  player: string;
  role: string;
  innings: number;
  matches: number;
  runs: number;
  strike_rate: number;
  wickets: number;
  economy: number;
}

export interface AnalystPlayersResponse {
  items: AnalystPlayerAggregateItem[];
  total: number;
  data_completeness: string;
}

export async function getAnalystPlayers(matchId?: string | null): Promise<AnalystPlayersResponse> {
  const params = new URLSearchParams();
  if (matchId) params.set('match_id', matchId);
  const query = params.toString();
  return request<AnalystPlayersResponse>(`/api/analyst/players${query ? `?${query}` : ''}`);
}

export interface AnalystDeliveryRow {
  match_id: string;
  innings: number | null;
  team: string | null;
  over_number: number | null;
  ball_number: number | null;
  batter: string | null;
  bowler: string | null;
  non_striker: string | null;
  runs_off_bat: number;
  extra_runs: number;
  total_runs: number;
  extra_type: string | null;
  wicket: boolean;
  dismissal_type: string | null;
  player_out: string | null;
  fielders: string[];
  phase: string | null;
  data_completeness: string;
}

export interface AnalystDeliveriesResponse {
  items: AnalystDeliveryRow[];
  total: number;
  data_completeness: string;
}

export async function getAnalystDeliveries(matchId?: string | null): Promise<AnalystDeliveriesResponse> {
  const params = new URLSearchParams();
  if (matchId) params.set('match_id', matchId);
  const query = params.toString();
  return request<AnalystDeliveriesResponse>(`/api/analyst/deliveries${query ? `?${query}` : ''}`);
}

/**
 * Phase 5M / Phase 10B: Registry metadata, provenance, and training eligibility for a match.
 * Returned by GET /analytics/matches/{matchId}/registry.
 */
export interface MatchRegistryResponse {
  match_id: string;
  is_historical: boolean;
  // Competition context (Phase 5M)
  competition: string | null;
  season: string | null;
  venue: string | null;
  teams: string | null;
  match_number: number | null;
  player_count: number;
  innings_count: number;
  has_deliveries: boolean;
  // Competition-aware fields (Phase 10B)
  competition_type: string | null;
  competition_name: string | null;
  match_format: string | null;
  tournament_name: string | null;
  tournament_round: string | null;
  venue_context: Record<string, unknown> | null;
  roster_snapshot_available: boolean;
  // Import batch / source provenance (Phase 5M)
  import_batch_id: string | null;
  source_filename: string | null;
  source_format: string | null;
  source_type: string;
  imported_at: string | null;
  // Provenance adapter lineage (Phase 10B)
  source_schema: string | null;
  source_schema_version: string | null;
  adapter_id: string | null;
  adapter_version: string | null;
  // Validation / registration / training eligibility
  validation_status: string; // "valid"|"invalid"|"unsupported"|"not_applicable"|"unknown"
  registration_status: string; // "registered"|"not_registered"
  training_eligible: boolean;
  blocking_reason: string | null;
}

/**
 * GET /analytics/matches/{matchId}/registry
 * Returns registry metadata, provenance, and training eligibility for a match.
 * Phase 5M: Cricket Data Registry Foundation.
 */
export async function getMatchRegistry(matchId: string): Promise<MatchRegistryResponse> {
  return request<MatchRegistryResponse>(
    `/analytics/matches/${encodeURIComponent(matchId)}/registry`,
  );
}

/* ------------------- Analyst Match Registry (Phase 10M) ------------------- */

/**
 * A single entry in the unified Analyst Match Registry.
 * Mirrors backend AnalystRegistryEntry schema.
 */
export interface AnalystRegistryEntry {
  match_id: string;
  match_title: string;
  team_a: string;
  team_b: string;
  canonical_team_a: string | null;
  canonical_team_b: string | null;
  competition_name: string | null;
  competition_code: string; // CPL_MEN | WCPL | unknown
  season: string | null;
  season_year: number | null;
  gender_category: string; // men | women | mixed | unknown
  age_category: string; // senior | youth | school | unknown
  format: string; // T20 | ODI | TEST | custom | unknown
  venue_raw: string | null;
  venue_canonical: string | null;
  match_date: string | null;
  source_type: string; // historical_import | cricksy_completed_scored | unknown
  data_completeness: string; // metadata_only | innings_totals | phase_level | delivery_complete
  has_delivery_data: boolean;
  has_phase_data: boolean;
  has_scorecard_data: boolean;
  result: string | null;
  analyst_ready: boolean;
}

/**
 * Response from GET /analytics/matches/registry (Phase 10M).
 */
export interface AnalystMatchRegistryListResponse {
  entries: AnalystRegistryEntry[];
  total: number;
  diagnostics: Record<string, number>;
}

/**
 * GET /analytics/matches/registry
 * Returns the unified Analyst Match Registry for the authenticated user.
 * Phase 10M: Analyst Data Registry + Unified Match Intelligence Foundation.
 */
export async function getAnalystRegistry(): Promise<AnalystMatchRegistryListResponse> {
  return request<AnalystMatchRegistryListResponse>('/analytics/matches/registry');
}

/* --------- Tournament Intelligence (Phase 10S.1) --------- */

export interface TournamentGroupKey {
  competition_code: string;
  competition_name: string | null;
  season: string | null;
  season_year: number | null;
  gender_category: string;
  format_family: string;
  source_type: string;
}

export interface TournamentGroupSummary {
  group_key: TournamentGroupKey;
  match_count: number;
  teams_count: number;
  has_result_data: boolean;
  has_delivery_data: boolean;
  champion_detected: boolean;
  champion_team: string | null;
  confidence: 'high' | 'medium' | 'low' | 'unknown';
}

export interface TournamentGroupsResponse {
  groups: TournamentGroupSummary[];
  total_groups: number;
  total_matches: number;
}

export interface DerivedStandingsRow {
  team_name: string;
  canonical_team_name: string | null;
  played: number;
  wins: number;
  losses: number;
  ties: number;
  no_results: number;
  points: number;
  net_run_rate: number | null;
  nrr_available: boolean;
  confidence: 'high' | 'medium' | 'low';
  note: string;
}

export interface TournamentMatchHighlight {
  match_id: string;
  match_title: string;
  match_date: string | null;
  stage_label: string | null;
  result: string | null;
  highlight_type: string;
  detail: string | null;
}

export interface TournamentPlayerLeader {
  player_name: string;
  value: number;
  matches_contributed: number;
  stat_type: string;
  source: string;
  confidence: 'high' | 'medium' | 'low';
}

export interface TournamentDataCompleteness {
  total_matches: number;
  matches_with_result: number;
  matches_missing_result: number;
  delivery_complete_matches: number;
  phase_level_matches: number;
  innings_totals_matches: number;
  metadata_only_matches: number;
  confidence_level: string;
  note: string;
}

export interface TournamentKnockoutContext {
  champion_team: string | null;
  champion_team_canonical: string | null;
  runner_up_team: string | null;
  runner_up_team_canonical: string | null;
  final_match_id: string | null;
  final_match_title: string | null;
  final_match_date: string | null;
  final_result: string | null;
  semi_final_matches: TournamentMatchHighlight[];
  qualifier_matches: TournamentMatchHighlight[];
  outcome_source: string;
  confidence: string;
}

export interface TournamentPodcastFacts {
  competition_label: string | null;
  season_label: string | null;
  champion: string | null;
  finalist: string | null;
  strongest_team_by_wins: string | null;
  top_scoring_venue: string | null;
  highest_scoring_match_title: string | null;
  highest_match_total_runs: number | null;
  key_journey_note: string | null;
  confidence: string;
  source_label: string;
}

export interface TournamentSummaryResponse {
  group_key: TournamentGroupKey;
  match_count: number;
  teams: string[];
  venues: string[];
  total_runs: number;
  total_wickets: number;
  highest_team_total: number | null;
  highest_team_total_by: string | null;
  lowest_completed_total: number | null;
  lowest_completed_total_by: string | null;
  closest_match: TournamentMatchHighlight | null;
  biggest_win_by_runs: TournamentMatchHighlight | null;
  biggest_win_by_wickets: TournamentMatchHighlight | null;
  top_run_scorer: TournamentPlayerLeader | null;
  top_wicket_taker: TournamentPlayerLeader | null;
  derived_standings: DerivedStandingsRow[];
  standings_label: string;
  knockout_context: TournamentKnockoutContext | null;
  data_completeness: TournamentDataCompleteness;
  podcast_facts: TournamentPodcastFacts | null;
}

export interface TeamJourneyMatch {
  match_id: string;
  match_title: string;
  match_date: string | null;
  opponent: string;
  venue: string | null;
  result: string | null;
  outcome: string;
  team_runs: number | null;
  opponent_runs: number | null;
  stage_label: string | null;
  highlight: string | null;
}

export interface TeamJourneySummary {
  wins: number;
  losses: number;
  ties: number;
  no_results: number;
  total_runs_for: number;
  total_runs_against: number;
  best_win: TeamJourneyMatch | null;
  worst_defeat: TeamJourneyMatch | null;
  closest_match: TeamJourneyMatch | null;
  top_scorer_name: string | null;
  top_scorer_runs: number | null;
  note: string;
}

export interface TeamJourneyResponse {
  team_name: string;
  canonical_team_name: string | null;
  group_key: TournamentGroupKey;
  matches: TeamJourneyMatch[];
  summary: TeamJourneySummary;
  note: string;
}

// ---------------------------------------------------------------------------
// Phase 10S.2 — Tournament Podcast Rundown types
// ---------------------------------------------------------------------------

export interface TournamentPodcastSection {
  section_key: string;
  title: string;
  body: string | null;
  confidence: string;
  note: string;
}

export interface TournamentChampionJourney {
  champion_team: string | null;
  final_opponent: string | null;
  final_result: string | null;
  derived_group_standing: string | null;
  best_win_title: string | null;
  closest_match_title: string | null;
  key_note: string | null;
  confidence: string;
  source_label: string;
}

export interface TournamentRoadToFinal {
  finalist_a: string | null;
  finalist_b: string | null;
  final_result: string | null;
  semi_final_titles: string[];
  qualifier_titles: string[];
  narrative: string | null;
  confidence: string;
  source_label: string;
}

export interface TournamentSeasonReview {
  competition_label: string;
  season_label: string | null;
  narrative: string;
  confidence: string;
  source_label: string;
}

export interface TournamentPodcastRundown {
  group_key: TournamentGroupKey;
  season_review: TournamentSeasonReview;
  champion_journey: TournamentChampionJourney | null;
  road_to_final: TournamentRoadToFinal | null;
  sections: TournamentPodcastSection[];
  overall_confidence: string;
  source_label: string;
  generated_at: string;
  note: string;
}

/**
 * GET /analytics/tournament-intelligence/groups
 * Phase 10S.1: Returns all discoverable tournament/season groups.
 */
export async function getTournamentGroups(): Promise<TournamentGroupsResponse> {
  return request<TournamentGroupsResponse>('/analytics/tournament-intelligence/groups');
}

/**
 * GET /analytics/tournament-intelligence/summary
 * Phase 10S.1: Returns full tournament intelligence for one group.
 */
export async function getTournamentSummary(
  competitionCode: string,
  season?: string | null,
  genderCategory?: string,
): Promise<TournamentSummaryResponse> {
  const params = new URLSearchParams({ competition_code: competitionCode });
  if (season) params.set('season', season);
  if (genderCategory) params.set('gender_category', genderCategory);
  return request<TournamentSummaryResponse>(
    `/analytics/tournament-intelligence/summary?${params.toString()}`,
  );
}

/**
 * GET /analytics/tournament-intelligence/team-journey
 * Phase 10S.1: Returns a team's journey within a competition/season.
 */
export async function getTeamJourney(
  competitionCode: string,
  teamName: string,
  season?: string | null,
  genderCategory?: string,
): Promise<TeamJourneyResponse> {
  const params = new URLSearchParams({
    competition_code: competitionCode,
    team_name: teamName,
  });
  if (season) params.set('season', season);
  if (genderCategory) params.set('gender_category', genderCategory);
  return request<TeamJourneyResponse>(
    `/analytics/tournament-intelligence/team-journey?${params.toString()}`,
  );
}

/**
 * GET /analytics/tournament-intelligence/podcast-rundown
 * Phase 10S.2: Returns a deterministic tournament podcast rundown for one group.
 */
export async function getTournamentPodcastRundown(
  competitionCode: string,
  season?: string | null,
  genderCategory?: string,
): Promise<TournamentPodcastRundown> {
  const params = new URLSearchParams({ competition_code: competitionCode });
  if (season) params.set('season', season);
  if (genderCategory) params.set('gender_category', genderCategory);
  return request<TournamentPodcastRundown>(
    `/analytics/tournament-intelligence/podcast-rundown?${params.toString()}`,
  );
}

export interface AnalystExportFilters {
  dateFrom?: string;
  dateTo?: string;
  player?: string;
  dismissalType?: string;
  phase?: string;
}

export interface AnalystExportDataResponse {
  rows: Record<string, unknown>[];
  meta: Record<string, unknown>;
}

export async function getAnalystExportData(
  filters: AnalystExportFilters = {},
  matchId?: string | null,
): Promise<AnalystExportDataResponse> {
  const params = new URLSearchParams();
  if (matchId) params.set('match_id', matchId);
  if (filters.dateFrom) params.set('date_from', filters.dateFrom);
  if (filters.dateTo) params.set('date_to', filters.dateTo);
  if (filters.player) params.set('player', filters.player);
  if (filters.dismissalType) params.set('dismissal_type', filters.dismissalType);
  if (filters.phase) params.set('phase', filters.phase);
  const query = params.toString();
  return request<AnalystExportDataResponse>(`/api/analyst/export-data${query ? `?${query}` : ''}`);
}

/* ------------------- Historical Stats (Phase 5N / CPL Dashboard) ------------------- */

/**
 * Aggregate stats for a single innings within a historical match.
 * Mirrors backend InningsAggregate schema.
 */
export interface InningsAggregate {
  inning_no: number;
  team: string | null;
  runs: number;
  wickets: number;
  overs: number;
  extras: number;
}

/**
 * Deterministic aggregate for a single historical match.
 * Mirrors backend MatchAggregate schema.
 */
export interface HistoricalMatchAggregate {
  match_id: string;
  teams: string;
  team_a: string | null;
  team_b: string | null;
  import_batch_id: string | null;
  source_filename: string | null;
  source_format: string | null;
  competition: string | null;
  season: string | null;
  season_raw?: string | null;
  season_source?: 'metadata' | 'match_date' | 'missing';
  venue: string | null;
  venue_raw?: string | null;
  venue_canonical?: string | null;
  venue_continuity_group?: string | null;
  match_date: string | null;
  match_type: string | null;
  innings_count: number;
  total_runs: number;
  total_wickets: number;
  innings_totals: InningsAggregate[];
  winner_team?: string | null;
  winner_team_canonical?: string | null;
  winner_source?: string | null;
  winner_confidence?: 'high' | 'medium' | 'low' | 'none';
  wicket_derivation_source?: 'deliveries' | 'innings_summary' | 'scorecard' | 'missing';
  phase_breakdown?: Record<string, { runs: number; wickets: number; legal_balls: number; overs: number; deliveries: number }>;
  over_progression?: Array<{
    inning_no: number;
    over: number;
    runs: number;
    cumulative_runs: number;
    wickets: number;
  }>;
  team_a_canonical?: string | null;
  team_b_canonical?: string | null;
  has_delivery_data: boolean;
}

/** Player batting + bowling aggregate across historical matches. */
export interface HistoricalPlayerAggregate {
  player_name: string;
  matches_contributed: number;
  runs_scored: number;
  balls_faced: number;
  strike_rate: number;
  fours: number;
  sixes: number;
  dismissals: number;
  overs_bowled: number;
  runs_conceded: number;
  wickets: number;
  economy_rate: number;
  maidens: number;
}

/** Team aggregate across historical matches. */
export interface HistoricalTeamAggregate {
  team_name: string;
  canonical_team_name?: string | null;
  continuity_group?: string | null;
  matches_played: number;
  innings_batted: number;
  avg_score: number;
  avg_wickets: number;
  total_runs: number;
  total_wickets: number;
}

/** Venue aggregate across historical matches. */
export interface HistoricalVenueAggregate {
  venue: string;
  canonical_venue?: string | null;
  continuity_group?: string | null;
  raw_venues?: string[];
  match_count: number;
  avg_first_innings_score: number;
  avg_second_innings_score: number | null;
  avg_total_runs: number;
  avg_wickets: number;
}

/** Competition aggregate across historical matches. */
export interface HistoricalCompetitionAggregate {
  competition: string;
  match_count: number;
  avg_total_runs: number;
  avg_wickets: number;
}

/** Season aggregate across historical matches. */
export interface HistoricalSeasonAggregate {
  season: string;
  match_count: number;
  avg_total_runs: number;
  avg_wickets: number;
}

export interface HistoricalSeasonOutcomeStageMatch {
  match_id: string;
  match_title: string;
  match_date: string | null;
  stage_label: string;
  result: string | null;
  winner_team_raw: string | null;
  winner_team_canonical: string | null;
  winner_confidence: 'high' | 'medium' | 'low' | 'none';
}

export interface HistoricalSeasonOutcomeAggregate {
  competition_code: string;
  competition_name: string;
  season: string | null;
  season_year: number | null;
  gender_category: string;
  champion_team_raw: string | null;
  champion_team_canonical: string | null;
  runner_up_team_raw: string | null;
  runner_up_team_canonical: string | null;
  final_match_id: string | null;
  final_match_title: string | null;
  final_match_date: string | null;
  final_result: string | null;
  league_table_leader_raw: string | null;
  league_table_leader_canonical: string | null;
  playoff_stage_matches_detected: HistoricalSeasonOutcomeStageMatch[];
  total_matches_in_season: number;
  outcome_source: string;
  confidence: 'high' | 'medium' | 'low' | 'unknown';
  unresolved_reason: string | null;
}

export interface HistoricalTrophySummaryAggregate {
  canonical_team: string;
  raw_team_names_seen: string[];
  trophies_detected: number;
  finals_appearances_detected: number;
  runner_up_finishes_detected: number;
  seasons_won: string[];
  competitions: string[];
  competition_codes: string[];
  gender_categories: string[];
  confidence_notes: string[];
}

/**
 * Full deterministic historical stats summary.
 * Mirrors backend HistoricalStatsSummaryResponse schema.
 * Phase 5N — read-only, no fake data.
 */
export interface HistoricalStatsSummaryResponse {
  total_eligible_matches: number;
  excluded_metadata_only_count: number;
  excluded_invalid_count: number;
  matches: HistoricalMatchAggregate[];
  players: HistoricalPlayerAggregate[];
  teams: HistoricalTeamAggregate[];
  venues: HistoricalVenueAggregate[];
  competitions: HistoricalCompetitionAggregate[];
  seasons: HistoricalSeasonAggregate[];
  diagnostics?: Record<string, number>;
  top_team_by_wins?: {
    team_name: string;
    wins: number;
    source?: string;
    confidence?: string;
  } | null;
  case_studies?: Array<{
    id: string;
    title: string;
    insight: string;
    source: string;
    context: string;
  }>;
  season_outcomes?: HistoricalSeasonOutcomeAggregate[];
  trophy_summary?: HistoricalTrophySummaryAggregate[];
  deterministic_outcome_insights?: string[];
  generated_at: string;
  note: string;
}

/**
 * GET /analytics/historical-stats/summary
 * Returns deterministic aggregate stats from all eligible historical matches.
 * Phase 5N — read-only. Requires analyst_pro or org_pro role.
 */
export async function getHistoricalStatsSummary(): Promise<HistoricalStatsSummaryResponse> {
  return request<HistoricalStatsSummaryResponse>('/analytics/historical-stats/summary');
}

/* ----------------------------- AI Commentary ----------------------------- */

/* Match AI Commentary (GET /matches/{match_id}/ai-commentary) */

export interface MatchCommentaryItem {
  over: number | null;
  ball_index: number | null;
  event_tags: string[];
  text: string;
  tone: 'neutral' | 'hype' | 'critical';
  created_at: string;
}

export interface MatchAiCommentaryResponse {
  match_id: string;
  commentary: MatchCommentaryItem[];
}

export async function fetchMatchAiCommentary(
  matchId: string
): Promise<MatchAiCommentaryResponse> {
  return request<MatchAiCommentaryResponse>(
    `/matches/${encodeURIComponent(matchId)}/ai-commentary`
  );
}

/* Single Delivery AI Commentary (POST /ai/commentary) */

export interface AICommentaryRequest {
  match_id: string;
  over: number;
  ball: number;
  runs: number;
  wicket: boolean;
  batter: string;
  bowler: string;
  context?: Record<string, unknown>;
}

export interface AICommentaryResponse {
  commentary: string;
}

export async function generateAICommentary(
  payload: AICommentaryRequest
): Promise<AICommentaryResponse> {
  return request<AICommentaryResponse>('/ai/commentary', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/* ----------------------------- AI Player Insights ----------------------------- */

export interface PlayerAIRecentForm {
  label: string;
  trend: number[];
}

export interface PlayerAIInsights {
  player_id: string;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  recent_form: PlayerAIRecentForm;
  role_tags: string[];
  recommendations: string[];
  ai_metadata?: AiOutputMetadata;
}

export async function getPlayerAIInsights(
  playerId: string
): Promise<PlayerAIInsights> {
  return request<PlayerAIInsights>(
    `/api/players/${encodeURIComponent(playerId)}/ai-insights`
  );
}

/* ----------------------------- Fan Mode types ----------------------------- */

export interface FanMatchCreate {
  home_team_name: string
  away_team_name: string
  match_type?: string
  overs_limit?: number | null
}

export interface FanMatchRead {
  id: string
  home_team_name: string
  away_team_name: string
  match_type: string
  overs_limit: number | null
  is_fan_match: boolean
}

export type FanFavoriteType = 'player' | 'team'

export interface FanFavoriteCreate {
  favorite_type: FanFavoriteType
  player_profile_id?: string | null
  team_id?: string | null
}

export interface FanFavoriteRead {
  id: string
  favorite_type: FanFavoriteType
  player_profile_id: string | null
  team_id: string | null
  created_at: string
  player_name?: string | null
  team_name?: string | null
}

/* ----------------------------- API surface ------------------------------- */

export const apiService = {
  /* Games */
  createGame: (body: CreateGameRequest) =>
    request<GameMinimal>('/games', { method: 'POST', body: JSON.stringify(body) }),

  getGame: (gameId: string) => request<GameMinimal>(`/games/${encodeURIComponent(gameId)}`),

  getSnapshot: (gameId: string) =>
    request<Snapshot>(`/games/${encodeURIComponent(gameId)}/snapshot`),

  // ?? ADDED: fetch persisted result for a completed game; returns null on 404
  async getResults(gameId: string): Promise<MatchResult | null> {
    try {
      return await request<MatchResult>(`/games/${encodeURIComponent(gameId)}/results`)
    } catch (e: any) {
      if (e?.status === 404) return null
      return null
    }
  },

  searchGames: (team_a?: string, team_b?: string) => {
    const qp = new URLSearchParams()
    if (team_a) qp.set('team_a', team_a)
    if (team_b) qp.set('team_b', team_b)
    const qs = qp.toString()
    return request<Array<{ id: string; team_a_name: string; team_b_name: string; status?: string }>>(
      `/games/search${qs ? `?${qs}` : ''}`
    )
  },

  /* Fan Mode */
  createFanMatch: (body: FanMatchCreate) =>
    request<FanMatchRead>('/api/fan/matches', { method: 'POST', body: JSON.stringify(body) }),

  listFanMatches: (limit = 20, offset = 0) =>
    request<FanMatchRead[]>(`/api/fan/matches?limit=${limit}&offset=${offset}`),

  getFanMatch: (matchId: string) =>
    request<FanMatchRead>(`/api/fan/matches/${encodeURIComponent(matchId)}`),

  /* Fan Favorites */
  getFanFavorites: () =>
    request<FanFavoriteRead[]>('/api/fan/favorites'),

  createFanFavorite: (payload: FanFavoriteCreate) =>
    request<FanFavoriteRead>('/api/fan/favorites', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  deleteFanFavorite: (favoriteId: string) =>
    request<void>(`/api/fan/favorites/${encodeURIComponent(favoriteId)}`, {
      method: 'DELETE',
    }),

  /* Scoring */
  scoreDelivery: (gameId: string, body: ScoreDeliveryRequest) =>
    request<Snapshot>(`/games/${encodeURIComponent(gameId)}/deliveries`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  correctDelivery: (gameId: string, deliveryId: number, body: DeliveryCorrectionRequest) =>
    request<Snapshot>(`/games/${encodeURIComponent(gameId)}/deliveries/${deliveryId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  undoLast: (gameId: string) =>
    request<Snapshot>(`/games/${encodeURIComponent(gameId)}/undo-last`, {
      method: 'POST',
    }),

  /* Match limits / rain */
  setOversLimit: (gameId: string, body: OversLimitBody | number) => {
  const payload = typeof body === 'number' ? { overs_limit: body } : body
  return request<{ id: string; overs_limit: number }>(
    `/games/${encodeURIComponent(gameId)}/overs-limit`,
    { method: 'POST', body: JSON.stringify(payload) },
  )
},

// 2) Add these two methods to the apiService object (near the other DLS/overs methods)
dlsRevisedTarget: (gameId: string, body: DlsRevisedTargetIn) =>
  request<DlsRevisedTargetOut>(
    `/games/${encodeURIComponent(gameId)}/dls/revised-target`,
    { method: 'POST', body: JSON.stringify(body) }
  ),

dlsParNow: (gameId: string, body: DlsParNowIn) =>
  request<DlsParNowOut>(
    `/games/${encodeURIComponent(gameId)}/dls/par`,
    { method: 'POST', body: JSON.stringify(body) }
  ),

  /* Team roles */
  setTeamRoles: (gameId: string, body: TeamRoleUpdate) =>
    request<{ ok: true; team_roles: any }>(
      `/games/${encodeURIComponent(gameId)}/team-roles`,
      { method: 'POST', body: JSON.stringify(body) },
    ),

  /* ?? Over gates */
  // Start a new over (select bowler)  matches POST /games/{id}/overs/start
  startOver: (gameId: string, bowler_id: string) =>
    request<{ ok: true; current_bowler_id: string }>(
      `/games/${encodeURIComponent(gameId)}/overs/start`,
      { method: 'POST', body: JSON.stringify({ bowler_id } as StartOverBody) },
    ),

  // Mid-over change (injury/other)  matches POST /games/{id}/overs/change_bowler
  changeBowlerMidOver: (gameId: string, new_bowler_id: string, reason: 'injury' | 'other' = 'injury') =>
    request<Snapshot>(`/games/${encodeURIComponent(gameId)}/overs/change_bowler`, {
      method: 'POST',
      body: JSON.stringify({ new_bowler_id, reason } as MidOverChangeBody),
    }),

  /* ?? Batter gates */
  // Replace the out batter before next ball  POST /games/{id}/batters/replace
  replaceBatter: (gameId: string, new_batter_id: string) =>
    request<Snapshot>(`/games/${encodeURIComponent(gameId)}/batters/replace`, {
      method: 'POST',
      body: JSON.stringify({ new_batter_id } as ReplaceBatterBody),
    }),

  // Explicitly set next batter (optional QoL)  POST /games/{id}/next-batter
  setNextBatter: (gameId: string, batter_id: string) =>
    request<{ ok: true; current_striker_id: string }>(
      `/games/${encodeURIComponent(gameId)}/next-batter`,
      { method: 'POST', body: JSON.stringify({ batter_id } as NextBatterBody) },
    ),

  deliveries: (
    gameId: string,
    params?: { innings?: number; limit?: number; order?: 'asc' | 'desc' }
  ) => {
    const qp = new URLSearchParams()
    if (params?.innings != null) qp.set('innings', String(params.innings))
    if (params?.limit != null)   qp.set('limit',   String(params.limit))
    if (params?.order)           qp.set('order',   params.order) // allow asc/desc order selection
    const qs = qp.toString()
    const path = `/games/${encodeURIComponent(gameId)}/deliveries${qs ? `?${qs}` : ''}`
    return request<{ game_id: string; count: number; deliveries: any[] }>(path)
  },

  recentDeliveries: (gameId: string, limit = 10) =>
    request<{ game_id: string; count: number; deliveries: any[] }>(
      `/games/${encodeURIComponent(gameId)}/recent_deliveries?limit=${encodeURIComponent(String(limit))}`
    ),


  // Set openers (optional QoL)  POST /games/{id}/openers
  setOpeners: (gameId: string, body: OpenersBody) =>
    request<Snapshot>(`/games/${encodeURIComponent(gameId)}/openers`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getInterruptions,
  openInterruption,
  stopInterruption,
  /* Contributors */
  addContributor: (gameId: string, body: ContributorIn) =>
    request<Contributor>(`/games/${encodeURIComponent(gameId)}/contributors`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  listContributors: (gameId: string) =>
    request<Contributor[]>(`/games/${encodeURIComponent(gameId)}/contributors`),

  removeContributor: (gameId: string, contribId: number) =>
    request<{ ok: true }>(`/games/${encodeURIComponent(gameId)}/contributors/${contribId}`, {
      method: 'DELETE',
    }),

  /* Sponsors */
  uploadSponsor: (body: SponsorCreateBody) => {
    const form = new FormData();
    form.append('name', body.name);
    form.append('logo', body.logo);
    if (body.click_url != null) form.append('click_url', body.click_url);
    if (body.weight != null) form.append('weight', String(body.weight));
    if (body.surfaces) form.append('surfaces', JSON.stringify(body.surfaces));
    if (body.start_at) form.append('start_at', body.start_at);
    if (body.end_at) form.append('end_at', body.end_at);
    return request<any>('/sponsors', { method: 'POST', body: form });
  },

  /** List all sponsors (active + inactive) */
  getSponsors: () =>
    request<SponsorRow[]>('/sponsors'),

  /** Get a single sponsor by ID */
  getSponsor: (sponsorId: string) =>
    request<SponsorRow>(`/sponsors/${encodeURIComponent(sponsorId)}`),

  /** Update an existing sponsor (partial update) */
  updateSponsor: (sponsorId: string, body: {
    name?: string;
    logo_url?: string;
    click_url?: string | null;
    weight?: number;
    is_active?: boolean;
    start_at?: string | null;
    end_at?: string | null;
  }) =>
    request<SponsorRow>(`/sponsors/${encodeURIComponent(sponsorId)}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  /** Delete a sponsor */
  deleteSponsor: (sponsorId: string) =>
    request<{ status: string }>(`/sponsors/${encodeURIComponent(sponsorId)}`, {
      method: 'DELETE',
    }),

  getGameSponsors: (gameId: string) =>
    request<SponsorRow[]>(`/games/${encodeURIComponent(gameId)}/sponsors`),

  logSponsorImpressions: (payload: SponsorImpressionIn | SponsorImpressionIn[]) =>
    request<SponsorImpressionsOut>('/sponsor_impressions', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  /* Health */
  healthz: () => request<{ status: 'ok' }>('/healthz'),

  /* Admin - Beta User Management */
  createBetaUser: (payload: {
    email: string;
    role: string;
    plan: string;
    org_id?: string | null;
    beta_tag?: string | null;
    password?: string | null;
  }) =>
    request<{
      id: string;
      email: string;
      role: string;
      plan: string;
      org_id: string | null;
      beta_tag: string | null;
      temp_password: string;
    }>('/api/admin/users', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listBetaUsers: () =>
    request<Array<{
      id: string;
      email: string;
      role: string;
      is_active: boolean;
      created_at: string | null;
      beta_tag: string | null;
      org_id: string | null;
    }>>('/api/admin/users'),

  resetUserPassword: (userId: string, password?: string | null) =>
    request<{
      id: string;
      email: string;
      temp_password: string;
    }>(`/api/admin/users/${encodeURIComponent(userId)}/reset-password`, {
      method: 'POST',
      body: JSON.stringify(password ? { password } : {}),
    }),

  deactivateUser: (userId: string) =>
    request<{
      id: string;
      email: string;
      is_active: boolean;
    }>(`/api/admin/users/${encodeURIComponent(userId)}/deactivate`, {
      method: 'POST',
    }),

  reactivateUser: (userId: string) =>
    request<{
      id: string;
      email: string;
      is_active: boolean;
    }>(`/api/admin/users/${encodeURIComponent(userId)}/reactivate`, {
      method: 'POST',
    }),

  /* Optional placeholder (backend route not present yet) */
  // This will 404 until you add a backend route; the store calls it only if you wire a UI button.
  startNextInnings: (gameId: string, body: StartNextInningsBody) =>
  request<Snapshot>(`/games/${encodeURIComponent(gameId)}/innings/start`, {
    method: 'POST',
    body: JSON.stringify(body),
  }),

  /* Tournament Management */
  // Tournaments
  createTournament: (body: {
    name: string;
    description?: string | null;
    tournament_type?: string;
    start_date?: string | null;
    end_date?: string | null;
  }) =>
    request<any>('/tournaments/', { method: 'POST', body: JSON.stringify(body) }),

  getTournaments: (skip = 0, limit = 100) =>
    request<any[]>(`/tournaments/?skip=${skip}&limit=${limit}`),

  getTournament: (tournamentId: string) =>
    request<any>(`/tournaments/${encodeURIComponent(tournamentId)}`),

  updateTournament: (tournamentId: string, body: {
    name?: string;
    description?: string | null;
    tournament_type?: string;
    start_date?: string | null;
    end_date?: string | null;
    status?: string;
  }) =>
    request<any>(`/tournaments/${encodeURIComponent(tournamentId)}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  deleteTournament: (tournamentId: string) =>
    request<{ status: string }>(`/tournaments/${encodeURIComponent(tournamentId)}`, {
      method: 'DELETE',
    }),

  // Teams
  addTeamToTournament: (tournamentId: string, body: {
    team_name: string;
    team_data?: any;
  }) =>
    request<any>(`/tournaments/${encodeURIComponent(tournamentId)}/teams`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getTournamentTeams: (tournamentId: string) =>
    request<any[]>(`/tournaments/${encodeURIComponent(tournamentId)}/teams`),

  getPointsTable: (tournamentId: string) =>
    request<any[]>(`/tournaments/${encodeURIComponent(tournamentId)}/points-table`),

  // Fixtures
  createFixture: (body: {
    tournament_id: string;
    match_number?: number | null;
    team_a_name: string;
    team_b_name: string;
    venue?: string | null;
    scheduled_date?: string | null;
  }) =>
    request<any>('/tournaments/fixtures', { method: 'POST', body: JSON.stringify(body) }),

  getFixture: (fixtureId: string) =>
    request<any>(`/tournaments/fixtures/${encodeURIComponent(fixtureId)}`),

  getTournamentFixtures: (tournamentId: string) =>
    request<any[]>(`/tournaments/${encodeURIComponent(tournamentId)}/fixtures`),

  updateFixture: (fixtureId: string, body: {
    match_number?: number | null;
    team_a_name?: string;
    team_b_name?: string;
    venue?: string | null;
    scheduled_date?: string | null;
    status?: string;
    result?: string | null;
    game_id?: string | null;
  }) =>
    request<any>(`/tournaments/fixtures/${encodeURIComponent(fixtureId)}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  deleteFixture: (fixtureId: string) =>
    request<{ status: string }>(`/tournaments/fixtures/${encodeURIComponent(fixtureId)}`, {
      method: 'DELETE',
    }),
};

export default apiService;

/* ----------------------------- Phase 5I: Historical Import ----------------------------- */

export interface HistoricalImportIssue {
  code: string;
  message: string;
  severity: 'error' | 'warning';
  path?: string | null;
}

export interface HistoricalImportDetectedSections {
  teams: boolean;
  players: boolean;
  innings: boolean;
  deliveries: boolean;
  metadata: boolean;
}

export interface HistoricalImportMetadataPreview {
  match_type?: string | null;
  venue?: string | null;
  date?: string | null;
  result?: string | null;
}

export interface HistoricalImportInningsPreview {
  inning_no: number;
  team?: string | null;
  deliveries: number;
  runs?: number | null;
  wickets?: number | null;
  overs?: number | null;
}

export interface HistoricalImportDuplicatePreview {
  source_hash_sha256: string;
  probable_duplicate: 'unknown' | 'likely_duplicate' | 'not_duplicate';
  tracking_available: boolean;
  duplicate_batch_id?: string | null;
  semantic_key?: string | null;
  semantic_duplicate: boolean;
  message: string;
}

export interface HistoricalImportDryRunResponse {
  status: 'valid' | 'invalid' | 'unsupported';
  detected_format: string;
  top_level_keys: string[];
  detected_sections: HistoricalImportDetectedSections;
  metadata_preview: HistoricalImportMetadataPreview;
  teams_preview: string[];
  innings_count: number;
  delivery_count: number;
  player_names_found: string[];
  innings_preview: HistoricalImportInningsPreview[];
  warnings: HistoricalImportIssue[];
  errors: HistoricalImportIssue[];
  duplicate_detection: HistoricalImportDuplicatePreview;
  no_persistence: boolean;
  record_id?: string | null;
}

export interface HistoricalImportBatchRecord {
  id: string;
  owner_user_id?: string | null;
  owner_org_id?: string | null;
  source_filename?: string | null;
  source_format: string;
  source_hash_sha256: string;
  semantic_key?: string | null;
  status: string;
  error_count: number;
  warning_count: number;
  innings_count: number;
  delivery_count: number;
  is_finalized: boolean;
  applied_game_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface HistoricalMetadataOnlyMatchItem {
  match_id: string;
  batch_id: string;
  source_filename?: string | null;
  team_a?: string | null;
  team_b?: string | null;
  match_date?: string | null;
  venue?: string | null;
  competition?: string | null;
  season?: string | null;
  completeness_status: string;
  expected_deliveries?: number | null;
  actual_deliveries: number;
  expected_wickets?: number | null;
  actual_wickets: number;
  source_payload_available: boolean;
  recommended_action: string;
}

export interface HistoricalMetadataOnlyMatchesResponse {
  status: 'ok';
  total: number;
  items: HistoricalMetadataOnlyMatchItem[];
}

export interface HistoricalImportApplyResponse {
  batch_id: string;
  applied_game_id?: string | null;
  records_created: number;
  status: 'applied' | 'skipped' | 'failed';
  warnings: string[];
  rollback_info: string;
}

export interface HistoricalImportTotalsValidation {
  inning_no: number;
  team?: string | null;
  derived_runs: number;
  expected_runs?: number | null;
  derived_wickets: number;
  expected_wickets?: number | null;
  legal_balls: number;
  status: 'ok' | 'warning' | 'blocked';
  notes: string;
}

export interface HistoricalImportApplyDeliveriesResponse {
  batch_id: string;
  applied_game_id: string;
  deliveries_imported: number;
  innings_processed: number;
  status: 'deliveries_applied' | 'already_applied' | 'failed';
  totals_validation: HistoricalImportTotalsValidation[];
  warnings: string[];
  rollback_info: string;
}

export interface HistoricalImportRollbackResponse {
  batch_id: string;
  rolled_back_game_id?: string | null;
  records_deleted: number;
  status: 'rolled_back';
  warnings: string[];
}

export interface HistoricalImportTrainingStatus {
  batch_id: string;
  source_format: string;
  source_hash_sha256: string;
  source_filename?: string | null;
  semantic_key?: string | null;
  applied_game_id?: string | null;
  imported_at: string;
  innings_count: number;
  delivery_count: number;
  training_eligible: boolean;
  exclusion_reason?: string | null;
  raw_json_retained: boolean;
  training_registry_phase: string;
}

export interface HistoricalImportBulkZipFilePreview {
  file_name: string;
  status: 'valid' | 'invalid' | 'duplicate' | 'unsupported' | 'error';
  message: string;
  duplicate_within_zip: boolean;
  duplicate_batch_id?: string | null;
  semantic_duplicate: boolean;
  detected_format?: string | null;
  warnings: HistoricalImportIssue[];
  errors: HistoricalImportIssue[];
  dry_run_preview?: HistoricalImportDryRunResponse | null;
}

export interface HistoricalImportBulkZipDryRunResponse {
  status: 'preview_ready' | 'invalid_zip';
  source_filename?: string | null;
  total_entries: number;
  files_scanned: number;
  json_entries: number;
  non_json_entries: number;
  metadata_only_intake_required: boolean;
  metadata_only_pending_count: number;
  intake_status: string;
  cost_control_message?: string | null;
  full_import_deferred: boolean;
  selected_apply_requires_confirm: boolean;
  max_files: number;
  max_file_size_bytes: number;
  max_total_uncompressed_bytes: number;
  max_total_compressed_bytes: number;
  summary: Record<string, number>;
  files: HistoricalImportBulkZipFilePreview[];
}

export interface HistoricalImportBulkZipApplyFileResult {
  file_name: string;
  status: 'applied' | 'metadata_extracted' | 'skipped' | 'error';
  message: string;
  batch_id?: string | null;
  applied_game_id?: string | null;
}

export interface HistoricalImportBulkZipApplyResponse {
  status: 'applied' | 'metadata_recorded' | 'partial' | 'failed';
  source_filename?: string | null;
  selected_count: number;
  applied_count: number;
  skipped_count: number;
  error_count: number;
  metadata_only_count: number;
  full_import_deferred: boolean;
  selected_apply_requires_confirm: boolean;
  results: HistoricalImportBulkZipApplyFileResult[];
}

export interface HistoricalBackfillAuditRequest {
  match_ids?: string[];
  batch_ids?: string[];
  max_batch_size?: number;
  source_payloads_by_batch?: Record<string, Record<string, unknown>>;
}

export interface HistoricalBackfillAuditMatchRecord {
  match_id: string;
  batch_id: string;
  import_source: 'single_json_apply' | 'bulk_zip_apply' | 'unknown';
  completeness: string;
  eligible: boolean;
  blocked_reason?: string | null;
  missing_source_json: boolean;
  duplicate_delivery_risk: boolean;
  apply_deliveries_previously_run: boolean;
  source_json_retained: boolean;
  registry_people_available: boolean;
  registry_people_count: number;
  players_without_source_ids: number;
  expected_deliveries: number;
  expected_wickets: number;
  expected_players: number;
  match_date?: string | null;
  competition?: string | null;
  season?: string | null;
  team_1?: string | null;
  team_2?: string | null;
  venue?: string | null;
  result?: string | null;
  status?: string | null;
  innings_1_summary?: string | null;
  innings_2_summary?: string | null;
  known_score_summary?: string | null;
  original_filename?: string | null;
  upload_filename?: string | null;
  source_file_hint?: string | null;
  match_identity_label?: string | null;
}

export interface HistoricalBackfillAuditResponse {
  total_imported_cpl_matches: number;
  completeness_counts: Record<string, number>;
  import_origin_counts: Record<string, number>;
  player_aggregate_scope: string;
  rollback_feasibility: string;
  eligible_matches: number;
  blocked_matches: number;
  selected_matches: number;
  records: HistoricalBackfillAuditMatchRecord[];
}

export interface HistoricalBackfillDiagnosisMatchRecord {
  match_id: string;
  batch_id: string;
  import_source: 'single_json_apply' | 'bulk_zip_apply' | 'unknown';
  completeness: string;
  source_json_retained: boolean;
  source_json_required: boolean;
  schema_detected: string;
  innings_path_detected: boolean;
  delivery_path_detected: boolean;
  detected_delivery_path?: string | null;
  delivery_path_candidates: string[];
  expected_deliveries: number;
  expected_wickets: number;
  registry_people_available: boolean;
  batter_field_detected: boolean;
  bowler_field_detected: boolean;
  non_striker_field_detected: boolean;
  runs_field_detected: boolean;
  extras_field_detected: boolean;
  wicket_field_detected: boolean;
  skip_or_failure_reason?: string | null;
  safely_reprocessable: boolean;
  recommended_next_action: string;
}

export interface HistoricalBackfillDiagnosisResponse {
  total_imported_cpl_matches: number;
  selected_matches: number;
  blocked_matches: number;
  records: HistoricalBackfillDiagnosisMatchRecord[];
}

export interface HistoricalBackfillApplyRequest extends HistoricalBackfillAuditRequest {
  confirm: boolean;
}

export interface HistoricalBackfillMappingReason {
  source_player_name?: string;
  source_player_id?: string;
  source_team?: string;
  source_venue_name?: string;
  reason?: string;
  candidate_count?: number;
  [key: string]: unknown;
}

export interface HistoricalBackfillApplyMatchResult {
  match_id: string;
  batch_id: string;
  status: 'processed' | 'skipped' | 'failed';
  reason?: string | null;
  completeness_before: string;
  completeness_after: string;
  deliveries_before: number;
  deliveries_after: number;
  wickets_before: number;
  wickets_after: number;
  player_mappings_updated: number;
  mappings_updated?: number;
  mappings_created?: number;
  resolved_players?: number;
  unresolved_players: number;
  ambiguous_players?: number;
  resolved_venues?: number;
  unresolved_venues: number;
  unresolved_player_reasons?: HistoricalBackfillMappingReason[];
  ambiguous_player_reasons?: HistoricalBackfillMappingReason[];
  unresolved_venue_reasons?: HistoricalBackfillMappingReason[];
}

export interface HistoricalBackfillApplyResponse {
  status: 'applied' | 'partial' | 'failed';
  processed_matches: number;
  skipped_matches: number;
  failed_matches: number;
  deliveries_rebuilt: number;
  wickets_rebuilt: number;
  player_mappings_updated: number;
  mappings_updated?: number;
  mappings_created?: number;
  resolved_players?: number;
  unresolved_players: number;
  ambiguous_players?: number;
  resolved_venues?: number;
  unresolved_venues: number;
  changed_match_ids: string[];
  blocked_records: Array<{ match_id: string; batch_id: string; reason: string }>;
  results: HistoricalBackfillApplyMatchResult[];
  rollback_info: string;
}

export interface HistoricalCplResetReimportDryRunRequest {
  file: File;
  max_batch_size?: number;
  match_ids?: string[];
  batch_ids?: string[];
  season?: string;
}

export interface HistoricalCplResetReimportSourceFileMapping {
  file_name: string;
  status: string;
  match_confidence: 'exact_match' | 'likely_match' | 'ambiguous' | 'no_match';
  blocked_from_apply: boolean;
  batch_id?: string | null;
  match_id?: string | null;
}

export interface HistoricalCplResetReimportDryRunResponse {
  status: 'preview_ready';
  operation: 'cpl_reset_reimport_dry_run';
  scope: {
    match_ids: string[];
    batch_ids: string[];
    max_batch_size: number;
  };
  total_candidate_existing_historical_records: number;
  records_safe_to_reset: number;
  records_blocked_from_reset: number;
  expected_matches_to_import: number;
  expected_deliveries: number;
  expected_wickets: number;
  expected_players: number;
  duplicate_risks: number;
  destructive_action_summary: {
    matches_to_reset: number;
    historical_batches_in_scope: number;
    delivery_rows_to_rebuild: number;
    blocked_records: number;
  };
  blocked_records: Array<{ match_id: string; batch_id: string; reason: string }>;
  source_bundle_preview?: HistoricalBulkZipSourcePayloadDryRunResponse | HistoricalSourcePayloadReattachDryRunResponse | null;
  source_file_mapping: HistoricalCplResetReimportSourceFileMapping[];
  audit?: HistoricalBackfillAuditResponse;
}

export interface HistoricalCplResetReimportApplyRequest
  extends HistoricalCplResetReimportDryRunRequest {
  confirm: true;
}

export interface HistoricalCplResetReimportApplyResponse {
  status: 'applied' | 'partial' | 'failed';
  operation: 'cpl_reset_reimport_apply';
  operation_id: string;
  scope: {
    match_ids: string[];
    batch_ids: string[];
    max_batch_size: number;
  };
  source_payload_retention: {
    attempted: boolean;
    report?: {
      status?: string;
      reattached_count?: number;
      skipped_count?: number;
      error_count?: number;
    } | null;
  };
  reimport_report: {
    status: string;
    selected_batches: number;
    selected_matches: number;
  };
}

export interface HistoricalSourcePayloadReattachMetadata {
  competition_name?: string | null;
  season?: string | null;
  match_number?: number | null;
  date?: string | null;
  teams: string[];
  venue?: string | null;
  city?: string | null;
  source_filename?: string | null;
  registry_people_available: boolean;
  expected_deliveries: number;
  expected_wickets: number;
}

export interface HistoricalSourcePayloadReattachMatchCandidate {
  match_id: string;
  batch_id: string;
  confidence: 'exact_match' | 'likely_match';
  matched_on: string[];
  source_json_retained: boolean;
  metadata: HistoricalSourcePayloadReattachMetadata;
}

export interface HistoricalSourcePayloadReattachDryRunFileResult {
  file_name: string;
  status: 'ready' | 'invalid' | 'unsupported' | 'error';
  match_confidence: 'exact_match' | 'likely_match' | 'ambiguous' | 'no_match';
  blocked_from_apply: boolean;
  message: string;
  metadata: HistoricalSourcePayloadReattachMetadata;
  matched_target?: HistoricalSourcePayloadReattachMatchCandidate | null;
  candidate_matches: HistoricalSourcePayloadReattachMatchCandidate[];
  warnings: string[];
}

export interface HistoricalSourcePayloadReattachDryRunResponse {
  status: 'preview_ready';
  source_filename?: string | null;
  total_candidates: number;
  ready_candidates: number;
  blocked_candidates: number;
  files: HistoricalSourcePayloadReattachDryRunFileResult[];
}

export interface HistoricalSourcePayloadReattachApplyFileResult {
  file_name: string;
  status: 'reattached' | 'skipped' | 'error';
  message: string;
  match_id?: string | null;
  batch_id?: string | null;
  match_confidence?: 'exact_match' | 'likely_match' | null;
}

export interface HistoricalSourcePayloadReattachApplyResponse {
  status: 'applied' | 'partial' | 'failed';
  source_filename?: string | null;
  selected_count: number;
  reattached_count: number;
  skipped_count: number;
  error_count: number;
  results: HistoricalSourcePayloadReattachApplyFileResult[];
  follow_up_message: string;
}

export interface HistoricalBackfillSourceReattachResponse {
  record_id: string;
  match_id: string;
  retained: boolean;
  status: 'reattached' | 'already_retained';
  validation_confidence: 'exact_match' | 'probable_match' | 'mismatch' | 'insufficient_identity';
  validation_reason: string;
  matched_identity_fields: string[];
  mismatch_warnings: string[];
  source_hash_sha256: string;
  uploaded_filename: string;
  recommended_next_action: string;
}

export interface HistoricalBulkZipSourcePayloadDryRunSummary {
  candidate_json_count: number;
  exact_match_count: number;
  likely_match_count: number;
  ambiguous_count: number;
  no_match_count: number;
  already_retained_count: number;
  malformed_count: number;
  unsafe_count: number;
}

export interface HistoricalBulkZipSourcePayloadDryRunResponse {
  status: 'preview_ready';
  source_filename?: string | null;
  summary: HistoricalBulkZipSourcePayloadDryRunSummary;
  files: HistoricalSourcePayloadReattachDryRunFileResult[];
}

export interface HistoricalBulkZipSourcePayloadApplyResponse {
  status: 'applied' | 'partial' | 'failed';
  source_filename?: string | null;
  selected_count: number;
  applied_count: number;
  skipped_count: number;
  ambiguous_count: number;
  no_match_count: number;
  malformed_count: number;
  error_count: number;
  results: HistoricalSourcePayloadReattachApplyFileResult[];
  follow_up_message: string;
}

export type HistoricalOcrReviewStatus =
  | 'uploaded'
  | 'extracted'
  | 'needs_review'
  | 'reviewed'
  | 'rejected'
  | 'ready_for_dry_run'
  | 'dry_run_failed'
  | 'dry_run_passed'
  | 'applied_via_structured_import_only';

export interface HistoricalOcrSourceDocument {
  filename: string;
  content_type: string;
  size_bytes: number;
  storage: Record<string, string>;
}

export interface HistoricalOcrExtractionMetadata {
  method: string;
  confidence?: number | null;
  uncertainty_flags: string[];
  ocr_text?: string | null;
  warnings?: string[];
  non_authoritative_notice: string;
}

export interface HistoricalOcrReviewCandidateResponse {
  candidate_id: string;
  batch_id: string;
  status: HistoricalOcrReviewStatus;
  status_history: HistoricalOcrReviewStatus[];
  source_document: HistoricalOcrSourceDocument;
  extraction: HistoricalOcrExtractionMetadata;
  candidate_json?: Record<string, unknown> | null;
  reviewed_json?: Record<string, unknown> | null;
  reviewer_notes?: string | null;
  rejection_reason?: string | null;
  validation_errors: HistoricalImportIssue[];
  dry_run_result?: HistoricalImportDryRunResponse | null;
  dry_run_batch_id?: string | null;
}

export interface HistoricalOcrReviewDryRunResponse {
  candidate_id: string;
  status: HistoricalOcrReviewStatus;
  dry_run_result: HistoricalImportDryRunResponse;
  dry_run_batch_id?: string | null;
  message: string;
}

/**
 * POST /api/historical-import/json/dry-run
 * Accepts a .json File; optionally persists batch metadata when recordPreview=true.
 * Returns a structured preview without creating any game/delivery rows.
 */
export async function historicalImportDryRun(
  file: File,
  recordPreview = false,
): Promise<HistoricalImportDryRunResponse> {
  const form = new FormData();
  form.append('file', file, file.name);
  const qs = recordPreview ? '?record_preview=true' : '';
  return request<HistoricalImportDryRunResponse>(
    `/api/historical-import/json/dry-run${qs}`,
    { method: 'POST', body: form },
  );
}

/**
 * GET /api/historical-import/json/batches
 * Returns import batch records scoped to the current user/org.
 */
export async function historicalImportListBatches(
  limit = 20,
): Promise<HistoricalImportBatchRecord[]> {
  return request<HistoricalImportBatchRecord[]>(
    `/api/historical-import/json/batches?limit=${limit}`,
  );
}

/**
 * GET /api/historical-import/json/metadata-only-matches
 * Returns historical matches with metadata but no delivery ledger rows.
 */
export async function historicalImportListMetadataOnlyMatches(params?: {
  competition?: string;
  season?: string;
  limit?: number;
  offset?: number;
}): Promise<HistoricalMetadataOnlyMatchesResponse> {
  const query = new URLSearchParams();
  if (params?.competition?.trim()) {
    query.set('competition', params.competition.trim());
  }
  if (params?.season?.trim()) {
    query.set('season', params.season.trim());
  }
  query.set('limit', String(params?.limit ?? 100));
  query.set('offset', String(params?.offset ?? 0));
  const qs = query.toString();
  return request<HistoricalMetadataOnlyMatchesResponse>(
    `/api/historical-import/json/metadata-only-matches${qs ? `?${qs}` : ''}`,
  );
}

/**
 * POST /api/historical-import/json/batches/{batchId}/apply
 * Creates a historical Game row from a validated import batch.
 * Requires explicit confirm=true.
 */
export async function historicalImportApply(
  batchId: string,
): Promise<HistoricalImportApplyResponse> {
  return request<HistoricalImportApplyResponse>(
    `/api/historical-import/json/batches/${encodeURIComponent(batchId)}/apply`,
    { method: 'POST', body: JSON.stringify({ confirm: true }) },
  );
}

/**
 * POST /api/historical-import/json/batches/{batchId}/apply-deliveries
 * Imports ball-by-ball delivery data into the historical game.
 * Requires the same JSON file and explicit confirm=true.
 */
export async function historicalImportApplyDeliveries(
  batchId: string,
  file: File,
): Promise<HistoricalImportApplyDeliveriesResponse> {
  const form = new FormData();
  form.append('file', file, file.name);
  return request<HistoricalImportApplyDeliveriesResponse>(
    `/api/historical-import/json/batches/${encodeURIComponent(batchId)}/apply-deliveries?confirm=true`,
    { method: 'POST', body: form },
  );
}

/**
 * POST /api/historical-import/json/batches/{batchId}/rollback
 * Removes the imported historical game for the batch.
 * Requires explicit confirm=true.
 */
export async function historicalImportRollback(
  batchId: string,
): Promise<HistoricalImportRollbackResponse> {
  return request<HistoricalImportRollbackResponse>(
    `/api/historical-import/json/batches/${encodeURIComponent(batchId)}/rollback`,
    { method: 'POST', body: JSON.stringify({ confirm: true }) },
  );
}

/**
 * GET /api/historical-import/json/batches/{batchId}/training-status
 * Returns training dataset readiness metadata for an import batch.
 */
export async function historicalImportGetTrainingStatus(
  batchId: string,
): Promise<HistoricalImportTrainingStatus> {
  return request<HistoricalImportTrainingStatus>(
    `/api/historical-import/json/batches/${encodeURIComponent(batchId)}/training-status`,
  );
}

/**
 * POST /api/historical-import/json/bulk-zip/dry-run
 * Runs dry-run validation for a ZIP containing multiple historical JSON files.
 */
export async function historicalImportBulkZipDryRun(
  file: File,
): Promise<HistoricalImportBulkZipDryRunResponse> {
  const form = new FormData();
  form.append('file', file, file.name);
  return request<HistoricalImportBulkZipDryRunResponse>(
    '/api/historical-import/json/bulk-zip/dry-run',
    { method: 'POST', body: form },
  );
}

/**
 * POST /api/historical-import/json/bulk-zip/apply
 * Applies selected valid entries from a ZIP import dry-run.
 */
export async function historicalImportBulkZipApply(
  file: File,
  selectedFiles: string[],
): Promise<HistoricalImportBulkZipApplyResponse> {
  const form = new FormData();
  form.append('file', file, file.name);
  form.append('confirm', 'true');
  form.append('selected_files', JSON.stringify(selectedFiles));
  return request<HistoricalImportBulkZipApplyResponse>(
    '/api/historical-import/json/bulk-zip/apply',
    { method: 'POST', body: form },
  );
}

/**
 * POST /api/historical-import/json/backfill-reprocess/audit
 * Performs controlled dry-run audit of historical CPL backfill/reprocess eligibility.
 */
export async function historicalBackfillReprocessAudit(
  payload: HistoricalBackfillAuditRequest,
): Promise<HistoricalBackfillAuditResponse> {
  return request<HistoricalBackfillAuditResponse>(
    '/api/historical-import/json/backfill-reprocess/audit',
    {
      method: 'POST',
      body: JSON.stringify({
        match_ids: payload.match_ids ?? [],
        batch_ids: payload.batch_ids ?? [],
        max_batch_size: payload.max_batch_size ?? 25,
        source_payloads_by_batch: payload.source_payloads_by_batch ?? {},
      }),
    },
  );
}

/**
 * POST /api/historical-import/json/backfill-reprocess/diagnose
 * Performs read-only diagnosis of delivery extraction readiness and failure reasons.
 */
export async function historicalBackfillReprocessDiagnose(
  payload: HistoricalBackfillAuditRequest,
): Promise<HistoricalBackfillDiagnosisResponse> {
  return request<HistoricalBackfillDiagnosisResponse>(
    '/api/historical-import/json/backfill-reprocess/diagnose',
    {
      method: 'POST',
      body: JSON.stringify({
        match_ids: payload.match_ids ?? [],
        batch_ids: payload.batch_ids ?? [],
        max_batch_size: payload.max_batch_size ?? 25,
        source_payloads_by_batch: payload.source_payloads_by_batch ?? {},
      }),
    },
  );
}

/**
 * POST /api/historical-import/json/backfill-reprocess/apply
 * Performs controlled apply/reprocess for selected historical CPL records.
 */
export async function historicalBackfillReprocessApply(
  payload: HistoricalBackfillApplyRequest,
): Promise<HistoricalBackfillApplyResponse> {
  return request<HistoricalBackfillApplyResponse>(
    '/api/historical-import/json/backfill-reprocess/apply',
    {
      method: 'POST',
      body: JSON.stringify({
        confirm: payload.confirm,
        match_ids: payload.match_ids ?? [],
        batch_ids: payload.batch_ids ?? [],
        max_batch_size: payload.max_batch_size ?? 25,
        source_payloads_by_batch: payload.source_payloads_by_batch ?? {},
      }),
    },
  );
}

/**
 * POST /api/historical-import/json/cpl-reset-reimport/dry-run
 * Runs read-only dry-run for controlled historical CPL reset + reimport.
 */
export async function runCplResetReimportDryRun(
  payload: HistoricalCplResetReimportDryRunRequest,
): Promise<HistoricalCplResetReimportDryRunResponse> {
  const form = new FormData();
  form.append('file', payload.file, payload.file.name);
  form.append('max_batch_size', String(payload.max_batch_size ?? 1));
  if (payload.match_ids?.length) {
    form.append('match_ids', JSON.stringify(payload.match_ids));
  }
  if (payload.batch_ids?.length) {
    form.append('batch_ids', JSON.stringify(payload.batch_ids));
  }
  if (payload.season?.trim()) {
    form.append('season', payload.season.trim());
  }
  return request<HistoricalCplResetReimportDryRunResponse>(
    '/api/historical-import/json/cpl-reset-reimport/dry-run',
    { method: 'POST', body: form },
  );
}

/**
 * POST /api/historical-import/json/cpl-reset-reimport/apply
 * Applies controlled historical CPL reset + reimport after dry-run confirmation.
 */
export async function applyCplResetReimport(
  payload: HistoricalCplResetReimportApplyRequest,
): Promise<HistoricalCplResetReimportApplyResponse> {
  const form = new FormData();
  form.append('file', payload.file, payload.file.name);
  form.append('confirm', 'true');
  form.append('max_batch_size', String(payload.max_batch_size ?? 1));
  if (payload.match_ids?.length) {
    form.append('match_ids', JSON.stringify(payload.match_ids));
  }
  if (payload.batch_ids?.length) {
    form.append('batch_ids', JSON.stringify(payload.batch_ids));
  }
  if (payload.season?.trim()) {
    form.append('season', payload.season.trim());
  }
  return request<HistoricalCplResetReimportApplyResponse>(
    '/api/historical-import/json/cpl-reset-reimport/apply',
    { method: 'POST', body: form },
  );
}

/**
 * POST /api/historical-import/json/backfill/{recordId}/reattach-source-json
 * Reattach source JSON to a single blocked historical backfill record.
 */
export async function historicalBackfillReattachSourceJson(
  recordId: string,
  file: File,
): Promise<HistoricalBackfillSourceReattachResponse> {
  const form = new FormData();
  form.append('file', file, file.name);
  return request<HistoricalBackfillSourceReattachResponse>(
    `/api/historical-import/json/backfill/${encodeURIComponent(recordId)}/reattach-source-json`,
    { method: 'POST', body: form },
  );
}

/**
 * POST /api/historical-import/json/source-reattach/dry-run
 * Runs deterministic dry-run matching for historical source payload reattach.
 */
export async function historicalSourcePayloadReattachDryRun(
  file: File,
): Promise<HistoricalSourcePayloadReattachDryRunResponse> {
  const form = new FormData();
  form.append('file', file, file.name);
  return request<HistoricalSourcePayloadReattachDryRunResponse>(
    '/api/historical-import/json/source-reattach/dry-run',
    { method: 'POST', body: form },
  );
}

/**
 * POST /api/historical-import/json/source-reattach/apply
 * Reattaches retained source JSON onto existing historical import records.
 */
export async function historicalSourcePayloadReattachApply(
  file: File,
  selectedMappings: Array<{ file_name: string; batch_id: string }>,
): Promise<HistoricalSourcePayloadReattachApplyResponse> {
  const form = new FormData();
  form.append('file', file, file.name);
  form.append('confirm', 'true');
  form.append('selected_mappings', JSON.stringify(selectedMappings));
  return request<HistoricalSourcePayloadReattachApplyResponse>(
    '/api/historical-import/json/source-reattach/apply',
    { method: 'POST', body: form },
  );
}

/**
 * POST /api/historical-import/json/backfill/source-zip/dry-run
 * Bulk ZIP source payload reattach dry-run for historical CPL imports.
 * Accepts a ZIP, scans JSON entries, and returns mapping candidates with summary counts.
 * Read-only — nothing is mutated.
 */
export async function historicalBulkZipSourcePayloadDryRun(
  file: File,
): Promise<HistoricalBulkZipSourcePayloadDryRunResponse> {
  const form = new FormData();
  form.append('file', file, file.name);
  return request<HistoricalBulkZipSourcePayloadDryRunResponse>(
    '/api/historical-import/json/backfill/source-zip/dry-run',
    { method: 'POST', body: form },
  );
}

/**
 * POST /api/historical-import/json/backfill/source-zip/apply
 * Bulk ZIP source payload reattach apply for historical CPL imports.
 * Applies only selected exact/likely mappings. Requires confirm=true.
 */
export async function historicalBulkZipSourcePayloadApply(
  file: File,
  selectedMappings: Array<{ file_name: string; batch_id: string }>,
): Promise<HistoricalBulkZipSourcePayloadApplyResponse> {
  const form = new FormData();
  form.append('file', file, file.name);
  form.append('confirm', 'true');
  form.append('selected_mappings', JSON.stringify(selectedMappings));
  return request<HistoricalBulkZipSourcePayloadApplyResponse>(
    '/api/historical-import/json/backfill/source-zip/apply',
    { method: 'POST', body: form },
  );
}

/**
 * POST /api/historical-import/json/ocr-review/candidates
 * Upload PDF/image source document and create OCR review candidate.
 */
export async function historicalOcrCreateCandidate(params: {
  file: File;
  candidateJson?: string;
  extractionMethod?: string;
  extractionConfidence?: number | null;
  uncertaintyFlags?: string[];
  ocrText?: string;
}): Promise<HistoricalOcrReviewCandidateResponse> {
  const form = new FormData();
  form.append('file', params.file, params.file.name);
  form.append('extraction_method', params.extractionMethod ?? 'manual_candidate_json');
  if (params.extractionConfidence !== undefined && params.extractionConfidence !== null) {
    form.append('extraction_confidence', String(params.extractionConfidence));
  }
  if (params.uncertaintyFlags?.length) {
    form.append('uncertainty_flags', JSON.stringify(params.uncertaintyFlags));
  }
  if (params.candidateJson) {
    form.append('candidate_json', params.candidateJson);
  }
  if (params.ocrText) {
    form.append('ocr_text', params.ocrText);
  }
  return request<HistoricalOcrReviewCandidateResponse>(
    '/api/historical-import/json/ocr-review/candidates',
    { method: 'POST', body: form },
  );
}

/**
 * GET /api/historical-import/json/ocr-review/candidates/{candidateId}
 * Fetch OCR review candidate details.
 */
export async function historicalOcrGetCandidate(
  candidateId: string,
): Promise<HistoricalOcrReviewCandidateResponse> {
  return request<HistoricalOcrReviewCandidateResponse>(
    `/api/historical-import/json/ocr-review/candidates/${encodeURIComponent(candidateId)}`,
  );
}

/**
 * PATCH /api/historical-import/json/ocr-review/candidates/{candidateId}/review
 * Submit reviewed/corrected structured JSON.
 */
export async function historicalOcrSubmitReview(
  candidateId: string,
  reviewedJson: Record<string, unknown>,
  reviewerNotes?: string,
  uncertaintyFlags: string[] = [],
): Promise<HistoricalOcrReviewCandidateResponse> {
  return request<HistoricalOcrReviewCandidateResponse>(
    `/api/historical-import/json/ocr-review/candidates/${encodeURIComponent(candidateId)}/review`,
    {
      method: 'PATCH',
      body: JSON.stringify({
        reviewed_json: reviewedJson,
        reviewer_notes: reviewerNotes ?? null,
        uncertainty_flags: uncertaintyFlags,
      }),
    },
  );
}

/**
 * POST /api/historical-import/json/ocr-review/candidates/{candidateId}/dry-run
 * Validate reviewed OCR candidate via existing historical JSON dry-run contract.
 */
export async function historicalOcrDryRunCandidate(
  candidateId: string,
  recordPreview = true,
): Promise<HistoricalOcrReviewDryRunResponse> {
  return request<HistoricalOcrReviewDryRunResponse>(
    `/api/historical-import/json/ocr-review/candidates/${encodeURIComponent(candidateId)}/dry-run`,
    { method: 'POST', body: JSON.stringify({ record_preview: recordPreview }) },
  );
}

/**
 * POST /api/historical-import/json/ocr-review/candidates/{candidateId}/reject
 * Mark OCR candidate as rejected/unusable.
 */
export async function historicalOcrRejectCandidate(
  candidateId: string,
  reason: string,
): Promise<HistoricalOcrReviewCandidateResponse> {
  return request<HistoricalOcrReviewCandidateResponse>(
    `/api/historical-import/json/ocr-review/candidates/${encodeURIComponent(candidateId)}/reject`,
    { method: 'POST', body: JSON.stringify({ reason }) },
  );
}

/* ──────────────────────────────────────────────────────────────────────────
   Phase 8C — AI Insight Feedback + Review Workflow
   ────────────────────────────────────────────────────────────────────────── */

/** Discrete review state for an AI-generated insight. */
export type AiInsightReviewState =
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'changes_requested'
  | 'flagged';

/** Discrete feedback signal attached to a review action. */
export type AiInsightFeedbackType =
  | 'useful'
  | 'not_useful'
  | 'unsafe'
  | 'unsupported_claim';

/** A single persisted review record returned by the API. */
export interface AiInsightReviewRecord {
  id: string;
  insight_type: string;
  insight_id: string;
  reviewer_id: string;
  reviewer_org_id: string | null;
  review_state: AiInsightReviewState;
  feedback_type: AiInsightFeedbackType | null;
  note: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * Response from GET /ai-insights/review/{insight_type}/{insight_id}.
 * When no review exists, ``current_state`` is ``'pending'``.
 */
export interface AiInsightReviewStateResponse {
  insight_type: string;
  insight_id: string;
  current_state: AiInsightReviewState;
  latest_review: AiInsightReviewRecord | null;
  total_reviews: number;
  /** Always true — review state is advisory metadata, not official cricket truth. */
  is_advisory_only: boolean;
}

/** Request body for POST /ai-insights/review/{insight_type}/{insight_id}. */
export interface AiInsightReviewSubmit {
  review_state: AiInsightReviewState;
  feedback_type?: AiInsightFeedbackType | null;
  note?: string | null;
}

/**
 * GET /ai-insights/review/{insightType}/{insightId}
 * Fetch the current review state for an AI insight.
 * Requires analyst_pro or org_pro role.
 */
export async function getAiInsightReviewState(
  insightType: string,
  insightId: string,
): Promise<AiInsightReviewStateResponse> {
  return request<AiInsightReviewStateResponse>(
    `/ai-insights/review/${encodeURIComponent(insightType)}/${encodeURIComponent(insightId)}`,
  );
}

/**
 * POST /ai-insights/review/{insightType}/{insightId}
 * Submit a review decision for an AI insight.
 * Requires analyst_pro or org_pro role.
 */
export async function submitAiInsightReview(
  insightType: string,
  insightId: string,
  payload: AiInsightReviewSubmit,
): Promise<AiInsightReviewRecord> {
  return request<AiInsightReviewRecord>(
    `/ai-insights/review/${encodeURIComponent(insightType)}/${encodeURIComponent(insightId)}`,
    { method: 'POST', body: JSON.stringify(payload) },
  );
}


// ---------------------------------------------------------------------------
// Phase 10J — Historical Identity Mapping Review API types and functions
// ---------------------------------------------------------------------------

export interface HistoricalPlayerCandidateItem {
  canonical_player_id: number;
  canonical_player_name: string;
  country: string | null;
  role: string | null;
  confidence: number | null;
  match_reason: string | null;
}

export interface HistoricalPlayerReviewItem {
  source_player_id: string;
  source_player_name: string;
  normalized_name: string;
  source_schema: string | null;
  source_system: string | null;
  resolution_state: string;
  reason: string | null;
  queue_state: string;
  review_required: boolean;
  match_references: string[];
  competition_references: Record<string, unknown>[];
  provenance_references: Record<string, unknown>[];
  candidates: HistoricalPlayerCandidateItem[];
  first_seen: string;
  last_seen: string;
}

export interface HistoricalVenueReviewItem {
  queue_id: string;
  decision_id: string | null;
  raw_imported_value: string;
  normalized_raw_value: string;
  source_schema: string | null;
  source_system: string | null;
  queue_state: string;
  reason: string;
  review_required: boolean;
  competition_name: string | null;
  season: string | null;
  provenance_references: Record<string, unknown>[];
  candidate_venues: Record<string, unknown>[];
  first_seen: string;
  last_seen: string;
}

export interface HistoricalIdentityReviewResponse {
  unresolved_players: HistoricalPlayerReviewItem[];
  unresolved_venues: HistoricalVenueReviewItem[];
  total_unresolved_players: number;
  total_unresolved_venues: number;
}

export interface PlayerLinkRequest {
  canonical_player_id: number;
  reviewed_by?: string | null;
}

export interface PlayerCreateRequest {
  name: string;
  country?: string | null;
  role?: string | null;
  reviewed_by?: string | null;
}

export interface PlayerDeferRequest {
  reason?: string;
  reviewed_by?: string | null;
}

export interface PlayerActionResponse {
  source_player_id: string;
  action: 'linked' | 'created' | 'deferred' | 'ambiguous_blocked';
  canonical_player_id: number | null;
  canonical_player_name: string | null;
  status: string;
  message: string;
  idempotent: boolean;
}

export interface VenueLinkRequest {
  queue_id: string;
  canonical_venue_id: string;
  reviewed_by?: string | null;
}

export interface VenueCreateAliasRequest {
  queue_id: string;
  canonical_venue_id: string;
  reviewed_by?: string | null;
}

export interface VenueCreateRequest {
  queue_id: string;
  canonical_name: string;
  city?: string | null;
  country?: string | null;
  notes?: string | null;
  reviewed_by?: string | null;
}

export interface VenueDeferRequest {
  queue_id: string;
  reason?: string;
  reviewed_by?: string | null;
}

export interface VenueActionResponse {
  queue_id: string;
  action: 'linked' | 'alias_created' | 'venue_created' | 'deferred';
  canonical_venue_id: string | null;
  canonical_venue_name: string | null;
  status: string;
  message: string;
  idempotent: boolean;
}

const IDENTITY_REVIEW_BASE = '/api/historical-import/json/identity-review';

/**
 * GET /api/historical-import/json/identity-review/unresolved
 * Returns unresolved player and venue review items.
 */
export async function getIdentityReviewUnresolved(
  limit = 100,
): Promise<HistoricalIdentityReviewResponse> {
  return request<HistoricalIdentityReviewResponse>(
    `${IDENTITY_REVIEW_BASE}/unresolved?limit=${limit}`,
  );
}

/**
 * POST /api/historical-import/json/identity-review/players/{sourcePlayerId}/link
 * Links a source player to an existing internal Player.
 */
export async function identityReviewPlayerLink(
  sourcePlayerId: string,
  payload: PlayerLinkRequest,
): Promise<PlayerActionResponse> {
  return request<PlayerActionResponse>(
    `${IDENTITY_REVIEW_BASE}/players/${encodeURIComponent(sourcePlayerId)}/link`,
    { method: 'POST', body: JSON.stringify(payload) },
  );
}

/**
 * POST /api/historical-import/json/identity-review/players/{sourcePlayerId}/create
 * Creates a new internal Player from a source player identity.
 */
export async function identityReviewPlayerCreate(
  sourcePlayerId: string,
  payload: PlayerCreateRequest,
): Promise<PlayerActionResponse> {
  return request<PlayerActionResponse>(
    `${IDENTITY_REVIEW_BASE}/players/${encodeURIComponent(sourcePlayerId)}/create`,
    { method: 'POST', body: JSON.stringify(payload) },
  );
}

/**
 * POST /api/historical-import/json/identity-review/players/{sourcePlayerId}/defer
 * Defers resolution of an unresolved source player.
 */
export async function identityReviewPlayerDefer(
  sourcePlayerId: string,
  payload: PlayerDeferRequest,
): Promise<PlayerActionResponse> {
  return request<PlayerActionResponse>(
    `${IDENTITY_REVIEW_BASE}/players/${encodeURIComponent(sourcePlayerId)}/defer`,
    { method: 'POST', body: JSON.stringify(payload) },
  );
}

/**
 * POST /api/historical-import/json/identity-review/venues/link
 * Links an unresolved venue to an existing canonical Venue.
 */
export async function identityReviewVenueLink(
  payload: VenueLinkRequest,
): Promise<VenueActionResponse> {
  return request<VenueActionResponse>(`${IDENTITY_REVIEW_BASE}/venues/link`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * POST /api/historical-import/json/identity-review/venues/create-alias
 * Creates a venue alias for an existing Venue.
 */
export async function identityReviewVenueCreateAlias(
  payload: VenueCreateAliasRequest,
): Promise<VenueActionResponse> {
  return request<VenueActionResponse>(`${IDENTITY_REVIEW_BASE}/venues/create-alias`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * POST /api/historical-import/json/identity-review/venues/create
 * Creates a new Venue from a source venue identity.
 */
export async function identityReviewVenueCreate(
  payload: VenueCreateRequest,
): Promise<VenueActionResponse> {
  return request<VenueActionResponse>(`${IDENTITY_REVIEW_BASE}/venues/create`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * POST /api/historical-import/json/identity-review/venues/defer
 * Defers resolution of an unresolved venue.
 */
export async function identityReviewVenueDefer(
  payload: VenueDeferRequest,
): Promise<VenueActionResponse> {
  return request<VenueActionResponse>(`${IDENTITY_REVIEW_BASE}/venues/defer`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

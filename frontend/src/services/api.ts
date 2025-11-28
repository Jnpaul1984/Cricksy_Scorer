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
console.info('API_BASE', API_BASE, '(URL override:', URL_OVERRIDE || 'none', ')');

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
  id: number;
  name: string;
  logoUrl: string;
  clickUrl?: string | null;
  weight: number;
  surfaces: string[];
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

  /* Scoring */
  scoreDelivery: (gameId: string, body: ScoreDeliveryRequest) =>
    request<Snapshot>(`/games/${encodeURIComponent(gameId)}/deliveries`, {
      method: 'POST',
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

  getGameSponsors: (gameId: string) =>
    request<SponsorRow[]>(`/games/${encodeURIComponent(gameId)}/sponsors`),

  logSponsorImpressions: (payload: SponsorImpressionIn | SponsorImpressionIn[]) =>
    request<SponsorImpressionsOut>('/sponsor_impressions', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  /* Health */
  healthz: () => request<{ status: 'ok' }>('/healthz'),

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

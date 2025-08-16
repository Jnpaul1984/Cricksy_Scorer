// src/utils/api.ts
// Single, canonical API client aligned with FastAPI backend & the Pinia game store.

export const API_BASE =
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE) ||
  (typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.host}` : '') ||
  '';

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
  } catch {}
  return 'Request failed';
}

export type TossDecision = 'bat' | 'bowl'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url(path), {
    headers: {
      ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(init?.headers || {}),
    },
    ...init,
  });
  if (!res.ok) {
    let detail: any = undefined;
    try { detail = await res.json(); } catch {}
    const msg = detail?.detail || `${res.status} ${res.statusText}`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  if (res.status === 204) return undefined as unknown as T;
  return (await res.json()) as T;
}

/* ----------------------------- Types (client) ----------------------------- */

// Create game — mirrors backend CreateGameRequest in main.py
export type MatchType = 'limited' | 'multi_day' | 'custom';
export type Decision = 'bat' | 'bowl';

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
  decision: TossDecision
  // plus many more fields the backend returns; we keep it loose for UI
  [k: string]: any;
}

// Score a delivery — mirrors backend schemas.ScoreDelivery in main.py
export interface ScoreDeliveryRequest {
  striker_id: string;
  non_striker_id: string;
  bowler_id: string;
  runs_scored: number;
  extra?: 'wd' | 'nb' | 'b' | 'lb'; // wire as backend expects: 'wd'|'nb' or 'wide'|'no_ball'—server accepts both
  is_wicket?: boolean;
  dismissal_type?: string | null;
  dismissed_player_id?: string | null;
  commentary?: string | null;
  fielder_id?: string | null;
}

// Snapshot — shape can vary; we keep it open but document common fields
export interface Snapshot {
  id?: string;
  status?: string;
  score?: { runs: number; wickets: number; overs: number | string };
  total_runs?: number;
  total_wickets?: number;
  overs_completed?: number;
  balls_this_over?: number;
  current_inning?: number;
  batting_team_name?: string;
  bowling_team_name?: string;
  batting_scorecard?: Record<string, any>;
  bowling_scorecard?: Record<string, any>;
  last_delivery?: Record<string, any> | null;
  [k: string]: any;
}

export interface OversLimitBody { overs_limit: number; }

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

/* ----------------------------- API surface ------------------------------- */

export const apiService = {
  /* Games */
  createGame: (body: CreateGameRequest) =>
    request<GameMinimal>('/games', { method: 'POST', body: JSON.stringify(body) }),

  getGame: (gameId: string) =>
    request<GameMinimal>(`/games/${encodeURIComponent(gameId)}`),

  getSnapshot: (gameId: string) =>
    request<Snapshot>(`/games/${encodeURIComponent(gameId)}/snapshot`),

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

  setOversLimit: (gameId: string, body: OversLimitBody) =>
    request<{ id: string; overs_limit: number }>(
      `/games/${encodeURIComponent(gameId)}/overs-limit`,
      { method: 'POST', body: JSON.stringify(body) },
    ),

  setTeamRoles: (gameId: string, body: TeamRoleUpdate) =>
    request<{ ok: true; team_roles: any }>(
      `/games/${encodeURIComponent(gameId)}/team-roles`,
      { method: 'POST', body: JSON.stringify(body) },
    ),

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
  startNextInnings: async (gameId: string) => {
    throw new Error('startNextInnings endpoint not implemented on server');
  },
};

export default apiService;

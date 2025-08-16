// ============================================================================
// File: src/services/api.ts
// Purpose: Lightweight HTTP client for scoring actions and fetching snapshots
// Notes: Uses native fetch (no axios dependency). Reads base URL from env.
//        Add VITE_API_BASE to your .env (example below).
// ============================================================================

/* eslint-disable @typescript-eslint/no-explicit-any */

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

const API_BASE = import.meta.env.VITE_API_BASE?.replace(/\/$/, '') || 'http://localhost:8000';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`;
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  const res = await fetch(url, { ...options, headers, credentials: 'include' });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} ${res.statusText} → ${text}`);
  }
  // some endpoints may 204
  if (res.status === 204) return undefined as unknown as T;
  return (await res.json()) as T;
}

// -------------------- Types (align with backend) ----------------------------
export interface DeliveryRequest {
  game_id: string;
  over?: number;             // optional if backend computes
  ball?: number;             // optional
  striker_id?: string;       // batter UUID
  non_striker_id?: string;   // batter UUID
  bowler_id?: string;        // bowler UUID
  runs?: number;             // 0..6
  extra_type?: 'wide' | 'no_ball' | 'bye' | 'leg_bye' | 'penalty' | null;
  extra_runs?: number | null;
  wicket?: {
    kind: string;            // 'bowled' | 'caught' | ... align with backend
    batter_id?: string;
    fielder_id?: string | null;
  } | null;
  commentary?: string | null;
}

export interface ScoreSnapshot {
  game_id: string;
  innings_no: number;
  batting_team_id: string;
  bowling_team_id: string;
  runs: number;
  wickets: number;
  overs: string; // e.g. "14.3"
  run_rate?: number;
  extras?: {
    wides: number; no_balls: number; byes: number; leg_byes: number; penalties: number;
  };
}

export interface BatterLine {
  player_id: string; name: string; runs: number; balls: number; fours: number; sixes: number; strike_rate: number; is_striker?: boolean;
}
export interface BowlerLine {
  player_id: string; name: string; overs: string; maidens: number; runs: number; wickets: number; econ: number; current_over?: string;
}

export interface ScoreUpdatePayload {
  score: ScoreSnapshot;
  batting: BatterLine[];
  bowling: BowlerLine[];
}

// -------------------- API surface ------------------------------------------
export const Api = {
  // POST one delivery and receive server-computed snapshot back
  postDelivery: (body: DeliveryRequest) =>
    request<ScoreUpdatePayload>('/deliveries', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  // fetch full snapshot (useful on page load/reconnect)
  getSnapshot: (gameId: string) =>
    request<ScoreUpdatePayload>(`/games/${encodeURIComponent(gameId)}/snapshot`),
};

export default Api;
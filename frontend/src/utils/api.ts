// src/utils/api.ts
import type {
  GameState,
  CreateGameRequest,
  ScoreDeliveryRequest,
} from '@/types'

/**
 * Base API URL (no trailing slash).
 * Configure in .env as VITE_API_BASE_URL="http://localhost:8000"
 */
const BASE_URL =
  (import.meta?.env?.VITE_API_BASE_URL as string | undefined)?.replace(/\/+$/, '') ||
  'http://localhost:8000'

/**
 * Small typed fetch wrapper that:
 * - sets JSON headers
 * - throws on non-OK responses with a useful message
 * - returns T (parsed JSON) or `undefined` for empty 204 responses
 */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    credentials: 'include', // change to 'omit' if you don't use cookies
    ...init,
  })

  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) msg = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      if (body?.message) msg = body.message
      // Fall through to throw with msg below
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(msg)
  }

  // Handle 204/empty body
  const text = await res.text()
  return text ? (JSON.parse(text) as T) : (undefined as unknown as T)
}

/** Public helper the store uses to normalize unknown errors into strings */
export function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message
  if (typeof err === 'string') return err
  try {
    return JSON.stringify(err)
  } catch {
    return 'Unknown error'
  }
}

/**
 * API surface used by the Pinia store.
 * NOTE: Adjust endpoint paths if your backend routes differ.
 */
export const apiService = {
  /** Create a new game */
  async createGame(payload: CreateGameRequest): Promise<GameState> {
    return request<GameState>('/games', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  /** Load a game by id */
  async getGame(id: string): Promise<GameState> {
    return request<GameState>(`/games/${encodeURIComponent(id)}`, {
      method: 'GET',
    })
  },

  /** Score a single delivery */
  async scoreDelivery(id: string, body: ScoreDeliveryRequest): Promise<GameState> {
    // If your backend path is different, e.g. `/games/{id}/deliveries`, update it here.
    return request<GameState>(`/games/${encodeURIComponent(id)}/score-delivery`, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  /** Start or advance to the next innings */
  async startNextInnings(id: string): Promise<GameState> {
    return request<GameState>(`/games/${encodeURIComponent(id)}/next-innings`, {
      method: 'POST',
    })
  },

  /** Add a commentary line (used by store.postCommentary) */
  async postCommentary(
    id: string,
    body: { text: string; over?: string }
  ): Promise<{ ok: true } | void> {
    // Update the path if your backend uses a different route.
    return request<{ ok: true }>(`/games/${encodeURIComponent(id)}/commentary`, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },
}

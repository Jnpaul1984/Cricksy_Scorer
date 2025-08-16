// frontend/src/utils/api.ts
import type {
  GameState,
  CreateGameRequest,
  ScoreDeliveryRequest,
} from '@/types'

const BASE_URL =
  import.meta?.env?.VITE_API_BASE_URL?.replace(/\/+$/, '') || 'http://localhost:8000'

/** Small typed fetch wrapper */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    credentials: 'include', // adjust if your API doesn’t use cookies
    ...init,
  })
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) msg = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      if (body?.message) msg = body.message
    } catch {
      // ignore JSON parse error
    }
    throw new Error(msg)
  }
  // 204 No Content or empty body:
  const text = await res.text()
  return text ? (JSON.parse(text) as T) : (undefined as unknown as T)
}

/** Public helper used by the store to normalize errors */
export function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message
  if (typeof err === 'string') return err
  try {
    return JSON.stringify(err)
  } catch {
    return 'Unknown error'
  }
}

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
    // Adjust the path if your backend differs (e.g. '/games/{id}/deliveries')
    return request<GameState>(`/games/${encodeURIComponent(id)}/score-delivery`, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  /** Start or advance to the next innings */
  async startNextInnings(id: string): Promise<GameState> {
    // Adjust the path if your backend uses a different route
    return request<GameState>(`/games/${encodeURIComponent(id)}/next-innings`, {
      method: 'POST',
    })
  },

  /** Add a commentary line (used by the store’s postCommentary) */
  async postCommentary(
    id: string,
    body: { text: string; over?: string }
  ): Promise<{ ok: true } | void> {
    // Adjust the path if your backend differs
    return request<{ ok: true }>(`/games/${encodeURIComponent(id)}/commentary`, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },
}

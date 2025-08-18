// src/utils/socket.ts
// Strongly-typed Socket.IO client for Cricksy Scorer

import type { Socket, ManagerOptions, SocketOptions } from 'socket.io-client'
import { io } from 'socket.io-client'

export const SOCKET_URL: string =
  (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_SOCKET_URL) ||
  (typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.host}` : '') ||
  ''

/** Common lightweight card/score shapes (kept loose to avoid tight coupling) */
type OversLike = string | number
type UUID = string

/** Server -> Client events */
export interface ServerToClientEvents {
  'presence:init': (payload: {
    game_id: string
    members: Array<{ sid: string; role: string; name: string }>
  }) => void

  'presence:update': (payload: {
    game_id: string
    joined?: Array<{ sid: string; role: string; name: string }>
    left?: Array<{ sid: string }>
  }) => void

  /**
   * Full or partial state snapshot.
   * We keep it flexible but include gate flags explicitly so TS knows about them.
   */
  'state:update': (payload: {
    id: string
    snapshot: {
      // score / meta (subset)
      total_runs?: number
      total_wickets?: number
      overs_completed?: number
      balls_this_over?: number
      current_inning?: number
      batting_team_name?: string
      bowling_team_name?: string
      status?: string
      target?: number | null

      // cards (loose)
      batting_scorecard?: Record<string, any>
      bowling_scorecard?: Record<string, any>
      last_delivery?: Record<string, any> | null

      // runtime bowling context (loose)
      current_bowler_id?: UUID | null
      last_ball_bowler_id?: UUID | null
      current_over_balls?: number
      mid_over_change_used?: boolean
      balls_bowled_total?: number

      // NEW gate flags
      needs_new_batter?: boolean
      needs_new_over?: boolean

      // allow future keys
      [k: string]: any
    }
  }) => void

  /**
   * Slim score tick update (optional cards); server MAY also include gate flags.
   * Your store already normalizes this and optionally refetches the full snapshot.
   */
  'score:update': (payload: {
    game_id?: string
    score?: { runs: number; wickets: number; overs: OversLike; innings_no?: number }
    batting?: Array<{ player_id: string; name: string; runs: number; balls?: number; fours?: number; sixes?: number; strike_rate?: number; is_striker?: boolean }>
    bowling?: Array<{ player_id: string; name: string; overs?: OversLike; maidens?: number; runs: number; wickets: number; econ?: number }>

    // NEW (optional): gate flags may be emitted with the tick as a hint
    needs_new_batter?: boolean
    needs_new_over?: boolean

    [k: string]: any
  }) => void

  'commentary:new': (payload: { game_id: string; text: string; at: string }) => void
}

/** Client -> Server events */
export interface ClientToServerEvents {
  join: (payload: { game_id: string }) => void
  leave?: (payload: { game_id: string }) => void
  ping?: (payload?: { t?: number }) => void
}

let socket: (Socket<ServerToClientEvents, ClientToServerEvents> & { _connectedOnce?: boolean }) | null = null

function ensureSocket(): Socket<ServerToClientEvents, ClientToServerEvents> {
  if (socket) return socket

  // SSR/Non-browser guard: return a no-op proxy
  if (typeof window === 'undefined') {
    return new Proxy({}, { get: () => () => {} }) as Socket<ServerToClientEvents, ClientToServerEvents>
  }

  const opts: Partial<ManagerOptions & SocketOptions> = {
    autoConnect: false,
    withCredentials: true,
    transports: ['websocket'],
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 500,
    reconnectionDelayMax: 5000,
    timeout: 10000,
  }

  socket = io(SOCKET_URL || undefined, opts) as Socket<ServerToClientEvents, ClientToServerEvents>
  socket.on('connect', () => { (socket as any)._connectedOnce = true })
  return socket
}

export function connectSocket(customAuth?: Record<string, unknown>): void {
  const s = ensureSocket()
  if (customAuth && typeof customAuth === 'object') {
    const sockAny: any = s
    sockAny.auth = { ...(sockAny.auth || {}), ...customAuth }
  }
  if (!s.connected) s.connect()
}

export function disconnectSocket(): void {
  const s = ensureSocket()
  if (s.connected) s.disconnect()
}

export function joinGame(gameId: string): void {
  const s = ensureSocket()
  if (!s.connected) s.connect()
  s.emit('join', { game_id: gameId })
}

/** Event helpers (typed) */
export function on<E extends keyof ServerToClientEvents>(
  event: E,
  handler: ServerToClientEvents[E]
): void
export function on(event: string, handler: (...args: unknown[]) => void): void
export function on(event: string, handler: (...args: unknown[]) => void): void {
  const s = ensureSocket()
  ;(s as any).on(event as any, handler as any)
}

export function off<E extends keyof ServerToClientEvents>(
  event: E,
  handler?: ServerToClientEvents[E]
): void
export function off(event: string, handler?: (...args: unknown[]) => void): void
export function off(event: string, handler?: (...args: unknown[]) => void): void {
  const s = ensureSocket()
  ;(s as any).off(event as any, handler as any)
}

export function emit<E extends keyof ClientToServerEvents>(
  event: E,
  ...args: Parameters<NonNullable<ClientToServerEvents[E]>>
): void {
  const s = ensureSocket()
  const sockAny: any = s
  sockAny.emit(event, ...args)
}

export function isConnected(): boolean {
  const s = ensureSocket()
  return !!s?.connected
}

export function getSocket(): Socket<ServerToClientEvents, ClientToServerEvents> {
  return ensureSocket()
}

export type { ServerToClientEvents as S2CEvents, ClientToServerEvents as C2SEvents }

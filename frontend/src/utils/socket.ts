// frontend/src/utils/socket.ts
// Typed Socket.IO client for Cricksy. Safe to import anywhere.

// Install once if needed:  npm i socket.io-client
import { io, Socket } from 'socket.io-client'
import type { StateUpdatePayload } from '@/types'
import type { ScoreUpdatePayload } from '@/services/api'

// Re-export server payload types so components/stores can import from "@/utils/socket"
export type {
  DeliveryRequest,
  ScoreSnapshot,
  BatterLine,
  BowlerLine,
  ScoreUpdatePayload,
} from '@/services/api'

// ---- Singleton socket -------------------------------------------------------
let socket: Socket | null = null

const SOCKET_URL =
  import.meta?.env?.VITE_SOCKET_URL ||
  import.meta?.env?.VITE_API_BASE_URL || // some setups use this
  import.meta?.env?.VITE_API_BASE ||      // or this (matches the API base)
  'http://localhost:8000'

// If your backend uses a non-default socket path, set it here:
// const SOCKET_PATH = '/socket.io';

function ensureSocket(): Socket {
  if (socket && socket.connected) return socket
  if (!socket) {
    socket = io(SOCKET_URL, {
      transports: ['websocket'],
      withCredentials: true,
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 500,
      // path: SOCKET_PATH,
    })
    // Optional debug logs:
    socket.on('connect', () => console.debug('[socket] connected', socket?.id))
    socket.on('disconnect', (reason) => console.warn('[socket] disconnected:', reason))
    socket.on('connect_error', (err) => console.error('[socket] connect_error:', err?.message || err))
  }
  return socket!
}

// ---- Event typing -----------------------------------------------------------
// Match this to what the server emits.
export interface EventMap {
  // connection/lifecycle
  'hello': { sid?: string } | undefined            // some servers just send a ping
  'live:connected': { sid?: string; at?: string }  // optional, if you emit it

  // game/state
  'state:update': import('@/types').StateUpdatePayload

  // scoring
  'score:update': import('@/services/api').ScoreUpdatePayload
  'delivery:new': unknown

  // commentary (align to server)
  'commentary:new': { game_id: string; text: string; at: string }
}

// ---- Public API -------------------------------------------------------------
export function connectSocket(): void {
  ensureSocket()
}

export function disconnectSocket(): void {
  if (!socket) return
  try {
    socket.removeAllListeners()
    socket.disconnect()
  } finally {
    socket = null
  }
}

export function joinGame(gameId: string): void {
  const s = ensureSocket()
  s.emit('join_game', { game_id: gameId })
}

export function on<K extends keyof EventMap>(event: K, cb: (payload: EventMap[K]) => void): void {
  const s = ensureSocket()
  s.on(event as string, cb as any)
}

export function off<K extends keyof EventMap>(event: K, cb?: (payload: EventMap[K]) => void): void {
  if (!socket) return
  if (cb) socket.off(event as string, cb as any)
  else socket.removeAllListeners(event as string)
}

export function emit<T = unknown>(event: string, payload?: T): void {
  const s = ensureSocket()
  s.emit(event, payload as any)
}

// ---- Optional: Snapshot type (if you also consume a looser shape somewhere) -
export type Snapshot = Partial<{
  total_runs: number
  total_wickets: number
  overs_completed: number
  balls_this_over: number
  current_inning: number
  status: 'not_started' | 'in_progress' | 'innings_break' | 'completed'
  target: number | null
  batting_team_name: string
  bowling_team_name: string
  batting_scorecard: Record<string, unknown>
  bowling_scorecard: Record<string, unknown>
  deliveries: unknown[]
  current_striker_id: string | null
  current_non_striker_id: string | null
}>

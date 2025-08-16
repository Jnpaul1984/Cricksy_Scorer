// src/utils/socket.ts
// Strongly-typed Socket.IO client for Cricksy Scorer
// Removed unused @ts-expect-error directives for Pylance safety

import type { Socket, ManagerOptions, SocketOptions } from 'socket.io-client'
import { io } from 'socket.io-client'

const SOCKET_URL: string =
  (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_SOCKET_URL) ||
  (typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.host}` : '') ||
  ''

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
  'state:update': (payload: { id: string; snapshot: unknown }) => void
  'score:update': (payload: {
    game_id?: string
    score?: { runs: number; wickets: number; overs: string | number; innings_no?: number }
    batting?: Array<{ player_id: string; name: string; runs: number; balls?: number; fours?: number; sixes?: number; strike_rate?: number; is_striker?: boolean }>
    bowling?: Array<{ player_id: string; name: string; overs?: number | string; maidens?: number; runs: number; wickets: number; econ?: number }>
  }) => void
  'commentary:new': (payload: { game_id: string; text: string; at: string }) => void
}

export interface ClientToServerEvents {
  join: (payload: { game_id: string }) => void
  leave?: (payload: { game_id: string }) => void
  ping?: (payload?: { t?: number }) => void
}

let socket: (Socket<ServerToClientEvents, ClientToServerEvents> & { _connectedOnce?: boolean }) | null = null

function ensureSocket(): Socket<ServerToClientEvents, ClientToServerEvents> {
  if (socket) return socket
  if (typeof window === 'undefined') {
    return new Proxy({}, {
      get: () => () => {},
    }) as Socket<ServerToClientEvents, ClientToServerEvents>
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
  const s: Socket<ServerToClientEvents, ClientToServerEvents> = ensureSocket()
  if (customAuth && typeof customAuth === 'object') {
    const sockAny: any = s
    sockAny.auth = { ...(sockAny.auth || {}), ...customAuth }
  }
  if (!s.connected) s.connect()
}

export function disconnectSocket(): void {
  const s: Socket<ServerToClientEvents, ClientToServerEvents> = ensureSocket()
  if (s.connected) s.disconnect()
}

export function joinGame(gameId: string): void {
  const s: Socket<ServerToClientEvents, ClientToServerEvents> = ensureSocket()
  if (!s.connected) s.connect()
  s.emit('join', { game_id: gameId })
}

export function on<E extends keyof ServerToClientEvents>(
  event: E,
  handler: ServerToClientEvents[E]
): void
export function on(event: string, handler: (...args: unknown[]) => void): void
export function on(event: string, handler: (...args: unknown[]) => void): void {
  const s: Socket<ServerToClientEvents, ClientToServerEvents> = ensureSocket()
  ;(s as any).on(event as any, handler as any)
}

export function off<E extends keyof ServerToClientEvents>(
  event: E,
  handler?: ServerToClientEvents[E]
): void
export function off(event: string, handler?: (...args: unknown[]) => void): void
export function off(event: string, handler?: (...args: unknown[]) => void): void {
  const s: Socket<ServerToClientEvents, ClientToServerEvents> = ensureSocket()
  ;(s as any).off(event as any, handler as any)
}

export function emit<E extends keyof ClientToServerEvents>(
  event: E,
  ...args: Parameters<NonNullable<ClientToServerEvents[E]>>
): void {
  const s: Socket<ServerToClientEvents, ClientToServerEvents> = ensureSocket()
  const sockAny: any = s
  sockAny.emit(event, ...args)
}

export function isConnected(): boolean {
  const s: Socket<ServerToClientEvents, ClientToServerEvents> = ensureSocket()
  return !!s?.connected
}

export function getSocket(): Socket<ServerToClientEvents, ClientToServerEvents> {
  return ensureSocket()
}

export type { ServerToClientEvents as S2CEvents, ClientToServerEvents as C2SEvents }

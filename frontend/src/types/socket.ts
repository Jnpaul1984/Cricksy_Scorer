// frontend/src/utils/live.ts
// If your store imports "@/utils/socket", either rename this file to socket.ts
// or update the import there to "@/utils/live".

import { io, Socket } from 'socket.io-client'

let socket: Socket | null = null

const SOCKET_URL =
  import.meta?.env?.VITE_SOCKET_URL ||
  import.meta?.env?.VITE_API_BASE_URL || // fall back to API host
  'http://localhost:8000'

/** Connect (idempotent) */
export function connectSocket(): void {
  if (socket && socket.connected) return

  socket = io(SOCKET_URL, {
    transports: ['websocket'],
    withCredentials: true, // adjust if you don’t use cookies
    // path: '/socket.io', // uncomment if your server uses a custom path
    autoConnect: true,
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 500,
  })

  // Basic visibility logs (optional)
  socket.on('connect', () => {
    // console.log('[socket] connected', socket?.id)
  })
  socket.on('disconnect', () => {
    // console.log('[socket] disconnected')
  })
  socket.on('connect_error', (err) => {
    // console.warn('[socket] connect_error', err?.message || err)
  })
}

/** Disconnect safely */
export function disconnectSocket(): void {
  if (!socket) return
  try {
    socket.removeAllListeners()
    socket.disconnect()
  } finally {
    socket = null
  }
}

/**
 * Subscribe to an event.
 * Callback is optional here so calls like on('hello', cb) and on('hello', undefined) won’t type‑error.
 * In practice, pass a real callback.
 */
export function on<T = unknown>(event: string, cb?: (payload: T) => void): void {
  if (!socket) return
  socket.on(event, cb || (() => {}))
}

// Add or extend your Snapshot type to reflect what the server sends
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
  deliveries: unknown[] // or your Delivery[]
  current_striker_id: string | null
  current_non_striker_id: string | null
}>

/**
 * Unsubscribe from an event.
 * If cb is provided, remove that listener; otherwise remove all listeners for the event.
 */
export function off<T = unknown>(event: string, cb?: (payload: T) => void): void {
  if (!socket) return
  if (cb) {
    socket.off(event, cb)
  } else {
    socket.removeAllListeners(event)
  }
}

/** Emit utility (not strictly required by your store, but handy) */
export function emit<T = unknown>(event: string, payload?: T): void {
  if (!socket) return
  socket.emit(event, payload as any)
}

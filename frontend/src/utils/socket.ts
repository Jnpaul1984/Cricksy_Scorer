import { io, Socket } from 'socket.io-client'

let socket: Socket | null = null

export function connectSocket() {
  if (socket && socket.connected) return
  socket = io(import.meta.env.VITE_SOCKET_URL, {
    transports: ['websocket'],
    autoConnect: true,
  })
}

export function disconnectSocket() {
  if (!socket) return
  try {
    socket.disconnect()
  } finally {
    socket = null
  }
}

export function getSocket(): Socket | null {
  return socket
}

/**
 * Typed event subscription.
 * Usage:
 *   on<StateUpdatePayload>('state:update', (payload) => { ... })
 */
export function on<T = any>(event: string, cb: (data: T) => void) {
  socket?.on(event, cb as any)
}

export function off<T = any>(event: string, cb: (data: T) => void) {
  socket?.off(event, cb as any)
}

/* Optional helper */
export function isConnected() {
  return Boolean(socket?.connected)
}

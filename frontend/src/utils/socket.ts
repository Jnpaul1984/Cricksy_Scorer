import { io, Socket } from 'socket.io-client'

let socket: Socket | null = null

// Prefer explicit URL, fall back to API base, then localhost.
const SOCKET_URL =
  import.meta.env.VITE_SOCKET_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  'http://localhost:8000'

export function connectSocket() {
  // Create once; if it exists but isn't connected, connect it.
  if (!socket) {
    socket = io(SOCKET_URL, {
      path: '/socket.io',         // default; keep explicit for clarity
      transports: ['websocket'],  // prefer ws
      autoConnect: false,         // connect manually so we can attach listeners first
      withCredentials: true,      // if you ever send cookies/CORS
    })

    // Standard lifecycle—useful in logs
    socket.on('connect', () => {
      // Your store listens for 'hello' — trigger the server handshake if it expects it.
      socket?.emit('hello', { ts: Date.now() })
    })
    socket.on('reconnect', () => {
      // On reconnect, also send hello so the store handler fires again
      socket?.emit('hello', { ts: Date.now(), reason: 'reconnect' })
    })
    // (Optional but handy)
    socket.on('connect_error', (err) => {
      // eslint-disable-next-line no-console
      console.error('[socket] connect_error:', err?.message || err)
    })
    socket.on('disconnect', (reason) => {
      // eslint-disable-next-line no-console
      console.warn('[socket] disconnected:', reason)
    })
  }

  if (!socket.connected) {
    socket.connect()
  }
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

/** Typed event subscription */
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

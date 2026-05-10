// ============================================================================
// File: src/services/liveSocket.ts
// Purpose: Socket.IO client wrapper. Joins game room and forwards events.
// Install (if needed): npm i socket.io-client
// Env: VITE_SOCKET_URL (e.g., https://api.example.com)
// ============================================================================
import { io } from "socket.io-client";
const LIVE_SOCKET_PATH = "/ws/live";
const BASE_SOCKET_URL = import.meta.env.VITE_SOCKET_URL ||
    (typeof window !== "undefined" ? window.location.origin : "") ||
    "";
const SOCKET_URL = (() => {
    const trimmed = BASE_SOCKET_URL.replace(/\/+$/, "");
    if (!trimmed)
        return LIVE_SOCKET_PATH;
    return trimmed.endsWith(LIVE_SOCKET_PATH) ? trimmed : `${trimmed}${LIVE_SOCKET_PATH}`;
})();
export class LiveSocket {
    socket = null;
    connect() {
        if (this.socket)
            return this.socket;
        this.socket = io(SOCKET_URL, {
            transports: ['websocket'],
            withCredentials: true,
            autoConnect: true,
        });
        // basic debug hooks
        this.socket.on('connect', () => console.debug('[live] connected', this.socket?.id));
        this.socket.on('disconnect', (reason) => console.warn('[live] disconnected', reason));
        this.socket.on('connect_error', (err) => console.error('[live] connect_error', err.message));
        return this.socket;
    }
    joinGame(gameId) {
        this.connect();
        this.socket.emit('join_game', { game_id: gameId });
    }
    on(event, cb) {
        this.connect();
        this.socket.on(event, cb);
    }
    off(event, cb) {
        this.socket?.off(event, cb);
    }
}
export const live = new LiveSocket();

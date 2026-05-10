// src/utils/socket.ts
// Strongly-typed Socket.IO client for Cricksy Scorer
import { io } from 'socket.io-client';
export const SOCKET_URL = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_SOCKET_URL) ||
    (typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.host}` : '') ||
    '';
let socket = null;
function ensureSocket() {
    if (socket)
        return socket;
    // SSR/Non-browser guard: return a no-op proxy
    if (typeof window === 'undefined') {
        return new Proxy({}, { get: () => () => { } });
    }
    const opts = {
        autoConnect: false,
        withCredentials: true,
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 500,
        reconnectionDelayMax: 5000,
        timeout: 10000,
    };
    socket = io(SOCKET_URL || undefined, opts);
    socket.on('connect', () => { socket._connectedOnce = true; });
    return socket;
}
export function connectSocket(customAuth) {
    const s = ensureSocket();
    if (customAuth && typeof customAuth === 'object') {
        const sockAny = s;
        sockAny.auth = { ...(sockAny.auth || {}), ...customAuth };
    }
    if (!s.connected)
        s.connect();
}
export function disconnectSocket() {
    const s = ensureSocket();
    if (s.connected)
        s.disconnect();
}
export function joinGame(gameId) {
    const s = ensureSocket();
    if (!s.connected)
        s.connect();
    s.emit('join', { game_id: gameId });
}
export function on(event, handler) {
    const s = ensureSocket();
    s.on(event, handler);
}
export function off(event, handler) {
    const s = ensureSocket();
    s.off(event, handler);
}
export function emit(event, ...args) {
    const s = ensureSocket();
    const sockAny = s;
    sockAny.emit(event, ...args);
}
export function isConnected() {
    const s = ensureSocket();
    return !!s?.connected;
}
export function getSocket() {
    return ensureSocket();
}

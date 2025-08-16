// ============================================================================
// File: src/services/liveSocket.ts
// Purpose: Socket.IO client wrapper. Joins game room and forwards events.
// Install (if needed): npm i socket.io-client
// Env: VITE_SOCKET_URL (e.g., http://localhost:8000)
// ============================================================================

import { io, Socket } from 'socket.io-client';
import type { ScoreUpdatePayload } from './api';

const SOCKET_URL = import.meta.env.VITE_SOCKET_URL || 'http://localhost:8000';

export type LiveEvents = {
  /** Emitted by server after a successful delivery POST and recompute */
  'score:update': (payload: ScoreUpdatePayload) => void;
  /** Emitted by server with raw delivery if you want granular animations */
  'delivery:new': (payload: unknown) => void;
  /** Optional: commentary streaming */
  'commentary:new': (payload: { game_id: string; text: string; at: string }) => void;
};

export class LiveSocket {
  private socket: Socket | null = null;

  connect() {
    if (this.socket) return this.socket;
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

  joinGame(gameId: string) {
    this.connect();
    this.socket!.emit('join_game', { game_id: gameId });
  }

  on<K extends keyof LiveEvents>(event: K, cb: LiveEvents[K]) {
    this.connect();
    this.socket!.on(event as string, cb as any);
  }

  off<K extends keyof LiveEvents>(event: K, cb: LiveEvents[K]) {
    this.socket?.off(event as string, cb as any);
  }
}

export const live = new LiveSocket();
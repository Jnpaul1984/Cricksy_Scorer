import { io, Socket } from "socket.io-client";
import { ref, onUnmounted } from "vue";

// Adjust to your backend URL/port
const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const socket: Socket = io(API_URL, { transports: ["websocket"] });

type Member = { sid: string; role: string; name: string };
const membersByGame = new Map<string, Member[]>();

export function useRealtime() {
  const connected = ref(socket.connected);

  const onConnect = () => (connected.value = true);
  const onDisconnect = () => (connected.value = false);

  socket.on("connect", onConnect);
  socket.on("disconnect", onDisconnect);

  const onPresenceInit = (payload: { game_id: string; members: Member[] }) => {
    membersByGame.set(payload.game_id, payload.members);
  };
  const onPresenceUpdate = (payload: { game_id: string; members: Member[] }) => {
    membersByGame.set(payload.game_id, payload.members);
  };

  socket.on("presence:init", onPresenceInit);
  socket.on("presence:update", onPresenceUpdate);

  function join(gameId: string, role: "SCORER"|"COMMENTATOR"|"ANALYST"|"VIEWER" = "VIEWER", name?: string) {
    socket.emit("join", { game_id: gameId, role, name });
  }
  function leave(gameId: string) {
    socket.emit("leave", { game_id: gameId });
  }
  function getMembers(gameId: string): Member[] {
    return membersByGame.get(gameId) ?? [];
  }
  function on<T = any>(event: string, handler: (p: T) => void) {
    socket.on(event, handler);
  }
  function off(event: string, handler?: (...args: any[]) => void) {
    socket.off(event, handler as any);
  }

  onUnmounted(() => {
    socket.off("connect", onConnect);
    socket.off("disconnect", onDisconnect);
    socket.off("presence:init", onPresenceInit);
    socket.off("presence:update", onPresenceUpdate);
  });

  return { socket, connected, join, leave, on, off, getMembers };
}

import { io } from "socket.io-client";
import { ref, onUnmounted } from "vue";
import { API_BASE } from "@/utils/api";
const SOCKET_URL = import.meta.env.VITE_SOCKET_URL ||
    import.meta.env.VITE_API_URL ||
    API_BASE ||
    (typeof window !== "undefined" ? window.location.origin : "");
const socket = io(SOCKET_URL, { transports: ["websocket"] });
const membersByGame = new Map();
export function useRealtime() {
    const connected = ref(socket.connected);
    const onConnect = () => (connected.value = true);
    const onDisconnect = () => (connected.value = false);
    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);
    const onPresenceInit = (payload) => {
        membersByGame.set(payload.game_id, payload.members);
    };
    const onPresenceUpdate = (payload) => {
        membersByGame.set(payload.game_id, payload.members);
    };
    socket.on("presence:init", onPresenceInit);
    socket.on("presence:update", onPresenceUpdate);
    function join(gameId, role = "VIEWER", name) {
        socket.emit("join", { game_id: gameId, role, name });
    }
    function leave(gameId) {
        socket.emit("leave", { game_id: gameId });
    }
    function getMembers(gameId) {
        return membersByGame.get(gameId) ?? [];
    }
    function on(event, handler) {
        socket.on(event, handler);
    }
    function off(event, handler) {
        socket.off(event, handler);
    }
    onUnmounted(() => {
        socket.off("connect", onConnect);
        socket.off("disconnect", onDisconnect);
        socket.off("presence:init", onPresenceInit);
        socket.off("presence:update", onPresenceUpdate);
    });
    return { socket, connected, join, leave, on, off, getMembers };
}

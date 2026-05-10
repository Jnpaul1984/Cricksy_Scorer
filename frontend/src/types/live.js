// src/types/live.ts
export function withLiveTypes(socket) {
    return {
        on(event, handler) {
            socket.on(event, handler);
            return this;
        },
        off(event, handler) {
            socket.off(event, handler);
            return this;
        },
        emit(event, payload) {
            socket.emit(event, payload);
            return this;
        },
    };
}
// ---------- Guard utilities (optional lightweight checks) ----------
export const isUUID = (s) => /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(s);
export const assertXIShape = (p) => {
    if (!Array.isArray(p.team_a) || !Array.isArray(p.team_b)) {
        throw new Error("team_a and team_b must be arrays");
    }
    if (![...p.team_a, ...p.team_b].every((x) => typeof x === "string" && isUUID(x))) {
        throw new Error("All XI player ids must be UUID strings");
    }
};

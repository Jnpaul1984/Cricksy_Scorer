import type { ScoreUpdatePayload } from "./api";
export type LiveEvents = {
    /** Emitted by server after a successful delivery POST and recompute */
    'score:update': (payload: ScoreUpdatePayload) => void;
    /** Emitted by server with raw delivery if you want granular animations */
    'delivery:new': (payload: unknown) => void;
    /** Optional: commentary streaming */
    'commentary:new': (payload: {
        game_id: string;
        text: string;
        at: string;
    }) => void;
};
export declare class LiveSocket {
    private socket;
    connect(): any;
    joinGame(gameId: string): void;
    on<K extends keyof LiveEvents>(event: K, cb: LiveEvents[K]): void;
    off<K extends keyof LiveEvents>(event: K, cb: LiveEvents[K]): void;
}
export declare const live: LiveSocket;

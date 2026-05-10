export type UUID = string;
export type PlayerJSON = {
    id: UUID;
    name: string;
    role?: "batter" | "bowler" | "allrounder" | "keeper";
};
export type TeamJSON = {
    name: string;
    players: PlayerJSON[];
    playing_xi?: UUID[];
};
export type GameCore = {
    id: UUID;
    team_a: TeamJSON;
    team_b: TeamJSON;
    team_a_captain_id?: UUID | null;
    team_a_keeper_id?: UUID | null;
    team_b_captain_id?: UUID | null;
    team_b_keeper_id?: UUID | null;
    format?: "limited" | "multi_day" | "custom";
    status?: "created" | "ready" | "live" | "break" | "finished";
    created_at?: string;
    updated_at?: string;
};
export type PlayingXIRequest = {
    team_a: UUID[];
    team_b: UUID[];
    captain_a?: UUID | null;
    keeper_a?: UUID | null;
    captain_b?: UUID | null;
    keeper_b?: UUID | null;
};
export type ExtraType = "wide" | "no_ball" | "bye" | "leg_bye";
export type ExtrasPayload = {
    type: ExtraType;
    runs: number;
};
export type WicketType = "bowled" | "lbw" | "caught" | "run_out" | "stumped" | "hit_wicket" | "obstructing_the_field" | "retired_hurt";
export type WicketPayload = {
    type: WicketType;
    batter_out_id?: UUID;
    fielder_id?: UUID;
};
export type BallEventPayload = {
    game_id: UUID;
    innings_no: number;
    over_no: number;
    ball_no: number;
    striker_id: UUID;
    non_striker_id: UUID;
    bowler_id: UUID;
    runs: number;
    extras?: ExtrasPayload;
    wicket?: WicketPayload;
    commentary?: string;
    at: string;
};
export type UndoPayload = {
    game_id: UUID;
    reason?: "user_undo" | "sync" | "admin";
    at: string;
};
export type CommentaryPayload = {
    game_id: UUID;
    text: string;
    at: string;
};
export type SponsorImpression = {
    game_id: UUID;
    sponsor_id: string;
    at: string;
};
export type LiveEventNames = "live:connected" | "live:disconnected" | "game:created" | "game:updated" | "game:state" | "game:playing_xi:set" | "score:ball" | "score:undo" | "commentary:added" | "sponsor:impressions";
export type LiveEventsMap = {
    "live:connected": {
        sid: string;
        at: string;
    };
    "live:disconnected": {
        sid: string;
        at: string;
    };
    "game:created": {
        game: GameCore;
    };
    "game:updated": {
        game: GameCore;
    };
    "game:state": {
        game: GameCore;
    };
    "game:playing_xi:set": {
        game_id: UUID;
        team_a: UUID[];
        team_b: UUID[];
        captain_a?: UUID | null;
        keeper_a?: UUID | null;
        captain_b?: UUID | null;
        keeper_b?: UUID | null;
    };
    "score:ball": BallEventPayload;
    "score:undo": UndoPayload;
    "commentary:added": CommentaryPayload;
    "sponsor:impressions": SponsorImpression[];
};
/**
 * Narrow a Socket.IO client to your LiveEventsMap so `on/emit` are type-safe.
 *
 * Usage:
 *   import { io } from "socket.io-client";
 *   import { withLiveTypes } from "@/types/live";
 *
 *   const base = io(import.meta.env.VITE_WS_URL, { transports: ["websocket"] });
 *   const socket = withLiveTypes(base);
 *
 *   socket.on("game:updated", ({ game }) => { ... });
 *   socket.emit("game:playing_xi:set", { game_id, team_a, team_b, ... });
 */
export type TypedSocket = {
    on<E extends keyof LiveEventsMap>(event: E, handler: (payload: LiveEventsMap[E]) => void): TypedSocket;
    off<E extends keyof LiveEventsMap>(event: E, handler?: (payload: LiveEventsMap[E]) => void): TypedSocket;
    emit<E extends keyof LiveEventsMap>(event: E, payload: LiveEventsMap[E]): TypedSocket;
};
export declare function withLiveTypes(socket: {
    on: (ev: string, cb: (p: unknown) => void) => unknown;
    off: (ev: string, cb?: (p: unknown) => void) => unknown;
    emit: (ev: string, p?: unknown) => unknown;
}): TypedSocket;
export declare const isUUID: (s: string) => boolean;
export declare const assertXIShape: (p: PlayingXIRequest) => void;

// src/types/live.ts

// ---------- Basic/shared types ----------
export type UUID = string;

export type PlayerJSON = {
  id: UUID;
  name: string;
  role?: "batter" | "bowler" | "allrounder" | "keeper";
};

export type TeamJSON = {
  name: string;
  players: PlayerJSON[];
  // When XI is chosen we persist the UUIDs; matches backend JSON write
  playing_xi?: UUID[];
};

export type GameCore = {
  id: UUID;
  // Stored as JSON in DB; mirrors backend model fields you’re writing in the router
  team_a: TeamJSON;
  team_b: TeamJSON;

  // Role columns (nullable) you persist in the router
  team_a_captain_id?: UUID | null;
  team_a_keeper_id?: UUID | null;
  team_b_captain_id?: UUID | null;
  team_b_keeper_id?: UUID | null;

  // Optional live bits you may already track
  format?: "limited" | "multi_day" | "custom";
  status?: "created" | "ready" | "live" | "break" | "finished";
  created_at?: string; // ISO
  updated_at?: string; // ISO
};

// Mirrors your POST /games/:id/playing-xi request (snake_case)
export type PlayingXIRequest = {
  team_a: UUID[];
  team_b: UUID[];
  captain_a?: UUID | null;
  keeper_a?: UUID | null;
  captain_b?: UUID | null;
  keeper_b?: UUID | null;
};

// ---------- Scoring payloads (used in live events) ----------
export type ExtraType = "wide" | "no_ball" | "bye" | "leg_bye";

export type ExtrasPayload = {
  type: ExtraType;
  runs: number; // total runs attributed to the extra
};

export type WicketType =
  | "bowled"
  | "lbw"
  | "caught"
  | "run_out"
  | "stumped"
  | "hit_wicket"
  | "obstructing_the_field"
  | "retired_hurt"; // note: not a wicket in totals, but can be pushed as an event

export type WicketPayload = {
  type: WicketType;
  batter_out_id?: UUID; // not needed for retired_hurt
  fielder_id?: UUID; // caught/run_out helpers (optional)
};

export type BallEventPayload = {
  game_id: UUID;
  innings_no: number; // 1-based
  over_no: number;    // 1-based
  ball_no: number;    // legal ball count in the over (1..6) for limited overs
  striker_id: UUID;
  non_striker_id: UUID;
  bowler_id: UUID;
  runs: number; // batter runs for the delivery (0..6, etc.)
  extras?: ExtrasPayload;
  wicket?: WicketPayload;
  commentary?: string;
  at: string; // ISO instant from server
};

export type UndoPayload = {
  game_id: UUID;
  reason?: "user_undo" | "sync" | "admin";
  at: string; // ISO
};

// ---------- Commentary ----------
export type CommentaryPayload = {
  game_id: UUID;
  text: string;
  at: string; // ISO
};

// ---------- Sponsor impressions (optional live) ----------
export type SponsorImpression = {
  game_id: UUID;
  sponsor_id: string;
  at: string; // ISO
};

// ---------- Live event names ----------
// Keep names flat and explicit so they’re easy to grep in FE/BE.
// If your backend uses different strings, change them here once and your app stays typed everywhere.
export type LiveEventNames =
  // lifecycle
  | "live:connected"
  | "live:disconnected"

  // game CRUD / full snapshots
  | "game:created"
  | "game:updated"  // generic snapshot push
  | "game:state"    // same as updated; some apps push periodic state

  // team selection
  | "game:playing_xi:set"

  // scoring
  | "score:ball"     // one delivery recorded
  | "score:undo"     // undo the last ball (or last event)

  // commentary
  | "commentary:added"

  // sponsors (optional)
  | "sponsor:impressions";

// ---------- Event map (name -> payload) ----------
export type LiveEventsMap = {
  // lifecycle
  "live:connected": { sid: string; at: string };     // server can ack with socket id
  "live:disconnected": { sid: string; at: string };

  // game snapshots
  "game:created": { game: GameCore };
  "game:updated": { game: GameCore };
  "game:state": { game: GameCore };

  // team selection result (what the backend commits in your router)
  "game:playing_xi:set": {
    game_id: UUID;
    team_a: UUID[];
    team_b: UUID[];
    captain_a?: UUID | null;
    keeper_a?: UUID | null;
    captain_b?: UUID | null;
    keeper_b?: UUID | null;
  };

  // scoring
  "score:ball": BallEventPayload;
  "score:undo": UndoPayload;

  // commentary
  "commentary:added": CommentaryPayload;

  // sponsors
  "sponsor:impressions": SponsorImpression[];
};

// ---------- Typed socket helpers ----------
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
  on<E extends keyof LiveEventsMap>(
    event: E,
    handler: (payload: LiveEventsMap[E]) => void
  ): TypedSocket;
  off<E extends keyof LiveEventsMap>(
    event: E,
    handler?: (payload: LiveEventsMap[E]) => void
  ): TypedSocket;
  emit<E extends keyof LiveEventsMap>(
    event: E,
    payload: LiveEventsMap[E]
  ): TypedSocket;
};

export function withLiveTypes(socket: {
  on: (ev: string, cb: (p: unknown) => void) => unknown;
  off: (ev: string, cb?: (p: unknown) => void) => unknown;
  emit: (ev: string, p?: unknown) => unknown;
}): TypedSocket {
  return {
    on(event, handler) {
      socket.on(event as string, handler as (p: unknown) => void);
      return this;
    },
    off(event, handler) {
      socket.off(event as string, handler as (p: unknown) => void);
      return this;
    },
    emit(event, payload) {
      socket.emit(event as string, payload as unknown);
      return this;
    },
  };
}

// ---------- Guard utilities (optional lightweight checks) ----------
export const isUUID = (s: string): boolean =>
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    s
  );

export const assertXIShape = (p: PlayingXIRequest): void => {
  if (!Array.isArray(p.team_a) || !Array.isArray(p.team_b)) {
    throw new Error("team_a and team_b must be arrays");
  }
  if (![...p.team_a, ...p.team_b].every((x) => typeof x === "string" && isUUID(x))) {
    throw new Error("All XI player ids must be UUID strings");
  }
};

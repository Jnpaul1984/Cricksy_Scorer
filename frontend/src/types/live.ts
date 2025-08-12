// Lightweight types that mirror the live snapshot your FastAPI backend emits
// in main.py -> sio.emit("state:update", { id, snapshot })

export interface ScoreLite {
  runs: number;
  wickets: number;
  overs: number;
}

export interface BatterBrief {
  id: string | null;
  name: string;
  runs: number;
  balls: number;
  is_out: boolean;
}

export interface Snapshot {
  id: string; // game id
  status: string; // e.g., "in_progress", "innings_break", "completed"
  score: ScoreLite;
  batsmen: {
    striker: BatterBrief;
    non_striker: BatterBrief;
  };
  over: { completed: number; balls_this_over: number };
  // Be flexible here; schema can evolve
  last_delivery: Record<string, unknown> | null;
}

export interface StateUpdatePayload {
  id: string;        // game id
  snapshot: Snapshot;
}

// Server -> Client (what we listen for)
export interface ServerToClientEvents {
  hello: (data: { ok: boolean }) => void;
  "state:update": (data: StateUpdatePayload) => void;
}

// Client -> Server (what we could emit later; keep empty for now or add as needed)
export interface ClientToServerEvents {
  // "room:join"?: (data: { id: string }) => void;
  // "room:leave"?: (data: { id: string }) => void;
}

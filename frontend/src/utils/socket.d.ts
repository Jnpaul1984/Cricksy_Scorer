import type { Socket } from 'socket.io-client';
export declare const SOCKET_URL: string;
/** Common lightweight card/score shapes (kept loose to avoid tight coupling) */
type OversLike = string | number;
type UUID = string;
/** Server -> Client events */
export interface ServerToClientEvents {
    'presence:init': (payload: {
        game_id: string;
        members: Array<{
            sid: string;
            role: string;
            name: string;
        }>;
    }) => void;
    'presence:update': (payload: {
        game_id: string;
        joined?: Array<{
            sid: string;
            role: string;
            name: string;
        }>;
        left?: Array<{
            sid: string;
        }>;
    }) => void;
    /**
     * Full or partial state snapshot.
     * We keep it flexible but include gate flags explicitly so TS knows about them.
     */
    'state:update': (payload: {
        id: string;
        snapshot: {
            total_runs?: number;
            total_wickets?: number;
            overs_completed?: number;
            balls_this_over?: number;
            current_inning?: number;
            batting_team_name?: string;
            bowling_team_name?: string;
            status?: string;
            target?: number | null;
            batting_scorecard?: Record<string, any>;
            bowling_scorecard?: Record<string, any>;
            last_delivery?: Record<string, any> | null;
            current_bowler_id?: UUID | null;
            last_ball_bowler_id?: UUID | null;
            current_over_balls?: number;
            mid_over_change_used?: boolean;
            balls_bowled_total?: number;
            needs_new_batter?: boolean;
            needs_new_over?: boolean;
            [k: string]: any;
        };
    }) => void;
    /**
     * Slim score tick update (optional cards); server MAY also include gate flags.
     * Your store already normalizes this and optionally refetches the full snapshot.
     */
    'score:update': (payload: {
        game_id?: string;
        score?: {
            runs: number;
            wickets: number;
            overs: OversLike;
            innings_no?: number;
        };
        batting?: Array<{
            player_id: string;
            name: string;
            runs: number;
            balls?: number;
            fours?: number;
            sixes?: number;
            strike_rate?: number;
            is_striker?: boolean;
        }>;
        bowling?: Array<{
            player_id: string;
            name: string;
            overs?: OversLike;
            maidens?: number;
            runs: number;
            wickets: number;
            econ?: number;
        }>;
        needs_new_batter?: boolean;
        needs_new_over?: boolean;
        [k: string]: any;
    }) => void;
    'commentary:new': (payload: {
        game_id: string;
        text: string;
        at: string;
    }) => void;
}
/** Client -> Server events */
export interface ClientToServerEvents {
    join: (payload: {
        game_id: string;
    }) => void;
    leave?: (payload: {
        game_id: string;
    }) => void;
    ping?: (payload?: {
        t?: number;
    }) => void;
}
export declare function connectSocket(customAuth?: Record<string, unknown>): void;
export declare function disconnectSocket(): void;
export declare function joinGame(gameId: string): void;
/** Event helpers (typed) */
export declare function on<E extends keyof ServerToClientEvents>(event: E, handler: ServerToClientEvents[E]): void;
export declare function on(event: string, handler: (...args: unknown[]) => void): void;
export declare function off<E extends keyof ServerToClientEvents>(event: E, handler?: ServerToClientEvents[E]): void;
export declare function off(event: string, handler?: (...args: unknown[]) => void): void;
export declare function emit<E extends keyof ClientToServerEvents>(event: E, ...args: Parameters<NonNullable<ClientToServerEvents[E]>>): void;
export declare function isConnected(): boolean;
export declare function getSocket(): Socket<ServerToClientEvents, ClientToServerEvents>;
export type { ServerToClientEvents as S2CEvents, ClientToServerEvents as C2SEvents };

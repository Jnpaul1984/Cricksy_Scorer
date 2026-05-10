/**
 * Canonical Metrics Composable
 *
 * Single source of truth for all scoreboard-critical metrics.
 * Primary data source: Pinia gameStore.liveSnapshot (real-time Socket.IO)
 * Fallback: GET /games/{gameId} API call
 *
 * NON-NEGOTIABLE RULE:
 * All UI scoreboard values MUST use this composable.
 * No local CRR/RRR/balls_remaining calculations allowed.
 */
import { type Ref } from 'vue';
export interface ExtrasBreakdown {
    total: number;
    wides: number;
    noBalls: number;
    byes: number;
    legByes: number;
}
export interface CanonicalMetrics {
    score: number | null;
    wickets: number | null;
    overs: string;
    ballsRemaining: number | null;
    crr: number | null;
    rrr: number | null;
    extras: ExtrasBreakdown;
    updatedAt: Date | null;
    isStale: boolean;
}
export declare function useCanonicalMetrics(gameIdInput: Ref<string> | string): {
    score: any;
    wickets: any;
    overs: any;
    ballsRemaining: any;
    crr: any;
    rrr: any;
    extras: any;
    updatedAt: any;
    isStale: any;
    refresh: () => Promise<void>;
    isRefreshing: any;
    lastError: any;
};
/**
 * Helper to format CRR/RRR for display
 */
export declare function formatRunRate(rate: number | null, decimals?: number): string;
/**
 * Helper to format balls remaining as overs
 */
export declare function formatBallsAsOvers(balls: number | null): string;

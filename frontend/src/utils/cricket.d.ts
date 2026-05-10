/** Formats Strike Rate as a string with 1 decimal place. Returns '—' if balls = 0. */
export declare function fmtSR(runs: number, balls: number): string;
/** Convert number of balls to decimal overs (e.g., 22 balls -> 3.666…, not 3.4). */
export declare function ballsToOversFloat(balls: number): number;
export declare function oversNotationToFloat(ov: number | string | undefined): number;
export type Delivery = {
    bowler_id?: string | number;
    over_number?: number | string;
    ball_number?: number;
    extra?: 'wd' | 'nb' | 'b' | 'lb' | string | null;
    extra_runs?: number;
    runs_off_bat?: number;
    runs_scored?: number;
};
/** Formats Economy Rate as a string with 2 decimals. Returns '—' if ballsBowled = 0. */
export declare function fmtEconomy(runsConceded: number, ballsBowled: number): string;
/** Formats balls as the conventional overs display "O.R" (e.g., 3.4 means 3 overs + 4 balls). */
export declare function oversDisplayFromBalls(balls: number): string;
/** Formats overs from whichever field is available.
 *  Prefers integer balls (authoritative) if present, else derives from X.Y notation.
 *  Accepts either a number of balls, a legacy overs number/string, or a bowler-like object.
 */
export declare function oversDisplayFromAny(src: number | string | {
    balls_bowled?: number;
    overs_bowled?: number | string;
    overs?: number | string;
} | Record<string, any>): string;
/** True if this delivery should count as a legal ball (increments ball count). */
export declare function isLegalBall(d: {
    is_extra?: boolean;
    extra?: string;
    extra_type?: 'wd' | 'nb' | 'b' | 'lb' | string;
} | Record<string, any>): boolean;
export declare function ballsFromOversNotation(ov: number | string | undefined): number;
/** Sum bowling figures (runs to bowler & legal balls) for one bowler. */
export declare function accumulateBowling(deliveries: Array<Record<string, any>>, bowlerId: string): {
    runs: number;
    balls: number;
};
/** Derive full figures for a bowler from deliveries (runs/balls/maidens/overs/econ). */
export declare function deriveBowlerFigures(deliveries: Delivery[], bowlerId: string | number): {
    runs: number;
    balls: number;
    maidens: number;
    oversText: string;
    econText: string | '—';
};
declare const _default: {
    fmtSR: typeof fmtSR;
    ballsToOversFloat: typeof ballsToOversFloat;
    fmtEconomy: typeof fmtEconomy;
    oversDisplayFromBalls: typeof oversDisplayFromBalls;
    oversDisplayFromAny: typeof oversDisplayFromAny;
    isLegalBall: typeof isLegalBall;
    ballsFromOversNotation: typeof ballsFromOversNotation;
    accumulateBowling: typeof accumulateBowling;
    deriveBowlerFigures: typeof deriveBowlerFigures;
};
export default _default;

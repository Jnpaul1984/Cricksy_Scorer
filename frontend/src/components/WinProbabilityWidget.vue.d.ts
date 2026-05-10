export interface WinProbability {
    batting_team_win_prob: number;
    bowling_team_win_prob: number;
    confidence: number;
    batting_team?: string;
    bowling_team?: string;
    factors?: {
        runs_needed?: number;
        balls_remaining?: number;
        required_run_rate?: number;
        current_run_rate?: number;
        wickets_remaining?: number;
        projected_score?: number;
        par_score?: number;
    };
}
declare const __VLS_export: any;
declare const _default: typeof __VLS_export;
export default _default;

export interface PlayerCareerSummary {
    player_id: string;
    player_name: string;
    career_summary: string;
    batting_stats: {
        matches: number;
        total_runs: number;
        average: number;
        consistency_score: number;
        strike_rate: number;
        boundary_percentage: number;
        fours: number;
        sixes: number;
        best_score: number;
        worst_score: number;
        fifties: number;
        centuries: number;
        out_percentage: number;
        dismissal_rate: number;
    };
    bowling_stats: {
        matches: number;
        total_wickets: number;
        total_overs: number;
        runs_conceded: number;
        economy_rate: number;
        average_wickets_per_match: number;
        maiden_percentage: number;
        maidens: number;
    };
    specialization: string;
    specialization_confidence: number;
    recent_form: {
        recent_matches: number;
        recent_runs: number;
        recent_average: number;
        recent_strike_rate: number;
        recent_wickets: number;
        trend: 'improving' | 'declining' | 'stable';
        last_match_performance: string;
    };
    best_performances: {
        best_batting?: {
            runs: number;
            balls_faced: number;
            fours: number;
            sixes: number;
            date: string;
        };
        best_bowling?: {
            wickets: number;
            overs: number;
            runs_conceded: number;
            economy: number;
            date: string;
        };
    };
    career_highlights: string[];
}
declare const __VLS_export: any;
declare const _default: typeof __VLS_export;
export default _default;

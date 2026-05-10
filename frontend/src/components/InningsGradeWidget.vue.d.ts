export interface InningsGradeData {
    grade: 'A+' | 'A' | 'B' | 'C' | 'D';
    score_percentage: number;
    par_score: number;
    total_runs: number;
    run_rate: number;
    wickets_lost: number;
    wicket_efficiency: number;
    boundary_count: number;
    boundary_percentage: number;
    dot_ball_ratio: number;
    overs_played: number;
    grade_factors: {
        score_percentage_contribution: string;
        wicket_efficiency_contribution: string;
        strike_rotation_contribution: string;
        boundary_efficiency_contribution: string;
    };
}
declare const __VLS_export: any;
declare const _default: typeof __VLS_export;
export default _default;

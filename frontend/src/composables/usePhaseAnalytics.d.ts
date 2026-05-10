/**
 * usePhaseAnalytics Composable
 *
 * State management and API integration for match phase analysis.
 * Provides functions to fetch and manage phase data for interactive visualizations.
 */
export interface PhaseData {
    phase_name: string;
    phase_number: number;
    start_over: number;
    end_over: number;
    total_runs: number;
    total_wickets: number;
    total_deliveries: number;
    run_rate: number;
    expected_runs_in_phase: number;
    actual_vs_expected_pct: number;
    wicket_rate: number;
    boundary_count: number;
    dot_ball_count: number;
    aggressive_index: number;
    acceleration_rate: number;
}
export interface PhaseSummary {
    total_runs: number;
    total_wickets: number;
    overall_run_rate: number;
    overall_expected_runs: number;
    acceleration_trend: 'increasing' | 'decreasing' | 'stable';
}
export interface PhasePrediction {
    powerplay_actual?: number;
    powerplay_efficiency?: number;
    total_expected_runs?: number;
    win_probability?: number;
}
export interface PhasePerformance {
    [phaseName: string]: {
        actual_runs: number;
        expected_runs: number;
        performance_pct: number;
    };
}
export interface PhaseAnalysisData {
    game_id: string;
    inning_number: number;
    overs_limit: number;
    phases: PhaseData[];
    current_phase: string;
    phase_index: number;
    summary: PhaseSummary;
    predictions: PhasePrediction;
    phase_performance: PhasePerformance;
}
export interface PhasePredictionData {
    game_id: string;
    inning_number: number;
    phase_predictions: {
        [phaseName: string]: {
            actual_runs: number;
            expected_runs: number;
            efficiency: number;
            run_rate: number;
            wickets_lost: number;
            aggressive_index: number;
        };
    };
    match_prediction: {
        projected_total: number;
        confidence: number;
        win_probability?: number;
    };
}
export interface PhaseTrendsData {
    game_id: string;
    inning_number: number;
    trends: {
        run_rate_trend: number[];
        wicket_rate_trend: number[];
        acceleration: 'increasing' | 'decreasing' | 'stable';
        phase_comparison: {
            vs_powerplay: number[];
            vs_benchmark: number[];
        };
    };
}
export declare function usePhaseAnalytics(): {
    phaseData: any;
    predictions: any;
    trends: any;
    loading: any;
    error: any;
    currentPhase: any;
    phaseIndex: any;
    isChasing: any;
    fetchPhaseMap: (gameId: string, inningNum?: number) => Promise<void>;
    fetchPredictions: (gameId: string, inningNum?: number) => Promise<void>;
    fetchTrends: (gameId: string, inningNum?: number) => Promise<void>;
    fetchAllPhaseData: (gameId: string, inningNum?: number) => Promise<void>;
    getPhaseStats: (phaseName: string) => PhaseData | undefined;
    getPhaseEfficiency: (phaseName: string) => number;
    getPhaseRating: (phaseName: string) => "excellent" | "good" | "average" | "poor";
    getAccelerationPhase: () => string;
    clear: () => void;
    refresh: (gameId: string, inningNum?: number) => Promise<void>;
};

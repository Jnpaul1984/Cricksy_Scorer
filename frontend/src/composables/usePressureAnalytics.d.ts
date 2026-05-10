export interface PressurePoint {
    delivery_num: number;
    over_num: number;
    pressure_score: number;
    pressure_level: string;
    factors: Record<string, number>;
    rates: {
        required_run_rate: number;
        actual_run_rate: number;
    };
    cumulative_stats: {
        runs: number;
        wickets: number;
        dot_count: number;
        strike_rate: number;
        balls_remaining: number;
        overs_remaining: number;
    };
}
export interface PressureSummary {
    total_deliveries: number;
    average_pressure: number;
    peak_pressure: number;
    peak_pressure_at_delivery: number;
    critical_moments: number;
    high_pressure_count: number;
}
export interface PressurePhases {
    powerplay: PressurePoint[];
    middle: PressurePoint[];
    death: PressurePoint[];
    powerplay_stats?: Record<string, number>;
    middle_stats?: Record<string, number>;
    death_stats?: Record<string, number>;
}
export interface PressureData {
    pressure_points: PressurePoint[];
    summary: PressureSummary;
    peak_moments: PressurePoint[];
    phases: PressurePhases;
}
export declare const usePressureAnalytics: () => {
    pressureData: any;
    criticalMoments: any;
    phases: any;
    loading: any;
    error: any;
    fetchPressureMap: (gameId: string, inningNum?: number) => Promise<PressureData | null>;
    fetchCriticalMoments: (gameId: string, threshold?: number, inningNum?: number) => Promise<PressurePoint[]>;
    fetchPressurePhases: (gameId: string, inningNum?: number) => Promise<PressurePhases | null>;
    calculatePressureStats: (pressurePoints: PressurePoint[]) => {
        averagePressure: number;
        peakPressure: number;
        minPressure: number;
        highPressureCount: number;
        extremePressureCount: number;
    };
    getPressureLevel: (score: number) => string;
    getPressureLevelWithEmoji: (score: number) => string;
    refresh: (gameId: string, inningNum?: number) => Promise<void>;
    clear: () => void;
};

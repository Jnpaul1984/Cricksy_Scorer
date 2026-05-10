import type { Ref } from 'vue';
export interface ImprovementMetrics {
    metric_name: string;
    previous_value: number;
    current_value: number;
    absolute_change: number;
    percentage_change: number;
    trend: 'improving' | 'declining' | 'stable';
    confidence: number;
}
export interface PeriodComparison {
    from_month: string;
    to_month: string;
    metrics: Record<string, ImprovementMetrics>;
}
export interface LatestStats {
    batting_average: number;
    strike_rate: number;
    consistency_score: number;
    matches_played: number;
    innings_played: number;
    role: string;
}
export interface ImprovementSummaryData {
    status: 'success' | 'insufficient_data';
    overall_trend: 'improving' | 'declining' | 'stable' | 'accelerating';
    improvement_score: number;
    latest_month: string;
    months_analyzed: number;
    latest_stats: LatestStats;
    latest_improvements: Record<string, ImprovementMetrics>;
    historical_improvements: PeriodComparison[];
    highlights: string[];
}
export interface UsePlayerImprovement {
    summaryData: Ref<ImprovementSummaryData | null>;
    monthlyStatsData: Ref<any | null>;
    trendData: Ref<any | null>;
    loading: Ref<boolean>;
    error: Ref<string | null>;
    fetchImprovementSummary: (playerId: string, months?: number) => Promise<void>;
    fetchMonthlyStats: (playerId: string, limit?: number) => Promise<void>;
    fetchTrends: (playerId: string, months?: number) => Promise<void>;
    getTrendIndicator: (trend: string) => string;
    formatTrendValue: (value: number) => string;
    refetch: () => Promise<void>;
}
export declare const usePlayerImprovement: () => UsePlayerImprovement;

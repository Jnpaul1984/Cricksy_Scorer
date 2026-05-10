/**
 * usePlayerFormTracker.ts - Player form tracking and visualization
 *
 * Calculates player performance trends over recent matches
 * and determines form color/trend indicators.
 */
import type { PlayerProfile } from '@/types/player';
export type FormColor = 'good' | 'average' | 'poor';
export type FormTrend = 'improving' | 'stable' | 'declining';
export interface FormMatch {
    matchIndex: number;
    strikeRate: number;
    runs: number;
    performance: FormColor;
}
export interface FormData {
    matches: FormMatch[];
    overallTrend: FormTrend;
    averagePerformance: FormColor;
    recentForm: FormColor;
}
export declare function usePlayerFormTracker(profile: Readonly<{
    value: PlayerProfile | null;
}>): {
    formData: any;
    colorMap: any;
    trendEmoji: any;
    getFormClass: (color: FormColor) => string;
    getFormLabel: (color: FormColor) => string;
    getTrendLabel: (trend: FormTrend) => string;
};

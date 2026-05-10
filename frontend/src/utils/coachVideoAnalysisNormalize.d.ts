import type { VideoAnalysisJob } from '@/services/coachPlusVideoService';
type AnalysisJob = VideoAnalysisJob;
export type CoachFriendlyMetricBand = 'Needs work' | 'Improving' | 'Strong';
export type CoachFriendlyMetric = {
    key: string;
    label: string;
    value: number | null;
    band: CoachFriendlyMetricBand | null;
};
export type CoachFriendlyFinding = {
    title: string;
    whyItMatters: string;
    whatToFix: string;
    drillSuggestions: string[];
};
export type CoachFriendlyNumbers = {
    totalFrames: number | null;
    sampledFrames: number | null;
    detectionRate: number | null;
    fps: number | null;
    width: number | null;
    height: number | null;
};
export type CoachFriendlyAnalysis = {
    status: string;
    isTerminal: boolean;
    hasResults: boolean;
    sessionId: string | null;
    jobId: string | null;
    errorMessage: string | null;
    coachSummary: {
        overallLevel: CoachFriendlyMetricBand | '—';
        takeaways: string[];
    };
    nextWork: CoachFriendlyFinding[];
    numbers: CoachFriendlyNumbers;
    metrics: CoachFriendlyMetric[];
    progress: {
        show: boolean;
        steps: string[];
    };
};
export declare function normalizeCoachVideoAnalysis(job: AnalysisJob | null | undefined): CoachFriendlyAnalysis;
export {};

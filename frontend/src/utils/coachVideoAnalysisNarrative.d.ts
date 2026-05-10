import type { VideoAnalysisJob } from '@/services/coachPlusVideoService';
export type CoachNarrativeRating = 'Needs Improvement' | 'Solid' | 'High Risk';
export type CoachNarrativeSeverity = 'low' | 'medium' | 'high';
export type CoachNarrative = {
    summary: {
        rating: CoachNarrativeRating;
        confidenceText: string;
        coverageText: string;
        coachSummaryText: string;
    };
    priorities: Array<{
        key: string;
        title: string;
        severity: CoachNarrativeSeverity;
        explanation: string;
        impact: string;
        drills: string[];
        evidence?: {
            threshold?: number;
            worstFrames: Array<{
                frameNum: number;
                timeSeconds?: number;
                score?: number;
            }>;
            badSegments: Array<{
                startFrame: number;
                endFrame: number;
                startSeconds?: number;
                endSeconds?: number;
                minScore?: number;
            }>;
        };
    }>;
    metrics: {
        framesAnalyzed?: number;
        totalFrames?: number;
        detectionRate?: number;
    };
};
export declare function buildCoachNarrative(analysisJob: VideoAnalysisJob | null | undefined): CoachNarrative;

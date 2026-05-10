export interface ApiErrorResponse {
    detail: string;
    status?: number;
    code?: string;
}
export declare class ApiError extends Error {
    status: number;
    detail?: string | undefined;
    code?: string | undefined;
    constructor(message: string, status?: number, detail?: string | undefined, code?: string | undefined);
    isFeatureDisabled(): boolean;
    isUnauthorized(): boolean;
}
export interface VideoSession {
    id: string;
    owner_type: string;
    owner_id: string;
    title: string;
    player_ids: string[];
    status: string;
    notes: string | null;
    analysis_context: string | null;
    camera_view: string | null;
    s3_bucket: string | null;
    s3_key: string | null;
    created_at: string;
    updated_at: string;
}
export interface VideoAnalysisJob {
    id: string;
    session_id: string;
    sample_fps: number;
    include_frames: boolean;
    status: string;
    error_message: string | null;
    sqs_message_id: string | null;
    results: VideoAnalysisResults | null;
    analysis_context?: string | null;
    camera_view?: string | null;
    stage?: string | null;
    progress_pct?: number | null;
    deep_enabled?: boolean | null;
    quick_results?: VideoAnalysisResults | null;
    deep_results?: VideoAnalysisResults | null;
    pdf_s3_key?: string | null;
    pdf_generated_at?: string | null;
    coach_goals?: any | null;
    outcomes?: any | null;
    goal_compliance_pct?: number | null;
    coach_suggestions?: any | null;
    player_summary?: any | null;
    video_stream?: VideoStreamUrl | null;
    created_at: string;
    started_at: string | null;
    completed_at: string | null;
    updated_at: string;
}
export interface VideoStreamUrl {
    video_url: string;
    expires_in: number;
    bucket: string;
    key: string;
}
export interface VideoAnalysisResults {
    evidence?: Record<string, {
        threshold?: number;
        worst_frames?: Array<{
            frame_num?: number;
            timestamp_s?: number;
            score?: number;
        }>;
        bad_segments?: Array<{
            start_frame?: number;
            end_frame?: number;
            start_timestamp_s?: number;
            end_timestamp_s?: number;
            min_score?: number;
        }>;
    }>;
    video_fps?: number;
    total_frames?: number;
    pose_summary?: {
        total_frames?: number;
        sampled_frames?: number;
        frames_with_pose?: number;
        detection_rate_percent?: number;
        model?: string;
        video_fps?: number;
    };
    pose?: {
        total_frames?: number;
        sampled_frames?: number;
        detected_frames?: number;
        detection_rate?: number;
        video_fps?: number;
        video_width?: number;
        video_height?: number;
        pose_summary?: {
            frame_count?: number;
        };
    };
    metrics?: {
        summary?: {
            total_frames?: number;
        };
        [k: string]: unknown;
    };
    findings?: Record<string, unknown> | Array<unknown> | null;
    coach?: {
        findings?: Record<string, unknown> | Array<unknown> | null;
        report?: unknown;
    };
    report?: {
        summary?: string;
        key_issues?: string[];
        drills?: {
            name?: string;
            description?: string;
            duration_minutes?: number;
            focus_areas?: string[];
        }[];
        one_week_plan?: string;
    };
    frames?: Array<Record<string, unknown>>;
}
export interface UploadInitiateResponse {
    job_id: string;
    session_id: string;
    presigned_url: string;
    expires_in: number;
    s3_bucket: string;
    s3_key: string;
}
export interface UploadCompleteResponse {
    job_id: string;
    status: string;
    sqs_message_id: string | null;
    message: string;
}
/**
 * Create a new video session for a coach
 */
export declare function createVideoSession(data: {
    title: string;
    player_ids?: string[];
    notes?: string | null;
    analysis_context?: string | null;
    camera_view?: string | null;
}): Promise<VideoSession>;
/**
 * List video sessions for current coach (paginated)
 */
export declare function listVideoSessions(limit?: number, offset?: number, options?: {
    statusFilter?: string;
    excludeFailed?: boolean;
}): Promise<VideoSession[]>;
/**
 * Get a specific video session
 */
export declare function getVideoSession(sessionId: string): Promise<VideoSession>;
/**
 * Delete a video session
 */
export declare function deleteVideoSession(sessionId: string): Promise<void>;
/**
 * Bulk delete old/failed sessions
 */
export declare function bulkDeleteSessions(options?: {
    statusFilter?: string;
    olderThanDays?: number;
}): Promise<{
    deleted_count: number;
    s3_files_deleted: number;
    filters_applied: any;
}>;
/**
 * Re-analyze an existing video session (create new analysis job)
 * Useful for testing different analysis modes or retrying failed analyses
 */
export declare function reanalyzeSession(sessionId: string, options?: {
    analysisMode?: 'batting' | 'bowling' | 'wicketkeeping' | 'fielding';
    sampleFps?: number;
    includeFrames?: boolean;
}): Promise<VideoAnalysisJob>;
/**
 * Initiate a video upload: creates analysis job and returns presigned S3 URL
 */
export declare function initiateVideoUpload(sessionId: string, sampleFps?: number, includeFrames?: boolean, analysisMode?: string | null): Promise<UploadInitiateResponse>;
/**
 * Upload file to presigned S3 URL
 * Yields progress events during upload
 */
export declare function uploadToPresignedUrl(presignedUrl: string, file: File, onProgress?: (percent: number) => void): Promise<void>;
/**
 * Complete a video upload: marks job as processing and queues to SQS
 */
export declare function completeVideoUpload(jobId: string): Promise<UploadCompleteResponse>;
/**
 * Get analysis job status (poll this for progress)
 */
export declare function getAnalysisJobStatus(jobId: string): Promise<VideoAnalysisJob>;
/**
 * List analysis jobs for a session
 */
export declare function listAnalysisJobs(sessionId: string): Promise<VideoAnalysisJob[]>;
/**
 * Get analysis history for a video session (ordered by created_at desc)
 */
export declare function getAnalysisHistory(sessionId: string): Promise<VideoAnalysisJob[]>;
/**
 * Get a short-lived presigned GET URL for the uploaded session video.
 */
export declare function getVideoStreamUrl(sessionId: string): Promise<VideoStreamUrl>;
/**
 * Export analysis results as PDF
 */
export interface PdfExportResponse {
    job_id: string;
    pdf_url: string;
    expires_in: number;
    pdf_s3_key: string;
    pdf_size_bytes: number;
}
export declare function exportAnalysisPdf(jobId: string): Promise<PdfExportResponse>;
/**
 * Set coach-defined goals for an analysis job
 */
export interface SetGoalsRequest {
    zones: Array<{
        zone_id: string;
        target_accuracy: number;
    }>;
    metrics: Array<{
        code: string;
        target_score: number;
    }>;
}
export declare function setJobGoals(jobId: string, goals: SetGoalsRequest): Promise<any>;
/**
 * Calculate compliance of analysis results against goals
 */
export interface OutcomesResponse {
    zones: Array<{
        zone_id: string;
        zone_name: string;
        target_accuracy: number;
        actual_accuracy: number;
        pass: boolean;
        delta: number;
    }>;
    metrics: Array<{
        code: string;
        title: string;
        target_score: number;
        actual_score: number;
        pass: boolean;
        delta: number;
    }>;
    overall_compliance_pct: number;
}
export declare function calculateCompliance(jobId: string): Promise<OutcomesResponse>;
/**
 * Get calculated outcomes for a job
 */
export declare function getJobOutcomes(jobId: string): Promise<OutcomesResponse>;
/**
 * Compare multiple analysis jobs within a session
 */
export interface CompareJobsRequest {
    job_ids: string[];
}
export interface CompareJobsResponse {
    timeline: Array<{
        timestamp: string | null;
        job_id: string;
        analysis_mode: string | null;
        metric_scores: Record<string, number>;
    }>;
    deltas: Array<{
        from_job_id: string;
        to_job_id: string;
        improvements: Array<{
            code: string;
            from_score: number;
            to_score: number;
            delta: number;
        }>;
        regressions: Array<{
            code: string;
            from_score: number;
            to_score: number;
            delta: number;
        }>;
    }>;
    persistent_issues: Array<{
        code: string;
        title: string;
        avg_score: number;
        trend: 'declining' | 'stable' | 'improving';
        occurrences: number;
    }>;
}
export declare function compareJobs(sessionId: string, jobIds: string[]): Promise<CompareJobsResponse>;
/**
 * Coaching suggestions response
 */
export interface CoachSuggestionsResponse {
    primary_focus: {
        code: string;
        title: string;
        severity: string;
        rationale: string;
    };
    secondary_focus: {
        code: string;
        title: string;
        severity: string;
        rationale: string;
    } | null;
    coaching_cues: string[];
    drills: Array<{
        name: string;
        description: string;
        equipment: string;
        focus: string;
    }>;
    proposed_next_goal: {
        zones: Array<{
            zone_id: string;
            zone_name: string;
            target_accuracy: number;
        }>;
        metrics: Array<{
            code: string;
            target_score: number;
        }>;
    };
    rationale: string;
}
/**
 * Player summary response
 */
export interface PlayerSummaryResponse {
    focus_area: string;
    key_points: string[];
    encouragement: string;
    next_steps: string;
}
/**
 * Generate coaching suggestions for a job
 */
export declare function generateCoachSuggestions(jobId: string): Promise<CoachSuggestionsResponse>;
/**
 * Get coaching suggestions for a job
 */
export declare function getCoachSuggestions(jobId: string): Promise<{
    coach_suggestions: CoachSuggestionsResponse;
    player_summary: PlayerSummaryResponse;
}>;

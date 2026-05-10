/**
 * Enums (immutable - additive changes only)
 */
export declare enum VideoSessionType {
    Batting = "batting",
    Bowling = "bowling",
    Fielding = "fielding",
    Wicketkeeping = "wicketkeeping"
}
export declare enum VideoSessionStatus {
    Pending = "pending",
    Uploaded = "uploaded",
    Processing = "processing",
    Ready = "ready",
    Failed = "failed"
}
export declare enum CoachNoteSeverity {
    Info = "info",
    Improvement = "improvement",
    Critical = "critical"
}
export declare enum VideoMomentType {
    Setup = "setup",
    Catch = "catch",
    Throw = "throw",
    Dive = "dive",
    Stumping = "stumping",
    Other = "other"
}
export declare enum PlayerRole {
    Batter = "batter",
    Bowler = "bowler",
    Wicketkeeper = "wicketkeeper",
    Fielder = "fielder"
}
export declare enum SkillFocus {
    BattingStance = "batting_stance",
    Footwork = "footwork",
    BowlingAction = "bowling_action",
    WicketkeepingStance = "wicketkeeping_stance",
    Catching = "catching",
    Throwing = "throwing"
}
/**
 * Video Sessions
 */
export interface VideoSessionCreate {
    title: string;
    player_ids: string[];
    notes?: string | null;
    session_type?: VideoSessionType | null;
    min_duration_seconds?: number;
}
export interface VideoSessionRead {
    id: string;
    owner_type: 'coach' | 'org';
    owner_id: string;
    title: string;
    player_ids: string[];
    status: VideoSessionStatus;
    notes: string | null;
    session_type: VideoSessionType | null;
    min_duration_seconds: number;
    s3_bucket: string | null;
    s3_key: string | null;
    file_size_bytes: number | null;
    created_at: string;
    updated_at: string;
}
export interface VideoUploadUrlResponse {
    upload_url: string;
    fields: Record<string, string>;
    expires_in: number;
    max_size_bytes: number;
}
/**
 * Coach Notes
 */
export interface CoachNoteCreate {
    player_id: number;
    note_text: string;
    severity?: CoachNoteSeverity;
    tags?: string[] | null;
    video_session_id?: string | null;
    moment_marker_id?: string | null;
}
export interface CoachNoteUpdate {
    note_text?: string | null;
    tags?: string[] | null;
    severity?: CoachNoteSeverity;
}
export interface CoachNoteRead {
    id: string;
    coach_id: string;
    player_id: number;
    player_name: string | null;
    video_session_id: string | null;
    video_session_title: string | null;
    moment_marker_id: string | null;
    note_text: string;
    tags: string[] | null;
    severity: CoachNoteSeverity;
    created_at: string;
    updated_at: string;
}
/**
 * Video Moment Markers
 */
export interface VideoMomentMarkerCreate {
    timestamp_ms: number;
    moment_type: VideoMomentType;
    description?: string | null;
}
export interface VideoMomentMarkerUpdate {
    timestamp_ms?: number;
    moment_type?: VideoMomentType;
    description?: string | null;
}
export interface VideoMomentMarkerRead {
    id: string;
    video_session_id: string;
    timestamp_ms: number;
    moment_type: VideoMomentType;
    description: string | null;
    created_by: string;
    created_at: string;
}
/**
 * Corrective Guidance
 */
export interface CorrectiveGuidanceRequest {
    player_role: PlayerRole;
    skill_focus: SkillFocus;
    observed_issue: string;
}
export interface Checkpoint {
    checkpoint: string;
    description: string;
}
export interface Drill {
    drill: string;
    description: string;
}
export interface CorrectiveGuidanceResponse {
    skill_focus: string;
    checkpoints: Checkpoint[];
    drills: Drill[];
    ai_explanation: string | null;
}
/**
 * Error Responses
 */
export interface ApiError {
    detail: string | object;
    status?: number;
    code?: string;
}
export declare enum ErrorCode {
    Unauthenticated = "401_UNAUTHENTICATED",
    Unauthorized = "403_UNAUTHORIZED",
    FeatureDisabled = "403_FEATURE_DISABLED",
    NotFound = "404_NOT_FOUND",
    QuotaExceeded = "413_QUOTA_EXCEEDED",
    ValidationError = "422_VALIDATION_ERROR"
}
/**
 * Query Parameters
 */
export interface VideoSessionListParams {
    offset?: number;
    limit?: number;
}
export interface CoachNoteListParams {
    severity?: CoachNoteSeverity;
    video_session_id?: string;
    offset?: number;
    limit?: number;
}
export interface VideoMomentMarkerListParams {
    moment_type?: VideoMomentType;
}
/**
 * Type Guards
 */
export declare function isVideoSessionType(value: string): value is VideoSessionType;
export declare function isVideoSessionStatus(value: string): value is VideoSessionStatus;
export declare function isCoachNoteSeverity(value: string): value is CoachNoteSeverity;
export declare function isVideoMomentType(value: string): value is VideoMomentType;
export declare function isPlayerRole(value: string): value is PlayerRole;
export declare function isSkillFocus(value: string): value is SkillFocus;
/**
 * Response Validators
 */
export declare function validateVideoSessionRead(data: unknown): VideoSessionRead;
export declare function validateCoachNoteRead(data: unknown): CoachNoteRead;
export declare function validateVideoMomentMarkerRead(data: unknown): VideoMomentMarkerRead;

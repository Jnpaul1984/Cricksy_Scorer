// frontend/src/types/coaching.ts
// TypeScript types for Coach Notes, Video Sessions, and Video Moment Markers
// CONTRACT VERSION: 1.0.0
// LOCKED: Do not modify without updating COACHING_CONTRACT.md

/**
 * Enums (immutable - additive changes only)
 */

export enum VideoSessionType {
  Batting = 'batting',
  Bowling = 'bowling',
  Fielding = 'fielding',
  Wicketkeeping = 'wicketkeeping',
}

export enum VideoSessionStatus {
  Pending = 'pending',
  Uploaded = 'uploaded',
  Processing = 'processing',
  Ready = 'ready',
  Failed = 'failed',
}

export enum CoachNoteSeverity {
  Info = 'info',
  Improvement = 'improvement',
  Critical = 'critical',
}

export enum VideoMomentType {
  Setup = 'setup',
  Catch = 'catch',
  Throw = 'throw',
  Dive = 'dive',
  Stumping = 'stumping',
  Other = 'other',
}

export enum PlayerRole {
  Batter = 'batter',
  Bowler = 'bowler',
  Wicketkeeper = 'wicketkeeper',
  Fielder = 'fielder',
}

export enum SkillFocus {
  BattingStance = 'batting_stance',
  Footwork = 'footwork',
  BowlingAction = 'bowling_action',
  WicketkeepingStance = 'wicketkeeping_stance',
  Catching = 'catching',
  Throwing = 'throwing',
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
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
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
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
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
  created_at: string; // ISO 8601
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

export enum ErrorCode {
  Unauthenticated = '401_UNAUTHENTICATED',
  Unauthorized = '403_UNAUTHORIZED',
  FeatureDisabled = '403_FEATURE_DISABLED',
  NotFound = '404_NOT_FOUND',
  QuotaExceeded = '413_QUOTA_EXCEEDED',
  ValidationError = '422_VALIDATION_ERROR',
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

export function isVideoSessionType(value: string): value is VideoSessionType {
  return Object.values(VideoSessionType).includes(value as VideoSessionType);
}

export function isVideoSessionStatus(value: string): value is VideoSessionStatus {
  return Object.values(VideoSessionStatus).includes(value as VideoSessionStatus);
}

export function isCoachNoteSeverity(value: string): value is CoachNoteSeverity {
  return Object.values(CoachNoteSeverity).includes(value as CoachNoteSeverity);
}

export function isVideoMomentType(value: string): value is VideoMomentType {
  return Object.values(VideoMomentType).includes(value as VideoMomentType);
}

export function isPlayerRole(value: string): value is PlayerRole {
  return Object.values(PlayerRole).includes(value as PlayerRole);
}

export function isSkillFocus(value: string): value is SkillFocus {
  return Object.values(SkillFocus).includes(value as SkillFocus);
}

/**
 * Response Validators
 */

export function validateVideoSessionRead(data: unknown): VideoSessionRead {
  if (typeof data !== 'object' || data === null) {
    throw new Error('Invalid VideoSessionRead: not an object');
  }

  const session = data as Partial<VideoSessionRead>;

  if (typeof session.id !== 'string') throw new Error('Missing or invalid id');
  if (session.owner_type !== 'coach' && session.owner_type !== 'org') {
    throw new Error('Invalid owner_type');
  }
  if (typeof session.owner_id !== 'string') throw new Error('Invalid owner_id');
  if (typeof session.title !== 'string') throw new Error('Invalid title');
  if (!Array.isArray(session.player_ids)) throw new Error('Invalid player_ids');
  if (!isVideoSessionStatus(session.status || '')) throw new Error('Invalid status');
  if (typeof session.min_duration_seconds !== 'number') {
    throw new Error('Invalid min_duration_seconds');
  }
  if (typeof session.created_at !== 'string') throw new Error('Invalid created_at');
  if (typeof session.updated_at !== 'string') throw new Error('Invalid updated_at');

  return session as VideoSessionRead;
}

export function validateCoachNoteRead(data: unknown): CoachNoteRead {
  if (typeof data !== 'object' || data === null) {
    throw new Error('Invalid CoachNoteRead: not an object');
  }

  const note = data as Partial<CoachNoteRead>;

  if (typeof note.id !== 'string') throw new Error('Missing or invalid id');
  if (typeof note.coach_id !== 'string') throw new Error('Invalid coach_id');
  if (typeof note.player_id !== 'number') throw new Error('Invalid player_id');
  if (typeof note.note_text !== 'string') throw new Error('Invalid note_text');
  if (!isCoachNoteSeverity(note.severity || '')) throw new Error('Invalid severity');
  if (typeof note.created_at !== 'string') throw new Error('Invalid created_at');
  if (typeof note.updated_at !== 'string') throw new Error('Invalid updated_at');

  return note as CoachNoteRead;
}

export function validateVideoMomentMarkerRead(data: unknown): VideoMomentMarkerRead {
  if (typeof data !== 'object' || data === null) {
    throw new Error('Invalid VideoMomentMarkerRead: not an object');
  }

  const marker = data as Partial<VideoMomentMarkerRead>;

  if (typeof marker.id !== 'string') throw new Error('Missing or invalid id');
  if (typeof marker.video_session_id !== 'string') throw new Error('Invalid video_session_id');
  if (typeof marker.timestamp_ms !== 'number') throw new Error('Invalid timestamp_ms');
  if (!isVideoMomentType(marker.moment_type || '')) throw new Error('Invalid moment_type');
  if (typeof marker.created_by !== 'string') throw new Error('Invalid created_by');
  if (typeof marker.created_at !== 'string') throw new Error('Invalid created_at');

  return marker as VideoMomentMarkerRead;
}

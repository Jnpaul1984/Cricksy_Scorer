// frontend/src/types/coaching.ts
// TypeScript types for Coach Notes, Video Sessions, and Video Moment Markers
// CONTRACT VERSION: 1.0.0
// LOCKED: Do not modify without updating COACHING_CONTRACT.md
/**
 * Enums (immutable - additive changes only)
 */
export var VideoSessionType;
(function (VideoSessionType) {
    VideoSessionType["Batting"] = "batting";
    VideoSessionType["Bowling"] = "bowling";
    VideoSessionType["Fielding"] = "fielding";
    VideoSessionType["Wicketkeeping"] = "wicketkeeping";
})(VideoSessionType || (VideoSessionType = {}));
export var VideoSessionStatus;
(function (VideoSessionStatus) {
    VideoSessionStatus["Pending"] = "pending";
    VideoSessionStatus["Uploaded"] = "uploaded";
    VideoSessionStatus["Processing"] = "processing";
    VideoSessionStatus["Ready"] = "ready";
    VideoSessionStatus["Failed"] = "failed";
})(VideoSessionStatus || (VideoSessionStatus = {}));
export var CoachNoteSeverity;
(function (CoachNoteSeverity) {
    CoachNoteSeverity["Info"] = "info";
    CoachNoteSeverity["Improvement"] = "improvement";
    CoachNoteSeverity["Critical"] = "critical";
})(CoachNoteSeverity || (CoachNoteSeverity = {}));
export var VideoMomentType;
(function (VideoMomentType) {
    VideoMomentType["Setup"] = "setup";
    VideoMomentType["Catch"] = "catch";
    VideoMomentType["Throw"] = "throw";
    VideoMomentType["Dive"] = "dive";
    VideoMomentType["Stumping"] = "stumping";
    VideoMomentType["Other"] = "other";
})(VideoMomentType || (VideoMomentType = {}));
export var PlayerRole;
(function (PlayerRole) {
    PlayerRole["Batter"] = "batter";
    PlayerRole["Bowler"] = "bowler";
    PlayerRole["Wicketkeeper"] = "wicketkeeper";
    PlayerRole["Fielder"] = "fielder";
})(PlayerRole || (PlayerRole = {}));
export var SkillFocus;
(function (SkillFocus) {
    SkillFocus["BattingStance"] = "batting_stance";
    SkillFocus["Footwork"] = "footwork";
    SkillFocus["BowlingAction"] = "bowling_action";
    SkillFocus["WicketkeepingStance"] = "wicketkeeping_stance";
    SkillFocus["Catching"] = "catching";
    SkillFocus["Throwing"] = "throwing";
})(SkillFocus || (SkillFocus = {}));
export var ErrorCode;
(function (ErrorCode) {
    ErrorCode["Unauthenticated"] = "401_UNAUTHENTICATED";
    ErrorCode["Unauthorized"] = "403_UNAUTHORIZED";
    ErrorCode["FeatureDisabled"] = "403_FEATURE_DISABLED";
    ErrorCode["NotFound"] = "404_NOT_FOUND";
    ErrorCode["QuotaExceeded"] = "413_QUOTA_EXCEEDED";
    ErrorCode["ValidationError"] = "422_VALIDATION_ERROR";
})(ErrorCode || (ErrorCode = {}));
/**
 * Type Guards
 */
export function isVideoSessionType(value) {
    return Object.values(VideoSessionType).includes(value);
}
export function isVideoSessionStatus(value) {
    return Object.values(VideoSessionStatus).includes(value);
}
export function isCoachNoteSeverity(value) {
    return Object.values(CoachNoteSeverity).includes(value);
}
export function isVideoMomentType(value) {
    return Object.values(VideoMomentType).includes(value);
}
export function isPlayerRole(value) {
    return Object.values(PlayerRole).includes(value);
}
export function isSkillFocus(value) {
    return Object.values(SkillFocus).includes(value);
}
/**
 * Response Validators
 */
export function validateVideoSessionRead(data) {
    if (typeof data !== 'object' || data === null) {
        throw new Error('Invalid VideoSessionRead: not an object');
    }
    const session = data;
    if (typeof session.id !== 'string')
        throw new Error('Missing or invalid id');
    if (session.owner_type !== 'coach' && session.owner_type !== 'org') {
        throw new Error('Invalid owner_type');
    }
    if (typeof session.owner_id !== 'string')
        throw new Error('Invalid owner_id');
    if (typeof session.title !== 'string')
        throw new Error('Invalid title');
    if (!Array.isArray(session.player_ids))
        throw new Error('Invalid player_ids');
    if (!isVideoSessionStatus(session.status || ''))
        throw new Error('Invalid status');
    if (typeof session.min_duration_seconds !== 'number') {
        throw new Error('Invalid min_duration_seconds');
    }
    if (typeof session.created_at !== 'string')
        throw new Error('Invalid created_at');
    if (typeof session.updated_at !== 'string')
        throw new Error('Invalid updated_at');
    return session;
}
export function validateCoachNoteRead(data) {
    if (typeof data !== 'object' || data === null) {
        throw new Error('Invalid CoachNoteRead: not an object');
    }
    const note = data;
    if (typeof note.id !== 'string')
        throw new Error('Missing or invalid id');
    if (typeof note.coach_id !== 'string')
        throw new Error('Invalid coach_id');
    if (typeof note.player_id !== 'number')
        throw new Error('Invalid player_id');
    if (typeof note.note_text !== 'string')
        throw new Error('Invalid note_text');
    if (!isCoachNoteSeverity(note.severity || ''))
        throw new Error('Invalid severity');
    if (typeof note.created_at !== 'string')
        throw new Error('Invalid created_at');
    if (typeof note.updated_at !== 'string')
        throw new Error('Invalid updated_at');
    return note;
}
export function validateVideoMomentMarkerRead(data) {
    if (typeof data !== 'object' || data === null) {
        throw new Error('Invalid VideoMomentMarkerRead: not an object');
    }
    const marker = data;
    if (typeof marker.id !== 'string')
        throw new Error('Missing or invalid id');
    if (typeof marker.video_session_id !== 'string')
        throw new Error('Invalid video_session_id');
    if (typeof marker.timestamp_ms !== 'number')
        throw new Error('Invalid timestamp_ms');
    if (!isVideoMomentType(marker.moment_type || ''))
        throw new Error('Invalid moment_type');
    if (typeof marker.created_by !== 'string')
        throw new Error('Invalid created_by');
    if (typeof marker.created_at !== 'string')
        throw new Error('Invalid created_at');
    return marker;
}

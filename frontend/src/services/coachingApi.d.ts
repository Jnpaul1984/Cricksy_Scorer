import type { CoachNoteCreate, CoachNoteListParams, CoachNoteRead, CoachNoteUpdate, CorrectiveGuidanceRequest, CorrectiveGuidanceResponse, VideoMomentMarkerCreate, VideoMomentMarkerListParams, VideoMomentMarkerRead, VideoMomentMarkerUpdate } from '../types/coaching';
export declare class CoachingApiError extends Error {
    status: number;
    code?: string | undefined;
    constructor(message: string, status?: number, code?: string | undefined);
    isUnauthenticated(): boolean;
    isUnauthorized(): boolean;
    isFeatureDisabled(): boolean;
    isNotFound(): boolean;
    isValidationError(): boolean;
    isQuotaExceeded(): boolean;
}
/**
 * Coach Notes API
 */
export declare function createCoachNote(playerId: number, noteData: CoachNoteCreate): Promise<CoachNoteRead>;
export declare function listPlayerNotes(playerId: number, params?: CoachNoteListParams): Promise<CoachNoteRead[]>;
export declare function getCoachNote(noteId: string): Promise<CoachNoteRead>;
export declare function updateCoachNote(noteId: string, noteData: CoachNoteUpdate): Promise<CoachNoteRead>;
export declare function deleteCoachNote(noteId: string): Promise<void>;
export declare function getCorrectiveGuidance(request: CorrectiveGuidanceRequest): Promise<CorrectiveGuidanceResponse>;
/**
 * Video Moment Markers API
 */
export declare function createMomentMarker(sessionId: string, markerData: VideoMomentMarkerCreate): Promise<VideoMomentMarkerRead>;
export declare function listSessionMarkers(sessionId: string, params?: VideoMomentMarkerListParams): Promise<VideoMomentMarkerRead[]>;
export declare function updateMomentMarker(markerId: string, markerData: VideoMomentMarkerUpdate): Promise<VideoMomentMarkerRead>;
export declare function deleteMomentMarker(markerId: string): Promise<void>;
/**
 * Helper Functions
 */
export declare function formatTimestamp(timestampMs: number): string;
export declare function parseTimestamp(timeString: string): number;

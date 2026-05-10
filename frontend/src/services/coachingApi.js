// frontend/src/services/coachingApi.ts
// API client for Coach Notes and Video Moment Markers
// Complements existing coachPlusVideoService.ts
import { validateCoachNoteRead, validateVideoMomentMarkerRead, } from '../types/coaching';
import { API_BASE, getStoredToken } from './api';
export class CoachingApiError extends Error {
    status;
    code;
    constructor(message, status = 500, code) {
        super(message);
        this.status = status;
        this.code = code;
        this.name = 'CoachingApiError';
    }
    isUnauthenticated() {
        return this.status === 401 || this.code === '401_UNAUTHENTICATED';
    }
    isUnauthorized() {
        return this.status === 403;
    }
    isFeatureDisabled() {
        return this.code === '403_FEATURE_DISABLED';
    }
    isNotFound() {
        return this.status === 404 || this.code === '404_NOT_FOUND';
    }
    isValidationError() {
        return this.status === 422 || this.code === '422_VALIDATION_ERROR';
    }
    isQuotaExceeded() {
        return this.status === 413 || this.code === '413_QUOTA_EXCEEDED';
    }
}
async function fetchWithAuth(url, options = {}) {
    const token = getStoredToken();
    if (!token) {
        throw new CoachingApiError('No authentication token found', 401, '401_UNAUTHENTICATED');
    }
    const headers = new Headers(options.headers);
    headers.set('Authorization', `Bearer ${token}`);
    headers.set('Content-Type', 'application/json');
    const response = await fetch(url, {
        ...options,
        headers,
    });
    // Handle 204 No Content
    if (response.status === 204) {
        return undefined;
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        const errorCode = response.headers.get('X-Error-Code') || undefined;
        const errorMessage = typeof data.detail === 'string' ? data.detail : 'Request failed';
        throw new CoachingApiError(errorMessage, response.status, errorCode);
    }
    return data;
}
/**
 * Coach Notes API
 */
export async function createCoachNote(playerId, noteData) {
    const url = `${API_BASE}/api/coaches/players/${playerId}/notes`;
    const data = await fetchWithAuth(url, {
        method: 'POST',
        body: JSON.stringify(noteData),
    });
    return validateCoachNoteRead(data);
}
export async function listPlayerNotes(playerId, params) {
    const queryParams = new URLSearchParams();
    if (params?.severity)
        queryParams.set('severity', params.severity);
    if (params?.video_session_id)
        queryParams.set('video_session_id', params.video_session_id);
    if (params?.offset !== undefined)
        queryParams.set('offset', params.offset.toString());
    if (params?.limit !== undefined)
        queryParams.set('limit', params.limit.toString());
    const url = `${API_BASE}/api/coaches/players/${playerId}/notes?${queryParams}`;
    const data = await fetchWithAuth(url);
    return data.map(validateCoachNoteRead);
}
export async function getCoachNote(noteId) {
    const url = `${API_BASE}/api/coaches/notes/${noteId}`;
    const data = await fetchWithAuth(url);
    return validateCoachNoteRead(data);
}
export async function updateCoachNote(noteId, noteData) {
    const url = `${API_BASE}/api/coaches/notes/${noteId}`;
    const data = await fetchWithAuth(url, {
        method: 'PATCH',
        body: JSON.stringify(noteData),
    });
    return validateCoachNoteRead(data);
}
export async function deleteCoachNote(noteId) {
    const url = `${API_BASE}/api/coaches/notes/${noteId}`;
    await fetchWithAuth(url, { method: 'DELETE' });
}
export async function getCorrectiveGuidance(request) {
    const url = `${API_BASE}/api/coaches/corrective-guidance`;
    return fetchWithAuth(url, {
        method: 'POST',
        body: JSON.stringify(request),
    });
}
/**
 * Video Moment Markers API
 */
export async function createMomentMarker(sessionId, markerData) {
    const url = `${API_BASE}/api/coaches/markers/sessions/${sessionId}/markers`;
    const data = await fetchWithAuth(url, {
        method: 'POST',
        body: JSON.stringify(markerData),
    });
    return validateVideoMomentMarkerRead(data);
}
export async function listSessionMarkers(sessionId, params) {
    const queryParams = new URLSearchParams();
    if (params?.moment_type)
        queryParams.set('moment_type', params.moment_type);
    const url = `${API_BASE}/api/coaches/markers/sessions/${sessionId}/markers?${queryParams}`;
    const data = await fetchWithAuth(url);
    return data.map(validateVideoMomentMarkerRead);
}
export async function updateMomentMarker(markerId, markerData) {
    const url = `${API_BASE}/api/coaches/markers/markers/${markerId}`;
    const data = await fetchWithAuth(url, {
        method: 'PATCH',
        body: JSON.stringify(markerData),
    });
    return validateVideoMomentMarkerRead(data);
}
export async function deleteMomentMarker(markerId) {
    const url = `${API_BASE}/api/coaches/markers/markers/${markerId}`;
    await fetchWithAuth(url, { method: 'DELETE' });
}
/**
 * Helper Functions
 */
export function formatTimestamp(timestampMs) {
    const totalSeconds = Math.floor(timestampMs / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}
export function parseTimestamp(timeString) {
    const parts = timeString.split(':').map(Number);
    if (parts.length === 2) {
        // MM:SS
        return (parts[0] * 60 + parts[1]) * 1000;
    }
    else if (parts.length === 3) {
        // HH:MM:SS
        return (parts[0] * 3600 + parts[1] * 60 + parts[2]) * 1000;
    }
    throw new Error('Invalid time format. Use MM:SS or HH:MM:SS');
}

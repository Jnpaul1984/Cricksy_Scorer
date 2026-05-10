// frontend/src/services/coachPlusVideoService.ts
// API client for Coach Pro Plus video upload & analysis endpoints
import { API_BASE, getStoredToken } from './api';
export class ApiError extends Error {
    status;
    detail;
    code;
    constructor(message, status = 500, detail, code) {
        super(message);
        this.status = status;
        this.detail = detail;
        this.code = code;
        this.name = 'ApiError';
    }
    isFeatureDisabled() {
        return !!(this.status === 403 &&
            (this.code?.includes('feature') || this.detail?.includes('feature')));
    }
    isUnauthorized() {
        return this.status === 401;
    }
}
function getAuthHeader() {
    const token = getStoredToken();
    if (!token)
        return null;
    return { Authorization: `Bearer ${token}` };
}
function url(path) {
    const base = (API_BASE || '').replace(/\/+$/, '');
    const p = path.startsWith('/') ? path : `/${path}`;
    return base ? `${base}${p}` : p;
}
/**
 * Create a new video session for a coach
 */
export async function createVideoSession(data) {
    const token = getStoredToken();
    const authHeader = getAuthHeader();
    console.log('[coachPlusVideoService] createVideoSession:', {
        url: url('/api/coaches/plus/sessions'),
        hasToken: !!token,
        tokenLength: token?.length || 0,
        hasAuthHeader: !!authHeader,
        authHeaderKeys: authHeader ? Object.keys(authHeader) : [],
    });
    const res = await fetch(url('/api/coaches/plus/sessions'), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(authHeader || {}),
        },
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        console.error('[coachPlusVideoService] createVideoSession failed:', {
            status: res.status,
            statusText: res.statusText,
            errorDetail,
            errorCode,
            responseBody: detail,
        });
        throw new ApiError(`Failed to create session: ${res.status}`, res.status, errorDetail, errorCode);
    }
    const result = await res.json();
    console.log('[coachPlusVideoService] createVideoSession success:', result);
    return result;
}
/**
 * List video sessions for current coach (paginated)
 */
export async function listVideoSessions(limit = 50, offset = 0, options) {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (options?.statusFilter) {
        params.set('status_filter', options.statusFilter);
    }
    if (options?.excludeFailed) {
        params.set('exclude_failed', 'true');
    }
    // Add cache-busting to prevent stale data after deletions
    const headers = {
        ...getAuthHeader(),
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
    };
    const res = await fetch(url(`/api/coaches/plus/sessions?${params.toString()}`), {
        method: 'GET',
        headers,
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to list sessions: ${res.status}`, res.status, errorDetail, errorCode);
    }
    return res.json();
}
/**
 * Get a specific video session
 */
export async function getVideoSession(sessionId) {
    const res = await fetch(url(`/api/coaches/plus/sessions/${sessionId}`), {
        method: 'GET',
        headers: getAuthHeader() || {},
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to get session: ${res.status}`, res.status, errorDetail, errorCode);
    }
    return res.json();
}
/**
 * Delete a video session
 */
export async function deleteVideoSession(sessionId) {
    const res = await fetch(url(`/api/coaches/plus/sessions/${sessionId}`), {
        method: 'DELETE',
        headers: getAuthHeader() || {},
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to delete session: ${res.status}`, res.status, errorDetail, errorCode);
    }
    // 204 No Content - no response body
}
/**
 * Bulk delete old/failed sessions
 */
export async function bulkDeleteSessions(options) {
    const params = new URLSearchParams();
    if (options?.statusFilter) {
        params.set('status_filter', options.statusFilter);
    }
    if (options?.olderThanDays) {
        params.set('older_than_days', String(options.olderThanDays));
    }
    const res = await fetch(url(`/api/coaches/plus/sessions/bulk?${params.toString()}`), {
        method: 'DELETE',
        headers: getAuthHeader() || {},
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to bulk delete sessions: ${res.status}`, res.status, errorDetail, errorCode);
    }
    return res.json();
}
/**
 * Re-analyze an existing video session (create new analysis job)
 * Useful for testing different analysis modes or retrying failed analyses
 */
export async function reanalyzeSession(sessionId, options = {}) {
    const res = await fetch(url(`/api/coaches/plus/sessions/${sessionId}/analysis-jobs`), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...getAuthHeader(),
        },
        body: JSON.stringify({
            analysis_mode: options.analysisMode || 'batting',
            sample_fps: options.sampleFps || 10,
            include_frames: options.includeFrames || false,
        }),
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to create analysis job: ${res.status}`, res.status, errorDetail, errorCode);
    }
    return res.json();
}
/**
 * Initiate a video upload: creates analysis job and returns presigned S3 URL
 */
export async function initiateVideoUpload(sessionId, sampleFps = 10, includeFrames = false, analysisMode = null) {
    const res = await fetch(url('/api/coaches/plus/videos/upload/initiate'), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(getAuthHeader() || {}),
        },
        body: JSON.stringify({
            session_id: sessionId,
            sample_fps: sampleFps,
            include_frames: includeFrames,
            analysis_mode: analysisMode,
        }),
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to initiate upload: ${res.status}`, res.status, errorDetail, errorCode);
    }
    return res.json();
}
/**
 * Upload file to presigned S3 URL
 * Yields progress events during upload
 */
export async function uploadToPresignedUrl(presignedUrl, file, onProgress) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        // Track upload progress
        if (onProgress) {
            xhr.upload.addEventListener('progress', (event) => {
                if (event.lengthComputable) {
                    const percent = Math.round((event.loaded / event.total) * 100);
                    onProgress(percent);
                }
            });
        }
        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                onProgress?.(100);
                resolve();
            }
            else {
                const responseText = (xhr.responseText || '').slice(0, 800);
                console.error('[coachPlusVideo] S3 upload failed', {
                    status: xhr.status,
                    statusText: xhr.statusText,
                    responseText,
                    responseHeaders: xhr.getAllResponseHeaders(),
                });
                const detail = responseText ? `; body: ${responseText}` : '';
                reject(new Error(`S3 upload failed: ${xhr.status} ${xhr.statusText}${detail}`));
            }
        });
        xhr.addEventListener('error', () => {
            reject(new Error('Network error during S3 upload'));
        });
        xhr.addEventListener('abort', () => {
            reject(new Error('Upload cancelled'));
        });
        xhr.open('PUT', presignedUrl);
        // Use the actual file type so the upload request is consistent.
        // (Some S3 policies/signatures may be sensitive to Content-Type.)
        xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');
        xhr.send(file);
    });
}
/**
 * Complete a video upload: marks job as processing and queues to SQS
 */
export async function completeVideoUpload(jobId) {
    const res = await fetch(url('/api/coaches/plus/videos/upload/complete'), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(getAuthHeader() || {}),
        },
        body: JSON.stringify({
            job_id: jobId,
        }),
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to complete upload: ${res.status}`, res.status, errorDetail, errorCode);
    }
    return res.json();
}
/**
 * Get analysis job status (poll this for progress)
 */
export async function getAnalysisJobStatus(jobId) {
    const res = await fetch(url(`/api/coaches/plus/analysis-jobs/${jobId}`), {
        method: 'GET',
        headers: getAuthHeader() || {},
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to get job status: ${res.status}`, res.status, errorDetail, errorCode);
    }
    return res.json();
}
/**
 * List analysis jobs for a session
 */
export async function listAnalysisJobs(sessionId) {
    const res = await fetch(url(`/api/coaches/plus/sessions/${sessionId}/analysis-jobs`), {
        method: 'GET',
        headers: getAuthHeader() || {},
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to list jobs: ${res.status}`, res.status, errorDetail, errorCode);
    }
    return res.json();
}
/**
 * Get analysis history for a video session (ordered by created_at desc)
 */
export async function getAnalysisHistory(sessionId) {
    const res = await fetch(url(`/api/coaches/plus/video-sessions/${sessionId}/analysis-history`), {
        method: 'GET',
        headers: getAuthHeader() || {},
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to get analysis history: ${res.status}`, res.status, errorDetail, errorCode);
    }
    return res.json();
}
/**
 * Get a short-lived presigned GET URL for the uploaded session video.
 */
export async function getVideoStreamUrl(sessionId) {
    const res = await fetch(url(`/api/coaches/plus/videos/${sessionId}/stream-url`), {
        method: 'GET',
        headers: getAuthHeader() || {},
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to get stream URL: ${res.status}`, res.status, errorDetail, errorCode);
    }
    return res.json();
}
export async function exportAnalysisPdf(jobId) {
    const res = await fetch(url(`/api/coaches/plus/analysis-jobs/${jobId}/export-pdf`), {
        method: 'POST',
        headers: getAuthHeader() || {},
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to export PDF: ${res.status}`, res.status, errorDetail, errorCode);
    }
    return res.json();
}
export async function setJobGoals(jobId, goals) {
    const res = await fetch(url(`/api/coaches/plus/analysis-jobs/${jobId}/set-goals`), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(getAuthHeader() || {}),
        },
        body: JSON.stringify(goals),
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to set goals: ${res.status}`, res.status, errorDetail, errorCode);
    }
    return res.json();
}
export async function calculateCompliance(jobId) {
    const res = await fetch(url(`/api/coaches/plus/analysis-jobs/${jobId}/calculate-compliance`), {
        method: 'POST',
        headers: getAuthHeader() || {},
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to calculate compliance: ${res.status}`, res.status, errorDetail, errorCode);
    }
    return res.json();
}
/**
 * Get calculated outcomes for a job
 */
export async function getJobOutcomes(jobId) {
    const res = await fetch(url(`/api/coaches/plus/analysis-jobs/${jobId}/outcomes`), {
        method: 'GET',
        headers: getAuthHeader() || {},
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to get outcomes: ${res.status}`, res.status, errorDetail, errorCode);
    }
    return res.json();
}
export async function compareJobs(sessionId, jobIds) {
    const res = await fetch(url(`/api/coaches/plus/sessions/${sessionId}/compare-jobs`), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(getAuthHeader() || {}),
        },
        body: JSON.stringify({ job_ids: jobIds }),
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to compare jobs: ${res.status}`, res.status, errorDetail, errorCode);
    }
    return res.json();
}
/**
 * Generate coaching suggestions for a job
 */
export async function generateCoachSuggestions(jobId) {
    const res = await fetch(url(`/api/coaches/plus/jobs/${jobId}/generate-suggestions`), {
        method: 'POST',
        headers: getAuthHeader() || {},
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to generate suggestions: ${res.status}`, res.status, errorDetail, errorCode);
    }
    return res.json();
}
/**
 * Get coaching suggestions for a job
 */
export async function getCoachSuggestions(jobId) {
    const res = await fetch(url(`/api/coaches/plus/jobs/${jobId}/suggestions`), {
        method: 'GET',
        headers: getAuthHeader() || {},
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        const errorDetail = detail?.detail || res.statusText;
        const errorCode = detail?.code || undefined;
        throw new ApiError(`Failed to get suggestions: ${res.status}`, res.status, errorDetail, errorCode);
    }
    return res.json();
}

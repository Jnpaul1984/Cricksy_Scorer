// frontend/src/services/coachPlusVideoService.ts
// API client for Coach Pro Plus video upload & analysis endpoints

import { API_BASE, getStoredToken } from './api';

export interface ApiErrorResponse {
  detail: string;
  status?: number;
  code?: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number = 500,
    public detail?: string,
    public code?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }

  isFeatureDisabled(): boolean {
    return !!(
      this.status === 403 &&
      (this.code?.includes('feature') || this.detail?.includes('feature'))
    );
  }

  isUnauthorized(): boolean {
    return this.status === 401;
  }
}

export interface VideoSession {
  id: string;
  owner_type: string; // "coach" | "org"
  owner_id: string;
  title: string;
  player_ids: string[];
  status: string; // "pending" | "uploaded" | "processing" | "ready" | "failed"
  notes: string | null;
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
  status: string; // "queued" | "processing" | "quick_running" | "quick_done" | "deep_running" | "done" | "completed" | "failed"
  error_message: string | null;
  sqs_message_id: string | null;
  results: VideoAnalysisResults | null;
  // Staged analysis (new; optional for backward compatibility)
  stage?: string | null;
  progress_pct?: number | null;
  deep_enabled?: boolean | null;
  quick_results?: VideoAnalysisResults | null;
  deep_results?: VideoAnalysisResults | null;
  // PDF export
  pdf_s3_key?: string | null;
  pdf_generated_at?: string | null;
  // Optional, short-lived playback URL (computed per-request; never persisted)
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
  // New (extend-only) evidence markers + convenience top-level fields
  evidence?: Record<
    string,
    {
      threshold?: number;
      worst_frames?: Array<{ frame_num?: number; timestamp_s?: number; score?: number }>;
      bad_segments?: Array<{
        start_frame?: number;
        end_frame?: number;
        start_timestamp_s?: number;
        end_timestamp_s?: number;
        min_score?: number;
      }>;
    }
  >;

  video_fps?: number;
  total_frames?: number;

  // Legacy (older API payloads)
  pose_summary?: {
    total_frames?: number;
    sampled_frames?: number;
    frames_with_pose?: number;
    detection_rate_percent?: number;
    model?: string;
    video_fps?: number;
  };

  // Current (nested) backend schema
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
    // other keys are typically numeric (0..1) but may vary
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

function getAuthHeader(): Record<string, string> | null {
  const token = getStoredToken();
  if (!token) return null;
  return { Authorization: `Bearer ${token}` };
}

function url(path: string): string {
  const base = (API_BASE || '').replace(/\/+$/, '');
  const p = path.startsWith('/') ? path : `/${path}`;
  return base ? `${base}${p}` : p;
}

/**
 * Create a new video session for a coach
 */
export async function createVideoSession(data: {
  title: string;
  player_ids?: string[];
  notes?: string | null;
}): Promise<VideoSession> {
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
    throw new ApiError(
      `Failed to create session: ${res.status}`,
      res.status,
      errorDetail,
      errorCode,
    );
  }

  const result = await res.json();
  console.log('[coachPlusVideoService] createVideoSession success:', result);
  return result;
}

/**
 * List video sessions for current coach (paginated)
 */
export async function listVideoSessions(limit = 50, offset = 0): Promise<VideoSession[]> {
  const res = await fetch(url(`/api/coaches/plus/sessions?limit=${limit}&offset=${offset}`), {
    method: 'GET',
    headers: getAuthHeader() || {},
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    const errorDetail = detail?.detail || res.statusText;
    const errorCode = detail?.code || undefined;
    throw new ApiError(
      `Failed to list sessions: ${res.status}`,
      res.status,
      errorDetail,
      errorCode,
    );
  }

  return res.json();
}

/**
 * Get a specific video session
 */
export async function getVideoSession(sessionId: string): Promise<VideoSession> {
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
 * Initiate a video upload: creates analysis job and returns presigned S3 URL
 */
export async function initiateVideoUpload(
  sessionId: string,
  sampleFps = 10,
  includeFrames = false,
): Promise<UploadInitiateResponse> {
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
    }),
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    const errorDetail = detail?.detail || res.statusText;
    const errorCode = detail?.code || undefined;
    throw new ApiError(
      `Failed to initiate upload: ${res.status}`,
      res.status,
      errorDetail,
      errorCode,
    );
  }

  return res.json();
}

/**
 * Upload file to presigned S3 URL
 * Yields progress events during upload
 */
export async function uploadToPresignedUrl(
  presignedUrl: string,
  file: File,
  onProgress?: (percent: number) => void,
): Promise<void> {
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
      } else {
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
export async function completeVideoUpload(jobId: string): Promise<UploadCompleteResponse> {
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
    throw new ApiError(
      `Failed to complete upload: ${res.status}`,
      res.status,
      errorDetail,
      errorCode,
    );
  }

  return res.json();
}

/**
 * Get analysis job status (poll this for progress)
 */
export async function getAnalysisJobStatus(jobId: string): Promise<VideoAnalysisJob> {
  const res = await fetch(url(`/api/coaches/plus/analysis-jobs/${jobId}`), {
    method: 'GET',
    headers: getAuthHeader() || {},
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    const errorDetail = detail?.detail || res.statusText;
    const errorCode = detail?.code || undefined;
    throw new ApiError(
      `Failed to get job status: ${res.status}`,
      res.status,
      errorDetail,
      errorCode,
    );
  }

  return res.json();
}

/**
 * List analysis jobs for a session
 */
export async function listAnalysisJobs(sessionId: string): Promise<VideoAnalysisJob[]> {
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
 * Get a short-lived presigned GET URL for the uploaded session video.
 */
export async function getVideoStreamUrl(sessionId: string): Promise<VideoStreamUrl> {
  const res = await fetch(url(`/api/coaches/plus/videos/${sessionId}/stream-url`), {
    method: 'GET',
    headers: getAuthHeader() || {},
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    const errorDetail = detail?.detail || res.statusText;
    const errorCode = detail?.code || undefined;
    throw new ApiError(
      `Failed to get stream URL: ${res.status}`,
      res.status,
      errorDetail,
      errorCode,
    );
  }

  return res.json();
}

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

export async function exportAnalysisPdf(jobId: string): Promise<PdfExportResponse> {
  const res = await fetch(url(`/api/coaches/plus/analysis-jobs/${jobId}/export-pdf`), {
    method: 'POST',
    headers: getAuthHeader() || {},
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    const errorDetail = detail?.detail || res.statusText;
    const errorCode = detail?.code || undefined;
    throw new ApiError(
      `Failed to export PDF: ${res.status}`,
      res.status,
      errorDetail,
      errorCode,
    );
  }

  return res.json();
}

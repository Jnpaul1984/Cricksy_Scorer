// frontend/src/services/coachPlusVideoService.ts
// API client for Coach Pro Plus video upload & analysis endpoints

import { API_BASE, getStoredToken, getErrorMessage } from './api'

export interface ApiErrorResponse {
  detail: string
  status?: number
  code?: string
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number = 500,
    public detail?: string,
    public code?: string
  ) {
    super(message)
    this.name = 'ApiError'
  }

  isFeatureDisabled(): boolean {
    return this.status === 403 && (this.code?.includes('feature') || this.detail?.includes('feature'))
  }

  isUnauthorized(): boolean {
    return this.status === 401
  }
}

export interface VideoSession {
  id: string
  owner_type: string // "coach" | "org"
  owner_id: string
  title: string
  player_ids: string[]
  status: string // "pending" | "uploaded" | "processing" | "ready" | "failed"
  notes: string | null
  s3_bucket: string | null
  s3_key: string | null
  created_at: string
  updated_at: string
}

export interface VideoAnalysisJob {
  id: string
  session_id: string
  sample_fps: number
  include_frames: boolean
  status: string // "queued" | "processing" | "completed" | "failed"
  error_message: string | null
  sqs_message_id: string | null
  results: VideoAnalysisResults | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  updated_at: string
}

export interface VideoAnalysisResults {
  pose_summary: {
    total_frames: number
    sampled_frames: number
    frames_with_pose: number
    detection_rate_percent: number
    model: string
    video_fps: number
  }
  metrics: Record<string, number>
  findings: Record<string, unknown>
  report: {
    summary: string
    key_issues: string[]
    drills: {
      name: string
      description: string
      duration_minutes: number
      focus_areas: string[]
    }[]
    one_week_plan: string
  }
  frames?: Array<Record<string, unknown>>
}

export interface UploadInitiateResponse {
  job_id: string
  session_id: string
  presigned_url: string
  expires_in: number
  s3_bucket: string
  s3_key: string
}

export interface UploadCompleteResponse {
  job_id: string
  status: string
  sqs_message_id: string | null
  message: string
}

function getAuthHeader(): Record<string, string> | null {
  const token = getStoredToken()
  if (!token) return null
  return { Authorization: `Bearer ${token}` }
}

function url(path: string): string {
  const base = (API_BASE || '').replace(/\/+$/, '')
  const p = path.startsWith('/') ? path : `/${path}`
  return base ? `${base}${p}` : p
}

/**
 * Create a new video session for a coach
 */
export async function createVideoSession(data: {
  title: string
  player_ids?: string[]
  notes?: string | null
}): Promise<VideoSession> {
  const res = await fetch(url('/api/coaches/plus/sessions'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(getAuthHeader() || {}),
    },
    body: JSON.stringify(data),
  })

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    const errorDetail = detail?.detail || res.statusText
    const errorCode = detail?.code || undefined
    throw new ApiError(
      `Failed to create session: ${res.status}`,
      res.status,
      errorDetail,
      errorCode
    )
  }

  return res.json()
}

/**
 * List video sessions for current coach (paginated)
 */
export async function listVideoSessions(limit = 50, offset = 0): Promise<VideoSession[]> {
  const res = await fetch(
    url(`/api/coaches/plus/sessions?limit=${limit}&offset=${offset}`),
    {
      method: 'GET',
      headers: getAuthHeader() || {},
    }
  )

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    const errorDetail = detail?.detail || res.statusText
    const errorCode = detail?.code || undefined
    throw new ApiError(
      `Failed to list sessions: ${res.status}`,
      res.status,
      errorDetail,
      errorCode
    )
  }

  return res.json()
}

/**
 * Get a specific video session
 */
export async function getVideoSession(sessionId: string): Promise<VideoSession> {
  const res = await fetch(url(`/api/coaches/plus/sessions/${sessionId}`), {
    method: 'GET',
    headers: getAuthHeader() || {},
  })

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    const errorDetail = detail?.detail || res.statusText
    const errorCode = detail?.code || undefined
    throw new ApiError(
      `Failed to get session: ${res.status}`,
      res.status,
      errorDetail,
      errorCode
    )
  }

  return res.json()
}

/**
 * Initiate a video upload: creates analysis job and returns presigned S3 URL
 */
export async function initiateVideoUpload(
  sessionId: string,
  sampleFps = 10,
  includeFrames = false
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
  })

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    const errorDetail = detail?.detail || res.statusText
    const errorCode = detail?.code || undefined
    throw new ApiError(
      `Failed to initiate upload: ${res.status}`,
      res.status,
      errorDetail,
      errorCode
    )
  }

  return res.json()
}

/**
 * Upload file to presigned S3 URL
 * Yields progress events during upload
 */
export async function uploadToPresignedUrl(
  presignedUrl: string,
  file: File,
  onProgress?: (percent: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()

    // Track upload progress
    if (onProgress) {
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100)
          onProgress(percent)
        }
      })
    }

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress?.(100)
        resolve()
      } else {
        reject(new Error(`S3 upload failed: ${xhr.status} ${xhr.statusText}`))
      }
    })

    xhr.addEventListener('error', () => {
      reject(new Error('Network error during S3 upload'))
    })

    xhr.addEventListener('abort', () => {
      reject(new Error('Upload cancelled'))
    })

    xhr.open('PUT', presignedUrl)
    xhr.setRequestHeader('Content-Type', 'video/mp4')
    xhr.send(file)
  })
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
  })

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    const errorDetail = detail?.detail || res.statusText
    const errorCode = detail?.code || undefined
    throw new ApiError(
      `Failed to complete upload: ${res.status}`,
      res.status,
      errorDetail,
      errorCode
    )
  }

  return res.json()
}

/**
 * Get analysis job status (poll this for progress)
 */
export async function getAnalysisJobStatus(jobId: string): Promise<VideoAnalysisJob> {
  const res = await fetch(url(`/api/coaches/plus/analysis-jobs/${jobId}`), {
    method: 'GET',
    headers: getAuthHeader() || {},
  })

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    const errorDetail = detail?.detail || res.statusText
    const errorCode = detail?.code || undefined
    throw new ApiError(
      `Failed to get job status: ${res.status}`,
      res.status,
      errorDetail,
      errorCode
    )
  }

  return res.json()
}

/**
 * List analysis jobs for a session
 */
export async function listAnalysisJobs(sessionId: string): Promise<VideoAnalysisJob[]> {
  const res = await fetch(url(`/api/coaches/plus/sessions/${sessionId}/analysis-jobs`), {
    method: 'GET',
    headers: getAuthHeader() || {},
  })

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    const errorDetail = detail?.detail || res.statusText
    const errorCode = detail?.code || undefined
    throw new ApiError(
      `Failed to list jobs: ${res.status}`,
      res.status,
      errorDetail,
      errorCode
    )
  }

  return res.json()
}

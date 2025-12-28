// frontend/src/stores/coachPlusVideoStore.ts
// Pinia store for Coach Pro Plus video upload & analysis

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  createVideoSession,
  listVideoSessions,
  getVideoSession,
  initiateVideoUpload,
  uploadToPresignedUrl,
  completeVideoUpload,
  getAnalysisJobStatus,
  listAnalysisJobs,
  ApiError,
  type VideoSession,
  type VideoAnalysisJob,
} from '@/services/coachPlusVideoService'

export interface UploadState {
  jobId: string
  fileName: string
  uploadProgressPercent: number
  status: 'uploading' | 'completing' | 'waiting' | 'error'
  error: string | null
}

export const useCoachPlusVideoStore = defineStore('coachPlusVideo', () => {
  // ============================================================================
  // STATE
  // ============================================================================

  const sessions = ref<VideoSession[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Upload state
  const uploading = ref<UploadState | null>(null)

  // Job polling state
  const pollingJobs = ref<Map<string, ReturnType<typeof setInterval>>>(new Map())
  const jobStatusMap = ref<Map<string, VideoAnalysisJob>>(new Map())

  // ============================================================================
  // COMPUTED
  // ============================================================================

  const isUploading = computed(() => uploading.value !== null)
  const uploadProgress = computed(() => uploading.value?.uploadProgressPercent ?? 0)

  const allJobs = computed(() => Array.from(jobStatusMap.value.values()))

  function isJobInProgress(job: VideoAnalysisJob): boolean {
    return (
      job.status === 'queued' ||
      job.status === 'processing' ||
      job.status === 'quick_running' ||
      job.status === 'quick_done' ||
      job.status === 'deep_running'
    )
  }

  function isJobTerminal(job: VideoAnalysisJob): boolean {
    return job.status === 'completed' || job.status === 'done' || job.status === 'failed'
  }

  const processingJobs = computed(() =>
    allJobs.value.filter((j) => isJobInProgress(j))
  )

  // ============================================================================
  // ACTIONS
  // ============================================================================

  /**
   * Fetch all sessions for current coach
   */
  async function fetchSessions(limit = 50, offset = 0) {
    loading.value = true
    error.value = null

    try {
      const data = await listVideoSessions(limit, offset)
      sessions.value = data

      // Fetch jobs for each session to populate job status
      for (const session of sessions.value) {
        await fetchJobsForSession(session.id)
      }
    } catch (err) {
      // Handle feature-disabled errors specifically
      if (err instanceof ApiError && err.isFeatureDisabled()) {
        error.value = `Video sessions feature is not enabled on your plan. ${err.detail || 'Please upgrade your subscription.'}`
      } else {
        error.value = err instanceof Error ? err.message : 'Failed to fetch sessions'
      }
      console.error('[coachPlusVideo] fetchSessions error:', err)
    } finally {
      loading.value = false
    }
  }

  /**
   * Create a new video session
   */
  async function createSession(data: {
    title: string
    player_ids?: string[]
    notes?: string
  }): Promise<VideoSession | null> {
    error.value = null

    try {
      const session = await createVideoSession(data)
      sessions.value.unshift(session)
      return session
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create session'
      console.error('[coachPlusVideo] createSession error:', err)
      return null
    }
  }

  /**
   * Start a video upload flow:
   * 1. Initiate upload (get presigned URL + job_id)
   * 2. Upload file to S3
   * 3. Complete upload (mark as processing)
   * 4. Begin polling job status
   */
  async function startUpload(
    file: File,
    sessionId: string,
    sampleFps = 10,
    includeFrames = false
  ): Promise<string | null> {
    error.value = null

    // Validate file
    const MAX_FILE_SIZE = 500 * 1024 * 1024 // 500MB
    const ALLOWED_TYPES = ['video/mp4', 'video/quicktime', 'video/x-msvideo']

    if (file.size > MAX_FILE_SIZE) {
      error.value = `File too large: ${(file.size / 1024 / 1024).toFixed(0)}MB (max 500MB)`
      return null
    }

    if (!ALLOWED_TYPES.includes(file.type)) {
      error.value = `Unsupported format: ${file.type}. Use MP4, MOV, or AVI.`
      return null
    }

    try {
      // 1. Initiate upload
      uploading.value = {
        jobId: '',
        fileName: file.name,
        uploadProgressPercent: 0,
        status: 'uploading',
        error: null,
      }

      const initiateResp = await initiateVideoUpload(sessionId, sampleFps, includeFrames)
      const jobId = initiateResp.job_id
      const presignedUrl = initiateResp.presigned_url

      uploading.value.jobId = jobId

      // 2. Upload file to S3
      await uploadToPresignedUrl(presignedUrl, file, (percent) => {
        if (uploading.value) {
          uploading.value.uploadProgressPercent = percent
        }
      })

      // 3. Complete upload
      uploading.value.status = 'completing'
      await completeVideoUpload(jobId)

      uploading.value.status = 'waiting'
      uploading.value.uploadProgressPercent = 100

      // 4. Start polling job status
      pollJobUntilComplete(jobId)

      return jobId
    } catch (err) {
      let msg = 'Upload failed'

      // Handle specific error types with better messaging
      if (err instanceof ApiError) {
        if (err.isFeatureDisabled()) {
          msg = `Video upload feature is not enabled on your plan. ${err.detail || 'Please upgrade to use this feature.'}`
        } else if (err.isUnauthorized()) {
          msg = 'Your session expired. Please log in again.'
        } else {
          msg = err.detail || err.message
        }
      } else if (err instanceof Error) {
        msg = err.message
      }

      error.value = msg
      if (uploading.value) {
        uploading.value.status = 'error'
        uploading.value.error = msg
      }
      console.error('[coachPlusVideo] startUpload error:', err)
      return null
    }
  }

  /**
   * Fetch jobs for a specific session and cache them
   */
  async function fetchJobsForSession(sessionId: string): Promise<void> {
    try {
      const jobs = await listAnalysisJobs(sessionId)
      for (const job of jobs) {
        jobStatusMap.value.set(job.id, job)
      }
    } catch (err) {
      console.error(`[coachPlusVideo] Failed to fetch jobs for session ${sessionId}:`, err)
    }
  }

  /**
   * Poll a job until it's no longer processing
   * Stops polling when status is "completed" or "failed"
   */
  function pollJobUntilComplete(jobId: string, intervalMs = 5000): void {
    // Clear any existing interval for this job
    const existingInterval = pollingJobs.value.get(jobId)
    if (existingInterval) {
      clearInterval(existingInterval)
    }

    // Fetch immediately first
    updateJobStatus(jobId)

    // Then poll
    const interval = setInterval(async () => {
      const job = jobStatusMap.value.get(jobId)
      if (!job) {
        stopPollingJob(jobId)
        return
      }

      await updateJobStatus(jobId)

      const updated = jobStatusMap.value.get(jobId)
      if (updated && isJobTerminal(updated)) {
        stopPollingJob(jobId)
      }
    }, intervalMs)

    pollingJobs.value.set(jobId, interval)
  }

  /**
   * Fetch and cache latest job status
   */
  async function updateJobStatus(jobId: string): Promise<void> {
    try {
      const job = await getAnalysisJobStatus(jobId)
      jobStatusMap.value.set(jobId, job)
    } catch (err) {
      console.error(`[coachPlusVideo] Failed to update job ${jobId}:`, err)
    }
  }

  /**
   * Stop polling a specific job
   */
  function stopPollingJob(jobId: string): void {
    const interval = pollingJobs.value.get(jobId)
    if (interval) {
      clearInterval(interval)
      pollingJobs.value.delete(jobId)
    }
  }

  /**
   * Stop all polling and clear upload state
   */
  function clearUploadState(): void {
    uploading.value = null
    error.value = null
  }

  /**
   * Clean up: stop all polling on unmount
   */
  function cleanup(): void {
    for (const interval of pollingJobs.value.values()) {
      clearInterval(interval)
    }
    pollingJobs.value.clear()
    clearUploadState()
  }

  return {
    // State
    sessions,
    loading,
    error,
    uploading,
    jobStatusMap,
    allJobs,
    processingJobs,

    // Computed
    isUploading,
    uploadProgress,

    // Actions
    fetchSessions,
    createSession,
    startUpload,
    fetchJobsForSession,
    pollJobUntilComplete,
    stopPollingJob,
    updateJobStatus,
    clearUploadState,
    cleanup,
  }
})

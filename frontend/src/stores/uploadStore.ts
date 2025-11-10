/**
 * Upload Store
 * Manages scorecard upload state and operations
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Upload {
  upload_id: string
  status: 'initiated' | 'uploaded' | 'processing' | 'parsed' | 'applied' | 'failed' | 'cancelled'
  filename: string
  game_id: string | null
  parsed_preview: ParsedPreview | null
  error_message: string | null
  created_at: string
  updated_at: string
  processed_at: string | null
  applied_at: string | null
}

export interface ParsedPreview {
  deliveries: Delivery[]
  teams: {
    team_a: string | null
    team_b: string | null
  }
  metadata: {
    match_type: string
    date: string | null
    venue: string | null
    total_runs?: number
    total_wickets?: number
    overs?: number
  }
  confidence: number
  raw_ocr: string
  warnings: string[]
  validation_errors?: string[]
}

export interface Delivery {
  over: number
  ball: number
  batsman?: string
  runs: number
  extras?: number
  wicket?: boolean
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const useUploadStore = defineStore('upload', () => {
  // State
  const uploads = ref<Map<string, Upload>>(new Map())
  const currentUploadId = ref<string | null>(null)
  const isUploading = ref(false)
  const uploadProgress = ref(0)

  // Computed
  const currentUpload = computed(() => {
    if (!currentUploadId.value) return null
    return uploads.value.get(currentUploadId.value) || null
  })

  const uploadsList = computed(() => {
    return Array.from(uploads.value.values()).sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
  })

  // Actions
  async function initiateUpload(
    file: File,
    gameId: string | null = null,
    userId: string | null = null
  ): Promise<string> {
    try {
      isUploading.value = true
      uploadProgress.value = 0

      // Step 1: Initiate upload
      const response = await fetch(`${API_BASE}/api/uploads/initiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: file.name,
          content_type: file.type,
          game_id: gameId,
          user_id: userId
        })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to initiate upload')
      }

      const data = await response.json()
      const { upload_id, presigned_url } = data

      currentUploadId.value = upload_id
      uploadProgress.value = 25

      // Step 2: Upload file to S3/MinIO
      const uploadResponse = await fetch(presigned_url, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': file.type
        }
      })

      if (!uploadResponse.ok) {
        throw new Error('Failed to upload file to storage')
      }

      uploadProgress.value = 75

      // Step 3: Mark upload complete
      const completeResponse = await fetch(`${API_BASE}/api/uploads/${upload_id}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_size: file.size
        })
      })

      if (!completeResponse.ok) {
        const error = await completeResponse.json()
        throw new Error(error.detail || 'Failed to complete upload')
      }

      uploadProgress.value = 100

      // Fetch initial status
      await fetchUploadStatus(upload_id)

      return upload_id
    } catch (error) {
      console.error('Upload failed:', error)
      throw error
    } finally {
      isUploading.value = false
    }
  }

  async function fetchUploadStatus(uploadId: string): Promise<Upload> {
    const response = await fetch(`${API_BASE}/api/uploads/${uploadId}/status`)

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to fetch upload status')
    }

    const upload = await response.json()
    uploads.value.set(uploadId, upload)

    return upload
  }

  async function pollUploadStatus(uploadId: string, maxAttempts = 60, intervalMs = 2000): Promise<Upload> {
    let attempts = 0

    while (attempts < maxAttempts) {
      const upload = await fetchUploadStatus(uploadId)

      // Stop polling if reached terminal state
      if (['parsed', 'applied', 'failed', 'cancelled'].includes(upload.status)) {
        return upload
      }

      // Wait before next poll
      await new Promise(resolve => setTimeout(resolve, intervalMs))
      attempts++
    }

    throw new Error('Upload processing timeout')
  }

  async function applyUpload(
    uploadId: string,
    confirm: boolean,
    validatedData: ParsedPreview | null = null
  ): Promise<void> {
    const response = await fetch(`${API_BASE}/api/uploads/${uploadId}/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        confirm,
        validated_data: validatedData
      })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to apply upload')
    }

    // Refresh status
    await fetchUploadStatus(uploadId)
  }

  function clearCurrentUpload() {
    currentUploadId.value = null
    uploadProgress.value = 0
  }

  function clearAllUploads() {
    uploads.value.clear()
    currentUploadId.value = null
    uploadProgress.value = 0
  }

  return {
    // State
    uploads,
    currentUploadId,
    isUploading,
    uploadProgress,

    // Computed
    currentUpload,
    uploadsList,

    // Actions
    initiateUpload,
    fetchUploadStatus,
    pollUploadStatus,
    applyUpload,
    clearCurrentUpload,
    clearAllUploads
  }
})

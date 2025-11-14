/**
 * Upload Store
 * 
 * Manages state for scorecard upload and OCR workflow.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export interface Upload {
  upload_id: number
  filename: string
  status: 'pending' | 'processing' | 'ready' | 'failed'
  game_id: number | null
  parsed_preview: ParsedPreview | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface ParsedPreview {
  deliveries: Delivery[]
  metadata: {
    confidence: number
    parser: string
    warnings?: string[]
    ocr_text?: string
    [key: string]: any
  }
}

export interface Delivery {
  over: number
  ball: number
  batsman: string
  bowler: string
  runs: number
  is_wicket: boolean
  is_extra: boolean
  extra_type?: string | null
}

export interface InitiateUploadResponse {
  upload_id: number
  presigned_url: string
  s3_key: string
  expires_in: number
}

export const useUploadStore = defineStore('upload', () => {
  // State
  const uploads = ref<Map<number, Upload>>(new Map())
  const currentUploadId = ref<number | null>(null)
  const isUploading = ref(false)
  const uploadProgress = ref(0)
  const error = ref<string | null>(null)

  // Computed
  const currentUpload = computed(() => {
    if (currentUploadId.value === null) return null
    return uploads.value.get(currentUploadId.value) || null
  })

  const isProcessing = computed(() => {
    return currentUpload.value?.status === 'processing'
  })

  const isReady = computed(() => {
    return currentUpload.value?.status === 'ready'
  })

  const hasFailed = computed(() => {
    return currentUpload.value?.status === 'failed'
  })

  // Actions
  async function initiateUpload(
    file: File,
    uploaderId: string,
    gameId?: number
  ): Promise<InitiateUploadResponse> {
    error.value = null
    isUploading.value = true

    try {
      const response = await axios.post<InitiateUploadResponse>('/api/uploads/initiate', {
        filename: file.name,
        content_type: file.type,
        uploader_id: uploaderId,
        game_id: gameId || null
      })

      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to initiate upload'
      throw err
    } finally {
      isUploading.value = false
    }
  }

  async function uploadToS3(presignedUrl: string, file: File): Promise<void> {
    error.value = null
    uploadProgress.value = 0

    try {
      await axios.put(presignedUrl, file, {
        headers: {
          'Content-Type': file.type
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            uploadProgress.value = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            )
          }
        }
      })
    } catch (err: any) {
      error.value = 'Failed to upload file to storage'
      throw err
    }
  }

  async function completeUpload(uploadId: number): Promise<void> {
    error.value = null

    try {
      const response = await axios.post('/api/uploads/complete', {
        upload_id: uploadId
      })

      currentUploadId.value = uploadId
      
      // Fetch initial status
      await fetchUploadStatus(uploadId)
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to complete upload'
      throw err
    }
  }

  async function fetchUploadStatus(uploadId: number): Promise<Upload> {
    try {
      const response = await axios.get<Upload>(`/api/uploads/${uploadId}/status`)
      
      uploads.value.set(uploadId, response.data)
      
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch upload status'
      throw err
    }
  }

  async function pollUploadStatus(uploadId: number, interval = 2000): Promise<Upload> {
    return new Promise((resolve, reject) => {
      const poll = setInterval(async () => {
        try {
          const upload = await fetchUploadStatus(uploadId)
          
          // Stop polling when processing is complete
          if (upload.status === 'ready' || upload.status === 'failed') {
            clearInterval(poll)
            resolve(upload)
          }
        } catch (err) {
          clearInterval(poll)
          reject(err)
        }
      }, interval)
    })
  }

  async function applyUpload(
    uploadId: number,
    editedPreview?: ParsedPreview
  ): Promise<void> {
    error.value = null

    try {
      await axios.post(`/api/uploads/${uploadId}/apply`, {
        confirmation: true,
        edited_preview: editedPreview || null
      })

      // Refresh upload status
      await fetchUploadStatus(uploadId)
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to apply upload'
      throw err
    }
  }

  async function uploadAndProcess(
    file: File,
    uploaderId: string,
    gameId?: number
  ): Promise<number> {
    // Step 1: Initiate upload
    const { upload_id, presigned_url } = await initiateUpload(file, uploaderId, gameId)

    // Step 2: Upload file to S3
    await uploadToS3(presigned_url, file)

    // Step 3: Complete upload and trigger processing
    await completeUpload(upload_id)

    return upload_id
  }

  function clearError(): void {
    error.value = null
  }

  function resetCurrentUpload(): void {
    currentUploadId.value = null
    uploadProgress.value = 0
    error.value = null
  }

  return {
    // State
    uploads,
    currentUploadId,
    isUploading,
    uploadProgress,
    error,

    // Computed
    currentUpload,
    isProcessing,
    isReady,
    hasFailed,

    // Actions
    initiateUpload,
    uploadToS3,
    completeUpload,
    fetchUploadStatus,
    pollUploadStatus,
    applyUpload,
    uploadAndProcess,
    clearError,
    resetCurrentUpload
  }
})

// src/stores/uploadStore.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Ref } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export interface Upload {
  upload_id: string
  status: 'pending' | 'processing' | 'ready' | 'failed'
  filename: string
  file_type: string
  game_id: string | null
  parsed_preview: ParsedPreview | null
  upload_metadata: Record<string, any>
  created_at: string
  updated_at: string
}

export interface ParsedPreview {
  deliveries: Delivery[]
  metadata: {
    total_deliveries: number
    parser_version: string
    ocr_length?: number
  }
}

export interface Delivery {
  over: number
  ball: number
  bowler: string
  batsman: string
  runs: number
  is_wicket: boolean
  extras: number
}

export interface InitiateUploadResponse {
  upload_id: string
  s3_key: string
  presigned_url: string
  expires_in: number
}

export const useUploadStore = defineStore('upload', () => {
  // State
  const currentUpload: Ref<Upload | null> = ref(null)
  const uploads: Ref<Upload[]> = ref([])
  const isUploading = ref(false)
  const uploadProgress = ref(0)
  const error: Ref<string | null> = ref(null)

  // Computed
  const isPending = computed(() => currentUpload.value?.status === 'pending')
  const isProcessing = computed(() => currentUpload.value?.status === 'processing')
  const isReady = computed(() => currentUpload.value?.status === 'ready')
  const isFailed = computed(() => currentUpload.value?.status === 'failed')

  // Actions
  async function initiateUpload(
    file: File,
    gameId: string | null = null
  ): Promise<InitiateUploadResponse> {
    error.value = null
    try {
      const response = await fetch(`${API_BASE}/api/uploads/initiate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filename: file.name,
          file_type: file.type,
          game_id: gameId,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to initiate upload')
      }

      const data = await response.json()
      return data as InitiateUploadResponse
    } catch (err: any) {
      error.value = err.message
      throw err
    }
  }

  async function uploadToS3(file: File, presignedUrl: string): Promise<void> {
    isUploading.value = true
    uploadProgress.value = 0

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          uploadProgress.value = Math.round((e.loaded / e.total) * 100)
        }
      })

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          uploadProgress.value = 100
          isUploading.value = false
          resolve()
        } else {
          isUploading.value = false
          reject(new Error(`Upload failed with status ${xhr.status}`))
        }
      })

      xhr.addEventListener('error', () => {
        isUploading.value = false
        reject(new Error('Network error during upload'))
      })

      xhr.open('PUT', presignedUrl)
      xhr.setRequestHeader('Content-Type', file.type)
      xhr.send(file)
    })
  }

  async function completeUpload(
    uploadId: string,
    s3Key: string,
    size: number,
    checksum?: string
  ): Promise<void> {
    error.value = null
    try {
      const response = await fetch(`${API_BASE}/api/uploads/complete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          upload_id: uploadId,
          s3_key: s3Key,
          size,
          checksum,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to complete upload')
      }
    } catch (err: any) {
      error.value = err.message
      throw err
    }
  }

  async function getUploadStatus(uploadId: string): Promise<Upload> {
    error.value = null
    try {
      const response = await fetch(`${API_BASE}/api/uploads/${uploadId}/status`)

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to get upload status')
      }

      const data = await response.json()
      currentUpload.value = data as Upload
      return data as Upload
    } catch (err: any) {
      error.value = err.message
      throw err
    }
  }

  async function pollUntilReady(
    uploadId: string,
    maxAttempts = 60,
    intervalMs = 2000
  ): Promise<Upload> {
    for (let i = 0; i < maxAttempts; i++) {
      const upload = await getUploadStatus(uploadId)

      if (upload.status === 'ready' || upload.status === 'failed') {
        return upload
      }

      // Wait before next poll
      await new Promise(resolve => setTimeout(resolve, intervalMs))
    }

    throw new Error('Upload processing timeout')
  }

  async function applyToGame(uploadId: string, gameId: string): Promise<void> {
    error.value = null
    try {
      const response = await fetch(`${API_BASE}/api/uploads/${uploadId}/apply`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          game_id: gameId,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to apply upload')
      }

      const result = await response.json()
      return result
    } catch (err: any) {
      error.value = err.message
      throw err
    }
  }

  async function uploadFile(file: File, gameId: string | null = null): Promise<string> {
    try {
      // Step 1: Initiate upload
      const { upload_id, s3_key, presigned_url } = await initiateUpload(file, gameId)

      // Step 2: Upload to S3
      await uploadToS3(file, presigned_url)

      // Step 3: Complete upload
      await completeUpload(upload_id, s3_key, file.size)

      return upload_id
    } catch (err: any) {
      error.value = err.message
      throw err
    }
  }

  function clearError() {
    error.value = null
  }

  function reset() {
    currentUpload.value = null
    isUploading.value = false
    uploadProgress.value = 0
    error.value = null
  }

  return {
    // State
    currentUpload,
    uploads,
    isUploading,
    uploadProgress,
    error,

    // Computed
    isPending,
    isProcessing,
    isReady,
    isFailed,

    // Actions
    initiateUpload,
    uploadToS3,
    completeUpload,
    getUploadStatus,
    pollUntilReady,
    applyToGame,
    uploadFile,
    clearError,
    reset,
  }
})

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Upload {
  upload_id: string
  filename: string
  status: 'pending' | 'uploaded' | 'processing' | 'parsed' | 'applied' | 'failed' | 'rejected'
  created_at: string
  updated_at: string
  processed_at?: string
  applied_at?: string
  error_message?: string
  parsed_data?: {
    teams?: Array<{ name: string }>
    innings?: Array<{ runs: number; wickets: number; confidence?: string }>
    format?: string
    parse_notes?: string[]
    raw_lines?: string[]
    [key: string]: any
  }
  game_id?: string
}

export interface UploadProgress {
  upload_id: string
  progress: number // 0-100
  stage: 'uploading' | 'processing' | 'complete' | 'error'
  message?: string
}

export const useUploadStore = defineStore('upload', () => {
  // State
  const uploads = ref<Map<string, Upload>>(new Map())
  const uploadProgress = ref<Map<string, UploadProgress>>(new Map())
  const isUploading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const recentUploads = computed(() => {
    return Array.from(uploads.value.values())
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 10)
  })

  const pendingUploads = computed(() => {
    return Array.from(uploads.value.values()).filter(
      (u) => u.status === 'pending' || u.status === 'uploaded' || u.status === 'processing'
    )
  })

  const parsedUploads = computed(() => {
    return Array.from(uploads.value.values()).filter((u) => u.status === 'parsed')
  })

  // Actions
  async function initiateUpload(file: File, uploaderName?: string) {
    isUploading.value = true
    error.value = null

    try {
      // Step 1: Initiate upload and get presigned URL
      const response = await fetch('/api/uploads/initiate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: file.name,
          content_type: file.type,
          file_size: file.size,
          uploader_name: uploaderName,
        }),
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || 'Failed to initiate upload')
      }

      const data = await response.json()
      const uploadId = data.upload_id

      // Track progress
      uploadProgress.value.set(uploadId, {
        upload_id: uploadId,
        progress: 0,
        stage: 'uploading',
        message: 'Uploading file...',
      })

      // Step 2: Upload file to S3/MinIO
      await uploadToS3(data.upload_url, file, uploadId)

      // Update progress
      uploadProgress.value.set(uploadId, {
        upload_id: uploadId,
        progress: 100,
        stage: 'complete',
        message: 'Upload complete',
      })

      // Step 3: Mark upload as complete
      await completeUpload(uploadId)

      // Step 4: Start polling for status
      pollUploadStatus(uploadId)

      return uploadId
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Upload failed'
      throw err
    } finally {
      isUploading.value = false
    }
  }

  async function uploadToS3(presignedUrl: string, file: File, uploadId: string) {
    return new Promise<void>((resolve, reject) => {
      const xhr = new XMLHttpRequest()

      // Track progress
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100)
          uploadProgress.value.set(uploadId, {
            upload_id: uploadId,
            progress: percent,
            stage: 'uploading',
            message: `Uploading... ${percent}%`,
          })
        }
      })

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve()
        } else {
          reject(new Error(`Upload failed with status ${xhr.status}`))
        }
      })

      xhr.addEventListener('error', () => {
        reject(new Error('Network error during upload'))
      })

      xhr.open('PUT', presignedUrl)
      xhr.setRequestHeader('Content-Type', file.type)
      xhr.send(file)
    })
  }

  async function completeUpload(uploadId: string) {
    const response = await fetch('/api/uploads/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ upload_id: uploadId }),
    })

    if (!response.ok) {
      const err = await response.json()
      throw new Error(err.detail || 'Failed to complete upload')
    }

    uploadProgress.value.set(uploadId, {
      upload_id: uploadId,
      progress: 100,
      stage: 'processing',
      message: 'Processing with OCR...',
    })
  }

  async function fetchUploadStatus(uploadId: string): Promise<Upload> {
    const response = await fetch(`/api/uploads/status/${uploadId}`)

    if (!response.ok) {
      const err = await response.json()
      throw new Error(err.detail || 'Failed to fetch upload status')
    }

    const upload: Upload = await response.json()
    uploads.value.set(uploadId, upload)

    // Update progress based on status
    if (upload.status === 'parsed') {
      uploadProgress.value.set(uploadId, {
        upload_id: uploadId,
        progress: 100,
        stage: 'complete',
        message: 'Processing complete - ready for review',
      })
    } else if (upload.status === 'failed') {
      uploadProgress.value.set(uploadId, {
        upload_id: uploadId,
        progress: 100,
        stage: 'error',
        message: upload.error_message || 'Processing failed',
      })
    }

    return upload
  }

  function pollUploadStatus(uploadId: string, intervalMs = 3000, maxAttempts = 60) {
    let attempts = 0

    const poll = async () => {
      if (attempts >= maxAttempts) {
        console.warn(`Stopped polling for upload ${uploadId} after ${maxAttempts} attempts`)
        return
      }

      attempts++

      try {
        const upload = await fetchUploadStatus(uploadId)

        // Stop polling if in terminal state
        if (['parsed', 'applied', 'failed', 'rejected'].includes(upload.status)) {
          return
        }

        // Continue polling
        setTimeout(poll, intervalMs)
      } catch (err) {
        console.error('Error polling upload status:', err)
        setTimeout(poll, intervalMs * 2) // Exponential backoff
      }
    }

    poll()
  }

  async function applyUpload(uploadId: string, gameId?: string): Promise<void> {
    const response = await fetch('/api/uploads/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        upload_id: uploadId,
        game_id: gameId,
        confirmation: true,
      }),
    })

    if (!response.ok) {
      const err = await response.json()
      throw new Error(err.detail || 'Failed to apply upload')
    }

    await fetchUploadStatus(uploadId)
  }

  function clearError() {
    error.value = null
  }

  function removeUpload(uploadId: string) {
    uploads.value.delete(uploadId)
    uploadProgress.value.delete(uploadId)
  }

  return {
    // State
    uploads,
    uploadProgress,
    isUploading,
    error,

    // Computed
    recentUploads,
    pendingUploads,
    parsedUploads,

    // Actions
    initiateUpload,
    fetchUploadStatus,
    applyUpload,
    clearError,
    removeUpload,
  }
})

/**
 * Pinia store for managing scorecard uploads
 */

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export interface Upload {
  upload_id: string;
  filename: string;
  status: 'pending' | 'uploaded' | 'processing' | 'completed' | 'failed' | 'applied';
  uploaded_at: string | null;
  processed_at: string | null;
  applied_at: string | null;
  parsed_preview: ParsedPreview | null;
  error_message: string | null;
}

export interface ParsedPreview {
  teams?: {
    team_a?: string;
    team_b?: string;
  };
  players?: Array<{
    name: string;
    runs: number;
    balls: number;
    wickets: number;
  }>;
  total_runs: number;
  total_wickets: number;
  overs: number;
  confidence: 'very_low' | 'low' | 'medium' | 'high';
  raw_text?: string;
  validation_error?: string;
}

export const useUploadStore = defineStore('upload', () => {
  // State
  const uploads = ref<Map<string, Upload>>(new Map());
  const currentUploadId = ref<string | null>(null);
  const isUploading = ref(false);
  const uploadError = ref<string | null>(null);

  // Computed
  const currentUpload = computed(() => {
    if (!currentUploadId.value) return null;
    return uploads.value.get(currentUploadId.value) || null;
  });

  const uploadsList = computed(() => {
    return Array.from(uploads.value.values()).sort((a, b) => {
      const timeA = a.uploaded_at || a.upload_id;
      const timeB = b.uploaded_at || b.upload_id;
      return timeB.localeCompare(timeA);
    });
  });

  // Actions
  async function initiateUpload(file: File): Promise<string | null> {
    isUploading.value = true;
    uploadError.value = null;

    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

      // Step 1: Initiate upload
      const initiateResponse = await fetch(`${API_BASE}/api/uploads/initiate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filename: file.name,
          content_type: file.type || 'image/jpeg',
        }),
      });

      if (!initiateResponse.ok) {
        const error = await initiateResponse.json();
        throw new Error(error.detail || 'Failed to initiate upload');
      }

      const { upload_id, upload_url } = await initiateResponse.json();

      // Store initial upload record
      uploads.value.set(upload_id, {
        upload_id,
        filename: file.name,
        status: 'pending',
        uploaded_at: null,
        processed_at: null,
        applied_at: null,
        parsed_preview: null,
        error_message: null,
      });

      currentUploadId.value = upload_id;

      // Step 2: Upload file directly to S3/MinIO
      const uploadResponse = await fetch(upload_url, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': file.type || 'image/jpeg',
        },
      });

      if (!uploadResponse.ok) {
        throw new Error('Failed to upload file to storage');
      }

      // Step 3: Complete upload
      const completeResponse = await fetch(`${API_BASE}/api/uploads/complete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ upload_id }),
      });

      if (!completeResponse.ok) {
        const error = await completeResponse.json();
        throw new Error(error.detail || 'Failed to complete upload');
      }

      // Update status
      const upload = uploads.value.get(upload_id);
      if (upload) {
        upload.status = 'uploaded';
        upload.uploaded_at = new Date().toISOString();
      }

      // Start polling for status
      pollUploadStatus(upload_id);

      return upload_id;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Upload failed';
      uploadError.value = message;
      console.error('Upload error:', error);
      return null;
    } finally {
      isUploading.value = false;
    }
  }

  async function fetchUploadStatus(uploadId: string): Promise<void> {
    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE}/api/uploads/${uploadId}/status`);

      if (!response.ok) {
        throw new Error('Failed to fetch upload status');
      }

      const data: Upload = await response.json();
      uploads.value.set(uploadId, data);
    } catch (error) {
      console.error('Failed to fetch upload status:', error);
    }
  }

  function pollUploadStatus(uploadId: string): void {
    const pollInterval = setInterval(async () => {
      await fetchUploadStatus(uploadId);

      const upload = uploads.value.get(uploadId);
      if (upload && ['completed', 'failed', 'applied'].includes(upload.status)) {
        clearInterval(pollInterval);
      }
    }, 2000); // Poll every 2 seconds

    // Stop polling after 5 minutes
    setTimeout(() => clearInterval(pollInterval), 300000);
  }

  async function applyUpload(uploadId: string): Promise<boolean> {
    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE}/api/uploads/${uploadId}/apply`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          upload_id: uploadId,
          confirm: true,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to apply upload');
      }

      // Update status
      await fetchUploadStatus(uploadId);
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to apply upload';
      uploadError.value = message;
      console.error('Apply error:', error);
      return false;
    }
  }

  function setCurrentUpload(uploadId: string | null): void {
    currentUploadId.value = uploadId;
  }

  function clearError(): void {
    uploadError.value = null;
  }

  return {
    // State
    uploads,
    currentUploadId,
    isUploading,
    uploadError,
    // Computed
    currentUpload,
    uploadsList,
    // Actions
    initiateUpload,
    fetchUploadStatus,
    applyUpload,
    setCurrentUpload,
    clearError,
  };
});

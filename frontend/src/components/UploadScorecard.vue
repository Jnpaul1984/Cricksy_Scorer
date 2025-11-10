<template>
  <div class="upload-scorecard">
    <h2>Upload Scorecard</h2>

    <div v-if="!uploadStore.isUploading && !uploadStore.currentUploadId" class="upload-form">
      <div class="file-input-container">
        <label for="file-input" class="file-label">
          <input
            id="file-input"
            type="file"
            accept="image/jpeg,image/png,image/jpg,application/pdf"
            @change="handleFileSelect"
            class="file-input"
          />
          <span class="file-button">Choose File</span>
          <span v-if="selectedFile" class="file-name">{{ selectedFile.name }}</span>
          <span v-else class="file-placeholder">No file chosen</span>
        </label>
      </div>

      <div v-if="selectedFile" class="file-info">
        <p><strong>File:</strong> {{ selectedFile.name }}</p>
        <p><strong>Size:</strong> {{ formatFileSize(selectedFile.size) }}</p>
        <p><strong>Type:</strong> {{ selectedFile.type }}</p>
      </div>

      <div v-if="gameId" class="game-info">
        <p><strong>Game ID:</strong> {{ gameId }}</p>
      </div>

      <button
        v-if="selectedFile"
        @click="handleUpload"
        :disabled="!selectedFile"
        class="upload-button"
      >
        Upload & Process
      </button>
    </div>

    <div v-if="uploadStore.isUploading" class="upload-progress">
      <h3>Uploading...</h3>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${uploadStore.uploadProgress}%` }"></div>
      </div>
      <p>{{ uploadStore.uploadProgress }}% complete</p>
    </div>

    <div v-if="uploadStore.currentUpload && !uploadStore.isUploading" class="upload-status">
      <h3>Upload Status</h3>
      <div class="status-card">
        <div class="status-row">
          <span class="label">Status:</span>
          <span :class="['status-badge', uploadStore.currentUpload.status]">
            {{ uploadStore.currentUpload.status }}
          </span>
        </div>
        <div class="status-row">
          <span class="label">File:</span>
          <span>{{ uploadStore.currentUpload.filename }}</span>
        </div>
        <div class="status-row">
          <span class="label">Upload ID:</span>
          <span class="mono">{{ uploadStore.currentUpload.upload_id }}</span>
        </div>

        <div v-if="uploadStore.currentUpload.status === 'processing'" class="processing-info">
          <p>🔄 Processing with OCR... This may take a moment.</p>
          <button @click="pollStatus" class="secondary-button">Check Status</button>
        </div>

        <div v-if="uploadStore.currentUpload.status === 'parsed'" class="parsed-info">
          <p>✅ Processing complete! Ready for review.</p>
          <router-link :to="`/upload-review/${uploadStore.currentUpload.upload_id}`" class="review-button">
            Review & Apply
          </router-link>
        </div>

        <div v-if="uploadStore.currentUpload.status === 'failed'" class="error-info">
          <p>❌ Processing failed</p>
          <p class="error-message">{{ uploadStore.currentUpload.error_message }}</p>
        </div>

        <div v-if="uploadStore.currentUpload.status === 'applied'" class="applied-info">
          <p>✅ Data successfully applied to game!</p>
        </div>
      </div>

      <button @click="startNewUpload" class="secondary-button">New Upload</button>
    </div>

    <div v-if="error" class="error-alert">
      <p>{{ error }}</p>
      <button @click="error = null">Dismiss</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useUploadStore } from '@/stores/uploadStore'

const props = defineProps<{
  gameId?: string
}>()

const uploadStore = useUploadStore()
const selectedFile = ref<File | null>(null)
const error = ref<string | null>(null)

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    selectedFile.value = target.files[0]
    error.value = null
  }
}

async function handleUpload() {
  if (!selectedFile.value) {
    error.value = 'Please select a file'
    return
  }

  try {
    const uploadId = await uploadStore.initiateUpload(
      selectedFile.value,
      props.gameId || null
    )

    // Start polling for status
    pollStatus()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Upload failed'
  }
}

async function pollStatus() {
  if (!uploadStore.currentUploadId) return

  try {
    await uploadStore.pollUploadStatus(uploadStore.currentUploadId)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to check status'
  }
}

function startNewUpload() {
  uploadStore.clearCurrentUpload()
  selectedFile.value = null
  error.value = null
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

onMounted(() => {
  // Clear any previous upload state
  if (!uploadStore.currentUploadId) {
    uploadStore.clearCurrentUpload()
  }
})
</script>

<style scoped>
.upload-scorecard {
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem;
}

.upload-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.file-input-container {
  margin: 1rem 0;
}

.file-label {
  display: flex;
  align-items: center;
  gap: 1rem;
  cursor: pointer;
}

.file-input {
  display: none;
}

.file-button {
  padding: 0.75rem 1.5rem;
  background: var(--primary-color, #007bff);
  color: white;
  border-radius: 4px;
  font-weight: 500;
  transition: background 0.2s;
}

.file-button:hover {
  background: var(--primary-hover, #0056b3);
}

.file-name {
  font-weight: 500;
}

.file-placeholder {
  color: #6c757d;
}

.file-info,
.game-info {
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 4px;
}

.file-info p,
.game-info p {
  margin: 0.5rem 0;
}

.upload-button,
.review-button,
.secondary-button {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-button,
.review-button {
  background: var(--primary-color, #007bff);
  color: white;
}

.upload-button:hover,
.review-button:hover {
  background: var(--primary-hover, #0056b3);
}

.upload-button:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.secondary-button {
  background: #6c757d;
  color: white;
}

.secondary-button:hover {
  background: #5a6268;
}

.upload-progress {
  text-align: center;
}

.progress-bar {
  width: 100%;
  height: 24px;
  background: #e9ecef;
  border-radius: 12px;
  overflow: hidden;
  margin: 1rem 0;
}

.progress-fill {
  height: 100%;
  background: var(--primary-color, #007bff);
  transition: width 0.3s ease;
}

.upload-status {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.status-card {
  padding: 1.5rem;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 0.75rem 0;
}

.label {
  font-weight: 600;
  color: #495057;
}

.mono {
  font-family: monospace;
  font-size: 0.9em;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-weight: 500;
  font-size: 0.875rem;
}

.status-badge.initiated,
.status-badge.uploaded {
  background: #e7f3ff;
  color: #004085;
}

.status-badge.processing {
  background: #fff3cd;
  color: #856404;
}

.status-badge.parsed {
  background: #d4edda;
  color: #155724;
}

.status-badge.applied {
  background: #d1ecf1;
  color: #0c5460;
}

.status-badge.failed {
  background: #f8d7da;
  color: #721c24;
}

.processing-info,
.parsed-info,
.error-info,
.applied-info {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 4px;
}

.processing-info {
  background: #fff3cd;
}

.parsed-info {
  background: #d4edda;
}

.error-info {
  background: #f8d7da;
}

.applied-info {
  background: #d1ecf1;
}

.error-message {
  margin-top: 0.5rem;
  color: #721c24;
  font-family: monospace;
  font-size: 0.9em;
}

.error-alert {
  margin-top: 1rem;
  padding: 1rem;
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  color: #721c24;
}

.error-alert button {
  margin-top: 0.5rem;
  padding: 0.5rem 1rem;
  background: #721c24;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style>

<template>
  <div class="upload-scorecard">
    <h2>Upload Scorecard</h2>
    
    <div v-if="error" class="error-message" role="alert">
      <strong>Error:</strong> {{ error }}
      <button @click="clearError" aria-label="Close error">×</button>
    </div>

    <div v-if="!uploadId" class="upload-form">
      <p>Upload a photo, PDF, or video of your scorecard for automatic data extraction.</p>
      
      <div class="file-input-container">
        <label for="file-input" class="file-label">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
          </svg>
          <span>{{ selectedFile ? selectedFile.name : 'Choose File' }}</span>
        </label>
        <input
          id="file-input"
          ref="fileInputRef"
          type="file"
          accept="image/*,.pdf"
          @change="onFileSelected"
          :disabled="isUploading"
        />
      </div>

      <div v-if="selectedFile" class="file-info">
        <p><strong>File:</strong> {{ selectedFile.name }}</p>
        <p><strong>Size:</strong> {{ formatFileSize(selectedFile.size) }}</p>
        <p><strong>Type:</strong> {{ selectedFile.type }}</p>
      </div>

      <div class="form-group">
        <label for="game-id-input">Game ID (optional)</label>
        <input
          id="game-id-input"
          v-model="gameId"
          type="text"
          placeholder="Enter game ID to associate with"
          :disabled="isUploading"
        />
      </div>

      <button
        class="upload-button"
        @click="handleUpload"
        :disabled="!selectedFile || isUploading"
      >
        {{ isUploading ? 'Uploading...' : 'Upload & Process' }}
      </button>

      <div v-if="isUploading" class="progress-container">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
        </div>
        <p class="progress-text">{{ uploadProgress }}% uploaded</p>
      </div>
    </div>

    <div v-if="uploadId && !isProcessingComplete" class="processing-status">
      <div class="spinner"></div>
      <h3>Processing Upload...</h3>
      <p>Please wait while we extract the scorecard data.</p>
      <p class="status-detail">Upload ID: {{ uploadId }}</p>
      <p class="status-detail">Status: {{ currentStatus }}</p>
    </div>

    <div v-if="isProcessingComplete && currentUpload" class="processing-complete">
      <div v-if="isFailed" class="error-box">
        <h3>Processing Failed</h3>
        <p>Unable to process the uploaded file. Please try again or upload a different file.</p>
        <button @click="reset">Upload Another File</button>
      </div>

      <div v-if="isReady" class="success-box">
        <h3>Processing Complete!</h3>
        <p>Found {{ deliveriesCount }} deliveries</p>
        <button @click="goToReview" class="primary-button">
          Review & Apply
        </button>
        <button @click="reset" class="secondary-button">
          Upload Another File
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUploadStore } from '@/stores/uploadStore'

const router = useRouter()
const uploadStore = useUploadStore()

// Refs
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const gameId = ref<string>('')
const uploadId = ref<string>('')
const pollInterval = ref<number | null>(null)

// Computed
const error = computed(() => uploadStore.error)
const isUploading = computed(() => uploadStore.isUploading)
const uploadProgress = computed(() => uploadStore.uploadProgress)
const currentUpload = computed(() => uploadStore.currentUpload)
const currentStatus = computed(() => currentUpload.value?.status || 'unknown')
const isProcessingComplete = computed(() => 
  currentStatus.value === 'ready' || currentStatus.value === 'failed'
)
const isReady = computed(() => uploadStore.isReady)
const isFailed = computed(() => uploadStore.isFailed)
const deliveriesCount = computed(() => 
  currentUpload.value?.parsed_preview?.deliveries?.length || 0
)

// Methods
function onFileSelected(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files[0]) {
    selectedFile.value = target.files[0]
  }
}

async function handleUpload() {
  if (!selectedFile.value) return

  try {
    uploadId.value = await uploadStore.uploadFile(
      selectedFile.value,
      gameId.value || null
    )

    // Start polling for status
    startPolling()
  } catch (err) {
    console.error('Upload failed:', err)
  }
}

function startPolling() {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
  }

  pollInterval.value = window.setInterval(async () => {
    if (!uploadId.value) return

    try {
      await uploadStore.getUploadStatus(uploadId.value)

      // Stop polling if processing is complete
      if (isProcessingComplete.value) {
        stopPolling()
      }
    } catch (err) {
      console.error('Failed to poll status:', err)
    }
  }, 2000)
}

function stopPolling() {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
    pollInterval.value = null
  }
}

function clearError() {
  uploadStore.clearError()
}

function reset() {
  uploadStore.reset()
  selectedFile.value = null
  gameId.value = ''
  uploadId.value = ''
  stopPolling()
}

function goToReview() {
  if (uploadId.value) {
    router.push({
      name: 'upload-review',
      params: { uploadId: uploadId.value }
    })
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// Lifecycle
onMounted(() => {
  uploadStore.reset()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.upload-scorecard {
  max-width: 600px;
  margin: 2rem auto;
  padding: 2rem;
}

.error-message {
  background-color: #fee;
  border: 1px solid #fcc;
  padding: 1rem;
  margin-bottom: 1rem;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.error-message button {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0 0.5rem;
}

.upload-form {
  background: var(--pico-background-color, #fff);
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.file-input-container {
  margin: 1.5rem 0;
}

.file-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: var(--pico-primary-background, #0066cc);
  color: white;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.file-label:hover {
  background: var(--pico-primary-hover, #0052a3);
}

#file-input {
  display: none;
}

.file-info {
  margin: 1rem 0;
  padding: 1rem;
  background: #f5f5f5;
  border-radius: 4px;
}

.form-group {
  margin: 1rem 0;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.form-group input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.upload-button {
  width: 100%;
  padding: 1rem;
  background: var(--pico-primary-background, #0066cc);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}

.upload-button:hover:not(:disabled) {
  background: var(--pico-primary-hover, #0052a3);
}

.upload-button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.progress-container {
  margin-top: 1rem;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background: #e0e0e0;
  border-radius: 10px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--pico-primary-background, #0066cc);
  transition: width 0.3s ease;
}

.progress-text {
  text-align: center;
  margin-top: 0.5rem;
  font-weight: 600;
}

.processing-status,
.processing-complete {
  text-align: center;
  padding: 2rem;
}

.spinner {
  width: 50px;
  height: 50px;
  margin: 0 auto 1rem;
  border: 4px solid #f3f3f3;
  border-top: 4px solid var(--pico-primary-background, #0066cc);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.status-detail {
  color: #666;
  font-size: 0.9rem;
}

.error-box,
.success-box {
  padding: 2rem;
  border-radius: 8px;
  margin-top: 1rem;
}

.error-box {
  background: #fee;
  border: 2px solid #fcc;
}

.success-box {
  background: #efe;
  border: 2px solid #cfc;
}

.primary-button,
.secondary-button {
  margin: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.primary-button {
  background: var(--pico-primary-background, #0066cc);
  color: white;
}

.primary-button:hover {
  background: var(--pico-primary-hover, #0052a3);
}

.secondary-button {
  background: #666;
  color: white;
}

.secondary-button:hover {
  background: #555;
}
</style>

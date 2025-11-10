<template>
  <div class="upload-scorecard">
    <h2>Upload Scorecard</h2>

    <!-- File Selection -->
    <div v-if="!uploadStarted" class="upload-section">
      <div class="file-input-wrapper">
        <input
          type="file"
          ref="fileInput"
          @change="handleFileSelect"
          accept="image/*,application/pdf"
          :disabled="isUploading"
        />
        <button
          v-if="!selectedFile"
          @click="triggerFileInput"
          class="button button-primary"
          :disabled="isUploading"
        >
          Choose File
        </button>
      </div>

      <div v-if="selectedFile" class="file-info">
        <p><strong>Selected:</strong> {{ selectedFile.name }}</p>
        <p><strong>Size:</strong> {{ formatFileSize(selectedFile.size) }}</p>
        <p><strong>Type:</strong> {{ selectedFile.type }}</p>

        <div class="actions">
          <button
            @click="startUpload"
            class="button button-primary"
            :disabled="isUploading"
          >
            {{ isUploading ? 'Uploading...' : 'Upload' }}
          </button>
          <button
            @click="clearSelection"
            class="button button-secondary"
            :disabled="isUploading"
          >
            Clear
          </button>
        </div>
      </div>

      <!-- Consent Checkbox -->
      <div v-if="selectedFile" class="consent-section">
        <label class="consent-label">
          <input type="checkbox" v-model="consentGiven" />
          <span>
            I confirm that I have the right to upload this scorecard and have obtained necessary consent.
            <a href="/docs/AI_ETHICS.md" target="_blank">Learn more</a>
          </span>
        </label>
      </div>
    </div>

    <!-- Upload Progress -->
    <div v-if="isUploading" class="progress-section">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${uploadProgress}%` }"></div>
      </div>
      <p>{{ uploadProgress }}% complete</p>
    </div>

    <!-- Processing Status -->
    <div v-if="uploadComplete && !isReady && !hasFailed" class="processing-section">
      <div class="spinner"></div>
      <p>Processing scorecard with OCR...</p>
      <p class="status-text">Status: {{ currentUpload?.status }}</p>
    </div>

    <!-- Error Display -->
    <div v-if="error" class="error-section">
      <p class="error-message">{{ error }}</p>
      <button @click="clearError" class="button button-secondary">Dismiss</button>
    </div>

    <!-- Success -->
    <div v-if="isReady" class="success-section">
      <p class="success-message">✓ Scorecard processed successfully!</p>
      <button @click="navigateToReview" class="button button-primary">
        Review Results
      </button>
    </div>

    <!-- Failure -->
    <div v-if="hasFailed" class="failure-section">
      <p class="error-message">Processing failed: {{ currentUpload?.error_message }}</p>
      <button @click="reset" class="button button-secondary">Try Again</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUploadStore } from '../stores/uploadStore'

const props = defineProps<{
  gameId?: number
  uploaderId: string
}>()

const router = useRouter()
const uploadStore = useUploadStore()

// Local state
const fileInput = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const consentGiven = ref(false)
const uploadStarted = ref(false)
const uploadComplete = ref(false)

// Computed
const { isUploading, uploadProgress, error, currentUpload, isReady, hasFailed } = uploadStore
const canUpload = computed(() => selectedFile.value && consentGiven.value && !isUploading)

// Methods
function triggerFileInput() {
  fileInput.value?.click()
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    selectedFile.value = file
  }
}

function clearSelection() {
  selectedFile.value = null
  consentGiven.value = false
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

async function startUpload() {
  if (!selectedFile.value || !canUpload.value) return

  uploadStarted.value = true

  try {
    const uploadId = await uploadStore.uploadAndProcess(
      selectedFile.value,
      props.uploaderId,
      props.gameId
    )

    uploadComplete.value = true

    // Poll for processing completion
    await uploadStore.pollUploadStatus(uploadId)
  } catch (err) {
    console.error('Upload failed:', err)
    // Error is handled by the store
  }
}

function navigateToReview() {
  if (uploadStore.currentUploadId) {
    router.push(`/upload-review/${uploadStore.currentUploadId}`)
  }
}

function reset() {
  uploadStore.resetCurrentUpload()
  uploadStarted.value = false
  uploadComplete.value = false
  clearSelection()
}

function clearError() {
  uploadStore.clearError()
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}
</script>

<style scoped>
.upload-scorecard {
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem;
}

h2 {
  margin-bottom: 1.5rem;
}

.upload-section {
  margin-bottom: 2rem;
}

.file-input-wrapper input[type="file"] {
  display: none;
}

.file-info {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--pico-card-background-color);
  border-radius: 8px;
}

.file-info p {
  margin: 0.5rem 0;
}

.actions {
  margin-top: 1rem;
  display: flex;
  gap: 1rem;
}

.consent-section {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--pico-card-background-color);
  border-radius: 8px;
}

.consent-label {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  cursor: pointer;
}

.consent-label input[type="checkbox"] {
  margin-top: 0.25rem;
}

.progress-section {
  margin: 2rem 0;
}

.progress-bar {
  width: 100%;
  height: 30px;
  background: var(--pico-muted-border-color);
  border-radius: 15px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--pico-primary);
  transition: width 0.3s ease;
}

.processing-section {
  text-align: center;
  padding: 2rem;
}

.spinner {
  width: 50px;
  height: 50px;
  margin: 0 auto 1rem;
  border: 4px solid var(--pico-muted-border-color);
  border-top-color: var(--pico-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.status-text {
  color: var(--pico-muted-color);
  font-size: 0.9rem;
}

.error-section,
.failure-section {
  padding: 1rem;
  background: var(--pico-del-background-color);
  border-radius: 8px;
  margin: 1rem 0;
}

.error-message {
  color: var(--pico-del-color);
  margin-bottom: 1rem;
}

.success-section {
  padding: 1rem;
  background: var(--pico-ins-background-color);
  border-radius: 8px;
  text-align: center;
  margin: 1rem 0;
}

.success-message {
  color: var(--pico-ins-color);
  font-size: 1.2rem;
  margin-bottom: 1rem;
}

button {
  cursor: pointer;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>

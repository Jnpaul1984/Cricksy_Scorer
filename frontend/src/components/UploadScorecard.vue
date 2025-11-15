<template>
  <div class="upload-scorecard">
    <h2>Upload Scorecard</h2>

    <div class="consent-notice">
      <h3>Before uploading</h3>
      <p>
        By uploading a file, you confirm that:
      </p>
      <ul>
        <li>You have the right to upload this scorecard</li>
        <li>The file will be processed using AI/OCR technology</li>
        <li>Extracted data will require your verification before use</li>
        <li>Files are stored securely and can be deleted upon request</li>
      </ul>
      <p class="small">
        See our <a href="/docs/AI_ETHICS.md" target="_blank">AI Ethics &amp; Privacy Policy</a> for details.
      </p>
    </div>

    <form @submit.prevent="handleUpload" class="upload-form">
      <div class="form-group">
        <label for="uploader-name">Your Name (optional)</label>
        <input
          id="uploader-name"
          v-model="uploaderName"
          type="text"
          placeholder="e.g., John Smith"
          maxlength="255"
        />
      </div>

      <div class="form-group">
        <label for="file-input">Select Scorecard Image</label>
        <input
          id="file-input"
          ref="fileInput"
          type="file"
          accept="image/*,.pdf"
          required
          @change="handleFileSelect"
        />
        <p class="help-text">
          Supported formats: JPG, PNG, PDF (max 10 MB)
        </p>
      </div>

      <div v-if="selectedFile" class="file-preview">
        <strong>Selected file:</strong> {{ selectedFile.name }}
        ({{ formatFileSize(selectedFile.size) }})
      </div>

      <div class="form-actions">
        <button
          type="submit"
          :disabled="!selectedFile || isUploading"
          class="btn btn-primary"
        >
          {{ isUploading ? 'Uploading...' : 'Upload Scorecard' }}
        </button>
        <button
          type="button"
          @click="resetForm"
          :disabled="isUploading"
          class="btn btn-secondary"
        >
          Clear
        </button>
      </div>
    </form>

    <div v-if="uploadProgress.size > 0" class="upload-progress-list">
      <h3>Upload Progress</h3>
      <div
        v-for="[uploadId, progress] in uploadProgress"
        :key="uploadId"
        class="progress-item"
      >
        <div class="progress-info">
          <span class="stage-badge" :class="progress.stage">
            {{ progress.stage }}
          </span>
          <span class="message">{{ progress.message }}</span>
        </div>
        <div class="progress-bar">
          <div
            class="progress-fill"
            :style="{ width: progress.progress + '%' }"
            :class="{ error: progress.stage === 'error' }"
          ></div>
        </div>
      </div>
    </div>

    <div v-if="error" class="error-message" role="alert">
      {{ error }}
      <button @click="clearError" class="close-btn">×</button>
    </div>

    <div v-if="recentUploads.length > 0" class="recent-uploads">
      <h3>Recent Uploads</h3>
      <ul>
        <li v-for="upload in recentUploads" :key="upload.upload_id">
          <router-link :to="`/uploads/${upload.upload_id}`">
            {{ upload.filename }}
            <span class="status-badge" :class="upload.status">
              {{ upload.status }}
            </span>
          </router-link>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUploadStore } from '@/stores/uploadStore'
import { storeToRefs } from 'pinia'

const router = useRouter()
const uploadStore = useUploadStore()
const { uploadProgress, isUploading, error, recentUploads } = storeToRefs(uploadStore)

const uploaderName = ref('')
const selectedFile = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    selectedFile.value = target.files[0]
  }
}

async function handleUpload() {
  if (!selectedFile.value) return

  try {
    const uploadId = await uploadStore.initiateUpload(
      selectedFile.value,
      uploaderName.value || undefined
    )

    // Navigate to upload review page
    router.push(`/uploads/${uploadId}`)
  } catch (err) {
    console.error('Upload failed:', err)
  }
}

function resetForm() {
  selectedFile.value = null
  uploaderName.value = ''
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function clearError() {
  uploadStore.clearError()
}
</script>

<style scoped>
.upload-scorecard {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
}

.consent-notice {
  background: var(--pico-background-color);
  border: 1px solid var(--pico-muted-border-color);
  border-radius: var(--pico-border-radius);
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.consent-notice h3 {
  margin-top: 0;
  font-size: 1.1rem;
}

.consent-notice ul {
  margin: 1rem 0;
}

.consent-notice .small {
  font-size: 0.9rem;
  color: var(--pico-muted-color);
}

.upload-form {
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.help-text {
  font-size: 0.9rem;
  color: var(--pico-muted-color);
  margin-top: 0.5rem;
}

.file-preview {
  background: var(--pico-secondary-background);
  padding: 1rem;
  border-radius: var(--pico-border-radius);
  margin-bottom: 1rem;
}

.form-actions {
  display: flex;
  gap: 1rem;
}

.upload-progress-list {
  margin-bottom: 2rem;
}

.progress-item {
  margin-bottom: 1rem;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.stage-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
}

.stage-badge.uploading {
  background: var(--pico-primary-background);
  color: var(--pico-primary);
}

.stage-badge.processing {
  background: var(--pico-secondary-background);
  color: var(--pico-secondary);
}

.stage-badge.complete {
  background: #d4edda;
  color: #155724;
}

.stage-badge.error {
  background: #f8d7da;
  color: #721c24;
}

.progress-bar {
  height: 8px;
  background: var(--pico-muted-border-color);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--pico-primary);
  transition: width 0.3s ease;
}

.progress-fill.error {
  background: var(--pico-del-color);
}

.error-message {
  background: #f8d7da;
  color: #721c24;
  padding: 1rem;
  border-radius: var(--pico-border-radius);
  margin-bottom: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  width: 2rem;
  height: 2rem;
}

.recent-uploads ul {
  list-style: none;
  padding: 0;
}

.recent-uploads li {
  margin-bottom: 0.5rem;
}

.status-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  margin-left: 0.5rem;
}

.status-badge.pending {
  background: var(--pico-secondary-background);
}

.status-badge.uploaded,
.status-badge.processing {
  background: var(--pico-primary-background);
}

.status-badge.parsed {
  background: #d4edda;
  color: #155724;
}

.status-badge.applied {
  background: #cce5ff;
  color: #004085;
}

.status-badge.failed,
.status-badge.rejected {
  background: #f8d7da;
  color: #721c24;
}
</style>

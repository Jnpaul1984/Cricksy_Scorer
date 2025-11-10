<template>
  <article class="upload-scorecard">
    <header>
      <h2>Upload Scorecard</h2>
      <p>Upload a scorecard image for OCR processing and review</p>
    </header>

    <div class="upload-area">
      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        @change="handleFileSelect"
        :disabled="uploadStore.isUploading"
        class="file-input"
      />

      <button
        @click="triggerFileSelect"
        :disabled="uploadStore.isUploading"
        class="upload-button"
      >
        {{ uploadStore.isUploading ? 'Uploading...' : 'Choose File' }}
      </button>

      <p v-if="selectedFile" class="file-info">
        Selected: {{ selectedFile.name }} ({{ formatFileSize(selectedFile.size) }})
      </p>
    </div>

    <div v-if="uploadStore.uploadError" class="error-message" role="alert">
      <strong>Error:</strong> {{ uploadStore.uploadError }}
      <button @click="uploadStore.clearError" class="close-button">×</button>
    </div>

    <div v-if="uploadStore.currentUpload" class="upload-status">
      <h3>Upload Status</h3>
      <div class="status-info">
        <p>
          <strong>File:</strong> {{ uploadStore.currentUpload.filename }}
        </p>
        <p>
          <strong>Status:</strong>
          <span :class="`status-${uploadStore.currentUpload.status}`">
            {{ formatStatus(uploadStore.currentUpload.status) }}
          </span>
        </p>
        <div v-if="uploadStore.currentUpload.status === 'processing'" class="progress">
          <div class="progress-bar" aria-busy="true"></div>
          <p>Processing with OCR, please wait...</p>
        </div>
      </div>

      <div v-if="uploadStore.currentUpload.status === 'completed'" class="completed-actions">
        <p class="success-message">✓ Processing completed! Review the results below.</p>
        <router-link
          :to="`/upload-review/${uploadStore.currentUpload.upload_id}`"
          class="review-button"
        >
          Review & Apply
        </router-link>
      </div>

      <div v-if="uploadStore.currentUpload.status === 'failed'" class="error-info">
        <p>
          <strong>Error:</strong> {{ uploadStore.currentUpload.error_message }}
        </p>
      </div>
    </div>

    <footer>
      <small>
        Supported formats: JPG, PNG, WEBP. Max file size: 10MB.
        <br />
        OCR results require manual review before applying to the ledger.
      </small>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useUploadStore } from '@/stores/uploadStore';

const uploadStore = useUploadStore();
const fileInput = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);

function triggerFileSelect() {
  fileInput.value?.click();
}

async function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];

  if (!file) return;

  // Validate file size (10MB max)
  if (file.size > 10 * 1024 * 1024) {
    alert('File size must be less than 10MB');
    return;
  }

  // Validate file type
  if (!file.type.startsWith('image/')) {
    alert('Please select an image file');
    return;
  }

  selectedFile.value = file;

  // Initiate upload
  const uploadId = await uploadStore.initiateUpload(file);

  if (uploadId) {
    console.log('Upload initiated:', uploadId);
  }

  // Reset file input
  if (fileInput.value) {
    fileInput.value.value = '';
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatStatus(status: string): string {
  const statusMap: Record<string, string> = {
    pending: 'Pending',
    uploaded: 'Uploaded',
    processing: 'Processing',
    completed: 'Completed',
    failed: 'Failed',
    applied: 'Applied',
  };
  return statusMap[status] || status;
}
</script>

<style scoped>
.upload-scorecard {
  max-width: 600px;
  margin: 2rem auto;
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
  border: 2px dashed var(--primary);
  border-radius: 8px;
  background: var(--card-background-color);
}

.file-input {
  display: none;
}

.upload-button {
  padding: 0.75rem 2rem;
  font-size: 1.1rem;
  cursor: pointer;
}

.upload-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.file-info {
  margin: 0;
  font-size: 0.9rem;
  color: var(--muted-color);
}

.error-message {
  margin: 1rem 0;
  padding: 1rem;
  background: var(--del-background-color);
  border-left: 4px solid var(--del-color);
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0 0.5rem;
}

.upload-status {
  margin-top: 2rem;
  padding: 1rem;
  background: var(--card-background-color);
  border-radius: 8px;
}

.status-info p {
  margin: 0.5rem 0;
}

.status-pending,
.status-uploaded {
  color: var(--primary);
}

.status-processing {
  color: var(--primary);
  font-weight: bold;
}

.status-completed {
  color: var(--ins-color);
  font-weight: bold;
}

.status-failed {
  color: var(--del-color);
  font-weight: bold;
}

.status-applied {
  color: var(--ins-color);
  font-weight: bold;
}

.progress {
  margin: 1rem 0;
}

.progress-bar {
  height: 4px;
  background: linear-gradient(90deg, var(--primary) 0%, var(--primary) 50%, transparent 50%);
  background-size: 200% 100%;
  animation: progress 1.5s infinite;
}

@keyframes progress {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.completed-actions {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--muted-border-color);
}

.success-message {
  color: var(--ins-color);
  font-weight: bold;
  margin-bottom: 1rem;
}

.review-button {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: var(--primary);
  color: white;
  text-decoration: none;
  border-radius: 4px;
  font-weight: bold;
}

.review-button:hover {
  background: var(--primary-hover);
}

.error-info {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--del-background-color);
  border-left: 4px solid var(--del-color);
  border-radius: 4px;
}
</style>

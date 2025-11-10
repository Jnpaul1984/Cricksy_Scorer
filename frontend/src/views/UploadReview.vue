<template>
  <article class="upload-review">
    <header>
      <h1>Review Uploaded Scorecard</h1>
      <p>Review the OCR results and apply to the delivery ledger</p>
    </header>

    <div v-if="loading" class="loading" aria-busy="true">
      <p>Loading upload details...</p>
    </div>

    <div v-else-if="error" class="error-message" role="alert">
      <strong>Error:</strong> {{ error }}
      <router-link to="/">Back to Home</router-link>
    </div>

    <div v-else-if="upload" class="review-content">
      <!-- Upload Info -->
      <section class="upload-info">
        <h2>Upload Information</h2>
        <dl>
          <dt>Filename:</dt>
          <dd>{{ upload.filename }}</dd>
          <dt>Status:</dt>
          <dd>
            <span :class="`status-${upload.status}`">
              {{ formatStatus(upload.status) }}
            </span>
          </dd>
          <dt>Uploaded:</dt>
          <dd>{{ formatDate(upload.uploaded_at) }}</dd>
          <dt>Processed:</dt>
          <dd>{{ formatDate(upload.processed_at) }}</dd>
        </dl>
      </section>

      <!-- Parsed Preview -->
      <section v-if="upload.parsed_preview" class="parsed-preview">
        <h2>OCR Results</h2>

        <div class="confidence-indicator">
          <strong>Confidence:</strong>
          <span :class="`confidence-${upload.parsed_preview.confidence}`">
            {{ upload.parsed_preview.confidence.toUpperCase() }}
          </span>
        </div>

        <div v-if="upload.parsed_preview.validation_error" class="validation-error">
          <strong>⚠ Validation Warning:</strong>
          {{ upload.parsed_preview.validation_error }}
        </div>

        <!-- Teams -->
        <div v-if="upload.parsed_preview.teams" class="teams-info">
          <h3>Teams</h3>
          <p>
            <strong>Team A:</strong> {{ upload.parsed_preview.teams.team_a || 'Unknown' }}
          </p>
          <p>
            <strong>Team B:</strong> {{ upload.parsed_preview.teams.team_b || 'Unknown' }}
          </p>
        </div>

        <!-- Score Summary -->
        <div class="score-summary">
          <h3>Score Summary</h3>
          <p class="total-score">
            {{ upload.parsed_preview.total_runs }}/{{ upload.parsed_preview.total_wickets }}
            <span v-if="upload.parsed_preview.overs">({{ upload.parsed_preview.overs }} overs)</span>
          </p>
        </div>

        <!-- Players -->
        <div v-if="upload.parsed_preview.players && upload.parsed_preview.players.length > 0" class="players-info">
          <h3>Players</h3>
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Runs</th>
                <th>Balls</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(player, index) in upload.parsed_preview.players" :key="index">
                <td>{{ player.name }}</td>
                <td>{{ player.runs }}</td>
                <td>{{ player.balls || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Raw OCR Text (collapsible) -->
        <details class="raw-text">
          <summary>View Raw OCR Text</summary>
          <pre>{{ upload.parsed_preview.raw_text }}</pre>
        </details>
      </section>

      <!-- Actions -->
      <section class="actions">
        <div class="warning-box">
          <strong>⚠ Human Verification Required</strong>
          <p>
            OCR results are not 100% accurate. Please review all data carefully before applying.
            Once applied, the data will be added to the delivery ledger.
          </p>
        </div>

        <div class="action-buttons">
          <button
            v-if="upload.status === 'completed'"
            @click="handleApply"
            :disabled="applying"
            class="apply-button"
          >
            {{ applying ? 'Applying...' : 'Confirm & Apply to Ledger' }}
          </button>

          <button
            v-if="upload.status === 'applied'"
            disabled
            class="applied-button"
          >
            ✓ Applied to Ledger
          </button>

          <router-link to="/" class="cancel-button">
            {{ upload.status === 'applied' ? 'Back to Home' : 'Cancel' }}
          </router-link>
        </div>
      </section>
    </div>
  </article>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useUploadStore, type Upload } from '@/stores/uploadStore';

const route = useRoute();
const router = useRouter();
const uploadStore = useUploadStore();

const upload = ref<Upload | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const applying = ref(false);

const uploadId = route.params.uploadId as string;

onMounted(async () => {
  try {
    await uploadStore.fetchUploadStatus(uploadId);
    upload.value = uploadStore.uploads.get(uploadId) || null;

    if (!upload.value) {
      error.value = 'Upload not found';
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load upload';
  } finally {
    loading.value = false;
  }
});

async function handleApply() {
  if (!upload.value) return;

  const confirmed = confirm(
    'Are you sure you want to apply this scorecard to the delivery ledger? ' +
    'Please ensure you have reviewed all OCR results for accuracy.'
  );

  if (!confirmed) return;

  applying.value = true;

  try {
    const success = await uploadStore.applyUpload(uploadId);

    if (success) {
      // Refresh upload data
      await uploadStore.fetchUploadStatus(uploadId);
      upload.value = uploadStore.uploads.get(uploadId) || null;
      alert('Scorecard applied successfully!');
    } else {
      alert('Failed to apply scorecard: ' + uploadStore.uploadError);
    }
  } catch (err) {
    alert('Error applying scorecard: ' + (err instanceof Error ? err.message : 'Unknown error'));
  } finally {
    applying.value = false;
  }
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

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'N/A';
  return new Date(dateStr).toLocaleString();
}
</script>

<style scoped>
.upload-review {
  max-width: 900px;
  margin: 2rem auto;
  padding: 0 1rem;
}

.loading,
.error-message {
  text-align: center;
  padding: 2rem;
}

.review-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.upload-info,
.parsed-preview,
.actions {
  background: var(--card-background-color);
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: var(--card-box-shadow);
}

dl {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 0.5rem 1rem;
  margin: 1rem 0;
}

dt {
  font-weight: bold;
}

dd {
  margin: 0;
}

.status-completed {
  color: var(--ins-color);
  font-weight: bold;
}

.status-applied {
  color: var(--ins-color);
  font-weight: bold;
}

.confidence-indicator {
  margin: 1rem 0;
  padding: 0.75rem;
  background: var(--code-background-color);
  border-radius: 4px;
}

.confidence-very_low,
.confidence-low {
  color: var(--del-color);
  font-weight: bold;
}

.confidence-medium {
  color: orange;
  font-weight: bold;
}

.confidence-high {
  color: var(--ins-color);
  font-weight: bold;
}

.validation-error {
  margin: 1rem 0;
  padding: 1rem;
  background: var(--del-background-color);
  border-left: 4px solid var(--del-color);
  border-radius: 4px;
}

.total-score {
  font-size: 2rem;
  font-weight: bold;
  color: var(--primary);
}

table {
  width: 100%;
  margin: 1rem 0;
}

.raw-text {
  margin-top: 1rem;
}

.raw-text pre {
  max-height: 300px;
  overflow-y: auto;
  background: var(--code-background-color);
  padding: 1rem;
  border-radius: 4px;
  font-size: 0.85rem;
}

.warning-box {
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 4px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.warning-box strong {
  display: block;
  margin-bottom: 0.5rem;
  color: #856404;
}

.action-buttons {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.apply-button {
  background: var(--primary);
  color: white;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
}

.apply-button:hover:not(:disabled) {
  background: var(--primary-hover);
}

.apply-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.applied-button {
  background: var(--ins-color);
  color: white;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  font-weight: bold;
  cursor: not-allowed;
}

.cancel-button {
  padding: 0.75rem 1.5rem;
  border: 1px solid var(--muted-border-color);
  border-radius: 4px;
  text-decoration: none;
  color: var(--color);
  display: inline-block;
}

.cancel-button:hover {
  background: var(--card-background-color);
}
</style>

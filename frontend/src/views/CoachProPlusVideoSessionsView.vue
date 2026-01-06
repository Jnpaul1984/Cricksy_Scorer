<template>
  <div class="coach-pro-plus-video-sessions">
    <!-- Feature Gate: Not Coach (Pro / Pro Plus) -->
    <div v-if="!authStore.isCoach" class="feature-gate">
      <div class="upgrade-card">
        <h2>Unlock Video Sessions</h2>
        <p>
          Manage and analyze video recordings of coaching sessions with AI-powered insights.
          Available with Coach Pro Plus ($24.99/month).
        </p>
        <router-link to="/pricing" class="upgrade-button"> Upgrade to Coach Pro Plus </router-link>
      </div>
    </div>

    <!-- Main Content: Coach Users -->
    <div v-else class="sessions-container">
      <header class="sessions-header">
        <h1>Video Sessions</h1>
        <p class="subtitle">Upload, manage, and analyze coaching session videos</p>
        <button class="btn-primary" @click="showCreateModal = true">+ New Video Session</button>
      </header>

      <!-- Loading State -->
      <div v-if="loading" class="loading">
        <p>Loading sessions...</p>
      </div>

      <!-- Error State -->
      <div v-if="error" class="error-banner">
        <p>{{ error }}</p>
        <button class="btn-close" @click="error = null">Dismiss</button>
      </div>

      <!-- Empty State -->
      <div v-if="!loading && sessions.length === 0" class="empty-state">
        <p>No video sessions yet.</p>
        <p class="hint">Create your first video session to get started.</p>
        <button class="btn-primary" @click="showCreateModal = true">Create Session</button>
      </div>

      <!-- Sessions List -->
      <div v-if="!loading && sessions.length > 0" class="sessions-list">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="session-card"
          @click="selectSession(session.id)"
        >
          <div class="session-header">
            <h3>{{ session.title }}</h3>
            <span :class="['status-badge', `status-${session.status}`]">
              {{ session.status }}
            </span>
          </div>

          <div class="session-meta">
            <p v-if="session.analysis_context">
              <strong>Analysis:</strong> {{ formatAnalysisContext(session.analysis_context) }}
              <span v-if="session.camera_view" class="camera-view">
                ({{ formatCameraView(session.camera_view) }})
              </span>
            </p>
            <p v-if="session.player_ids.length > 0">
              <strong>Players:</strong> {{ session.player_ids.length }}
            </p>
            <p><strong>Created:</strong> {{ formatDate(session.created_at) }}</p>
          </div>

          <div v-if="session.notes" class="session-notes">
            {{ session.notes }}
          </div>

          <div class="session-actions">
            <button class="btn-primary" @click.stop="openUploadModal(session.id)">
              📹 Upload & Analyze
            </button>
            <button class="btn-secondary" @click.stop="editSession(session.id)">Edit</button>
            <button class="btn-danger" @click.stop="deleteSession(session.id)">Delete</button>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="sessions.length > 0" class="pagination">
        <button :disabled="offset === 0" class="btn-pagination" @click="previousPage">
          ← Previous
        </button>
        <span class="page-info">
          Page {{ currentPage }} (showing {{ sessions.length }} sessions)
        </span>
        <button class="btn-pagination" @click="nextPage">Next →</button>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <h2>{{ editingId ? 'Edit' : 'Create' }} Video Session</h2>

        <form @submit.prevent="submitForm">
          <div class="form-group">
            <label for="title">Session Title</label>
            <input
              id="title"
              v-model="formData.title"
              type="text"
              placeholder="e.g., Batting Technique - Session 1"
              required
            />
          </div>

          <div class="form-group">
            <label for="analysis-context">What are we analyzing? <span class="required">*</span></label>
            <select
              id="analysis-context"
              v-model="formData.analysis_context"
              required
            >
              <option value="">Select analysis type...</option>
              <option value="batting">Batting</option>
              <option value="bowling">Bowling</option>
              <option value="wicketkeeping">Wicketkeeping</option>
              <option value="fielding">Fielding</option>
              <option value="mixed">Mixed/General</option>
            </select>
          </div>

          <div class="form-group">
            <label for="camera-view">Camera Angle/View</label>
            <select
              id="camera-view"
              v-model="formData.camera_view"
            >
              <option value="">Select camera angle...</option>
              <option value="side">Side View</option>
              <option value="front">Front View</option>
              <option value="behind">Behind View</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div class="form-group">
            <label for="players">Player IDs (comma-separated)</label>
            <textarea
              id="players"
              v-model="playersText"
              placeholder="player1_id, player2_id"
              rows="3"
            ></textarea>
          </div>

          <div class="form-group">
            <label for="notes">Notes</label>
            <textarea
              id="notes"
              v-model="formData.notes"
              placeholder="Additional notes about this session..."
              rows="4"
            ></textarea>
          </div>

          <div class="modal-actions">
            <button type="submit" class="btn-primary">
              {{ editingId ? 'Save Changes' : 'Create Session' }}
            </button>
            <button type="button" class="btn-secondary" @click="closeModal">Cancel</button>
          </div>
        </form>

        <div class="modal-hint">
          <p>
            <strong>Note:</strong> Video upload is coming soon. For now, you can create sessions and
            add metadata. Video files will be added in the next update.
          </p>
        </div>
      </div>
    </div>

    <!-- Upload Video Modal -->
    <div v-if="showUploadModal" class="modal-overlay" @click="() => closeUploadModal()">
      <div class="modal-content" @click.stop>
        <h2>Upload Video for Analysis</h2>

        <div v-if="videoStore.uploading" class="upload-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: videoStore.uploadProgress + '%' }"></div>
          </div>
          <p class="progress-text">
            {{ videoStore.uploadProgress }}% - {{ videoStore.uploading.status }}
          </p>
        </div>

        <form v-else @submit.prevent="handleVideoUpload">
          <div class="form-group">
            <label for="video-file">Select Video File</label>
            <input
              id="video-file"
              ref="fileInput"
              type="file"
              accept="video/mp4,video/quicktime,video/x-msvideo"
              required
              @change="onFileSelected"
            />
            <p class="file-hint">Supported: MP4, MOV, AVI (max 500MB)</p>
            <p v-if="selectedFile" class="file-selected">
              ✓ Selected: {{ selectedFile.name }} ({{
                (selectedFile.size / 1024 / 1024).toFixed(1)
              }}MB)
            </p>
          </div>

          <div class="form-group">
            <label for="sample-fps">Sample FPS (frames per second)</label>
            <input
              id="sample-fps"
              v-model.number="uploadSettings.sampleFps"
              type="number"
              min="1"
              max="30"
              value="10"
            />
            <p class="setting-hint">
              Higher = more detailed analysis but slower processing (10 recommended)
            </p>
          </div>

          <div class="form-group checkbox">
            <label>
              <input v-model="uploadSettings.includeFrames" type="checkbox" />
              Include frame data in results
            </label>
            <p class="setting-hint">Stores individual frame analysis (increases storage)</p>
          </div>

          <div class="modal-actions">
            <button type="submit" class="btn-primary" :disabled="!selectedFile">
              🚀 Upload & Analyze
            </button>
            <button type="button" class="btn-secondary" @click="() => closeUploadModal()">Cancel</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Session History Modal -->
    <div v-if="showHistoryModal && selectedSession" class="modal-overlay" @click="closeHistoryModal">
      <div class="modal-content" @click.stop>
        <button class="modal-close-btn" @click="closeHistoryModal">✕</button>
        
        <h2>{{ selectedSession.title }} - Analysis History</h2>
        
        <div v-if="loadingHistory" class="loading">
          <p>Loading analysis history...</p>
        </div>

        <div v-else-if="analysisHistory.length === 0" class="empty-state">
          <p>No analysis jobs yet for this session.</p>
          <button class="btn-primary" @click="closeHistoryModalAndUpload">Upload & Analyze Video</button>
        </div>

        <div v-else class="history-list">
          <table class="history-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="job in analysisHistory" :key="job.id">
                <td>{{ formatDate(job.created_at) }}</td>
                <td>
                  <span :class="['status-badge', `status-${job.status}`]">
                    {{ job.status }}
                  </span>
                </td>
                <td class="history-actions">
                  <button 
                    class="btn-small btn-primary" 
                    @click="viewJobResults(job)"
                    :disabled="job.status === 'queued' || job.status === 'processing'"
                  >
                    View
                  </button>
                  <button 
                    v-if="canExport"
                    class="btn-small btn-secondary" 
                    @click="exportJobPdf(job.id)"
                    :disabled="exportingPdf || !isJobCompleted(job)"
                  >
                    {{ exportingPdf ? '...' : 'Export PDF' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="modal-actions">
          <button type="button" class="btn-secondary" @click="closeHistoryModal">Close</button>
        </div>
      </div>
    </div>

    <!-- Results Modal -->
    <div v-if="showResultsModal && selectedJob" class="modal-overlay" @click="closeResultsModal">
      <div class="modal-content modal-large" @click.stop>
        <button class="modal-close-btn" @click="closeResultsModal">✕</button>
        <h2>Analysis Results</h2>
        <div v-if="selectedJob.analysis_context" class="analysis-context-header">
          <span class="context-label">{{ formatAnalysisContext(selectedJob.analysis_context) }}</span>
          <span v-if="selectedJob.camera_view" class="camera-label">
            • {{ formatCameraView(selectedJob.camera_view) }}
          </span>
        </div>

        <!-- Timed out -->
        <div v-if="pollTimedOut" class="results-error">
          <h3>⏱️ Analysis is taking longer than expected</h3>
          <p class="status-text">Status: {{ selectedJob.status }}</p>
          <p class="status-text">You can retry the upload, or close and check back later.</p>
          <div class="modal-actions">
            <button
              type="button"
              class="btn-primary"
              :disabled="!selectedJob.session_id"
              @click="retrySelectedJob"
            >
              Retry
            </button>
          </div>
        </div>

        <!-- Progress UI (only before results are available) -->
        <div
          v-else-if="
            selectedJob.status === 'queued' ||
            selectedJob.status === 'processing' ||
            selectedJob.status === 'quick_running'
          "
          class="results-loading"
        >
          <section class="results-section coach-summary-card">
            <h3>Summary</h3>
            <p class="summary-level">
              Rating: <strong>{{ coachNarrative.summary.rating }}</strong>
            </p>
            <p class="status-text">{{ coachNarrative.summary.confidenceText }}</p>
            <p class="status-text">{{ coachNarrative.summary.coverageText }}</p>
            <p class="status-text">{{ coachNarrative.summary.coachSummaryText }}</p>
          </section>

          <p>⏳ Analysis in progress...</p>
          <p class="status-text">Status: {{ selectedJob.status }}</p>
          <div class="progress-bar" aria-label="Analysis progress">
            <div class="progress-bar-indeterminate" />
          </div>
          <div class="step-labels">
            <span
              v-for="(step, idx) in progressSteps"
              :key="idx"
              class="step-label"
            >
              {{ step }}
            </span>
          </div>
        </div>

        <!-- Failed -->
        <div v-else-if="selectedJob.status === 'failed'" class="results-error">
          <h3>⚠️ Analysis failed</h3>
          <p class="status-text">
            {{ coachNarrative.summary.coachSummaryText }}
          </p>
          <div class="modal-actions">
            <button
              type="button"
              class="btn-primary"
              :disabled="!selectedJob.session_id"
              @click="retrySelectedJob"
            >
              Retry
            </button>
          </div>
        </div>

        <!-- Completed / other states -->
        <div v-else class="results-loaded">
          <section v-if="canSeeEvidence" class="results-section">
            <h3>Video</h3>
            <p v-if="!videoPlaybackSrc" class="status-text">
              Video preview is not available yet. Evidence markers can still be listed, but “Jump to” requires a
              playable video source.
            </p>
            <video
              v-else
              ref="resultsVideoEl"
              class="results-video"
              :src="videoPlaybackSrc"
              controls
              preload="metadata"
              @loadedmetadata="onVideoLoaded"
            />
          </section>

          <section class="results-section coach-summary-card">
            <h3>Summary</h3>
            <p class="summary-level">
              Rating: <strong>{{ coachNarrative.summary.rating }}</strong>
            </p>
            <p class="status-text">{{ coachNarrative.summary.confidenceText }}</p>
            <p class="status-text">{{ coachNarrative.summary.coverageText }}</p>
            <p class="status-text">{{ coachNarrative.summary.coachSummaryText }}</p>
          </section>

          <section class="results-section">
            <h3>Metrics</h3>
            <div class="metrics-grid">
              <div class="metric">
                <span class="metric-label">Frames analyzed</span>
                <span class="metric-value">{{ formatCount(coachNarrative.metrics.framesAnalyzed) }}</span>
              </div>
              <div class="metric">
                <span class="metric-label">Total frames</span>
                <span class="metric-value">{{ formatCount(coachNarrative.metrics.totalFrames) }}</span>
              </div>
              <div class="metric">
                <span class="metric-label">Detection rate</span>
                <span class="metric-value">{{ formatPercent01(coachNarrative.metrics.detectionRate) }}</span>
              </div>
            </div>
          </section>

          <section v-if="isFreeTier" class="results-section">
            <h3>Upgrade to see priorities</h3>
            <p class="status-text">
              Your current plan shows the summary only. Upgrade to Coach Pro to unlock priorities and drills.
            </p>
          </section>

          <section v-else class="results-section">
            <h3>Priorities</h3>
            <p v-if="coachNarrative.priorities.length === 0" class="status-text">
              No actionable priorities were returned for this analysis yet.
            </p>
            <div
              v-for="p in coachNarrative.priorities"
              :key="p.key"
              class="finding-card"
            >
              <div class="priority-header">
                <h4>{{ p.title }}</h4>
                <span :class="['severity-badge', `sev-${p.severity}`]">{{ severityLabel(p.severity) }}</span>
              </div>
              <p class="finding-line">{{ p.explanation }}</p>
              <p class="finding-line">{{ p.impact }}</p>

              <div v-if="canSeeEvidence && p.evidence" class="evidence">
                <h5>Evidence</h5>

                <div v-if="videoDurationSec && p.evidence.badSegments.length" class="timeline">
                  <div class="timeline-bar">
                    <div
                      v-for="(seg, sidx) in p.evidence.badSegments"
                      :key="sidx"
                      class="timeline-seg"
                      :style="timelineSegStyle(seg)"
                    />
                  </div>
                </div>

                <div v-if="p.evidence.worstFrames.length" class="evidence-block">
                  <h6>Worst moments</h6>
                  <ul>
                    <li v-for="(w, widx) in p.evidence.worstFrames" :key="widx" class="evidence-row">
                      <span>
                        Frame {{ w.frameNum }}
                        <span v-if="formatMomentTime(w)" class="evidence-time">({{ formatMomentTime(w) }})</span>
                      </span>
                      <button
                        v-if="canSeekToMoment(w)"
                        type="button"
                        class="btn-secondary btn-small"
                        @click="jumpToMoment(w)"
                      >
                        Jump to
                      </button>
                    </li>
                  </ul>
                </div>

                <div v-if="p.evidence.badSegments.length" class="evidence-block">
                  <h6>Problem segments</h6>
                  <ul>
                    <li v-for="(seg, sidx) in p.evidence.badSegments" :key="sidx" class="evidence-row">
                      <span>
                        Frames {{ seg.startFrame }}–{{ seg.endFrame }}
                        <span v-if="formatSegmentTime(seg)" class="evidence-time">({{ formatSegmentTime(seg) }})</span>
                      </span>
                      <button
                        v-if="canSeekToSegment(seg)"
                        type="button"
                        class="btn-secondary btn-small"
                        @click="jumpToSegment(seg)"
                      >
                        Jump to
                      </button>
                    </li>
                  </ul>
                </div>
              </div>

              <div v-if="canSeeDrills && p.drills.length" class="drills">
                <h5>Drills</h5>
                <ul>
                  <li v-for="(d, didx) in p.drills" :key="didx">{{ d }}</li>
                </ul>
              </div>
            </div>
          </section>
        </div>

        <div v-if="canExport" class="modal-actions">
          <button 
            type="button" 
            class="btn-primary" 
            :disabled="exportingPdf || !selectedJob"
            @click="exportPdf"
          >
            {{ exportingPdf ? 'Generating PDF...' : 'Export PDF' }}
          </button>
        </div>

        <div class="modal-actions">
          <button type="button" class="btn-secondary" @click="closeResultsModal">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';

import { ApiError } from '@/services/coachPlusVideoService';
import type { VideoAnalysisJob } from '@/services/coachPlusVideoService';
import { getVideoStreamUrl } from '@/services/coachPlusVideoService';
import { useAuthStore } from '@/stores/authStore';
import { useCoachPlusVideoStore } from '@/stores/coachPlusVideoStore';
import { buildCoachNarrative } from '@/utils/coachVideoAnalysisNarrative';

// ============================================================================
// State
// ============================================================================

const authStore = useAuthStore();
const videoStore = useCoachPlusVideoStore();

const sessions = ref<any[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const showCreateModal = ref(false);
const showUploadModal = ref(false);
const showResultsModal = ref(false);
const showHistoryModal = ref(false);
const editingId = ref<string | null>(null);
const uploadingSessionId = ref<string | null>(null);

// Session history state
const selectedSession = ref<any | null>(null);
const analysisHistory = ref<VideoAnalysisJob[]>([]);
const loadingHistory = ref(false);

const selectedFile = ref<File | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const videoPreviewUrl = ref<string | null>(null);
const videoStreamUrl = ref<string | null>(null);
const resultsVideoEl = ref<HTMLVideoElement | null>(null);
const videoDurationSec = ref<number | null>(null);

const offset = ref(0);
const limit = ref(10);

const formData = ref({
  title: '',
  player_ids: [] as string[],
  notes: '',
  analysis_context: '',
  camera_view: '',
});

const uploadSettings = ref({
  sampleFps: 10,
  includeFrames: false,
});

const playersText = ref('');

// PDF export state
const exportingPdf = ref(false);

// Watch store errors and display them
watch(
  () => videoStore.error,
  (newError) => {
    if (newError) {
      error.value = newError;
    }
  },
);

// Watch for completed jobs and show results
const selectedJob = ref<VideoAnalysisJob | null>(null);

const coachNarrative = computed(() => buildCoachNarrative(selectedJob.value));

watch(
  () => [showResultsModal.value, selectedJob.value?.id, selectedJob.value?.status, videoPreviewUrl.value] as const,
  async ([open]) => {
    if (!open) return;
    await ensureStreamUrlForSelectedJob();
  },
  { immediate: true },
);

const progressSteps = ['Extract pose', 'Compute metrics', 'Generate findings', 'Generate report'];

const tierRaw = computed(() => {
  const user = authStore.currentUser as unknown as { subscriptionTier?: unknown } | null;
  const subscriptionTier = typeof user?.subscriptionTier === 'string' ? user.subscriptionTier : null;
  return subscriptionTier ?? authStore.planName ?? authStore.role ?? 'free';
});

const isFreeTier = computed(() => {
  // Role/capability should override any legacy subscriptionTier strings.
  // Superusers (and Coach Pro/Plus) should never be treated as free.
  if (authStore.isCoachProPlus || authStore.isCoachPro || authStore.isSuperuser) return false;
  const t = String(tierRaw.value).toLowerCase();
  return t.includes('free');
});

const canSeeDrills = computed(() => {
  // Coach Pro and above
  if (authStore.isCoachProPlus || authStore.isCoachPro) return true;
  const t = String(tierRaw.value).toLowerCase();
  return t.includes('coach_pro');
});

const canSeeEvidence = computed(() => {
  // Coach Pro Plus only (and superuser)
  return authStore.isCoachProPlus;
});

const canExport = computed(() => {
  // Coach Pro Plus only
  if (authStore.isCoachProPlus) return true;
  const t = String(tierRaw.value).toLowerCase();
  return t.includes('plus');
});

const uiPollInterval = ref<ReturnType<typeof setInterval> | null>(null);
const pollTimedOut = ref(false);
const pollBackoffMs = ref(1000); // Start with 1 second, increase on errors

const videoPlaybackSrc = computed(() => videoPreviewUrl.value ?? videoStreamUrl.value);

async function ensureStreamUrlForSelectedJob(): Promise<void> {
  // Only needed when we don't have a local Object URL (e.g. after reload)
  if (!canSeeEvidence.value) return;
  if (videoPreviewUrl.value) return;
  if (videoStreamUrl.value) return;

  const sessionId = selectedJob.value?.session_id;
  if (!sessionId) return;

  // Prefer embedded stream URL from the single-job poll response
  const embedded = selectedJob.value?.video_stream?.video_url;
  if (typeof embedded === 'string' && embedded.length > 0) {
    videoStreamUrl.value = embedded;
    return;
  }

  try {
    const stream = await getVideoStreamUrl(sessionId);
    videoStreamUrl.value = stream.video_url;
  } catch {
    // Best-effort: keep UI working without a stream URL.
  }
}

function stopUiPolling() {
  if (uiPollInterval.value) {
    clearInterval(uiPollInterval.value);
    uiPollInterval.value = null;
  }
}

function startUiPolling(jobId: string) {
  stopUiPolling();
  pollTimedOut.value = false;
  pollBackoffMs.value = 1000; // Reset backoff

  const startedAt = Date.now();
  const timeoutMs = 5 * 60 * 1000;
  const maxBackoffMs = 10000; // Max 10 second backoff

  uiPollInterval.value = setInterval(async () => {
    try {
      // Force fetch to get latest status (bypasses terminal status protection)
      const freshJob = await videoStore.forceFetchJob(jobId);
      if (freshJob) {
        selectedJob.value = freshJob;
        pollBackoffMs.value = 1000; // Reset backoff on success
      }
    } catch (err) {
      console.error('[CoachProPlus] Poll error:', err);
      // Exponential backoff on error
      pollBackoffMs.value = Math.min(pollBackoffMs.value * 2, maxBackoffMs);
    }

    const latest = selectedJob.value;
    if (latest && (latest.status === 'completed' || latest.status === 'done' || latest.status === 'failed')) {
      pollTimedOut.value = false; // Reset timeout flag when terminal status reached
      stopUiPolling();
      return;
    }

    // Show timeout message but KEEP POLLING until terminal status
    if (Date.now() - startedAt > timeoutMs && !pollTimedOut.value) {
      pollTimedOut.value = true;
      // DO NOT stop polling - keep checking until done/failed
    }
  }, pollBackoffMs.value);
}

function retrySelectedJob() {
  const sessionId = selectedJob.value?.session_id;
  if (!sessionId) return;
  closeResultsModal();
  openUploadModal(sessionId);
}

async function exportPdf() {
  const jobId = selectedJob.value?.id;
  if (!jobId) return;

  exportingPdf.value = true;
  error.value = null;

  try {
    const { exportAnalysisPdf } = await import('@/services/coachPlusVideoService');
    const response = await exportAnalysisPdf(jobId);

    console.log(`[ExportPDF] Generated PDF: ${response.pdf_size_bytes} bytes, S3 key: ${response.pdf_s3_key}`);

    // Download via blob or open in new tab
    // Option 1: Download as file
    const link = document.createElement('a');
    link.href = response.pdf_url;
    link.download = `analysis-${jobId}.pdf`;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Optional: Also open in new tab for preview
    // window.open(response.pdf_url, '_blank');
  } catch (err) {
    console.error('[ExportPDF] Failed:', err);
    error.value = err instanceof Error ? err.message : 'Failed to export PDF';
  } finally {
    exportingPdf.value = false;
  }
}

// ============================================================================
// Computed
// ============================================================================

const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1);

// ============================================================================
// Methods
// ============================================================================

async function fetchSessions() {
  loading.value = true;
  error.value = null;

  try {
    await videoStore.fetchSessions(limit.value, offset.value);
    sessions.value = videoStore.sessions;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load sessions';
    console.error(err);
  } finally {
    loading.value = false;
  }
}

async function submitForm() {
  try {
    // Parse player IDs
    formData.value.player_ids = playersText.value
      .split(',')
      .map((id) => id.trim())
      .filter((id) => id.length > 0);

    if (!formData.value.title.trim()) {
      error.value = 'Session title is required';
      return;
    }

    if (editingId.value) {
      // TODO: Update session via API
      console.log('Update session:', editingId.value, formData.value);
    } else {
      // Create new session via store
      const session = await videoStore.createSession(formData.value);
      if (!session) {
        error.value = videoStore.error || 'Failed to create session';
        return;
      }

      // Immediately prompt for upload after creating a session
      closeModal();
      await fetchSessions();
      openUploadModal(session.id);
      return;
    }

    closeModal();
    await fetchSessions();
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Operation failed';
    error.value = msg;
    console.error(err);
  }
}

function onFileSelected(event: Event) {
  const target = event.target as HTMLInputElement;
  const files = target.files;
  if (files && files.length > 0) {
    selectedFile.value = files[0];
    setVideoPreviewFromFile(files[0]);
  }
}

function setVideoPreviewFromFile(file: File) {
  if (videoPreviewUrl.value) {
    URL.revokeObjectURL(videoPreviewUrl.value);
    videoPreviewUrl.value = null;
  }
  videoPreviewUrl.value = URL.createObjectURL(file);
  videoDurationSec.value = null;
}

function clearVideoPreview() {
  if (videoPreviewUrl.value) {
    URL.revokeObjectURL(videoPreviewUrl.value);
  }
  videoPreviewUrl.value = null;
  videoStreamUrl.value = null;
  videoDurationSec.value = null;
  resultsVideoEl.value = null;
}

async function handleVideoUpload() {
  if (!selectedFile.value || !uploadingSessionId.value) {
    error.value = 'Please select a video file';
    return;
  }

  // Reset results modal
  stopUiPolling();
  pollTimedOut.value = false;
  showResultsModal.value = false;
  selectedJob.value = null;

  try {
    // Start upload
    const jobId = await videoStore.startUpload(
      selectedFile.value,
      uploadingSessionId.value,
      uploadSettings.value.sampleFps,
      uploadSettings.value.includeFrames,
    );

    if (!jobId) {
      error.value = videoStore.error || 'Failed to start upload';
      return;
    }

    // Close upload modal but keep local video preview for jump-to UX
    closeUploadModal(true);

    // Show modal immediately (progress UI) and keep it updated as polling runs.
    await videoStore.updateJobStatus(jobId);
    selectedJob.value = videoStore.jobStatusMap.get(jobId) || null;
    showResultsModal.value = true;
    startUiPolling(jobId);
  } catch (err) {
    let msg = 'Upload failed';
    if (err instanceof ApiError) {
      if (err.isFeatureDisabled()) {
        msg = `Video upload feature is not enabled on your plan. ${err.detail || 'Please upgrade to use this feature.'}`;
      } else if (err.isUnauthorized()) {
        msg = 'Your session expired. Please log in again.';
      } else {
        msg = err.detail || err.message;
      }
    } else if (err instanceof Error) {
      msg = err.message;
    }
    error.value = msg;
    console.error(err);
  }
}

function openUploadModal(sessionId: string) {
  uploadingSessionId.value = sessionId;
  selectedFile.value = null;
  clearVideoPreview();
  showUploadModal.value = true;
  if (fileInput.value) {
    fileInput.value.value = '';
  }
}

function closeUploadModal(keepPreviewForResults = false) {
  showUploadModal.value = false;
  uploadingSessionId.value = null;
  selectedFile.value = null;
  if (!keepPreviewForResults) {
    clearVideoPreview();
  }
  if (fileInput.value) {
    fileInput.value.value = '';
  }
}

function closeResultsModal() {
  showResultsModal.value = false;
  selectedJob.value = null;
  stopUiPolling();
  clearVideoPreview();
}

function onVideoLoaded() {
  const el = resultsVideoEl.value;
  if (!el) return;
  const d = el.duration;
  videoDurationSec.value = Number.isFinite(d) ? d : null;
}

function formatMmSs(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '—';
  const s = Math.floor(seconds);
  const mm = Math.floor(s / 60);
  const ss = s % 60;
  return `${mm}:${String(ss).padStart(2, '0')}`;
}

function getJobFps(): number | null {
  const results: any = selectedJob.value?.results as any;
  const fps =
    (typeof results?.video_fps === 'number' ? results.video_fps : null) ??
    (typeof results?.pose?.video_fps === 'number' ? results.pose.video_fps : null) ??
    (typeof results?.pose?.fps === 'number' ? results.pose.fps : null) ??
    null;
  return fps && Number.isFinite(fps) && fps > 0 ? fps : null;
}

function momentSeconds(w: { frameNum: number; timeSeconds?: number }): number | null {
  if (typeof w.timeSeconds === 'number' && Number.isFinite(w.timeSeconds) && w.timeSeconds >= 0) {
    return w.timeSeconds;
  }
  const fps = getJobFps();
  if (!fps) return null;
  if (!Number.isFinite(w.frameNum) || w.frameNum <= 0) return null;
  return w.frameNum / fps;
}

function segmentStartSeconds(seg: {
  startFrame: number;
  startSeconds?: number;
}): number | null {
  if (typeof seg.startSeconds === 'number' && Number.isFinite(seg.startSeconds) && seg.startSeconds >= 0) {
    return seg.startSeconds;
  }
  const fps = getJobFps();
  if (!fps) return null;
  return seg.startFrame > 0 ? seg.startFrame / fps : null;
}

function segmentEndSeconds(seg: { endFrame: number; endSeconds?: number }): number | null {
  if (typeof seg.endSeconds === 'number' && Number.isFinite(seg.endSeconds) && seg.endSeconds >= 0) {
    return seg.endSeconds;
  }
  const fps = getJobFps();
  if (!fps) return null;
  return seg.endFrame > 0 ? seg.endFrame / fps : null;
}

function formatMomentTime(w: { frameNum: number; timeSeconds?: number }): string | null {
  const sec = momentSeconds(w);
  return sec == null ? null : formatMmSs(sec);
}

function formatSegmentTime(seg: {
  startFrame: number;
  endFrame: number;
  startSeconds?: number;
  endSeconds?: number;
}): string | null {
  const s = segmentStartSeconds(seg);
  const e = segmentEndSeconds(seg);
  if (s == null || e == null) return null;
  return `${formatMmSs(s)}–${formatMmSs(e)}`;
}

function canSeekToMoment(w: { frameNum: number; timeSeconds?: number }): boolean {
  return !!resultsVideoEl.value && momentSeconds(w) != null;
}

function canSeekToSegment(seg: { startFrame: number; startSeconds?: number }): boolean {
  return !!resultsVideoEl.value && segmentStartSeconds(seg) != null;
}

function jumpTo(seconds: number) {
  const el = resultsVideoEl.value;
  if (!el) return;
  el.currentTime = Math.max(0, seconds);
  el.play().catch(() => {
    // Autoplay may be blocked; seeking is still applied.
  });
}

function jumpToMoment(w: { frameNum: number; timeSeconds?: number }) {
  const sec = momentSeconds(w);
  if (sec == null) return;
  jumpTo(sec);
}

function jumpToSegment(seg: { startFrame: number; startSeconds?: number }) {
  const sec = segmentStartSeconds(seg);
  if (sec == null) return;
  jumpTo(sec);
}

function timelineSegStyle(seg: {
  startFrame: number;
  endFrame: number;
  startSeconds?: number;
  endSeconds?: number;
}): Record<string, string> {
  const dur = videoDurationSec.value;
  if (!dur || !Number.isFinite(dur) || dur <= 0) return { display: 'none' };
  const s = segmentStartSeconds(seg);
  const e = segmentEndSeconds(seg);
  if (s == null || e == null) return { display: 'none' };
  const start = Math.max(0, Math.min(1, s / dur));
  const end = Math.max(0, Math.min(1, e / dur));
  const left = Math.min(start, end);
  const width = Math.max(0.002, Math.abs(end - start));
  return {
    left: `${left * 100}%`,
    width: `${width * 100}%`,
  };
}

async function selectSession(sessionId: string) {
  try {
    // Find the session
    const session = sessions.value.find(s => s.id === sessionId);
    if (!session) {
      error.value = 'Session not found';
      return;
    }

    // Load analysis history
    selectedSession.value = session;
    loadingHistory.value = true;
    showHistoryModal.value = true;

    const { getAnalysisHistory } = await import('@/services/coachPlusVideoService');
    analysisHistory.value = await getAnalysisHistory(sessionId);
    loadingHistory.value = false;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load session history';
    console.error('selectSession error:', err);
    loadingHistory.value = false;
  }
}

function editSession(sessionId: string) {
  editingId.value = sessionId;
  showCreateModal.value = true;
}

async function deleteSession(sessionId: string) {
  if (!confirm('Are you sure you want to delete this session?')) {
    return;
  }

  try {
    console.log('Delete session:', sessionId);
    // TODO: Delete via API
    await fetchSessions();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to delete session';
    console.error(err);
  }
}

function closeModal() {
  showCreateModal.value = false;
  editingId.value = null;
  formData.value = { title: '', player_ids: [], notes: '' };
  playersText.value = '';
}

function closeHistoryModal() {
  showHistoryModal.value = false;
  selectedSession.value = null;
  analysisHistory.value = [];
}

function closeHistoryModalAndUpload() {
  const sessionId = selectedSession.value?.id;
  closeHistoryModal();
  if (sessionId) {
    openUploadModal(sessionId);
  }
}

function viewJobResults(job: VideoAnalysisJob) {
  selectedJob.value = job;
  showHistoryModal.value = false;
  showResultsModal.value = true;
  
  // Start polling if not terminal
  if (!isJobCompleted(job)) {
    startUiPolling(job.id);
  }
}

async function exportJobPdf(jobId: string) {
  exportingPdf.value = true;
  error.value = null;

  try {
    const { exportAnalysisPdf } = await import('@/services/coachPlusVideoService');
    const response = await exportAnalysisPdf(jobId);

    console.log(`[ExportPDF] Generated PDF: ${response.pdf_size_bytes} bytes, S3 key: ${response.pdf_s3_key}`);

    // Download PDF
    const link = document.createElement('a');
    link.href = response.pdf_url;
    link.download = `analysis-${jobId}.pdf`;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (err) {
    console.error('[ExportPDF] Failed:', err);
    error.value = err instanceof Error ? err.message : 'Failed to export PDF';
  } finally {
    exportingPdf.value = false;
  }
}

function isJobCompleted(job: VideoAnalysisJob): boolean {
  return job.status === 'completed' || job.status === 'done' || job.status === 'failed';
}

function previousPage() {
  offset.value = Math.max(0, offset.value - limit.value);
  fetchSessions();
}

function nextPage() {
  offset.value += limit.value;
  fetchSessions();
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatAnalysisContext(context: string): string {
  const map: Record<string, string> = {
    batting: 'Batting',
    bowling: 'Bowling',
    wicketkeeping: 'Wicketkeeping',
    fielding: 'Fielding',
    mixed: 'Mixed/General',
  };
  return map[context] || context;
}

function formatCameraView(view: string): string {
  const map: Record<string, string> = {
    side: 'Side View',
    front: 'Front View',
    behind: 'Behind View',
    other: 'Other',
  };
  return map[view] || view;
}

function formatCount(value: number | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  return String(Math.round(value));
}

function formatPercent01(value01: number | undefined): string {
  if (typeof value01 !== 'number' || !Number.isFinite(value01)) return '—';
  const pct = Math.round(Math.max(0, Math.min(1, value01)) * 100);
  return `${pct}%`;
}

function severityLabel(sev: 'low' | 'medium' | 'high'): string {
  if (sev === 'high') return 'High';
  if (sev === 'medium') return 'Medium';
  return 'Low';
}

// ============================================================================
// Lifecycle
// ============================================================================

onMounted(() => {
  if (authStore.isCoachProPlus) {
    fetchSessions();
  }
});

onBeforeUnmount(() => {
  stopUiPolling();
  videoStore.cleanup();
});
</script>

<style scoped>
.coach-pro-plus-video-sessions {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

/* Feature Gate */
.feature-gate {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.upgrade-card {
  text-align: center;
  padding: 3rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px;
  max-width: 500px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}

.upgrade-card h2 {
  font-size: 1.75rem;
  margin-bottom: 1rem;
}

.upgrade-card p {
  font-size: 1rem;
  line-height: 1.6;
  margin-bottom: 2rem;
  opacity: 0.95;
}

.upgrade-button {
  display: inline-block;
  padding: 0.75rem 2rem;
  background: white;
  color: #667eea;
  text-decoration: none;
  border-radius: 6px;
  font-weight: bold;
  transition: transform 0.2s;
}

.upgrade-button:hover {
  transform: translateY(-2px);
}

/* Main Container */
.sessions-container {
  padding: 1rem;
}

.sessions-header {
  margin-bottom: 2rem;
}

.sessions-header h1 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #666;
  margin-bottom: 1.5rem;
}

/* Loading & Error */
.loading,
.error-banner {
  padding: 1.5rem;
  text-align: center;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.loading {
  background: #f0f0f0;
}

.results-error {
  padding: 1.5rem;
  background: #fff3cd;
  border: 1px solid #ffeeba;
  border-radius: 8px;
}

.progress-bar {
  position: relative;
  height: 8px;
  background: #eee;
  border-radius: 999px;
  overflow: hidden;
  margin: 1rem 0;
}

.progress-bar-indeterminate {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 35%;
  background: #667eea;
  animation: indeterminate 1.2s infinite;
}

@keyframes indeterminate {
  0% {
    left: -35%;
  }
  100% {
    left: 100%;
  }
}

.step-labels {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  color: #666;
  font-size: 0.9rem;
}

.step-label {
  padding: 0.25rem 0.5rem;
  background: #f6f6f6;
  border-radius: 999px;
}

.coach-summary-card {
  background: #f9f9ff;
  border: 1px solid #e7e7ff;
}

.summary-level {
  margin: 0.25rem 0 0.75rem;
}

.takeaways {
  margin: 0;
  padding-left: 1.25rem;
}

.finding-card {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 1rem;
  margin-top: 0.75rem;
}

.priority-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
}

.results-video {
  width: 100%;
  max-height: 360px;
  border-radius: 10px;
}

.severity-badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  font-size: 0.75rem;
  border-radius: 999px;
  border: 1px solid #ddd;
  color: #333;
  white-space: nowrap;
}

.sev-high {
  background: #ffeaa7;
  border-color: #ffd36d;
}

.sev-medium {
  background: #dfe6e9;
  border-color: #c8d0d4;
}

.sev-low {
  background: #f6f6f6;
  border-color: #e6e6e6;
}

.finding-line {
  margin: 0.5rem 0;
  color: #444;
}

.evidence {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid #eee;
}

.evidence-block {
  margin-top: 0.6rem;
}

.evidence-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.evidence-time {
  color: #666;
  margin-left: 0.35rem;
}

.btn-small {
  padding: 0.35rem 0.6rem;
  font-size: 0.9rem;
}

.timeline {
  margin: 0.6rem 0;
}

.timeline-bar {
  position: relative;
  height: 10px;
  border-radius: 999px;
  background: #f2f2f2;
  overflow: hidden;
}

.timeline-seg {
  position: absolute;
  top: 0;
  bottom: 0;
  background: rgba(220, 53, 69, 0.55);
}

.drills {
  margin: 0.5rem 0 0;
  padding-left: 1.25rem;
}

.numbers-accordion summary {
  cursor: pointer;
  font-weight: bold;
}

.metric-band {
  display: inline-block;
  margin-top: 0.35rem;
  padding: 0.15rem 0.5rem;
  font-size: 0.75rem;
  border-radius: 999px;
  border: 1px solid #ddd;
  color: #333;
}

.band-needs-work {
  background: #ffeaa7;
  border-color: #ffd36d;
}

.band-improving {
  background: #dfe6e9;
  border-color: #c8d0d4;
}

.band-strong {
  background: #55efc4;
  border-color: #31d8a8;
}

.error-banner {
  background: #fee;
  color: #c33;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.btn-close {
  background: none;
  border: none;
  color: #c33;
  cursor: pointer;
  font-weight: bold;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 3rem;
  background: #f9f9f9;
  border-radius: 8px;
  margin: 2rem 0;
}

.empty-state p {
  margin: 0.5rem 0;
  color: #666;
}

.hint {
  font-size: 0.95rem;
  color: #999;
}

/* Sessions List */
.sessions-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.session-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.session-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 1rem;
}

.session-header h3 {
  margin: 0;
  font-size: 1.1rem;
  flex: 1;
}

.status-badge {
  display: inline-block;
  padding: 0.35rem 0.75rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: bold;
  text-transform: uppercase;
  margin-left: 0.5rem;
}

.status-pending {
  background: #ffeaa7;
  color: #d63031;
}

.status-uploaded {
  background: #81ecec;
  color: #0984e3;
}

.status-processing {
  background: #dfe6e9;
  color: #2d3436;
}

.status-ready {
  background: #55efc4;
  color: #00b894;
}

.session-meta {
  font-size: 0.9rem;
  color: #666;
  margin-bottom: 1rem;
}

.session-meta p {
  margin: 0.3rem 0;
}

.session-meta .camera-view {
  color: #999;
  font-style: italic;
}

.analysis-context-header {
  background: #f0f4ff;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  margin-bottom: 1.5rem;
  font-size: 0.95rem;
  color: #667eea;
  font-weight: 500;
}

.analysis-context-header .context-label {
  font-weight: 600;
}

.analysis-context-header .camera-label {
  color: #999;
  margin-left: 0.25rem;
}

.session-notes {
  background: #f9f9f9;
  padding: 0.75rem;
  border-left: 3px solid #667eea;
  margin: 1rem 0;
  font-size: 0.9rem;
  color: #333;
}

.session-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.session-actions button {
  flex: 1;
  padding: 0.5rem;
  font-size: 0.85rem;
}

/* Buttons */
.btn-primary,
.btn-secondary,
.btn-danger,
.btn-pagination {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.2s;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover {
  background: #5568d3;
}

.btn-secondary {
  background: #e0e0e0;
  color: #333;
}

.btn-secondary:hover {
  background: #d0d0d0;
}

.btn-danger {
  background: #ff6b6b;
  color: white;
}

.btn-danger:hover {
  background: #ee5a52;
}

.btn-pagination {
  padding: 0.5rem 1rem;
  background: #f0f0f0;
  color: #333;
}

.btn-pagination:hover:not(:disabled) {
  background: #e0e0e0;
}

.btn-pagination:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #ddd;
}

.page-info {
  color: #666;
  font-size: 0.95rem;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  position: relative;
}

.modal-large {
  max-width: 900px;
}

.modal-close-btn {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #999;
}

.modal-close-btn:hover {
  color: #333;
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  font-weight: bold;
  margin-bottom: 0.5rem;
  color: #333;
}

.form-group label .required {
  color: #e74c3c;
  margin-left: 0.25rem;
}

.form-group input[type='text'],
.form-group input[type='file'],
.form-group input[type='number'],
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: inherit;
  font-size: 1rem;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-group input[type='checkbox'] {
  margin-right: 0.5rem;
}

.form-group.checkbox label {
  display: flex;
  align-items: center;
}

.file-hint,
.setting-hint {
  font-size: 0.85rem;
  color: #999;
  margin-top: 0.3rem;
}

.file-selected {
  color: #00b894;
  font-weight: bold;
}

.upload-progress {
  margin-bottom: 1.5rem;
}

.progress-bar {
  width: 100%;
  height: 30px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  font-size: 0.9rem;
  transition: width 0.3s ease;
}

.progress-text {
  margin-top: 0.5rem;
  text-align: center;
  color: #666;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
}

.modal-actions button {
  flex: 1;
}

/* Results Modal */
.results-loading {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.status-text {
  color: #999;
  font-size: 0.95rem;
}

.results-section {
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid #eee;
}

.results-section h3 {
  margin-top: 0;
  margin-bottom: 1.2rem;
  font-size: 1.3rem;
  color: #333;
}

.results-section h4 {
  margin: 1.2rem 0 0.8rem;
  font-size: 1.1rem;
  color: #555;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.metric {
  background: #f9f9f9;
  padding: 1rem;
  border-radius: 6px;
  text-align: center;
  border: 1px solid #eee;
}

.metric-label {
  display: block;
  font-size: 0.85rem;
  color: #999;
  margin-bottom: 0.3rem;
  font-weight: 500;
}

.metric-value {
  display: block;
  font-size: 1.5rem;
  font-weight: bold;
  color: #667eea;
}

.report-subsection {
  margin-bottom: 1.2rem;
}

.report-subsection ul {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}

.report-subsection li {
  margin: 0.3rem 0;
  color: #555;
}

.drill-card {
  background: #f9f9f9;
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 0.8rem;
  border-left: 3px solid #667eea;
}

.drill-card h5 {
  margin: 0 0 0.5rem;
  color: #333;
}

.drill-card p {
  margin: 0.3rem 0;
  color: #666;
  font-size: 0.95rem;
}

.drill-meta {
  color: #999;
  font-size: 0.85rem !important;
  margin-top: 0.5rem;
}

.training-plan {
  background: #f9f9f9;
  padding: 1rem;
  border-radius: 6px;
  line-height: 1.6;
  color: #555;
}

/* Responsive */
@media (max-width: 768px) {
  .coach-pro-plus-video-sessions {
    padding: 1rem;
  }

  .sessions-list {
    grid-template-columns: 1fr;
  }

  .sessions-header h1 {
    font-size: 1.5rem;
  }

  .modal-content {
    width: 95%;
  }

  .pagination {
    flex-direction: column;
    gap: 0.5rem;
  }

  .session-actions {
    flex-direction: column;
  }

  .session-actions button {
    width: 100%;
  }
}

/* History Modal */
.history-list {
  margin-top: 1.5rem;
}

.history-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1.5rem;
}

.history-table th,
.history-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.history-table th {
  background: #f9f9f9;
  font-weight: 600;
  color: #555;
}

.history-table tbody tr:hover {
  background: #f5f5f5;
}

.history-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-small {
  padding: 0.4rem 0.8rem;
  font-size: 0.875rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-small.btn-primary {
  background: #667eea;
  color: white;
}

.btn-small.btn-primary:hover:not(:disabled) {
  background: #5568d3;
}

.btn-small.btn-secondary {
  background: #e0e0e0;
  color: #333;
}

.btn-small.btn-secondary:hover:not(:disabled) {
  background: #d0d0d0;
}

.btn-small:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>

/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/template-helpers.d.ts" />
/// <reference types="../../../../../../.npm/_npx/2db181330ea4b15b/node_modules/@vue/language-core/types/props-fallback.d.ts" />
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import GoalSetter from '@/components/GoalSetter.vue';
import OutcomesViewer from '@/components/OutcomesViewer.vue';
import SessionComparison from '@/components/SessionComparison.vue';
import CoachSuggestionsPanel from '@/components/CoachSuggestionsPanel.vue';
import PlayerSummaryCard from '@/components/PlayerSummaryCard.vue';
import { ApiError, getVideoStreamUrl, calculateCompliance, getJobOutcomes, generateCoachSuggestions, getCoachSuggestions, } from '@/services/coachPlusVideoService';
import { useAuthStore } from '@/stores/authStore';
import { useCoachPlusVideoStore } from '@/stores/coachPlusVideoStore';
import { buildCoachNarrative } from '@/utils/coachVideoAnalysisNarrative';
// ============================================================================
// State
// ============================================================================
const authStore = useAuthStore();
const videoStore = useCoachPlusVideoStore();
const sessions = ref([]);
const loading = ref(false);
const error = ref(null);
const showCreateModal = ref(false);
const showUploadModal = ref(false);
const showResultsModal = ref(false);
const showHistoryModal = ref(false);
const editingId = ref(null);
const uploadingSessionId = ref(null);
// Phase 2: Goals & Comparison State
const showGoalsModal = ref(false);
const goalsJobId = ref(null);
const goalsSessionId = ref(null);
const jobOutcomes = ref(null);
const showComparisonModal = ref(false);
const comparisonMode = ref(false);
const selectedJobsForComparison = ref([]);
// Phase 3: Coaching Suggestions state
const coachSuggestions = ref(null);
const playerSummary = ref(null);
const showPlayerSummary = ref(false);
const loadingSuggestions = ref(false);
// Session history state
const selectedSession = ref(null);
const analysisHistory = ref([]);
const loadingHistory = ref(false);
const selectedFile = ref(null);
const fileInput = ref(null);
const videoPreviewUrl = ref(null);
const videoStreamUrl = ref(null);
const resultsVideoEl = ref(null);
const videoDurationSec = ref(null);
const offset = ref(0);
const limit = ref(10);
const excludeFailed = ref(true); // Performance: hide failed sessions by default
const statusFilter = ref(null);
const formData = ref({
    title: '',
    player_ids: [],
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
watch(() => videoStore.error, (newError) => {
    if (newError) {
        error.value = newError;
    }
});
// Watch for completed jobs and show results
const selectedJob = ref(null);
const coachNarrative = computed(() => buildCoachNarrative(selectedJob.value));
watch(() => [showResultsModal.value, selectedJob.value?.id, selectedJob.value?.status, videoPreviewUrl.value], async ([open]) => {
    if (!open)
        return;
    await ensureStreamUrlForSelectedJob();
}, { immediate: true });
const progressSteps = ['Extract pose', 'Compute metrics', 'Generate findings', 'Generate report'];
const tierRaw = computed(() => {
    const user = authStore.currentUser;
    const subscriptionTier = typeof user?.subscriptionTier === 'string' ? user.subscriptionTier : null;
    return subscriptionTier ?? authStore.planName ?? authStore.role ?? 'free';
});
const isFreeTier = computed(() => {
    // Role/capability should override any legacy subscriptionTier strings.
    // Superusers (and Coach Pro/Plus) should never be treated as free.
    if (authStore.isCoachProPlus || authStore.isCoachPro || authStore.isSuperuser)
        return false;
    const t = String(tierRaw.value).toLowerCase();
    return t.includes('free');
});
const canSeeDrills = computed(() => {
    // Coach Pro and above
    if (authStore.isCoachProPlus || authStore.isCoachPro)
        return true;
    const t = String(tierRaw.value).toLowerCase();
    return t.includes('coach_pro');
});
const canSeeEvidence = computed(() => {
    // Coach Pro Plus only (and superuser)
    return authStore.isCoachProPlus;
});
const canExport = computed(() => {
    // Coach Pro Plus only
    if (authStore.isCoachProPlus)
        return true;
    const t = String(tierRaw.value).toLowerCase();
    return t.includes('plus');
});
const uiPollInterval = ref(null);
const pollTimedOut = ref(false);
const pollBackoffMs = ref(1000); // Start with 1 second, increase on errors
const videoPlaybackSrc = computed(() => videoPreviewUrl.value ?? videoStreamUrl.value);
async function ensureStreamUrlForSelectedJob() {
    // Only needed when we don't have a local Object URL (e.g. after reload)
    if (!canSeeEvidence.value)
        return;
    if (videoPreviewUrl.value)
        return;
    if (videoStreamUrl.value)
        return;
    const sessionId = selectedJob.value?.session_id;
    if (!sessionId)
        return;
    // Prefer embedded stream URL from the single-job poll response
    const embedded = selectedJob.value?.video_stream?.video_url;
    if (typeof embedded === 'string' && embedded.length > 0) {
        videoStreamUrl.value = embedded;
        return;
    }
    try {
        const stream = await getVideoStreamUrl(sessionId);
        videoStreamUrl.value = stream.video_url;
    }
    catch {
        // Best-effort: keep UI working without a stream URL.
    }
}
function stopUiPolling() {
    if (uiPollInterval.value) {
        clearInterval(uiPollInterval.value);
        uiPollInterval.value = null;
    }
}
function startUiPolling(jobId) {
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
        }
        catch (err) {
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
    if (!sessionId)
        return;
    closeResultsModal();
    openUploadModal(sessionId);
}
async function exportPdf() {
    const jobId = selectedJob.value?.id;
    if (!jobId)
        return;
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
    }
    catch (err) {
        console.error('[ExportPDF] Failed:', err);
        error.value = err instanceof Error ? err.message : 'Failed to export PDF';
    }
    finally {
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
        const { listVideoSessions } = await import('@/services/coachPlusVideoService');
        sessions.value = await listVideoSessions(limit.value, offset.value, {
            excludeFailed: excludeFailed.value,
            statusFilter: statusFilter.value || undefined,
        });
    }
    catch (err) {
        error.value = err instanceof Error ? err.message : 'Failed to load sessions';
        console.error(err);
    }
    finally {
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
        }
        else {
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
    }
    catch (err) {
        const msg = err instanceof Error ? err.message : 'Operation failed';
        error.value = msg;
        console.error(err);
    }
}
function onFileSelected(event) {
    const target = event.target;
    const files = target.files;
    if (files && files.length > 0) {
        selectedFile.value = files[0];
        setVideoPreviewFromFile(files[0]);
    }
}
function setVideoPreviewFromFile(file) {
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
        // Extract analysis mode from session context
        const session = sessions.value.find((s) => s.id === uploadingSessionId.value);
        const analysisMode = (session?.analysis_context ?? null);
        // Start upload
        const jobId = await videoStore.startUpload(selectedFile.value, uploadingSessionId.value, uploadSettings.value.sampleFps, uploadSettings.value.includeFrames, analysisMode);
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
    }
    catch (err) {
        let msg = 'Upload failed';
        if (err instanceof ApiError) {
            if (err.isFeatureDisabled()) {
                msg = `Video upload feature is not enabled on your plan. ${err.detail || 'Please upgrade to use this feature.'}`;
            }
            else if (err.isUnauthorized()) {
                msg = 'Your session expired. Please log in again.';
            }
            else {
                msg = err.detail || err.message;
            }
        }
        else if (err instanceof Error) {
            msg = err.message;
        }
        error.value = msg;
        console.error(err);
    }
}
function openUploadModal(sessionId) {
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
    if (!el)
        return;
    const d = el.duration;
    videoDurationSec.value = Number.isFinite(d) ? d : null;
}
function formatMmSs(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0)
        return '—';
    const s = Math.floor(seconds);
    const mm = Math.floor(s / 60);
    const ss = s % 60;
    return `${mm}:${String(ss).padStart(2, '0')}`;
}
function getJobFps() {
    const results = selectedJob.value?.results;
    const fps = (typeof results?.video_fps === 'number' ? results.video_fps : null) ??
        (typeof results?.pose?.video_fps === 'number' ? results.pose.video_fps : null) ??
        (typeof results?.pose?.fps === 'number' ? results.pose.fps : null) ??
        null;
    return fps && Number.isFinite(fps) && fps > 0 ? fps : null;
}
function momentSeconds(w) {
    if (typeof w.timeSeconds === 'number' && Number.isFinite(w.timeSeconds) && w.timeSeconds >= 0) {
        return w.timeSeconds;
    }
    const fps = getJobFps();
    if (!fps)
        return null;
    if (!Number.isFinite(w.frameNum) || w.frameNum <= 0)
        return null;
    return w.frameNum / fps;
}
function segmentStartSeconds(seg) {
    if (typeof seg.startSeconds === 'number' && Number.isFinite(seg.startSeconds) && seg.startSeconds >= 0) {
        return seg.startSeconds;
    }
    const fps = getJobFps();
    if (!fps)
        return null;
    return seg.startFrame > 0 ? seg.startFrame / fps : null;
}
function segmentEndSeconds(seg) {
    if (typeof seg.endSeconds === 'number' && Number.isFinite(seg.endSeconds) && seg.endSeconds >= 0) {
        return seg.endSeconds;
    }
    const fps = getJobFps();
    if (!fps)
        return null;
    return seg.endFrame > 0 ? seg.endFrame / fps : null;
}
function formatMomentTime(w) {
    const sec = momentSeconds(w);
    return sec == null ? null : formatMmSs(sec);
}
function formatSegmentTime(seg) {
    const s = segmentStartSeconds(seg);
    const e = segmentEndSeconds(seg);
    if (s == null || e == null)
        return null;
    return `${formatMmSs(s)}–${formatMmSs(e)}`;
}
function canSeekToMoment(w) {
    return !!resultsVideoEl.value && momentSeconds(w) != null;
}
function canSeekToSegment(seg) {
    return !!resultsVideoEl.value && segmentStartSeconds(seg) != null;
}
function jumpTo(seconds) {
    const el = resultsVideoEl.value;
    if (!el)
        return;
    el.currentTime = Math.max(0, seconds);
    el.play().catch(() => {
        // Autoplay may be blocked; seeking is still applied.
    });
}
function jumpToMoment(w) {
    const sec = momentSeconds(w);
    if (sec == null)
        return;
    jumpTo(sec);
}
function jumpToSegment(seg) {
    const sec = segmentStartSeconds(seg);
    if (sec == null)
        return;
    jumpTo(sec);
}
function timelineSegStyle(seg) {
    const dur = videoDurationSec.value;
    if (!dur || !Number.isFinite(dur) || dur <= 0)
        return { display: 'none' };
    const s = segmentStartSeconds(seg);
    const e = segmentEndSeconds(seg);
    if (s == null || e == null)
        return { display: 'none' };
    const start = Math.max(0, Math.min(1, s / dur));
    const end = Math.max(0, Math.min(1, e / dur));
    const left = Math.min(start, end);
    const width = Math.max(0.002, Math.abs(end - start));
    return {
        left: `${left * 100}%`,
        width: `${width * 100}%`,
    };
}
async function selectSession(sessionId) {
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
    }
    catch (err) {
        error.value = err instanceof Error ? err.message : 'Failed to load session history';
        console.error('selectSession error:', err);
        loadingHistory.value = false;
    }
}
function editSession(sessionId) {
    editingId.value = sessionId;
    showCreateModal.value = true;
}
async function bulkDeleteOldSessions() {
    const confirmed = confirm('Delete old failed sessions? This will:\n' +
        '• Delete all FAILED sessions older than 7 days\n' +
        '• Free up storage space\n' +
        '• Improve page load performance\n\n' +
        'This cannot be undone. Continue?');
    if (!confirmed)
        return;
    try {
        const { bulkDeleteSessions } = await import('@/services/coachPlusVideoService');
        const result = await bulkDeleteSessions({
            statusFilter: 'failed',
            olderThanDays: 7,
        });
        alert(`Cleanup complete!\n\n` +
            `• Sessions deleted: ${result.deleted_count}\n` +
            `• Storage freed: ${result.s3_files_deleted} videos removed`);
        // Refresh list
        await fetchSessions();
    }
    catch (err) {
        error.value = err instanceof Error ? err.message : 'Failed to bulk delete sessions';
        console.error('Bulk delete error:', err);
    }
}
async function deleteSession(sessionId) {
    if (!confirm('Are you sure you want to delete this session? This will also delete the uploaded video and all analysis data.')) {
        return;
    }
    try {
        const { deleteVideoSession } = await import('@/services/coachPlusVideoService');
        await deleteVideoSession(sessionId);
        console.log('Session deleted successfully:', sessionId);
        // Force refresh from backend to ensure deleted session is gone
        await fetchSessions();
    }
    catch (err) {
        error.value = err instanceof Error ? err.message : 'Failed to delete session';
        console.error('Delete session error:', err);
    }
}
async function reanalyzeVideo(sessionId) {
    const analysisMode = prompt('Select analysis mode for re-analysis:\n\n' +
        'Enter one of: batting, bowling, wicketkeeping, fielding\n\n' +
        '(Leave blank to use "batting" as default)', 'batting');
    if (analysisMode === null)
        return; // User cancelled
    const validModes = ['batting', 'bowling', 'wicketkeeping', 'fielding'];
    const mode = (analysisMode.trim().toLowerCase() || 'batting');
    if (!validModes.includes(mode)) {
        error.value = `Invalid analysis mode: ${mode}. Must be one of: ${validModes.join(', ')}`;
        return;
    }
    if (!confirm(`Re-analyze this video in "${mode}" mode? This will create a new analysis job while keeping the existing video.`)) {
        return;
    }
    try {
        const { reanalyzeSession } = await import('@/services/coachPlusVideoService');
        const job = await reanalyzeSession(sessionId, {
            analysisMode: mode,
            sampleFps: 10,
            includeFrames: false,
        });
        alert(`Re-analysis started!\n\nJob ID: ${job.id}\nMode: ${mode}\nStatus: ${job.status}`);
        // Refresh sessions to show new job
        await fetchSessions();
    }
    catch (err) {
        error.value = err instanceof Error ? err.message : 'Failed to start re-analysis';
        console.error('Re-analysis error:', err);
    }
}
function closeModal() {
    showCreateModal.value = false;
    editingId.value = null;
    formData.value = {
        title: '',
        player_ids: [],
        notes: '',
        analysis_context: '',
        camera_view: '',
    };
    playersText.value = '';
}
function closeHistoryModal() {
    showHistoryModal.value = false;
    selectedSession.value = null;
    analysisHistory.value = [];
}
// ============================================================================
// Phase 2: Goals & Outcomes
// ============================================================================
function openGoalsModal(jobId, sessionId) {
    goalsJobId.value = jobId;
    goalsSessionId.value = sessionId;
    showGoalsModal.value = true;
}
function closeGoalsModal() {
    showGoalsModal.value = false;
    goalsJobId.value = null;
    goalsSessionId.value = null;
}
async function handleGoalsSaved() {
    // After goals are saved, calculate compliance and refresh outcomes
    if (!goalsJobId.value)
        return;
    try {
        await calculateCompliance(goalsJobId.value);
        const outcomes = await getJobOutcomes(goalsJobId.value);
        jobOutcomes.value = outcomes;
        // Refresh history to show updated job
        if (selectedSession.value?.id) {
            await selectSession(selectedSession.value.id);
        }
        closeGoalsModal();
    }
    catch (err) {
        error.value = err instanceof Error ? err.message : 'Failed to calculate compliance';
        console.error('Calculate compliance error:', err);
    }
}
async function loadJobOutcomes(jobId) {
    try {
        const outcomes = await getJobOutcomes(jobId);
        jobOutcomes.value = outcomes;
    }
    catch (err) {
        console.error('Failed to load job outcomes:', err);
        jobOutcomes.value = null;
    }
}
// ============================================================================
// Phase 3: Coaching Suggestions
// ============================================================================
async function handleGenerateSuggestions() {
    const job = selectedJob.value;
    if (!job)
        return;
    loadingSuggestions.value = true;
    try {
        const suggestions = await generateCoachSuggestions(job.id);
        coachSuggestions.value = suggestions;
        // Also fetch player summary
        const data = await getCoachSuggestions(job.id);
        playerSummary.value = data.player_summary;
    }
    catch (err) {
        console.error('Failed to generate suggestions:', err);
        alert('Failed to generate coaching suggestions. Please try again.');
    }
    finally {
        loadingSuggestions.value = false;
    }
}
async function loadCoachSuggestions(jobId) {
    try {
        const data = await getCoachSuggestions(jobId);
        coachSuggestions.value = data.coach_suggestions;
        playerSummary.value = data.player_summary;
    }
    catch (err) {
        // Suggestions don't exist yet - this is fine
        coachSuggestions.value = null;
        playerSummary.value = null;
    }
}
async function handleApproveGoal(proposedGoal) {
    // In a real implementation, this would:
    // 1. Create a new session with these goals pre-populated
    // 2. Or save to the current session for next analysis
    console.log('Approved goal:', proposedGoal);
    alert('Goal approved! In the next session, these goals will be pre-loaded.');
    // For now, just show confirmation
}
function togglePlayerSummary() {
    showPlayerSummary.value = !showPlayerSummary.value;
}
// ============================================================================
// Phase 2: Session Comparison
// ============================================================================
function toggleComparisonMode() {
    comparisonMode.value = !comparisonMode.value;
    if (!comparisonMode.value) {
        selectedJobsForComparison.value = [];
    }
}
function toggleJobSelection(jobId) {
    const index = selectedJobsForComparison.value.indexOf(jobId);
    if (index >= 0) {
        selectedJobsForComparison.value.splice(index, 1);
    }
    else {
        selectedJobsForComparison.value.push(jobId);
    }
}
function openComparisonModal() {
    if (selectedJobsForComparison.value.length < 2) {
        error.value = 'Please select at least 2 jobs to compare';
        return;
    }
    showComparisonModal.value = true;
}
function closeComparisonModal() {
    showComparisonModal.value = false;
}
// ============================================================================
// Existing Modal Functions (continued)
// ============================================================================
function closeHistoryModalAndUpload() {
    const sessionId = selectedSession.value?.id;
    closeHistoryModal();
    if (sessionId) {
        openUploadModal(sessionId);
    }
}
function viewJobResults(job) {
    selectedJob.value = job;
    showHistoryModal.value = false;
    showResultsModal.value = true;
    // Load outcomes if goals exist
    if (job.coach_goals) {
        loadJobOutcomes(job.id);
    }
    else {
        jobOutcomes.value = null;
    }
    // Load coaching suggestions if they exist
    if (job.coach_suggestions) {
        loadCoachSuggestions(job.id);
    }
    else {
        coachSuggestions.value = null;
        playerSummary.value = null;
    }
    // Start polling if not terminal
    if (!isJobCompleted(job)) {
        startUiPolling(job.id);
    }
}
async function exportJobPdf(jobId) {
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
    }
    catch (err) {
        console.error('[ExportPDF] Failed:', err);
        error.value = err instanceof Error ? err.message : 'Failed to export PDF';
    }
    finally {
        exportingPdf.value = false;
    }
}
function isJobCompleted(job) {
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
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}
function formatAnalysisContext(context) {
    const map = {
        batting: 'Batting',
        bowling: 'Bowling',
        wicketkeeping: 'Wicketkeeping',
        fielding: 'Fielding',
        mixed: 'Mixed/General',
    };
    return map[context] || context;
}
function formatCameraView(view) {
    const map = {
        side: 'Side View',
        front: 'Front View',
        behind: 'Behind View',
        other: 'Other',
    };
    return map[view] || view;
}
function formatCount(value) {
    if (typeof value !== 'number' || !Number.isFinite(value))
        return '—';
    return String(Math.round(value));
}
function formatPercent01(value01) {
    if (typeof value01 !== 'number' || !Number.isFinite(value01))
        return '—';
    const pct = Math.round(Math.max(0, Math.min(1, value01)) * 100);
    return `${pct}%`;
}
function severityLabel(sev) {
    if (sev === 'high')
        return 'High';
    if (sev === 'medium')
        return 'Medium';
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
const __VLS_ctx = {
    ...{},
    ...{},
};
let __VLS_components;
let __VLS_intrinsics;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['upgrade-card']} */ ;
/** @type {__VLS_StyleScopedClasses['upgrade-card']} */ ;
/** @type {__VLS_StyleScopedClasses['upgrade-button']} */ ;
/** @type {__VLS_StyleScopedClasses['sessions-header']} */ ;
/** @type {__VLS_StyleScopedClasses['filter-checkbox']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-warning']} */ ;
/** @type {__VLS_StyleScopedClasses['loading']} */ ;
/** @type {__VLS_StyleScopedClasses['error-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
/** @type {__VLS_StyleScopedClasses['session-card']} */ ;
/** @type {__VLS_StyleScopedClasses['session-header']} */ ;
/** @type {__VLS_StyleScopedClasses['session-meta']} */ ;
/** @type {__VLS_StyleScopedClasses['session-meta']} */ ;
/** @type {__VLS_StyleScopedClasses['analysis-context-header']} */ ;
/** @type {__VLS_StyleScopedClasses['analysis-context-header']} */ ;
/** @type {__VLS_StyleScopedClasses['session-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-danger']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-danger']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-pagination']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-pagination']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-pagination']} */ ;
/** @type {__VLS_StyleScopedClasses['modal-close-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['modal-content']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['form-group']} */ ;
/** @type {__VLS_StyleScopedClasses['progress-bar']} */ ;
/** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['results-section']} */ ;
/** @type {__VLS_StyleScopedClasses['results-section']} */ ;
/** @type {__VLS_StyleScopedClasses['report-subsection']} */ ;
/** @type {__VLS_StyleScopedClasses['report-subsection']} */ ;
/** @type {__VLS_StyleScopedClasses['drill-card']} */ ;
/** @type {__VLS_StyleScopedClasses['drill-card']} */ ;
/** @type {__VLS_StyleScopedClasses['coach-pro-plus-video-sessions']} */ ;
/** @type {__VLS_StyleScopedClasses['sessions-list']} */ ;
/** @type {__VLS_StyleScopedClasses['sessions-header']} */ ;
/** @type {__VLS_StyleScopedClasses['modal-content']} */ ;
/** @type {__VLS_StyleScopedClasses['pagination']} */ ;
/** @type {__VLS_StyleScopedClasses['session-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['session-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['history-table']} */ ;
/** @type {__VLS_StyleScopedClasses['history-table']} */ ;
/** @type {__VLS_StyleScopedClasses['history-table']} */ ;
/** @type {__VLS_StyleScopedClasses['history-table']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-small']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-small']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-small']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-small']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-small']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-small']} */ ;
/** @type {__VLS_StyleScopedClasses['comparison-toolbar']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['btn-toggle-summary']} */ ;
__VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
    ...{ class: "coach-pro-plus-video-sessions" },
});
/** @type {__VLS_StyleScopedClasses['coach-pro-plus-video-sessions']} */ ;
if (!__VLS_ctx.authStore.isCoach) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "feature-gate" },
    });
    /** @type {__VLS_StyleScopedClasses['feature-gate']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "upgrade-card" },
    });
    /** @type {__VLS_StyleScopedClasses['upgrade-card']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    let __VLS_0;
    /** @ts-ignore @type { | typeof __VLS_components.routerLink | typeof __VLS_components.RouterLink | typeof __VLS_components['router-link'] | typeof __VLS_components.routerLink | typeof __VLS_components.RouterLink | typeof __VLS_components['router-link']} */
    routerLink;
    // @ts-ignore
    const __VLS_1 = __VLS_asFunctionalComponent1(__VLS_0, new __VLS_0({
        to: "/pricing",
        ...{ class: "upgrade-button" },
    }));
    const __VLS_2 = __VLS_1({
        to: "/pricing",
        ...{ class: "upgrade-button" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_1));
    /** @type {__VLS_StyleScopedClasses['upgrade-button']} */ ;
    const { default: __VLS_5 } = __VLS_3.slots;
    // @ts-ignore
    [authStore,];
    var __VLS_3;
}
else {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "sessions-container" },
    });
    /** @type {__VLS_StyleScopedClasses['sessions-container']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.header, __VLS_intrinsics.header)({
        ...{ class: "sessions-header" },
    });
    /** @type {__VLS_StyleScopedClasses['sessions-header']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h1, __VLS_intrinsics.h1)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
        ...{ class: "subtitle" },
    });
    /** @type {__VLS_StyleScopedClasses['subtitle']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "header-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['header-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (...[$event]) => {
                if (!!(!__VLS_ctx.authStore.isCoach))
                    return;
                __VLS_ctx.showCreateModal = true;
                // @ts-ignore
                [showCreateModal,];
            } },
        ...{ class: "btn-primary" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "toolbar" },
    });
    /** @type {__VLS_StyleScopedClasses['toolbar']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "filters" },
    });
    /** @type {__VLS_StyleScopedClasses['filters']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        ...{ class: "filter-checkbox" },
    });
    /** @type {__VLS_StyleScopedClasses['filter-checkbox']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        ...{ onChange: (...[$event]) => {
                if (!!(!__VLS_ctx.authStore.isCoach))
                    return;
                __VLS_ctx.fetchSessions();
                // @ts-ignore
                [fetchSessions,];
            } },
        type: "checkbox",
    });
    (__VLS_ctx.excludeFailed);
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        ...{ onChange: (...[$event]) => {
                if (!!(!__VLS_ctx.authStore.isCoach))
                    return;
                __VLS_ctx.fetchSessions();
                // @ts-ignore
                [fetchSessions, excludeFailed,];
            } },
        value: (__VLS_ctx.statusFilter),
        ...{ class: "status-filter" },
    });
    /** @type {__VLS_StyleScopedClasses['status-filter']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: (null),
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "pending",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "uploaded",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "processing",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "ready",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "failed",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "bulk-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['bulk-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.bulkDeleteOldSessions) },
        ...{ class: "btn-warning" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-warning']} */ ;
    if (__VLS_ctx.loading) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "loading" },
        });
        /** @type {__VLS_StyleScopedClasses['loading']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    }
    if (__VLS_ctx.error) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "error-banner" },
        });
        /** @type {__VLS_StyleScopedClasses['error-banner']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
        (__VLS_ctx.error);
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(!__VLS_ctx.authStore.isCoach))
                        return;
                    if (!(__VLS_ctx.error))
                        return;
                    __VLS_ctx.error = null;
                    // @ts-ignore
                    [statusFilter, bulkDeleteOldSessions, loading, error, error, error,];
                } },
            ...{ class: "btn-close" },
        });
        /** @type {__VLS_StyleScopedClasses['btn-close']} */ ;
    }
    if (!__VLS_ctx.loading && __VLS_ctx.sessions.length === 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "empty-state" },
        });
        /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "hint" },
        });
        /** @type {__VLS_StyleScopedClasses['hint']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (...[$event]) => {
                    if (!!(!__VLS_ctx.authStore.isCoach))
                        return;
                    if (!(!__VLS_ctx.loading && __VLS_ctx.sessions.length === 0))
                        return;
                    __VLS_ctx.showCreateModal = true;
                    // @ts-ignore
                    [showCreateModal, loading, sessions,];
                } },
            ...{ class: "btn-primary" },
        });
        /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
    }
    if (!__VLS_ctx.loading && __VLS_ctx.sessions.length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "sessions-list" },
        });
        /** @type {__VLS_StyleScopedClasses['sessions-list']} */ ;
        for (const [session] of __VLS_vFor((__VLS_ctx.sessions))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ onClick: (...[$event]) => {
                        if (!!(!__VLS_ctx.authStore.isCoach))
                            return;
                        if (!(!__VLS_ctx.loading && __VLS_ctx.sessions.length > 0))
                            return;
                        __VLS_ctx.selectSession(session.id);
                        // @ts-ignore
                        [loading, sessions, sessions, selectSession,];
                    } },
                key: (session.id),
                ...{ class: "session-card" },
            });
            /** @type {__VLS_StyleScopedClasses['session-card']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "session-header" },
            });
            /** @type {__VLS_StyleScopedClasses['session-header']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
            (session.title);
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: (['status-badge', `status-${session.status}`]) },
            });
            /** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
            (session.status);
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "session-meta" },
            });
            /** @type {__VLS_StyleScopedClasses['session-meta']} */ ;
            if (session.analysis_context) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
                __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
                (__VLS_ctx.formatAnalysisContext(session.analysis_context));
                if (session.camera_view) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                        ...{ class: "camera-view" },
                    });
                    /** @type {__VLS_StyleScopedClasses['camera-view']} */ ;
                    (__VLS_ctx.formatCameraView(session.camera_view));
                }
            }
            if (session.player_ids.length > 0) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
                __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
                (session.player_ids.length);
            }
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
            (__VLS_ctx.formatDate(session.created_at));
            if (session.notes) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "session-notes" },
                });
                /** @type {__VLS_StyleScopedClasses['session-notes']} */ ;
                (session.notes);
            }
            __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                ...{ class: "session-actions" },
            });
            /** @type {__VLS_StyleScopedClasses['session-actions']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                ...{ onClick: (...[$event]) => {
                        if (!!(!__VLS_ctx.authStore.isCoach))
                            return;
                        if (!(!__VLS_ctx.loading && __VLS_ctx.sessions.length > 0))
                            return;
                        __VLS_ctx.openUploadModal(session.id);
                        // @ts-ignore
                        [formatAnalysisContext, formatCameraView, formatDate, openUploadModal,];
                    } },
                ...{ class: "btn-primary" },
            });
            /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
            if (session.s3_key) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                    ...{ onClick: (...[$event]) => {
                            if (!!(!__VLS_ctx.authStore.isCoach))
                                return;
                            if (!(!__VLS_ctx.loading && __VLS_ctx.sessions.length > 0))
                                return;
                            if (!(session.s3_key))
                                return;
                            __VLS_ctx.reanalyzeVideo(session.id);
                            // @ts-ignore
                            [reanalyzeVideo,];
                        } },
                    ...{ class: "btn-secondary" },
                    title: "Re-analyze this video with different settings",
                });
                /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
            }
            __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                ...{ onClick: (...[$event]) => {
                        if (!!(!__VLS_ctx.authStore.isCoach))
                            return;
                        if (!(!__VLS_ctx.loading && __VLS_ctx.sessions.length > 0))
                            return;
                        __VLS_ctx.editSession(session.id);
                        // @ts-ignore
                        [editSession,];
                    } },
                ...{ class: "btn-secondary" },
            });
            /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                ...{ onClick: (...[$event]) => {
                        if (!!(!__VLS_ctx.authStore.isCoach))
                            return;
                        if (!(!__VLS_ctx.loading && __VLS_ctx.sessions.length > 0))
                            return;
                        __VLS_ctx.deleteSession(session.id);
                        // @ts-ignore
                        [deleteSession,];
                    } },
                ...{ class: "btn-danger" },
            });
            /** @type {__VLS_StyleScopedClasses['btn-danger']} */ ;
            // @ts-ignore
            [];
        }
    }
    if (__VLS_ctx.sessions.length > 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "pagination" },
        });
        /** @type {__VLS_StyleScopedClasses['pagination']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (__VLS_ctx.previousPage) },
            disabled: (__VLS_ctx.offset === 0),
            ...{ class: "btn-pagination" },
        });
        /** @type {__VLS_StyleScopedClasses['btn-pagination']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "page-info" },
        });
        /** @type {__VLS_StyleScopedClasses['page-info']} */ ;
        (__VLS_ctx.currentPage);
        (__VLS_ctx.sessions.length);
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (__VLS_ctx.nextPage) },
            ...{ class: "btn-pagination" },
        });
        /** @type {__VLS_StyleScopedClasses['btn-pagination']} */ ;
    }
}
if (__VLS_ctx.showCreateModal) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (__VLS_ctx.closeModal) },
        ...{ class: "modal-overlay" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-overlay']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: () => { } },
        ...{ class: "modal-content" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    (__VLS_ctx.editingId ? 'Edit' : 'Create');
    __VLS_asFunctionalElement1(__VLS_intrinsics.form, __VLS_intrinsics.form)({
        ...{ onSubmit: (__VLS_ctx.submitForm) },
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        for: "title",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
        id: "title",
        value: (__VLS_ctx.formData.title),
        type: "text",
        placeholder: "e.g., Batting Technique - Session 1",
        required: true,
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        for: "analysis-context",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
        ...{ class: "required" },
    });
    /** @type {__VLS_StyleScopedClasses['required']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        id: "analysis-context",
        value: (__VLS_ctx.formData.analysis_context),
        required: true,
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "batting",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "bowling",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "wicketkeeping",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "fielding",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "mixed",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        for: "camera-view",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.select, __VLS_intrinsics.select)({
        id: "camera-view",
        value: (__VLS_ctx.formData.camera_view),
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "side",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "front",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "behind",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.option, __VLS_intrinsics.option)({
        value: "other",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        for: "players",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.textarea, __VLS_intrinsics.textarea)({
        id: "players",
        value: (__VLS_ctx.playersText),
        placeholder: "player1_id, player2_id",
        rows: "3",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "form-group" },
    });
    /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
        for: "notes",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.textarea, __VLS_intrinsics.textarea)({
        id: "notes",
        value: (__VLS_ctx.formData.notes),
        placeholder: "Additional notes about this session...",
        rows: "4",
    });
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        type: "submit",
        ...{ class: "btn-primary" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
    (__VLS_ctx.editingId ? 'Save Changes' : 'Create Session');
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.closeModal) },
        type: "button",
        ...{ class: "btn-secondary" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-hint" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-hint']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
}
if (__VLS_ctx.showUploadModal) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (() => __VLS_ctx.closeUploadModal()) },
        ...{ class: "modal-overlay" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-overlay']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: () => { } },
        ...{ class: "modal-content" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    if (__VLS_ctx.videoStore.uploading) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "upload-progress" },
        });
        /** @type {__VLS_StyleScopedClasses['upload-progress']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "progress-bar" },
        });
        /** @type {__VLS_StyleScopedClasses['progress-bar']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "progress-fill" },
            ...{ style: ({ width: __VLS_ctx.videoStore.uploadProgress + '%' }) },
        });
        /** @type {__VLS_StyleScopedClasses['progress-fill']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "progress-text" },
        });
        /** @type {__VLS_StyleScopedClasses['progress-text']} */ ;
        (__VLS_ctx.videoStore.uploadProgress);
        (__VLS_ctx.videoStore.uploading.status);
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.form, __VLS_intrinsics.form)({
            ...{ onSubmit: (__VLS_ctx.handleVideoUpload) },
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "form-group" },
        });
        /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
            for: "video-file",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
            ...{ onChange: (__VLS_ctx.onFileSelected) },
            id: "video-file",
            ref: "fileInput",
            type: "file",
            accept: "video/mp4,video/quicktime,video/x-msvideo",
            required: true,
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "file-hint" },
        });
        /** @type {__VLS_StyleScopedClasses['file-hint']} */ ;
        if (__VLS_ctx.selectedFile) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "file-selected" },
            });
            /** @type {__VLS_StyleScopedClasses['file-selected']} */ ;
            (__VLS_ctx.selectedFile.name);
            ((__VLS_ctx.selectedFile.size / 1024 / 1024).toFixed(1));
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "form-group" },
        });
        /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({
            for: "sample-fps",
        });
        __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
            id: "sample-fps",
            type: "number",
            min: "1",
            max: "30",
            value: "10",
        });
        (__VLS_ctx.uploadSettings.sampleFps);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "setting-hint" },
        });
        /** @type {__VLS_StyleScopedClasses['setting-hint']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "form-group checkbox" },
        });
        /** @type {__VLS_StyleScopedClasses['form-group']} */ ;
        /** @type {__VLS_StyleScopedClasses['checkbox']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.label, __VLS_intrinsics.label)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
            type: "checkbox",
        });
        (__VLS_ctx.uploadSettings.includeFrames);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "setting-hint" },
        });
        /** @type {__VLS_StyleScopedClasses['setting-hint']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "modal-actions" },
        });
        /** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            type: "submit",
            ...{ class: "btn-primary" },
            disabled: (!__VLS_ctx.selectedFile),
        });
        /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (() => __VLS_ctx.closeUploadModal()) },
            type: "button",
            ...{ class: "btn-secondary" },
        });
        /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
    }
}
if (__VLS_ctx.showHistoryModal && __VLS_ctx.selectedSession) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (__VLS_ctx.closeHistoryModal) },
        ...{ class: "modal-overlay" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-overlay']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: () => { } },
        ...{ class: "modal-content" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-content']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.closeHistoryModal) },
        ...{ class: "modal-close-btn" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-close-btn']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    (__VLS_ctx.selectedSession.title);
    if (__VLS_ctx.loadingHistory) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "loading" },
        });
        /** @type {__VLS_StyleScopedClasses['loading']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
    }
    else if (__VLS_ctx.analysisHistory.length === 0) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "empty-state" },
        });
        /** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (__VLS_ctx.closeHistoryModalAndUpload) },
            ...{ class: "btn-primary" },
        });
        /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "history-list" },
        });
        /** @type {__VLS_StyleScopedClasses['history-list']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "comparison-toolbar" },
        });
        /** @type {__VLS_StyleScopedClasses['comparison-toolbar']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (__VLS_ctx.toggleComparisonMode) },
            ...{ class: "btn-secondary" },
        });
        /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
        (__VLS_ctx.comparisonMode ? '✕ Exit Comparison' : '📊 Compare Sessions');
        if (__VLS_ctx.comparisonMode) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                ...{ onClick: (__VLS_ctx.openComparisonModal) },
                ...{ class: "btn-primary" },
                disabled: (__VLS_ctx.selectedJobsForComparison.length < 2),
            });
            /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
            (__VLS_ctx.selectedJobsForComparison.length);
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.table, __VLS_intrinsics.table)({
            ...{ class: "history-table" },
        });
        /** @type {__VLS_StyleScopedClasses['history-table']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.thead, __VLS_intrinsics.thead)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({});
        if (__VLS_ctx.comparisonMode) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({
                ...{ style: {} },
            });
            __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
                type: "checkbox",
                disabled: true,
            });
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.th, __VLS_intrinsics.th)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.tbody, __VLS_intrinsics.tbody)({});
        for (const [job] of __VLS_vFor((__VLS_ctx.analysisHistory))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.tr, __VLS_intrinsics.tr)({
                key: (job.id),
            });
            if (__VLS_ctx.comparisonMode) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
                __VLS_asFunctionalElement1(__VLS_intrinsics.input)({
                    ...{ onChange: (...[$event]) => {
                            if (!(__VLS_ctx.showHistoryModal && __VLS_ctx.selectedSession))
                                return;
                            if (!!(__VLS_ctx.loadingHistory))
                                return;
                            if (!!(__VLS_ctx.analysisHistory.length === 0))
                                return;
                            if (!(__VLS_ctx.comparisonMode))
                                return;
                            __VLS_ctx.toggleJobSelection(job.id);
                            // @ts-ignore
                            [showCreateModal, sessions, sessions, previousPage, offset, currentPage, nextPage, closeModal, closeModal, editingId, editingId, submitForm, formData, formData, formData, formData, playersText, showUploadModal, closeUploadModal, closeUploadModal, videoStore, videoStore, videoStore, videoStore, handleVideoUpload, onFileSelected, selectedFile, selectedFile, selectedFile, selectedFile, uploadSettings, uploadSettings, showHistoryModal, selectedSession, selectedSession, closeHistoryModal, closeHistoryModal, loadingHistory, analysisHistory, analysisHistory, closeHistoryModalAndUpload, toggleComparisonMode, comparisonMode, comparisonMode, comparisonMode, comparisonMode, openComparisonModal, selectedJobsForComparison, selectedJobsForComparison, toggleJobSelection,];
                        } },
                    type: "checkbox",
                    checked: (__VLS_ctx.selectedJobsForComparison.includes(job.id)),
                    disabled: (job.status !== 'completed' && job.status !== 'done'),
                });
            }
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            (__VLS_ctx.formatDate(job.created_at));
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: (['status-badge', `status-${job.status}`]) },
            });
            /** @type {__VLS_StyleScopedClasses['status-badge']} */ ;
            (job.status);
            __VLS_asFunctionalElement1(__VLS_intrinsics.td, __VLS_intrinsics.td)({
                ...{ class: "history-actions" },
            });
            /** @type {__VLS_StyleScopedClasses['history-actions']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                ...{ onClick: (...[$event]) => {
                        if (!(__VLS_ctx.showHistoryModal && __VLS_ctx.selectedSession))
                            return;
                        if (!!(__VLS_ctx.loadingHistory))
                            return;
                        if (!!(__VLS_ctx.analysisHistory.length === 0))
                            return;
                        __VLS_ctx.viewJobResults(job);
                        // @ts-ignore
                        [formatDate, selectedJobsForComparison, viewJobResults,];
                    } },
                ...{ class: "btn-small btn-primary" },
                disabled: (job.status === 'queued' || job.status === 'processing'),
            });
            /** @type {__VLS_StyleScopedClasses['btn-small']} */ ;
            /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
            if (__VLS_ctx.isJobCompleted(job)) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                    ...{ onClick: (...[$event]) => {
                            if (!(__VLS_ctx.showHistoryModal && __VLS_ctx.selectedSession))
                                return;
                            if (!!(__VLS_ctx.loadingHistory))
                                return;
                            if (!!(__VLS_ctx.analysisHistory.length === 0))
                                return;
                            if (!(__VLS_ctx.isJobCompleted(job)))
                                return;
                            __VLS_ctx.openGoalsModal(job.id, __VLS_ctx.selectedSession.id);
                            // @ts-ignore
                            [selectedSession, isJobCompleted, openGoalsModal,];
                        } },
                    ...{ class: "btn-small btn-secondary" },
                    title: "Set goals for this analysis",
                });
                /** @type {__VLS_StyleScopedClasses['btn-small']} */ ;
                /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
            }
            if (__VLS_ctx.canExport) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                    ...{ onClick: (...[$event]) => {
                            if (!(__VLS_ctx.showHistoryModal && __VLS_ctx.selectedSession))
                                return;
                            if (!!(__VLS_ctx.loadingHistory))
                                return;
                            if (!!(__VLS_ctx.analysisHistory.length === 0))
                                return;
                            if (!(__VLS_ctx.canExport))
                                return;
                            __VLS_ctx.exportJobPdf(job.id);
                            // @ts-ignore
                            [canExport, exportJobPdf,];
                        } },
                    ...{ class: "btn-small btn-secondary" },
                    disabled: (__VLS_ctx.exportingPdf || !__VLS_ctx.isJobCompleted(job)),
                });
                /** @type {__VLS_StyleScopedClasses['btn-small']} */ ;
                /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
                (__VLS_ctx.exportingPdf ? '...' : 'Export PDF');
            }
            // @ts-ignore
            [isJobCompleted, exportingPdf, exportingPdf,];
        }
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.closeHistoryModal) },
        type: "button",
        ...{ class: "btn-secondary" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
}
if (__VLS_ctx.showResultsModal && __VLS_ctx.selectedJob) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (__VLS_ctx.closeResultsModal) },
        ...{ class: "modal-overlay" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-overlay']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: () => { } },
        ...{ class: "modal-content modal-large" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-content']} */ ;
    /** @type {__VLS_StyleScopedClasses['modal-large']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.closeResultsModal) },
        ...{ class: "modal-close-btn" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-close-btn']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.h2, __VLS_intrinsics.h2)({});
    if (__VLS_ctx.selectedJob.analysis_context) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "analysis-context-header" },
        });
        /** @type {__VLS_StyleScopedClasses['analysis-context-header']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "context-label" },
        });
        /** @type {__VLS_StyleScopedClasses['context-label']} */ ;
        (__VLS_ctx.formatAnalysisContext(__VLS_ctx.selectedJob.analysis_context));
        if (__VLS_ctx.selectedJob.camera_view) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                ...{ class: "camera-label" },
            });
            /** @type {__VLS_StyleScopedClasses['camera-label']} */ ;
            (__VLS_ctx.formatCameraView(__VLS_ctx.selectedJob.camera_view));
        }
    }
    if (__VLS_ctx.pollTimedOut) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "results-error" },
        });
        /** @type {__VLS_StyleScopedClasses['results-error']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "status-text" },
        });
        /** @type {__VLS_StyleScopedClasses['status-text']} */ ;
        (__VLS_ctx.selectedJob.status);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "status-text" },
        });
        /** @type {__VLS_StyleScopedClasses['status-text']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "modal-actions" },
        });
        /** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (__VLS_ctx.retrySelectedJob) },
            type: "button",
            ...{ class: "btn-primary" },
            disabled: (!__VLS_ctx.selectedJob.session_id),
        });
        /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
    }
    else if (__VLS_ctx.selectedJob.status === 'queued' ||
        __VLS_ctx.selectedJob.status === 'processing' ||
        __VLS_ctx.selectedJob.status === 'quick_running') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "results-loading" },
        });
        /** @type {__VLS_StyleScopedClasses['results-loading']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "results-section coach-summary-card" },
        });
        /** @type {__VLS_StyleScopedClasses['results-section']} */ ;
        /** @type {__VLS_StyleScopedClasses['coach-summary-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "summary-level" },
        });
        /** @type {__VLS_StyleScopedClasses['summary-level']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
        (__VLS_ctx.coachNarrative.summary.rating);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "status-text" },
        });
        /** @type {__VLS_StyleScopedClasses['status-text']} */ ;
        (__VLS_ctx.coachNarrative.summary.confidenceText);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "status-text" },
        });
        /** @type {__VLS_StyleScopedClasses['status-text']} */ ;
        (__VLS_ctx.coachNarrative.summary.coverageText);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "status-text" },
        });
        /** @type {__VLS_StyleScopedClasses['status-text']} */ ;
        (__VLS_ctx.coachNarrative.summary.coachSummaryText);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "status-text" },
        });
        /** @type {__VLS_StyleScopedClasses['status-text']} */ ;
        (__VLS_ctx.selectedJob.status);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "progress-bar" },
            'aria-label': "Analysis progress",
        });
        /** @type {__VLS_StyleScopedClasses['progress-bar']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
            ...{ class: "progress-bar-indeterminate" },
        });
        /** @type {__VLS_StyleScopedClasses['progress-bar-indeterminate']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "step-labels" },
        });
        /** @type {__VLS_StyleScopedClasses['step-labels']} */ ;
        for (const [step, idx] of __VLS_vFor((__VLS_ctx.progressSteps))) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                key: (idx),
                ...{ class: "step-label" },
            });
            /** @type {__VLS_StyleScopedClasses['step-label']} */ ;
            (step);
            // @ts-ignore
            [formatAnalysisContext, formatCameraView, closeHistoryModal, showResultsModal, selectedJob, selectedJob, selectedJob, selectedJob, selectedJob, selectedJob, selectedJob, selectedJob, selectedJob, selectedJob, selectedJob, closeResultsModal, closeResultsModal, pollTimedOut, retrySelectedJob, coachNarrative, coachNarrative, coachNarrative, coachNarrative, progressSteps,];
        }
    }
    else if (__VLS_ctx.selectedJob.status === 'failed') {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "results-error" },
        });
        /** @type {__VLS_StyleScopedClasses['results-error']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "status-text" },
        });
        /** @type {__VLS_StyleScopedClasses['status-text']} */ ;
        (__VLS_ctx.coachNarrative.summary.coachSummaryText);
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "modal-actions" },
        });
        /** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (__VLS_ctx.retrySelectedJob) },
            type: "button",
            ...{ class: "btn-primary" },
            disabled: (!__VLS_ctx.selectedJob.session_id),
        });
        /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
    }
    else {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "results-loaded" },
        });
        /** @type {__VLS_StyleScopedClasses['results-loaded']} */ ;
        if (__VLS_ctx.jobOutcomes) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
                ...{ class: "results-section" },
            });
            /** @type {__VLS_StyleScopedClasses['results-section']} */ ;
            const __VLS_6 = OutcomesViewer;
            // @ts-ignore
            const __VLS_7 = __VLS_asFunctionalComponent1(__VLS_6, new __VLS_6({
                outcomes: (__VLS_ctx.jobOutcomes),
            }));
            const __VLS_8 = __VLS_7({
                outcomes: (__VLS_ctx.jobOutcomes),
            }, ...__VLS_functionalComponentArgsRest(__VLS_7));
        }
        if (__VLS_ctx.jobOutcomes && __VLS_ctx.selectedJob?.status === 'completed') {
            __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
                ...{ class: "results-section" },
            });
            /** @type {__VLS_StyleScopedClasses['results-section']} */ ;
            const __VLS_11 = CoachSuggestionsPanel;
            // @ts-ignore
            const __VLS_12 = __VLS_asFunctionalComponent1(__VLS_11, new __VLS_11({
                ...{ 'onGenerate': {} },
                ...{ 'onApproveGoal': {} },
                suggestions: (__VLS_ctx.coachSuggestions),
            }));
            const __VLS_13 = __VLS_12({
                ...{ 'onGenerate': {} },
                ...{ 'onApproveGoal': {} },
                suggestions: (__VLS_ctx.coachSuggestions),
            }, ...__VLS_functionalComponentArgsRest(__VLS_12));
            let __VLS_16;
            const __VLS_17 = ({ generate: {} },
                { onGenerate: (__VLS_ctx.handleGenerateSuggestions) });
            const __VLS_18 = ({ approveGoal: {} },
                { onApproveGoal: (__VLS_ctx.handleApproveGoal) });
            var __VLS_14;
            var __VLS_15;
            if (__VLS_ctx.playerSummary) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "player-summary-toggle" },
                    ...{ style: {} },
                });
                /** @type {__VLS_StyleScopedClasses['player-summary-toggle']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                    ...{ onClick: (__VLS_ctx.togglePlayerSummary) },
                    ...{ class: "btn-toggle-summary" },
                });
                /** @type {__VLS_StyleScopedClasses['btn-toggle-summary']} */ ;
                (__VLS_ctx.showPlayerSummary ? '🙈 Hide' : '👤 Show');
            }
            if (__VLS_ctx.showPlayerSummary && __VLS_ctx.playerSummary) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ style: {} },
                });
                const __VLS_19 = PlayerSummaryCard;
                // @ts-ignore
                const __VLS_20 = __VLS_asFunctionalComponent1(__VLS_19, new __VLS_19({
                    ...{ 'onClose': {} },
                    summary: (__VLS_ctx.playerSummary),
                }));
                const __VLS_21 = __VLS_20({
                    ...{ 'onClose': {} },
                    summary: (__VLS_ctx.playerSummary),
                }, ...__VLS_functionalComponentArgsRest(__VLS_20));
                let __VLS_24;
                const __VLS_25 = ({ close: {} },
                    { onClose: (...[$event]) => {
                            if (!(__VLS_ctx.showResultsModal && __VLS_ctx.selectedJob))
                                return;
                            if (!!(__VLS_ctx.pollTimedOut))
                                return;
                            if (!!(__VLS_ctx.selectedJob.status === 'queued' ||
                                __VLS_ctx.selectedJob.status === 'processing' ||
                                __VLS_ctx.selectedJob.status === 'quick_running'))
                                return;
                            if (!!(__VLS_ctx.selectedJob.status === 'failed'))
                                return;
                            if (!(__VLS_ctx.jobOutcomes && __VLS_ctx.selectedJob?.status === 'completed'))
                                return;
                            if (!(__VLS_ctx.showPlayerSummary && __VLS_ctx.playerSummary))
                                return;
                            __VLS_ctx.showPlayerSummary = false;
                            // @ts-ignore
                            [selectedJob, selectedJob, selectedJob, retrySelectedJob, coachNarrative, jobOutcomes, jobOutcomes, jobOutcomes, coachSuggestions, handleGenerateSuggestions, handleApproveGoal, playerSummary, playerSummary, playerSummary, togglePlayerSummary, showPlayerSummary, showPlayerSummary, showPlayerSummary,];
                        } });
                var __VLS_22;
                var __VLS_23;
            }
        }
        if (__VLS_ctx.canSeeEvidence) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
                ...{ class: "results-section" },
            });
            /** @type {__VLS_StyleScopedClasses['results-section']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
            if (!__VLS_ctx.videoPlaybackSrc) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                    ...{ class: "status-text" },
                });
                /** @type {__VLS_StyleScopedClasses['status-text']} */ ;
            }
            else {
                __VLS_asFunctionalElement1(__VLS_intrinsics.video)({
                    ...{ onLoadedmetadata: (__VLS_ctx.onVideoLoaded) },
                    ref: "resultsVideoEl",
                    ...{ class: "results-video" },
                    src: (__VLS_ctx.videoPlaybackSrc),
                    controls: true,
                    preload: "metadata",
                });
                /** @type {__VLS_StyleScopedClasses['results-video']} */ ;
            }
        }
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "results-section coach-summary-card" },
        });
        /** @type {__VLS_StyleScopedClasses['results-section']} */ ;
        /** @type {__VLS_StyleScopedClasses['coach-summary-card']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "summary-level" },
        });
        /** @type {__VLS_StyleScopedClasses['summary-level']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.strong, __VLS_intrinsics.strong)({});
        (__VLS_ctx.coachNarrative.summary.rating);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "status-text" },
        });
        /** @type {__VLS_StyleScopedClasses['status-text']} */ ;
        (__VLS_ctx.coachNarrative.summary.confidenceText);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "status-text" },
        });
        /** @type {__VLS_StyleScopedClasses['status-text']} */ ;
        (__VLS_ctx.coachNarrative.summary.coverageText);
        __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
            ...{ class: "status-text" },
        });
        /** @type {__VLS_StyleScopedClasses['status-text']} */ ;
        (__VLS_ctx.coachNarrative.summary.coachSummaryText);
        __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
            ...{ class: "results-section" },
        });
        /** @type {__VLS_StyleScopedClasses['results-section']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "metrics-grid" },
        });
        /** @type {__VLS_StyleScopedClasses['metrics-grid']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "metric" },
        });
        /** @type {__VLS_StyleScopedClasses['metric']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "metric-label" },
        });
        /** @type {__VLS_StyleScopedClasses['metric-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "metric-value" },
        });
        /** @type {__VLS_StyleScopedClasses['metric-value']} */ ;
        (__VLS_ctx.formatCount(__VLS_ctx.coachNarrative.metrics.framesAnalyzed));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "metric" },
        });
        /** @type {__VLS_StyleScopedClasses['metric']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "metric-label" },
        });
        /** @type {__VLS_StyleScopedClasses['metric-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "metric-value" },
        });
        /** @type {__VLS_StyleScopedClasses['metric-value']} */ ;
        (__VLS_ctx.formatCount(__VLS_ctx.coachNarrative.metrics.totalFrames));
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "metric" },
        });
        /** @type {__VLS_StyleScopedClasses['metric']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "metric-label" },
        });
        /** @type {__VLS_StyleScopedClasses['metric-label']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
            ...{ class: "metric-value" },
        });
        /** @type {__VLS_StyleScopedClasses['metric-value']} */ ;
        (__VLS_ctx.formatPercent01(__VLS_ctx.coachNarrative.metrics.detectionRate));
        if (__VLS_ctx.isFreeTier) {
            __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
                ...{ class: "results-section" },
            });
            /** @type {__VLS_StyleScopedClasses['results-section']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
            __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                ...{ class: "status-text" },
            });
            /** @type {__VLS_StyleScopedClasses['status-text']} */ ;
        }
        else {
            __VLS_asFunctionalElement1(__VLS_intrinsics.section, __VLS_intrinsics.section)({
                ...{ class: "results-section" },
            });
            /** @type {__VLS_StyleScopedClasses['results-section']} */ ;
            __VLS_asFunctionalElement1(__VLS_intrinsics.h3, __VLS_intrinsics.h3)({});
            if (__VLS_ctx.coachNarrative.priorities.length === 0) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                    ...{ class: "status-text" },
                });
                /** @type {__VLS_StyleScopedClasses['status-text']} */ ;
            }
            for (const [p] of __VLS_vFor((__VLS_ctx.coachNarrative.priorities))) {
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    key: (p.key),
                    ...{ class: "finding-card" },
                });
                /** @type {__VLS_StyleScopedClasses['finding-card']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                    ...{ class: "priority-header" },
                });
                /** @type {__VLS_StyleScopedClasses['priority-header']} */ ;
                __VLS_asFunctionalElement1(__VLS_intrinsics.h4, __VLS_intrinsics.h4)({});
                (p.title);
                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                    ...{ class: (['severity-badge', `sev-${p.severity}`]) },
                });
                /** @type {__VLS_StyleScopedClasses['severity-badge']} */ ;
                (__VLS_ctx.severityLabel(p.severity));
                __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                    ...{ class: "finding-line" },
                });
                /** @type {__VLS_StyleScopedClasses['finding-line']} */ ;
                (p.explanation);
                __VLS_asFunctionalElement1(__VLS_intrinsics.p, __VLS_intrinsics.p)({
                    ...{ class: "finding-line" },
                });
                /** @type {__VLS_StyleScopedClasses['finding-line']} */ ;
                (p.impact);
                if (__VLS_ctx.canSeeEvidence && p.evidence) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                        ...{ class: "evidence" },
                    });
                    /** @type {__VLS_StyleScopedClasses['evidence']} */ ;
                    __VLS_asFunctionalElement1(__VLS_intrinsics.h5, __VLS_intrinsics.h5)({});
                    if (__VLS_ctx.videoDurationSec && p.evidence.badSegments.length) {
                        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                            ...{ class: "timeline" },
                        });
                        /** @type {__VLS_StyleScopedClasses['timeline']} */ ;
                        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                            ...{ class: "timeline-bar" },
                        });
                        /** @type {__VLS_StyleScopedClasses['timeline-bar']} */ ;
                        for (const [seg, sidx] of __VLS_vFor((p.evidence.badSegments))) {
                            __VLS_asFunctionalElement1(__VLS_intrinsics.div)({
                                key: (sidx),
                                ...{ class: "timeline-seg" },
                                ...{ style: (__VLS_ctx.timelineSegStyle(seg)) },
                            });
                            /** @type {__VLS_StyleScopedClasses['timeline-seg']} */ ;
                            // @ts-ignore
                            [coachNarrative, coachNarrative, coachNarrative, coachNarrative, coachNarrative, coachNarrative, coachNarrative, coachNarrative, coachNarrative, canSeeEvidence, canSeeEvidence, videoPlaybackSrc, videoPlaybackSrc, onVideoLoaded, formatCount, formatCount, formatPercent01, isFreeTier, severityLabel, videoDurationSec, timelineSegStyle,];
                        }
                    }
                    if (p.evidence.worstFrames.length) {
                        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                            ...{ class: "evidence-block" },
                        });
                        /** @type {__VLS_StyleScopedClasses['evidence-block']} */ ;
                        __VLS_asFunctionalElement1(__VLS_intrinsics.h6, __VLS_intrinsics.h6)({});
                        __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
                        for (const [w, widx] of __VLS_vFor((p.evidence.worstFrames))) {
                            __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                                key: (widx),
                                ...{ class: "evidence-row" },
                            });
                            /** @type {__VLS_StyleScopedClasses['evidence-row']} */ ;
                            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
                            (w.frameNum);
                            if (__VLS_ctx.formatMomentTime(w)) {
                                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                                    ...{ class: "evidence-time" },
                                });
                                /** @type {__VLS_StyleScopedClasses['evidence-time']} */ ;
                                (__VLS_ctx.formatMomentTime(w));
                            }
                            if (__VLS_ctx.canSeekToMoment(w)) {
                                __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                                    ...{ onClick: (...[$event]) => {
                                            if (!(__VLS_ctx.showResultsModal && __VLS_ctx.selectedJob))
                                                return;
                                            if (!!(__VLS_ctx.pollTimedOut))
                                                return;
                                            if (!!(__VLS_ctx.selectedJob.status === 'queued' ||
                                                __VLS_ctx.selectedJob.status === 'processing' ||
                                                __VLS_ctx.selectedJob.status === 'quick_running'))
                                                return;
                                            if (!!(__VLS_ctx.selectedJob.status === 'failed'))
                                                return;
                                            if (!!(__VLS_ctx.isFreeTier))
                                                return;
                                            if (!(__VLS_ctx.canSeeEvidence && p.evidence))
                                                return;
                                            if (!(p.evidence.worstFrames.length))
                                                return;
                                            if (!(__VLS_ctx.canSeekToMoment(w)))
                                                return;
                                            __VLS_ctx.jumpToMoment(w);
                                            // @ts-ignore
                                            [formatMomentTime, formatMomentTime, canSeekToMoment, jumpToMoment,];
                                        } },
                                    type: "button",
                                    ...{ class: "btn-secondary btn-small" },
                                });
                                /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
                                /** @type {__VLS_StyleScopedClasses['btn-small']} */ ;
                            }
                            // @ts-ignore
                            [];
                        }
                    }
                    if (p.evidence.badSegments.length) {
                        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                            ...{ class: "evidence-block" },
                        });
                        /** @type {__VLS_StyleScopedClasses['evidence-block']} */ ;
                        __VLS_asFunctionalElement1(__VLS_intrinsics.h6, __VLS_intrinsics.h6)({});
                        __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
                        for (const [seg, sidx] of __VLS_vFor((p.evidence.badSegments))) {
                            __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                                key: (sidx),
                                ...{ class: "evidence-row" },
                            });
                            /** @type {__VLS_StyleScopedClasses['evidence-row']} */ ;
                            __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({});
                            (seg.startFrame);
                            (seg.endFrame);
                            if (__VLS_ctx.formatSegmentTime(seg)) {
                                __VLS_asFunctionalElement1(__VLS_intrinsics.span, __VLS_intrinsics.span)({
                                    ...{ class: "evidence-time" },
                                });
                                /** @type {__VLS_StyleScopedClasses['evidence-time']} */ ;
                                (__VLS_ctx.formatSegmentTime(seg));
                            }
                            if (__VLS_ctx.canSeekToSegment(seg)) {
                                __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
                                    ...{ onClick: (...[$event]) => {
                                            if (!(__VLS_ctx.showResultsModal && __VLS_ctx.selectedJob))
                                                return;
                                            if (!!(__VLS_ctx.pollTimedOut))
                                                return;
                                            if (!!(__VLS_ctx.selectedJob.status === 'queued' ||
                                                __VLS_ctx.selectedJob.status === 'processing' ||
                                                __VLS_ctx.selectedJob.status === 'quick_running'))
                                                return;
                                            if (!!(__VLS_ctx.selectedJob.status === 'failed'))
                                                return;
                                            if (!!(__VLS_ctx.isFreeTier))
                                                return;
                                            if (!(__VLS_ctx.canSeeEvidence && p.evidence))
                                                return;
                                            if (!(p.evidence.badSegments.length))
                                                return;
                                            if (!(__VLS_ctx.canSeekToSegment(seg)))
                                                return;
                                            __VLS_ctx.jumpToSegment(seg);
                                            // @ts-ignore
                                            [formatSegmentTime, formatSegmentTime, canSeekToSegment, jumpToSegment,];
                                        } },
                                    type: "button",
                                    ...{ class: "btn-secondary btn-small" },
                                });
                                /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
                                /** @type {__VLS_StyleScopedClasses['btn-small']} */ ;
                            }
                            // @ts-ignore
                            [];
                        }
                    }
                }
                if (__VLS_ctx.canSeeDrills && p.drills.length) {
                    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
                        ...{ class: "drills" },
                    });
                    /** @type {__VLS_StyleScopedClasses['drills']} */ ;
                    __VLS_asFunctionalElement1(__VLS_intrinsics.h5, __VLS_intrinsics.h5)({});
                    __VLS_asFunctionalElement1(__VLS_intrinsics.ul, __VLS_intrinsics.ul)({});
                    for (const [d, didx] of __VLS_vFor((p.drills))) {
                        __VLS_asFunctionalElement1(__VLS_intrinsics.li, __VLS_intrinsics.li)({
                            key: (didx),
                        });
                        (d);
                        // @ts-ignore
                        [canSeeDrills,];
                    }
                }
                // @ts-ignore
                [];
            }
        }
    }
    if (__VLS_ctx.canExport) {
        __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
            ...{ class: "modal-actions" },
        });
        /** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
        __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
            ...{ onClick: (__VLS_ctx.exportPdf) },
            type: "button",
            ...{ class: "btn-primary" },
            disabled: (__VLS_ctx.exportingPdf || !__VLS_ctx.selectedJob),
        });
        /** @type {__VLS_StyleScopedClasses['btn-primary']} */ ;
        (__VLS_ctx.exportingPdf ? 'Generating PDF...' : 'Export PDF');
    }
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.closeResultsModal) },
        type: "button",
        ...{ class: "btn-secondary" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
}
if (__VLS_ctx.showGoalsModal && __VLS_ctx.goalsJobId && __VLS_ctx.goalsSessionId) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (__VLS_ctx.closeGoalsModal) },
        ...{ class: "modal-overlay" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-overlay']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: () => { } },
        ...{ class: "modal-content" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-content']} */ ;
    const __VLS_26 = GoalSetter;
    // @ts-ignore
    const __VLS_27 = __VLS_asFunctionalComponent1(__VLS_26, new __VLS_26({
        ...{ 'onClose': {} },
        ...{ 'onGoalsSaved': {} },
        jobId: (__VLS_ctx.goalsJobId),
        sessionId: (__VLS_ctx.goalsSessionId),
    }));
    const __VLS_28 = __VLS_27({
        ...{ 'onClose': {} },
        ...{ 'onGoalsSaved': {} },
        jobId: (__VLS_ctx.goalsJobId),
        sessionId: (__VLS_ctx.goalsSessionId),
    }, ...__VLS_functionalComponentArgsRest(__VLS_27));
    let __VLS_31;
    const __VLS_32 = ({ close: {} },
        { onClose: (__VLS_ctx.closeGoalsModal) });
    const __VLS_33 = ({ goalsSaved: {} },
        { onGoalsSaved: (__VLS_ctx.handleGoalsSaved) });
    var __VLS_29;
    var __VLS_30;
}
if (__VLS_ctx.showComparisonModal && __VLS_ctx.selectedSession) {
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: (__VLS_ctx.closeComparisonModal) },
        ...{ class: "modal-overlay" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-overlay']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ onClick: () => { } },
        ...{ class: "modal-content modal-large" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-content']} */ ;
    /** @type {__VLS_StyleScopedClasses['modal-large']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.closeComparisonModal) },
        ...{ class: "modal-close-btn" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-close-btn']} */ ;
    const __VLS_34 = SessionComparison;
    // @ts-ignore
    const __VLS_35 = __VLS_asFunctionalComponent1(__VLS_34, new __VLS_34({
        sessionId: (__VLS_ctx.selectedSession.id),
        selectedJobIds: (__VLS_ctx.selectedJobsForComparison),
    }));
    const __VLS_36 = __VLS_35({
        sessionId: (__VLS_ctx.selectedSession.id),
        selectedJobIds: (__VLS_ctx.selectedJobsForComparison),
    }, ...__VLS_functionalComponentArgsRest(__VLS_35));
    __VLS_asFunctionalElement1(__VLS_intrinsics.div, __VLS_intrinsics.div)({
        ...{ class: "modal-actions" },
    });
    /** @type {__VLS_StyleScopedClasses['modal-actions']} */ ;
    __VLS_asFunctionalElement1(__VLS_intrinsics.button, __VLS_intrinsics.button)({
        ...{ onClick: (__VLS_ctx.closeComparisonModal) },
        type: "button",
        ...{ class: "btn-secondary" },
    });
    /** @type {__VLS_StyleScopedClasses['btn-secondary']} */ ;
}
// @ts-ignore
[selectedSession, selectedSession, selectedJobsForComparison, canExport, exportingPdf, exportingPdf, selectedJob, closeResultsModal, exportPdf, showGoalsModal, goalsJobId, goalsJobId, goalsSessionId, goalsSessionId, closeGoalsModal, closeGoalsModal, handleGoalsSaved, showComparisonModal, closeComparisonModal, closeComparisonModal, closeComparisonModal,];
const __VLS_export = (await import('vue')).defineComponent({});
export default {};

<template>
  <div class="hocr-panel" data-testid="ocr-review-panel">
    <h3 class="hocr-title">Import from PDF/Image (Review Required)</h3>
    <p class="hocr-subtitle">
      Upload a scorecard document, review extracted JSON, then run structured dry-run validation.
      OCR/AI extraction is always non-authoritative.
    </p>

    <div class="hocr-grid">
      <label class="hocr-label">
        Source document (PDF/PNG/JPEG/WEBP)
        <input
          ref="fileInputRef"
          class="hocr-input"
          type="file"
          accept=".pdf,image/png,image/jpeg,image/webp"
          data-testid="ocr-source-file"
          @change="onFileChange"
        >
      </label>

      <label class="hocr-label">
        Extraction method
        <select v-model="extractionMethod" class="hocr-input">
          <option value="manual_candidate_json">Manual candidate JSON</option>
          <option value="pdf_text_extract">PDF text extraction (digital PDFs)</option>
          <option value="ocr_text_attachment">OCR text attached</option>
        </select>
      </label>

      <label class="hocr-label">
        Extraction confidence (0-1)
        <input
          v-model="confidenceInput"
          class="hocr-input"
          type="number"
          min="0"
          max="1"
          step="0.01"
        >
      </label>
    </div>

    <label class="hocr-label">
      Candidate structured JSON (editable)
      <textarea
        v-model="candidateJsonText"
        class="hocr-textarea"
        rows="9"
        data-testid="ocr-candidate-json"
        placeholder="{ ...historical import JSON candidate... }"
      />
    </label>

    <label class="hocr-label">
      OCR text (optional)
      <textarea
        v-model="ocrText"
        class="hocr-textarea"
        rows="4"
        data-testid="ocr-text"
        placeholder="Paste OCR text for operator review context"
      />
    </label>

    <div class="hocr-actions">
      <button class="hocr-btn hocr-btn--primary" data-testid="ocr-create-candidate" :disabled="loading || !selectedFile" @click="createCandidate">
        Create review candidate
      </button>
      <button class="hocr-btn" data-testid="ocr-save-review" :disabled="!canSaveReview" @click="submitReview">
        Save reviewed JSON
      </button>
      <button class="hocr-btn" data-testid="ocr-run-dry-run" :disabled="!canRunDryRun" @click="runDryRun">
        Dry-run reviewed JSON
      </button>
    </div>

    <label class="hocr-label">
      Reject reason
      <input v-model="rejectReason" class="hocr-input" placeholder="Why this extraction is unusable">
    </label>

    <div class="hocr-actions">
      <button class="hocr-btn hocr-btn--danger" data-testid="ocr-reject-candidate" :disabled="!canRejectCandidate" @click="rejectCandidate">
        Reject candidate
      </button>
    </div>

    <p v-if="loading" class="hocr-loading" role="status" data-testid="ocr-loading-state">{{ currentActionLabel }}</p>
    <p v-if="error" class="hocr-error" role="alert">{{ error }}</p>
    <p v-if="message" class="hocr-message" role="status" data-testid="ocr-flow-message">{{ message }}</p>

    <div v-if="candidate" class="hocr-summary" data-testid="ocr-candidate-summary">
      <p><strong>Candidate ID:</strong> <code>{{ candidate.candidate_id }}</code></p>
      <p><strong>Status:</strong> {{ candidate.status }}</p>
      <p><strong>Confidence:</strong> {{ candidate.extraction.confidence ?? 'N/A' }}</p>
      <p class="hocr-notice">{{ candidate.extraction.non_authoritative_notice }}</p>
      <p v-if="candidate.rejection_reason"><strong>Rejected:</strong> {{ candidate.rejection_reason }}</p>

      <div v-if="candidate.extraction.method === 'pdf_text_extract'" class="hocr-extracted-text" data-testid="ocr-extracted-text-preview">
        <p class="hocr-notice hocr-notice--warning">
          ⚠ Extracted text is <strong>not official match data</strong>. Operator review and correction are required before dry-run validation.
        </p>
        <template v-if="candidate.extraction.ocr_text">
          <p><strong>Extracted text preview (non-authoritative):</strong></p>
          <pre class="hocr-extracted-pre" data-testid="ocr-extracted-text-content">{{ candidate.extraction.ocr_text }}</pre>
        </template>
        <p v-else class="hocr-notice hocr-notice--fallback" data-testid="ocr-no-text-message">
          No extractable text was found in this PDF. This may be a scanned image PDF.
          Image OCR is not performed — please enter the scorecard JSON manually in the field above.
        </p>
        <ul v-if="candidate.extraction.warnings && candidate.extraction.warnings.length" class="hocr-warnings">
          <li v-for="(w, i) in candidate.extraction.warnings" :key="i">{{ w }}</li>
        </ul>
      </div>
    </div>

    <div v-if="dryRunResult" class="hocr-dryrun" data-testid="ocr-dry-run-result">
      <h4>Dry-run result: {{ dryRunResult.status }}</h4>
      <p>{{ dryRunResult.message }}</p>
      <p v-if="dryRunResult.dry_run_batch_id">
        Structured batch: <code>{{ dryRunResult.dry_run_batch_id }}</code>
      </p>
      <ul v-if="dryRunResult.dry_run_result.errors.length">
        <li v-for="(issue, idx) in dryRunResult.dry_run_result.errors" :key="idx">
          {{ issue.code }} — {{ issue.message }}
        </li>
      </ul>
    </div>

    <p v-else class="hocr-empty" data-testid="ocr-empty-state">
      No OCR review candidate yet. Upload a PDF/image scorecard to create a non-authoritative draft for operator review.
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import {
  historicalOcrCreateCandidate,
  historicalOcrDryRunCandidate,
  historicalOcrRejectCandidate,
  historicalOcrSubmitReview,
  type HistoricalOcrReviewCandidateResponse,
  type HistoricalOcrReviewDryRunResponse,
} from '@/services/api'

const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const extractionMethod = ref<'manual_candidate_json' | 'pdf_text_extract' | 'ocr_text_attachment'>('manual_candidate_json')
const confidenceInput = ref('')
const candidateJsonText = ref('')
const ocrText = ref('')
const rejectReason = ref('')

const candidate = ref<HistoricalOcrReviewCandidateResponse | null>(null)
const dryRunResult = ref<HistoricalOcrReviewDryRunResponse | null>(null)
const loading = ref(false)
const currentActionLabel = ref('')
const message = ref('')
const error = ref('')

const canSaveReview = computed(
  () => {
    const currentCandidate = candidate.value
    if (!currentCandidate) return false
    return !loading.value && currentCandidate.status !== 'rejected'
  },
)
const canRunDryRun = computed(
  () => {
    const currentCandidate = candidate.value
    if (!currentCandidate) return false
    return (
      !loading.value
      && ['ready_for_dry_run', 'dry_run_failed', 'dry_run_passed'].includes(currentCandidate.status)
    )
  },
)
const canRejectCandidate = computed(
  () => {
    const currentCandidate = candidate.value
    if (!currentCandidate) return false
    return !loading.value && currentCandidate.status !== 'rejected' && Boolean(rejectReason.value.trim())
  },
)

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

function parseCandidateJson(): Record<string, unknown> | undefined {
  if (!candidateJsonText.value.trim()) return undefined
  try {
    return JSON.parse(candidateJsonText.value) as Record<string, unknown>
  } catch (err) {
    const reason = err instanceof Error ? err.message : 'Unknown JSON parse error'
    throw new Error(`Invalid structured JSON: ${reason}`)
  }
}

async function createCandidate() {
  if (!selectedFile.value) return
  loading.value = true
  currentActionLabel.value = 'Creating OCR review candidate...'
  error.value = ''
  message.value = ''
  dryRunResult.value = null
  try {
    const parsedCandidate = parseCandidateJson()
    const created = await historicalOcrCreateCandidate({
      file: selectedFile.value,
      extractionMethod: extractionMethod.value,
      extractionConfidence: confidenceInput.value.trim() ? Number(confidenceInput.value) : null,
      candidateJson: parsedCandidate ? JSON.stringify(parsedCandidate) : undefined,
      ocrText: ocrText.value.trim() || undefined,
    })
    candidate.value = created
    if (created.candidate_json) {
      candidateJsonText.value = JSON.stringify(created.candidate_json, null, 2)
    }
    message.value = 'OCR review candidate created. Review and correct before dry-run.'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to create OCR review candidate'
  } finally {
    currentActionLabel.value = ''
    loading.value = false
  }
}

async function submitReview() {
  if (!candidate.value) return
  loading.value = true
  currentActionLabel.value = 'Saving reviewed JSON...'
  error.value = ''
  message.value = ''
  try {
    const reviewedJson = parseCandidateJson()
    if (!reviewedJson) {
      throw new Error('Reviewed JSON is required before submitting review.')
    }
    candidate.value = await historicalOcrSubmitReview(
      candidate.value.candidate_id,
      reviewedJson,
      'Reviewed by operator in Analyst Workspace.',
      [],
    )
    message.value = 'Review saved. Candidate is ready for dry-run.'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to save review'
  } finally {
    currentActionLabel.value = ''
    loading.value = false
  }
}

async function runDryRun() {
  if (!candidate.value) return
  loading.value = true
  currentActionLabel.value = 'Running structured dry-run validation...'
  error.value = ''
  message.value = ''
  try {
    dryRunResult.value = await historicalOcrDryRunCandidate(candidate.value.candidate_id, true)
    message.value = dryRunResult.value.message
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Dry-run failed'
  } finally {
    currentActionLabel.value = ''
    loading.value = false
  }
}

async function rejectCandidate() {
  if (!candidate.value || !rejectReason.value.trim()) return
  loading.value = true
  currentActionLabel.value = 'Rejecting OCR review candidate...'
  error.value = ''
  message.value = ''
  try {
    candidate.value = await historicalOcrRejectCandidate(candidate.value.candidate_id, rejectReason.value.trim())
    message.value = 'Candidate marked as rejected.'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to reject candidate'
  } finally {
    currentActionLabel.value = ''
    loading.value = false
  }
}

</script>

<style scoped>
.hocr-panel { border: 1px solid var(--color-border, #d7dbe6); border-radius: 14px; padding: 1rem; background: #fff; }
.hocr-title { margin: 0 0 0.25rem; font-size: 1.05rem; }
.hocr-subtitle { margin: 0 0 1rem; color: #4b5563; font-size: 0.9rem; }
.hocr-grid { display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
.hocr-label { display: flex; flex-direction: column; gap: 0.35rem; margin-bottom: 0.75rem; font-size: 0.85rem; }
.hocr-input, .hocr-textarea { border: 1px solid #ced4e0; border-radius: 8px; padding: 0.5rem 0.6rem; font: inherit; }
.hocr-textarea { resize: vertical; }
.hocr-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.75rem; }
.hocr-btn { border: 1px solid #cad2e5; border-radius: 8px; padding: 0.45rem 0.8rem; background: #f8f9fc; cursor: pointer; }
.hocr-btn:disabled { opacity: 0.55; cursor: not-allowed; }
.hocr-btn--primary { background: #0d6efd; color: #fff; border-color: #0d6efd; }
.hocr-btn--danger { background: #b42318; color: #fff; border-color: #b42318; }
.hocr-loading { color: #1d4ed8; margin: 0.25rem 0; }
.hocr-error { color: #b42318; margin: 0.25rem 0; }
.hocr-message { color: #065f46; margin: 0.25rem 0; }
.hocr-summary, .hocr-dryrun { margin-top: 0.8rem; padding-top: 0.8rem; border-top: 1px dashed #d7dbe6; font-size: 0.88rem; }
.hocr-empty { margin-top: 0.8rem; color: #4b5563; font-size: 0.88rem; }
.hocr-notice { font-size: 0.82rem; color: #374151; }
.hocr-notice--warning { color: #92400e; background: #fef3c7; border-radius: 6px; padding: 0.4rem 0.6rem; margin: 0.5rem 0; }
.hocr-notice--fallback { color: #374151; font-style: italic; }
.hocr-extracted-text { margin-top: 0.6rem; padding-top: 0.6rem; border-top: 1px dotted #d7dbe6; }
.hocr-extracted-pre { background: #f8f9fc; border: 1px solid #ced4e0; border-radius: 6px; padding: 0.6rem; font-size: 0.78rem; white-space: pre-wrap; word-break: break-word; max-height: 200px; overflow-y: auto; }
.hocr-warnings { margin: 0.4rem 0 0; padding-left: 1.2rem; font-size: 0.8rem; color: #92400e; }
</style>

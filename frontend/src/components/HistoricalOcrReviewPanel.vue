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
      <button class="hocr-btn" data-testid="ocr-save-review" :disabled="loading || !candidate" @click="submitReview">
        Save reviewed JSON
      </button>
      <button class="hocr-btn" data-testid="ocr-run-dry-run" :disabled="loading || !candidate" @click="runDryRun">
        Dry-run reviewed JSON
      </button>
    </div>

    <label class="hocr-label">
      Reject reason
      <input v-model="rejectReason" class="hocr-input" placeholder="Why this extraction is unusable">
    </label>

    <div class="hocr-actions">
      <button class="hocr-btn hocr-btn--danger" data-testid="ocr-reject-candidate" :disabled="loading || !candidate || !rejectReason.trim()" @click="rejectCandidate">
        Reject candidate
      </button>
    </div>

    <p v-if="error" class="hocr-error" role="alert">{{ error }}</p>
    <p v-if="message" class="hocr-message" role="status" data-testid="ocr-flow-message">{{ message }}</p>

    <div v-if="candidate" class="hocr-summary" data-testid="ocr-candidate-summary">
      <p><strong>Candidate ID:</strong> <code>{{ candidate.candidate_id }}</code></p>
      <p><strong>Status:</strong> {{ candidate.status }}</p>
      <p><strong>Confidence:</strong> {{ candidate.extraction.confidence ?? 'N/A' }}</p>
      <p class="hocr-notice">{{ candidate.extraction.non_authoritative_notice }}</p>
      <p v-if="candidate.rejection_reason"><strong>Rejected:</strong> {{ candidate.rejection_reason }}</p>
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
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

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
const extractionMethod = ref<'manual_candidate_json' | 'ocr_text_attachment'>('manual_candidate_json')
const confidenceInput = ref('')
const candidateJsonText = ref('')
const ocrText = ref('')
const rejectReason = ref('')

const candidate = ref<HistoricalOcrReviewCandidateResponse | null>(null)
const dryRunResult = ref<HistoricalOcrReviewDryRunResponse | null>(null)
const loading = ref(false)
const message = ref('')
const error = ref('')

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

function parseCandidateJson(): Record<string, unknown> | undefined {
  if (!candidateJsonText.value.trim()) return undefined
  return JSON.parse(candidateJsonText.value) as Record<string, unknown>
}

async function createCandidate() {
  if (!selectedFile.value) return
  loading.value = true
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
    loading.value = false
  }
}

async function submitReview() {
  if (!candidate.value) return
  loading.value = true
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
    loading.value = false
  }
}

async function runDryRun() {
  if (!candidate.value) return
  loading.value = true
  error.value = ''
  message.value = ''
  try {
    dryRunResult.value = await historicalOcrDryRunCandidate(candidate.value.candidate_id, true)
    message.value = dryRunResult.value.message
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Dry-run failed'
  } finally {
    loading.value = false
  }
}

async function rejectCandidate() {
  if (!candidate.value || !rejectReason.value.trim()) return
  loading.value = true
  error.value = ''
  message.value = ''
  try {
    candidate.value = await historicalOcrRejectCandidate(candidate.value.candidate_id, rejectReason.value.trim())
    message.value = 'Candidate marked as rejected.'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to reject candidate'
  } finally {
    loading.value = false
  }
}

void fileInputRef
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
.hocr-error { color: #b42318; margin: 0.25rem 0; }
.hocr-message { color: #065f46; margin: 0.25rem 0; }
.hocr-summary, .hocr-dryrun { margin-top: 0.8rem; padding-top: 0.8rem; border-top: 1px dashed #d7dbe6; font-size: 0.88rem; }
.hocr-notice { font-size: 0.82rem; color: #374151; }
</style>

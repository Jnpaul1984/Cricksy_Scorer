# Phase 7B — OCR Extraction Engine Integration Audit + Spec Lock

- Date: 2026-05-15
- Author: Copilot
- Classification: **Docs-only — audit + spec-lock. No OCR engine implementation added.**
- Phase: 7B (sub-phase of Phase 7 — Historical Match Ingestion: PDF/Image/OCR Review Flow)
- Repository: `Jnpaul1984/Cricksy_Scorer`

---

## 1. Executive Summary

Phase 7B audits the existing Phase 7/7A OCR review pipeline, evaluates OCR extraction engine
options, and produces a locked spec that governs how OCR extraction must be integrated safely
in a future implementation phase (Phase 7C).

**Key finding:** The current architecture is already correct and safe. The Phase 7 workflow
stores uploaded PDF/image source documents and requires operators to manually supply structured
JSON candidate data. No automatic OCR extraction engine is integrated yet. This is the safest
possible starting point.

**Recommendation:** Adopt a **Hybrid path (Option 6)** — keep the current manual candidate
JSON path as the default production mode, and add optional local PDF text extraction (for
digitally generated PDFs only) as the first incremental engine slice in Phase 7C. Local
Tesseract-based image OCR may follow in a subsequent sub-phase once the extraction boundary
contract and confidence schema are validated in production.

**Critical boundary rule — unchanged from Phase 7:** OCR extraction output must remain
non-authoritative. OCR must never directly create, mutate, or apply official cricket match
truth. All extraction output must pass through the existing review → dry-run → explicit apply
chain.

---

## 2. Current Phase 7/7A Workflow Recap

### 2.1 Phase 7 — Core pipeline

Phase 7 established a governed candidate intake pipeline for scanned scorecards, PDFs, and
phone photos:

```text
PDF/Image upload  (POST /api/historical-import/json/ocr-review/candidates)
→ file validation (type, size, magic-bytes)
→ candidate stored with status="uploaded" | "needs_review"
→ operator reviews / corrects structured JSON candidate
→ PATCH /review  →  status="ready_for_dry_run"
→ POST /dry-run  →  existing historical JSON dry-run validation
→ if passed: handoff batch id created
→ explicit apply only via existing /batches/{batch_id}/apply endpoint
```

No automatic extraction engine was integrated. The current supported `extraction_method` is
`manual_candidate_json` (operator supplies the structured JSON alongside the uploaded
document).

### 2.2 Phase 7A — Operator workflow validation

Phase 7A validated the operator UX, added explicit empty/loading states, tightened dry-run
gating (rejected candidates cannot be dry-run), improved error messaging, and added focused
unit coverage for `HistoricalOcrReviewPanel`. All gates were green in GitHub Actions.

See: `docs/PHASE_7A_OCR_REVIEW_FLOW_MANUAL_QA.md`

---

## 3. Existing Code and Assets Audited

### 3.1 Backend — OCR review candidate endpoints

File: `backend/routes/historical_import.py`

| Endpoint | Method | Description |
|---|---|---|
| `/api/historical-import/json/ocr-review/candidates` | `POST` | Upload source document + create candidate |
| `/api/historical-import/json/ocr-review/candidates/{id}` | `GET` | Fetch candidate details |
| `/api/historical-import/json/ocr-review/candidates/{id}/review` | `PATCH` | Submit reviewed/corrected JSON |
| `/api/historical-import/json/ocr-review/candidates/{id}/reject` | `POST` | Reject candidate |
| `/api/historical-import/json/ocr-review/candidates/{id}/dry-run` | `POST` | Validate reviewed JSON via existing dry-run contract |

The `dry-run` endpoint re-uses `build_dry_run_response()` from
`backend/services/historical_import_preview.py` — the same validation service used for the
Phase 5 structured JSON import. No special OCR-only validation path exists; OCR candidates
must pass the same structured import contract as any other batch.

### 3.2 Backend — Schemas

File: `backend/api/schemas/historical_import.py`

| Schema | Purpose |
|---|---|
| `HistoricalOcrReviewStatus` | 9-state literal: `uploaded` → `extracted` → `needs_review` → `reviewed` → `ready_for_dry_run` → `dry_run_failed` → `dry_run_passed` → `rejected` → `applied_via_structured_import_only` |
| `HistoricalOcrSourceDocument` | Source file metadata (filename, content_type, size_bytes, storage reference) |
| `HistoricalOcrExtractionMetadata` | Extraction provenance: method, confidence (0–1 float or null), uncertainty_flags (string list), ocr_text (optional raw text), non_authoritative_notice (hardcoded string) |
| `HistoricalOcrReviewCandidateResponse` | Full candidate response including source doc, extraction metadata, candidate_json, reviewed_json, dry_run_result |
| `HistoricalOcrReviewUpdateRequest` | Operator correction payload: reviewed_json (dict), reviewer_notes (str), uncertainty_flags (list[str]) |
| `HistoricalOcrRejectRequest` | reason (str, 3–500 chars) |
| `HistoricalOcrDryRunRequest` | record_preview (bool, default True) |
| `HistoricalOcrDryRunResponse` | candidate_id, status, dry_run_result, dry_run_batch_id, message |

### 3.3 Backend — File validation constants

File: `backend/routes/historical_import.py` (lines 89–99)

```python
PHASE_7_MAX_DOCUMENT_BYTES = 10 * 1024 * 1024  # 10 MB
PHASE_7_ALLOWED_DOCUMENT_CONTENT_TYPES = frozenset({
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
})
PHASE_7_ALLOWED_DOCUMENT_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".webp"})
```

Validation logic checks both `Content-Type` and file extension, rejects empty payloads,
rejects oversized payloads (`413`), rejects unsupported types (`415`), and validates that
`extraction_confidence` is in `[0, 1]` if provided.

### 3.4 Frontend — HistoricalOcrReviewPanel

File: `frontend/src/components/HistoricalOcrReviewPanel.vue`

Full candidate lifecycle UI:
- File picker (PDF/PNG/JPEG/WEBP)
- Extraction method selector (`manual_candidate_json` | `ocr_text_attachment`)
- Extraction confidence input (0–1)
- Candidate JSON textarea (editable)
- OCR text textarea (optional context)
- Create / Save review / Dry-run / Reject actions
- Loading, empty, error, and message states
- Candidate summary (status, confidence, non-authoritative notice)
- Dry-run result display with validation errors

### 3.5 Frontend — API client functions

File: `frontend/src/services/api.ts`

| Function | Maps to |
|---|---|
| `historicalOcrCreateCandidate` | POST `/ocr-review/candidates` |
| `historicalOcrGetCandidate` | GET `/ocr-review/candidates/{id}` |
| `historicalOcrSubmitReview` | PATCH `/ocr-review/candidates/{id}/review` |
| `historicalOcrDryRunCandidate` | POST `/ocr-review/candidates/{id}/dry-run` |
| `historicalOcrRejectCandidate` | POST `/ocr-review/candidates/{id}/reject` |

### 3.6 Test coverage

| Suite | File | Tests | CI gate |
|---|---|---|---|
| Backend OCR review flow | `backend/tests/test_historical_ocr_review_flow.py` | 7 tests | `pytest tests/test_historical_ocr_review_flow.py` |
| Frontend unit | `frontend/tests/unit/HistoricalOcrReviewPanel.spec.ts` | 4 tests | `npm run test:unit -- HistoricalOcrReviewPanel.spec.ts` |
| Frontend E2E | `frontend/cypress/e2e/historical_import_review_flow.cy.ts` | 1 flow test | `npm run test:e2e:import` |

Backend tests cover: valid PDF upload, unsupported file rejection, oversized file rejection,
malformed uncertainty_flags rejection, non-authoritative boundary (no official match created),
correction update, dry-run pass with handoff batch, dry-run failure with validation errors,
rejected candidate cannot dry-run.

Frontend unit tests cover: empty state display, loading state, dry-run gating + rejection
block, malformed JSON parse error prefix.

E2E test covers: full flow with intercepts — panel visible, non-authoritative copy present,
candidate creation, review save, dry-run pass, handoff batch id display.

### 3.7 Existing backend dependencies relevant to OCR

From `backend/requirements.txt`:

| Package | Current version | OCR relevance |
|---|---|---|
| `opencv-python-headless` | `4.8.1.78` | Image preprocessing (thresholding, deskew) — present but not yet used for OCR |
| `mediapipe` | `0.10.31` | Pose/video detection — not relevant to OCR |
| `Pillow` / `PIL` | Not currently listed | Would be required for image preprocessing with Tesseract |
| `pytesseract` | Not listed | Would be required for Tesseract-based image OCR |
| `pdfplumber` | Not listed | Would be required for PDF text extraction |
| `PyMuPDF` (fitz) | Not listed | Alternative PDF text extraction |
| `pdf2image` | Not listed | Would be required for PDF → image conversion before Tesseract |

No OCR extraction dependency is currently present in the backend runtime. The uploaded
source documents are stored but not parsed. The only functioning extraction method is
`manual_candidate_json`.

### 3.8 Deployment constraints observed

- CI runs on GitHub-hosted Ubuntu runners.
- Tesseract binary would require `apt-get install tesseract-ocr` in the Docker image or CI
  runner — this is not currently configured.
- The Docker Compose stack (`docker compose up -d db backend`) does not include a Tesseract
  image layer.
- No S3 bucket is configured by default in development; the backend falls back to local disk
  storage (`_store_bytes_with_fallback`).
- `PHASE_7_MAX_DOCUMENT_BYTES = 10 MB` is the current upload cap.

---

## 4. OCR Engine Options Comparison Table

| # | Option | Accuracy | Cost | Privacy / Data exposure | Infra complexity | Dependency / runtime risk | CI testability | Speed | Handwritten scorecard | Tabular cricket scorecard | Confidence support | Non-authoritative compliance |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Manual extraction input only** | Operator-dependent (can be perfect if operator is careful) | None | None — no file leaves the server boundary | None | None — no new dep | ✅ Fully testable today | Dependent on operator | ✅ Operator can correct any layout | ✅ Operator can parse any table format | Operator supplies confidence manually via `extraction_confidence` field | ✅ Fully safe — operator is the authority |
| 2 | **Local Tesseract-based OCR** | 60–85% on clean print; ≤40% on handwritten/blurry | Free (open-source) | None — stays in runtime | Medium: apt/Docker layer; `pytesseract`, `pdf2image`, `Pillow` | Medium: binary install in Docker; version pinning; CI apt layer | ✅ Testable with mocked subprocess | Seconds per page | ⚠️ Poor on handwritten; deskew required | ⚠️ Table structure extraction unreliable without custom parsing | ✅ Tesseract provides per-word confidence; must be mapped to field-level flags | ✅ Output feeds candidate only; review wall enforced |
| 3 | **PDF text extraction (digitally generated PDFs)** | 95–100% for digital PDFs; 0% for scanned PDFs | Free (`pdfplumber` / `PyMuPDF`) | None — stays in runtime | Low: single Python dep | Low: `pdfplumber` or `PyMuPDF` pip install | ✅ Fully testable with PDF fixtures | Fast (< 0.5 s per page) | N/A — only works on digital PDFs | ✅ Excellent for digital scorecards with consistent structure | ✅ Detection of text vs. scanned image provides binary confidence signal | ✅ Output feeds candidate only; review wall enforced |
| 4 | **Image preprocessing + Tesseract OCR** | 70–90% on clean photos with preprocessing; still poor on handwritten | Free | None — stays in runtime | High: OpenCV (already present), `pytesseract`, `pdf2image`, `Pillow`; preprocessing pipeline required | Medium-high: preprocessing heuristics are fragile | ⚠️ Testable but preprocessing pipeline needs careful fixture set | Seconds per image | ⚠️ Poor unless deskewed + binarized | ⚠️ Table detection adds further complexity | ✅ Confidence per word available; per-field mapping requires heuristics | ✅ Output feeds candidate only; review wall enforced |
| 5 | **Hosted OCR service (e.g. Google Vision, AWS Textract, Azure Form Recognizer)** | 90–98% on printed scorecards; good table detection (Textract) | Per-request cost (AWS Textract: ~$0.0015/page; Google Vision: ~$0.0015/page) | **High** — source document leaves Cricksy server boundary; PII, match data, and proprietary scorecards are transmitted externally | Low–medium: SDK install; API key management; network dependency | Low runtime risk if service is stable; external dependency on third-party availability | ⚠️ Integration tests require live credentials or recorded fixture cassettes | Fast (< 2 s per page via API) | ✅ Good (hosted models include handwriting training data) | ✅ Textract/Form Recognizer include table extraction models | ✅ Field-level confidence scores returned natively | ✅ Output feeds candidate only if enforced in code |
| 6 | **Hybrid: manual first; local PDF text extraction optional; local Tesseract optional later** | Manual: operator-perfect; PDF text: 95–100% on digital; Tesseract: 60–85% on images | Free | None for local paths | Incremental: start with `pdfplumber`; add Tesseract only if validated | Incremental: adds one dep at a time | ✅ Each step independently testable | Tiered by method selected | ⚠️ Manual or Tesseract path required for handwritten | ✅ PDF text path excellent for digital; Tesseract path moderate | ✅ Method-specific confidence signal possible at each tier | ✅ All paths feed candidate; review wall enforced |

---

## 5. Recommended OCR Strategy

**Recommendation: Option 6 — Hybrid path, incremental.**

### Rationale

1. **Manual candidate JSON is already production-ready.** Phase 7 and 7A validated it end-to-end. It is the safest and most accurate path because a human operator constructs the structured JSON directly.

2. **Digital PDF text extraction is low-risk and high-reward.** Many published cricket scorecards are digitally generated PDFs (official scorecards from cricket boards, scorecard apps). `pdfplumber` is a well-maintained, MIT-licensed Python library with no binary system dependency, no privacy risk, and near-perfect extraction accuracy for digital PDFs. It can be added as a single pip install.

3. **Tesseract-based image OCR is medium-risk and should be deferred.** It requires a system binary install (breaking the current clean Docker image), produces highly variable accuracy on cricket scorecard photos, and requires a preprocessing pipeline. It should be added only after PDF text extraction is validated in production.

4. **Hosted OCR services must not be used without explicit privacy/data-governance review.** Uploading match documents to a third-party API exposes potentially proprietary or personal data. This requires a separate governance decision outside Phase 7B scope.

5. **The review wall must remain.** Regardless of which extraction method is active, all output must enter the review candidate pipeline and require operator confirmation before the dry-run handoff batch can be applied.

### Phased rollout

| Sub-phase | Scope |
|---|---|
| Phase 7C (next) | Add optional `pdfplumber`-based PDF text extraction as a new `extraction_method="pdf_text_extract"`. Detection of digital vs. scanned PDF determines whether extraction is attempted. Confidence = 1.0 for digital text; 0.0 / `fallback_to_manual` for scanned. No Tesseract. |
| Phase 7D (future) | Add optional local Tesseract image OCR (`extraction_method="tesseract_image_ocr"`) with `opencv-python-headless` preprocessing. Requires Docker layer change, CI apt install, and extensive fixture coverage before merge. |
| Phase 7E (future, conditional) | Hosted OCR service integration, only if privacy/data-governance review is approved and a business case exists. |

---

## 6. Explicit Non-Authoritative OCR Boundary Rules

These rules are binding for all present and future OCR integration work.

**Rule OCR-1: OCR output is always a candidate.**
OCR extraction output must always produce a `HistoricalOcrReviewCandidateResponse` with
`extraction.non_authoritative_notice` set. No extraction result may bypass candidate status.

**Rule OCR-2: No automatic apply.**
OCR output must never be passed directly to the historical import apply endpoint. The sequence
`ocr_extract → apply` is forbidden. Only the sequence
`ocr_extract → candidate → review → dry-run → explicit apply` is allowed.

**Rule OCR-3: Rejected candidates stay rejected.**
A candidate in `status="rejected"` must not be dry-run or applied. This is enforced at the
backend endpoint level.

**Rule OCR-4: No official match rows from extraction alone.**
Creating or dry-running an OCR candidate must never produce a row in the `games` or
`innings`/`deliveries` tables. The `POST /ocr-review/candidates` and
`POST /ocr-review/candidates/{id}/dry-run` endpoints must not call `apply_historical_batch`.

**Rule OCR-5: Training eligibility is never granted from OCR candidate status alone.**
`training_eligible=false` must be the case for any batch linked to an OCR candidate until
after the batch is explicitly applied via the governed import path with status `valid` and
`error_count=0`. This is enforced by the existing eligibility gate in
`historical_stats_aggregation_service.py`.

**Rule OCR-6: Confidence must be exposed to operators.**
Any automated extraction method must populate `extraction.confidence` (0–1) and
`extraction.uncertainty_flags` (list of flagged fields). Operators must be able to see
confidence and uncertainty data in the review UI before approving.

**Rule OCR-7: Low-confidence extractions must not auto-promote.**
A candidate extracted with `confidence < 0.70` (or with any `uncertainty_flags` present)
must remain in `needs_review` status. It must not be silently promoted to `ready_for_dry_run`
without explicit operator correction and PATCH /review call.

**Rule OCR-8: Hosted OCR services require separate governance approval.**
No hosted OCR API (Google Vision, AWS Textract, Azure Form Recognizer, or equivalent) may be
integrated without an explicit governance decision documented in a separate spec. The data
privacy implications must be reviewed before any document leaves the Cricksy server boundary.

---

## 7. Input/Output Contract for OCR Extraction Candidates

### 7.1 Candidate creation input (multipart/form-data)

| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | `UploadFile` | ✅ | PDF/PNG/JPEG/WEBP; max 10 MB |
| `extraction_method` | `str` | ✅ | `manual_candidate_json` \| `ocr_text_attachment` \| `pdf_text_extract` (future) \| `tesseract_image_ocr` (future) |
| `extraction_confidence` | `float` | ✗ | 0.0–1.0; null if unknown |
| `uncertainty_flags` | `str` (JSON array) | ✗ | List of field-level uncertainty markers |
| `candidate_json` | `str` (JSON object) | ✗ | Operator-supplied structured JSON; optional for upload-only |
| `ocr_text` | `str` | ✗ | Raw OCR text for operator review context |

### 7.2 Candidate creation output (`HistoricalOcrReviewCandidateResponse`)

```json
{
  "candidate_id": "<uuid>",
  "batch_id": "<uuid>",
  "status": "needs_review",
  "status_history": ["uploaded", "extracted", "needs_review"],
  "source_document": {
    "filename": "scorecard.pdf",
    "content_type": "application/pdf",
    "size_bytes": 102400,
    "storage": { "storage": "local", "path": "..." }
  },
  "extraction": {
    "method": "manual_candidate_json",
    "confidence": 0.82,
    "uncertainty_flags": ["team_name_low_confidence"],
    "ocr_text": null,
    "non_authoritative_notice": "OCR/AI extraction is non-authoritative and must be reviewed before historical import."
  },
  "candidate_json": { "...": "..." },
  "reviewed_json": null,
  "reviewer_notes": null,
  "rejection_reason": null,
  "validation_errors": [],
  "dry_run_result": null,
  "dry_run_batch_id": null
}
```

### 7.3 Review update input (`HistoricalOcrReviewUpdateRequest`)

```json
{
  "reviewed_json": { "...": "corrected_scorecard_data..." },
  "reviewer_notes": "Corrected team names and innings totals.",
  "uncertainty_flags": ["batting_order_uncertain"]
}
```

### 7.4 Dry-run output (`HistoricalOcrDryRunResponse`)

```json
{
  "candidate_id": "<uuid>",
  "status": "dry_run_passed",
  "dry_run_batch_id": "<handoff-batch-uuid>",
  "message": "Dry-run passed. Use /api/historical-import/json/batches/{batch_id}/apply for explicit import apply.",
  "dry_run_result": { "status": "valid", "...": "..." }
}
```

### 7.5 Future OCR-engine extraction output contract

When an automatic extraction engine is added (Phase 7C+), it must populate the same
`HistoricalOcrReviewCandidateResponse` structure. The extraction step must:

1. Attempt extraction.
2. Populate `candidate_json` with the extracted structured JSON (or `null` on failure).
3. Set `extraction.confidence` to the overall extraction confidence score.
4. Populate `extraction.uncertainty_flags` with a list of field names where confidence is low
   (e.g., `["total_runs_uncertain", "team_b_name_uncertain"]`).
5. Set `extraction.ocr_text` to the raw extracted text (for operator review context).
6. Set `status="needs_review"` regardless of confidence.

---

## 8. Confidence and Uncertainty Schema

### 8.1 Overall confidence score

| Field | Type | Range | Meaning |
|---|---|---|---|
| `extraction.confidence` | `float \| null` | 0.0–1.0 | Overall extraction confidence. `null` = not computed (manual). `1.0` = digital PDF text extraction. Lower values indicate lower OCR reliability. |

Thresholds (recommended for Phase 7C):

| Confidence | Operator experience |
|---|---|
| `null` or not set | Manual input; no automated extraction |
| `≥ 0.90` | High confidence; review still required; uncertainty flags may be empty |
| `0.70–0.89` | Medium confidence; review required; operator should check flagged fields |
| `< 0.70` | Low confidence; review required; operator should treat candidate as draft only |

### 8.2 Uncertainty flags

`extraction.uncertainty_flags` is a `list[str]` of field-level uncertainty markers.

Recommended standard flag names (to be locked in Phase 7C):

| Flag | Meaning |
|---|---|
| `team_a_name_low_confidence` | Team A name may be incorrectly extracted |
| `team_b_name_low_confidence` | Team B name may be incorrectly extracted |
| `total_runs_uncertain` | Innings total may be misread |
| `wickets_uncertain` | Wicket count may be misread |
| `overs_uncertain` | Overs value may be misread |
| `batting_order_uncertain` | Batting order sequence cannot be confirmed |
| `bowler_figures_uncertain` | Bowling figures may be misread |
| `match_date_uncertain` | Date field unclear or missing |
| `venue_uncertain` | Venue name may be incorrect |
| `layout_not_standard` | Scorecard layout does not match expected tabular format |
| `handwritten_detected` | Handwriting detected; accuracy significantly reduced |
| `scanned_pdf_no_text` | PDF is a scanned image; digital text extraction was not possible |

### 8.3 Persistence

Confidence and uncertainty flags are stored in `HistoricalImportBatch.dry_run_summary["ocr_review"]["extraction"]`
and are visible in the `HistoricalOcrReviewCandidateResponse` returned to the frontend.

---

## 9. Failure Modes and Fallback Behavior

| Failure mode | Behavior | Operator experience |
|---|---|---|
| Unsupported file type | HTTP 415; candidate not created | Clear error: "Only PDF/PNG/JPEG/WEBP scorecard documents are supported." |
| Oversized file (> 10 MB) | HTTP 413; candidate not created | Clear error with byte limit |
| Empty file body | HTTP 422; candidate not created | Error: "Uploaded document is empty." |
| Malformed `uncertainty_flags` JSON | HTTP 422; candidate not created | Error: "uncertainty_flags must be a JSON array of strings." |
| Malformed `candidate_json` | HTTP 422; candidate not created | Error: "candidate_json must be valid JSON." |
| `extraction_confidence` out of range | HTTP 422; candidate not created | Error: "extraction_confidence must be between 0 and 1." |
| OCR extraction fails / no text returned (future) | Candidate created with `candidate_json=null`, `confidence=0.0`, `uncertainty_flags=["extraction_failed"]`, `status="needs_review"` | Operator sees empty candidate JSON with explicit failure notice; can enter JSON manually |
| OCR extraction returns low confidence (future) | Candidate created with populated `candidate_json`, low confidence score, populated `uncertainty_flags` | Operator sees confidence score and flagged fields; must review before dry-run |
| Dry-run validation fails | HTTP 200 with `status="dry_run_failed"`, `validation_errors` list populated | Operator sees specific error codes (e.g., `MISSING_INNINGS`) and messages; can correct and retry |
| Reviewed JSON is missing before dry-run | HTTP 422 | Error: "No reviewed structured JSON is available. Submit review corrections first." |
| Rejected candidate dry-run attempt | HTTP 409 | Error: "Rejected OCR review candidates cannot be dry-run applied." |
| Rejected candidate review attempt | HTTP 409 | Error: "Rejected OCR review candidates cannot be reviewed." |

### 9.1 Fallback chain

If automated extraction fails or produces low-confidence results, the operator fallback
sequence is:

```text
automated extraction attempt (future)
→ if failed/low-confidence: operator reviews empty/draft candidate
→ operator enters or corrects structured JSON manually (same textarea as today)
→ PATCH /review → POST /dry-run → explicit apply
```

This fallback is already fully implemented in the current `manual_candidate_json` path.

---

## 10. File Validation Rules

The following rules are currently enforced and must remain in place for all future phases.

### 10.1 File type

- Allowed MIME types: `application/pdf`, `image/png`, `image/jpeg`, `image/jpg`, `image/webp`
- Allowed extensions: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`
- Validation: both Content-Type header and file extension are checked.
- Rejected types return HTTP 415.

### 10.2 File size

- Maximum: 10 MB (`PHASE_7_MAX_DOCUMENT_BYTES = 10 * 1024 * 1024`)
- Oversized files return HTTP 413.

### 10.3 Empty file

- Empty payload (zero bytes) returns HTTP 422.

### 10.4 Magic-byte validation (Phase 7C recommendation)

PDF text extraction in Phase 7C should additionally validate the PDF magic bytes
(`%PDF-` prefix) before attempting `pdfplumber` extraction, to prevent processing
non-PDF content that was uploaded with a PDF extension.

For image files, basic Pillow/PIL open validation (catching `UnidentifiedImageError`)
should be added before any Tesseract processing in Phase 7D.

### 10.5 Storage

Source documents are stored via `_store_bytes_with_fallback()` keyed at:
`historical-imports/{owner_scope}/{candidate_id}/ocr-review/source/{safe_document_name}`

where `safe_document_name` is a sanitized filename with the source SHA-256 hash appended.
Production deployments should store documents in S3 (controlled by `settings.s3_*`); development
environments fall back to local disk.

---

## 11. Dependency and Runtime Requirements

### 11.1 Current state (Phase 7/7A)

No new OCR dependencies are required. The current pipeline stores and manages documents
without parsing them. The `manual_candidate_json` path has zero runtime OCR dependency.

### 11.2 Phase 7C: PDF text extraction

| Dependency | Package | Justification |
|---|---|---|
| PDF text extraction | `pdfplumber>=0.11` | Pure-Python; MIT license; no system binary required; well-maintained; supports tables |
| (Alternative) | `PyMuPDF` (fitz) | AGPL-licensed (check compatibility); faster but heavier |

`pdfplumber` is preferred because it is pure-Python (no system binary install, no Docker layer change), MIT-licensed, well-maintained, and includes table detection which is useful for cricket scorecard layouts.

**Docker and CI changes required for Phase 7C:** Only a `pip install pdfplumber` addition to `backend/requirements.txt`. No system package install. No Dockerfile change.

### 11.3 Phase 7D: Tesseract image OCR (deferred)

| Dependency | Notes |
|---|---|
| `tesseract-ocr` (system binary) | `apt-get install tesseract-ocr tesseract-ocr-eng` required in Dockerfile / CI runner |
| `pytesseract` (Python binding) | `pip install pytesseract` |
| `pdf2image` (PDF→image) | `pip install pdf2image`; requires `poppler-utils` (system binary) |
| `Pillow` (image preprocessing) | `pip install Pillow` (or add to requirements.txt) |
| `opencv-python-headless` (preprocessing) | Already present at `4.8.1.78` |

**Docker and CI changes required for Phase 7D:** Dockerfile must be updated to install
`tesseract-ocr`, `tesseract-ocr-eng`, and `poppler-utils` via `apt-get`. CI workflow must be
updated to install these system packages on the Ubuntu runner. This is a non-trivial
infrastructure change.

### 11.4 Phase 7E: Hosted OCR (deferred, governance required)

Not specced at this time. Requires separate privacy/data-governance review.

---

## 12. CI / Testing Plan

### 12.1 Current state

All Phase 7/7A tests pass in GitHub Actions. The CI workflow (`.github/workflows/ci.yml`) does not run for docs-only changes (paths-ignore includes `**.md` and `docs/**`).

Backend tests run in `CRICKSY_IN_MEMORY_DB=1` mode (SQLite, no Postgres required).

The E2E import suite (`npm run test:e2e:import` → `historical_import_review_flow.cy.ts`) uses only API intercepts and does not require a live backend.

### 12.2 Phase 7C test requirements (PDF text extraction)

Before PDF text extraction integration can merge, the following tests are required:

| Test | Type | Description |
|---|---|---|
| `test_pdf_text_extract_digital_pdf` | Backend unit | Verify that a digital PDF produces a populated `candidate_json` with `confidence=1.0` and `uncertainty_flags=[]` |
| `test_pdf_text_extract_scanned_pdf` | Backend unit | Verify that a scanned/image-only PDF falls back gracefully with `candidate_json=null`, `confidence=0.0`, and `uncertainty_flags=["scanned_pdf_no_text"]` |
| `test_pdf_text_extract_non_authoritative_boundary` | Backend integration | Verify `GET /games/results` count unchanged after PDF text extract candidate creation |
| `test_pdf_text_extract_dry_run_to_handoff` | Backend integration | Verify PDF-extracted candidate can be reviewed + dry-run to produce a handoff batch id without official match creation |
| Frontend unit: `pdf_text_extract_method_displayed` | Frontend unit | Verify extraction method `pdf_text_extract` displays correctly in the panel with confidence and flags |
| E2E import suite update | Cypress E2E | Add intercept scenario for `extraction_method="pdf_text_extract"` with mock confidence + uncertainty flags |

### 12.3 Phase 7D test requirements (Tesseract, deferred)

Before Tesseract integration can merge:

| Test | Type | Description |
|---|---|---|
| Tesseract subprocess mock test | Backend unit | Mock `pytesseract.image_to_data` and verify confidence mapping to `extraction.confidence` and `uncertainty_flags` |
| Low confidence block test | Backend unit | Verify `confidence < 0.70` produces correct uncertainty flags |
| Handwritten detection test | Backend unit | Verify handwritten scorecard photo produces `handwritten_detected` flag |
| CI apt install verification | CI workflow | Confirm `tesseract-ocr` system package available in GitHub Actions runner |
| Docker smoke test | Docker | Verify backend container starts and health check passes after adding system packages |

### 12.4 No-regression test gates (all phases)

These gates must remain green before any OCR engine integration merges:

- `pytest tests/test_historical_ocr_review_flow.py` — 7 existing tests
- `pytest tests/test_historical_import*.py` — existing import suite
- `pytest tests/integration/` — integration suite
- `npm run test:unit -- HistoricalOcrReviewPanel.spec.ts` — 4 unit tests
- `npm run type-check` — TypeScript
- `npm run build-only` — frontend build
- `ruff check .` + `ruff format --check .` — backend linting
- `mypy --config-file pyproject.toml --explicit-package-bases .` — backend types

---

## 13. Frontend / Operator UX Implications

### 13.1 Current UX (Phase 7/7A — manual only)

The `HistoricalOcrReviewPanel` currently shows:
- Extraction method selector: `manual_candidate_json` | `ocr_text_attachment`
- Confidence input (operator-supplied; optional)
- Candidate JSON textarea (operator constructs or pastes JSON)
- Non-authoritative notice prominently displayed

This is correct and should remain the default experience.

### 13.2 Phase 7C UX additions (PDF text extraction)

When PDF text extraction is integrated, the operator experience should change as follows:

- If the uploaded file is a digital PDF and `extraction_method="pdf_text_extract"` is
  selected, the backend attempts extraction and pre-populates `candidate_json`.
- The confidence score and uncertainty flags are displayed in the candidate summary panel.
- Flagged fields should be highlighted or labeled (e.g., `[?] team_b_name_low_confidence`)
  so operators know which fields to verify.
- The JSON textarea should remain fully editable regardless of confidence.
- The non-authoritative notice must remain visible for all automated extraction results.
- Operators must still click "Save reviewed JSON" (PATCH /review) before "Dry-run reviewed JSON".
- The UI should not offer an "auto-approve" or skip-review path.

### 13.3 Uncertainty flags display

Recommended: render uncertainty flags as a badge list beneath the confidence score:

```
Confidence: 0.74
⚠ team_b_name_low_confidence
⚠ total_runs_uncertain
```

This is not implemented yet. Phase 7C implementation should include this UX addition.

### 13.4 Existing import panels unaffected

The JSON import panel (`HistoricalImportPanel`) and bulk ZIP import panel remain unaffected
by all OCR changes. No changes to those panels are required in Phase 7C or 7D.

---

## 14. Rollout Plan

### Phase 7C rollout (PDF text extraction)

1. Add `pdfplumber` to `backend/requirements.txt`.
2. Add extraction service function `extract_pdf_text_candidate(payload: bytes) -> HistoricalOcrExtractionResult` in a new `backend/services/ocr_extraction_service.py`.
3. When `extraction_method="pdf_text_extract"` is requested in `POST /ocr-review/candidates`, call the extraction service and populate `candidate_json`, `confidence`, and `uncertainty_flags` in the creation response.
4. Scanned PDFs (no extractable text) must fall back gracefully: `candidate_json=null`, `confidence=0.0`, `uncertainty_flags=["scanned_pdf_no_text"]`.
5. Add all required tests from Section 12.2.
6. Update `HistoricalOcrReviewPanel.vue` to display confidence score and uncertainty flags.
7. Update E2E suite with PDF-extract intercept scenario.
8. Run all no-regression gates (Section 12.4) before merge.
9. Announce in release notes that PDF text extraction is now available as an optional extraction method (manual JSON remains the default).

### Feature flag consideration

Phase 7C should expose PDF text extraction behind a backend feature flag
(`settings.ocr_pdf_text_extract_enabled: bool = False`) to allow safe toggling without
redeployment. The flag defaults to `False` (manual-only mode) and can be enabled via
environment variable after testing.

---

## 15. Rollback Plan

### Phase 7C rollback

1. Set `OCR_PDF_TEXT_EXTRACT_ENABLED=false` (or equivalent env var) to disable the extraction path. Existing candidates are unaffected.
2. If `pdfplumber` must be removed, `pip uninstall pdfplumber` and remove from `requirements.txt`. No database migration required (schema unchanged).
3. All existing manual candidates remain valid and unaffected.
4. The review → dry-run → apply pipeline continues to function with `manual_candidate_json` only.

### General OCR rollback guarantee

Because OCR output feeds only into the candidate pipeline (never directly into official match
tables), any OCR integration can be rolled back at the `extraction_method` level without
affecting any official match records, scorecards, analytics, or training-eligible data.

---

## 16. Follow-Up Implementation Phase Recommendation — Phase 7C

Based on this audit and spec-lock, Phase 7C is recommended with the following scope:

**Title:** `Phase 7C — PDF Text Extraction Integration (Smallest Safe OCR Slice)`

**Scope:**
- Add `pdfplumber` as the first OCR extraction dependency.
- Implement optional `extraction_method="pdf_text_extract"` in `POST /ocr-review/candidates`.
- Add `backend/services/ocr_extraction_service.py` with `extract_pdf_text_candidate()`.
- Populate `candidate_json`, `confidence`, and `uncertainty_flags` from PDF text extraction.
- Graceful fallback for scanned PDFs.
- Add feature flag `settings.ocr_pdf_text_extract_enabled`.
- Add all required tests (Section 12.2).
- Update frontend to display confidence and uncertainty flags.
- Run all no-regression gates before merge.
- No Tesseract. No hosted OCR. No auto-apply.

**Not in Phase 7C scope:**
- Tesseract-based image OCR (Phase 7D).
- Hosted OCR service integration (Phase 7E, pending governance).
- Any change to official match/scoring truth.
- Any change to Phase 5 structured JSON import behavior.
- Phase 8 (AI Analytics + Match Intelligence Enhancements).

---

## 17. Readiness Questions — Answered

**Q1: Should Cricksy use local OCR, hosted OCR, PDF text extraction, manual candidate input, or a hybrid approach?**

Hybrid approach (Option 6). Keep manual candidate JSON as the default production path. Add
optional local PDF text extraction (`pdfplumber`) as the first incremental slice in Phase 7C.
Hosted OCR must not be used without a separate privacy governance review.

**Q2: What is the safest smallest implementation slice for Phase 7C?**

`pdfplumber`-based PDF text extraction for digitally generated PDFs only. Single pip install.
No system binary. No Docker change. Zero impact on the existing manual path.

**Q3: What dependencies are acceptable for the current deployment environment?**

Pure-Python dependencies with no system binary requirements are acceptable immediately. System
binary dependencies (Tesseract, Poppler) require Dockerfile changes and are deferred to
Phase 7D.

**Q4: What OCR confidence data should be exposed to operators?**

Overall confidence score (0–1 float), per-field uncertainty flags (list of named strings),
and extraction method name. All three are already in the `HistoricalOcrExtractionMetadata`
schema. The frontend needs to render confidence and flags in the candidate summary panel.

**Q5: How should failed/low-confidence extraction be handled?**

Failed extraction: produce a candidate with `candidate_json=null`, `confidence=0.0`,
`uncertainty_flags=["extraction_failed"]`. The operator must enter the structured JSON
manually. Low-confidence extraction: produce a candidate with a populated but flagged
`candidate_json`. The operator must review all flagged fields before submitting PATCH /review.
Neither path auto-promotes the candidate to `ready_for_dry_run`.

**Q6: How will OCR outputs map into the existing review candidate structure?**

The extraction service must produce a `HistoricalOcrReviewCandidateResponse`-compatible
payload. The extracted text maps to `extraction.ocr_text`. The structured JSON candidate maps
to `candidate_json`. Confidence maps to `extraction.confidence`. Field-level flags map to
`extraction.uncertainty_flags`. No new schema fields are required.

**Q7: What tests are required before OCR engine integration can merge?**

See Section 12. Summary: backend unit tests for digital PDF extraction, scanned PDF fallback,
non-authoritative boundary; backend integration test for dry-run to handoff; frontend unit
test for new UI elements; updated E2E import suite intercept. All existing no-regression
gates must remain green.

**Q8: What file validation controls are required for uploaded PDFs/images?**

Current controls (Section 10) are sufficient for Phase 7C. Phase 7C should additionally add
magic-byte validation (Section 10.4) before attempting PDF text extraction. Phase 7D should
add Pillow open validation before Tesseract processing.

---

## 18. PR and Audit Summary

| Item | Status |
|---|---|
| Audit of Phase 7/7A backend endpoints | ✅ Complete — see Section 3.1 |
| Audit of backend schemas | ✅ Complete — see Section 3.2 |
| Audit of file validation rules | ✅ Complete — see Section 3.3 |
| Audit of `HistoricalOcrReviewPanel` frontend flow | ✅ Complete — see Section 3.4 |
| Audit of test:e2e:import coverage | ✅ Complete — see Section 3.6 |
| Audit of existing OCR/PDF/image dependencies | ✅ Complete — see Section 3.7 |
| Audit of deployment constraints | ✅ Complete — see Section 3.8 |
| OCR options comparison table | ✅ Complete — see Section 4 |
| Recommended OCR strategy | ✅ Complete — Option 6 hybrid; Section 5 |
| Explicit non-authoritative OCR boundary rules | ✅ Complete — Section 6 |
| Input/output contract for OCR candidates | ✅ Complete — Section 7 |
| Confidence/uncertainty schema | ✅ Complete — Section 8 |
| Failure modes and fallback behavior | ✅ Complete — Section 9 |
| File validation rules | ✅ Complete — Section 10 |
| Dependency/runtime requirements | ✅ Complete — Section 11 |
| CI/testing plan | ✅ Complete — Section 12 |
| Frontend/operator UX implications | ✅ Complete — Section 13 |
| Rollout plan | ✅ Complete — Section 14 |
| Rollback plan | ✅ Complete — Section 15 |
| Follow-up Phase 7C recommendation | ✅ Complete — Section 16 |
| Readiness questions answered | ✅ Complete — Section 17 |

**Files inspected:**
- `backend/routes/historical_import.py`
- `backend/api/schemas/historical_import.py`
- `backend/tests/test_historical_ocr_review_flow.py`
- `backend/requirements.txt`
- `frontend/src/components/HistoricalOcrReviewPanel.vue`
- `frontend/src/services/api.ts`
- `frontend/tests/unit/HistoricalOcrReviewPanel.spec.ts`
- `frontend/cypress/e2e/historical_import_review_flow.cy.ts`
- `docs/PHASE_7A_OCR_REVIEW_FLOW_MANUAL_QA.md`
- `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`
- `docs/PHASE_6F_INTELLIGENCE_OS_CLOSURE_AND_PHASE_7_READINESS.md`

**Files changed:** `docs/PHASE_7B_OCR_EXTRACTION_ENGINE_AUDIT_AND_SPEC_LOCK.md` (created),
`docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` (evidence pointer added).

**Classification:** Docs-only. No OCR engine implementation added. No OCR libraries or hosted
OCR SDKs added. No new OCR runtime behavior added. No official cricket truth behavior changed.
Phase 8 work not started.

**OCR strategy recommendation:** Hybrid — manual candidate JSON (default, current); optional
PDF text extraction via `pdfplumber` in Phase 7C; Tesseract image OCR deferred to Phase 7D.

**Follow-up Phase 7C implementation issue recommended:** Yes — see Section 16 for scope.

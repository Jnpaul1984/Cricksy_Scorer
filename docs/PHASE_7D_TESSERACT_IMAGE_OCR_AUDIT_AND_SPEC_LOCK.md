# Phase 7D — Tesseract/Image OCR Integration Audit + Spec Lock

- Date: 2026-05-15
- Author: Copilot
- Classification: **Docs-only — audit + spec-lock. No image OCR runtime implementation added.**
- Phase: 7D (sub-phase of Phase 7 — Historical Match Ingestion: PDF/Image/OCR Review Flow)
- Repository: `Jnpaul1984/Cricksy_Scorer`

---

## 1. Executive Summary

Phase 7D audits whether local Tesseract-based image OCR is a safe next step for the existing
review-only OCR candidate pipeline.

**Conclusion:** local Tesseract is **technically viable** in the current backend deployment model,
but only as a tightly scoped, optional, operator-triggered feature that remains fully
non-authoritative. The current architecture already has the right governance wall:

```text
image upload
→ OCR candidate text
→ operator review/correction
→ structured JSON candidate
→ existing dry-run validation
→ explicit apply only through governed historical import path
```

**Recommended path:** proceed only with a **small Phase 7E** if desired:

- direct image uploads only (`png` / `jpg` / `jpeg` / `webp`)
- local Tesseract only
- minimal preprocessing only
- populate **candidate OCR text + metadata only**
- no direct structured import generation
- no scanned PDF-to-image conversion in the first slice
- no hosted OCR

This keeps image OCR useful as an operator assist while preserving the Phase 7 rule that OCR
output never becomes official cricket truth by itself.

---

## 2. Current Phase 7 / 7A / 7B / 7C Workflow Recap

### Phase 7

Phase 7 established the review-only OCR candidate flow:

```text
PDF/Image upload
→ validated/stored source document
→ OCR review candidate metadata
→ operator review/correction
→ dry-run against existing historical JSON import validator
→ explicit apply through existing governed import path only
```

### Phase 7A

Phase 7A validated the operator workflow and added focused frontend safeguards:

- explicit loading/empty states
- rejection handling
- dry-run gating
- non-authoritative UX copy
- focused `HistoricalOcrReviewPanel` unit coverage

### Phase 7B

Phase 7B locked the OCR engine strategy:

- manual candidate JSON remains the safest default
- optional PDF text extraction was the next safest incremental slice
- Tesseract image OCR was deferred to this Phase 7D audit

### Phase 7C

Phase 7C implemented optional **PDF text extraction only**:

- `pdfplumber` extracts embedded text from digital PDFs
- scanned PDFs fall back safely with warnings
- image OCR is still not implemented
- extracted text remains non-authoritative review metadata only

---

## 3. Existing Code / Assets Audited

### Backend workflow and metadata

- `backend/routes/historical_import.py`
  - OCR review candidate creation, review, reject, and dry-run endpoints
  - file type/size validation for PDF + image uploads
  - current extraction metadata persistence path
- `backend/api/schemas/historical_import.py`
  - `HistoricalOcrReviewStatus`
  - `HistoricalOcrExtractionMetadata`
  - `HistoricalOcrReviewCandidateResponse`
- `backend/services/pdf_extraction_service.py`
  - existing Phase 7C PDF text extraction behavior and fallback model
- `backend/tests/test_historical_ocr_review_flow.py`
  - backend OCR review and PDF extraction coverage

### Frontend workflow and tests

- `frontend/src/components/HistoricalOcrReviewPanel.vue`
  - upload/review/dry-run UI
  - extraction method selector
  - non-authoritative notices
  - extracted text preview for PDF extraction
- `frontend/src/services/api.ts`
  - OCR review API client contract
- `frontend/tests/unit/HistoricalOcrReviewPanel.spec.ts`
  - focused unit tests
- `frontend/cypress/e2e/historical_import_review_flow.cy.ts`
  - import review flow E2E smoke
- `frontend/tests/E2E_COVERAGE_MATRIX.md`
  - import flow E2E coverage status

### Runtime / deployment / CI

- `backend/Dockerfile`
- `Dockerfile`
- `.github/workflows/ci.yml`
- `.github/workflows/deploy-backend.yml`
- `backend/requirements.txt`

### Audit observations

- image file upload is already supported at the API boundary
- current OCR candidate metadata already supports:
  - `method`
  - `confidence`
  - `uncertainty_flags`
  - `ocr_text`
  - `warnings`
  - `non_authoritative_notice`
- OpenCV is already present in backend dependencies
- Tesseract/pytesseract/pdf2image are not currently installed
- the frontend already has a natural place to show OCR text previews and warnings

### Baseline validation run during this audit

- `pytest -q backend/tests/test_historical_ocr_review_flow.py` ✅ passed
- `npm run test:unit -- HistoricalOcrReviewPanel.spec.ts` ✅ passed
- `npm ci` required `CYPRESS_INSTALL_BINARY=0`, matching current CI practice

---

## 4. Image OCR Options Comparison Table

| Option | Accuracy | Runtime / deployment complexity | Docker / ECS impact | CI / testability | Speed / performance | Operator usefulness | Handwritten limitations | Tabular limitations | Confidence / uncertainty support | Rollback safety | Non-authoritative safety |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1. Keep manual JSON + Phase 7C PDF text only | Highest when operator enters data carefully | None | None | Excellent | Best | Good for careful operators; lowest automation | None beyond operator effort | None beyond operator effort | Manual confidence only | Excellent | Excellent |
| 2. Local Tesseract, minimal preprocessing | Moderate on clean printed images; weak on poor photos | Moderate | Requires Docker image + CI changes | Good with mocks; avoid brittle real-text assertions | Usually seconds per image | Useful as raw text assist | Poor | Poor-to-moderate | Good if mapped to coarse confidence bands + flags | Good | Excellent if review wall kept |
| 3. Local Tesseract + OpenCV preprocessing | Better than option 2 on some photos; still weak on handwriting | Higher due to heuristics | Same as option 2 plus more runtime tuning | Moderate; preprocessing fixtures add brittleness | Slower and less predictable | Higher on difficult photos | Still poor | Still poor | Good | Good | Excellent if review wall kept |
| 4. Scanned PDF → image conversion → Tesseract | Moderate on clean scanned PDFs | High | Requires extra system tools and larger image | Moderate-to-low | Slowest of local options for multi-page docs | Useful for scanned PDFs, but overlaps with Phase 7C fallback path | Poor | Poor | Good | Good | Excellent if review wall kept |
| 5. Hosted OCR deferred to governance review | Often highest on printed docs/tables | Operationally simpler in code, harder in governance | No local binary cost, but adds network/service dependency | Harder without live creds/recordings | Often fast | High | Best of listed options | Best of listed options | Strong native confidence output | Medium | Only safe with explicit governance and review wall |

### Option comparison summary

- **Option 1** is the safest current state.
- **Option 2** is the smallest viable local image OCR step.
- **Option 3** should be deferred until real operator feedback proves option 2 is insufficient.
- **Option 4** should be deferred because Phase 7C already handles digital PDFs and scanned PDF
  OCR adds extra system dependencies.
- **Option 5** must remain deferred pending separate privacy/governance review.

---

## 5. Tesseract / Docker / Runtime Feasibility Assessment

### 5.1 Current backend runtime posture

The current backend image is built from `python:3.12-slim` and already performs `apt-get`
during image build. That means **adding Tesseract is feasible in principle**.

Current deployment facts observed:

- backend Docker image is built in GitHub Actions from `backend/Dockerfile`
- backend deploy flow pushes a new ECR image and reuses ECS task definitions
- ECS runtime is image-based, so required binaries must be baked into the image
- ECR image scanning blocks deploys on non-kernel HIGH/CRITICAL findings

### 5.2 Required dependencies for local image OCR

### Required for smallest local Tesseract slice

| Dependency | Type | Notes |
|---|---|---|
| `tesseract-ocr` | system package | required binary |
| `tesseract-ocr-eng` | system package | English language data |
| `pytesseract` | Python package | wrapper for invoking Tesseract |
| `Pillow` | Python package | image loading/normalization; already transitively present today but should be pinned directly if relied on |

### Already available

| Dependency | Status | Usefulness |
|---|---|---|
| `opencv-python-headless` | already installed | optional preprocessing for later phases |
| `pdfplumber` | already installed | Phase 7C digital PDF path only |

### Required only if scanned PDF OCR is added later

| Dependency | Type | Notes |
|---|---|---|
| `pdf2image` | Python package | convert PDF pages to images |
| `poppler-utils` | system package | required by `pdf2image` |

### 5.3 Wrapper acceptability

Using `pytesseract` is acceptable **only** if:

- it is pinned in `backend/requirements.txt`
- errors/timeouts are trapped into non-authoritative fallback metadata
- tests mock wrapper behavior instead of relying on exact OCR strings

### 5.4 OpenCV usefulness

OpenCV is already available and can help with:

- grayscale conversion
- thresholding
- basic denoise
- limited deskew / resize

However, it should **not** be part of the smallest Phase 7E slice because:

- preprocessing heuristics are hard to validate deterministically
- they increase runtime complexity without solving handwriting/table extraction limits
- the first safe question is whether raw OCR text helps operators at all

### 5.5 Feasibility conclusion

**Answer:** yes, local Tesseract is viable in the current deployment environment, but it is not
zero-cost. It requires:

- Dockerfile changes
- CI image/build verification
- ECR scan re-checks
- wrapper dependency pinning
- careful timeout/fallback handling

That makes it appropriate for a narrow implementation phase, not for this audit phase.

Large or low-quality images will also increase synchronous extraction time and reduce confidence,
so the first implementation slice should stay limited to single direct-image uploads within the
existing Phase 7 size guardrails.

---

## 6. Recommended Strategy

### Recommendation

Proceed to a **narrow Phase 7E** only if the team wants image OCR now.

### Smallest safe implementation slice

1. Add `extraction_method="tesseract_image_ocr"` for **direct image uploads only**.
2. Use local Tesseract with **minimal preprocessing only**.
3. Populate **`extraction.ocr_text` + confidence/flags/warnings** only.
4. Do **not** generate structured `candidate_json` automatically from image OCR.
5. Keep manual operator correction as the only way to produce structured JSON for dry-run.
6. Keep scanned PDF → image OCR deferred.
7. Keep OpenCV-heavy preprocessing deferred.
8. Keep hosted OCR deferred.

### Why this strategy is safest

- it fits the current frontend and backend candidate model
- it avoids pretending table extraction is reliable when it is not
- it keeps image OCR useful as a reading aid without claiming structured correctness
- it minimizes rollback cost to a single extraction method / dependency set

---

## 7. Explicit Non-Authoritative Image OCR Boundary Rules

These rules are binding for any future image OCR work:

1. **Image OCR output is always candidate metadata, never official truth.**
2. **Image OCR must never call apply logic directly.**
3. **The only allowed path is:** `image OCR → review candidate → human correction → dry-run → explicit apply`.
4. **`games`, `innings`, `deliveries`, player stats, results, DLS, and registry/training truth must remain unchanged until explicit governed apply.**
5. **Rejected candidates remain rejected and cannot be dry-run.**
6. **Low-confidence image OCR must be shown as uncertain, never silently trusted.**
7. **If OCR fails, the operator must still be able to complete the flow with manual JSON.**
8. **Hosted OCR remains out of scope unless separately approved by governance review.**

---

## 8. Input / Output Contract for Image OCR Candidate Metadata

### 8.1 Candidate creation input

Use the existing endpoint:

`POST /api/historical-import/json/ocr-review/candidates`

Recommended Phase 7E input contract:

| Field | Type | Rule |
|---|---|---|
| `file` | upload | required; `png` / `jpg` / `jpeg` / `webp` only for the first slice |
| `extraction_method` | string | required; `tesseract_image_ocr` |
| `candidate_json` | JSON object string | optional operator seed only |
| `ocr_text` | string | optional operator override only |
| `extraction_confidence` | float 0-1 | optional operator override only |
| `uncertainty_flags` | JSON string array | optional operator override only |

### 8.2 Candidate creation output

Keep the existing `HistoricalOcrReviewCandidateResponse` envelope.

Recommended `extraction` payload for image OCR:

```json
{
  "method": "tesseract_image_ocr",
  "confidence": 0.42,
  "uncertainty_flags": [
    "low_overall_confidence",
    "table_layout_uncertain"
  ],
  "ocr_text": "raw extracted scorecard text...",
  "warnings": [
    "Image OCR is non-authoritative and may miss rows, totals, or names."
  ],
  "non_authoritative_notice": "OCR/AI extraction is non-authoritative and must be reviewed before historical import."
}
```

### 8.3 Recommended future optional metadata

If Phase 7E needs more auditability, add optional JSON-only fields inside the extraction block
without changing official match schema:

- `engine_name`
- `engine_version`
- `language`
- `preprocessing_steps`
- `duration_ms`
- `input_width`
- `input_height`

These are useful for debugging and rollback analysis but are not required for the first slice.

---

## 9. Confidence / Uncertainty Schema

### 9.1 Overall confidence

Image OCR should expose a coarse overall score in `[0, 1]`, derived from Tesseract token-level
confidence but **not** presented as proof of correctness.

Recommended display bands:

| Range | Band | UX treatment |
|---|---|---|
| `0.80 - 1.00` | higher confidence | still requires human review |
| `0.50 - 0.79` | medium confidence | warning banner + careful review prompt |
| `0.00 - 0.49` | low confidence | strong warning; operator should expect manual entry/correction |
| `null` | unavailable | show as unknown confidence |

### 9.2 Recommended uncertainty flags

- `low_overall_confidence`
- `partial_text_only`
- `image_blurry`
- `low_resolution`
- `handwriting_detected_or_suspected`
- `table_layout_uncertain`
- `names_uncertain`
- `totals_uncertain`
- `ocr_timeout`
- `ocr_failed`

### 9.3 Confidence rule

No confidence score may change governance behavior. Confidence affects **operator messaging only**.

---

## 10. Failure Modes and Fallback Behavior

| Failure mode | Expected behavior |
|---|---|
| Tesseract unavailable in runtime | candidate still created with `confidence=0.0`, `ocr_text=null`, `warnings`, `ocr_failed`-style flag |
| Wrapper/runtime exception | same fallback behavior; never auto-fail into official import |
| Timeout on large/poor image | candidate still created; show timeout warning and allow manual JSON |
| Very low confidence output | create candidate, show strong warning, keep operator in review flow |
| Handwritten scorecard | warn that handwriting support is unreliable; expect manual correction |
| Tabular scorecard row misread | preserve raw OCR text only; operator manually maps to structured JSON |
| Unsupported future scanned PDF path | keep using Phase 7C fallback and manual JSON; do not auto-convert in first slice |

### Fallback principle

Failure must degrade to **manual candidate JSON**, not to an error that blocks intake entirely.

---

## 11. CI / Testing Strategy

### 11.1 Deterministic validation

Yes, CI can validate image OCR safely **without brittle full-text assertions**.

Recommended strategy:

- unit-test the OCR service with `pytesseract` mocked
- assert:
  - method name
  - confidence band / range
  - uncertainty flags
  - warnings
  - candidate status transitions
  - non-authoritative notice
- integration-test the endpoint with the OCR service mocked
- keep one or two tiny fixture images only if needed for sanity, and assert coarse substrings only

### 11.2 What not to do

- do not assert full exact OCR output strings for real images
- do not require live handwritten OCR accuracy in CI
- do not make CI depend on scanned PDF conversion in the first slice

### 11.3 Docker / CI implications

Phase 7E would require CI updates to:

- build an image containing Tesseract
- verify tests pass with that image/runtime
- re-check ECR vulnerability scan outcomes after new system packages

---

## 12. Frontend / Operator UX Implications

The current `HistoricalOcrReviewPanel` already provides most of the needed UX primitives:

- source file upload
- extraction method selector
- OCR text area / preview space
- confidence display
- warning / notice copy
- manual JSON editing
- review / dry-run / reject actions

### Recommended Phase 7E UX additions

- add `Tesseract image OCR (review required)` to extraction method options
- show extracted raw text preview exactly as non-authoritative helper text
- show confidence band and uncertainty flags
- show stronger copy for low confidence and handwriting/table limitations
- keep manual JSON textarea primary for actual importable structure

### Operator rule

Low-confidence OCR should prompt:

> “Use OCR text as a draft reading aid only. Verify names, totals, wickets, and over-by-over rows manually before dry-run.”

---

## 13. Rollout Plan

### Phase 7E, if approved

1. Add pinned runtime dependencies (`tesseract-ocr`, `tesseract-ocr-eng`, `pytesseract`).
2. Add backend service for image OCR with timeout/fallback behavior.
3. Add `tesseract_image_ocr` as a new optional extraction method for image uploads only.
4. Store raw OCR text and metadata only.
5. Add focused backend unit/integration tests with mocks.
6. Add focused frontend unit updates for warnings/confidence display.
7. Keep E2E coverage intercept-based; do not require live OCR in browser tests.
8. Roll out behind an operator-triggered option, not as default behavior.

---

## 14. Rollback Plan

Rollback remains straightforward if the implementation is kept narrow:

1. remove or disable `tesseract_image_ocr` from the frontend selector
2. stop invoking the image OCR service in candidate creation
3. remove Docker / requirements additions
4. retain existing manual JSON + Phase 7C PDF text paths unchanged

Because image OCR is non-authoritative candidate metadata only, rollback does **not** require
data repair of official match truth.

---

## 15. Follow-up Recommendation and Readiness Answers

### Recommendation

**Proceed to Phase 7E only as a narrow local Tesseract image-text assist feature.**

Do **not** include:

- scanned PDF → image conversion
- OpenCV-heavy preprocessing by default
- hosted OCR
- direct structured JSON generation from image OCR

### Readiness answers

1. **Is local Tesseract viable for the current backend deployment environment?**
   **Yes, technically.** The Docker/ECS model can support it, but it requires image and CI
   changes.

2. **What Docker/system dependencies would be required?**
   At minimum: `tesseract-ocr`, `tesseract-ocr-eng`, and a pinned Python wrapper
   (`pytesseract`). If scanned PDFs are later supported, add `pdf2image` + `poppler-utils`.

3. **Can CI validate image OCR deterministically without brittle results?**
   **Yes.** Prefer mocked OCR service tests and coarse metadata assertions over exact OCR text.

4. **Should scanned PDF support be included with image OCR or deferred?**
   **Deferred.** Phase 7C already covers digital PDFs, and scanned PDF OCR adds more runtime
   complexity than the smallest safe slice should take on.

5. **How should low-confidence image OCR be shown to operators?**
   Via confidence band, uncertainty flags, warnings, and explicit non-authoritative copy in the
   review panel.

6. **How should failed image OCR fall back to manual candidate JSON?**
   Candidate creation should still succeed with `ocr_text=null` or partial text, warnings, and
   low-confidence flags so the operator can continue manually.

7. **What is the smallest safe implementation slice for Phase 7E?**
   Direct image upload → local Tesseract → raw OCR text + metadata only → operator manually
   produces structured JSON.

8. **Should Phase 7E proceed or should image OCR be deferred?**
   **Proceed only if the team wants the operator assist now; otherwise safe to defer.**
   The path is viable, but only as the narrow slice defined above.

---

## Governance confirmations

- No image OCR runtime implementation was added in Phase 7D.
- No Tesseract binary or wrapper was added in Phase 7D.
- No Docker/runtime dependency changes were made in Phase 7D.
- No hosted OCR was added.
- OCR remains non-authoritative in this spec.
- Existing review → dry-run → explicit apply remains the only governed path.
- No official cricket truth behavior was changed.
- Phase 8 work was not started.

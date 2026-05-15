# Phase 7C — PDF Text Extraction Integration

- Date: 2026-05-15
- Author: Copilot
- Classification: **Phase 7C implementation — PDF text extraction only. No image OCR.**
- Phase: 7C (sub-phase of Phase 7 — Historical Match Ingestion: PDF/Image/OCR Review Flow)
- Repository: `Jnpaul1984/Cricksy_Scorer`

---

## 1. Audit Summary

This document records the pre-implementation audit, dependency decision, files changed,
commands run, and governance confirmation for Phase 7C.

Phase 7C follows the Phase 7B spec-lock recommendation exactly:

- `manual_candidate_json` remains the production default extraction method.
- Optional PDF text extraction (`pdf_text_extract`) is added as the first incremental
  extraction slice, using `pdfplumber` — a pure-Python, MIT-licensed library with no
  system binary dependencies.
- Tesseract/image OCR is deferred to Phase 7D.
- Hosted OCR is deferred until a separate governance review (Phase 7E at earliest).

---

## 2. Pre-Implementation Audit Answers

### Q1. Which PDF text extraction dependency should be used?

**`pdfplumber>=0.11.4`** (pure Python, MIT license, no binary system dependencies, no
privacy risk). Recommended in the Phase 7B spec-lock as the first-slice dependency for
digitally generated PDFs. Validated clean in the GitHub Advisory Database (no known
vulnerabilities as of 2026-05-15).

### Q2. Can extraction be optional and disabled/fallback-safe?

Yes. The extraction service is wrapped in a `try/except Exception` block and returns a
`PdfExtractionResult` regardless of whether extraction succeeds or fails. If `pdfplumber`
is not installed, extraction is disabled gracefully with an explicit
`pdf_extraction_unavailable` uncertainty flag. Extraction only runs when
`extraction_method="pdf_text_extract"` **and** the uploaded file is a PDF; image uploads
are skipped entirely.

### Q3. How will extracted text be stored in review candidate metadata?

Extracted text is stored in `extraction.ocr_text` on the `HistoricalOcrReviewCandidateResponse`.
The field was already present in the Phase 7/7A schema for manual OCR text attachments and
now also receives auto-extracted text when `extraction_method="pdf_text_extract"` is used.

### Q4. How will extraction confidence/uncertainty be represented?

- Digital PDF with extracted text → `confidence=1.0`, `uncertainty_flags=[]`
- Valid PDF with no embedded text (scanned image PDF) → `confidence=0.0`,
  `uncertainty_flags=["scanned_pdf_no_text"]`
- Extraction failure (corrupt/invalid PDF) → `confidence=0.0`,
  `uncertainty_flags=["extraction_failed"]`
- `pdfplumber` not installed → `confidence=0.0`,
  `uncertainty_flags=["pdf_extraction_unavailable"]`

Additionally, `extraction.warnings` (a new `list[str]` field on
`HistoricalOcrExtractionMetadata`) carries human-readable fallback messages for operators.

### Q5. What happens when the PDF contains no extractable text?

The candidate is still created successfully (HTTP 200). The candidate receives:
- `extraction.ocr_text = null`
- `extraction.confidence = 0.0`
- `extraction.uncertainty_flags = ["scanned_pdf_no_text"]`
- `status = "uploaded"` (not escalated to `needs_review` since no text was found)
- `extraction.warnings` includes a clear message: _"PDF contains no extractable text layer.
  This is likely a scanned image PDF. Image OCR is not performed — please enter the
  scorecard JSON manually."_

The operator can still use the manual JSON textarea to supply candidate data.

### Q6. What tests prove extraction remains non-authoritative?

- `test_pdf_text_extraction_does_not_create_official_match_data`: asserts `/games/results`
  count is unchanged after creating a PDF-text-extract candidate.
- `test_candidate_with_extracted_text_still_requires_human_review`: asserts the candidate
  status is never `applied_via_structured_import_only`, `dry_run_passed`, or
  `ready_for_dry_run` immediately after creation.
- `test_existing_dry_run_handoff_unchanged_after_phase_7c`: asserts the full
  upload → review → dry-run handoff still works for existing `manual_candidate_json` path.

---

## 3. Dependency Decision

| Package | Version | Justification |
|---|---|---|
| `pdfplumber` | `>=0.11.4` | Pure Python, MIT license, no system binary dependency, no privacy risk, zero known CVEs as of 2026-05-15. Recommended in Phase 7B spec-lock. |

No other new dependencies were added. No existing dependency versions were changed.

---

## 4. Files Changed

### Backend

| File | Change |
|---|---|
| `requirements.txt` | Added `pdfplumber>=0.11.4` |
| `backend/services/pdf_extraction_service.py` | **New file.** Fail-safe PDF text extraction service using `pdfplumber`. Returns `PdfExtractionResult` with extracted text, confidence, uncertainty flags, and warnings. Never raises. |
| `backend/routes/historical_import.py` | Extended `create_historical_ocr_review_candidate` to call `extract_text_from_pdf()` when `extraction_method="pdf_text_extract"` and upload is a PDF. Operator-supplied values take precedence. |
| `backend/api/schemas/historical_import.py` | Added `warnings: list[str]` field to `HistoricalOcrExtractionMetadata`. |
| `backend/tests/test_historical_ocr_review_flow.py` | Added `_pdf_with_text_bytes()` and `_pdf_without_text_bytes()` test helpers. Added 7 new Phase 7C tests (see §6). |

### Frontend

| File | Change |
|---|---|
| `frontend/src/services/api.ts` | Added `warnings?: string[]` to `HistoricalOcrExtractionMetadata` interface. |
| `frontend/src/components/HistoricalOcrReviewPanel.vue` | Added `pdf_text_extract` dropdown option; added extracted text preview block with non-authoritative notice; added no-text fallback message; updated `extractionMethod` ref type; added new CSS classes. |
| `frontend/tests/unit/HistoricalOcrReviewPanel.spec.ts` | Added `pdfExtractCandidateWithText` and `pdfExtractCandidateNoText` fixtures; added 3 new Phase 7C unit tests (see §6). |

### Docs

| File | Change |
|---|---|
| `docs/PHASE_7C_PDF_TEXT_EXTRACTION_INTEGRATION.md` | **This file.** Phase 7C audit, dependency decision, and governance confirmation. |

### Migration

No database migration changes. The `extraction.warnings` field is stored in the existing
JSON column (`dry_run_summary["ocr_review"]["extraction"]["warnings"]`) — no schema
migration required.

---

## 5. Backend Touched

**Yes.** Added `pdf_extraction_service.py`, extended `create_historical_ocr_review_candidate`
endpoint, added `warnings` field to schema, added 7 new backend tests.

## 6. Frontend Touched

**Yes.** Added `pdf_text_extract` dropdown option, extracted text preview block, and 3 new
frontend unit tests.

## 7. Migration Touched

**No.** The `warnings` list is persisted inside the existing `dry_run_summary` JSON column.
No new columns or Alembic revision required.

---

## 8. Commands Run and Results

### Backend

```bash
# Ruff check (new files only)
ruff check backend/services/pdf_extraction_service.py backend/api/schemas/historical_import.py
# All checks passed!

# Ruff format check (new files)
ruff format --check backend/services/pdf_extraction_service.py backend/api/schemas/historical_import.py backend/routes/historical_import.py
# 3 files already formatted

# Pytest — Phase 7C tests
PYTHONPATH=. CRICKSY_IN_MEMORY_DB=1 pytest backend/tests/test_historical_ocr_review_flow.py -v --tb=short
# 16 passed (9 pre-existing + 7 new)
```

### Frontend

```bash
npm run type-check   # 0 errors
npm run build-only   # ✓ built in 5.26s
npm run test:unit -- HistoricalOcrReviewPanel.spec.ts
# 7 passed (4 pre-existing + 3 new)
```

---

## 9. Governance Confirmations

| Requirement | Status |
|---|---|
| Image OCR was NOT implemented | ✅ Confirmed |
| Tesseract integration was NOT added | ✅ Confirmed |
| Hosted OCR integration was NOT added | ✅ Confirmed |
| Extracted text does NOT create official match truth | ✅ Confirmed (test_pdf_text_extraction_does_not_create_official_match_data) |
| Existing review/correction/dry-run path remains mandatory | ✅ Confirmed |
| No official match data is created or mutated by extraction | ✅ Confirmed |
| `manual_candidate_json` remains the production default | ✅ Confirmed |
| Empty/no-text PDFs are handled gracefully | ✅ Confirmed (scanned_pdf_no_text fallback state) |
| Phase 8 work was NOT started | ✅ Confirmed |

---

## 10. New Extraction Method: `pdf_text_extract`

When `extraction_method="pdf_text_extract"` is submitted with a PDF file:

1. `extract_text_from_pdf(payload)` is called from `pdf_extraction_service.py`.
2. If text is found: `ocr_text` is populated, `confidence=1.0`, `uncertainty_flags=[]`.
3. If no text is found (scanned PDF): `ocr_text=null`, `confidence=0.0`,
   `uncertainty_flags=["scanned_pdf_no_text"]`.
4. If extraction fails (corrupt PDF): `ocr_text=null`, `confidence=0.0`,
   `uncertainty_flags=["extraction_failed"]`.
5. Candidate is always created (never rejected) unless the upload itself is invalid (wrong
   type, too large, empty).
6. `status` escalates to `needs_review` only if `ocr_text` or `candidate_json` is populated.
7. Operator-supplied `ocr_text`, `extraction_confidence`, and `uncertainty_flags` form
   values always override auto-extracted values.
8. All extracted text is displayed in the `HistoricalOcrReviewPanel` as a non-authoritative
   preview with a clear warning: _"Extracted text is not official match data."_

---

## 11. Frontend Changes Summary

### Extraction method dropdown

Added `pdf_text_extract` as a new option alongside the existing
`manual_candidate_json` and `ocr_text_attachment` options.

### Extracted text preview (shown for `pdf_text_extract` method only)

When `candidate.extraction.method === 'pdf_text_extract'`:

- If `ocr_text` is present: shows a `<pre>` block with the extracted text, prefixed by
  a non-authoritative warning notice.
- If `ocr_text` is null: shows a fallback message: _"No extractable text was found in this
  PDF. This may be a scanned image PDF. Image OCR is not performed — please enter the
  scorecard JSON manually in the field above."_
- Extraction warnings are listed below both states if present.

Manual JSON correction remains available in all cases.

---

## 12. Phase 7D / 7E Notes

- Phase 7D (optional Tesseract image OCR) is deferred. Will require Docker layer change,
  CI `apt install tesseract-ocr`, and extensive fixture coverage.
- Phase 7E (hosted OCR) is deferred. Requires separate data-governance review.

# Phase 7 Closure and OCR Deferral Note

**Date:** 2026-05-15
**Issue:** Phase 7 Closure — Defer Remaining OCR Sub-phases Until Club Onboarding

---

## Status

**Phase 7 — Historical Match Ingestion: PDF/Image/OCR Review Flow**

> Core workflow implemented. Remaining OCR enhancement sub-phases intentionally deferred
> until real club/customer onboarding provides representative scorecards, scanned documents,
> and operator workflow evidence.

---

## Completed Sub-phases

| Sub-phase | Status | Evidence |
|---|---|---|
| Phase 7 — OCR review candidate workflow | ✅ Complete | `backend/routes/historical_import.py`, `frontend/src/components/HistoricalOcrReviewPanel.vue` |
| Phase 7A — Manual QA + operator workflow validation | ✅ Complete | `docs/PHASE_7A_OCR_REVIEW_FLOW_MANUAL_QA.md` |
| Phase 7B — OCR extraction engine audit/spec-lock | ✅ Complete | `docs/PHASE_7B_OCR_EXTRACTION_ENGINE_AUDIT_AND_SPEC_LOCK.md` |
| Phase 7C — PDF text extraction for review candidates | ✅ Complete | `docs/PHASE_7C_PDF_TEXT_EXTRACTION_INTEGRATION.md` |
| Phase 7D — Tesseract/image OCR audit/spec-lock | ✅ Complete | `docs/PHASE_7D_TESSERACT_IMAGE_OCR_AUDIT_AND_SPEC_LOCK.md` |

---

## Deferred Sub-phases

| Sub-phase | Status | Reason |
|---|---|---|
| Phase 7E — Optional Tesseract/Image OCR Integration for Review Candidates | ⏸ Deferred | See deferral reason below |
| Phase 7F — OCR Ingestion Manual QA + Production Readiness Gate | ⏸ Deferred | Depends on Phase 7E |

---

## Reason for Deferral

Image OCR has higher operational complexity than PDF text extraction and should be
implemented once real club scorecard formats, scanned documents, and customer workflows
are available. Specifically:

- Tesseract preprocessing quality depends heavily on document format, scan resolution,
  and paper layout — all of which vary by club and region.
- OpenCV-based image preprocessing introduces a significant binary footprint increase in
  the Docker container deployed to ECS.
- Hosted OCR services (Google Vision, AWS Textract, Azure CV) require cost/tier decisions
  that should be driven by real production volume.
- No beta customer or club has submitted scanned scorecards requiring image OCR; the
  `pdfplumber` digital-PDF path (Phase 7C) satisfies current operator needs.

Deferral is a **product/customer timing decision**, not technical abandonment.
The Phase 7D spec-lock document preserves all design decisions and constraints so that
Phase 7E can be resumed cleanly when club onboarding begins.

---

## Phase 7 Governance Summary

- All Phase 7 runtime code is non-authoritative: OCR extraction is review-only; operators
  must review and confirm before any dry-run or apply step.
- No official cricket truth behavior was changed in any Phase 7 sub-phase.
- The `extraction_method` field on OCR review candidates correctly records provenance.
- CI gates remain green. No Tesseract binary, OpenCV, or hosted OCR client was added to
  the runtime container.

---

## Next Active Phase

**Phase 8 — AI Analytics + Match Intelligence Enhancements**

Phase 8 is now the next active phase. It covers improvements to AI insights, prediction
endpoints, player insight services, and frontend analytics/dashboard views, while
protecting deterministic cricket truth.

See `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` (Phase 8 section) for full scope,
gates, and required tests.

---

## References

- Master Checklist: `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`
- Phase 7D spec-lock (contains deferred Phase 7E/7F design): `docs/PHASE_7D_TESSERACT_IMAGE_OCR_AUDIT_AND_SPEC_LOCK.md`
- Phase 6 closure/Phase 7 readiness: `docs/PHASE_6F_INTELLIGENCE_OS_CLOSURE_AND_PHASE_7_READINESS.md`

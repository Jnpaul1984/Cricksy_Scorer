# Post-Phase-6 Ordering + Incomplete Phase 5 Audit

**Document type**: Docs/checklist-governance only
**Relates to**: GitHub Issue #190
**Date**: 2026-05-14
**Status**: Audit complete — no runtime code changed, no migrations added, no dependencies added

---

## 1. Purpose

Audit `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` after Phase 6A–6H governance completion and align the next execution order before any new runtime implementation begins.

This document:

- Classifies every Phase 5 sub-phase as complete/incomplete/follow-up/blocked.
- Documents exactly what comes after Phase 6 in the current checklist.
- Identifies the mismatch between the Phase 6H completion note (which referenced an invented "Phase 7A" name) and the actual Phase 7 in the checklist.
- Confirms the phase naming governance rule.
- Recommends a checklist-grounded next action.

---

## 2. Phase 5 Completion / Incomplete / Follow-Up Audit

The following table classifies all Phase 5 sub-phases based on evidence in:
- `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`
- Individual phase QA/spec docs under `docs/`
- Backend service files, route files, and test files in the repo

### 2.1 Phase 5 Sub-Phase Status Table

| Sub-Phase | Title | Status | Evidence |
|---|---|---|---|
| Phase 5A | Historical JSON Import Audit + Spec Lock | **Complete** | `docs/PHASE_5A_HISTORICAL_JSON_IMPORT_AUDIT_AND_SPEC_LOCK.md` exists; backend implementation follows from spec |
| Phase 5B–5G | Core import implementation (dry-run, batch tracking, apply, rollback, apply-deliveries) | **Complete** | Referenced in `docs/PHASE_5I_HISTORICAL_JSON_UPLOAD_AND_TRAINING_RETENTION.md` as "Fully implemented (Phases 5A–5H)"; `backend/tests/test_historical_import_dry_run.py`, `test_historical_import_apply.py`, `test_historical_import_apply_deliveries.py`, `test_historical_import_rollback.py`, `test_historical_import_batch_tracking.py` all exist and pass |
| Phase 5H | Historical JSON Real-Dataset Validation + Analyst Workspace QA | **Complete** | `docs/PHASE_5H_HISTORICAL_JSON_REAL_DATASET_QA.md` shows passing results for both Cricsheet and cricksy-fixture formats; Analyst Workspace visibility, duplicate detection, and rollback checks pass |
| Phase 5I | Historical JSON Upload UI + Training Dataset Retention | **Complete** | `docs/PHASE_5I_HISTORICAL_JSON_UPLOAD_AND_TRAINING_RETENTION.md` status = "Implemented"; `HistoricalImportPanel.vue` and `historicalImport*` API functions exist; `backend/tests/test_historical_import_training_status.py` exists |
| Phase 5J | Historical Import Metadata Accuracy + Registry Readiness | **Complete** | `docs/PHASE_5J_HISTORICAL_IMPORT_METADATA_ACCURACY_AND_REGISTRY.md` documents fixes for innings-team bug, result/status bug, and overs display; fields `event_name`, `season`, `match_number`, `source_dates` added to import path; Phase 5K doc confirms fixes were in place as baseline |
| Phase 5K | Historical Data Backfill + Analyst UI Theme Fix | **Complete** | `docs/PHASE_5K_HISTORICAL_BACKFILL_AND_ANALYST_THEME_QA.md` status = "Complete"; `backend/services/historical_import_backfill_service.py` and `POST .../repair-metadata` endpoint exist; `backend/tests/test_historical_import_backfill.py` exists; `--color-surface-raised` CSS variable fix confirmed |
| Phase 5L | Bulk ZIP Historical Upload | **Implementation complete; manual QA pending** | `backend/tests/test_historical_import_bulk_zip.py` exists; `POST /api/historical-import/json/bulk-zip/dry-run` and `/bulk-zip/apply` endpoints exist; `docs/PHASE_5L_BULK_ZIP_HISTORICAL_JSON_UPLOAD_QA.md` has implementation detail but manual QA checklist items remain unchecked (open) — operator-level manual validation has not been signed off |
| Phase 5L.1 | Cost-Controlled Large Historical ZIP Intake | **Complete** | Checklist section "Phase 5L.1 Validation Evidence" at line 1161–1180 of the master checklist documents final configured limits (`PHASE_5L_MAX_FILES=2000`, `PHASE_5L_MAX_FILE_SIZE_BYTES=2MB`, etc.) and cost-control path; constants confirmed in `backend/routes/historical_import.py` |
| Phase 5M | Cricket Data Registry Foundation | **Complete** | Checklist section "Phase 5M Implementation Notes (completed)" at lines 1249–1283 documents: `MatchRegistryResponse` schema, `GET /analytics/matches/{match_id}/registry` endpoint, 4 backend tests, Registry & Provenance UI in `AnalystWorkspaceView.vue`, 7 frontend tests; all validation evidence listed passes |
| Phase 5N | Historical Stats Aggregation Layer | **Not started** | No `historical_stats_aggregation` service, route, or test file exists in the repo; no checklist implementation notes present |
| Phase 5O | Analyst Workspace Data Library | **Not started** | No data-library browsing service, filter API, or folder-structure component exists; no checklist implementation notes present |
| Phase 5P | Model Training Dataset Builder | **Not started** | No dataset export pipeline, eligibility gates, or versioning service exists; no checklist implementation notes present |

### 2.2 Phase 5L Manual QA Follow-Up Note

Phase 5L backend implementation is complete and tested (automated tests pass). However, the manual QA document `docs/PHASE_5L_BULK_ZIP_HISTORICAL_JSON_UPLOAD_QA.md` contains a "Manual QA checklist" section with all items unchecked. This checklist represents operator-level validation that has not been signed off.

**Follow-up required**: A Phase 5L operator manual QA pass should be completed and the checklist items checked off before Phase 5L is considered fully closed for production readiness purposes.

### 2.3 Phase 5N–5P: Incomplete Work Before Phase 7

Phase 5N (Historical Stats Aggregation), Phase 5O (Analyst Workspace Data Library), and Phase 5P (Model Training Dataset Builder) are all defined in the checklist with full scope, gates, and tests but have **not been started**. These phases represent the analytical readiness layer that:

- Phase 5N: Provides aggregated stats from registered/validated historical imports.
- Phase 5O: Provides analyst-facing data library browsing over registered historical records.
- Phase 5P: Produces governed training dataset exports from validated + aggregated data.

Phase 7 (Historical Match Ingestion: PDF/Image/OCR Review Flow) would expand the import surface area, adding new unstructured sources. Starting Phase 7 before Phase 5N–5O–5P means the OCR-imported records would enter a system that still has no aggregation layer, no analyst library, and no dataset builder. This is a dependency risk documented in the checklist's Phase 5N pre-audit requirements:

> "Audit registry completeness from Phase 5M… before aggregation starts."

---

## 3. Post-Phase-6 Ordering Documentation

### 3.1 What Comes After Phase 6 in the Checklist

The checklist's "Recommended Execution Order" section (lines 2580–2601) places:

```text
7.  Phase 6 — Cricksy Intelligence Operating System Governance
8.  Phase 7 — Historical Match Ingestion: PDF/Image/OCR Review Flow
9.  Phase 8 — AI Analytics + Match Intelligence Enhancements
10. Phase 9 — Player Development Intelligence Foundation
11. Phase 10 — Subscription, Pricing + Tier Enforcement Hardening
...
```

**The checklist-defined Phase 7 is: "Historical Match Ingestion: PDF/Image/OCR Review Flow."**

This phase is described at lines 2041–2095 of the master checklist.

### 3.2 Existing Phase 7 Title, Purpose, Gates, and Tests (Copied from Checklist)

**Title**: `Phase 7 — Historical Match Ingestion: PDF/Image/OCR Review Flow`

**Purpose**:
> "Expand historical imports to scanned scorecards, PDFs, and phone photos using OCR and human review."

**Pre-Phase Audit** (per checklist):
- Phase 4 ingestion schema
- file upload/S3 handling
- OCR library/cloud options
- storage cost
- async processing options
- security handling for uploaded files

**Spec Lock** (per checklist):
- OCR pipeline
- file type rules
- confidence score schema
- editable review UI
- low-confidence field behavior
- failed OCR behavior
- human approval workflow

**Gates** (per checklist):
- OCR is never final authority
- human review required before save
- low-confidence fields visible
- secure file validation
- existing structured JSON import unaffected
- CI passes

**Required Tests** (per checklist):
- PDF upload
- image upload
- unsupported file rejection
- OCR extraction mocked test
- low-confidence review test
- manual correction test
- failed OCR test
- existing ingestion regression tests
- full CI gates

**Completion Criteria** (per checklist):
> "Teams can upload scans/photos/PDFs and review extracted match data before saving."

### 3.3 Phase 7 Dependencies on Incomplete Phase 5 Work

Phase 7 does not explicitly depend on Phase 5N/5O/5P in its own spec section. However:
- Phase 5N prerequisites (registry completeness from Phase 5M) are satisfied — Phase 5M is complete.
- Phase 7 would add new import sources. If Phase 5N/5O/5P are not started, OCR-imported records will enter a system without aggregation or analyst-library support.
- The checklist's Phase 7 spec itself does not require Phase 5N–5P to be complete before starting.

### 3.4 Phase 7 Dependency on Phase 6 Governance Completion

Phase 6A–6H are all complete as spec/governance. Phase 7 is an import-pipeline phase (not an intelligence phase), so it does not require the Phase 6 intelligence architecture to be implemented — only governed. Phase 6 governance is complete. Phase 7 may proceed from a Phase 6 perspective.

---

## 4. Mismatch: Phase 6H "Phase 7A" vs Actual Checklist Phase 7

### 4.1 The Mismatch

The Phase 6H completion summary in the master checklist (lines 2027–2029) contains:

> "Phase 6A–6H completion summary added and next-phase recommendation locked: pause for `Phase 7A — Intelligence Runtime Readiness Audit + First Implementation Slice Selection` unless explicit approval is given to jump directly to a first runtime MVP slice."

**This references a phase name ("Phase 7A — Intelligence Runtime Readiness Audit + First Implementation Slice Selection") that does not exist anywhere in the Master Execution Checklist.**

The actual Phase 7 in the checklist is:

> **Phase 7 — Historical Match Ingestion: PDF/Image/OCR Review Flow**

The "Phase 7A" name appears to have been invented during the Phase 6H implementation session without being added to the checklist through a governance PR. This violates the checklist-as-source-of-truth principle.

### 4.2 Required Correction

The Phase 6H completion note that references "Phase 7A" must be corrected in the checklist to:
- Remove the invented "Phase 7A" name.
- Reference the actual Phase 7 from the checklist.
- Note that incomplete Phase 5N/5P work should be considered before Phase 7 begins.

The correction is made in `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` as part of this PR.

---

## 5. Phase Naming Governance Rule

The following rule has been added to the Master Execution Checklist (Section 2, Rule 8):

```text
No new phase name may be used for GitHub issues, PRs, commit messages, or
implementation plans unless it already exists in the Master Execution Checklist
or is first added through a checklist-governance PR.

Inventing a phase name outside the checklist is a governance violation.
If a new phase is needed, add it to the checklist first, then reference it.
```

---

## 6. Next-Action Recommendation

Based on checklist evidence only:

### Option A: Continue an incomplete Phase 5 item (RECOMMENDED)

**Recommended next action: Start Phase 5N — Historical Stats Aggregation Layer**

Evidence from checklist:
- Phase 5N is the next incomplete Phase 5 sub-phase in checklist order (after 5M which is complete).
- Phase 5N pre-audit requires confirming Phase 5M registry completeness — Phase 5M is complete.
- Phase 5N is required before Phase 5O (Analyst Workspace Data Library) which needs aggregated outputs.
- Phase 5O is required before Phase 5P (Model Training Dataset Builder) which needs library + aggregation.
- The intelligence architecture from Phase 6 explicitly requires validated/registered/aggregated historical data to feed skills and intelligence outputs.
- Starting Phase 7 (OCR ingestion) without Phase 5N–5P means new OCR-imported records enter a system that has no aggregation, no analyst library, and no training-dataset export.

**Supporting checklist evidence (Phase 6A — Data Foundation Link):**
```text
Historical JSON import
↓
Metadata registry
↓
Training eligibility gates
↓
Analyst Workspace visibility
↓
Skills + intelligence pipeline later
```

Phase 5N→5O→5P fills the "Training eligibility gates" and "Analyst Workspace visibility" steps that intelligence needs. Phase 7 (OCR) expands the import surface but does not fill these analytical readiness gaps.

### Option B: Perform Phase 5L manual QA follow-up (secondary, lower priority)

Phase 5L implementation is complete and automated tests pass. The manual QA checklist in `docs/PHASE_5L_BULK_ZIP_HISTORICAL_JSON_UPLOAD_QA.md` has unchecked items. This could be done concurrently or immediately before Phase 5N, but it does not block Phase 5N.

### Option C: Proceed directly to Phase 7 (not recommended without Phase 5N–5P)

The checklist permits Phase 7 after Phase 6. However, starting Phase 7 without Phase 5N–5P means OCR-imported records would join a system without aggregated stats, analyst library support, or training dataset readiness. The checklist's Phase 5N–5P sub-phases are mandatory dependencies for the Phase 6 intelligence pipeline and should be completed before Phase 7 expands the import surface.

### Option D: Update the checklist with a formal Phase 5 → Phase 7 transition readiness phase (not recommended)

No new phase name needs to be invented. Phase 5N, 5O, and 5P are already defined in the checklist and represent exactly the transition/readiness work needed. Creating a new phase would add unnecessary overhead.

---

## 7. Summary of Files Changed in This PR

| File | Change Type | Reason |
|---|---|---|
| `docs/POST_PHASE_6_ORDERING_AND_PHASE_5_AUDIT.md` | New file | This audit document |
| `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` | Updated | (1) Phase 5K heading update with COMPLETE marker; (2) Phase 5L status note; (3) Phase 6H mismatch correction (remove invented "Phase 7A" reference); (4) Phase Naming Governance rule added; (5) Recommended Execution Order alignment note |

---

## 8. Validation

- [x] Docs-only changes — no runtime files changed
- [x] No backend services, routes, models, or migrations added or changed
- [x] No frontend components or stores changed
- [x] No new dependencies added
- [x] No Phase 5 item marked complete without validation evidence
- [x] No new implementation phase name invented
- [x] Phase 7 name unchanged (remains "Historical Match Ingestion: PDF/Image/OCR Review Flow")
- [x] Markdown formatting reviewed
- [x] Checklist heading order remains readable
- [x] Recommendation is checklist-grounded

---

## 9. Confirmation

- No runtime behavior was changed.
- No implementation work was performed.
- No phase name was invented outside the checklist.
- No Phase 5 item was marked complete without evidence in docs or tests.
- The Phase 6H invented "Phase 7A" mismatch is documented and corrected in the checklist.
- The recommended next action (Phase 5N) is based on checklist evidence and ordering.

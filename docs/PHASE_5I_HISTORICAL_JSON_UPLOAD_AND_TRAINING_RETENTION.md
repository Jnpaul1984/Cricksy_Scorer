# Phase 5I: Historical JSON Upload UI + Training Dataset Retention

**Phase:** 5I  
**Status:** Implemented  
**Date:** 2026-05-11  
**PR:** Phase 5I implementation

---

## Objective

Phase 5I delivers the first safe user-facing path for uploading historical JSON files into the Analyst Workspace and retaining source/batch metadata in a form that supports future model-training workflows.

---

## Audit Findings (pre-implementation)

| Area | Finding |
|------|---------|
| Backend import endpoints | Fully implemented (Phases 5A–5H): dry-run, batch tracking, apply, rollback, apply-deliveries |
| Frontend API service | No historical import functions existed in `services/api.ts` |
| Analyst Workspace | Import-capable tabs existed; no upload UI existed |
| Auth/RBAC | `get_current_user_optional` used; ownership scoped by user/org |
| Raw JSON retention | **Not retained** — only parsed metadata stored in `HistoricalImportBatch.dry_run_summary` |
| DB schema for ML registry | No dedicated ML registry columns exist; eligibility derivable from existing fields without migration |
| Training dataset export | Not implemented; deferred to Phase 5J |

---

## Upload Workflow

```
1. User selects .json file in Analyst Workspace → "Import JSON" tab
2. HistoricalImportPanel runs POST /api/historical-import/json/dry-run (no record_preview)
3. Preview displayed:
   - detected_format (cricksy_fixture | cricsheet_json | unsupported)
   - teams, innings count, delivery count, warnings, errors
   - duplicate detection result (not_duplicate | likely_duplicate)
4. If status = invalid or unsupported → clear error shown, user prompted to upload different file
5. If status = valid → user sees preview and clicks "Save import record"
6. POST /api/historical-import/json/dry-run?record_preview=true → batchId returned
7. User clicks "Confirm: Create match record" → POST /api/historical-import/json/batches/{id}/apply
8. User optionally clicks "Confirm: Import deliveries" → POST /api/historical-import/json/batches/{id}/apply-deliveries?confirm=true
9. On done: training status fetched from GET /api/historical-import/json/batches/{id}/training-status
10. User navigated back to Matches tab; match list refreshed (imported match visible with "Imported" badge)
```

### Key UI Safety Gates

- Dry-run preview shown before any DB writes
- `record_preview` only activated after user sees preview
- Apply step requires explicit button click ("Confirm: Create match record")
- Apply-deliveries step requires separate explicit confirmation
- User can skip apply-deliveries (match record is complete without deliveries)
- No auto-apply; no bypass of validation

---

## Files Changed

### Backend

| File | Change |
|------|--------|
| `backend/api/schemas/historical_import.py` | Added `HistoricalImportTrainingStatus` Pydantic schema |
| `backend/services/historical_import_service.py` | Added `get_import_batch()` function |
| `backend/routes/historical_import.py` | Added `GET /batches/{batch_id}/training-status` endpoint; imported new schema/service |
| `backend/tests/test_historical_import_training_status.py` | New test file (6 tests) |

### Frontend

| File | Change |
|------|--------|
| `frontend/src/services/api.ts` | Added historical import types and 5 typed API functions |
| `frontend/src/components/HistoricalImportPanel.vue` | New self-contained upload panel component |
| `frontend/src/views/AnalystWorkspaceView.vue` | Added "Import JSON" tab, imported panel, added `onImportDone` handler |

### Documentation

| File | Change |
|------|--------|
| `docs/PHASE_5I_HISTORICAL_JSON_UPLOAD_AND_TRAINING_RETENTION.md` | This file |

---

## Retention Behaviour

### What IS retained (Phase 5I)

- `source_hash_sha256` (SHA-256 of raw JSON bytes)
- `source_filename` (uploaded filename)
- `source_format` (detected: `cricksy_fixture` | `cricsheet_json`)
- `semantic_key` (derived from teams + date + format)
- `status` (`valid` | `invalid` | `unsupported`)
- `error_count`, `warning_count`
- `innings_count`, `delivery_count`
- `dry_run_summary` (full dry-run JSON stored in batch row)
- `applied_game_id` (Game row ID created by apply)
- `is_finalized` (True after apply)
- `owner_user_id`, `owner_org_id` (access scoping)
- `created_at`, `updated_at`

### What is NOT retained (Phase 5I — deferred)

- **Raw source JSON bytes** — not stored server-side
- Uploaded file content is consumed in-memory during the request and not persisted to storage
- ML training registry columns — no DB migration performed

**Decision rationale:** Phase 5I scope was kept to MVP. Raw file retention would require:
- An approved private object storage location (S3 bucket with ACL)
- File sanitization before storage
- Access-controlled retrieval
- Retention lifecycle policies

This is deferred to Phase 5J.

---

## Training Dataset Readiness

### New endpoint: `GET /api/historical-import/json/batches/{batch_id}/training-status`

Returns a `HistoricalImportTrainingStatus` object with:

| Field | Description |
|-------|-------------|
| `batch_id` | Import batch ID |
| `source_format` | Detected JSON format |
| `source_hash_sha256` | File hash (64 hex chars) |
| `source_filename` | Original filename |
| `semantic_key` | Match semantic key |
| `applied_game_id` | Game ID (if applied) |
| `imported_at` | Batch creation timestamp |
| `innings_count` | Innings in the file |
| `delivery_count` | Deliveries in the file |
| `training_eligible` | `true` if batch meets eligibility criteria |
| `exclusion_reason` | Reason for ineligibility (null if eligible) |
| `raw_json_retained` | Always `false` in Phase 5I |
| `training_registry_phase` | Always `"deferred"` in Phase 5I |

### Eligibility criteria (computed from existing fields — no migration)

A batch is `training_eligible=True` when ALL of:
1. `is_finalized = true` (apply was called)
2. `applied_game_id` is not null (game row exists)
3. `status = "valid"` (no structural errors)
4. `error_count = 0` (no validation errors)

### Exclusion reasons

| Code | Meaning |
|------|---------|
| `batch_not_finalized` | Apply step not yet completed |
| `no_game_applied` | Batch finalized but game row missing |
| `invalid_status:<status>` | Batch status was not "valid" |
| `has_errors` | error_count > 0 |

---

## Raw JSON Retention Decision

**Phase 5I decision: DEFERRED.**

Raw source JSON is not retained in Phase 5I. Only parsed metadata is stored in `dry_run_summary`.

Rationale:
- Uploaded JSON may contain sensitive player/competition data
- Raw retention requires private, access-controlled storage
- No approved storage location configured yet
- MVP scope can be achieved with metadata only

**Phase 5J should implement:**
- Private S3 bucket or equivalent for raw JSON storage
- Sanitization pipeline before storage
- Access control (user/org scoped, no public access)
- Retention lifecycle (e.g., 90-day auto-expiry or explicit deletion)
- `raw_json_s3_key` field in `HistoricalImportBatch` (migration required)

---

## New Frontend API Functions

```typescript
// Dry-run preview (recordPreview=false = no DB write)
historicalImportDryRun(file: File, recordPreview?: boolean): Promise<HistoricalImportDryRunResponse>

// List persisted batch records
historicalImportListBatches(limit?: number): Promise<HistoricalImportBatchRecord[]>

// Apply (create historical Game row)
historicalImportApply(batchId: string): Promise<HistoricalImportApplyResponse>

// Apply deliveries (ball-by-ball)
historicalImportApplyDeliveries(batchId: string, file: File): Promise<HistoricalImportApplyDeliveriesResponse>

// Training readiness status
historicalImportGetTrainingStatus(batchId: string): Promise<HistoricalImportTrainingStatus>
```

---

## Tests Added / Updated

### New backend test file: `test_historical_import_training_status.py` (6 tests)

| Test | What it validates |
|------|------------------|
| `test_training_status_404_for_unknown_batch` | 404 for non-existent batch_id |
| `test_training_status_unfinalized_batch_not_eligible` | Unfinalized batch → not eligible |
| `test_training_status_required_fields_present` | All required metadata fields returned |
| `test_training_status_no_fake_metadata` | Hash matches actual file content |
| `test_training_status_applied_batch_is_eligible` | Applied batch → training_eligible=True |
| `test_training_status_does_not_mutate_data` | GET is idempotent, no side effects |

### Existing tests validated (72 total, all passing)

```
backend/tests/test_historical_import_dry_run.py         ✅ 9 tests
backend/tests/test_historical_import_batch_tracking.py  ✅ 16 tests
backend/tests/test_historical_import_apply.py           ✅ 14 tests
backend/tests/test_historical_import_rollback.py        ✅ 7 tests
backend/tests/test_historical_import_apply_deliveries.py ✅ 20 tests
backend/tests/test_historical_import_training_status.py  ✅ 6 tests
```

---

## Validation Commands Run

### Backend

```bash
PYTHONPATH=/home/runner/work/Cricksy_Scorer/Cricksy_Scorer \
CRICKSY_IN_MEMORY_DB=1 \
APP_SECRET_KEY=test-secret-key \
pytest backend/tests/test_historical_import_*.py -v
# Result: 72 passed

pytest backend/tests/test_health.py backend/tests/test_results_endpoint.py \
       backend/tests/test_analyst_pro_features.py -v
# Result: 18 passed
```

### Frontend

```bash
cd frontend && node ../scripts/check-fake-data.js   # PASS (0 errors)
cd frontend && node_modules/.bin/vue-tsc --build --force  # PASS (no errors)
cd frontend && npm run build-only                   # PASS (build in 4.78s)
```

---

## Security & Privacy Notes

- Uploaded JSON files are consumed in-memory; no raw bytes written to disk
- Batch metadata is scoped to `owner_user_id` / `owner_org_id`
- `get_current_user_optional` used on all import endpoints; unauthenticated users can import but records are unscoped (anonymous)
- No private/competition JSON files committed to the repository
- Tests use only sanitized fixtures (`simulated_t20_match.json`, `sanitized_cricsheet_t20.json`)
- Training eligibility check is read-only (GET endpoint)

---

## Rollback Plan

1. Import can be rolled back via existing Phase 5E rollback endpoint:
   ```
   POST /api/historical-import/json/batches/{batch_id}/rollback
   Body: {"confirm": true}
   ```
2. This deletes the applied Game row and resets `is_finalized = false`
3. The batch record itself is retained for audit trail
4. Frontend: batch record visible in Analyst Workspace "Import JSON" tab; re-apply or discard

---

## Manual QA Checklist

- [ ] Open Analyst Workspace → click "Import JSON" tab
- [ ] Drop a valid Cricksy fixture `.json` file into the dropzone
- [ ] Preview appears: format, teams, innings, deliveries, duplicate status
- [ ] Drop an unsupported `.json` file → error shown, no data saved
- [ ] Drop a duplicate `.json` file → duplicate warning shown in preview
- [ ] Click "Save import record" → batch ID shown
- [ ] Click "Confirm: Create match record" → game ID shown
- [ ] Click "Confirm: Import deliveries" → deliveries count shown
- [ ] Click "Skip — finish without deliveries" → done state without deliveries
- [ ] After import: click "View in Matches tab" → Matches tab refreshed, imported match visible with "Imported" badge
- [ ] Verify training status: `GET /api/historical-import/json/batches/{id}/training-status` returns `training_eligible=true` after full import
- [ ] Verify `raw_json_retained=false` in training status response
- [ ] Verify rollback works: POST rollback endpoint → game row deleted

---

## Phase 5J Recommendation

Phase 5J should implement:

1. **Raw JSON retention** in private object storage (S3)
   - Add `raw_json_s3_key` column to `HistoricalImportBatch` (migration required)
   - Upload sanitized raw JSON to private S3 bucket on `record_preview=true`
   - Scoped access control (user/org)

2. **ML dataset registry**
   - Create a `TrainingDatasetRegistry` table with:
     - `batch_id`, `game_id`, `format`, `source_hash`, `imported_at`, `training_eligible`, `exclusion_reason`, `raw_json_s3_key`
   - Export endpoint: `GET /api/ml/training-dataset?eligible_only=true`

3. **Full audit trail UI**
   - Show import history in Analyst Workspace "Import JSON" tab
   - Show training eligibility per batch in the batch list

4. **Access control hardening**
   - Require Analyst or Admin role for import actions
   - Add rate limiting on dry-run endpoint

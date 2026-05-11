# Phase 5K: Historical Data Backfill & Analyst UI Theme Fix — QA Document

**Phase**: 5K  
**Date**: 2026-05-11  
**Status**: Complete  

---

## 1. Audit Findings

### 1.1 Legacy Historical Import Metadata

**Finding**: Legacy historical imported Game rows created before Phase 5J may be missing the following metadata fields in `Game.phases["historical_import"]`:

| Field | Phase 5J Addition | Legacy Default |
|---|---|---|
| `event_name` | ✅ Added | absent |
| `season` | ✅ Added | absent |
| `match_number` | ✅ Added | absent |
| `source_dates` | ✅ Added | absent |

The current `historical_import_apply_service.py` (Phase 5J-aware) writes all four fields for every new import, even when the source JSON does not supply them (they default to `None`/`[]`). A "legacy" game is therefore defined as one where **none** of these four keys appear in `historical_import` at all.

**Source of truth for repair**: `HistoricalImportBatch.dry_run_summary["metadata_preview"]`. If the batch still exists and its `dry_run_summary` contains those fields, safe repair is possible.

**Decision**: Safe backfill implemented via a controlled repair endpoint. When `dry_run_summary` does not supply the metadata, repair is refused and reimport is required (documented below).

### 1.2 Analyst Workspace Dark-Theme Issue

**Finding**: Two components used a hardcoded light-mode fallback color `#f8fafc` as the CSS `var()` fallback value for `--color-surface-raised`:

```css
/* Before (broken in dark mode) */
background: var(--color-surface-raised, #f8fafc);  /* falls back to light bg */
```

**Affected classes**: `.aw-keyplayer-card`, `.aw-podcast-prep`

**Root cause**: `--color-surface-raised` was never defined in `designSystem.css`. In dark mode the CSS variable was undefined, so browsers fell back to the hardcoded `#f8fafc` (a light off-white), rendering cards with a light background inside the dark Analyst Workspace.

**Decision**: Added `--color-surface-raised` to `designSystem.css` for both light and dark modes. No hardcoded colour fallback remains in the component.

---

## 2. Changes Made

### 2.1 Backend — Metadata Repair Service

**New file**: `backend/services/historical_import_backfill_service.py`

Implements `repair_legacy_historical_metadata()` with the following safety gates:

1. `confirm` must be `True` (accidental-write guard)  
2. Batch must exist  
3. Batch must be finalized with a non-null `applied_game_id`  
4. The linked Game must exist  
5. Game `status` must be `completed` (live/in-progress games are **never** touched)  
6. Game must have `phases["historical_import"]` key (must be a historical import)  
7. Phase 5J fields must **not** already be present (no overwrite of valid data)  
8. Batch `dry_run_summary` must contain at least one Phase 5J field; otherwise the repair is refused with a message directing the operator to reimport  

On success, the repair writes a `_repair_log` audit entry inside `phases["historical_import"]`.

### 2.2 Backend — Repair API Endpoint

**Modified file**: `backend/routes/historical_import.py`

New endpoint:
```
POST /api/historical-import/json/batches/{batch_id}/repair-metadata
```

Request body:
```json
{ "confirm": true }
```

Response:
```json
{
  "batch_id": "...",
  "game_id": "...",
  "status": "repaired" | "already_complete" | "refused",
  "fields_added": ["event_name", "season", "match_number", "source_dates"],
  "warnings": [],
  "detail": "Human-readable summary"
}
```

HTTP status codes:
- `200` — success (repaired or already_complete)  
- `404` — batch not found or linked game not found  
- `409` — repair refused (reimport required, business logic refusal)  
- `422` — `confirm` not provided or `confirm=false`  

### 2.3 Backend — New Schemas

**Modified file**: `backend/api/schemas/historical_import.py`

Added:
- `HistoricalImportRepairRequest`
- `HistoricalImportRepairResponse`

### 2.4 Frontend — Dark-Theme Fix

**Modified file**: `frontend/src/assets/designSystem.css`

Added `--color-surface-raised` CSS token to both light and dark mode blocks:

```css
/* Light mode */
--color-surface-raised: #f8fafc;

/* Dark mode (prefers-color-scheme: dark) */
--color-surface-raised: #273447;
```

This ensures `.aw-keyplayer-card` and `.aw-podcast-prep` (and any future component using `var(--color-surface-raised)`) use a theme-appropriate background in both modes.

### 2.5 Tests

**New file**: `backend/tests/test_historical_import_backfill.py`

16 tests covering:
- HTTP safety gates (confirm gate, missing batch 404, unfinalized batch 409, already_complete)
- Service-level unit tests using direct DB access:
  - confirm=False rejected
  - unknown batch rejected
  - unfinalized batch rejected
  - live/in-progress game refused and untouched
  - non-historical game refused
  - already_complete returns correct status without overwriting
  - legacy game repaired with correct field values
  - audit log written on repair
  - idempotent: second repair returns already_complete
  - refused when batch lacks Phase 5J metadata (reimport required)
  - repair does not alter other games
  - repair does not alter deliveries/scoring data

**Modified file**: `frontend/tests/unit/AnalystWorkspaceView.spec.ts`

5 new dark-theme contract tests:
- Key Players card uses `aw-keyplayer-card` class (CSS variable styling anchor)
- Key Players cards have all required sub-elements for readable contrast
- Podcast Prep container has `aw-podcast-prep` class (CSS variable styling anchor)
- Podcast Prep talking-point items have `aw-podcast-tp` class with label sub-elements
- Key Players section heading always renders

---

## 3. Manual QA Checklist

### 3.1 Dark-Theme Verification

- [ ] Open Analyst Workspace in a browser with dark mode enabled (`prefers-color-scheme: dark`)
- [ ] Select a completed historical match from the match list
- [ ] Verify **Key Players** cards have a dark background (not light `#f8fafc`)
- [ ] Verify player names are legible (light text on dark background)
- [ ] Verify **Podcast Prep Package** section has a dark background
- [ ] Verify all talking-point cards are legible in dark mode
- [ ] Switch to light mode — verify Key Players and Podcast Prep cards have a light raised background
- [ ] Verify no other UI sections changed appearance

### 3.2 Legacy Match Verification

To check if a specific game needs repair:

```bash
# 1. Find the batch linked to the game
GET /api/historical-import/json/batches

# 2. Check the game's phases — look for missing Phase 5J fields
# If phases["historical_import"] is missing event_name/season/match_number/source_dates,
# the game is legacy and can be repaired if the batch is still present.

# 3. Run a repair (preview: check response without DB commit — confirm=False returns 422)
POST /api/historical-import/json/batches/{batch_id}/repair-metadata
{"confirm": false}   → 422 (safe probe; will not modify data)

# 4. Apply the repair
POST /api/historical-import/json/batches/{batch_id}/repair-metadata
{"confirm": true}

# 5. Verify audit log in response and in game.phases["historical_import"]["_repair_log"]
```

**If repair returns 409 with "reimport" in the message**: the batch's `dry_run_summary` does not contain Phase 5J metadata. The original JSON file must be re-uploaded through the standard dry-run → apply flow.

### 3.3 Post-Repair Verification

After running a repair:
- [ ] `GET /api/historical-import/json/batches` shows batch still finalized
- [ ] The repaired game still shows in the Analyst Workspace match list
- [ ] Match detail panel displays correctly after repair
- [ ] No deliveries or scoring data changed
- [ ] `phases["historical_import"]["_repair_log"]` contains a Phase 5K entry

### 3.4 New Import Verification (Regression)

- [ ] Submit a new Cricsheet JSON through dry-run → apply
- [ ] Confirm new game has Phase 5J metadata from the start
- [ ] Call repair-metadata on the new batch → response is `already_complete`
- [ ] No fields were overwritten

---

## 4. Validation Results

### Backend

```
pytest backend/tests/test_health.py backend/tests/test_analyst_pro_features.py \
       backend/tests/test_results_endpoint.py backend/tests/test_dls_calculations.py \
       backend/tests/test_historical_import_apply.py backend/tests/test_historical_import_backfill.py
```

Results: **All tests pass** (14 + 14 + 7 + 21 + 14 + 16 = 86 tests)

### Frontend

```
cd frontend && npm run guard:fake-data     → 0 errors, 3 acceptable warnings
cd frontend && npm run type-check          → clean
cd frontend && npm run build-only          → ✓ built successfully
npx vitest run tests/unit/AnalystWorkspaceView.spec.ts → 34/34 passed
```

---

## 5. What Was NOT Changed

- Scoring engine (`scoring_service.py`)
- DLS calculations (`dls_calculations.py`)
- Live bus (`live_bus.py`)
- Historical import delivery service
- Coach Pro Plus / video analysis
- Mental analysis
- `HistoricalImportBatch` model (no migration needed)
- `Game` model (repair writes to existing `phases` JSON column)
- Analyst Workspace Vue template/logic (CSS-only change)
- Any other route, service, or model not mentioned above

---

## 6. Phase 5L Readiness Notes

Phase 5L (registry/model-training work) can proceed now that:

1. New imports produce accurate Phase 5J metadata from the outset.
2. Legacy imports have a controlled repair path (or a documented reimport path).
3. The Analyst Workspace dark-theme is fixed, removing a QA blocker.
4. All required test gates pass cleanly.

**Recommended Phase 5L focus areas**:
- ML dataset registry table (requires migration — audit first)
- Export of finalized historical batch metadata for training pipelines
- Raw JSON retention (deferred from Phase 5I) if training pipeline requires it

---

## 7. Repair Decision Summary

| Scenario | Outcome |
|---|---|
| Game already has Phase 5J fields | `already_complete` — no change |
| Game is legacy AND batch has Phase 5J metadata | `repaired` — fields backfilled, audit logged |
| Game is legacy BUT batch lacks Phase 5J metadata | `409` refused — reimport required |
| Batch not found | `404` |
| Batch not yet applied | `409` not applicable |
| Game is live/in-progress | `409` refused — live games never touched |
| Game is not a historical import | `409` refused — not applicable |
| `confirm` not true | `422` |

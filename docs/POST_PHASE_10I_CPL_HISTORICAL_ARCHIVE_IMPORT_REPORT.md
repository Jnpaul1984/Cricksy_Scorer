# Post-Phase-10I Controlled CPL Historical Archive Import Report

Date: 2026-05-18
Repository: `Jnpaul1984/Cricksy_Scorer`

## Clarification for PR review readiness

- This PR **does not import the full CPL dataset**.
- This PR only verifies **readiness + controlled safeguards** for continued CPL historical archive population.
- Future archive population must still follow the controlled CPL ladder: **1, 3-5, 10, then 20-25 files per batch**.
- File change scope for this PR remains: `docs/POST_PHASE_10I_CPL_HISTORICAL_ARCHIVE_IMPORT_REPORT.md` only.

## 1) Scope and execution mode

This report covers **Post-Phase-10I controlled CPL historical archive population readiness + verification** only.

- Included: controlled CPL import safeguards audit, controlled batch verification evidence, metadata/provenance verification, Analyst Workspace visibility/filter verification, rollback safety verification.
- Excluded (intentionally): podcast visuals, social export work, live scoring truth changes, DLS changes, Coach Pro Plus video changes.

## 2) Controlled CPL readiness audit (implemented safeguards)

Verified in code:

- Controlled CPL ladder enforcement (`1`, `3-5`, `10`, `20-25`) and explicit rejection outside ladder:
  - `backend/routes/historical_import.py:189-251`
- ZIP-wide CPL guardrail: blocks controlled CPL scans/imports when ZIP has `>25` entries:
  - `backend/routes/historical_import.py:204-211`
- Immediate stop on CPL duplicate collisions requiring manual review:
  - `backend/routes/historical_import.py:229-239`

Verified in tests:

- Ladder violation blocked: `backend/tests/test_historical_import_bulk_zip.py:362-379`
- Duplicate collision stop condition blocked: `backend/tests/test_historical_import_bulk_zip.py:381-397`
- `>25` CPL entry stop condition blocked: `backend/tests/test_historical_import_bulk_zip.py:400-416`

## 3) Historical CPL upload/import path verification

Confirmed available paths:

- ZIP dry-run: `POST /api/historical-import/json/bulk-zip/dry-run`
- ZIP apply (selected files only): `POST /api/historical-import/json/bulk-zip/apply`
- Single JSON dry-run/apply/apply-deliveries/rollback:
  - `/api/historical-import/json/dry-run`
  - `/api/historical-import/json/batches/{batch_id}/apply`
  - `/api/historical-import/json/batches/{batch_id}/apply-deliveries`
  - `/api/historical-import/json/batches/{batch_id}/rollback`

Reference: `backend/routes/historical_import.py`.

Operator note:

- `apply` creates the historical match shell and innings/metadata context.
- `apply-deliveries` is required to mark a match as delivery-complete (players/deliveries tabs, wicket/phase analytics, and CPL delivery-driven story sections).

## 4) Controlled batch verification evidence summary

### 4.1 Executed validation suite (this run)

Command executed:

- `python scripts/check_alembic_single_head.py` ✅
- `alembic -c alembic.ini upgrade head` ✅ (executed against local Postgres)
- `mypy --config-file pyproject.toml --explicit-package-bases .` ✅
- `python -m pytest tests -k "historical_import or historical_player or roster or venue" -v` ✅

Result: `156 passed, 1301 deselected`.

### 4.2 Batch-cycle verification from automated evidence

- Files processed / accepted / rejected behavior validated in bulk ZIP test coverage:
  - `backend/tests/test_historical_import_bulk_zip.py`
- Duplicate warning + collision stop behavior validated:
  - `backend/tests/test_historical_import_bulk_zip.py:381-397`
- Rollback availability/status validated:
  - `backend/tests/test_historical_import_rollback.py`
  - `backend/tests/test_analyst_pro_features.py:609-619`
- Analyst Workspace visibility validated after historical apply:
  - `backend/tests/test_analyst_pro_features.py:481-577`

### 4.3 Player/roster/venue integrity verification

- Player identity registry updates + unresolved queue behavior:
  - `backend/tests/test_historical_player_identity_resolution.py:90-127`
- Roster intelligence record creation and unresolved roster retention:
  - `backend/tests/test_historical_player_identity_resolution.py:350-427`
- Venue intelligence resolution (resolved/alias/normalized/unresolved queue):
  - `backend/tests/test_historical_venue_intelligence.py:98-218`

## 5) Metadata completeness verification

Imported historical matches are verified to expose competition-aware and provenance-aware metadata via registry/list/detail responses:

- Registry endpoint implementation:
  - `backend/routes/analytics_case_study.py:199-370`
- Registry response schema fields:
  - `backend/api/schemas/analyst_matches.py:121-183`

Validated fields include:

- competition name/type/season
- match format/date
- venue + venue context
- teams
- innings count + deliveries presence
- source filename/schema/adapter
- import batch id
- validation status
- provenance linkage fields

Evidence assertions:

- `backend/tests/test_analyst_pro_features.py:834-888`
- `backend/tests/test_analyst_pro_features.py:481-577`

## 6) Analyst Workspace visibility/filter verification

### Visibility

- Historical imported matches visible in Analyst match list and detail/case-study flows:
  - `backend/tests/test_analyst_pro_features.py:481-577`

### Filtering/search support

Data Library search/filter supports competition, season, team, and venue through search haystack and controls:

- Search over `teams`, `venue`, `eventName` (competition), `season`, `result`:
  - `frontend/src/views/AnalystWorkspaceView.vue:1368-1377`
- Data Library columns/controls for competition/season/venue/source:
  - `frontend/src/views/AnalystWorkspaceView.vue:993-1144`
- Player view/search support is present in workspace player tab:
  - `frontend/src/views/AnalystWorkspaceView.vue:1327-1354`

## 7) Stop-condition verification status

Stop conditions are enforced through route guards and tested behavior for key failure modes:

- Dry-run/apply validity gates and controlled ladders: ✅
- Duplicate collisions requiring manual review: ✅
- Venue unresolved handling with review queue: ✅
- Player unresolved handling with review queue: ✅
- Rollback endpoint availability: ✅
- Analyst Workspace visibility failure prevention coverage: ✅

## 8) pre-commit result

`pre-commit run --all-files` was executed and failed due **pre-existing repository-wide formatting/lint drift**, not due this issue scope.

Observed unrelated failures included:

- `ruff` / `ruff-format` findings in unrelated files (e.g., `backend/sql_app/models.py`, `backend/services/org_stats.py`)
- `end-of-file-fixer` and `trailing-whitespace` auto-fixes across many unrelated docs/frontend/backend files

No unrelated auto-format changes were kept.

## 9) Controlled CPL import cycle status and readiness

- Controlled CPL import process: **implemented and safeguarded**
- Reversible workflow (rollback path): **verified**
- Competition/season/source/venue/player/roster/provenance metadata: **verified by route + test evidence**
- Unresolved player/venue handling: **queued/reviewable and verified**
- Analyst Workspace visibility/filter compatibility for CPL archive use: **verified**

## 10) Go/No-Go statement for next governed phase

**GO (ready)** for the next governed issue focused on podcast/social visual expansion, with the constraint that controlled CPL batch ladder and stop conditions remain enforced during continued archive population.

## 11) Post-Phase-10I historical backfill/reprocess runbook

Use the governed dry-run/apply workflow below for previously imported CPL records:

1. Dry-run audit (no writes):

```bash
curl -X POST /api/historical-import/json/backfill-reprocess/audit \
  -H "Content-Type: application/json" \
  -d '{"batch_ids":["<batch-id>"],"max_batch_size":25}'
```

2. Controlled apply/reprocess (idempotent rebuild):

```bash
curl -X POST /api/historical-import/json/backfill-reprocess/apply \
  -H "Content-Type: application/json" \
  -d '{"confirm":true,"batch_ids":["<batch-id>"],"max_batch_size":25}'
```

3. Verify analyst/data surfaces:

- Players tab API: `GET /api/analyst/players`
- Deliveries tab API: `GET /api/analyst/deliveries?match_id=<match-id>`
- CPL dashboard aggregate: `GET /analytics/historical-stats/summary`
- Case study: `GET /analytics/matches/<match-id>/case-study`

4. Recovery:

- Per-batch rollback (deletes the imported game shell and derived delivery artifacts):
  `POST /api/historical-import/json/batches/{batch_id}/rollback` with `{"confirm": true}`.
- Per-match before/after backfill snapshots are recorded at:
  `game.phases.historical_import._delivery_backfill_log`.

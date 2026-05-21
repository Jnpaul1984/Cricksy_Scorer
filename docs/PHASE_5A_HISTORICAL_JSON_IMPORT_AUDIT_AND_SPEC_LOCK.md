# PHASE 5A — Historical JSON Match Import Audit and Spec Lock

**Repository:** `Jnpaul1984/Cricksy_Scorer`
**Date:** 2026-05-10
**Phase:** 5A (governance/audit/spec-lock only)
**Scope:** Docs-only. No importer code, routes, migrations, or schema changes in this phase.

---

## 1) Purpose and Scope

Define a safe, repo-grounded spec for importing historical cricket matches from structured JSON **before** any importer implementation (Phase 5B).

This phase locks:
- what must be validated,
- what can and cannot be written,
- how to preview/dry-run,
- how to prevent duplicate/corrupt imports,
- and what data/contracts are required from the user.

---

## 2) Known Historical JSON Source Assumptions

Assumptions for first import source:
- Source files were used in model training and are more structured than OCR/PDF/photo inputs.
- Files may vary by competition type (domestic/international).
- Files likely contain match-level metadata + innings + ball-by-ball events.
- Source player/team IDs may not match Cricksy runtime IDs.
- Source timestamps/timezones may be inconsistent and require normalization.

Non-assumption: current repo has **no production historical JSON importer** yet.

---

## 3) Required Sample Files Needed from User

Before Phase 5B starts, user must provide:
1. **2–3 representative historical JSON files** from the training pipeline.
2. **At least one complete match** with full ball-by-ball data.
3. **One domestic/non-international sample** (if format differs).
4. **One international sample** (if format differs).
5. **Any schema notes/spec from training pipeline**, including optional/nullable fields and known anomalies.

Current repo JSON files found are mostly simulated/test fixtures (not confirmed historical production source), so user-provided real samples are still required.

---

## 4) Current Cricksy Match/Game DB Model Audit

Current match truth model is centered on `Game`:
- `games` row stores teams (`team_a`, `team_b`) as JSON,
- live/runtime state (`status`, `current_inning`, totals),
- delivery ledger (`deliveries` JSON),
- scorecards (`batting_scorecard`, `bowling_scorecard`),
- result/toss/match config fields.

Findings:
- Game creation and scoring paths are optimized for live scoring flows.
- Historical imports must not overwrite live-scored rows.
- `created_by_user_id` exists and is relevant for ownership/isolation scoping.

---

## 5) Current Innings/Delivery/Player/Team Model Audit

### Innings
- No dedicated normalized innings table for canonical historical ingestion state.
- Innings summary is partly represented by `first_inning_summary` + current innings runtime fields.

### Deliveries
- Two representations exist:
  1. authoritative gameplay ledger in `Game.deliveries` JSON,
  2. normalized `Delivery` table model.
- Field-shape drift risk exists between some service code and normalized table definitions; mapping must be locked explicitly in Phase 5B.

### Players/Teams
- `Team` is org/user-owned (`owner_user_id`, optional `coach_user_id`).
- `Player` table exists (integer PK) while live game team/player references in JSON commonly use string IDs.
- Importer must resolve identity mapping safely; never assume direct key compatibility.

---

## 6) Current Analyst Endpoint Dependency Audit

Analyst Workspace dependencies currently include:
- `GET /analytics/matches` (list completed analyst matches)
- `GET /analytics/matches/{id}/case-study`
- `GET /api/analyst/matches/{id}`
- `GET /api/analyst/export-data`
- `GET /api/analyst/matches/{id}/ai-summary`
- `GET /api/analyst/matches/{id}/context-package`

Access/isolation pattern:
- analyst endpoints use role gating (`analyst_pro`, `org_pro`) and scoped game filtering via `scoped_games_stmt`.
- imported historical rows must remain compatible with these existing selectors/filters.

---

## 7) Current Import/Upload/OCR Code Audit (if any)

Findings:
- No `/import` match endpoint exists.
- No OCR pipeline for match ingestion is present in backend code.
- Existing upload flows are for Coach Pro Plus video sessions, not match imports.

Conclusion:
- Historical JSON importer is net-new implementation work for Phase 5B.

---

## 8) JSON Format Discovery Plan

Phase 5B must start with format discovery (no writes):
1. Parse sample files in dry-run mode only.
2. Capture top-level keys and nested field paths.
3. Detect variant schemas and classify them (e.g., v1 domestic, v2 international).
4. Produce canonical internal contract + per-variant adapter rules.
5. Record required/optional/defaulted fields.
6. Flag ambiguous fields for explicit user approval before write-path enablement.

---

## 9) JSON-to-Cricksy Schema Mapping Plan

Mapping strategy (spec-lock):
- Match metadata → `Game` setup fields (`match_type`, teams, toss/decision, limits, result metadata).
- Innings totals → innings summary structures + derived game totals for completed state.
- Ball events → canonical delivery contract compatible with existing gameplay/analytics expectations (`inning`, `over_number`, `ball_number`, batter/bowler IDs, runs/extras/wicket context).
- Team/player source identifiers → deterministic identity mapping layer (not direct blind insertion into live IDs).

Importer must output data that existing analyst/gameplay reads can consume without schema surprises.

---

## 10) Validation Rules Before Import

Required pre-write validation:
- JSON structural validity.
- Required match metadata presence (teams, format or overs context, outcome state).
- Innings-level arithmetic validation:
  - legal balls/overs consistency,
  - runs = batter runs + extras,
  - wickets <= 10,
  - innings and match totals reconcile.
- Delivery sequencing validation (monotonic inning/over/ball order).
- Dismissal type + fielder constraints for wicket events.
- Unknown enum/value normalization checks (`extra_type`, dismissal labels, match type).
- Ownership/org assignment validation before insert.

Any critical validation failure must block write.

---

## 11) Dry-Run/Preview Requirements

Importer must support **dry-run first**:
- no DB writes in dry-run,
- return parsed summary,
- return validation errors/warnings by file and by event,
- return normalized preview payload and projected inserted counts,
- require explicit confirm step before write mode.

Dry-run output should include deterministic checksum/fingerprint for the exact source file.

---

## 12) Duplicate Detection Rules

Duplicate prevention spec:
- Compute source fingerprint (e.g., SHA-256 of canonicalized file bytes).
- Also compute semantic key (competition/date/team tuple + source match id if present).
- Block import when exact fingerprint already imported successfully.
- Mark semantic collisions as `requires_review` unless explicitly forced with audit trail.
- Duplicate checks must be org-scoped where ownership differs.

No silent upserts over existing match truth.

---

## 13) Player/Team Matching Rules

Deterministic matching order:
1. exact external/source ID map (if supplied),
2. strict normalized name match within org scope,
3. optional alias table match,
4. otherwise unresolved.

Rules:
- unresolved entities must not be auto-created silently in strict mode,
- ambiguous matches must return blocking validation errors,
- optional create-new behavior (if enabled later) must be explicit and auditable.

---

## 14) Historical Match Metadata Requirements

Each imported match must retain:
- source system name,
- source file name/path token,
- source checksum/fingerprint,
- import timestamp,
- importer version,
- org/owner context,
- source match identifier (if available),
- format/competition/date/venue (when available),
- import mode (`dry_run`, `committed`, `rolled_back`).

---

## 15) Import Status/Audit Trail Requirements

Phase 5B should add explicit auditability primitives (likely new tables):
- import batch/job record,
- per-file status,
- per-match status,
- summary counters (accepted/rejected/warnings/errors),
- user who initiated import,
- timestamps and lifecycle status transitions.

All write operations must be traceable to an import batch.

---

## 16) Error Reporting Format

Error contract should be machine-readable and human-usable:
- top-level: `request_id`, `batch_id`, `status`,
- arrays: `errors[]`, `warnings[]`,
- each error item: `code`, `message`, `severity`, `file`, `path`, `inning`, `over`, `ball`, `raw_value`, `expected`.

Align with existing API error envelope style where practical (`request_id` + typed error object).

---

## 17) Postgres Migration Expectations (if importer needs new tables)

If Phase 5B introduces import-tracking tables:
- add Alembic migrations with upgrade path,
- follow master checklist migration governance,
- validate migrations against real Postgres (not SQLite-only).

`docs/POSTGRES_MIGRATION_VALIDATION_GATE.md` is not present; use the gate defined in `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`.

---

## 18) No-Corruption Rules for Live Scoring Truth

Hard rules:
- never mutate ongoing live matches via importer,
- never silently rewrite existing official scorecards/deliveries,
- imported data must be clearly marked historical/imported,
- writes must be idempotent and duplicate-protected,
- importer must operate in explicit commit mode only after dry-run approval.

---

## 19) Analyst Workspace Integration Expectations

Imported historical matches should become discoverable by existing analyst APIs without bespoke frontend hacks:
- included in completed-match list flows where ownership allows,
- available to case-study/export/context-package pipelines,
- scoped by existing role/org access patterns.

No fake-data fallback should be required for imported matches.

---

## 20) Required Tests/Gates for Implementation (Phase 5B)

Minimum required tests:
- schema discovery/variant adapter tests,
- validation failure matrix tests,
- dry-run no-write guarantee tests,
- commit path success tests,
- duplicate detection/idempotency tests,
- player/team matching ambiguity tests,
- org isolation access tests,
- rollback/cleanup tests,
- analyst endpoint compatibility regression tests.

Validation gates:
- backend lint/type/tests per repo standards,
- Postgres migration validation if schema changes are introduced.

---

## 21) Protected Files/Areas

Phase 5B must not directly alter deterministic live scoring behavior except through explicitly approved importer write-path boundaries.

Protected/high-risk areas:
- core live scoring rule paths,
- DLS logic,
- live bus/socket update semantics,
- analyst feature behavior unrelated to import integration,
- Coach Pro Plus video and mental-analysis systems,
- unrelated migrations/workflows/infra.

---

## 22) Recommended Phase 5B Implementation Issue

**Recommended issue title:**
`Phase 5B: Historical JSON Importer (Dry-Run + Validation + Idempotent Commit)`

**Required scope for Phase 5B issue:**
- implement JSON format discovery adapters from real sample files,
- implement dry-run preview API/service (no writes),
- implement validated commit path with duplicate protection,
- implement import batch audit trail + rollback capability,
- wire imported matches to existing analyst match discovery with org isolation,
- add tests and migration validation gates.

---

## 23) Rollback/Cleanup Plan for Imported Data

Rollback requirements for Phase 5B:
- every imported record must link to import batch id,
- support batch-level cleanup (soft-delete or hard-delete strategy must be explicit),
- cleanup must remove dependent imported artifacts in safe order,
- cleanup must never touch non-imported/live-scored matches,
- emit post-cleanup report with counts and any residual conflicts.

---

## Audit Sources Reviewed

- `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`
- `docs/PHASE_4A_ANALYST_SYSTEM_ARCHITECTURE_AUDIT_AND_SPEC_LOCK.md`
- `docs/CRICKSY_ANALYST_SYSTEM_BLUEPRINT_V1.md`
- `docs/ANALYST_PRODUCTION_WORKFLOW_V1.md`
- `docs/PHASE_1D_OPEN_PR_TRIAGE_AND_CHECKLIST_NUMBERING.md`
- `backend/sql_app/models.py`
- `backend/sql_app/schemas.py`
- `backend/sql_app/crud.py`
- `backend/routes/gameplay.py`
- `backend/routes/games_router.py`
- `backend/routes/games_core.py`
- `backend/routes/analyst_pro.py`
- `backend/routes/analytics_case_study.py`
- `backend/routes/fan_mode.py`
- `backend/routes/teams.py`
- `backend/services/analyst_access.py`
- `backend/services/game_helpers.py`
- `backend/services/scorecard_service.py`
- `backend/train_win_predictors.py`
- JSON fixtures/samples reviewed:
  - `simulated_t20_match.json`
  - `backend/tests/simulated_t20_match.json`
  - `frontend/simulated_t20_match.json`
  - `backend/tests/ci_smoke/fixtures/first_innings_120.json`

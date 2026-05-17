# PHASE 10A.1 — Competition-Aware Historical Match Registry Audit + Spec Lock

**Repository:** `Jnpaul1984/Cricksy_Scorer`  
**Date:** 2026-05-17  
**Phase:** 10A.1 (governance/audit/spec-lock only)  
**Scope:** Docs-only. No backend/frontend/tests/migrations/workflow/package implementation in this issue.

---

## 1. Purpose and phase boundaries

This document locks the Phase 10A.1 audit/spec boundaries before any Phase 10B implementation.

- Governance-only: define what **must** be implemented later, and what is protected now.
- No runtime implementation changes in this phase.
- Preserve deterministic cricket-truth paths and protected production areas.

Grounding: `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md:3164-3337`.

## 2. Source documents reviewed

- `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md:3164-3337`
- `docs/PHASE_5A_HISTORICAL_JSON_IMPORT_AUDIT_AND_SPEC_LOCK.md:1-355`
- `docs/CRICKSY_ANALYST_SYSTEM_BLUEPRINT_V1.md:1-463`
- `docs/ANALYST_PRODUCTION_WORKFLOW_V1.md:1-651`
- `docs/COMPETITION_INTELLIGENCE_FRAMEWORK_V1.md:1-385`

## 3. Current repo audit summary

Current repo already contains a Phase 5 historical import pipeline (dry-run, batch tracking, apply, delivery import, rollback, training-status, metadata repair, bulk ZIP, OCR review), Analyst Workspace integration hooks, and registry/provenance endpoints.

Key evidence:
- Historical import API + services: `backend/routes/historical_import.py`, `backend/services/historical_import_preview.py`, `backend/services/historical_import_apply_service.py`, `backend/services/historical_import_service.py`.
- Historical batch model + migration: `backend/sql_app/models.py:2757-2843`, `backend/alembic/versions/a9b8c7d6e5f4_add_historical_import_batch_table.py`, `backend/alembic/versions/b1c2d3e4f5a6_add_applied_game_id_to_historical_import_batches.py`.
- Analyst list/detail/registry: `backend/routes/analytics_case_study.py:81-322`, `backend/routes/analyst_pro.py:350-656`, `backend/api/schemas/analyst_matches.py`.
- Analyst frontend import/data-library/registry UI: `frontend/src/views/AnalystWorkspaceView.vue:761-1134, 1271-1696`, `frontend/src/components/HistoricalImportPanel.vue`, `frontend/src/components/HistoricalImportBulkZipPanel.vue`.

## 4. Existing historical JSON import capability audit

Existing capabilities:
- Dry-run parser/validator with format detection (`cricksy_fixture`, `cricsheet_json`, `unknown`) and structured errors/warnings: `backend/services/historical_import_preview.py:248-579`.
- Persistable preview batches (`record_preview=true`): `backend/routes/historical_import.py:563-681`.
- Apply gate requires explicit confirm and valid batch: `backend/services/historical_import_apply_service.py:103-295`.
- Delivery import gate includes hash verification and totals reconciliation: `backend/services/historical_import_apply_service.py:423-680`.
- Rollback endpoint with safety checks: `backend/routes/historical_import.py:1483-1525`.
- Bulk ZIP dry-run/apply with duplicate checks and metadata-only deferred mode: `backend/routes/historical_import.py:1075-1390`.
- OCR review candidate flow with explicit non-authoritative positioning: `backend/routes/historical_import.py:694-1072`.

## 5. Existing registry/provenance capability audit

Existing provenance data includes:
- `source_filename`, `source_format`, `source_hash_sha256`, `semantic_key`, ownership, counts, status, finalized marker, linked applied game id: `backend/sql_app/models.py:2765-2843`.
- Registry endpoint returns competition/season/venue/source/validation/registration/training eligibility: `backend/routes/analytics_case_study.py:195-322`.
- Registry schema contract is explicit for Analyst UI: `backend/api/schemas/analyst_matches.py:99-172`.

## 6. Existing Analyst Workspace compatibility audit

Already implemented:
- Completed matches list from `/analytics/matches`: `backend/routes/analytics_case_study.py:81-131` and `frontend/src/services/api.ts:792-794`.
- Imported badge and historical source distinctions: `frontend/src/views/AnalystWorkspaceView.vue:222-225, 1060-1075`.
- Match intelligence detail load: `frontend/src/views/AnalystWorkspaceView.vue:306-760, 1533-1545`.
- Registry & provenance panel: `frontend/src/views/AnalystWorkspaceView.vue:761-875`.
- Import tab integrates JSON, bulk ZIP, OCR review: `frontend/src/views/AnalystWorkspaceView.vue:1101-1114`.

## 7. Existing competition metadata capability audit

Current imported match metadata fields available in historical import paths:
- `event_name`, `season`, `match_number`, `source_dates`, `match_date`, `venue`: `backend/services/historical_import_preview.py:513-523`, `backend/services/historical_import_apply_service.py:228-243`.
- Analyst match list exposes event/season/match_number/source_dates: `backend/api/schemas/analyst_matches.py:41-50`, `backend/routes/analytics_case_study.py:119-128`.

Gap: no explicit canonical `competition_type`/`competition_name` split and no locked taxonomy for franchise/club/international/domestic/school/academy/unknown in current runtime importer.

## 8. Existing venue/team/player/roster capability audit

- `Game` stores teams as JSON blobs (`team_a`, `team_b`) and deliveries as JSON ledger: `backend/sql_app/models.py:274-356`.
- Imported deliveries can populate inline team players, batting/bowling scorecards, innings summaries: `backend/services/historical_import_apply_service.py:585-667`.
- No dedicated historical roster snapshot table (playing XI/squad/substitute state normalized by competition context is not modeled yet).
- Tournament models exist but are separate from import provenance contract (`Tournament`, `TournamentTeam`, `TournamentFixture`): `backend/sql_app/models.py:1703-1806`.

## 9. Existing API endpoint audit

Historical import endpoints:
- `POST /api/historical-import/json/dry-run`
- `GET /api/historical-import/json/batches`
- `POST /api/historical-import/json/batches/{batch_id}/apply`
- `POST /api/historical-import/json/batches/{batch_id}/apply-deliveries`
- `POST /api/historical-import/json/batches/{batch_id}/rollback`
- `GET /api/historical-import/json/batches/{batch_id}/training-status`
- `POST /api/historical-import/json/bulk-zip/dry-run`
- `POST /api/historical-import/json/bulk-zip/apply`
- OCR review endpoints under `/api/historical-import/json/ocr-review/...`

Evidence: `backend/routes/historical_import.py:563-1777`.

Analyst compatibility endpoints:
- `GET /analytics/matches`
- `GET /analytics/matches/{match_id}/case-study`
- `GET /analytics/matches/{match_id}/ai-summary`
- `GET /analytics/matches/{match_id}/registry`
- `GET /api/analyst/matches/{match_id}`
- `GET /api/analyst/export-data`
- `GET /api/analyst/matches/{match_id}/ai-summary`
- `GET /api/analyst/matches/{match_id}/context-package`

Evidence: `backend/routes/analytics_case_study.py:81-322`, `backend/routes/analyst_pro.py:350-656`.

## 10. Existing frontend UX audit

- Analyst Workspace has tabs for Matches, Data Library, Import Data, and detail panel with registry/provenance: `frontend/src/views/AnalystWorkspaceView.vue:152-1134`.
- Imported matches get explicit visual labels and cleanup action backed by rollback API: `frontend/src/views/AnalystWorkspaceView.vue:222-225, 273-281, 1654-1684`.
- Podcast prep package uses real loaded detail data and insufficient-data messaging (no fake path): `frontend/src/views/AnalystWorkspaceView.vue:636-753, 1756-1884`.
- JSON import panel enforces dry-run-first and staged apply/apply-deliveries: `frontend/src/components/HistoricalImportPanel.vue:43-552`.
- Bulk ZIP panel supports deferred metadata-only mode messaging: `frontend/src/components/HistoricalImportBulkZipPanel.vue:34-112`.

## 11. Existing tests and CI gate audit

Existing backend tests cover dry-run/apply/rollback/delivery import/batch tracking/bulk ZIP/training/backfill and analyst routes:
- `backend/tests/test_historical_import_dry_run.py`
- `backend/tests/test_historical_import_apply.py`
- `backend/tests/test_historical_import_apply_deliveries.py`
- `backend/tests/test_historical_import_rollback.py`
- `backend/tests/test_historical_import_batch_tracking.py`
- `backend/tests/test_historical_import_bulk_zip.py`
- `backend/tests/test_historical_import_training_status.py`
- `backend/tests/test_historical_import_backfill.py`
- `backend/tests/test_analyst_pro_features.py`

Frontend unit coverage includes Analyst Workspace and import panels:
- `frontend/tests/unit/AnalystWorkspaceView.spec.ts`
- `frontend/tests/unit/HistoricalImportBulkZipPanel.spec.ts`
- `frontend/tests/unit/HistoricalOcrReviewPanel.spec.ts`

CI gates include lint, security, backend tests, integration tests, DLS tests, frontend guard/type-check/build, and E2E gates. Docs-only changes are path-ignored in CI/lint workflows.
- `.github/workflows/ci.yml:6-15, 52-304`
- `.github/workflows/lint.yml:6-15`

## 12. Gap analysis

Major gaps for Phase 10B competition-aware foundation:
1. Canonical contract not yet locked for explicit competition taxonomy and tournament context object.
2. Adapter strategy currently limited to shape detection; not a formal adapter registry with contract versioning.
3. Roster snapshot semantics (playing XI/squad/substitutes/unresolved mapping) are not locked in persisted canonical form.
4. Venue metadata contract is minimal (`venue` string only); no normalized venue identity/quality flags.
5. Registry lacks explicit `competition_type`, `competition_name`, and adapter lineage fields in canonical schema.
6. Analyst UI registry panel supports current fields but not full competition-aware contract fields.

## 13. Canonical Cricksy import contract spec

Phase 10B MUST normalize every supported source into a canonical object with required top-level sections:

- `match_metadata`
- `competition_context`
- `tournament_season_context`
- `venue_context`
- `team_context`
- `squad_roster_snapshot`
- `player_identity_mapping`
- `innings_summaries`
- `delivery_events`
- `result_metadata`
- `source_provenance`
- `validation_report`

Contract rules:
- Deterministic fields only for cricket-truth values.
- Explicit nullable handling (missing vs inferred vs unknown).
- Persist source lineage (`source_format`, `source_schema_version`, checksum, batch id).

## 14. JSON schema adapter strategy

Phase 10B adapter policy:
- Classify incoming payload as one of:
  - Cricksy internal JSON
  - Cricsheet-style JSON
  - Franchise tournament JSON
  - International match JSON
  - Domestic/club match JSON
  - School/academy match JSON
  - Unknown/unsupported
- Each adapter must map source -> canonical contract and emit adapter diagnostics.
- Unknown/unsupported must fail safely with dry-run report; no writes.

Grounding baseline detection exists in `backend/services/historical_import_preview.py:248-257`; this section locks expansion strategy.

## 15. Competition metadata spec

Required canonical competition fields:
- `competition_type` (enum): `franchise`, `club`, `international`, `domestic`, `school`, `academy`, `unknown`
- `competition_name` (nullable string)
- `competition_stage` (nullable string)
- `season` (nullable string)
- `match_format` (required normalized string)
- `tournament_name` (nullable string)
- `tournament_round` (nullable string)

Rules:
- If source is missing, set `competition_type="unknown"`; never fabricate.
- Preserve raw source competition values in provenance payload for traceability.

## 16. Squad/roster snapshot spec

Canonical `squad_roster_snapshot` must include per team:
- `playing_xi` (list)
- `named_squad` (list)
- `substitutes` (list)
- `unresolved_entries` (list of unresolved source players)
- `mapping_confidence` summary

Rules:
- Snapshot is match-scoped historical truth; do not mutate live team-management state.
- Ambiguous player mapping is blocking unless explicitly approved in later controlled flow.

## 17. Venue metadata spec

Canonical `venue_context` fields:
- `venue_name` (nullable)
- `city` (nullable)
- `country` (nullable)
- `ground_code` (nullable)
- `source_venue_raw` (nullable)
- `venue_resolution_status` (`resolved`, `unresolved`, `unknown`)

Rules:
- Never invent venue identity.
- Preserve raw source venue string even when unresolved.

## 18. Dry-run validation spec

Phase 10B dry-run requirements (lock):
- No writes to `Game`, `Delivery`, player/team entities in dry-run.
- Return canonical preview + structural and semantic validation report.
- Include file-level and section-level issues with severity.
- Return checksum and semantic key.
- Explicitly flag inferred/unknown competition and roster fields.

Grounding: existing dry-run no-write and issue reporting in `backend/services/historical_import_preview.py` and `backend/routes/historical_import.py:563-681`.

## 19. Duplicate detection and idempotency spec

Required duplicate protections:
- Exact duplicate by canonical file hash.
- Semantic duplicate by competition/date/team key (or stronger canonical key when available).
- Org/user scoped lookups as baseline.
- Apply endpoints must be idempotent with explicit statuses.

Grounding: `backend/services/historical_import_service.py:24-84`, `backend/services/historical_import_preview.py:37-55`, `backend/services/historical_import_apply_service.py:517-526`.

## 20. Import provenance/audit trail spec

Every imported match must keep a recoverable trail:
- Import batch id
- Source filename/format/hash/schema version
- Adapter id/version used
- User/org ownership scope
- Validation summary and warnings/errors
- Timestamp lifecycle (`dry_run`, `applied`, `deliveries_applied`, `rolled_back`, etc.)

Grounding baseline model: `backend/sql_app/models.py:2765-2843`.

## 21. Rollback/cleanup spec

Phase 10B rollback must remain:
- Batch-targeted
- Safety-gated
- Non-destructive to unrelated live or imported matches
- Audited with rollback log entries

Grounding: `backend/services/historical_import_apply_service.py:297-415`, `backend/routes/historical_import.py:1483-1525`.

## 22. Analyst Workspace integration spec

Imported matches in Phase 10B must:
- Appear in existing completed-match list and data library.
- Show imported status and registry/provenance metadata.
- Open match intelligence detail without errors.
- Expose innings/delivery availability accurately.
- Work with export paths when sufficient data exists.
- Keep podcast prep and AI sections safe under insufficient data.
- Require no fake frontend data path.

Grounding: `frontend/src/views/AnalystWorkspaceView.vue:153-225, 378-409, 636-875, 921-1094, 1101-1114, 1610-1884`.

## 23. Permission/RBAC/org isolation spec

Phase 10B must preserve RBAC/org scoping rules:
- Analyst endpoints remain `analyst_pro`/`org_pro` gated.
- Match visibility uses scoped query by user/org relationship.
- Rollback/import operations respect batch ownership scope.

Grounding: `backend/routes/analyst_pro.py:39-42`, `backend/services/analyst_access.py:10-25`, `backend/services/historical_import_apply_service.py:319-336`, `backend/tests/test_analyst_pro_features.py`.

## 24. AI boundary and deterministic cricket truth rules

Locked rule:
- Deterministic systems compute cricket truth (scores, innings, wickets, phase math, result, provenance).
- AI may summarize/explain/recommend only from available approved data.
- AI must not invent missing match/player/venue/competition context.
- If data is insufficient, AI output must degrade safely and be labeled limited/insufficient.

Grounding examples:
- Deterministic AI summary route statement: `backend/routes/analyst_pro.py:601-612`.
- Frontend deterministic fallback and insufficient-data handling: `frontend/src/views/AnalystWorkspaceView.vue:1547-1607, 1610-1629`.

## 25. Required migrations, if any, as a plan only

No migrations in Phase 10A.1.

Phase 10B migration planning (if approved):
- Extend historical provenance metadata storage for canonical competition/tournament/venue/roster fields.
- Add adapter lineage/version fields.
- Add optional normalized roster/identity tables only if current JSON blobs are insufficient.
- Maintain backward compatibility for existing Phase 5 batch and registry reads.

## 26. Protected areas

Phase 10B must not rewrite or destabilize:
- Live scoring truth paths (`Game.deliveries`, scoring services)
- DLS logic and tests
- Coach Pro Plus video analysis systems
- Subscription/tier enforcement and unrelated RBAC systems
- Existing completed phase evidence/workflows

Grounding: `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md:3199-3208, 3322-3328` and protected routes/services currently in use.

## 27. Phase 10B implementation scope recommendation

**Recommended issue title:**  
`Phase 10B: Competition-Aware Historical JSON Import Foundation Implementation`

MVP-bounded scope:
- Canonical competition-aware contract implementation (adapter + validator + provenance extension)
- Dry-run-first enforcement and write-gated apply behavior
- Duplicate/idempotency enforcement aligned to competition-aware keys
- Analyst Workspace compatibility updates only where needed for new canonical fields
- No advanced prediction engine changes, no broad dashboard rewrites

## 28. Required tests for Phase 10B

Must include:
- Schema classification and adapter mapping tests by competition type
- Canonical contract validation tests (required/nullable/inferred/unknown)
- Dry-run no-write tests
- Duplicate and idempotency tests (hash + semantic)
- Provenance and registry response tests
- Roster snapshot and player identity mapping tests
- Rollback/cleanup tests
- Analyst Workspace compatibility tests (list/detail/registry/export/AI fallback behavior)
- Org/RBAC isolation tests
- Migration tests (if schema changes introduced)

## 29. CI/gate requirements for Phase 10B

- Governance/spec-lock approval is a precondition to implementation PRs.
- Existing repository CI gates remain required for runtime changes.
- Keep fake-data guard, backend tests, DLS tests, lint/security gates, and relevant frontend tests.
- Add/extend targeted importer/registry/competition-aware test jobs only if necessary.

Grounding baseline: `.github/workflows/ci.yml`, `.github/workflows/lint.yml`.

## 30. Acceptance criteria for Phase 10A.1

Phase 10A.1 is complete when:
- This document exists at the required path.
- It is repo-grounded and cites concrete existing files/paths.
- It explicitly separates audit/spec-lock from implementation.
- It locks Phase 10B requirements for canonical import, competition metadata, roster snapshot, provenance, dry-run, duplicates, rollback, analyst compatibility, RBAC, and AI boundary.
- It preserves protected area constraints and does not propose broad rewrites.
- It ends with the required Phase 10B title and bounded MVP scope.

---

## Phase 10B recommended next issue

**Title:** `Phase 10B: Competition-Aware Historical JSON Import Foundation Implementation`

**Bounded MVP scope summary:** Implement competition-aware canonical normalization, adapter/validation boundaries, provenance and idempotent import behavior, and Analyst Workspace compatibility extensions using real data-only paths, without expanding into advanced prediction engine or broad dashboard rewrites.

# CRICKSY MASTER EXECUTION CHECKLIST

## Repository Grounding

Repository: `Jnpaul1984/Cricksy_Scorer`

Default branch: `main`

This checklist is for the existing Cricksy AI application. It is not a rebuild plan.

Cricksy already has a working production-oriented codebase, GitHub workflows, AWS/Amazon infrastructure references, FastAPI backend, frontend application, Alembic migrations, Docker Compose development flows, Coach Pro Plus Video Analysis, S3 upload handling, worker processing, and CI/CD gates.

All future development must improve the existing system safely.

---

# 0. Real Repo Structure

## Core Paths

- Backend app: `backend/`
- Backend entrypoint: `backend/main.py`
- Backend requirements: `backend/requirements.txt`
- Backend pytest config: `backend/pytest.ini`
- Backend pyproject/mypy/ruff/bandit config: `backend/pyproject.toml`
- Alembic config: `backend/alembic.ini`
- Alembic migrations: `backend/alembic/versions/`
- Frontend app: `frontend/`
- Frontend package config: `frontend/package.json`
- Frontend lockfile: `frontend/package-lock.json`
- Frontend services: `frontend/src/services/`
- Frontend stores: `frontend/src/stores/`
- Infra/Terraform: `infra/terraform/`
- Docker Compose local: `docker-compose.yml`
- Docker Compose dev: `docker-compose.dev.yml`
- Docker Compose CI: `docker-compose.ci.yml`
- Docker Compose test: `docker-compose.test.yml`
- GitHub workflows: `.github/workflows/`

---

# 1. Existing CI/CD Gates

These gates are already defined in the repo and must be respected.

## GitHub Workflow Files

- `.github/workflows/ci.yml`
- `.github/workflows/lint.yml`
- `.github/workflows/deploy-backend.yml`
- `.github/workflows/deploy-frontend.yml`
- `.github/workflows/release.yml`
- `.github/workflows/copilot-agent-run.yml`

## Current CI Workflow Requirements

The main CI workflow runs on pushes to:

- `main`
- `agent/**`
- `feature/**`

It also runs on pull requests into `main`.

Important: Markdown and docs-only changes are ignored by CI according to the current path-ignore rules.

## Required CI Jobs

### Pre-commit

- Installs `pre-commit==3.5.0`
- Runs `pre-commit run --all-files || true`
- Runs `pre-commit run --all-files`

### Lint + Type Safety

- Python version from `.python-version`
- Installs backend dependencies from `backend/requirements.txt`
- Runs `ruff check .`
- Runs `ruff format --check .`
- Runs `mypy --config-file pyproject.toml --explicit-package-bases .` from `backend/`

### Security

- Runs `pip-audit` against `backend/requirements.txt`
- Runs `bandit -r backend -c backend/pyproject.toml -ll`

### Backend Fast Tests

Runs from `backend/` with in-memory DB:

```bash
pytest -q tests/test_health.py tests/test_results_endpoint.py
```

Required env in CI:

```bash
CRICKSY_IN_MEMORY_DB=1
DATABASE_URL=sqlite+aiosqlite:///:memory:?cache=shared
APP_SECRET_KEY=test-secret-key
PYTHONPATH=<repo-root>
```

### Backend Integration Tests

Runs:

```bash
pytest tests/integration/ -v --tb=short --cov=. --cov-report=xml --cov-report=term
```

### Backend DLS Tests

Runs:

```bash
pytest tests/test_dls_calculations.py -v --tb=short
```

### Frontend Build + Type Check

Runs from `frontend/`:

```bash
npm ci
npm run guard:fake-data
npm run type-check
npm run build-only
```

With:

```bash
VITE_API_BASE=http://localhost:8000
```

---

# 2. Global Execution Rules

## Rule 1 — Existing App First

Cricksy is already an existing app. All work must be treated as controlled enhancement.

Do not recreate working systems.
Do not replace architecture unless the audit proves it is necessary and the user approves it.
Do not rewrite large areas when a targeted patch works.
Do not bypass GitHub or CI/CD.

## Rule 2 — Branch and PR Discipline

All implementation phases should use:

- `feature/<phase-name>` for normal features
- `agent/<phase-name>` for Copilot/agent-led work
- Pull request into `main`

No production-sensitive work should be merged without passing CI.

## Rule 3 — Pre-Phase Audit Required

Before each implementation phase, perform a repo audit.

Audit must identify:

- Existing files affected
- Existing models affected
- Existing API routes affected
- Existing frontend components affected
- Existing services/workers affected
- Existing migrations affected
- Existing tests affected
- Existing CI impact
- Existing deployment impact
- Existing data impact
- Existing role/tier impact
- Existing AI/model impact

Audit must state:

- What already works
- What must not change
- What can be safely improved
- What needs test coverage before editing
- What needs user approval before editing

## Rule 4 — Spec Lock Required

After audit, write a Spec Lock before coding.

Spec Lock must include:

- Objective
- Strict scope
- Files allowed to change
- Files protected from change
- Product behavior
- API changes
- DB/schema changes
- Frontend behavior
- Permissions/RBAC behavior
- Feature flags
- Tests required
- CI commands required
- Rollback plan
- Acceptance criteria

## Rule 5 — Intelligence System Rule + Deterministic Cricket Truth Protection

Cricksy must not become AI everywhere.

All intelligence features must follow:

1. Deterministic systems calculate facts.
2. AI systems explain, summarize, recommend, or communicate.
3. Skills must be reusable, versioned, testable, and governed.
4. AI outputs must be grounded in approved data.
5. Confidence and limitations must be visible.
6. Expensive AI must be event-triggered, not always running.
7. Sensitive outputs require validation and review.
8. User-facing intelligence must respect role, organization, youth-safety, and data-boundary rules.

Hard gate:

- No LLM may calculate, overwrite, or mutate official cricket truth.

Deterministic systems own:

- scoring
- runs
- balls
- overs
- wickets
- innings state
- match result
- scorecards
- official player stats
- DLS
- validations
- filters
- metrics
- venue par calculations
- win probability model outputs where applicable

AI systems may only:

- explain
- summarize
- interpret
- recommend
- communicate
- generate reviewable reports
- answer questions grounded in approved data

Additional intelligence governance rules:

- Do not load all available cricket data into AI context. Load only the minimum relevant match/player/team/phase/video data required for the user’s question.
- AI-generated intelligence must expose confidence and limitations. Low-confidence insights must never be presented as certain.
- Continuous intelligence should be mostly deterministic and cheap. Expensive AI should only run on explicit triggers.
- No always-running LLM loops without explicit user approval, cost guardrails, and governance approval.
- Sensitive or high-impact outputs require validation and review before becoming official or coach-facing.

## Rule 6 — Migrations Are Controlled

Any DB model change must include:

- Alembic migration in `backend/alembic/versions/`
- Upgrade path
- Downgrade path where reasonable
- Test impact review
- Deployment risk review

Do not edit existing migrations unless fixing a migration that has not been deployed and the user approves.

### Postgres Migration Validation Gate (Mandatory)

> Any PR touching `backend/alembic/versions/` must run Alembic upgrade against real Postgres before merge. SQLite/in-memory tests are not sufficient for migration validation.

Migration touched?
- [ ] Run Alembic upgrade against Postgres
- [ ] Use the same Alembic command as deploy workflow where possible
- [ ] Confirm no multiple-head issue
- [ ] Confirm enum columns and enum seed inserts work on Postgres
- [ ] Confirm JSON/JSONB, UUID, ARRAY, server defaults, indexes, and constraints work on Postgres
- [ ] Confirm downgrade path or document why downgrade is not safe/applicable
- [ ] Do not rely only on SQLite/in-memory tests
- [ ] Include migration validation output in PR body

Required CI/Governance notes:

- Backend tests with `CRICKSY_IN_MEMORY_DB=1` are useful for app regression checks, but they are not migration validation.
- SQLite/in-memory test execution does not reliably catch PostgreSQL enum and other Postgres-specific type/DDL failures.
- Any new migration must be validated against real Postgres (for example via Docker Compose/test database or a deploy-compatible migration job) before merge.
- If deployment migration fails, ship a minimal migration-fix PR first; do not bundle feature refactors into the migration-fix change.

Recommended follow-up (documented only, do not implement in this issue):

- Add a PR workflow job that starts Postgres and runs Alembic upgrade for PRs touching `backend/alembic/versions/**`.

## Rule 7 — Protected Production Areas

These areas require extra caution:

- `backend/main.py`
- `backend/alembic/versions/`
- `backend/services/coach_plus_analysis.py`
- `backend/services/pose_service.py`
- `backend/workers/analysis_worker.py`
- `backend/scripts/run_video_analysis_worker.py`
- `frontend/src/services/coachPlusVideoService.ts`
- `frontend/src/stores/coachPlusVideoStore.ts`
- `infra/terraform/`
- `.github/workflows/`
- `backend/config/pricing.py`
- scoring/result endpoints and tests
- DLS calculation logic

Protected does not mean untouchable. It means audit first, spec lock, targeted edits only, and regression tests required.

---

# 3. Current Video Analysis System — Existing Assets

The repository already contains a Coach Pro Plus Video Analysis system.

Important existing files/docs include:

- `COMPLETE_VIDEO_ANALYSIS_FLOW.md`
- `README_COACH_PRO_PLUS_VIDEO_MVP.md`
- `COACH_PRO_PLUS_VIDEO_ANALYSIS_FILE_MANIFEST.txt`
- `TESTING_GUIDE_COACH_VIDEO.md`
- `COACH_PRO_PLUS_VIDEO_SESSIONS_SCAFFOLDING.md`
- `COACH_PRO_PLUS_VIDEO_SESSIONS_READY.md`
- `COACH_PRO_PLUS_VIDEO_SESSIONS_QUICK_REF.md`
- `COACH_REPORT_V2_README.md`
- `PDF_EXPORT_AND_MODE_ROUTING_FIXES.md`
- `RESULTS_PERSISTENCE_FIX.md`
- `RESULTS_PERSISTENCE_DEPLOYMENT.md`
- `S3_PRESIGNED_UPLOAD_IMPLEMENTATION.md`
- `S3_UPLOAD_FIX_DIFFS.md`
- `S3_UPLOAD_LIFECYCLE_FIX.md`
- `GPU_PIPELINE_QUICK_REF.md`
- `docs/ANALYSIS_MODE_ENFORCEMENT.md`
- `ANALYSIS_MODE_RESOLUTION_COMPLETE.md`
- `ANALYSIS_MODE_BALL_TRACKING_IMPLEMENTATION.md`
- `backend/workers/analysis_worker.py`
- `backend/scripts/run_video_analysis_worker.py`
- `backend/services/coach_plus_analysis.py`
- `backend/services/pose_service.py`
- `backend/services/sqs_service.py`
- `backend/mediapipe_init.py`
- `frontend/src/services/coachPlusVideoService.ts`
- `frontend/src/stores/coachPlusVideoStore.ts`
- video analysis migrations under `backend/alembic/versions/`

## Video Analysis Rule

Do not rebuild this system.

Phase 3 must preserve the existing model/pipeline behavior and only harden, test, extend, or safely improve it.

---

# 3A. Analyst System Roadmap — Existing Blueprint Assets

The repository contains two strategic analyst-system documents that must be treated as governed roadmap inputs, not immediate implementation instructions:

- `docs/CRICKSY_ANALYST_SYSTEM_BLUEPRINT_V1.md`
- `docs/ANALYST_PRODUCTION_WORKFLOW_V1.md`

## Analyst System Rule

Do not build the analyst system directly from these documents without a pre-phase audit and spec lock.

These documents define a major future product stream for:

- analyst workspace
- podcast preparation
- tactical analysis
- cricket intelligence dashboards
- visualizations
- media production workflows
- scouting workflows
- coach-facing interpretation
- future Sports Intelligence Institute workflows

Because this stream can touch match data, analytics, exports, AI summaries, dashboards, permissions, and media features, it must be handled as a governed phase.

## Required Future Phase

Before implementation, create:

`Phase 4 — Analyst System Blueprint Audit + Spec Lock`

Phase 4 must convert the two analyst documents into:

- MVP scope
- non-MVP scope
- backend data requirements
- frontend dashboard requirements
- API gaps
- visualization priorities
- AI guardrails
- role/permission matrix
- export requirements
- podcast workflow boundaries
- tests and gates
- protected files
- smallest safe implementation slice

## Analyst System Gates

No analyst-system code implementation may begin until Phase 4 is complete.

Phase 4 must prove:

- existing match/scoring truth remains untouched
- analyst dashboards consume existing match data safely
- generated insights cite match data or clearly label uncertainty
- AI cannot invent unsupported claims
- podcast/media exports require review before publishing
- analyst workspaces do not expose organization/private team data across boundaries
- historical match ingestion dependencies are clearly identified
- fake/mock data usage is either removed, blocked, or explicitly dev-only

## Analyst System Source Documents

All future analyst-system issues must reference both:

- `docs/CRICKSY_ANALYST_SYSTEM_BLUEPRINT_V1.md`
- `docs/ANALYST_PRODUCTION_WORKFLOW_V1.md`

---

# 4. Phase Structure

Every phase follows this structure:

```text
Pre-Phase Audit
    ↓
Spec Lock
    ↓
Implementation Plan
    ↓
Copilot/Agent Prompt
    ↓
Targeted Implementation
    ↓
Local Validation
    ↓
GitHub CI Validation
    ↓
Manual QA
    ↓
Merge Approval
    ↓
Deployment Approval
```

---

# Phase 0 — Repo Baseline + CI/CD Lock

## Purpose

Lock the current production-safe development process before feature expansion.

## Pre-Phase Audit

Audit:

- `.github/workflows/ci.yml`
- `.github/workflows/lint.yml`
- `.github/workflows/deploy-backend.yml`
- `.github/workflows/deploy-frontend.yml`
- `.github/workflows/release.yml`
- `.github/workflows/copilot-agent-run.yml`
- `backend/pytest.ini`
- `backend/pyproject.toml`
- `frontend/package.json`
- `docker-compose.yml`
- `docker-compose.dev.yml`
- `docker-compose.ci.yml`
- `docker-compose.test.yml`
- `infra/terraform/`

## Spec Lock

Lock:

- required branch naming
- required PR checks
- required backend commands
- required frontend commands
- required security commands
- migration rules
- deployment rules
- rollback expectations

## Gates

- CI workflow documented
- local dev commands documented
- production-sensitive paths documented
- protected files documented
- checklist committed under `docs/`

## Tests

Docs-only phase. CI may be skipped by path-ignore, but next code phase must validate full CI.

## Completion Criteria

A repo-grounded execution checklist exists and becomes required context for Copilot/agents.

---

# Phase 1 — Existing App Stabilization + Regression Protection

## Purpose

Protect existing app behavior before adding new product systems.

This phase is not a rebuild.

## Primary Areas

- `backend/main.py`
- scoring/result endpoints
- `backend/tests/test_results_endpoint.py`
- `backend/tests/test_health.py`
- `backend/tests/test_dls_calculations.py`
- `backend/tests/integration/`
- frontend pages/components that depend on scoring/viewer state

## Pre-Phase Audit

Audit:

- current health endpoint
- result endpoint behavior
- scoring event behavior
- DLS calculation behavior
- viewer sync behavior
- frontend fake-data guard
- role/tier visibility
- known production issues in docs such as `PRODUCTION_ISSUES_ANALYSIS.md`

## Spec Lock

Lock:

- existing scoring behavior that must not change
- delivery payload contract
- result endpoint contract
- health endpoint contract
- viewer state contract
- files allowed to change
- files protected from change

## Gates

- No scoring regression
- No DLS regression
- No fake data introduction
- No broken frontend build
- No backend type/lint/security regression
- All existing CI jobs pass

## Required Tests

```bash
pre-commit run --all-files
ruff check .
ruff format --check .
cd backend && mypy --config-file pyproject.toml --explicit-package-bases .
cd backend && pytest -q tests/test_health.py tests/test_results_endpoint.py
cd backend && pytest tests/integration/ -v --tb=short
cd backend && pytest tests/test_dls_calculations.py -v --tb=short
cd frontend && npm ci
cd frontend && npm run guard:fake-data
cd frontend && npm run type-check
cd frontend && npm run build-only
```

## Completion Criteria

Existing Cricksy behavior is safer and better covered without changing product identity.

---

# Phase 2 — Coach + Player Development Enhancements

## Purpose

Add player development and mental analysis features around the existing Coach Pro/Coach Pro Plus direction.

This phase should not disrupt video analysis, scoring, or core analytics.

## Primary Areas

Likely affected after audit:

- backend player/coach models
- backend routes connected to coach/player profiles
- frontend coach dashboard components
- frontend player profile components
- PDF/report generation code if already present
- permissions/tier logic

## Features

- Coach-player development profile
- Mental analysis questionnaire
- Mental category scoring
- Strength-based recommendations
- Development-area recommendations
- Separate mental analysis report/PDF
- Mental analysis shown alongside video analysis, but not merged into the same PDF yet

## Pre-Phase Audit

Audit:

- existing coach-player relationships
- existing player profile data
- existing coach dashboard
- existing PDF/report code
- existing auth/RBAC/tier checks
- existing Coach Pro Plus video page/store/service dependencies

## Spec Lock

Lock:

- questionnaire categories
- scoring formula
- recommendation mapping
- safe language rules
- coach visibility rules
- player visibility rules
- report structure
- DB schema/migration plan

## Gates

- Coach-led workflow preserved
- Mental analysis does not break video analysis
- Mental PDF/report remains separate
- No negative youth/player labels
- Recommendations explain their source
- CI passes

## Required Tests

- questionnaire schema tests
- response submission tests
- score calculation tests
- recommendation mapping tests
- coach permission tests
- player permission tests
- frontend form validation tests
- report/PDF generation tests, if touched
- full existing CI gates

## Completion Criteria

Coach accounts can manage mental/player development information safely without disrupting existing scoring or video systems.

---

# Phase 3 — Coach Pro Plus Video Analysis Hardening + Extension

## Phase 3A — Audit + Spec Lock (COMPLETE)

Phase 3A is the pre-phase audit and spec lock for Coach Pro Plus Video Analysis Hardening.

Audit document: `docs/PHASE_3A_COACH_VIDEO_HARDENING_AUDIT_AND_SPEC_LOCK.md`

Phase 3A deliverables:

- Architecture map (frontend, backend, worker, S3, MediaPipe)
- Backend route/API map
- Worker/job lifecycle map
- S3/upload/storage flow map
- MediaPipe/model-loading flow map
- Analysis mode routing map
- PDF/report export flow map
- Result/session persistence flow map
- Testing gaps identified
- Private-beta/access-control behavior documented
- Failure/timeout/retry behavior documented
- Known risks catalogued
- Protected files list
- Allowed hardening areas
- Forbidden changes
- Recommended smallest safe Phase 3B implementation slice
- Required tests/gates for Phase 3B
- Rollback plan

## Purpose

Protect and improve the existing Coach Pro Plus Video Analysis system.

This phase is not a model rebuild.

The current model behavior is liked and must be preserved unless the user explicitly approves a model change.

## Existing System Files

High-risk/protected files:

- `backend/workers/analysis_worker.py`
- `backend/scripts/run_video_analysis_worker.py`
- `backend/services/coach_plus_analysis.py`
- `backend/services/pose_service.py`
- `backend/services/sqs_service.py`
- `backend/mediapipe_init.py`
- `frontend/src/services/coachPlusVideoService.ts`
- `frontend/src/stores/coachPlusVideoStore.ts`
- video analysis migrations under `backend/alembic/versions/`

Supporting docs:

- `COMPLETE_VIDEO_ANALYSIS_FLOW.md`
- `README_COACH_PRO_PLUS_VIDEO_MVP.md`
- `TESTING_GUIDE_COACH_VIDEO.md`
- `COACH_REPORT_V2_README.md`
- `PDF_EXPORT_AND_MODE_ROUTING_FIXES.md`
- `RESULTS_PERSISTENCE_FIX.md`
- `RESULTS_PERSISTENCE_DEPLOYMENT.md`
- `GPU_PIPELINE_QUICK_REF.md`
- `docs/ANALYSIS_MODE_ENFORCEMENT.md`

## Allowed Improvements

- session/result persistence hardening
- previous session access for authorized coaches/admins
- PDF export reliability
- worker timeout handling
- retry/failure visibility
- private beta access control
- role-specific report safety for batting, bowling, and wicketkeeping
- mental analysis alongside video analysis
- better test coverage around existing behavior

## Forbidden Without Approval

Do not:

- replace the model
- rewrite the full pipeline
- remove existing analysis stages
- change model outputs without comparison tests
- expose video analysis publicly
- delete existing migrations
- merge video and mental PDFs unless approved later

## Pre-Phase Audit

Audit:

- job lifecycle from README/docs
- local worker commands
- S3 upload flow
- MediaPipe model loading
- analysis mode enforcement
- PDF export flow
- result persistence flow
- frontend store/service behavior
- backend API route protections
- existing migration state
- current tests for video analysis

## Spec Lock

Lock:

- model behavior preservation rules
- allowed file edits
- protected file sections
- session schema changes, if any
- report schema changes, if any
- worker retry rules
- timeout behavior
- role-specific output rules
- private beta access rules
- required regression tests

## Gates

- Current model behavior preserved
- Existing analysis modes preserved
- Unauthorized users blocked by backend, not just frontend
- Coach/admin authorized session access works
- PDF export works from stored result
- Worker failures produce clear status
- Batting/bowling/wicketkeeping instructions do not cross-contaminate
- CI passes

## Required Tests

- existing video analysis tests from `TESTING_GUIDE_COACH_VIDEO.md`
- worker lifecycle tests
- result persistence tests
- session retrieval tests
- access control tests
- PDF export tests
- analysis mode routing tests
- batting report tests
- bowling report tests
- wicketkeeper report tests
- frontend service/store tests if available
- full existing CI gates

## Completion Criteria

Coach Pro Plus Video Analysis remains working, is more reliable, private, reportable, and safe for coach-led use.

---

# Phase 4 — Analyst System Blueprint Audit + Spec Lock

## Phase 4A — Architecture Audit + Spec Lock (COMPLETE)

Phase 4A is the pre-phase audit and spec lock for the Analyst System.

Audit document: `docs/PHASE_4A_ANALYST_SYSTEM_ARCHITECTURE_AUDIT_AND_SPEC_LOCK.md`

Phase 4A deliverables:

- Analyst system vision summary and source document synthesis
- Existing match/scoring data access audit
- Existing completed/live match data availability audit
- Existing delivery-level data access audit
- Existing analytics/dashboard/frontend audit
- Existing chart/visualization component audit
- Existing export/report capability audit
- Existing AI/LLM capability audit
- Existing RBAC/tier capability audit
- Fake/mock data risk catalogue (6 active risks identified)
- Analyst MVP scope defined
- Non-MVP/future scope defined
- First analyst persona and workflow target locked (Podcast Analyst)
- Recommended first dashboard/workspace slice (Match Intelligence Dashboard)
- Backend API/data requirements specified
- Frontend UX requirements specified
- Visualization requirements specified
- Export requirements specified
- AI guardrails and grounding rules locked
- Permission/isolation requirements locked
- No-fake-data rules locked
- Testing/gate requirements locked
- Protected files/areas confirmed
- Recommended smallest safe Phase 4B implementation issue
- Rollback/containment plan for analyst implementation

## Purpose

Convert the strategic analyst-system documents into a safe, phased, buildable product plan before any analyst-system implementation begins.

This phase governs:

- `docs/CRICKSY_ANALYST_SYSTEM_BLUEPRINT_V1.md`
- `docs/ANALYST_PRODUCTION_WORKFLOW_V1.md`

This phase is mandatory before building analyst dashboards, analyst workspaces, podcast prep tooling, AI analyst assistants, visualizations, analyst exports, scouting workflows, or Sports Intelligence Institute workflows.

## Primary Areas

Likely affected after audit:

- backend match/query APIs
- backend analytics services
- backend export/report services
- frontend analyst dashboard/workspace components
- frontend chart/visualization components
- permissions and organization data boundaries
- AI insight/summarization services
- media/export tooling
- historical match ingestion dependencies

## Pre-Phase Audit

Audit:

- both analyst source documents
- existing match data access routes
- existing completed/live match data availability
- existing scorecard/delivery-level access
- existing analytics services
- existing chart/export components
- existing fake/mock data areas
- existing role/tier system for analyst/coach/media/scout access
- existing PDF/PNG/CSV/Markdown export code
- dependencies on historical match ingestion phases
- dependencies on AI analytics phases

## Spec Lock

Lock:

- Analyst MVP scope
- non-MVP/future scope
- first analyst user persona
- first workflow target, likely podcast prep
- first dashboard requirements
- first visualization requirements
- backend API/data contracts
- frontend workspace UX boundaries
- AI assistance boundaries
- export formats for MVP
- role and permission rules
- data citation/explainability requirements
- no-fake-data rules
- approval workflow rules
- tests and gates
- smallest safe implementation slice

## Gates

- Do not build analyst-system code before Phase 4 is complete.
- Existing scoring/match truth must remain untouched.
- Analyst dashboards must consume existing data safely.
- No cross-organization data leakage.
- No unsupported AI claims.
- Generated insights must cite source data or be marked tentative.
- Media/podcast outputs must remain reviewable before publishing.
- Fake/mock data must not be introduced into production paths.
- Historical ingestion dependencies must be documented before analyst features depend on them.
- CI passes for any implementation PR after Phase 4.

## Required Tests

Phase 4 itself is docs/spec only.

Future analyst implementation tests must include:

- backend API contract tests
- permission/isolation tests
- dashboard empty/loading/error state tests
- chart data validation tests
- export generation tests
- AI insight grounding tests
- no-fake-data guard checks
- full existing CI gates when implementation begins

## Completion Criteria

Phase 4 is complete when the analyst system has a repo-grounded MVP spec, implementation sequence, data/API map, visualization list, permission model, AI guardrails, export plan, and first safe implementation issue.

---

# Phase 5 — Historical Match Ingestion: Structured JSON First

## Purpose

Allow teams/orgs to upload old matches through a safe structured path first.

Start with structured JSON before OCR/AI parsing.

Phase 5A pre-implementation governance/audit/spec-lock doc:

- `docs/PHASE_5A_HISTORICAL_JSON_IMPORT_AUDIT_AND_SPEC_LOCK.md`

## Primary Areas

Likely affected after audit:

- backend match/import routes
- backend match/delivery schemas
- backend validation services
- frontend upload/review UI
- tests under `backend/tests/`
- migrations if new ingest job table is needed

## Pre-Phase Audit

Audit:

- existing match schema
- existing result endpoint
- existing player/team models
- existing import/export utilities
- existing file upload patterns
- existing validation patterns

## Spec Lock

Lock:

- JSON source contract
- ingest job schema
- validation errors format
- preview-before-save workflow
- player/team matching rules
- duplicate detection rules
- rollback behavior

## Gates

- JSON imports normalize to existing match structure
- No imported match becomes official without validation
- Bad rows return clear errors
- Duplicate detection exists
- Existing scoring unaffected
- CI passes

## Required Tests

- valid JSON import
- invalid JSON import
- missing required fields
- innings total mismatch
- extras mismatch
- duplicate detection
- player matching
- preview save confirmation
- full existing CI gates

## Completion Criteria

Structured historical match import works safely and does not corrupt live scoring data.

---

## Phase 5K — Historical Data Backfill + Analyst UI Theme Fix

### Purpose

- Execute a governed backfill/reprocess pass for legacy historical imports where safe after Phase 5J metadata fixes.
- Repair historical metadata display regressions for already-imported matches.
- Fix Analyst Workspace dark-theme contrast issues in Key Players and Podcast Prep cards.
- Enforce metadata accuracy before any model-training eligibility expansion.

### Pre-Phase Audit Requirements

- Audit legacy imported matches for metadata gaps and backfill safety (no live-truth mutation risk).
- Audit historical metadata rendering paths to confirm Phase 5J interpretation remains correct for new imports.
- Audit Analyst Workspace dark-theme CSS/component behavior for Key Players and Podcast Prep cards.
- Audit rollback readiness for historical import batches that require reprocessing.

### Strict Scope

- Historical import backfill/reprocess logic for legacy imported matches only.
- Historical metadata display fixes for previously imported historical matches.
- Analyst Workspace dark-theme visual fixes limited to Key Players and Podcast Prep cards.
- Required tests, governance checks, and rollback documentation for this scope only.

### Protected Files/Systems

- Live scoring truth paths and deterministic scoring logic.
- DLS calculations and rules.
- Live bus/socket semantics.
- Video-analysis and mental-analysis systems.
- Unrelated workflows, dependencies, migrations, and non-historical runtime paths.

### Gates

- Historical imports must not mutate live scoring truth.
- Imported data remains not training-ready until validated and registered.
- Backfill/reprocess must be auditable, idempotent where possible, and rollback-capable.
- Metadata fixes must preserve venue/competition/season/match context for future analysis.
- No runtime behavior outside strict Phase 5K scope is changed.

### Tests

- Legacy historical backfill safety tests (eligible vs blocked cases).
- Metadata regression tests for historical match list/detail/case-study outputs.
- Analyst Workspace dark-theme visual/contract checks for Key Players and Podcast Prep cards.
- Historical rollback/regression tests proving only historical-import artifacts are affected.

### Rollout / Rollback Considerations

- Roll out behind explicit operator confirmation for reprocess operations.
- Keep per-batch audit logs for every legacy record touched.
- Provide rollback path to prior import-batch state if regressions appear.
- Stop rollout if metadata parity or UI contrast checks fail.

### What Must Not Be Done

- Do not alter live scoring, DLS, live bus, video-analysis, or mental-analysis runtime behavior.
- Do not broaden scope into new registry schema design (reserved for Phase 5M).
- Do not mark legacy imports as training-ready without validation + registry linkage.

### Completion Criteria

- Legacy backfill/reprocess scope is completed safely with audit trail and rollback coverage.
- Historical metadata display is correct for both newly imported and legacy imported matches.
- Analyst Workspace dark-theme issues are resolved for Key Players and Podcast Prep cards.
- Governance gates and tests pass with strict docs-defined boundaries respected.

---

## Phase 5L — Bulk ZIP Historical Upload

### Purpose

- Support uploading many historical JSON files in a single ZIP through a governed bulk-import flow.
- Preserve dry-run-first behavior with duplicate protection and explicit apply confirmation.
- Improve operator visibility with per-file status reporting.

### Pre-Phase Audit Requirements

- Audit current single-file historical dry-run/apply flow and batch lifecycle constraints.
- Audit ZIP parsing/security controls (file count, size, compression-ratio safety).
- Audit duplicate-detection behavior for both in-archive duplicates and existing import-batch collisions.
- Audit rollback behavior for partial/failed bulk operations.

### Strict Scope

- ZIP intake and controlled extraction for historical JSON files only.
- Dry-run execution per file before any apply stage.
- Duplicate detection inside ZIP and against existing import batches.
- Per-file success/error status and explicit confirmation gate before apply.

### Protected Files/Systems

- Live scoring truth and gameplay runtime paths.
- Existing non-historical upload systems (including unrelated media workflows).
- DLS/live bus and unrelated Analyst features.
- Unrelated migrations/workflows/dependencies.

### Gates

- Bulk import cannot bypass dry-run, duplicate detection, explicit confirmation, or rollback.
- ZIP safety checks must enforce file-size/file-count/compression-ratio limits.
- Duplicate handling must be explicit (blocked, flagged, or operator-reviewed) and auditable.
- Apply stage is blocked when critical file-level validation failures remain.

### Tests

- ZIP intake safety tests (oversized ZIP, zip-bomb patterns, invalid file types, file-count limits).
- Per-file dry-run result tests with mixed valid/invalid JSON inputs.
- Duplicate detection tests (inside ZIP and against prior batches).
- Confirmation-gate tests proving apply cannot execute without explicit confirmation.
- Rollback tests for failed/partial bulk apply scenarios.

### Rollout / Rollback Considerations

- Roll out with conservative ZIP limits first, then widen only after stable telemetry.
- Store per-file lifecycle state for deterministic recovery.
- Support rollback that only touches records created by the specific bulk batch.
- Emit operator-facing post-run reports with file-level outcomes.

### What Must Not Be Done

- Do not auto-apply bulk uploads after dry-run without explicit user confirmation.
- Do not silently ignore duplicates or overwrite existing imported truth.
- Do not allow ZIP upload path to mutate live scoring state.

### Completion Criteria

- Users can upload a ZIP of historical JSON files and receive per-file dry-run outcomes.
- Duplicate files are detected both within the ZIP and against existing batches.
- Apply requires explicit confirmation and supports safe rollback.
- ZIP safety limits and governance tests pass.

### Phase 5L.1 Validation Evidence (Cost-Controlled Large ZIP Intake)

- Final configured limits:
  - `PHASE_5L_MAX_FILES = 2000`
  - `PHASE_5L_MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024`
  - `PHASE_5L_MAX_TOTAL_UNCOMPRESSED_BYTES = 100 * 1024 * 1024`
  - `PHASE_5L_MAX_TOTAL_COMPRESSED_BYTES = 100 * 1024 * 1024`
- Cost-control path:
  - ZIPs above `PHASE_5L_MAX_FULL_APPLY_FILES = 100` are accepted in metadata-only mode.
  - Metadata-only records are persisted with `status="pending_full_import"` and full import is deferred.
  - Training gate is enforced: `training_eligible=false`, `blocking_reason="metadata_only_pending_full_import"`.
- Storage behavior:
  - Uses existing S3 configuration (`S3_COACH_VIDEOS_BUCKET`) when present.
  - Uses local/dev fallback only behind the same storage interface when S3 bucket is unset.
  - No new storage system or AWS service introduced.
- Metadata-only storage reference pattern:
  - `historical-imports/{org_or_user_scope}/{batch_id}/raw/{filename}_{hash}.json`
  - `historical-imports/{org_or_user_scope}/{batch_id}/manifest.json`
  - `historical-imports/{org_or_user_scope}/{batch_id}/validation_report.json`

---

## Phase 5M — Cricket Data Registry Foundation

### Purpose

- Establish registry foundations for competition, season, venue, team, player, match provenance, and import-batch linkage.
- Prepare reliable metadata infrastructure for venue par score, competition folders, player stats, and model-training datasets.
- Enforce that imported data is validated/registered before becoming training-eligible.

### Pre-Phase Audit Requirements

- Audit existing metadata preserved through Phase 5J/5K historical import paths.
- Audit entity-resolution rules for team/player deduplication and canonicalization.
- Audit provenance requirements linking every imported match to source + batch lineage.
- Audit migration plan and backward compatibility before schema introduction.

### Strict Scope

- Registry foundation design and implementation for competition, season, venue, team, and player entities.
- Match provenance model linking imports to source metadata and import batches.
- Validation/registration gates for training-readiness decisions.
- Migration governance and Postgres validation for all schema changes in this phase.

### Protected Files/Systems

- Deterministic live scoring and DLS logic.
- Live bus/event semantics.
- Historical import runtime behavior not required for registry linkage.
- Unrelated AI/media systems and unrelated workflow/dependency surfaces.

### Gates

- Metadata accuracy is mandatory before model training usage.
- Imported data is not training-ready until validated and registered.
- Player/team registries must not blindly create duplicate entities.
- Venue and competition metadata must be preserved for future analysis workflows.
- Real Postgres Alembic validation gate is mandatory for registry migrations.

### Tests

- Registry entity creation/linkage tests for competition/season/venue/team/player.
- Duplicate-prevention tests for player/team canonical resolution.
- Match provenance tests verifying source metadata + import batch lineage integrity.
- Training-readiness gate tests proving unregistered imports remain ineligible.
- Alembic migration tests validated against real Postgres (upgrade/downgrade where supported).

### Rollout / Rollback Considerations

- Use staged rollout with migration checkpoints and data reconciliation reports.
- Keep reversible migration strategy and batch-safe rollback guidance.
- Block downstream training dataset generation if registry integrity checks fail.
- Provide reconciliation scripts/processes for unresolved or ambiguous registry mappings.

### What Must Not Be Done

- Do not permit unvalidated or unregistered imported rows into model-training datasets.
- Do not auto-create duplicate player/team entities from weak matching.
- Do not lose venue/competition/season provenance during canonicalization.
- Do not mutate live scoring truth while building registry foundations.

### Completion Criteria

- Competition, season, venue, team, and player registry foundations are defined and governed.
- Match provenance and import-batch linkage are enforced for historical imports.
- Training-readiness depends on successful validation + registry linkage.
- Postgres Alembic migration gate not required (no new tables added — provenance is stored in existing `phases.historical_import` JSON and `HistoricalImportBatch` model).

### Phase 5M Implementation Notes (completed)

Phase 5M is implemented as the smallest safe slice that is visible in the frontend:

**Backend (no new migration required):**
- `MatchRegistryResponse` Pydantic schema added to `backend/api/schemas/analyst_matches.py`.
- `GET /analytics/matches/{match_id}/registry` endpoint added to `backend/routes/analytics_case_study.py`.
  - Looks up `HistoricalImportBatch` by `batch_id` stored in `game.phases.historical_import`.
  - Returns competition, season, venue, teams, player_count, innings_count, has_deliveries,
    import batch provenance (batch ID, source filename, source format, imported_at),
    validation_status (from `batch.status`), registration_status, training_eligible, and blocking_reason.
  - For non-historical matches: returns `validation_status="not_applicable"`, `training_eligible=False`.
  - Training eligibility requires: `is_finalized=True` + `status="valid"` + `error_count=0`.
- 4 new backend tests added to `backend/tests/test_analyst_pro_features.py`.

**Frontend:**
- `MatchRegistryResponse` TypeScript interface and `getMatchRegistry()` function added to `frontend/src/services/api.ts`.
- "Registry & Provenance" section added to `AnalystWorkspaceView.vue` match detail panel.
  - Shows competition, season, venue, teams, player registry status, innings/deliveries counts,
    import batch ID, source file/format, imported_at, validation status, registration status,
    training eligibility, and blocking reason.
  - Missing values shown as "Unknown" / "Not registered yet" / "Not available".
  - No fake/demo data introduced.
- 7 new frontend tests added to `frontend/tests/unit/AnalystWorkspaceView.spec.ts`.

**Validation evidence:**
- `pytest backend/tests/test_analyst_pro_features.py` → 18 passed (including 4 new)
- `pytest backend/tests/test_health.py backend/tests/test_results_endpoint.py` → 9 passed
- `pytest backend/tests/integration/` → 38 passed
- `pytest backend/tests/test_dls_calculations.py` → 21 passed
- `npm run test:unit -- tests/unit/AnalystWorkspaceView.spec.ts` → 48 passed (including 7 new)
- `npm run type-check` → passes
- `npm run build-only` → passes
- `npm run guard:fake-data` → 0 errors

---

## Phase 5N — Historical Stats Aggregation Layer

### Purpose

- Calculate and maintain analytics-ready historical aggregates from validated, registered, imported match data.
- Deliver governed aggregation outputs for player batting stats, player bowling stats, team stats, venue par scores, competition stats, and phase stats (powerplay, middle overs, death overs).
- Preserve reproducibility so any aggregate can be recomputed from governed source records.

### Pre-Phase Audit Requirements

- Audit registry completeness from Phase 5M (competition/season/venue/team/player/provenance linkage) before aggregation starts.
- Audit historical import validation status to confirm only validated + registered matches are aggregation-eligible.
- Audit existing aggregate/stat consumers to confirm no live scoring mutation path is introduced.
- Audit schema/migration impact and Postgres readiness if new aggregate tables/materialized views are required.

### Strict Scope

- Aggregation logic and governed storage for historical batting/bowling/team/venue/competition/phase statistics only.
- Controlled recompute/backfill flows for aggregation outputs derived from imported historical matches.
- Validation and governance gates for stat integrity, provenance linkage, and recomputation behavior.
- Documentation/test coverage for this aggregation layer only.

### Protected Files/Systems

- Live scoring truth, deterministic scoring logic, and DLS paths.
- Live bus/socket semantics and real-time scoring flows.
- Video-analysis and mental-analysis systems.
- Unrelated historical import runtime ingestion paths outside aggregation linkage.
- Unrelated workflows, dependencies, and non-aggregation product features.

### Data Governance Rules

- Imported data is not analytics-ready or model-training-ready until validated, registered, and aggregation-eligible (validation passed, registry linkage complete, provenance intact).
- Metadata accuracy and registry integrity take priority over aggregate coverage.
- No fake stats or fabricated aggregate rows; every value must map to governed source/provenance.
- Aggregations must be deterministic, reproducible, and recomputable from source inputs.
- Live scoring truth must never be mutated by aggregation jobs.
- Any registry/aggregation schema migration must pass real Postgres Alembic validation before rollout.

### Gates

- Aggregation runs are blocked for unvalidated, unregistered, or provenance-broken matches.
- Player/team/venue/competition/phase outputs must include audit metadata for source lineage and compute version.
- Segment stats (powerplay/middle/death) must correctly distinguish legal deliveries from extras (including wides/no-balls) under governed cricket rules.
- Recompute operations must support idempotent rerun behavior and mismatch detection/reporting.

### Tests

- Aggregation correctness tests for player batting, player bowling, team, venue par score, competition, and phase stats.
- Edge-case tests for extras/wickets/abandoned or incomplete imported data handling under governed rules.
- Recompute/idempotency tests proving reproducible outputs from the same source dataset.
- Postgres Alembic migration validation tests (required upgrade and required downgrade) when new aggregation tables/views are introduced.
- Regression tests proving aggregation paths do not mutate live scoring truth.

### Rollout / Rollback Considerations

- Roll out aggregation in staged batches with per-run audit logs and reconciliation summaries.
- Maintain rollback/recompute playbooks to invalidate and rebuild affected aggregate slices safely.
- Block downstream analytics/model dataset exports when aggregate integrity checks fail.
- Keep deterministic versioned aggregation configs so historical outputs can be reproduced after rollback.

### What Must Not Be Done

- Do not aggregate from unvalidated or unregistered imported matches.
- Do not fabricate stats to fill missing records or unknown metadata.
- Do not alter live scoring truth, DLS behavior, or unrelated runtime flows.
- Do not bypass real Postgres Alembic validation for aggregation-related schema changes.

### Completion Criteria

- Governed historical aggregation exists for player batting, player bowling, team, venue par, competition, and phase (powerplay/middle/death) stats.
- Aggregations are reproducible, recomputable, auditable, and blocked on registry/provenance failures.
- Required tests/gates pass, including Postgres migration validation where schema changes are present.
- Live scoring truth remains unchanged and protected.

---

## Phase 5O — Analyst Workspace Data Library

### Purpose

- Provide analyst-facing governed data-library browsing over imported historical records.
- Add consistent folders/filters for competition, season, venue, team, player, match type, and imported batch.
- Ensure analyst workflows expose real governed records with clear empty-state handling when no data is available.

### Pre-Phase Audit Requirements

- Audit Analyst Workspace data-entry points and navigation components that will host folders/filters.
- Audit backend query contracts for historical metadata dimensions (competition/season/venue/team/player/match type/batch).
- Audit permission/visibility boundaries so library views only expose authorized governed data.
- Audit empty-state and error-state UX rules before implementation lock.

### Strict Scope

- Analyst Workspace data-library structure and filter surfaces for governed imported historical data browsing only.
- Backend/frontend contract alignment for folder/filter retrieval and filtering behavior.
- Empty-state, loading-state, and no-results handling tied to governed data availability.
- Tests and governance checks for this browsing layer only.

### Protected Files/Systems

- Live scoring truth and match-scoring runtime paths.
- DLS/live bus semantics and non-analyst gameplay APIs.
- Historical import ingestion logic unrelated to library browsing contracts.
- Model training pipelines and dataset export runtimes (reserved for later governed phases).
- Unrelated workflows, dependencies, and non-Analyst Workspace features.

### Data Governance Rules

- Metadata accuracy and registry integrity must be validated before records appear in library folders/filters.
- No fake folders, fake counts, placeholder data, or fabricated rows in analyst views.
- Imported data browsing must preserve provenance context (including imported batch lineage).
- Live scoring truth must not be mutated by library indexing/filtering logic.

### Gates

- Folder/filter outputs must be sourced from validated + registered historical metadata only.
- Backend/frontend contracts for each filter dimension must be versioned and test-verified.
- UI must show explicit governed empty states when filtered datasets have no eligible records.
- Filter combinations must remain deterministic and reproducible for the same governed snapshot.

### Tests

- Backend contract tests for competition, season, venue, team, player, match type, and imported batch filters.
- Frontend contract/integration tests validating folder/filter rendering and filter-application behavior.
- UI tests for empty/loading/error/no-results states with no fabricated fallback data.
- Permission and provenance visibility tests ensuring authorized access and batch-trace display.
- Regression tests proving no side effects on live scoring/runtime gameplay systems.

### Rollout / Rollback Considerations

- Roll out behind feature flags or phased enablement for analyst cohorts.
- Keep reversible configuration/state changes for folder/filter definitions and ordering.
- Provide rollback path to previous Analyst Workspace navigation without data mutation.
- Require reconciliation checks if filter counts diverge from governed metadata snapshot.

### What Must Not Be Done

- Do not display synthetic/fake folders, fake totals, or fabricated match rows.
- Do not bypass backend/frontend contract validation for new library filter dimensions.
- Do not mutate live scoring truth or unrelated analyst/runtime systems.
- Do not expand scope into model training/retraining execution.

### Completion Criteria

- Analyst Workspace exposes governed folders/filters for competition, season, venue, team, player, match type, and imported batch.
- Backend/frontend contract tests and UI empty-state rules pass with no fake data behavior.
- Library outputs are provenance-aware, deterministic, and bounded by validated registry metadata.
- Protected systems remain unchanged.

---

## Phase 5P — Model Training Dataset Builder

### Purpose

- Build governed dataset export pipelines (not model training) for downstream model-development phases.
- Produce clean export targets for win prediction, par score prediction, player form, venue adjustment, phase momentum, and matchup prediction use cases.
- Enforce dataset governance so only validated, registered, and aggregated historical data becomes training-dataset eligible.

### Pre-Phase Audit Requirements

- Audit readiness of Phase 5M registry and Phase 5N aggregation outputs for each export target.
- Audit feature availability and label definitions for all planned dataset families before schema lock.
- Audit security/privacy constraints and data-classification handling for exported datasets.
- Audit versioning/provenance strategy for reproducible export artifacts and lineage tracking.

### Strict Scope

- Dataset extraction/transformation/export governance for approved dataset families only.
- Eligibility checks, provenance tracking, split governance, and export versioning controls.
- Validation tooling and tests for feature/label integrity in export outputs.
- Documentation and gates for export reliability only.

### Protected Files/Systems

- Live scoring truth and deterministic gameplay runtime behavior.
- DLS/live bus and unrelated analyst/runtime systems.
- Direct model-training/retraining execution pipelines (out of scope for this phase; deferred to a later governed model-training phase after separate approval).
- Unrelated workflows, dependencies, and non-dataset product areas.

### Data Governance Rules

- Imported data is not training-ready until validated, registered, and aggregated under governance.
- Metadata and registry integrity are mandatory prerequisites before any dataset export.
- No fake model labels, no fabricated feature rows, and no synthetic training samples presented as truth.
- Dataset lineage must retain source match provenance, aggregation version, and export configuration metadata.
- Privacy/security controls must prevent unauthorized exposure of sensitive or restricted fields.
- Live scoring truth must never be mutated by dataset export logic.

### Gates

- Training eligibility gate blocks exports when validation/registry/aggregation prerequisites fail.
- Feature extraction and label-generation rules must pass deterministic validation with documented assumptions.
- Train/validation/test split governance must enforce non-leaky partition policies and reproducible split seeds.
- Export versioning must generate immutable, traceable dataset versions with checksum/manifest metadata.
- Direct model retraining remains blocked in this phase and requires separate approval in a later governed model-training phase, after dataset-export reliability gates are complete.

### Tests

- Export correctness tests for each dataset family: win prediction, par score prediction, player form, venue adjustment, phase momentum, matchup prediction.
- Feature/label integrity tests detecting null/invalid/leaky mappings and fabricated-row attempts.
- Provenance/manifest tests ensuring lineage, version, and checksum records are complete and queryable.
- Privacy/security tests confirming restricted fields are excluded or protected per policy.
- Split-governance tests validating deterministic train/validation/test partition behavior without leakage.
- Regression tests proving exports do not mutate live scoring truth or unrelated runtime paths.

### Rollout / Rollback Considerations

- Roll out exports in controlled versions with compatibility notes and reproducibility manifests.
- Maintain rollback/rebuild procedure to deprecate invalid dataset versions and regenerate from governed sources.
- Suspend downstream consumption when provenance, validation, or privacy checks fail.
- Keep export history immutable for audit and reproducibility guarantees.

### What Must Not Be Done

- Do not export datasets from unvalidated/unregistered/unaggregated inputs.
- Do not fabricate labels/features or backfill missing values as synthetic truth without governance approval.
- Do not run direct model retraining in this phase; it is deferred to a later governed model-training phase after separate approval.
- Do not alter live scoring truth or unrelated runtime systems.

### Completion Criteria

- Governed exports exist for win prediction, par score prediction, player form, venue adjustment, phase momentum, and matchup prediction datasets.
- Eligibility, provenance, privacy/security, feature validation, split governance, and versioning gates are enforced and test-covered.
- Exports are reproducible, auditable, and blocked when upstream governance requirements fail.
- Phase scope remains dataset-builder only; model retraining remains deferred.

---

# Phase 6 — Cricksy Intelligence Operating System Governance

## Purpose

- Add a governed architecture stream for Cricksy as a sports intelligence operating system.
- Keep future intelligence work cost-controlled, testable, reviewable, and safely separated from deterministic cricket truth.
- Treat Phase 6A as documentation/audit/spec-lock only; no runtime intelligence implementation is allowed in this phase.

## Governed Future Architecture (Spec Only)

This is future governed architecture, not current implementation unless a later audit proves a component already exists and it is explicitly approved.

```text
User / Coach / Analyst
        ↓
Cricksy Supervisor
        ↓
Intent Router
        ↓
Skill Router
        ↓
Specialist Agents
        ↓
Validation Agents
        ↓
Governance Layer
        ↓
Review Queue
        ↓
Approved Intelligence Output
```

## Phase 6A — Intelligence OS Audit + Spec Lock

### Purpose

- Audit the current repo surfaces that will constrain or support future intelligence work.
- Lock governance, protected boundaries, validation gates, and future subphase sequencing before any agent/router/skill implementation begins.
- Publish the audit/spec-lock in `docs/PHASE_6A_CRICKSY_INTELLIGENCE_OS_AUDIT_AND_SPEC_LOCK.md`.

### Pre-Phase Audit Requirements

Audit and summarize:

- Existing Analyst Workspace files/components/routes.
- Existing historical import and registry work from Phase 5.
- Existing deterministic scoring/result/DLS systems.
- Existing analytics/match intelligence endpoints.
- Existing model/prediction code, if any.
- Existing video analysis / Coach Pro Plus architecture.
- Existing auth/RBAC/tier/organization boundary rules.
- Existing fake-data guard behavior.
- Existing report/export capability.
- Existing AI/LLM-related code, if any.
- Existing places where AI could accidentally calculate or mutate cricket truth.
- Existing CI/test gates relevant to future intelligence work.

### Strict Scope

- Update this Master Execution Checklist with the governed Phase 6 architecture stream.
- Add the dedicated Phase 6A audit/spec-lock document.
- Define future Phase 6B–6H subphases, rules, gates, and protected systems.
- Map current Phase 5 historical registry work as the data foundation for future intelligence.

### What Must Not Be Done

- Do not build a Supervisor implementation.
- Do not build Intent Router code.
- Do not build Skill Router code.
- Do not build agent code.
- Do not build LLM workflows.
- Do not call external AI providers.
- Do not add new runtime dependencies.
- Do not add migrations.
- Do not modify backend/frontend runtime behavior.

### Data Foundation Link

Current Phase 5 work is the governed data foundation for future intelligence:

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

Phase 5L.1 provides cost-controlled large ZIP intake and Phase 5M provides registry/provenance/training-eligibility foundations that future intelligence must consume rather than bypass.

### Deterministic vs AI Boundary

Deterministic systems own:

- scoring
- runs
- balls
- overs
- wickets
- innings state
- match result
- scorecards
- official player stats
- DLS
- validations
- filters
- metrics
- venue par calculations
- win probability model outputs where applicable

AI systems may only:

- explain
- summarize
- interpret
- recommend
- communicate
- generate reviewable reports
- answer questions grounded in approved data

Hard gate:

- No LLM may calculate, overwrite, or mutate official cricket truth.

### Phase 6 Governance Rules

- Do not load all available cricket data into AI context. Load only the minimum relevant match/player/team/phase/video/context required for the user’s question.
- AI-generated intelligence must expose confidence and limitations, including limited-sample caveats when appropriate.
- Low-confidence insights must never be presented as certain.
- Continuous intelligence should be mostly deterministic and cheap; expensive AI should only run on explicit triggers.
- No always-running LLM loops without explicit user approval, cost guardrails, and governance approval.
- Sensitive or high-impact outputs require validation and review before becoming official or coach-facing.
- High-impact outputs include youth player feedback, mental-analysis recommendations, coach reports, scouting reports, public/podcast content, model-derived recommendations, and performance criticism.

### Future Phase 6 Roadmap

#### Phase 6B — Deterministic vs AI Boundary Enforcement (COMPLETE)

Lock code and test boundaries that prevent AI from mutating cricket truth.

Spec-lock document: `docs/PHASE_6B_DETERMINISTIC_AI_BOUNDARY_ENFORCEMENT.md`

Phase 6B deliverables (boundary enforcement only — no agents/skills/routers built):

- `backend/domain/ai_boundary.py` — new boundary guard module with `AiOutputType` enum,
  `OFFICIAL_TRUTH_FIELDS` frozenset, `AiOutputMetadata` Pydantic model (embeds
  `is_official_truth=False` in every AI response), and `validate_no_official_truth_mutation`
  guard function that raises `ValueError` if AI code attempts to set official truth fields.
- AI response schemas updated with `ai_metadata` field: `AiCommentaryResponse`,
  `MatchAiCommentaryResponse`, `MatchAiSummaryResponse`, `PlayerAiInsights`.
- Non-authoritative Phase 6B boundary docstrings added to: `ai_commentary.py`,
  `match_ai_service.py`, `ai_player_insights.py`, `coach_ai_pipeline.py`, `agent_budget.py`.
- `backend/tests/test_phase_6b_ai_boundary.py` — 37 tests proving:
  - Guard rejects AI payloads containing runs/wickets/result/dls_target/training_eligible/etc.
  - AI schemas carry `is_official_truth=False` and correct `output_type`.
  - `scoring_service`, `dls_service`, and `domain/constants` do not import AI modules.
  - Training-eligibility fields are blocked from AI mutation.

Validation evidence:

- `pytest tests/test_health.py tests/test_results_endpoint.py` → 9 passed
- `pytest tests/test_dls_calculations.py` → 21 passed
- `pytest tests/test_analyst_pro_features.py` → 18 passed
- `pytest tests/test_match_ai_summary.py` → 5 passed
- `pytest tests/test_phase_6b_ai_boundary.py` → 37 passed
- No frontend files touched; frontend CI unaffected.
- No migrations, no new runtime dependencies, no scoring/DLS/historical import behavior changed.

#### Phase 6C — Cricksy Skills Architecture Spec (COMPLETE)

Spec-lock document: `docs/PHASE_6C_CRICKSY_SKILLS_ARCHITECTURE_SPEC.md`

Phase 6C deliverables (architecture only — no runtime skills/routers/agents built):

- Pre-phase audit captured for Phase 6A/6B governance, `backend/domain/ai_boundary.py`,
  AI response schemas carrying `ai_metadata`, deterministic analytics surfaces,
  historical import/registry/provenance/training eligibility, Analyst Workspace,
  Coach Pro Plus outputs, fake-data guard, auth/RBAC/org boundaries, CI gates,
  and existing skill-like modules already in repo.
- Mandatory formal Cricksy Skill contract locked, including required fields:
  `skill_id`, `name`, `version`, `category`, `purpose`, `supported_intents`,
  `allowed_roles`, `required_inputs`, `optional_inputs`,
  `deterministic_data_dependencies`, `forbidden_inputs`, `output_type`,
  `ai_boundary_metadata`, confidence/limitations fields, validation/safety rules,
  youth/org/no-fake-data rules, review requirement, sample output shape,
  tests required, and rollback/disable strategy.
- Future skill categories locked across Match Analysis, Player Analysis,
  Team/Opposition, Coach/Communication, and Data/Validation skills.
- Required architecture rules locked:
  deterministic-data-first, no official truth mutation, progressive disclosure,
  confidence + limitations labeling, review gating for high-impact outputs,
  no fake data, and strict role/org/youth-safety boundaries.
- Three fully written sample skills locked:
  Match Momentum Skill, Spin Weakness Skill, Coach Communication Skill.
- Protected deterministic systems and Phase 6B AI boundary explicitly preserved.

Validation notes:

- Markdown formatting reviewed.
- Phase ordering remains clear.
- Phase 6D–6H remain separate future phases and are not marked complete.
- No runtime implementation code, migrations, dependencies, routers, agents, or
  external AI provider workflows were added in this phase.

#### Phase 6D — Intent Router + Skill Router Spec (COMPLETE)

Spec-lock document: `docs/PHASE_6D_INTENT_ROUTER_AND_SKILL_ROUTER_SPEC.md`

Phase 6D deliverables (architecture/spec only — no runtime routers/skills/agents built):

- Future router architecture documented:
  User/Coach/Analyst Request → Intent Classifier → Intent Safety Gate →
  Skill Eligibility Resolver → Context Requirement Planner →
  Progressive Disclosure Loader → Skill Execution Request →
  Validation/Review Routing.
- Pre-phase audit captured for Phase 6A/6B/6C governance, Phase 6C skill contract,
  `backend/domain/ai_boundary.py` + `AiOutputMetadata`, Analyst Workspace data surfaces,
  historical import/registry/provenance/training-eligibility surfaces, Coach Pro Plus
  surfaces, AI-adjacent prompt-entry routes/services, auth/RBAC/org boundaries,
  fake-data guard, CI gates, and current ad-hoc intent-like behavior.
- Initial intent taxonomy locked across Match Analysis, Player Analysis,
  Team/Opposition, Coach/Communication, Analyst/Media, and Data/Validation intents.
- Blocked/deterministic-only intents explicitly locked (score/wicket/over/result/DLS/stat
  mutations, training-eligibility bypass attempts, validation bypass attempts).
- Mandatory intent-to-skill routing contract locked with required fields:
  `intent_id`, `intent_category`, `supported_user_phrases`, `required_role`,
  `allowed_skill_ids`, `required_context`, `forbidden_context`,
  `clarifying_questions`, `confidence_requirements`, `review_requirements`,
  `blocked_conditions`, `fallback_behavior`, `output_type`, `ai_boundary_metadata`.
- Required clarification, blocking, fallback, role/org boundary, youth-safety,
  and no-fake-data routing rules are documented.
- Required example mappings included (momentum analysis, spin weakness analysis,
  coaching notes generation, podcast breakdown with review requirement,
  deterministic-only score update request).
- Phase separation explicitly preserved:
  - Phase 6E = progressive disclosure mechanics
  - Phase 6F = confidence/uncertainty mechanics
  - Phase 6G = event-triggered compute rules
  - Phase 6H = validation agent/review queue mechanics

Validation notes:

- Markdown formatting reviewed.
- Phase ordering remains clear.
- Phase 6E–6H remain separate future phases and are not marked complete.
- No runtime implementation code, migrations, dependencies, routers, agents, or
  external AI provider workflows were added in this phase.

#### Phase 6E — Progressive Disclosure + Context Loading Rules

Define strict rules to load only relevant match/player/team/video/context data for each intelligence request.

#### Phase 6F — Confidence + Uncertainty System Spec

Define confidence metadata for generated intelligence, including data quality, sample size, tactical confidence, video confidence, recommendation confidence, overall confidence, and limitations.

#### Phase 6G — Event-Triggered Intelligence Spec

Define cheap always-on deterministic intelligence vs expensive triggered AI, with triggers such as coach questions, report requests, collapse detection, confidence drops, video uploads, or analyst-requested outputs.

#### Phase 6H — Validation Agents + Review Queue Spec

Define the review flow:

```text
Generated insight
↓
Data validation
↓
Cricket correctness validation
↓
Safety/language validation
↓
Confidence validation
↓
Coach/admin review queue
↓
Approved output
```

### Protected Files/Systems

- Live scoring truth and official score/balls/overs/wickets/innings/result/scorecard/player-stat paths.
- DLS calculation logic and related regression tests.
- Live bus/socket behavior.
- Historical import safety gates, registry linkage, and training-eligibility gates.
- Analyst Workspace provenance visibility rules.
- Coach Pro Plus video analysis, mental-analysis, and youth-facing report systems.
- Auth/RBAC/tier/organization boundaries.
- Fake-data guard behavior.
- CI/CD gates.

### Required Validation

Because Phase 6A is docs/spec-lock only:

- Verify Markdown formatting.
- Verify checklist phase ordering remains clear.
- Verify no existing phases are removed or marked complete without evidence.
- Verify no implementation code changed.
- Verify checklist structure is not accidentally corrupted.

### Completion Criteria

- Master Execution Checklist includes the governed Phase 6 intelligence architecture stream.
- Global intelligence rules, deterministic/AI boundaries, progressive disclosure, confidence, event-triggered compute, and review-queue rules are documented.
- Future Phase 6B–6H roadmap is documented.
- Phase 5 registry/import work is connected to the future intelligence foundation.
- No runtime app behavior changes.

---

# Phase 7 — Historical Match Ingestion: PDF/Image/OCR Review Flow

## Purpose

Expand historical imports to scanned scorecards, PDFs, and phone photos using OCR and human review.

## Pre-Phase Audit

Audit:

- Phase 4 ingestion schema
- file upload/S3 handling
- OCR library/cloud options
- storage cost
- async processing options
- security handling for uploaded files

## Spec Lock

Lock:

- OCR pipeline
- file type rules
- confidence score schema
- editable review UI
- low-confidence field behavior
- failed OCR behavior
- human approval workflow

## Gates

- OCR is never final authority
- human review required before save
- low-confidence fields visible
- secure file validation
- existing structured JSON import unaffected
- CI passes

## Required Tests

- PDF upload
- image upload
- unsupported file rejection
- OCR extraction mocked test
- low-confidence review test
- manual correction test
- failed OCR test
- existing ingestion regression tests
- full CI gates

## Completion Criteria

Teams can upload scans/photos/PDFs and review extracted match data before saving.

---

# Phase 8 — AI Analytics + Match Intelligence Enhancements

## Purpose

Improve AI insights while protecting deterministic cricket truth.

## Primary Areas

Likely affected after audit:

- backend analytics services
- prediction endpoints
- player insight services
- frontend analytics/dashboard views
- model input/output contracts

## Pre-Phase Audit

Audit:

- existing analytics services
- existing prediction behavior
- existing AI/model usage
- data quality
- latency
- cost
- dashboard dependencies

## Spec Lock

Lock:

- model input schema
- model output schema
- confidence thresholds
- explainability fields
- cache/fallback behavior
- forbidden mutations

## Gates

- AI advisory only
- scoring truth untouched
- confidence shown
- explanations included
- existing liked model behavior preserved unless approved
- CI passes

## Required Tests

- prediction input validation
- prediction output validation
- confidence threshold tests
- explainability tests
- latency tests where possible
- dashboard rendering tests
- full CI gates

## Completion Criteria

AI insights are more useful and explainable without compromising official cricket data.

---

# Phase 9 — Subscription, Pricing + Tier Enforcement Hardening

## Purpose

Make monetization and access control production-safe.

## Primary Areas

- `backend/config/pricing.py`
- backend auth/RBAC/tier services
- frontend pricing/upgrade/paywall pages
- subscription/webhook code, if present

## Pre-Phase Audit

Audit:

- pricing config
- tier matrix
- entitlements
- payment flow
- webhook flow
- premium feature checks
- Coach Pro Plus access

## Spec Lock

Lock:

- tier matrix
- feature entitlements
- trial behavior
- coupon behavior
- webhook behavior
- cancellation behavior
- private beta exceptions

## Gates

- no premium leakage
- backend enforces access
- frontend hides restricted UI
- webhook updates trusted only
- failed payment handling exists
- CI passes

## Required Tests

- tier access tests
- upgrade/downgrade tests
- expired subscription tests
- private beta allowlist tests
- webhook tests if present
- frontend paywall tests
- full CI gates

## Completion Criteria

Paid features are protected correctly and pricing/tier behavior is reliable.

---

# Phase 10 — Organization Pro + League Operations

## Purpose

Strengthen Cricksy for schools, clubs, leagues, academies, and multi-team organizations.

## Pre-Phase Audit

Audit:

- organization/team schemas
- tournament schemas
- role hierarchy
- sponsor tools
- viewer branding
- admin tools

## Spec Lock

Lock:

- org hierarchy
- team management rules
- coach/analyst/player permissions
- sponsor rules
- tournament workflows
- branded viewer rules

## Gates

- organization data isolation
- role hierarchy enforced
- sponsor assets scoped correctly
- tournament changes do not break scoring
- CI passes

## Required Tests

- cross-org isolation
- team assignment
- coach-player linking
- analyst access
- tournament management
- sponsor upload/visibility
- full CI gates

## Completion Criteria

Organizations can safely manage teams, tournaments, sponsors, and roles.

---

# Phase 11 — Live Viewer, Streaming + Sponsor Experience

## Purpose

Improve match viewing, streaming support, sponsor display, and fan experience.

## Pre-Phase Audit

Audit:

- viewer architecture
- snapshot/polling/websocket approach
- sponsor components
- stream link assumptions
- frontend performance
- CDN/static hosting assumptions

## Spec Lock

Lock:

- viewer update contract
- stream link rules
- overlay layout
- sponsor strip placement
- watermark behavior
- performance targets

## Gates

- viewer remains fast
- score readability preserved
- sponsor display controlled
- stream links permissioned
- CI passes

## Required Tests

- viewer rendering
- snapshot update behavior
- sponsor strip rendering
- stream link permission
- mobile/tablet checks
- full CI gates

## Completion Criteria

The live viewing experience is more professional without harming scoring or performance.

---

# Phase 12 — Media, Highlights + Report Content Engine

## Purpose

Turn match/player data into reports, social content, summaries, and sponsor-ready assets.

## Pre-Phase Audit

Audit:

- export/report code
- PDF/report generation
- player stats sources
- sponsor branding assets
- storage location
- AI text generation usage

## Spec Lock

Lock:

- content types
- export formats
- branding rules
- human review rules
- sharing permissions
- AI safety rules

## Gates

- public content reviewable
- generated claims grounded in data
- permissions enforced
- sponsor branding accurate
- CI passes

## Required Tests

- match summary generation
- player card generation
- report export
- sponsor branding
- permission checks
- full CI gates

## Completion Criteria

Cricksy can safely create useful media/reporting assets from existing data.

---

# Phase 13 — Lightweight Cricket Supervisor Layer

## Purpose

Introduce a careful orchestration layer inspired by Claw-style workflow management without giving AI control over match truth.

This phase should happen only after core features are stable.

## Pre-Phase Audit

Audit:

- existing AI service boundaries
- existing coach workflows
- existing analytics workflows
- report generation flows
- permissions
- logs/auditability

## Spec Lock

Lock:

- supervisor responsibilities
- forbidden actions
- routing map
- memory rules
- approval rules
- audit logs
- fallback behavior

## Gates

- supervisor cannot mutate score/match truth
- high-impact actions require approval
- routing is logged
- permissions enforced
- CI passes

## Required Tests

- routing tests
- permission tests
- forbidden mutation tests
- approval tests
- audit log tests
- fallback tests
- full CI gates

## Completion Criteria

Cricksy gains safe workflow orchestration without becoming over-agentic or unstable.

---

# Phase 14 — Production Scale, Monitoring + Cost Control

## Purpose

Prepare Cricksy for larger adoption across schools, clubs, leagues, academies, and organizations.

## Primary Areas

- `infra/terraform/`
- deployment workflows
- logging/monitoring
- S3/storage lifecycle
- worker scaling
- AI/video/OCR cost tracking

## Pre-Phase Audit

Audit:

- AWS infrastructure
- Terraform outputs/variables
- backend deployment workflow
- frontend deployment workflow
- S3 usage
- worker costs
- AI/model costs
- DB backups
- monitoring/logging

## Spec Lock

Lock:

- scaling thresholds
- alerting rules
- backup schedule
- recovery process
- cost thresholds
- security hardening
- abuse prevention

## Gates

- load stability
- recovery readiness
- cost visibility
- security baseline
- CI passes

## Required Tests

- load tests
- worker stress tests
- upload stress tests
- backup/restore test plan
- security tests
- cost reporting checks
- full CI gates

## Completion Criteria

Cricksy is operationally ready for wider adoption and heavier usage.

---

# Universal Phase Completion Report

Every phase must end with:

```text
Phase:
Branch:
PR:
Files changed:
Protected files touched:
Migrations added:
Existing behavior preserved:
Tests added:
Tests run locally:
CI result:
Manual QA:
Deployment impact:
Rollback plan:
Known risks:
User approval needed:
Ready to merge:
Ready to deploy:
```

---

# Universal Copilot Prompt Template

```text
System context:
You are working in the existing Cricksy production app repository: Jnpaul1984/Cricksy_Scorer. This is not a rebuild. The app already has backend, frontend, CI/CD, Alembic migrations, Docker Compose flows, AWS/Terraform infrastructure, and an existing Coach Pro Plus Video Analysis pipeline.

Objective:
[State exact task.]

Pre-phase audit findings:
[Paste findings.]

Spec lock:
[Paste locked scope.]

Strict scope:
Only modify:
- [allowed files]

Do not modify:
- [protected files]

Constraints:
- Preserve existing production behavior.
- Do not rewrite working systems.
- Do not replace the existing video model/pipeline unless explicitly approved.
- Do not bypass CI/CD expectations.
- AI must not mutate official cricket truth.
- Add or update tests for changed behavior.
- No placeholders.
- Must compile.

Required validation:
- pre-commit run --all-files
- ruff check .
- ruff format --check .
- backend mypy from backend/
- affected backend pytest files
- backend integration tests when API/data behavior changes
- DLS tests when scoring/match rules are touched
- frontend guard/type-check/build when frontend changes

Output requirements:
- Exact files changed
- Full changed functions/files where needed
- Tests added/updated
- Commands run
- Results
- Risks
- Rollback notes

Self-validation:
Check imports, typing, formatting, migrations, tests, and CI impact before final response.
```

---

# Recommended Execution Order

1. Phase 0 — Repo Baseline + CI/CD Lock
2. Phase 1 — Existing App Stabilization + Regression Protection
3. Phase 2 — Coach + Player Development Enhancements
4. Phase 3 — Coach Pro Plus Video Analysis Hardening + Extension
5. Phase 4 — Analyst System Blueprint Audit + Spec Lock
6. Phase 5 — Historical Match Ingestion: Structured JSON First
7. Phase 6 — Cricksy Intelligence Operating System Governance
8. Phase 7 — Historical Match Ingestion: PDF/Image/OCR Review Flow
9. Phase 8 — AI Analytics + Match Intelligence Enhancements
10. Phase 9 — Subscription, Pricing + Tier Enforcement Hardening
11. Phase 10 — Organization Pro + League Operations
12. Phase 11 — Live Viewer, Streaming + Sponsor Experience
13. Phase 12 — Media, Highlights + Report Content Engine
14. Phase 13 — Lightweight Cricket Supervisor Layer
15. Phase 14 — Production Scale, Monitoring + Cost Control

Reason:

Protect the deployed app and CI/CD first. Then stabilize the already-working Coach Pro Plus Video Analysis system before expanding into player development, historical ingestion, governed intelligence architecture, and broader intelligence features.

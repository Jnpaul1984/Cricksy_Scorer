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

## Rule 8 — Phase Naming Governance

No new phase name may be used for GitHub issues, PRs, commit messages, or implementation plans unless it already exists in the Master Execution Checklist or is first added through a checklist-governance PR.

Inventing a phase name outside the checklist is a governance violation.

If a new phase is needed:

1. Open a checklist-governance PR that adds the new phase to this document.
2. Get the PR reviewed and merged.
3. Only then reference the new phase name in issues, PRs, or implementation work.

This rule prevents phase-name drift where assistant/Copilot recommendations use invented names that do not match the governed phase sequence.

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

## Phase 5K — Historical Data Backfill + Analyst UI Theme Fix (COMPLETE)

> **Completion evidence**: `docs/PHASE_5K_HISTORICAL_BACKFILL_AND_ANALYST_THEME_QA.md` status = "Complete".
> Backend: `backend/services/historical_import_backfill_service.py`, `POST .../repair-metadata` endpoint, `backend/tests/test_historical_import_backfill.py` all exist and pass.
> Frontend: `--color-surface-raised` CSS variable added to `designSystem.css`; Key Players and Podcast Prep dark-theme cards fixed.


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

## Phase 5L — Bulk ZIP Historical Upload (Implementation Complete; Manual QA Pending)

> **Status note**: Backend implementation and automated tests are complete.
> `backend/tests/test_historical_import_bulk_zip.py` exists and passes; `POST /api/historical-import/json/bulk-zip/dry-run` and `/bulk-zip/apply` endpoints are implemented.
> Phase 5L.1 cost-control limits are validated (see Phase 5L.1 Validation Evidence section below).
> **Follow-up required**: The operator-level manual QA checklist in `docs/PHASE_5L_BULK_ZIP_HISTORICAL_JSON_UPLOAD_QA.md` has unchecked items. A manual QA pass and sign-off is needed before Phase 5L is fully closed for production readiness.


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

#### Phase 6E — Progressive Disclosure + Context Loading Rules (COMPLETE)

Spec-lock document: `docs/PHASE_6E_PROGRESSIVE_DISCLOSURE_AND_CONTEXT_LOADING_RULES.md`

Phase 6E deliverables (architecture/spec only — no runtime loaders/routers/skills/agents built):

- Required future context-loading architecture is locked:
  Intent + Skill Mapping → Context Requirement Contract →
  Permission + Org Boundary Check → Minimum Relevant Data Selection →
  Context Budget Check → Confidence/Sufficiency Check →
  Skill Execution Context Package → Fallback if insufficient/unsafe/too large.
- Pre-phase audit captured for Phase 6A–6D governance docs, 6D context fields
  (`required_context`, `forbidden_context`), Analyst Workspace and case-study surfaces,
  historical import/registry/provenance/training-eligibility surfaces,
  Coach Pro Plus/video-analysis surfaces, player/team/match/delivery/stat surfaces,
  auth/RBAC/org boundaries, fake-data guard, AI-adjacent context patterns, `agent_budget.py`,
  CI gates, and current risky broad-context patterns.
- Required principles are locked:
  minimum necessary context, deterministic-data-first context selection,
  permission-before-context, explicit context budgets, sufficiency checks with
  `insufficient_data`, staged progressive loading, and strict no-fake-data behavior.
- Mandatory future context package contract is documented with required fields including:
  `context_package_id`, `intent_id`, `skill_id`, `user_role`, `org_scope`,
  `selected_entities`, `required_context`, `optional_context`, `forbidden_context`,
  `data_sources`, `permission_checks`, `context_budget`,
  `loaded_context_summary`, `omitted_context_summary`, `sufficiency_status`,
  `insufficient_data_reasons`, `confidence_inputs`, `privacy_boundary_notes`,
  `provenance_references`, `no_fake_data_confirmation`.
- Safe fallback outcomes are explicitly locked:
  `insufficient_data`, `needs_narrower_scope`, `not_authorized`,
  `context_budget_exceeded`, `metadata_only_pending_full_import`,
  `missing_selected_match`, `missing_selected_player`,
  `video_context_unavailable`, `blocked_by_youth_safety`,
  `blocked_by_org_boundary`.
- Required example context contracts are included for:
  spin weakness (one player, one match), match momentum (one selected match),
  coach notes (one selected player), podcast breakdown (one selected historical match),
  and training eligibility review (metadata-only historical import).
- Phase separation explicitly preserved:
  - Phase 6F = confidence/uncertainty mechanics
  - Phase 6G = event-triggered compute rules
  - Phase 6H = validation/review queue mechanics

Validation notes:

- Markdown formatting reviewed.
- Phase ordering remains clear.
- Phase 6F–6H remain separate future phases and are not marked complete.
- No runtime context loader, routers, skills, agents, Supervisor logic, migrations,
  dependencies, or external AI provider workflows were added in this phase.
- No production behavior changed.

#### Phase 6F — Confidence + Uncertainty System Spec (COMPLETE)

Spec-lock document: `docs/PHASE_6F_CONFIDENCE_AND_UNCERTAINTY_SYSTEM_SPEC.md`

Phase 6F deliverables (architecture/spec only — no runtime confidence engine, validation
agents, routers, skills, LLM calls, migrations, dependencies, or production behavior changes):

- Pre-phase audit captured for Phase 6A–6E governance docs, `AiOutputMetadata` and
  non-authoritative AI output behavior, Phase 6C skill contract confidence fields,
  Phase 6E context package sufficiency and `confidence_inputs` fields, prediction/model
  probability outputs, Analyst Workspace case-study/key-player/momentum/report surfaces,
  Coach Pro Plus/video-analysis outputs and confidence-like fields, historical import
  validation/registry/provenance/training-eligibility, fake-data guard, auth/RBAC/org
  boundaries, CI gates, and current risky patterns where insights are presented without
  limitations.
- Required future confidence architecture locked:
  Context Package → Data Quality Check → Sample Size Check →
  Skill-Specific Confidence Inputs → Uncertainty Classification →
  Confidence Score Package → Output Framing Rules → Review / Fallback Decision.
- Required confidence dimensions locked:
  `data_quality_confidence`, `sample_size_confidence`, `tactical_confidence`,
  `video_confidence`, `model_confidence`, `recommendation_confidence`,
  `overall_confidence`, `limitations`, `uncertainty_reasons`, `review_required`.
- Mandatory confidence package contract locked with all required fields:
  `confidence_package_id`, `intent_id`, `skill_id`, `context_package_id`,
  `output_type`, all confidence dimension scores, `confidence_band`, `limitations`,
  `uncertainty_reasons`, `required_disclaimers`, `review_required`, `review_reason`,
  `fallback_behavior`, `no_fake_data_confirmation`, `provenance_references`.
- Standard confidence bands locked with conceptual thresholds (governance defaults only):
  `high_confidence` (>= 0.80), `medium_confidence` (0.60–0.79),
  `low_confidence` (0.40–0.59), `insufficient_data` (< 0.40 or missing required context),
  `not_applicable` (dimension does not apply).
- Standard uncertainty reason codes locked:
  `small_sample_size`, `missing_delivery_data`, `metadata_only_pending_full_import`,
  `video_context_unavailable`, `low_data_quality`, `conflicting_signals`,
  `model_not_calibrated`, `insufficient_historical_context`,
  `not_authorized_to_access_context`, `youth_safety_review_required`,
  `manual_review_required`.
- User-facing language rules locked: low-confidence must never be written as certain;
  insufficient-data must not produce recommendations; small-sample insights labelled as
  early signals; model outputs not presented as guarantees; video-derived insights expose
  visibility limitations; youth/player feedback uses safe developmental language.
- Review trigger rules locked: youth player feedback, mental/performance criticism,
  public/podcast content, scouting reports, low/medium recommendation confidence,
  low sample size confidence, low/uncalibrated model confidence, low video certainty,
  conflicting signals, and outputs affecting training/selection/development decisions.
- Safe fallback outcomes locked:
  `insufficient_data`, `low_confidence_review_required`, `needs_more_context`,
  `sample_size_too_small`, `model_uncalibrated`, `video_context_unavailable`,
  `blocked_by_youth_safety`, `not_authorized`, `metadata_only_pending_full_import`.
- Five example confidence packages included:
  high-confidence match momentum insight, low-sample spin weakness insight,
  video-analysis insight with medium video certainty,
  metadata-only historical import training eligibility review,
  podcast/analyst media output requiring review.
- Phase separation explicitly preserved:
  - Phase 6G = event-triggered compute rules
  - Phase 6H = validation agent/review queue mechanics
- Docs-only template added: `docs/confidence_templates/confidence_score_package.example.yaml`.

Validation notes:

- Markdown formatting reviewed.
- Phase ordering remains clear.
- Phase 6G–6H remain separate future phases and are not marked complete.
- No runtime confidence engine, validation agents, runtime skills, runtime routers, agents,
  Supervisor logic, LLM workflows, migrations, dependencies, or external AI provider
  workflows were added in this phase.
- No production behavior changed.

#### Phase 6G — Event-Triggered Compute + Cost Control Spec (COMPLETE)

Spec-lock document: `docs/PHASE_6G_EVENT_TRIGGERED_COMPUTE_AND_COST_CONTROL_SPEC.md`

Phase 6G deliverables (architecture/spec only — no runtime event bus, queues, workers,
schedulers, agents, runtime skills, runtime routers, Supervisor logic, LLM calls,
migrations, dependencies, or production behavior changes):

- Pre-phase audit captured for Phase 6A–6F governance docs, existing always-on deterministic
  systems (score engine, match state, statistical engine, metadata registry, prediction
  outputs, player metrics, phase tags, validation/training-eligibility status), existing
  AI-adjacent services and their current trigger models, `backend/services/agent_budget.py`
  operational budget guard, Coach Pro Plus/video-analysis worker patterns, Phase 5L.1
  historical import metadata-only and full import gating, auth/RBAC/org/youth-safety
  boundaries, CI/CD constraints, fake-data guard behavior, and current risky patterns where
  route-triggered AI outputs run without explicit user approval or budget governance.
- Required future event-triggered compute architecture locked:
  Event/User Action/System Signal → Trigger Eligibility Check → Role + Org + Safety Check →
  Context Budget Check → Compute Budget Check → Confidence/Necessity Check →
  Approved Compute Request → Output + Cost/Audit Metadata → Review Queue if required.
- Always-on vs triggered compute split locked:
  always-on deterministic systems listed; triggered/expensive/governed systems listed with
  explicit requirement for approved trigger, compute budget package, and audit metadata.
- Trigger taxonomy locked:
  `user.coach_question`, `user.analyst_report_request`, `user.podcast_breakdown_request`,
  `user.match_player_analysis_request`, `user.coach_development_notes_request`,
  `match.collapse_detected`, `match.momentum_swing_detected`, `match.phase_transition`,
  `match.win_probability_swing`, `match.death_overs_reached`, `match.unusual_run_rate_drop`,
  `data.historical_import_completed`, `data.metadata_only_promoted_to_full`,
  `data.video_uploaded`, `data.video_analysis_completed`,
  `data.new_player_team_competition_registered`, `data.model_output_generated`,
  `confidence.low_confidence_detected`, `confidence.conflicting_signals_detected`,
  `confidence.sample_size_below_threshold`, `confidence.missing_data_blocks_recommendation`,
  `safety.youth_safety_review_required`.
- Blocked triggers locked: every ball, every score update, every page load, every dashboard
  refresh, every historical import file, every video frame, every player profile visit.
- Mandatory compute budget package contract locked with all required fields:
  `compute_request_id`, `trigger_id`, `trigger_type`, `intent_id`, `skill_id`,
  `context_package_id`, `confidence_package_id`, `requested_by_user_id`, `org_scope`,
  `compute_class`, `estimated_cost_class`, `max_runtime_seconds`, `max_context_items`,
  `max_model_calls`, `rate_limit_key`, `requires_user_confirmation`, `requires_review`,
  `fallback_behavior`, `audit_log_required`, `no_fake_data_confirmation`.
- Cost classes locked: `free_deterministic`, `low_cost_local`, `moderate_model_compute`,
  `high_cost_ai_generation`, `blocked_without_approval`.
- Guardrails locked: no page-load compute, no per-ball compute, rate limiting required,
  role/org authorization required, sufficient context required, metadata-only gate,
  youth/safety review gate, audit metadata required.
- Safe fallback outcomes locked:
  `deterministic_summary_only`, `requires_user_confirmation`, `compute_budget_exceeded`,
  `rate_limited`, `insufficient_context`, `metadata_only_pending_full_import`,
  `not_authorized`, `review_required_before_generation`, `blocked_by_cost_policy`,
  `unsupported_trigger`.
- Five example compute contracts included:
  coach spin-weakness question (moderate_model_compute, 1 model call),
  analyst podcast breakdown (high_cost_ai_generation, review required),
  collapse detected during live match (deferred until coach confirms),
  video uploaded and completed then coach requests technical summary (review required),
  metadata-only ZIP import blocks cross-match AI analysis until full import.
- Trigger eligibility check flow documented (8-step governance sequence).
- Phase separation explicitly preserved:
  - Phase 6H = validation agent/review queue mechanics
- Docs-only template added: `docs/compute_templates/event_trigger_compute_contract.example.yaml`.

Validation notes:

- Markdown formatting reviewed.
- Phase ordering remains clear.
- Phase 6H remains separated from Phase 6G scope and is completed in the section below.
- No runtime event bus, queue, worker, scheduler, agent, runtime skill, runtime router,
  Supervisor logic, LLM workflow, migration, dependency, or external AI provider workflow
  was added in this phase.
- No production behavior changed.
- `backend/services/agent_budget.py` runtime logic unchanged.

#### Phase 6H — Validation Agents + Review Queue Spec (COMPLETE)

Spec-lock document: `docs/PHASE_6H_VALIDATION_AGENTS_AND_REVIEW_QUEUE_SPEC.md`

Phase 6H deliverables (architecture/spec only — no runtime validation agents,
review queue backend/UI, approval workflow code, notifications, migrations,
dependencies, infrastructure, routers, skills, agents, Supervisor logic,
LLM calls, or production behavior changes):

- Pre-phase audit captured for Phase 6A–6G governance/contracts, AI boundary metadata,
  context/confidence/compute contract foundations, Analyst Workspace and case-study
  report surfaces, Coach Pro Plus/video-analysis/PDF surfaces, mental/performance
  output surfaces, auth/RBAC/org boundaries, youth-safety and language governance,
  fake-data/provenance guardrails, audit/logging patterns, CI gates, and current risky
  pattern where route-triggered output can become user-facing without standardized review.
- Required future validation architecture locked:
  Generated Insight/Report/Recommendation → Data Validation →
  Cricket Correctness Validation → Confidence + Uncertainty Validation →
  Safety + Language Validation → Role + Org Boundary Validation →
  Review Queue → Coach/Admin/Analyst Approval →
  Approved Output or Rejected/Escalated Output.
- Required validation agent/check categories locked:
  Data Validation Agent, Cricket Correctness Validator,
  Confidence + Uncertainty Validator, Safety + Language Validator,
  Role + Org Boundary Validator.
- Review queue states locked:
  `draft_generated`, `validation_pending`, `validation_failed`, `review_required`,
  `in_review`, `changes_requested`, `approved_internal`, `approved_coach_facing`,
  `approved_public`, `rejected`, `escalated`, `archived`.
- Mandatory review queue item contract locked with required fields including:
  `review_item_id`, `source_output_id`, `output_type`, `intent_id`, `skill_id`,
  `compute_request_id`, `context_package_id`, `confidence_package_id`,
  `created_by_system_component`, `requested_by_user_id`, scope fields,
  `review_state`, `validation_results`, `confidence_band`, risk/review assignment fields,
  approval/publication fields, audit/no-fake-data/provenance fields.
- Output-type review requirements locked for youth feedback, mental/performance criticism,
  coach reports, scouting reports, podcast/public content, training recommendations,
  workload/injury-sensitive recommendations, low-confidence outputs,
  AI tactical recommendations, model-derived recommendations, video-analysis summaries,
  and opposition reports.
- Reviewer roles and approval levels locked:
  roles (`coach`, `analyst`, `admin`, `organization_admin`, `safety_reviewer`,
  `media_reviewer`, `system_validator`) and publication levels
  (`internal_only`, `coach_facing`, `team_facing`, `player_facing`,
  `organization_facing`, `public_media`) with stricter `public_media` controls.
- Validation outcomes and fallback behaviors locked:
  outcomes (`passed`, `failed`, `warning`, `needs_review`, `blocked`,
  `insufficient_data`, `not_authorized`, `low_confidence`, `unsafe_language`,
  `unsupported_claim`) and safe fallbacks (`hold_for_review`, `request_more_context`,
  `request_human_revision`, `block_publication`, `return_insufficient_data`,
  `downgrade_to_internal_only`, `strip_unsupported_claims`, `escalate_to_admin`).
- Required audit trail rules locked for requester/context/intent-skill/confidence,
  validators/outcomes, reviewer decisions, timestamps, publication target,
  and approval/rejection/escalation reasoning.
- Five required example review queue items included:
  youth feedback requiring coach/safety review,
  podcast breakdown requiring analyst/media review,
  low-confidence spin weakness recommendation requiring review,
  coach report approved for coach-facing use,
  unsupported claim blocked by cricket correctness validator.
- Future runtime validation tests defined for state transitions, permission gates,
  public-media stricter approval, fallback enforcement, provenance/no-fake-data checks,
  audit completeness, and preserved Phase 6B official-truth boundaries.
- Phase 6A–6H completion summary: Phase 6 governance stream is now complete as
  spec architecture. The next checklist-defined phase is
  **Phase 7 — Historical Match Ingestion: PDF/Image/OCR Review Flow**.
  The earlier post-Phase-6 governance snapshot in
  `docs/POST_PHASE_6_ORDERING_AND_PHASE_5_AUDIT.md` identified Phase 5N, 5O, and
  5P as incomplete at that time. Since then, the repo has added implemented
  Phase 5N, 5O, and 5P foundations. See
  `docs/PHASE_6F_INTELLIGENCE_OS_CLOSURE_AND_PHASE_7_READINESS.md` for the
  current closure audit and Phase 7 entry recommendation.

> **Governance correction (Issue #190)**: A previous draft of this section
> referenced "Phase 7A — Intelligence Runtime Readiness Audit + First
> Implementation Slice Selection." That name does not exist in the Master
> Execution Checklist and was an invented phase name. Per Rule 8 (Phase Naming
> Governance), no phase name may be used unless it is already in the checklist
> or is added through a checklist-governance PR. The correct next phase, per the
> checklist, is **Phase 7 — Historical Match Ingestion: PDF/Image/OCR Review
> Flow**. The invented "Phase 7A" name is not valid and must not be used in
> issues, PRs, or implementation plans.


Validation notes:

- Markdown formatting reviewed.
- Phase ordering remains clear.
- Phase 6 governance stream (6A–6H) is now complete as spec architecture.
- No runtime implementation code, migrations, dependencies, infrastructure,
  or production behavior changes were added.

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

## Sub-phases

### Phase 7A — Manual QA + Operator Workflow Validation for OCR Review Flow

- Completed.
- Evidence: `docs/PHASE_7A_OCR_REVIEW_FLOW_MANUAL_QA.md`
- Scope: operator UX validation, empty/loading state polish, dry-run gating tightening,
  focused frontend unit coverage for `HistoricalOcrReviewPanel`.

### Phase 7B — OCR Extraction Engine Integration Audit + Spec Lock

- Completed.
- Evidence: `docs/PHASE_7B_OCR_EXTRACTION_ENGINE_AUDIT_AND_SPEC_LOCK.md`
- Scope: audit of existing Phase 7/7A code assets; OCR engine options comparison;
  spec-lock document with recommended hybrid extraction strategy, non-authoritative boundary
  rules, input/output contract, confidence/uncertainty schema, failure modes, file validation
  rules, CI/testing plan, rollout/rollback plan, and Phase 7C recommendation.
- Recommendation: Option 6 hybrid — manual candidate JSON (default, current); optional PDF
  text extraction via `pdfplumber` in Phase 7C; Tesseract image OCR deferred to Phase 7D.
- No OCR engine implementation added. No official cricket truth behavior changed.

---

### Phase 7C — PDF Text Extraction Integration

- Completed.
- Evidence: `docs/PHASE_7C_PDF_TEXT_EXTRACTION_INTEGRATION.md`
- Scope: optional `pdfplumber`-based extraction for digital PDFs only; graceful fallback for
  scanned PDFs; review-only extracted text preview; focused backend/frontend test coverage.
- Recommendation: keep PDF extraction non-authoritative and review-only; defer image OCR to
  Phase 7D audit/spec-lock.
- No image OCR or hosted OCR added. No official cricket truth behavior changed.

### Phase 7D — Tesseract/Image OCR Integration Audit + Spec Lock

- Completed.
- Evidence: `docs/PHASE_7D_TESSERACT_IMAGE_OCR_AUDIT_AND_SPEC_LOCK.md`
- Scope: audit of the existing OCR review flow, Phase 7C extraction path, frontend review
  panel, import E2E coverage, backend Docker/runtime constraints, deploy workflow, ECS image
  implications, local Tesseract/OpenCV feasibility, confidence/fallback rules, and rollback
  safety for image OCR.
- Recommendation: proceed only with a narrow optional Phase 7E local Tesseract image-text
  assist slice for direct image uploads; defer scanned PDF conversion, OpenCV-heavy
  preprocessing, and hosted OCR.
- No image OCR runtime implementation added. No official cricket truth behavior changed.

### Phase 7 — Closure Note

- Status: **Core workflow implemented. Remaining OCR enhancement sub-phases intentionally deferred.**
- Closure note: `docs/PHASE_7_CLOSURE_AND_OCR_DEFERRAL_NOTE.md`

**Completed sub-phases:**
- Phase 7 — OCR review candidate workflow ✅
- Phase 7A — Manual QA + operator workflow validation ✅
- Phase 7B — OCR extraction engine audit/spec-lock ✅
- Phase 7C — PDF text extraction for review candidates ✅
- Phase 7D — Tesseract/image OCR audit/spec-lock ✅

**Deferred sub-phases:**
- Phase 7E — Optional Tesseract/Image OCR Integration for Review Candidates ⏸
- Phase 7F — OCR Ingestion Manual QA + Production Readiness Gate ⏸

**Reason for deferral:**
Image OCR has higher operational complexity and should be implemented once real club
scorecard formats, scanned documents, and customer workflows are available. Deferral is a
product/customer timing decision, not technical abandonment.

**Next active phase: Phase 8 — AI Analytics + Match Intelligence Enhancements**

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

## Phase 8 Sub-phases

### Phase 8A — AI Analytics Runtime Audit + Spec Lock

**Purpose**
- Audit existing AI analytics and related contracts/operations before new implementation continues.

**Strict scope**
- Docs/spec only. No runtime code changes.

**Gates**
- Audit is repo-grounded across prediction endpoints, player insight services, frontend dashboards, confidence behavior, latency, cost, and model contracts.
- Deterministic cricket truth remains protected (`AI advisory only`, `scoring truth untouched`).

**Required tests / validation expectations**
- Documentation validation only (render/format checks, references resolve, no runtime behavior changed).

**Completion criteria**
- Repo-grounded audit and spec lock exist for Phase 8 implementation.

**Status**
- Pending.

### Phase 8B — Insight Contract + Explainability Standardization

**Purpose**
- Standardize AI insight output shape so each insight exposes confidence, explanation, limitations, provenance/source references, and advisory metadata.

**Strict scope**
- Backend/frontend contracts only. Do not retrain or replace models.

**Gates**
- Contract fields are defined and governed:
  - `insight_id`
  - `insight_type`
  - `title`
  - `summary`
  - `explanation`
  - `confidence_score`
  - `confidence_band`
  - `limitations`
  - `source_context`
  - `provenance_references`
  - `generated_at`
  - `model_or_service_source`
  - `review_state`
  - `ai_metadata`
- Contract governance does not permit mutation of official scoring truth.

**Required tests / validation expectations**
- Contract/schema validation tests for affected backend/frontend AI insight surfaces.
- Backward-compatibility checks or documented migration path validation where full conformance is deferred.

**Completion criteria**
- Insight contract exists and affected AI insight outputs conform or have documented migration paths.

**Status**
- Pending.

### Phase 8C — AI Insight Feedback + Review Workflow

**Purpose**
- Enable authorized reviewers to approve/reject/request changes, mark useful/not useful, flag unsupported/unsafe claims, and add reviewer notes to AI insights.

**Strict scope**
- Review metadata workflow only. No scoring, DLS, official stat/result, or model mutation.

**Gates**
- Reviewer actions are permissioned and auditable.
- Role/org boundaries are enforced.
- AI remains advisory and cannot alter deterministic match truth.

**Required tests / validation expectations**
- Backend persistence and RBAC tests for review state.
- Frontend workflow tests for review actions and visible review status on a real insight surface.
- CI must pass before completion.

**Completion criteria**
- Review workflow is visible in at least one real insight surface, backend review state is persisted, role/org boundaries are enforced, and tests pass.

**Status**
- In progress via PR `Jnpaul1984/Cricksy_Scorer#225`. Do not mark complete until that PR merges and CI passes.

### Phase 8D — Analyst Workspace AI Insight Panel Upgrade

**Purpose**
- Make AI insights visible and useful in Analyst Workspace using real match/player/team data.

**Strict scope**
- Analyst Workspace UI and supporting read-only data contracts only.

**Gates**
- Display must include confidence labels, limitations, source references, and review state.
- No fake data and no mutation of scoring truth.

**Required tests / validation expectations**
- Analyst Workspace UI rendering and contract tests for insight payloads.
- Validation that displayed insights are sourced from real data pipelines.

**Completion criteria**
- Analysts can view match intelligence summaries, key player insights, tactical/phase notes, confidence labels, limitations, source references, and review status.

**Status**
- Pending.

### Phase 8E — Player Development AI Insight Cards

**Purpose**
- Support coaching vision with clear developmental recommendations for weaker-player improvement.

**Strict scope**
- Developmental insight cards only. Player-facing outputs must remain reviewed and safe.

**Gates**
- Card sections are governed:
  - `main strength`
  - `main weakness`
  - `technical focus`
  - `tactical focus`
  - `recommended drill category`
  - `confidence level`
  - `sample-size warning`
  - `coach review status`
- Youth/player-impacting output must respect review gating.

**Required tests / validation expectations**
- Card schema/UI tests for required sections and safe language behavior.
- Review-gate tests ensuring coach/player-facing outputs are blocked until approved where required.

**Completion criteria**
- Coach-facing player development cards exist with confidence, limitations, safe language, and review gating for youth/player-impacting output.

**Status**
- Pending.

### Phase 8F — Match Intelligence Explainability + Source Citations

**Purpose**
- Ensure tactical AI claims can surface deterministic data sources behind each claim.

**Strict scope**
- Explainability and source/provenance display only. No model replacement.

**Gates**
- Claims show source/provenance links to deterministic cricket data.
- Sample-size caveats are shown where relevant.
- Scoring truth remains unchanged.

**Required tests / validation expectations**
- Explainability/source citation rendering tests across match insight surfaces.
- Validation that cited metrics map to deterministic sources (balls faced, phase data, scoring rate, dismissal patterns, dot-ball percentage, opposition context).

**Completion criteria**
- AI match insights show source references such as balls faced, phase data, scoring rate, dismissal patterns, dot-ball percentage, opposition context, and sample-size caveats where relevant.

**Status**
- Pending.

### Phase 8G — AI Insight Cache + Fallback Behavior

**Purpose**
- Reduce repeated AI generation and control latency/cost.

**Strict scope**
- AI insight caching/fallback behavior only.

**Gates**
- Required behavior is governed:
  - reuse existing insight if context has not changed
  - fallback to deterministic summary if AI is unavailable
  - show stale/refresh status
  - do not regenerate on every page load
  - rate-limit expensive insight generation
- Deterministic cricket truth remains authoritative.

**Required tests / validation expectations**
- Cache hit/miss and freshness tests.
- Fallback behavior tests when AI dependency is unavailable.
- Event-triggered or explicit user-triggered generation behavior tests.

**Completion criteria**
- AI insight generation is event-triggered or explicitly user-triggered, cached safely, and falls back to deterministic summaries when needed.

**Status**
- Pending.

### Phase 8H — Manual QA + Production Readiness Gate

**Purpose**
- Close Phase 8 only after end-to-end AI insight workflow is manually validated.

**Strict scope**
- Manual QA and production readiness evidence only.

**Gates**
- Required manual QA flow is completed and documented:
  - analyst opens match
  - AI insight appears
  - confidence/explanation visible
  - reviewer approves or rejects
  - review state persists
  - coach/player-facing output is blocked until approved
  - no scoring truth is changed
  - no fake data appears
  - frontend builds
  - backend tests pass

**Required tests / validation expectations**
- Manual QA evidence checklist with traceable run artifacts.
- Final CI green status across required frontend/backend gates.

**Completion criteria**
- Manual QA evidence exists, CI passes, no fake data is introduced, and Phase 8 completion report is added.

**Status**
- Pending.

---

# Phase 9 — Player Development Intelligence Foundation

## Product doctrine

> Cricksy must not only help teams win matches. In school and academy settings, Cricksy must help every player improve, especially weaker or overlooked players.

## Core principle

> Every player should leave the season measurably better than they started.

## Existing partial foundations to reuse

- `backend/routes/coach_pro.py` coach-player assignment and coaching session workflows
- `backend/services/ai_player_insights.py` non-authoritative strengths, weaknesses, form, role tags, and recommendations
- existing monthly improvement tracking, training drill suggestions, tactical suggestion engine, dismissal pattern detection, heatmap overlays
- Coach Pro Plus video analysis/reporting pipelines
- Phase 6C Cricksy Skills Architecture governance
- Phase 8C AI Insight Feedback + Review Workflow

## Phase support requirements

- weakest-player uplift
- personalized development plans
- coach-approved AI recommendations
- evidence-based progress tracking
- drill assignments
- progress checkpoints
- video-analysis evidence intake
- school/team improvement visibility
- youth-safe coaching language
- no fake performance claims
- deterministic stats separated from AI recommendations
- organization/player privacy boundaries

### Phase 9A — Pre-Phase Audit + Spec Lock

**Status**
- COMPLETE

Audit existing player, coach, AI insight, drill, video-analysis, and improvement-tracking features before implementation.

**Evidence**
- `docs/PHASE_9A_PLAYER_DEVELOPMENT_INTELLIGENCE_AUDIT_AND_SPEC_LOCK.md`

**Must inspect and document**
- PlayerProfile / PlayerForm models
- CoachPlayerAssignment
- CoachingSession
- AI Player Insights service
- Training Drill Generator
- Monthly Improvement Tracker
- Coach Pro / Coach Pro Plus routes
- Coach video-analysis pipeline
- AI Insight Review workflow
- Analyst Workspace player/match data surfaces
- Frontend player profile and coach dashboard views

**Acceptance criteria**
- Existing partial features documented
- No duplicate player-development system planned
- Data ownership defined
- AI boundary rules defined
- Coach approval rules defined
- Youth-safe wording rules defined
- Org/player access boundaries defined
- Frontend visibility requirements defined
- Documentation only; no runtime behavior changes

Validation notes:

- No backend runtime files changed.
- No frontend runtime files changed.
- No migrations, tests, CI files, or package files changed.
- Phase 9C and later remain future work and are not marked complete.

### Phase 9B — Player Development Data Model

**Status**
- COMPLETE

Future backend foundation for structured player development.

**Required future entities**
- PlayerDevelopmentPlan
- PlayerDevelopmentGoal
- PlayerWeaknessTag
- PlayerStrengthTag
- PlayerDevelopmentIntervention
- PlayerDrillAssignment
- PlayerProgressCheckpoint

**Required future fields/concepts**
- player_profile_id
- coach_user_id
- org_id
- source_type: match_data | video_analysis | coach_note | ai_insight | manual
- weakness_category
- severity
- confidence_score
- coach_approved
- status: draft | active | completed | paused | archived
- evidence_refs
- ai_metadata where applicable
- created_at / updated_at

**Acceptance criteria**
- Alembic migration required in implementation phase
- SQLAlchemy models required in implementation phase
- Pydantic schemas required in implementation phase
- Org/coach/player access boundaries enforced
- AI-generated suggestions cannot mutate official stats
- Tests required for creation, update, permissions, and status transitions

Validation notes:

- Files changed:
  - `backend/sql_app/models.py`
  - `backend/sql_app/schemas.py`
  - `backend/services/player_development_state.py`
  - `backend/alembic/versions/d9b1c2e3f4a5_add_player_development_tables.py`
  - `backend/tests/test_player_development_models.py`
- New entities added:
  - `PlayerDevelopmentPlan`
  - `PlayerDevelopmentGoal`
  - `PlayerWeaknessTag`
  - `PlayerStrengthTag`
  - `PlayerDevelopmentIntervention`
  - `PlayerDrillAssignment`
  - `PlayerProgressCheckpoint`
- Migration:
  - `d9b1c2e3f4a5_add_player_development_tables.py`
- Commands run:
  - `cd backend && python -m pytest tests -k "player_development or development_plan" -v` → 5 passed
  - `cd backend && python -m pytest tests/test_health.py tests/test_results_endpoint.py -q` → 9 passed
  - `cd backend && python -m pytest tests/test_dls_calculations.py -v --tb=short` → 21 passed
  - `cd backend && ruff check .` → passed
  - `cd backend && ruff format --check .` → passed
  - `cd backend && mypy --config-file pyproject.toml --explicit-package-bases .` → passed
  - `cd backend && DATABASE_URL=sqlite:////tmp/phase9b_alembic.sqlite alembic upgrade head` → blocked by a pre-existing SQLite-incompatible `now()` default in older migration `1b13e5e48c1e_add_sponsors_table.py` before Phase 9B migration execution
- Postgres migration validation:
  - Pending in this sandbox. `psql` client is installed, but `pg_isready` reported no local Postgres server response.
- Scope confirmations:
  - No frontend runtime files changed.
  - No official scoring, DLS, results, or player career truth tables were mutated by development-plan creation tests.

### Phase 9C — Development Plan Service + Recommendation Engine

**Status**
- todo

Convert existing AI player insights, drill suggestions, and improvement tracking into a coach-approved development plan.

**Required future behavior**
- Generate draft development plan for a player
- Use existing AI player insights for strengths/weaknesses
- Use existing drill generator for suggested drills
- Use monthly improvement tracker for baseline metrics
- Allow coach to approve/reject/edit AI suggestions
- Preserve AI insight review rules from Phase 8C
- Include limitations, confidence scores, and evidence references

**Acceptance criteria**
- Draft plan generated from real player data only
- No fake drills, fake stats, or fake improvement claims
- Weaknesses map to specific drills
- Plan includes measurable goals
- Plan includes review date/checkpoint
- Coach approval required before activation
- Tests required for plan generation and approval flow

### Phase 9D — Coach Workspace Player Development UI

**Status**
- todo

Make the player-development system visible and usable in the Coach Workspace.

**Required future frontend**
- Assigned players list with development status
- Player development profile
- Strengths and weaknesses panel
- Active goals
- Assigned drills
- Coaching notes/sessions
- Progress checkpoints
- Coach approve/reject/edit AI suggestions
- “Needs attention” indicator for struggling players
- “Improving” indicator for players showing progress

**Acceptance criteria**
- Coach can open assigned player
- Coach can view development plan
- Coach can activate plan
- Coach can assign drills
- Coach can record session outcome
- Weakest/developing players are easy to identify without negative wording
- UI builds successfully in future implementation
- No backend-only feature if it is meant for coach use

### Phase 9E — School / Team Development Dashboard

**Status**
- todo

Give schools and coaches a team-level view of player improvement.

**Required future dashboard sections**
- Team development overview
- Weakest players needing support, framed constructively
- Most improved players
- Players without recent coaching activity
- Common team weaknesses
- Drill completion summary
- Progress by skill category
- Player confidence/mental-readiness indicators if available
- School-safe export/report summary

**Acceptance criteria**
- Coach/org can see all assigned players within permitted scope
- Dashboard separates match performance from player development
- Weak players are framed constructively, not negatively
- Youth-safe language enforced
- Export/report can summarize team improvement

### Phase 9F — Player Development Reports

**Status**
- todo

Generate clear reports for coaches, schools, parents, and players.

**Required future report types**
- Individual player development report
- Team development report
- Before/after improvement report
- Coach session summary
- Drill progress summary

**Acceptance criteria**
- Reports use real data only
- AI-generated recommendations are clearly marked as recommendations
- Reports include strengths, weaknesses, actions taken, progress, and next steps
- Parent/school version uses positive, youth-safe wording
- Coach version can include deeper technical notes

### Phase 9G — Player Development Skill Contract

**Status**
- todo

Register player development as a governed Cricksy Skill family.

**Required future skills**
- player_weakness_detection.v1
- player_development_plan.v1
- drill_recommendation.v1
- progress_checkpoint_summary.v1
- team_development_overview.v1

**Acceptance criteria**
- Each skill follows Phase 6C skill contract
- Required inputs, forbidden inputs, confidence fields, limitations, safety rules, youth safety rules, and review requirements defined
- No skill can overwrite official cricket truth
- Tests required to validate skill metadata in future implementation

---

# Phase 10 — Subscription, Pricing + Tier Enforcement Hardening

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

# Phase 11 — Organization Pro + League Operations

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

# Phase 12 — Live Viewer, Streaming + Sponsor Experience

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

# Phase 13 — Media, Highlights + Report Content Engine

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

# Phase 14 — Lightweight Cricket Supervisor Layer

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

# Phase 15 — Production Scale, Monitoring + Cost Control

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
10. Phase 9 — Player Development Intelligence Foundation
11. Phase 10 — Subscription, Pricing + Tier Enforcement Hardening
12. Phase 11 — Organization Pro + League Operations
13. Phase 12 — Live Viewer, Streaming + Sponsor Experience
14. Phase 13 — Media, Highlights + Report Content Engine
15. Phase 14 — Lightweight Cricket Supervisor Layer
16. Phase 15 — Production Scale, Monitoring + Cost Control

Reason:

Protect the deployed app and CI/CD first. Then stabilize the already-working Coach Pro Plus Video Analysis system before expanding into player development, historical ingestion, governed intelligence architecture, and broader intelligence features.

---

## Post-Phase-6 Alignment Note (Issue #190 — 2026-05-14)

Phase 6A–6H governance is complete. The following ordering clarifications are added here for
alignment. Full audit in `docs/POST_PHASE_6_ORDERING_AND_PHASE_5_AUDIT.md`.

### Phase 5 Completion Status (closure-audit snapshot)

| Sub-Phase | Status |
|---|---|
| Phase 5A (Audit/Spec Lock) | Complete |
| Phase 5B–5G (Core import: dry-run, apply, rollback, apply-deliveries) | Complete |
| Phase 5H (Real-dataset validation QA) | Complete |
| Phase 5I (Upload UI + training retention) | Complete |
| Phase 5J (Metadata accuracy + Cricsheet fixes) | Complete |
| Phase 5K (Legacy backfill + Analyst dark-theme fix) | Complete |
| Phase 5L (Bulk ZIP upload — backend + tests) | Implementation complete; manual QA sign-off pending |
| Phase 5L.1 (Cost-controlled large ZIP intake) | Complete |
| Phase 5M (Cricket Data Registry Foundation) | Complete |
| Phase 5N (Historical Stats Aggregation Layer) | Complete |
| Phase 5O (Analyst Workspace Data Library) | Complete |
| Phase 5P (Model Training Dataset Builder) | Complete |

### Recommended Next Step

With Phase 5N, 5O, and 5P now implemented, the checklist-defined next phase is:

**Phase 7 — Historical Match Ingestion: PDF/Image/OCR Review Flow**

Current readiness evidence and remaining non-blocking follow-up items are tracked in
`docs/PHASE_6F_INTELLIGENCE_OS_CLOSURE_AND_PHASE_7_READINESS.md`.

### Phase Naming Governance Reminder

Per Rule 8 of this checklist: no phase name may be used in issues, PRs, or implementation
plans unless it already exists in this document or is first added through a
checklist-governance PR. The only valid names for the phases after Phase 6 are those listed
above (Phase 5N, 5O, 5P, Phase 7, Phase 8, etc.). "Phase 7A" is not a valid phase name —
it does not exist in this checklist.

---

## Post-Phase-7 Alignment Note (Issue #— 2026-05-15)

Phase 7 core workflow is complete. Remaining OCR enhancement sub-phases are intentionally
deferred until real club/customer onboarding. Full closure details in
`docs/PHASE_7_CLOSURE_AND_OCR_DEFERRAL_NOTE.md`.

### Phase 7 Completion Status (closure snapshot)

| Sub-phase | Status |
|---|---|
| Phase 7 — OCR review candidate workflow | ✅ Complete |
| Phase 7A — Manual QA + operator workflow validation | ✅ Complete |
| Phase 7B — OCR extraction engine audit/spec-lock | ✅ Complete |
| Phase 7C — PDF text extraction for review candidates | ✅ Complete |
| Phase 7D — Tesseract/image OCR audit/spec-lock | ✅ Complete |
| Phase 7E — Optional Tesseract/Image OCR Integration | ⏸ Deferred — pending club onboarding |
| Phase 7F — OCR Ingestion Manual QA + Production Readiness Gate | ⏸ Deferred — depends on Phase 7E |

### Next Active Phase

**Phase 8 — AI Analytics + Match Intelligence Enhancements** is now the next active phase.

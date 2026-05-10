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

## Rule 5 — Deterministic Cricket Truth Protection

AI must never directly own or mutate:

- official score
- balls
- overs
- wickets
- innings state
- match result
- official scorecard
- official player stats

AI may:

- analyze
- recommend
- summarize
- generate coach reports
- explain patterns
- assist with review

## Rule 6 — Migrations Are Controlled

Any DB model change must include:

- Alembic migration in `backend/alembic/versions/`
- Upgrade path
- Downgrade path where reasonable
- Test impact review
- Deployment risk review

Do not edit existing migrations unless fixing a migration that has not been deployed and the user approves.

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

# Phase 5 — Historical Match Ingestion: Structured CSV First

## Purpose

Allow teams/orgs to upload old matches through a safe structured path first.

Start with CSV before OCR/AI parsing.

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

- CSV template
- ingest job schema
- validation errors format
- preview-before-save workflow
- player/team matching rules
- duplicate detection rules
- rollback behavior

## Gates

- CSV imports normalize to existing match structure
- No imported match becomes official without validation
- Bad rows return clear errors
- Duplicate detection exists
- Existing scoring unaffected
- CI passes

## Required Tests

- valid CSV import
- invalid CSV import
- missing headers
- innings total mismatch
- extras mismatch
- duplicate detection
- player matching
- preview save confirmation
- full existing CI gates

## Completion Criteria

Structured historical match import works safely and does not corrupt live scoring data.

---

# Phase 6 — Historical Match Ingestion: PDF/Image/OCR Review Flow

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
- existing CSV import unaffected
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

# Phase 7 — AI Analytics + Match Intelligence Enhancements

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

# Phase 8 — Subscription, Pricing + Tier Enforcement Hardening

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

# Phase 9 — Organization Pro + League Operations

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

# Phase 10 — Live Viewer, Streaming + Sponsor Experience

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

# Phase 11 — Media, Highlights + Report Content Engine

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

# Phase 12 — Lightweight Cricket Supervisor Layer

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

# Phase 13 — Production Scale, Monitoring + Cost Control

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
6. Phase 5 — Historical Match Ingestion: Structured CSV First
7. Phase 6 — Historical Match Ingestion: PDF/Image/OCR Review Flow
8. Phase 7 — AI Analytics + Match Intelligence Enhancements
9. Phase 8 — Subscription, Pricing + Tier Enforcement Hardening
10. Phase 9 — Organization Pro + League Operations
11. Phase 10 — Live Viewer, Streaming + Sponsor Experience
12. Phase 11 — Media, Highlights + Report Content Engine
13. Phase 12 — Lightweight Cricket Supervisor Layer
14. Phase 13 — Production Scale, Monitoring + Cost Control

Reason:

Protect the deployed app and CI/CD first. Then stabilize the already-working Coach Pro Plus Video Analysis system before expanding into player development, historical ingestion, broader intelligence features, and the governed analyst-system roadmap.

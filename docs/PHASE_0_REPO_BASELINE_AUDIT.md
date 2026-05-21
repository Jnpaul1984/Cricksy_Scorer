# PHASE 0 — Repo Baseline Audit (CI/CD Lock)

Repository: `Jnpaul1984/Cricksy_Scorer`
Default branch: `main`
Checklist source: `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`

This is a baseline audit for the **existing Cricksy application**. It is **not** a rebuild plan.

---

## 1) Existing CI/CD Workflow Summary

Current workflow files under `.github/workflows/`:

- `ci.yml`
- `lint.yml`
- `deploy-backend.yml`
- `deploy-frontend.yml`
- `release.yml`
- `copilot-agent-run.yml`

### `ci.yml` (main quality gate)
- Triggers:
  - `push` to `main`, `agent/**`, `feature/**`
  - `pull_request` to `main`
- Path ignore: docs/markdown-only changes are excluded (`**.md`, `docs/**`, `.mcp/**`)
- Jobs:
  - `pre-commit` (double pass)
  - `lint` (ruff + format-check + mypy)
  - `security` (pip-audit + bandit)
  - `backend-tests` (fast tests)
  - `backend-integration-tests`
  - `backend-dls-tests`
  - `frontend-build` (guard + type-check + production build)

### `lint.yml`
- Separate lint workflow on push/PR to `main` (same docs path-ignore)
- Runs backend Ruff + Ruff format check + MyPy

### `deploy-backend.yml`
- Triggers on `push` to `main` and manual dispatch
- Ignores docs-only and frontend-only path changes
- Stages:
  1. Postgres-backed backend test job + Alembic migration check
  2. Build/push image to ECR + vulnerability scan gate
  3. ECS deploy (backend service), one-off migration task, then worker deploy

### `deploy-frontend.yml`
- Triggers on `push` to `main` and manual dispatch
- Builds `frontend/` and deploys Firebase Hosting via `firebase deploy --only hosting`

### `release.yml`
- Triggers on version tags `v*`
- Builds/pushes Docker image to GHCR (`ghcr.io/Jnpaul1984/cricksy_scorer`)

### `copilot-agent-run.yml`
- Manual workflow-dispatch job to run `.github/scripts/copilot_agent_runner.py`

---

## 2) Exact Backend Validation Commands

Primary backend validation commands currently used by CI/checklist:

```bash
# from repo root
pre-commit run --all-files
ruff check .
ruff format --check .

# from backend/
cd backend && mypy --config-file pyproject.toml --explicit-package-bases .

# backend fast tests (in-memory)
cd backend && pytest -q tests/test_health.py tests/test_results_endpoint.py

# backend integration tests
cd backend && pytest tests/integration/ -v --tb=short --cov=. --cov-report=xml --cov-report=term

# DLS-focused tests
cd backend && pytest tests/test_dls_calculations.py -v --tb=short
```

Required CI-style env for backend tests:

```bash
CRICKSY_IN_MEMORY_DB=1
DATABASE_URL=sqlite+aiosqlite:///:memory:?cache=shared
APP_SECRET_KEY=test-secret-key
PYTHONPATH=<repo-root>
```

---

## 3) Exact Frontend Validation Commands

Frontend validation commands currently used by CI/checklist:

```bash
cd frontend && npm ci
cd frontend && npm run guard:fake-data
cd frontend && npm run type-check
cd frontend && npm run build-only
```

CI build env:

```bash
VITE_API_BASE=http://localhost:8000
```

---

## 4) Existing Deployment Workflow Summary

### Backend deployment path
- Workflow: `.github/workflows/deploy-backend.yml`
- Deploy target: AWS ECR + ECS (`cricksy-ai-backend-service`, `cricksy-ai-worker-service`)
- Flow:
  1. Validate backend in GitHub Actions with Postgres service
  2. Run Alembic migrations check (`alembic -c backend/alembic.ini upgrade head`)
  3. Build and push ECR image
  4. Block deploy if ECR scan finds non-kernel HIGH/CRITICAL vulnerabilities
  5. Register new task definition
  6. Run one-off ECS migration task
  7. Update ECS backend service and wait for stabilization
  8. Update ECS analysis worker service with same image + worker command

### Frontend deployment path
- Workflow: `.github/workflows/deploy-frontend.yml`
- Deploy target: Firebase Hosting
- Flow:
  1. `npm ci || npm install`
  2. `npm run build` with production API/socket env values
  3. `firebase deploy --only hosting --non-interactive`

### Container release path
- Workflow: `.github/workflows/release.yml`
- Trigger: tag push matching `v*`
- Publishes Docker image to GHCR with tag and `latest`

---

## 5) Protected Files List

Per `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` (Rule 7), protected production-sensitive areas:

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
- Scoring/result endpoints and tests
- DLS calculation logic

Protected means: audit first, spec lock, targeted edits only, and regression validation.

---

## 6) Existing Coach Pro Plus Video Analysis File Map

Existing Coach Pro Plus video analysis footprint (repo-grounded):

### Core backend runtime
- `backend/services/coach_plus_analysis.py`
- `backend/services/pose_service.py`
- `backend/services/sqs_service.py`
- `backend/workers/analysis_worker.py`
- `backend/scripts/run_video_analysis_worker.py`
- `backend/mediapipe_init.py`

### Frontend integration
- `frontend/src/services/coachPlusVideoService.ts`
- `frontend/src/stores/coachPlusVideoStore.ts`

### Data/migrations
- Video-analysis-related migrations in `backend/alembic/versions/`

### Key docs/manifests already in repo
- `COACH_PRO_PLUS_VIDEO_ANALYSIS_FILE_MANIFEST.txt`
- `COMPLETE_VIDEO_ANALYSIS_FLOW.md`
- `README_COACH_PRO_PLUS_VIDEO_MVP.md`
- `TESTING_GUIDE_COACH_VIDEO.md`
- `COACH_PRO_PLUS_VIDEO_SESSIONS_SCAFFOLDING.md`
- `COACH_PRO_PLUS_VIDEO_SESSIONS_READY.md`
- `COACH_PRO_PLUS_VIDEO_SESSIONS_QUICK_REF.md`
- `COACH_REPORT_V2_README.md`
- `docs/ANALYSIS_MODE_ENFORCEMENT.md`

**Lock rule:** Do not replace the existing Coach Pro Plus model/pipeline; only harden/extend safely.

---

## 7) Migration Rules

Migration policy from checklist Rule 6:

1. Any DB model change must include an Alembic migration in `backend/alembic/versions/`.
2. Provide upgrade path (and downgrade where reasonable).
3. Include test impact review and deployment risk review.
4. Do **not** edit existing migrations unless fixing an undeployed migration with explicit approval.

---

## 8) Known Risks

1. **Docs-only CI bypass risk**: `.github/workflows/ci.yml` ignores docs-only changes, so process errors in docs can merge without CI feedback.
2. **Environment parity risk**: local `make ci` enforces exact runtime versions (`Python 3.12.12`, `Node 20.18.1`); mismatches can block local validation.
3. **Frontend dependency install risk in restricted networks**: Cypress binary download can fail in locked environments unless `CYPRESS_INSTALL_BINARY=0` is used.
4. **Deployment complexity risk**: backend deploy includes ECR scan, ECS task definition registration, one-off migration task, and worker rollout; failures can occur at multiple handoff points.
5. **Production-sensitive surface area risk**: scoring logic, DLS, and Coach Pro Plus analysis pipeline are tightly coupled and must be guarded by targeted regression checks.

---

## 9) Recommended Phase 1 Starting Point

Start exactly from **Phase 1 — Existing App Stabilization + Regression Protection** in `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`.

Recommended first execution slice:

1. Audit current behavior for:
   - health endpoint
   - result endpoint
   - scoring event flow
   - DLS calculations
   - viewer sync + fake-data guard
2. Write Phase 1 spec lock with explicit “must not change” contracts.
3. Run baseline regression commands before edits:
   - backend fast tests
   - integration tests
   - DLS tests
   - frontend guard/type-check/build
4. Apply only targeted fixes to stabilize existing behavior.

**Non-negotiable preservation rules for Phase 1 and beyond:**
- Do not rebuild Cricksy.
- Do not replace Coach Pro Plus Video Analysis model/pipeline behavior.

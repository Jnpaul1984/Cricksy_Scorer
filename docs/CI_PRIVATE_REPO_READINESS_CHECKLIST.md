# CI / Private Repo Readiness Checklist

- [x] **Backend tests** run with explicit in-memory async DB env (`CRICKSY_IN_MEMORY_DB`, `DATABASE_URL`, `APP_SECRET_KEY`, `PYTHONPATH`).
- [x] **Async DB teardown hardening**: backend `db_session` fixture now tolerates SQLite `"no active connection"` during teardown rollback/close.
- [x] **Frontend build CI** disables Cypress binary install for non-E2E build jobs (`CYPRESS_INSTALL_BINARY=0`).
- [x] **Frontend build dependencies** explicitly verify `sharp` is present in CI (`npm ls sharp --depth=0`).
- [x] **CI deploy-parity validation** runs branch-safe backend deploy checks (dependency install, Alembic upgrade, backend startup import, `pytest -v`) without production deploy secrets.
- [x] **CI deploy-parity validation** runs branch-safe frontend deploy checks (`npm ci` with `CYPRESS_INSTALL_BINARY=0`, `npm run build`, and `frontend/dist/index.html` artifact validation).
- [x] **Deploy Backend** secret validation is restricted to production mutation jobs (`build-and-scan` / `deploy`), not branch-safe validation jobs.
- [x] **Deploy Frontend** secret validation is restricted to the Firebase deploy stage.
- [x] **Deploy Frontend** validates build artifacts (`frontend/dist/index.html`) before deployment.
- [x] **Workflow permissions** are explicit (`contents: read` on deploy frontend; backend deploy already declares permissions).
- [x] **Manual trigger safety** exists for both deploy workflows (`workflow_dispatch` present).
- [x] **`deploy-backend.yml` trigger boundary**: `deploy-backend.yml` triggers only on `push: [main]` and `workflow_dispatch`. It does **not** trigger on `pull_request` and therefore never creates a PR-required status check. All pre-merge validation is handled by the `CI` workflow's `Backend (deploy validation parity)` job.
- [x] **`deploy-backend.yml` is deploy-only**: The `test-backend-postgres` pre-deploy test job has been removed from `deploy-backend.yml`. All branch-safe validation commands (Alembic upgrade, pytest, import checks) are exclusively handled in the CI workflow using dummy/test credentials, not in the deploy workflow.

## Branch protection guidance

**Require these CI workflow checks:**

| Check name | Workflow | Required? |
|---|---|---|
| `Backend (deploy validation parity)` | `CI` | ✅ Yes — mirrors deploy commands with dummy secrets |
| `Frontend (build + type-check)` | `CI` | ✅ Yes — mirrors frontend deploy build |
| `Lint (ruff + ruff format + mypy)` | `CI` | ✅ Recommended |
| `Security (bandit + pip-audit)` | `CI` | ✅ Recommended |
| `Pre-commit (all files)` | `CI` | ✅ Recommended |

**Do NOT require these workflow checks:**

| Check name | Workflow | Why not |
|---|---|---|
| `Build and Scan ECR Image` | `Deploy Backend` | Post-merge only; requires `AWS_GITHUB_DEPLOY_ROLE_ARN` production secret |
| `Deploy Backend` | `Deploy Backend` | Post-merge only; requires `APP_SECRET_KEY` + `AWS_GITHUB_DEPLOY_ROLE_ARN` production secrets |
| `deploy-frontend` | `Deploy Frontend` | Post-merge only; requires `FIREBASE_TOKEN` production secret |

**Key rule**: Only require checks from the `CI` workflow (triggered by `pull_request`). Never require checks from `Deploy Backend` or `Deploy Frontend` workflows, which run post-merge on `push: [main]` and will fail safely if production secrets are not configured.

Deploy workflows are intentionally designed to fail with a clear error message when production secrets are absent, so that misconfigured environments are caught before reaching production. This is correct behavior and not a CI failure.

## Required repository secrets

- `APP_SECRET_KEY`
- `AWS_GITHUB_DEPLOY_ROLE_ARN`
- `FIREBASE_TOKEN`

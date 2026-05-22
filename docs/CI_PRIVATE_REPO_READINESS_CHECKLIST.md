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

## Branch protection guidance

- Require CI deploy-parity checks as merge gates (at minimum `Backend (deploy validation parity)` and `Frontend (build + type-check)` under the `CI` workflow).
- Do **not** require production deploy workflows (`Deploy Backend`, `Deploy Frontend`) as branch protection checks.
- Deploy workflows may still fail safely when manually triggered without required deployment secrets.

## Required repository secrets

- `APP_SECRET_KEY`
- `AWS_GITHUB_DEPLOY_ROLE_ARN`
- `FIREBASE_TOKEN`

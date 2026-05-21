# CI / Private Repo Readiness Checklist

- [x] **Backend tests** run with explicit in-memory async DB env (`CRICKSY_IN_MEMORY_DB`, `DATABASE_URL`, `APP_SECRET_KEY`, `PYTHONPATH`).
- [x] **Async DB teardown hardening**: backend `db_session` fixture now tolerates SQLite `"no active connection"` during teardown rollback/close.
- [x] **Frontend build CI** disables Cypress binary install for non-E2E build jobs (`CYPRESS_INSTALL_BINARY=0`).
- [x] **Frontend build dependencies** explicitly verify `sharp` is present in CI (`npm ls sharp --depth=0`).
- [x] **Deploy Backend** fails early when required secrets are missing (`APP_SECRET_KEY`, `AWS_GITHUB_DEPLOY_ROLE_ARN`).
- [x] **Deploy Frontend** fails early when `FIREBASE_TOKEN` is missing.
- [x] **Deploy Frontend** validates build artifacts (`frontend/dist/index.html`) before deployment.
- [x] **Workflow permissions** are explicit (`contents: read` on deploy frontend; backend deploy already declares permissions).
- [x] **Manual trigger safety** exists for both deploy workflows (`workflow_dispatch` present).

## Required repository secrets

- `APP_SECRET_KEY`
- `AWS_GITHUB_DEPLOY_ROLE_ARN`
- `FIREBASE_TOKEN`

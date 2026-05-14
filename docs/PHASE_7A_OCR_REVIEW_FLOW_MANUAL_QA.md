# Phase 7A — OCR Review Flow Manual QA

- Date: 2026-05-14
- Tester: Copilot
- Recommendation: **Ready to proceed**
- Classification: **Code-touching, low-risk operator UX polish + QA report**

## Environment used

- Repository: `Jnpaul1984/Cricksy_Scorer`
- Workspace: `/home/runner/work/Cricksy_Scorer/Cricksy_Scorer`
- OS: GitHub-hosted Ubuntu runner
- Python: `3.12.3`
- Node: `v24.14.1`
- Backend runtime for manual QA:
  - `DATABASE_URL=sqlite+aiosqlite:////tmp/phase7a/phase7a.db`
  - `APP_SECRET_KEY=test-secret-key`
  - `CRICKSY_ENV=dev`
  - `PYTHONPATH=/home/runner/work/Cricksy_Scorer/Cricksy_Scorer`
  - backend served at `http://127.0.0.1:8000`
- Frontend runtime for manual QA:
  - preview served at `http://127.0.0.1:3000`
  - runtime API override via `?apiBase=http://127.0.0.1:8000`
- Analyst-capable test account:
  - `qa-analyst@example.com`
  - role: `org_pro`
- Safe local sample files:
  - `/tmp/phase7a/sample_scorecard.pdf`
  - `/tmp/phase7a/sample_scorecard.png`
  - `/tmp/phase7a/unsupported.txt`
  - `/tmp/phase7a/oversized.pdf`
  - `/tmp/phase7a/valid_candidate.json`
  - `/tmp/phase7a/malformed_review.json`

## Tiny operator fixes made during QA

Two small operator-facing gaps were found during the manual pass and fixed in this PR:

1. The OCR panel did not show an explicit empty/loading state.
2. The dry-run button remained clickable in UI states where operators should not be able to continue (for example after rejection).

Low-risk polish added:

- explicit empty-state copy
- explicit loading-state copy
- dry-run gating until review is ready
- dry-run disabled again after rejection
- clearer malformed JSON error prefix (`Invalid structured JSON: ...`)
- focused frontend unit coverage for the OCR review panel

## Commands run

### Backend

```bash
cd backend
ruff check .
ruff format --check .
mypy --config-file pyproject.toml --explicit-package-bases .
pytest -q tests/test_health.py tests/test_results_endpoint.py
pytest tests/integration/ -v --tb=short
pytest tests/test_dls_calculations.py -v --tb=short
pytest tests/test_historical_ocr_review_flow.py -v --tb=short
```

Result:

- `ruff check .` ✅
- `ruff format --check .` ✅
- `mypy --config-file pyproject.toml --explicit-package-bases .` ✅
- `pytest -q tests/test_health.py tests/test_results_endpoint.py` ✅
- `pytest tests/integration/ -v --tb=short` ✅
- `pytest tests/test_dls_calculations.py -v --tb=short` ✅
- `pytest tests/test_historical_ocr_review_flow.py -v --tb=short` ✅

### Frontend

```bash
cd frontend
CYPRESS_INSTALL_BINARY=0 npm ci
npm run guard:fake-data
npm run test:unit -- HistoricalOcrReviewPanel.spec.ts
npm run type-check
npm run build-only
npm run test:e2e:smoke
npm run test:e2e:import
```

Result:

- `CYPRESS_INSTALL_BINARY=0 npm ci` ✅
- `npm run guard:fake-data` ✅ (3 existing warning-only `Math.random()` notices in `DevDashboardWidget.vue`; no new errors)
- `npm run test:unit -- HistoricalOcrReviewPanel.spec.ts` ✅
- `npm run type-check` ✅
- `npm run build-only` ✅
- `npm run test:e2e:smoke` ❌ local blocker
- `npm run test:e2e:import` ❌ local blocker

Local Cypress blocker:

- `npx cypress install` failed with `getaddrinfo ENOTFOUND download.cypress.io`
- This environment could not download the Cypress binary
- The blocker is environmental, not an application error

GitHub Actions evidence reviewed:

- Latest successful main CI run: `25890991439` (`CI`) ✅
- Latest successful main lint run: `25890991450` (`Lint`) ✅
- Jobs in successful CI run included:
  - `Frontend (build + type-check)` ✅
  - `Frontend (analyst workspace E2E)` ✅
  - backend fast/integration/DLS jobs ✅

Note: the import-specific Cypress spec exists in-repo (`frontend/cypress/e2e/historical_import_review_flow.cy.ts`) but could not be executed locally because the Cypress binary download was blocked in this runner.

## Manual operator walkthrough

Validated flow:

```text
Analyst Workspace
→ Import Data
→ Import from PDF/Image (Review Required)
→ create/upload OCR review candidate
→ inspect candidate preview
→ edit/correct structured JSON candidate
→ run dry-run validation
→ verify dry-run result display
→ reject candidate path
→ confirm rejected candidate cannot be dry-run/applied
```

Observed highlights:

- Analyst Workspace loaded successfully after authenticating with an `org_pro` test user.
- Import Data tab showed the JSON import panel, bulk ZIP panel, and OCR review panel together.
- OCR panel copy clearly stated that OCR/AI extraction is non-authoritative and must be reviewed first.
- PDF upload created a `needs_review` candidate successfully.
- Malformed JSON correction failed with a clear operator-facing parse message.
- Valid reviewed JSON moved the candidate to `ready_for_dry_run`.
- A deliberately incomplete JSON payload failed dry-run with visible validation errors (`MISSING_INNINGS`).
- A valid fixture payload dry-run passed and produced a structured handoff batch id without creating any official match rows.
- Image upload created a candidate successfully.
- Rejection reason remained visible after reject.
- Rejected candidates were blocked from dry-run/apply.

Additional API safety spot-checks:

- `GET /games/results` remained at `0` before and after OCR candidate creation/dry-run in the local QA environment.
- `GET /analytics/matches` remained empty before apply, confirming no official match surfaced from OCR intake alone.
- `GET /api/historical-import/json/batches/{batch_id}/training-status` returned:
  - `training_eligible=false`
  - `exclusion_reason=batch_not_finalized`
  - `applied_game_id=null`

## Manual QA checklist

### UI Access + Navigation

- [x] Analyst Workspace loads.
- [x] Import Data tab/section is visible.
- [x] OCR/PDF/Image review panel is visible.
- [x] Panel copy clearly says review is required before import.
- [x] Existing JSON/ZIP import panels still work/are still visible.

### Candidate Creation

- [x] Valid PDF upload candidate is accepted.
- [x] Valid image upload candidate is accepted.
- [x] Unsupported file type is rejected with a clear message.
- [x] Oversized upload is rejected with a clear message.
- [x] Candidate status is visible after creation.
- [x] Candidate is clearly labelled non-authoritative.

### Review + Correction

- [x] Candidate preview renders.
- [x] Corrected JSON/input can be edited.
- [x] Malformed correction JSON is rejected clearly.
- [x] Valid correction JSON is accepted.
- [x] Candidate moves to reviewed/ready state only after valid correction.
- [x] Confidence/uncertainty wording is understandable.

### Dry-Run Handoff

- [x] Reviewed candidate can run historical JSON dry-run validation.
- [x] Dry-run success displays clearly.
- [x] Dry-run failure displays validation errors clearly.
- [x] Dry-run does not create official match data.
- [x] Apply/import is not automatic.
- [x] Flow makes it clear existing structured import validation is still required.

### Rejection Flow

- [x] Candidate can be rejected with a reason.
- [x] Rejected candidate shows rejected status.
- [x] Rejected candidate cannot be dry-run/applied.
- [x] Rejection reason remains visible.

### Safety + Governance

- [x] OCR/AI output is never presented as official truth.
- [x] No official match appears before explicit structured import apply.
- [x] No training-ready status is granted from OCR candidate alone.
- [x] Existing deterministic cricket truth behavior is unaffected.
- [x] Existing Analyst Workspace Data Library still loads.
- [x] Existing frontend E2E smoke gates remain green in GitHub Actions; local Cypress execution was blocked by binary download failure.

### Error / Empty / Loading States

- [x] Loading state support is present during upload/create.
- [x] Loading state support is present during dry-run.
- [x] API failure paths show clear error messages (`415`, `413`, `409` paths verified).
- [x] Empty candidate state is understandable.
- [x] Retry path is clear.

## Screenshot notes

Screenshots were captured locally during QA and kept out of the repository:

- `/tmp/phase7a/screens/01-analyst-workspace.png`
  - Analyst Workspace shell loaded with authenticated analyst-capable user
- `/tmp/phase7a/screens/02-import-panels.png`
  - Import Data tab showing JSON import, bulk ZIP import, and OCR review panels together
- `/tmp/phase7a/screens/03-pdf-candidate-created.png`
  - PDF-based OCR review candidate created in `needs_review`
- `/tmp/phase7a/screens/04-dry-run-result.png`
  - Dry-run failure path with visible validation error messaging
- `/tmp/phase7a/screens/05-rejected-candidate.png`
  - Rejected image candidate with rejection reason still visible
- `/tmp/phase7a/screens/06-dry-run-pass.png`
  - Successful dry-run handoff with explicit non-auto-apply messaging

## Issues found

No remaining blocking issues were found after the low-risk operator polish noted above.

Resolved in this PR:

- OCR panel now exposes explicit empty/loading copy for operators.
- OCR panel no longer invites dry-run from invalid UI states.
- Malformed JSON errors now read as structured-input errors instead of a raw parse-only failure.

## Follow-up issues

- None created from this QA pass.
- No additional blocking bug or workflow-risk issue was required after the low-risk fixes in this PR.

## Safety confirmations

- No official cricket truth behavior was changed.
- No OCR candidate auto-apply behavior was introduced.
- Rejected candidates remain blocked.
- Dry-run handoff remains review-only and still requires explicit structured import apply.
- OCR-derived data is still non-authoritative and not training-ready on candidate creation/dry-run alone.

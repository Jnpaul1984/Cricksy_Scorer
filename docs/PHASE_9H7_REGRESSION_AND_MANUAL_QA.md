# Phase 9H.7 — Regression + Manual QA
## Closeout Evidence

Date (UTC): 2026-05-17
Repository: `Jnpaul1984/Cricksy_Scorer`
Issue: Phase 9H.7 — Regression + Manual QA

---

## 1) Scope and closeout decision

Phase 9H.7 validation is **complete**.

This closeout run stayed within allowed scope:

- documented regression/manual-QA evidence
- updated the Phase 9H checklist status
- applied one minimal validation blocker fix in the Phase 9H.5 UI path so authorized `org_pro` reviewers can access the video sessions review surface
- added one focused frontend regression test for that blocker

No AI generation, LLM behavior, video-analysis pipeline behavior, migrations, CI workflows, package files, or infrastructure files were changed.

---

## 2) Bug found during validation

Status: **FIXED**

Bug:

- `frontend/src/views/CoachProPlusVideoSessionsView.vue` used `!authStore.isCoach` for the page-level feature gate.
- `authStore.isCoach` excludes `org_pro`, so authorized Org Pro reviewers were shown the upgrade gate instead of the video sessions workspace.

Fix:

- Updated the page-level gate to `!authStore.canCoach`.
- Added `frontend/tests/unit/CoachProPlusVideoSessionsView.spec.ts` to verify:
  - authorized `org_pro` users see the video sessions workspace
  - non-coach users still see the upgrade gate

---

## 3) Regression commands and results

### Backend

Executed from `backend/` with:

- `PYTHONPATH=/home/runner/work/Cricksy_Scorer/Cricksy_Scorer`
- `CRICKSY_IN_MEMORY_DB=1`
- `APP_SECRET_KEY=test-secret-key`

Commands:

```bash
python -m pytest -q \
  tests/test_coaching_video_evidence_skill_contract.py \
  tests/test_video_evidence_to_skill_input_mapping.py \
  tests/test_player_development_approval_gate.py \
  tests/test_player_development_recommendation_output.py \
  tests/test_coaching_skill_audit_log.py \
  tests/test_player_development_routes.py \
  tests/test_player_development_reports.py

ruff check .
ruff format --check .
mypy --config-file pyproject.toml --explicit-package-bases .
```

Results:

- backend pytest regression slice: **pass**
- `ruff check .`: **pass**
- `ruff format --check .`: **pass**
- `mypy --config-file pyproject.toml --explicit-package-bases .`: **pass**
- observed warnings were pre-existing/non-blocking deprecations from dependencies and framework constants; no new regression failure found

### Frontend

Executed from `frontend/`:

```bash
CYPRESS_INSTALL_BINARY=0 npm ci
npm run guard:fake-data
npm run type-check
npm run build-only
npm run test:unit -- CoachProPlusVideoSessionsView.spec.ts CoachingSkillRecommendationReviewCard.spec.ts
```

Results:

- `CYPRESS_INSTALL_BINARY=0 npm ci`: **pass**
  - required because Cypress binary download is blocked in this sandbox; this does not affect the requested non-Cypress validation commands
- `guard:fake-data`: **pass with warnings only**
  - known warning-only `Math.random()` detections remain in `frontend/src/components/DevDashboardWidget.vue`
  - 0 errors
- `type-check`: **pass**
- `build-only`: **pass**
- targeted unit tests: **pass**
  - Test Files: 2 passed
  - Tests: 6 passed

---

## 4) Migration validation

Commands:

```bash
cd backend
alembic heads
DATABASE_URL=postgresql+asyncpg://postgres:RubyAnita2018@127.0.0.1:5555/cricksy_scorer alembic upgrade head
```

Environment/result:

- Real Postgres validation was run locally via Docker Compose (`docker compose up -d db`) against the repo Postgres service on `127.0.0.1:5555`.
- `alembic heads`: **pass**
  - single head: `d7e9a4b6c1f2 (head)`
- `alembic upgrade head` against Postgres: **pass**
- Phase 9H.6 migration `d7e9a4b6c1f2_add_coaching_skill_audit_logs_table` applied successfully in sequence after the prior migration chain.

Production-readiness note:

- This satisfies the Phase 9H.7 requirement to validate migrations against real Postgres, not only SQLite/in-memory test configuration.

---

## 5) Manual QA evidence

> Evidence format: text-based UI evidence + targeted unit tests + backend route/report/audit tests + runtime command output.
> Screenshots were not practical in this authenticated CI-style sandbox; validation is traceable via source, tests, and command results.

### A. Coach Pro Plus UI

Status: **PASS**

Validated evidence:

- Coach-facing video sessions page exists and renders the governed review workspace:
  - `frontend/src/views/CoachProPlusVideoSessionsView.vue`
- Authorized `org_pro` reviewers now reach the workspace instead of the upgrade gate:
  - `frontend/src/views/CoachProPlusVideoSessionsView.vue`
  - `frontend/tests/unit/CoachProPlusVideoSessionsView.spec.ts`
- Completed/done jobs surface governed recommendation review cards:
  - `frontend/src/views/CoachProPlusVideoSessionsView.vue`
  - `frontend/src/components/CoachingSkillRecommendationReviewCard.vue`
- Queued/processing jobs show safe not-yet-eligible messaging:
  - `frontend/src/views/CoachProPlusVideoSessionsView.vue`
- Failed jobs show safe not-reviewable messaging:
  - `frontend/src/views/CoachProPlusVideoSessionsView.vue`
- Sessions with no linked player IDs show safe no-linked-plan messaging:
  - `frontend/src/views/CoachProPlusVideoSessionsView.vue`
- Completed jobs with no linked recommendation show explicit awaiting-recommendation messaging:
  - `frontend/src/views/CoachProPlusVideoSessionsView.vue`
- Pending/approved/rejected/changes-requested states render explicit labels and visibility language:
  - `frontend/src/components/CoachingSkillRecommendationReviewCard.vue`
  - `frontend/src/views/CoachProPlusVideoSessionsView.vue`
- Governed review card renders advisory visibility notice, evidence references, and latest review state:
  - `frontend/tests/unit/CoachingSkillRecommendationReviewCard.spec.ts`

### B. Review actions / RBAC

Status: **PASS**

Validated evidence:

- Coach Pro Plus can approve/reject/request changes:
  - `backend/tests/test_player_development_approval_gate.py`
- Org Pro can approve where authorized:
  - `backend/tests/test_player_development_approval_gate.py`
  - `frontend/tests/unit/CoachProPlusVideoSessionsView.spec.ts`
- Unauthorized roles receive backend `403`:
  - `backend/tests/test_player_development_approval_gate.py`
- Cross-org access is rejected:
  - `backend/tests/test_player_development_approval_gate.py`
- Reviewing archived plans returns `409`:
  - `backend/tests/test_player_development_approval_gate.py`
- Safe UI review error messaging exists for `403`, `404`, `409`, and validation errors:
  - `frontend/src/views/CoachProPlusVideoSessionsView.vue`

### C. Player-facing safety

Status: **PASS**

Validated evidence:

- Approved + coach-approved recommendations appear player-facing:
  - `backend/tests/test_player_development_recommendation_output.py`
- Pending / rejected / changes requested recommendations do not appear player-facing:
  - `backend/tests/test_player_development_recommendation_output.py`
- Player-facing approval gate is enforced in service code:
  - `backend/services/player_development_report_service.py`
- Raw `ai_metadata` is not exposed player-facing:
  - `backend/services/player_development_report_service.py`
  - `backend/tests/test_player_development_recommendation_output.py`
- Raw evidence marker JSON is reduced to safe `{type, label}` summaries player-facing:
  - `backend/services/player_development_report_service.py`
  - `backend/tests/test_player_development_recommendation_output.py`
- Coach notes and next coach actions are not exposed player-facing:
  - `backend/tests/test_player_development_recommendation_output.py`

### D. Audit log safety

Status: **PASS**

Validated evidence:

- Approve / reject / changes-requested actions write governed audit events:
  - `backend/services/coaching_skill_audit_service.py`
  - `backend/tests/test_coaching_skill_audit_log.py`
- Audit records include plan/player/reviewer/video identifiers when available:
  - `backend/services/coaching_skill_audit_service.py`
  - `backend/tests/test_coaching_skill_audit_log.py`
- Audit records strip raw frames, prompts, tokens, and unsafe payload fields:
  - `backend/services/coaching_skill_audit_service.py`
  - `backend/tests/test_coaching_skill_audit_log.py`
- Audit persistence failure does not silently approve a plan:
  - `backend/routes/player_development.py`
  - `backend/tests/test_coaching_skill_audit_log.py`

### E. Cricket truth safety

Status: **PASS**

Validated evidence:

- Review action does not mutate plan evidence refs or AI metadata:
  - `backend/tests/test_player_development_approval_gate.py`
  - `backend/tests/test_coaching_skill_audit_log.py`
- Review action does not mutate official player stats / cricket truth fields:
  - `backend/tests/test_player_development_approval_gate.py`
  - `backend/tests/test_coaching_skill_audit_log.py`
- Player-development reports remain advisory-only and explicitly do not change official match statistics, rankings, or selection decisions:
  - `backend/services/player_development_report_service.py`

---

## 6) CI / PR check snapshot

GitHub PR check status reviewed for PR #273:

- active check run at inspection time: `copilot` — **in progress**

Relevant workflow configuration:

- `.github/workflows/ci.yml` ignores docs-only changes via `paths-ignore` for `**.md`, `docs/**`, and `.mcp/**`
- `.github/workflows/lint.yml` does the same

Current closeout note:

- this validation branch is **not docs-only** because it includes the minimal frontend gate fix and a focused unit test, so CI/lint PR checks remain applicable after push
- local validation commands above passed and are the concrete regression evidence gathered in this sandbox run

---

## 7) Remaining limitations / follow-ups

1. Frontend fake-data guard still reports the known warning-only `Math.random()` usages in `frontend/src/components/DevDashboardWidget.vue`; no error/blocker was introduced by Phase 9H.7.
2. Backend pytest output still includes pre-existing dependency/framework deprecation warnings; no new failing regression was introduced in this closeout.
3. GitHub PR checks were still running at the time of the last status snapshot, so this document records the live status rather than claiming completed remote CI.

---

## 8) Final governance confirmations

- AI generation / LLM behavior changed: **no**
- Coach Pro Plus video-analysis runtime pipeline changed: **no**
- Skill orchestration behavior changed: **no**
- New migration added: **no**
- Unauthorized player-facing recommendation exposure found: **no**
- Raw `ai_metadata` exposed player-facing: **no**
- Raw evidence marker JSON exposed player-facing: **no**
- Coach notes/internal actions exposed player-facing: **no**
- Audit logging confirmed for review decisions: **yes**
- Official scoring, match result, DLS, scorecards, innings state, and player stats mutation introduced: **no**
- No Claw Studio references introduced: **confirmed**

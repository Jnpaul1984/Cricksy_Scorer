# PHASE 1D — Open PR Triage + Checklist Numbering Cleanup

**Repository:** `Jnpaul1984/Cricksy_Scorer`  
**Date:** 2026-05-10  
**Scope:** Governance/docs only. No app code, workflow, migration, or dependency edits in this phase.

---

## 1) Current Open PR Inventory

Open PR inventory was collected from GitHub (state=`open`) and includes **17** PRs at triage time.

- High-risk or very-high-risk pre-governance PRs: **13**
- Medium-risk pre-governance PRs: **2**
- Low-risk pre-governance PRs: **1**
- Current governed Phase 1D docs PR: **1**

---

## 2) Per-PR Triage (Governance-First)

| PR | Title | Changed areas (from PR body + changed files) | Risk | Governance status | Recommendation | Reason |
|---|---|---|---|---|---|---|
| #101 | [WIP] Perform phase 1D PR triage and checklist numbering cleanup | Docs-only checklist/triage scope; no app-code files in current state | low | compliant | keep | Directly implements governed Phase 1D docs task. |
| #50 | ci: add ECR image scanning with HIGH/CRITICAL failure threshold; fix AWS CLI output flags | `.github/workflows/deploy-backend.yml`, `backend/Dockerfile` | high | needs split | split into smaller governed issues | Infra/deploy hardening mixed with security scanning; high blast radius and overlaps #49. |
| #49 | Fix ECR vulnerability scanning and AWS CLI syntax in deploy workflow | `.github/workflows/deploy-backend.yml`, `backend/Dockerfile` | high | needs split | split into smaller governed issues | Similar to #50; deployment/security changes should be reissued as narrow governed infra tasks. |
| #45 | alembic: merge parallel heads and update CI to use 'upgrade heads' | Alembic revisions + workflow, plus broad extra file changes (`backend/`, artifacts, tools, workflows) | very high | unsafe | do not merge | Title implies 2 files, but actual diff is very broad and unsafe to merge blind. |
| #44 | Add upload pipeline with OCR worker and WebSocket hardening | `backend/routes/uploads.py`, `backend/worker/*`, `backend/services/live_bus.py`, migrations, frontend upload views/store, docs | very high | unsafe | split into smaller governed issues | Large multi-domain pre-governance feature bundle (upload/OCR/WebSocket) across backend+frontend+migrations+deps. |
| #43 | Add upload pipeline with OCR worker, frontend UI, and WebSocket delta compression | Upload/OCR worker stack, websocket delta logic, migration, frontend upload/review flow, dependencies/docs | very high | unsafe | split into smaller governed issues | Same broad stream as #40/#41/#42/#44; cannot be merged as one pre-governance batch. |
| #42 | Implement upload pipeline, OCR worker, and WebSocket optimizations | Upload/OCR + websocket + migration + frontend + deps/docs | very high | unsafe | split into smaller governed issues | Very broad feature PR spanning protected production areas and migration/dependency changes. |
| #41 | Implement upload pipeline, OCR worker, and WebSocket hardening with Redis adapter | Upload API/model, worker/Celery/Redis, ws metrics/adapter, frontend, env/dependency/docs updates | very high | unsafe | split into smaller governed issues | Large architectural change set before governed phase slicing/spec lock. |
| #40 | Add upload pipeline with OCR worker and WebSocket delta optimization | Upload/OCR worker + ws delta/redis + migration + frontend routes/store + docs/deps | very high | unsafe | split into smaller governed issues | Cross-cutting high-risk bundle; not suitable for blind merge. |
| #38 | Fix lint failures and Python 3.13 compatibility in CI workflows | `.github/workflows/lint.yml` + assorted formatting/import churn | high | needs split | rebase | CI/lint changes should be rebased and re-scoped to current governed baseline and pinned versions. |
| #27 | Fix Python 3.12 compatibility and in-memory DB mode for CI | `requirements`, DB wiring, role route, workflow dispatch, config/tooling files | high | pre-governance | close | Appears superseded by #26 with same objective; avoid duplicate stale PRs. |
| #26 | Fix Python 3.12 compatibility and in-memory DB mode for CI | `requirements`, `sql_app/database.py`, route wiring, CI/lint/release dispatch adjustments | high | needs split | split into smaller governed issues | Valuable themes but mixed app behavior + dependency + workflow changes need narrow governed slices. |
| #23 | Fix pre-commit issues: modernize config, fix imports, and apply formatting | 80 files across backend/routes/services/sql_app/tools + pre-commit/ruff configs | very high | unsafe | do not merge | Massive wide-scope code churn with formatting + behavior-adjacent edits across critical modules. |
| #22 | [WIP] Fix pre-commit failures for Ruff, Black, isort, and mypy | 49 files across backend + config + formatting/bulk cleanup | very high | unsafe | close | Older WIP superseded by newer variants; still too broad for governed merge path. |
| #4 | chore(refactor): add package skeleton and tests — split main.py (step 1) | New `cricksy_scorer/` package, root main shim, root tests, workflow changes | high | unsafe | do not merge | Refactor stream outside current governed phase plan; introduces alternate structure and CI changes. |
| #3 | Enable cross-platform CI simulation suite with proper environment setup | scripts, frontend test runner/tsconfig, docs, CI additions; base is `agent/sandbox` | medium | pre-governance | do not merge | Not targeting `main`, contains CI/script behavior changes and cross-platform assumptions. |
| #1 | Add simulated T20 match JSON file with ball-by-ball breakdown | Adds `simulated_t20_match.json`; base is `agent/sandbox` | low | pre-governance | close | Not targeting `main`; can be reintroduced later via small governed test-data PR if needed. |

---

## 3) Focus Review of Older Broad PR Clusters

### A) Upload / OCR / WebSocket hardening cluster
PRs: **#40, #41, #42, #43, #44**

- All are broad, overlapping, and pre-governance.
- All touch high-risk areas (uploads, OCR worker queue, sockets, metrics, migrations, deps, frontend flows).
- **Decision:** Do not blind-merge any of these. Close or convert to governed issue slices and reimplement in scoped phase order.

### B) Alembic merge-head cluster
PR: **#45**

- Intended narrow migration/workflow fix but includes far broader diff footprint.
- **Decision:** Mark unsafe/do not merge. Recreate as a clean, minimal migration-governance issue if still required.

### C) Deploy/ECR workflow cluster
PRs: **#49, #50**

- Both are infra-sensitive and overlapping; both modify deploy workflow + Docker image behavior.
- **Decision:** Keep out of blind merge path; split into small governed infra/security issues and rebase to current main.

### D) CI/lint modernization cluster
PRs: **#22, #23, #26, #27, #38**

- Large style/config churn mixed with behavior-adjacent edits.
- **Decision:** Close stale/duplicate PRs and reissue only minimal, auditable, governed fixes.

---

## 4) Recommended Cleanup Actions Before Next Feature Phase

1. Freeze merges of all **pre-governance** and **unsafe** open PRs.
2. Close duplicate/superseded PRs first: **#27**, **#22**, and non-main targets **#1**, **#3**.
3. For each retained concern (deploy scan, Alembic heads, CI/lint), create new **small governed issues** with:
   - pre-phase audit
   - explicit spec lock
   - strict file allowlist
   - required validation commands
4. Treat upload/OCR/WebSocket bundle PRs (**#40-#44**) as source context only; do not merge directly.
5. Keep only the current governed docs PR (**#101**) active for Phase 1D completion.

---

## 5) Phase 1B / 1C Completion Check

- `docs/PHASE_1C_HEALTH_PARITY_STABILIZATION.md` exists and records completion with no production-code drift.
- No currently open PR in this inventory is an active Phase 1B or Phase 1C execution PR.
- Phase 1B has no open PR in the current inventory; if Phase 1B artifacts are required, track via a dedicated governed issue/doc update rather than legacy pre-governance PRs.

---

## 6) Recommended Next Safe Phase After Cleanup

After completing the cleanup actions above, the next safe governed phase is:

- **Phase 3 — Coach Pro Plus Video Analysis Hardening + Extension**

Then proceed with the master checklist execution order.

---

## 7) Phase 1D Output Confirmation

- Open PR triage completed with governance-first recommendations.
- Older large pre-governance PRs are explicitly marked as **not safe for blind merge**.
- Checklist numbering cleanup is completed in `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`.

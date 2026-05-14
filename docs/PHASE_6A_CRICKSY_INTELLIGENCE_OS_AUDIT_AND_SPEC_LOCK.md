# PHASE 6A — CRICKSY INTELLIGENCE OS AUDIT AND SPEC LOCK

## Status

Docs/spec-lock only.

No agents, skills, routers, LLM workflows, dependencies, migrations, or runtime app behavior are implemented in this phase.

---

## 1) Purpose

Lock the governance layer for Cricksy's future evolution into a governed sports intelligence operating system.

This phase exists to:

- audit the current repo surfaces that future intelligence work will depend on,
- document deterministic-vs-AI boundaries,
- define protected systems and forbidden changes,
- map Phase 5 historical registry work as the approved data foundation,
- sequence future subphases before any intelligence implementation begins.

---

## 2) Audit Summary

### A. Analyst Workspace — existing surfaces

Current Analyst Workspace work already exists across backend and frontend surfaces:

- `frontend/src/views/AnalystWorkspaceView.vue`
  - analyst-facing workspace with match filters, export UI, AI callouts, empty/error/loading states, and historical-import visibility.
- `frontend/tests/unit/AnalystWorkspaceView.spec.ts`
  - governed UI tests for real API-driven rendering, imported-match metadata, and historical cleanup flows.
- `backend/routes/analyst_pro.py`
  - analyst export endpoints (`/players/export`, `/matches/export`, `/player-form/export`) plus match detail endpoints.
- `backend/routes/analytics_case_study.py`
  - registry/provenance response used by analyst match detail views.
- `backend/services/analyst_access.py`
  - scoped game visibility by user/org boundary.

Implication for Phase 6:

Future intelligence must plug into the existing Analyst Workspace and governed match-access boundaries instead of inventing parallel AI-only surfaces.

### B. Historical import + registry foundation — existing Phase 5 work

Current historical foundation already exists and is stronger than a raw file-upload layer:

- `backend/routes/historical_import.py`
  - dry-run, apply, rollback, apply-deliveries, training-status, bulk ZIP dry-run/apply, and legacy metadata repair endpoints.
- `backend/services/historical_import_preview.py`
  - deterministic preview/validation of structured historical JSON.
- `backend/services/historical_import_apply_service.py`
  - controlled match creation, rollback, and delivery import behavior.
- `backend/services/historical_import_backfill_service.py`
  - metadata repair/backfill for legacy historical records.
- `backend/routes/analytics_case_study.py`
  - registry/provenance/training-eligibility surface for imported matches.
- `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`
  - Phase 5L.1 cost-controlled large ZIP intake and Phase 5M registry/training-eligibility foundations are already documented.

Implication for Phase 6:

Future intelligence must consume validated historical imports, provenance metadata, and training-eligibility gates. It must not bypass Phase 5 governance.

### C. Deterministic scoring / result / DLS truth — existing protected systems

Official cricket truth is already calculated by deterministic systems:

- `backend/services/scoring_service.py`
  - per-ball scoring mutations for runs, extras, wickets, striker rotation, and over completion.
- `backend/routes/gameplay.py`
  - gameplay runtime endpoints and live state emission via `emit_state_update()`.
- `backend/routes/dls.py`
  - DLS revised-target and par-score calculation routes.
- Existing CI/test checklist entries and DLS tests in the master checklist.

Implication for Phase 6:

These systems remain the source of truth. Intelligence layers must read from them, never calculate or overwrite them.

### D. Existing analytics / match-intelligence endpoints

The repo already contains analytics-oriented endpoints and services, including:

- `backend/routes/analytics.py`
- `backend/routes/analytics_case_study.py`
- `backend/routes/phase_analysis.py`
- `backend/routes/player_analytics.py`
- `backend/routes/prediction.py`
- `backend/services/analytics_case_study.py`

Implication for Phase 6:

Future skills should compose these governed analytics surfaces where possible instead of loading unbounded raw data or introducing duplicate calculations.

### E. Existing model / prediction code

Prediction/model-related code already exists:

- `backend/routes/prediction.py`
  - game win-probability endpoint.
- `backend/services/prediction_service.py`
  - ML-assisted win-probability service with rule-based fallback.
- `backend/services/ml_features.py`
- `backend/services/ml_model_service.py`
- `backend/services/model_manager.py`

Implication for Phase 6:

Where governed prediction/model outputs already exist, future intelligence may explain them but must not silently replace or mutate the underlying model outputs.

### F. Coach Pro Plus / video analysis — existing governed subsystem

Coach Pro Plus already contains a substantial video-analysis/report/export architecture:

- `backend/routes/coach_pro_plus.py`
  - video session/job APIs, upload lifecycle, results/report/PDF availability, and feature gating.
- `backend/services/coach_ai_pipeline.py`
  - pose + ball-tracking orchestration with rule-based findings and explicit note that LLM integration is future work.
- `backend/services/coach_report_service.py`
  - deterministic report generation with optional future LLM enhancement noted but not implemented for MVP.
- `backend/services/pdf_export_service.py`
  - PDF generation for coaching analysis exports.

Implication for Phase 6:

Future intelligence work must not weaken Coach Pro Plus reviewability, evidence trails, or youth-facing/report-facing safeguards.

### G. Auth / RBAC / tier / organization boundaries — existing enforcement

Multiple layers already constrain access and visibility:

- `backend/security.py`
  - authenticated-user resolution and role enforcement helpers.
- `backend/routes/auth_router.py`
  - user profile/subscription context.
- `backend/services/entitlement_service.py`
  - feature access via superuser, beta grants, and plan entitlements.
- `backend/services/analyst_access.py`
  - org-aware game scoping for analyst flows.

Implication for Phase 6:

All user-facing intelligence must inherit role, plan, organization, and access boundaries. No intelligence surface may bypass these checks.

### H. Fake-data guard — existing protection

Fake/demo/random production data already has a dedicated guard:

- `scripts/check-fake-data.js`
  - scans frontend production files for mock/random/hardcoded data patterns and fails on errors.
- `.github/workflows/ci.yml`
  - runs the fake-data guard in frontend CI.

Implication for Phase 6:

Future skills, prompts, reports, or intelligence UIs must not fabricate stats, recommendations, or sample outputs as if they were real data.

### I. Report / export capability — existing surfaces

The repo already includes governed export/report paths:

- `backend/routes/analyst_pro.py`
  - JSON/CSV exports for players, matches, and player form.
- `backend/services/coach_report_service.py`
  - narrative coaching report generation.
- `backend/services/pdf_export_service.py`
  - PDF exports for Coach Report V2.

Implication for Phase 6:

Future intelligence outputs should target existing export/review/report channels where appropriate and remain reviewable before becoming official or coach-facing.

### J. Existing AI / LLM-related code

AI-style or future-AI surfaces already exist, but they are partial and mostly rule-based today:

- `backend/routes/ai.py`
  - delivery commentary endpoint.
- `backend/services/ai_commentary.py`
  - rule-based commentary with explicit TODO for future LLM replacement.
- `backend/services/match_ai_service.py`
  - mock AI match commentary/summary service with explicit TODOs.
- `backend/services/ai_player_insights.py`
  - rule-based player insights with future LLM TODOs.
- `backend/services/coach_report_service.py`
  - deterministic reporting with optional future LLM narrative path noted but not implemented.
- `backend/services/agent_budget.py`
  - budget scaffolding for future agent runs.

Audit conclusion:

The repo contains AI-adjacent scaffolding and rule-based “AI-style” outputs, but it does not yet contain the governed Supervisor / Intent Router / Skill Router / validation-agent architecture required by this phase.

### K. Places where AI could accidentally calculate or mutate truth later

Future intelligence work would be high-risk if it were allowed to bypass these systems:

- `backend/services/scoring_service.py`
- `backend/routes/gameplay.py`
- `backend/routes/dls.py`
- historical import apply/rollback/training-status flows in `backend/routes/historical_import.py`
- registry/provenance/training-eligibility logic in `backend/routes/analytics_case_study.py`
- analyst filter/export paths in `backend/routes/analyst_pro.py`

Hard warning:

If future LLM or agent features are allowed to write directly into scoring, results, DLS, registry, or official stat paths, Cricksy would risk turning advisory AI into accidental cricket truth. That boundary must be blocked in code and tests in Phase 6B.

### L. Existing CI / test gates relevant to intelligence work

Current CI/test protections already relevant to future intelligence include:

- `.github/workflows/ci.yml`
  - docs-only changes are path-ignored,
  - backend lint/mypy,
  - bandit + pip-audit,
  - backend fast tests,
  - backend integration tests,
  - backend DLS tests,
  - frontend fake-data guard,
  - frontend type-check + build.
- `frontend/tests/unit/AnalystWorkspaceView.spec.ts`
  - Analyst Workspace regression coverage.
- Phase 5 historical-import backend tests under `backend/tests/test_historical_import_*.py`.

Implication for Phase 6:

Future intelligence work must add bounded tests around deterministic protection, confidence labeling, review gating, access boundaries, and no-fake-data behavior rather than bypassing current CI expectations.

---

## 3) Spec Lock

### A. Core direction

Cricksy should evolve into:

```text
A governed sports intelligence operating system
```

Not:

```text
AI everywhere
```

### B. Governed future architecture

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

This architecture is future-state only in Phase 6A. It is not implemented here.

### C. Global intelligence rules

All future intelligence work must follow these rules:

1. Deterministic systems calculate facts.
2. AI systems explain, summarize, recommend, or communicate.
3. Skills must be reusable, versioned, testable, and governed.
4. AI outputs must be grounded in approved data.
5. Confidence and limitations must be visible.
6. Expensive AI must be event-triggered, not always running.
7. Sensitive outputs require validation and review.
8. User-facing intelligence must respect role, organization, youth-safety, and data-boundary rules.

### D. Deterministic vs AI boundary

Deterministic systems own:

- scoring,
- runs,
- balls,
- overs,
- wickets,
- innings state,
- match result,
- scorecards,
- official player stats,
- DLS,
- validations,
- filters,
- metrics,
- venue par calculations,
- win probability model outputs where applicable.

AI systems may only:

- explain,
- summarize,
- interpret,
- recommend,
- communicate,
- generate reviewable reports,
- answer questions grounded in approved data.

Hard gate:

```text
No LLM may calculate, overwrite, or mutate official cricket truth.
```

### E. Progressive disclosure rule

Do not load all available cricket data into AI context.

Load only the minimum relevant match/player/team/phase/video/context data required for the user’s question.

Example allowed context for “Why did Player X struggle against spin today?”

- Player X,
- today’s innings,
- spin deliveries,
- recent spin weakness summary,
- relevant confidence metadata,
- optional tagged clips.

Explicitly do not load:

- all players,
- all seasons,
- all matches,
- all reports.

### F. Confidence + uncertainty rule

AI-generated intelligence must expose confidence and limitations.

Example:

```text
Limited sample size: this recommendation is based on 14 deliveries against spin, so treat it as an early signal.
```

Low-confidence insights must never be presented as certain.

### G. Event-triggered compute rule

Continuous intelligence should be mostly deterministic and cheap.

Expensive AI should only run on explicit triggers such as:

- coach asks a question,
- report requested,
- collapse detected,
- win-probability swing needs explanation,
- video uploaded,
- model confidence low,
- analyst requests podcast prep,
- export/report requested.

Hard gate:

No always-running LLM loops without explicit user approval, cost guardrails, and governance approval.

### H. Validation / review queue rule

Sensitive or high-impact outputs require validation and review before becoming official or coach-facing.

High-impact outputs include:

- youth player feedback,
- mental-analysis recommendations,
- coach reports,
- scouting reports,
- public/podcast content,
- model-derived recommendations,
- performance criticism.

Required future validation flow:

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

### I. Protected systems

Do not change or weaken:

- live scoring truth,
- official score / balls / overs / wickets / innings state / result / scorecard / player stats,
- DLS calculation logic,
- live bus/socket behavior,
- historical import safety gates,
- training-eligibility gates,
- video analysis / Coach Pro Plus systems,
- mental-analysis systems,
- auth / RBAC / org boundaries,
- fake-data guard,
- CI/CD gates.

### J. Phase 5 foundation link

Future intelligence must follow this governed chain:

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

Phase 5L.1 and Phase 5M are therefore locked in as structured-data and registry foundations for later intelligence phases.

---

## 4) Future Phase 6 Breakdown

### Phase 6A — Intelligence OS Audit + Spec Lock

This document/checklist update only.

### Phase 6B — Deterministic vs AI Boundary Enforcement

Lock code and test boundaries that prevent AI from mutating cricket truth.

### Phase 6C — Cricksy Skills Architecture Spec

Define reusable intelligence skills before agent implementation.

Example future skill families:

- Match Momentum Skill
- Batting Collapse Skill
- Powerplay Skill
- Pressure Overs Skill
- Spin Weakness Skill
- Opposition Scout Skill
- Coach Communication Skill
- Youth Safety Skill
- Report Writing Skill
- Data Validation Skill

Each future skill must define:

- purpose,
- inputs,
- outputs,
- deterministic dependencies,
- confidence rules,
- allowed users/roles,
- validation tests,
- safety rules,
- sample outputs,
- no-fake-data rule.

### Phase 6D — Intent Router + Skill Router Spec

Define how user intents map to approved skills and safe data retrieval.

Example future intents:

- Analyze batting collapse
- Review player against spin
- Prepare opposition report
- Generate coaching notes
- Explain match momentum
- Prepare podcast talking points

### Phase 6E — Progressive Disclosure + Context Loading Rules

Define strict context-minimization rules so AI only sees relevant data slices.

### Phase 6F — Confidence + Uncertainty System Spec

Define confidence metadata and limitation labels for generated intelligence.

### Phase 6G — Event-Triggered Intelligence Spec

Define cheap deterministic always-on signals vs expensive triggered AI.

### Phase 6H — Validation Agents + Review Queue Spec

Define validation, review, and approval routing before high-impact outputs reach end users.

---

## 5) Acceptance Lock for Phase 6A

Phase 6A is complete only if:

- the Master Execution Checklist contains the new Phase 6 governance stream,
- the global intelligence system rule is documented,
- deterministic-vs-AI boundaries are documented,
- future Phase 6B–6H roadmap is documented,
- Phase 5 foundations are explicitly linked,
- no runtime app behavior is changed,
- no agents/skills/routers/LLM flows are implemented,
- no dependencies or migrations are added.

---

## 6) Files Reviewed For This Audit

- `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`
- `frontend/src/views/AnalystWorkspaceView.vue`
- `frontend/tests/unit/AnalystWorkspaceView.spec.ts`
- `backend/routes/analyst_pro.py`
- `backend/routes/analytics_case_study.py`
- `backend/routes/historical_import.py`
- `backend/services/scoring_service.py`
- `backend/routes/gameplay.py`
- `backend/routes/dls.py`
- `backend/routes/prediction.py`
- `backend/services/prediction_service.py`
- `backend/routes/ai.py`
- `backend/services/ai_commentary.py`
- `backend/services/match_ai_service.py`
- `backend/services/ai_player_insights.py`
- `backend/routes/coach_pro_plus.py`
- `backend/services/coach_ai_pipeline.py`
- `backend/services/coach_report_service.py`
- `backend/services/pdf_export_service.py`
- `backend/security.py`
- `backend/routes/auth_router.py`
- `backend/services/entitlement_service.py`
- `backend/services/analyst_access.py`
- `scripts/check-fake-data.js`
- `.github/workflows/ci.yml`

---

## 7) Phase 6A Validation Notes

Validation for this issue is documentation-oriented:

- verify markdown structure and headings,
- verify phase numbering/order is still clear,
- verify no runtime files changed,
- verify no phases were marked complete without evidence.

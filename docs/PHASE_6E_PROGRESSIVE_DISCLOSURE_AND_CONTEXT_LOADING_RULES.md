# PHASE 6E — PROGRESSIVE DISCLOSURE + CONTEXT LOADING RULES

## Status

Spec-lock complete. Architecture only.

No runtime context loader, runtime router, runtime skill, Supervisor, agents, LLM workflows, migrations, dependencies, or production behavior changes are implemented in this phase.

---

## 1) Purpose

Define strict future rules for progressive disclosure and context loading so Cricksy intelligence workflows load only the minimum safe data required for a selected intent and skill.

Failure mode to prevent:

```text
Intent is understood → skill is selected → system loads too much data → high cost, slow output, privacy risk, weaker analysis.
```

Outcome enabled:

```text
Intent → skill → minimum required context → bounded analysis → confidence/limitations → review when needed.
```

---

## 2) Required Future Architecture (Spec Only)

```text
Intent + Skill Mapping
        ↓
Context Requirement Contract
        ↓
Permission + Org Boundary Check
        ↓
Minimum Relevant Data Selection
        ↓
Context Budget Check
        ↓
Confidence / Sufficiency Check
        ↓
Skill Execution Context Package
        ↓
Fallback if insufficient/unsafe/too large
```

This phase defines context-loading governance contracts only. Runtime implementation is deferred.

---

## 3) Pre-Phase Audit Summary

### A. Existing Phase 6A/6B/6C/6D governance baseline

- `docs/PHASE_6A_CRICKSY_INTELLIGENCE_OS_AUDIT_AND_SPEC_LOCK.md`
- `docs/PHASE_6B_DETERMINISTIC_AI_BOUNDARY_ENFORCEMENT.md`
- `docs/PHASE_6C_CRICKSY_SKILLS_ARCHITECTURE_SPEC.md`
- `docs/PHASE_6D_INTENT_ROUTER_AND_SKILL_ROUTER_SPEC.md`
- `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`

### B. Existing Phase 6D intent-to-skill mappings and required context fields

- Phase 6D already locks intent taxonomy and intent→skill mapping patterns.
- Mandatory routing contract fields already include `required_context` and `forbidden_context`.
- Existing 6D fallback statuses (`insufficient_data`, `needs_clarification`, `not_authorized`, etc.) are the base layer that 6E extends with stricter context-loading outcomes.

### C. Existing Analyst Workspace data surfaces and case-study endpoints

- Frontend: `frontend/src/views/AnalystWorkspaceView.vue`
- Backend:
  - `backend/routes/analytics_case_study.py`
  - `backend/services/analytics_case_study.py`
  - `backend/services/analyst_access.py`
- Existing analyst flows already depend on scoped match visibility and deterministic case-study outputs.

### D. Existing historical import / registry / provenance / training-eligibility surfaces

- `backend/routes/historical_import.py`
- `backend/services/historical_import_preview.py`
- `backend/services/historical_import_apply_service.py`
- `backend/services/historical_import_backfill_service.py`
- Registry/provenance endpoint:
  - `GET /analytics/matches/{match_id}/registry` in `backend/routes/analytics_case_study.py`
- Existing `metadata_only_pending_full_import` gating is already part of training-eligibility behavior and is preserved.

### E. Existing Coach Pro Plus / video-analysis outputs and stored result surfaces

- `backend/routes/coach_pro_plus.py`
- `backend/services/coach_ai_pipeline.py`
- `backend/services/coach_report_service.py`
- `backend/services/pdf_export_service.py`
- Existing job/results/report/PDF artifacts are role-gated and must remain bounded and reviewable.

### F. Existing player/team/match/delivery/statistics data surfaces

- Match/game state and deliveries from deterministic game records.
- Analytics and case-study services expose phase/player/performance summaries.
- Existing match-context package service (`backend/services/match_context_service.py`) includes broad/full-context structures and highlights why 6E budget/selection rules are required before any future runtime loader work.

### G. Existing auth/RBAC/org boundary checks

- `backend/security.py`:
  - `get_current_user`, `get_current_active_user`, `require_roles`
- `backend/services/analyst_access.py`:
  - org/user-scoped game access clause and statement builders
- Existing route-level role checks in analytics/coach surfaces are baseline controls that must run before context loading.

### H. Existing fake-data guard and no-fake-data requirements

- `scripts/check-fake-data.js`
- `.github/workflows/ci.yml` (`npm run guard:fake-data`)
- Phase 6A–6D governance already prohibits fabricated data in intelligence outputs.

### I. Existing AI-adjacent services and prompt/context patterns

- `backend/routes/ai.py`
- `backend/services/ai_commentary.py`
- `backend/services/match_ai_service.py`
- `backend/services/ai_player_insights.py`
- `backend/services/ai_match_summary.py`
- Current services are mostly rule-based/mocked and not governed by a centralized runtime context loader; 6E defines future constraints before that runtime exists.

### J. Existing cost-control/budget logic

- `backend/services/agent_budget.py` contains advisory limits (`max_runs_per_day`, `max_tokens_per_run`, `MAX_DAILY_TOKENS_TOTAL`) for agent-run operations.
- No unified intelligence context-budget engine exists yet; 6E defines that contract.

### K. Existing tests and CI gates relevant to future context-loading validation

- `.github/workflows/ci.yml`: pre-commit, lint/type checks, security, backend tests, frontend guard/type-check/build.
- `backend/tests/test_phase_6b_ai_boundary.py`: protects non-authoritative AI boundary and official-truth mutation constraints.
- Existing integration and historical-import tests already cover data quality gates that future context loading must respect.

### L. Current risky patterns to explicitly prevent in future implementation

- Risk of broad/unbounded context packaging (example: full match context structures in `match_context_service.py`).
- Risk of loading unrelated org/player/team data without strict pre-load authorization checks.
- Risk of unnecessary raw-delivery/video overfetch when deterministic summaries are sufficient.
- Risk of confidence inflation if required context is missing but workflow still attempts a narrative answer.

---

## 4) Strict Scope Lock for Phase 6E

### Allowed

- This architecture/spec document.
- Master checklist update for Phase 6E completion notes.
- Context-loading governance contracts and validation requirements for future implementation.

### Conditionally allowed

- Docs-only template example for context-loading contracts.

### Not allowed

- Runtime context-loader implementation.
- Runtime intent/skill router implementation.
- Runtime skill implementation.
- Supervisor/agent implementation.
- LLM provider/external AI integration.
- Migrations, dependencies, or infrastructure changes.
- Any production behavior changes to scoring, DLS, gameplay/live bus, historical import truth, registry/training eligibility, or auth boundaries.

---

## 5) Required Context Loading Principles

### Rule 1 — Minimum Necessary Context

Load only the smallest data slice required by the selected intent + skill.

Must not load by default:

- all players
- all matches
- all seasons
- all reports
- all videos
- all deliveries
- unrelated organization/team/player data

### Rule 2 — Deterministic Data Products First

Future context packages must prefer bounded deterministic products first:

- match phase summaries
- player-specific delivery slices
- venue/competition metadata
- selected video tags/clips
- existing computed metrics
- registry/provenance data
- confidence signals

Raw/unbounded records are last resort only when strictly required.

### Rule 3 — Permission Before Context

Before loading any context, future systems must verify:

- user role
- organization ownership
- team visibility
- player visibility
- youth-safety constraints
- coach/analyst permissions

No skill may receive context the user is not authorized to access.

### Rule 4 — Context Budgeting

Every future context package must declare budgets such as:

- max matches
- max players
- max deliveries
- max phases
- max clips/tags
- max reports
- max lookback window
- max token/context size (if AI is used later)

If budget is exceeded, return safe fallback (`needs_narrower_scope` / `context_budget_exceeded`) rather than overloading context.

### Rule 5 — Sufficiency Check

Before execution, context must pass sufficiency checks.

If required data is missing, return:

```text
insufficient_data
```

Missing data must never be fabricated (match/player/venue/video/performance).

### Rule 6 — Progressive Loading Stages

Future loaders must request context in this order:

1. Selected entity identity (match/player/team/competition)
2. Required metadata/provenance
3. Required deterministic metrics/summaries
4. Narrow delivery/video slices if needed
5. Historical lookback only if confidence/sample size requires it
6. Broader data only after explicit user narrowing or approval

### Rule 7 — No Fake Data

If real approved data is unavailable, return honest unavailable/insufficient states.

Production intelligence must never inject fake/demo/synthetic facts as context.

---

## 6) Required Context Package Contract (Mandatory Fields)

Every future skill execution context package must define all fields below:

- `context_package_id`
- `intent_id`
- `skill_id`
- `user_role`
- `org_scope`
- `selected_entities`
- `required_context`
- `optional_context`
- `forbidden_context`
- `data_sources`
- `permission_checks`
- `context_budget`
- `loaded_context_summary`
- `omitted_context_summary`
- `sufficiency_status`
- `insufficient_data_reasons`
- `confidence_inputs`
- `privacy_boundary_notes`
- `provenance_references`
- `no_fake_data_confirmation`

### 6A) Docs-only reference contract shape

```yaml
context_package_id: "ctx_2026_05_14_match_momentum_001"
intent_id: "analyze_match_momentum"
skill_id: "match_momentum.v1"
user_role: "analyst_pro"
org_scope:
  org_id: "org_123"
  scope_type: "org_visible_matches_only"
selected_entities:
  match_id: "match_abc"
  player_ids: []
required_context:
  - "match_phase_summary"
  - "innings_totals"
  - "phase_run_rate_swings"
optional_context:
  - "selected_delivery_slice"
forbidden_context:
  - "cross_org_match_data"
  - "all_matches_dump"
data_sources:
  - "analytics_case_study.phase_breakdown"
  - "game.deliveries (bounded slice only)"
permission_checks:
  role_check: "pass"
  org_boundary_check: "pass"
  player_visibility_check: "not_applicable"
context_budget:
  max_matches: 1
  max_players: 4
  max_deliveries: 72
  max_phases: 6
  max_clips_or_tags: 12
  max_reports: 1
  max_lookback_days: 30
  max_tokens_estimate: 6000
loaded_context_summary:
  matches_loaded: 1
  players_loaded: 3
  deliveries_loaded: 48
  clips_loaded: 0
omitted_context_summary:
  omitted:
    - "full_org_history"
    - "unselected_player_video"
sufficiency_status: "sufficient"
insufficient_data_reasons: []
confidence_inputs:
  data_quality: "validated_match_complete"
  sample_size: "single_match"
privacy_boundary_notes:
  - "No cross-org entities loaded."
provenance_references:
  - "analytics_case_study.match_id=match_abc"
  - "registry.validation_status=valid"
no_fake_data_confirmation: true
```

---

## 7) Required Fallback Behavior (Safe Outcomes)

Future context loading/execution must return explicit safe statuses when required:

- `insufficient_data`
- `needs_narrower_scope`
- `not_authorized`
- `context_budget_exceeded`
- `metadata_only_pending_full_import`
- `missing_selected_match`
- `missing_selected_player`
- `video_context_unavailable`
- `blocked_by_youth_safety`
- `blocked_by_org_boundary`

Fallback outputs must never fabricate missing evidence and must preserve deterministic authority.

---

## 8) Required Example Context Contracts

Each example below includes allowed context, forbidden context, budget, sufficiency rules, fallback behavior, and review requirements where applicable.

### 8.1 Spin Weakness Analysis (One Player, One Match)

- intent: `analyze_spin_weakness`
- skill: `player_spin_weakness.v1`
- selected scope: one player + one selected match
- allowed context:
  - selected `player_id`
  - selected `match_id`
  - player-vs-spin delivery slice (bounded)
  - dismissal/shot tags for that player in that match
  - related phase summaries
- forbidden context:
  - all players in competition
  - full-season delivery corpus
  - cross-org player records
  - unrelated coach reports
- budget/limits:
  - max_matches=1, max_players=1, max_deliveries=120, max_clips_or_tags=20
- sufficiency rules:
  - must have selected player + selected match
  - must have minimum spin-faced sample (balls threshold)
  - if no spin events found, insufficient
- fallback behavior:
  - `missing_selected_player`, `missing_selected_match`, or `insufficient_data`
- review requirement:
  - required for youth-facing coaching language or high-impact recommendation text

### 8.2 Match Momentum Analysis (One Selected Match)

- intent: `analyze_match_momentum`
- skill: `match_momentum.v1`
- selected scope: one selected match
- allowed context:
  - match phase summaries
  - innings run/wicket progression
  - bounded key-event delivery slice
  - deterministic momentum swings
- forbidden context:
  - all matches in org history
  - all player profiles
  - unrelated video archives
- budget/limits:
  - max_matches=1, max_players=6, max_deliveries=90, max_phases=6
- sufficiency rules:
  - requires valid selected match and phase data
  - if phase breakdown missing/unvalidated, insufficient
- fallback behavior:
  - `missing_selected_match`, `insufficient_data`, `context_budget_exceeded`
- review requirement:
  - generally not required unless promoted into public/media output workflow

### 8.3 Coach Notes (One Selected Player)

- intent: `generate_coaching_notes`
- skill: `coach_communication.v1`
- selected scope: one player with bounded evidence bundle
- allowed context:
  - approved deterministic findings for selected player
  - confidence + limitations fields
  - provenance references and training-context metadata
- forbidden context:
  - unverifiable narrative claims
  - non-visible players
  - historical records outside authorized org scope
- budget/limits:
  - max_players=1, max_reports=1, max_matches=3 lookback, max_tokens_estimate=5000
- sufficiency rules:
  - requires selected player + minimum evidence citations
  - no source findings => insufficient
- fallback behavior:
  - `missing_selected_player`, `insufficient_data`, `not_authorized`
- review requirement:
  - required for youth-facing notes and high-impact communication

### 8.4 Podcast Breakdown (One Selected Historical Match)

- intent: `prepare_podcast_breakdown`
- skill: `analyst_media_report.v1` (future)
- selected scope: one selected historical match
- allowed context:
  - case-study summary for selected match
  - registry/provenance metadata
  - bounded notable events and key-player slices
- forbidden context:
  - multi-season dump
  - unselected match archives
  - hidden org content
- budget/limits:
  - max_matches=1, max_players=8, max_deliveries=80, max_reports=1
- sufficiency rules:
  - selected match must exist and be visible
  - registry metadata should be available for citation quality
- fallback behavior:
  - `missing_selected_match`, `blocked_by_org_boundary`, `insufficient_data`
- review requirement:
  - required before public/media-facing release

### 8.5 Training Eligibility Review (Metadata-Only Historical Import)

- intent: `review_training_eligibility`
- skill: `training_eligibility_review.v1` (future data/validation skill)
- selected scope: one historical import batch or linked match
- allowed context:
  - registry metadata
  - validation status
  - import finalization state
  - provenance references
- forbidden context:
  - fabricated completion assumptions
  - unrelated match performance context
  - unofficial manual overrides outside deterministic gates
- budget/limits:
  - max_matches=1, max_reports=1, max_deliveries=0 (metadata-only path)
- sufficiency rules:
  - if import is metadata-only and full import is pending, must report blocked status
- fallback behavior:
  - `metadata_only_pending_full_import`, `insufficient_data`, `not_authorized`
- review requirement:
  - deterministic gate outcome only; no AI override of training eligibility truth

---

## 9) Relationship to Phase 6F–6H (Separation Lock)

Phase 6E defines:

```text
what context may load, what is forbidden, how budgets/sufficiency/fallback apply.
```

Still out of scope:

- **Phase 6F**: confidence + uncertainty scoring policy and deeper calibration mechanics.
- **Phase 6G**: event-triggered context/AI compute orchestration.
- **Phase 6H**: validation/review queue runtime mechanics after outputs are produced.

These phases remain separate and are not collapsed into Phase 6E.

---

## 10) Protected Systems (Unchanged by This Phase)

- official score/runs/balls/overs/wickets/innings state/match result/scorecards/player stats
- DLS calculations
- gameplay/live bus behavior
- historical import validation/provenance/training-eligibility gates
- Phase 5M registry endpoint behavior
- Phase 6B AI boundary behavior
- Phase 6C skill contract behavior
- Phase 6D intent/skill routing boundaries
- Coach Pro Plus/video-analysis runtime
- mental analysis runtime
- auth/RBAC/org boundaries
- fake-data guard
- CI/CD gates

---

## 11) Future Context-Loading Validation Requirements

When runtime context loading is implemented later, tests must include at minimum:

- permission-before-context checks (role/org/team/player/youth safety).
- minimum-necessary context enforcement tests.
- deterministic-data-first selection tests.
- context-budget enforcement tests (`needs_narrower_scope`, `context_budget_exceeded`).
- sufficiency detection tests returning `insufficient_data` when required fields are missing.
- no-fake-data context confirmation tests.
- blocked cross-org context-load tests (`blocked_by_org_boundary`).
- metadata-only training-eligibility blocking tests (`metadata_only_pending_full_import`).
- regression tests proving no official-truth mutation and no bypass of Phase 6B/6C/6D boundaries.

---

## 12) Validation Notes

- Markdown formatting reviewed (headings, lists, fenced blocks, YAML example).
- Phase ordering remains clear; Phase 6F–6H remain future and not complete.
- This phase is architecture/spec-lock only; no runtime implementation was added.
- No new dependencies, migrations, external AI provider calls, or production behavior changes were introduced.

---

## 13) Confirmation Statements

- This is context-loading architecture/spec only.
- No runtime context loader was implemented.
- No runtime routers, runtime skills, agents, or Supervisor logic were implemented.
- No runtime behavior changed.
- Phase 6B boundary, Phase 6C skill contract, and Phase 6D routing boundaries remain intact.

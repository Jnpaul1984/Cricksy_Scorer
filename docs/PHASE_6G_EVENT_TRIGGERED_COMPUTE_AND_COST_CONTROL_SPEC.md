# PHASE 6G — EVENT-TRIGGERED COMPUTE + COST CONTROL SPEC

## Status

Spec-lock complete. Architecture only.

No runtime event bus, queues, workers, schedulers, agents, runtime skills, runtime routers,
Supervisor logic, LLM workflows, migrations, dependencies, or production behavior changes
are implemented in this phase.

---

## 1) Purpose

Define when future Cricksy intelligence compute is allowed to run and how expensive
AI/model work is controlled.

Failure mode to prevent:

```text
Continuous intelligence becomes continuous expensive AI compute.
```

Outcome enabled:

```text
Cheap deterministic awareness always available.
Expensive AI/model reasoning runs only on approved triggers with budgets, gates, and audit logs.
```

---

## 2) Required Future Architecture (Spec Only)

```text
Event / User Action / System Signal
        ↓
Trigger Eligibility Check
        ↓
Role + Org + Safety Check
        ↓
Context Budget Check
        ↓
Compute Budget Check
        ↓
Confidence / Necessity Check
        ↓
Approved Compute Request
        ↓
Output + Cost/Audit Metadata
        ↓
Review Queue if required
```

This phase defines governance contracts only. Runtime event-triggered compute
orchestration implementation is deferred.

---

## 3) Pre-Phase Audit Summary

### A. Existing Phase 6A–6F governance baseline

- `docs/PHASE_6A_CRICKSY_INTELLIGENCE_OS_AUDIT_AND_SPEC_LOCK.md` — Intelligence OS audit,
  governance rules, protected systems, and future-phase separation.
- `docs/PHASE_6B_DETERMINISTIC_AI_BOUNDARY_ENFORCEMENT.md` — Enforceable code boundaries
  preventing AI from mutating cricket truth; `backend/domain/ai_boundary.py` with
  `AiOutputType`, `OFFICIAL_TRUTH_FIELDS`, `AiOutputMetadata`, and
  `validate_no_official_truth_mutation`.
- `docs/PHASE_6C_CRICKSY_SKILLS_ARCHITECTURE_SPEC.md` — Mandatory skill contract with
  `confidence_fields`, `limitations_fields`, `review_required`, and three sample skills.
- `docs/PHASE_6D_INTENT_ROUTER_AND_SKILL_ROUTER_SPEC.md` — Intent taxonomy, routing contract
  with `confidence_requirements`, `review_requirements`, and fallback status codes.
- `docs/PHASE_6E_PROGRESSIVE_DISCLOSURE_AND_CONTEXT_LOADING_RULES.md` — Context minimisation
  rules; context package contract includes `confidence_inputs`, `sufficiency_status`, and
  `metadata_only_pending_full_import` gating.
- `docs/PHASE_6F_CONFIDENCE_AND_UNCERTAINTY_SYSTEM_SPEC.md` — Confidence score package
  contract, confidence bands, uncertainty reason codes, user-facing framing rules, review
  triggers, and safe fallback outcomes.

### B. Existing always-on deterministic systems

The following systems are currently operational and deterministic. They are always-on,
cheap, and must never become LLM-driven:

- **Score engine** (`backend/services/scoring_service.py`): records every delivery,
  updates runs, balls, wickets, extras, innings state, and match result deterministically.
- **Match/gameplay state** (`backend/routes/gameplay.py`, `backend/services/live_bus.py`):
  live bus broadcasts `state:update` to all clients on every scored delivery via Socket.IO.
- **Statistical engine** (`backend/routes/analytics_case_study.py`,
  `backend/services/analytics_case_study.py`): phase breakdowns, momentum series, key
  player summaries, and case-study narratives derived from finalized scorecards.
- **Metadata registry** (`GET /analytics/matches/{match_id}/registry`): returns
  `provenance`, `validation_status`, `registration_status`, and `training_eligible` —
  fully deterministic, from Phase 5M.
- **Prediction/model output** (`backend/routes/prediction.py`,
  `backend/services/prediction_service.py`): win-probability series and match-state
  probability outputs — currently rule-based, not LLM-driven.
- **Player metrics**: batting/bowling averages and economy derived from finalized scorecards.
- **Match phase tags**: powerplay/middle/death phase tagging applied during scoring.
- **Validation/training eligibility status**: derived from `HistoricalImportBatch` and
  registry fields; gated deterministically.

### C. Existing AI-adjacent services and their trigger model

| Service | Current trigger model | Notes |
|---|---|---|
| `backend/routes/ai_commentary.py` | Route-triggered (user navigates or refreshes) | Commentary is rule-based / mocked; no live LLM calls |
| `backend/services/coach_ai_pipeline.py` | User-triggered (coach Pro Plus workflow) | Video jobs are async; analysis runs on job completion |
| `backend/routes/coach_pro_plus.py` | User-triggered (coach uploads video) | Terminal states `done` / `completed` |
| `backend/services/analytics_case_study.py` | Route-triggered (analyst opens workspace) | Narrative summaries generated on request |
| `backend/routes/analytics_case_study.py` | Route-triggered (analyst requests report) | Full report generated on explicit request |
| `backend/services/prediction_service.py` | Embedded in match state fetch | Win-probability included in match state response |

No current service runs expensive LLM compute automatically on every ball, every page load,
or every dashboard refresh. However, some route-triggered services (commentary, case-study
narratives) generate output on every route visit without an explicit user approval step.
Phase 6G defines the future governance contract to prevent uncontrolled compute as
AI/model complexity increases.

### D. Existing cost-control / budget file: `backend/services/agent_budget.py`

`agent_budget.py` provides an operational budget guard for named agent keys:

- `AGENT_BUDGETS` dict defines `max_runs_per_day` and `max_tokens_per_run` per agent key.
- `MAX_DAILY_TOKENS_TOTAL = 20000` — global daily token cap.
- `check_agent_limits()` enforces per-agent and global token limits against a `agent_runs`
  DB table.
- `record_agent_run()` writes an `AgentRun` record for audit.
- `get_today_token_total()` queries today's token consumption.

This file is the seed of the future compute budget enforcement system. Phase 6G extends
the governance model to cover trigger eligibility, cost classes, context budgets, and
audit metadata beyond per-agent token caps.

### E. Coach Pro Plus / video-analysis worker behavior

- Video upload endpoint: `POST /api/coach-pro-plus/upload` — user-triggered.
- Video jobs are stored in `VideoJob` model with terminal states `done` / `completed`.
- `coach_ai_pipeline.py` processes video: frame extraction, tagging, narrative generation.
- No automatic re-processing or background polling without user initiation.
- Video analysis compute is already user-triggered; Phase 6G formalises the governance
  contract around cost class, budget, and audit metadata for future LLM-powered video
  interpretation summaries.

### F. Historical import metadata-only and full import patterns (Phase 5L.1)

- Dry-run endpoint: `POST /api/historical-import/json/bulk-zip/dry-run` — previews files.
- Apply endpoint: `POST /api/historical-import/json/bulk-zip/apply` — imports metadata.
- Apply-deliveries endpoint: `POST …/apply-deliveries` — imports full delivery data.
- A batch at metadata-only state (`training_eligible = false`) must block downstream
  AI/model analysis until full import completes. This deterministic gate must not be
  overridden by any triggered compute request.
- ZIP limits: max 2,000 files, 2 MB per file, 100 MB total compressed/uncompressed.

### G. Existing auth/RBAC/org/youth-safety boundaries

- `backend/security.py`: `get_current_user`, `require_roles`.
- `backend/services/analyst_access.py`: org/user-scoped game access builders.
- Role-based access required before any AI output is assembled or delivered.
- Youth-safety review rules defined in Phase 6F; they must feed into trigger eligibility
  checks (blocked without `review_required` confirmation path).

### H. Existing CI/CD and deployment constraints

- `.github/workflows/ci.yml`: pre-commit hooks, Ruff lint, mypy type checks, Bandit
  security scan, pytest backend tests, frontend Vitest, TypeScript build check, and
  `npm run guard:fake-data` fake-data scan.
- CI pipeline ignores docs-only changes (`paths-ignore: ["**.md", "docs/**"]`).
- No new CI steps, AWS services, or deployment infrastructure added in this phase.

### I. Existing fake-data guard

- `scripts/check-fake-data.js` scans source for fabricated/demo data patterns.
- CI runs `npm run guard:fake-data` on every push.
- Phase 6G extends the no-fake-data requirement: every compute request must carry
  `no_fake_data_confirmation: true` in its compute budget package.

### J. Current risky patterns to prevent in future implementation

- Commentary and case-study narrative outputs are generated on every route visit without
  an explicit trigger approval step; when backed by real LLMs this would become unbounded
  compute.
- Win-probability series is embedded in every match-state response; if replaced with
  heavy model inference this would run on every client poll.
- No cross-request rate limiting or per-user compute budget currently exists beyond
  `agent_budget.py` token caps.
- No structured trigger eligibility check exists before AI outputs are assembled.
- No compute budget package or audit-log entry is produced per AI output request.

---

## 4) Strict Scope Lock for Phase 6G

### Allowed

- This architecture/spec document.
- Master checklist update for Phase 6G completion notes.
- Trigger taxonomy, eligibility rules, cost classes, compute budget contract, guardrails,
  fallback behavior, and example compute contracts documented for future implementation.
- Docs-only template: `docs/compute_templates/event_trigger_compute_contract.example.yaml`.

### Conditionally allowed

- Docs-only template examples for compute budget contracts.

### Not allowed

- Runtime event bus implementation.
- Queue or scheduler implementation.
- Worker implementation.
- Runtime agent implementation.
- Runtime skill implementation.
- Runtime router implementation.
- Cricksy Supervisor implementation.
- LLM provider / external AI integration.
- New AWS services, migrations, dependencies, or infrastructure changes.
- Any production behavior changes to scoring, DLS, gameplay/live bus, historical import
  truth, registry/training eligibility, `agent_budget.py` runtime logic, or auth boundaries.

---

## 5) Always-On vs Triggered Compute Split

### 5.1 Always-On / Cheap / Deterministic

These systems must remain always available, deterministic, and not LLM-driven:

| System | Description |
|---|---|
| Score engine | Records deliveries, updates runs/balls/overs/wickets/extras/innings state/result |
| Match state | Current innings, phase, overs remaining, required rate |
| Gameplay state | Ball-by-ball state for live scoring UI |
| Statistical engine | Batting/bowling averages, economy, phase breakdowns from finalized scorecards |
| Metadata registry | `validation_status`, `registration_status`, `training_eligible` from Phase 5M |
| Basic player metrics | Career averages, recent form summary derived from finalized data |
| Match phase tags | Powerplay/middle/death phase classification applied during scoring |
| Deterministic prediction outputs | Win-probability series (rule-based, currently cheap) |
| Validation status | Import batch and game validation state |
| Training eligibility status | `training_eligible` gate (metadata-only vs full import) |

These systems must never be replaced with LLM-driven equivalents without a separate
architecture decision and full governance review.

### 5.2 Triggered / Expensive / Governed

These systems require an explicit approved trigger, a compute budget package, and
audit metadata before they are allowed to run:

| Future System | Why Expensive |
|---|---|
| LLM explanation | Token-based inference; non-deterministic |
| Report generation | Multi-skill chaining; long context; model calls |
| Tactical recommendation generation | Cross-match analysis; heavy inference |
| Podcast/media output generation | Long-form generation; editorial review required |
| Scouting narrative generation | Player-sensitive; cross-org data; review required |
| Video interpretation summaries | Frame-level analysis; high-cost video model |
| Low-confidence validator review | Assembles evidence; review queue entry |
| Cross-match pattern analysis | Multi-game query; heavy data assembly |
| Model reprocessing or heavy inference | Full model re-run; non-trivial compute cost |

---

## 6) Required Trigger Taxonomy

### 6.1 User-Initiated Triggers

These triggers require an explicit user action. They are the safest trigger class.

| Trigger | Example |
|---|---|
| `user.coach_question` | Coach asks: "Why is this batter weak against spin?" |
| `user.analyst_report_request` | Analyst clicks "Generate Report" for a match |
| `user.podcast_breakdown_request` | Analyst requests podcast breakdown for a match |
| `user.match_player_analysis_request` | User selects match + player and requests analysis |
| `user.coach_development_notes_request` | Coach requests player development notes |

### 6.2 Match-State Triggers

These triggers fire when a significant in-match event is detected by the deterministic
score engine. They may queue a compute request but must not automatically run expensive
AI without a subsequent user confirmation step.

| Trigger | Condition |
|---|---|
| `match.collapse_detected` | 3+ wickets in N balls without significant scoring |
| `match.momentum_swing_detected` | Win-probability delta exceeds configured threshold |
| `match.phase_transition` | Entry into powerplay, middle, or death overs |
| `match.win_probability_swing` | Win-probability swing exceeds threshold (e.g. 20pp in 2 overs) |
| `match.death_overs_reached` | Over 16+ in T20 or equivalent phase |
| `match.unusual_run_rate_drop` | Required run rate crosses unsustainable threshold |

### 6.3 Data/Event Triggers

These triggers fire when a data ingestion or system event completes. They may make
compute eligible but must not automatically run expensive AI.

| Trigger | Condition |
|---|---|
| `data.historical_import_completed` | A full historical import (with deliveries) finalized |
| `data.metadata_only_promoted_to_full` | A metadata-only batch promoted after delivery apply |
| `data.video_uploaded` | Coach Pro Plus video uploaded and stored |
| `data.video_analysis_completed` | Video job reaches terminal state `done` / `completed` |
| `data.new_player_team_competition_registered` | New entity registered in metadata registry |
| `data.model_output_generated` | Prediction or model inference output produced |

### 6.4 Confidence/Validation Triggers

These triggers fire when a confidence package or validation check indicates that
intelligent review or additional processing is warranted.

| Trigger | Condition |
|---|---|
| `confidence.low_confidence_detected` | Confidence package returns `low_confidence` band |
| `confidence.conflicting_signals_detected` | Uncertainty reason `conflicting_signals` raised |
| `confidence.sample_size_below_threshold` | Uncertainty reason `small_sample_size` raised |
| `confidence.missing_data_blocks_recommendation` | Insufficient context for requested skill |
| `safety.youth_safety_review_required` | Output targets youth player; review gate required |

### 6.5 Blocked Triggers

The following events must **never** automatically invoke expensive AI compute. They occur
too frequently, have no meaningful per-event signal, or would cause unbounded cost:

| Blocked trigger | Reason |
|---|---|
| Every ball scored | Too frequent; deterministic score engine handles this |
| Every score update / Socket.IO broadcast | Too frequent; live bus is deterministic |
| Every page load | No user intent signal; would fire on every client navigation |
| Every dashboard refresh | Same as page load; may be automated |
| Every historical import file | A bulk ZIP may contain 2,000 files; per-file AI is blocked |
| Every video frame | Frame extraction is internal; per-frame LLM is blocked |
| Every player profile visit | No explicit user intent to request analysis |

---

## 7) Required Compute Budget Contract

Every future approved compute request must carry a fully populated compute budget package.
No triggered expensive compute is allowed without all required fields present.

### 7.1 Required Fields

| Field | Type | Description |
|---|---|---|
| `compute_request_id` | string | Unique ID for this compute request |
| `trigger_id` | string | ID of the originating trigger event |
| `trigger_type` | string | Trigger taxonomy code (see Section 6) |
| `intent_id` | string | Intent ID from Phase 6D routing contract |
| `skill_id` | string | Skill ID from Phase 6C skill contract |
| `context_package_id` | string | Context package ID from Phase 6E |
| `confidence_package_id` | string \| null | Confidence package ID from Phase 6F (if available) |
| `requested_by_user_id` | string | Authenticated user ID initiating the request |
| `org_scope` | string | Organisation boundary for this compute request |
| `compute_class` | string | One of the compute classes in Section 8 |
| `estimated_cost_class` | string | One of the cost classes in Section 8 |
| `max_runtime_seconds` | integer | Maximum allowed wall-clock runtime |
| `max_context_items` | integer | Maximum number of context items loaded |
| `max_model_calls` | integer | Maximum number of model/LLM calls permitted |
| `rate_limit_key` | string | Key used for per-user / per-org rate limiting |
| `requires_user_confirmation` | boolean | True if user must explicitly confirm before compute runs |
| `requires_review` | boolean | True if output must enter review queue before delivery |
| `fallback_behavior` | string | Safe fallback outcome code (see Section 10) |
| `audit_log_required` | boolean | Always true for triggered expensive compute |
| `no_fake_data_confirmation` | boolean | Must be true; blocks compute if false |

### 7.2 Contract Enforcement Rules

- `no_fake_data_confirmation: false` must block compute immediately.
- `requires_user_confirmation: true` must pause the request until the user explicitly approves.
- `requires_review: true` must route output to the Phase 6H review queue before delivery.
- `audit_log_required: true` must produce an audit log entry on request completion or
  failure, regardless of outcome.
- Any missing required field must trigger the `unsupported_trigger` fallback.

---

## 8) Required Cost Classes

Five conceptual cost classes govern all future compute requests. No runtime billing or
cost tracking is implemented in Phase 6G.

| Cost class | Description | Examples |
|---|---|---|
| `free_deterministic` | Always-on cheap deterministic compute; no model calls | Score engine, match state, metadata registry, phase tags |
| `low_cost_local` | Lightweight rule-based or template computation; no LLM | Deterministic prediction output, basic stat summaries |
| `moderate_model_compute` | Model inference with bounded context; single model call | Win-probability inference for one match, single-skill LLM explanation |
| `high_cost_ai_generation` | Long-form generation; chained skills; multiple model calls | Full match report, podcast breakdown, scouting narrative |
| `blocked_without_approval` | Compute that must not run without explicit administrator approval | Bulk re-processing, cross-org analysis, model retraining triggers |

---

## 9) Required Guardrails

These guardrails must be enforced when the runtime event-triggered compute layer is
implemented. They are documented here as future architecture requirements.

1. **No page-load compute**: Expensive AI must not run on page load or dashboard refresh.
2. **No per-ball compute**: Expensive AI must not run on every ball or score update.
3. **Rate limiting required**: Expensive AI must not run repeatedly for the same
   user/org/skill without enforced rate limits (`rate_limit_key`).
4. **Role/org authorization required**: Expensive AI must not run without valid role and
   org-scope authorization confirmed before trigger eligibility is evaluated.
5. **Sufficient context required**: Expensive AI must not run when the Phase 6E context
   package returns `insufficient_data` or `context_budget_exceeded`.
6. **Metadata-only gate**: Expensive AI must not run on historical import data when
   `training_eligible = false` (metadata-only import pending full delivery apply).
7. **Youth/safety review gate**: Expensive AI must not run for youth-player-sensitive
   outputs without the `requires_review: true` path confirmed.
8. **Audit metadata required**: Expensive AI must not run without producing a complete
   compute budget package and audit log entry.

---

## 10) Required Fallback Behavior

When a compute request cannot proceed, it must resolve to one of the following safe
fallback outcomes. Fallback codes must be returned to the caller and logged.

| Fallback code | Meaning |
|---|---|
| `deterministic_summary_only` | Only always-on deterministic output is available; no AI output |
| `requires_user_confirmation` | Compute is eligible but requires explicit user confirmation |
| `compute_budget_exceeded` | Request exceeds `max_model_calls`, `max_runtime_seconds`, or token cap |
| `rate_limited` | User/org has exceeded the rate limit for this `rate_limit_key` |
| `insufficient_context` | Phase 6E context package reports `insufficient_data` or budget exceeded |
| `metadata_only_pending_full_import` | Historical import is metadata-only; full import required first |
| `not_authorized` | Role/org authorization failed before or during eligibility check |
| `review_required_before_generation` | Output requires review but no review queue path is configured |
| `blocked_by_cost_policy` | Compute class is `blocked_without_approval` and approval is absent |
| `unsupported_trigger` | Trigger type is not in the approved taxonomy or required fields are missing |

---

## 11) Required Example Compute Contracts

### 11.1 — Coach Asks for Spin Weakness Explanation

**Scenario**: A coach with Coach Pro Plus access asks the Cricksy assistant why a specific
batter is weak against left-arm spin.

```yaml
compute_request_id: "cr_ex_001"
trigger_id: "trig_001"
trigger_type: "user.coach_question"
intent_id: "explain_spin_weakness"
skill_id: "spin_weakness_analysis.v1"
context_package_id: "ctx_ex_001"
confidence_package_id: "conf_ex_001"
requested_by_user_id: "user_coach_001"
org_scope: "org_001"
compute_class: "moderate_model_compute"
estimated_cost_class: "moderate_model_compute"
max_runtime_seconds: 30
max_context_items: 20
max_model_calls: 1
rate_limit_key: "org_001:spin_weakness:user_coach_001"
requires_user_confirmation: false
requires_review: false
fallback_behavior: "deterministic_summary_only"
audit_log_required: true
no_fake_data_confirmation: true
```

- **Trigger type**: User-initiated (`user.coach_question`)
- **Allowed compute class**: `moderate_model_compute` — single explanation call
- **Budget rules**: 1 model call, 30-second cap, 20 context items max
- **Context requirements**: Selected batter, at least one completed match, delivery-level data required
- **Confidence requirements**: `data_quality_confidence >= 0.6`; `sample_size_confidence >= 0.5`
- **Review requirements**: Not required unless youth player or low confidence
- **Fallback behavior**: `deterministic_summary_only` — return raw spin economy stats without narrative

---

### 11.2 — Analyst Requests Podcast Breakdown for One Match

**Scenario**: An Analyst Pro user requests a full podcast breakdown for a completed match
to be used as editorial content.

```yaml
compute_request_id: "cr_ex_002"
trigger_id: "trig_002"
trigger_type: "user.podcast_breakdown_request"
intent_id: "prepare_podcast_breakdown"
skill_id: "analyst_media_report.v1"
context_package_id: "ctx_ex_002"
confidence_package_id: "conf_ex_002"
requested_by_user_id: "user_analyst_001"
org_scope: "org_001"
compute_class: "high_cost_ai_generation"
estimated_cost_class: "high_cost_ai_generation"
max_runtime_seconds: 120
max_context_items: 60
max_model_calls: 4
rate_limit_key: "org_001:podcast_breakdown:daily"
requires_user_confirmation: true
requires_review: true
fallback_behavior: "review_required_before_generation"
audit_log_required: true
no_fake_data_confirmation: true
```

- **Trigger type**: User-initiated (`user.podcast_breakdown_request`)
- **Allowed compute class**: `high_cost_ai_generation` — long-form multi-skill generation
- **Budget rules**: 4 model calls max, 120-second cap, daily org rate limit applies
- **Context requirements**: Full match scorecard with deliveries; `validation_status = valid`
- **Confidence requirements**: `overall_confidence >= 0.7`; `model_confidence` must not be `not_applicable`
- **Review requirements**: Required — podcast/media content must enter editorial review queue before release
- **Fallback behavior**: `review_required_before_generation` — generation blocked until review path confirmed

---

### 11.3 — Collapse Detected During Live Match; AI Generation Deferred

**Scenario**: The deterministic score engine detects a batting collapse (3 wickets in
12 balls). A match-state trigger is raised, but AI generation is deferred until a coach
explicitly opens the insight panel.

```yaml
compute_request_id: "cr_ex_003"
trigger_id: "trig_003"
trigger_type: "match.collapse_detected"
intent_id: "explain_collapse_context"
skill_id: "match_momentum.v1"
context_package_id: null
confidence_package_id: null
requested_by_user_id: null
org_scope: "org_001"
compute_class: "moderate_model_compute"
estimated_cost_class: "moderate_model_compute"
max_runtime_seconds: 20
max_context_items: 15
max_model_calls: 1
rate_limit_key: "org_001:collapse_insight:match_live_001"
requires_user_confirmation: true
requires_review: false
fallback_behavior: "requires_user_confirmation"
audit_log_required: true
no_fake_data_confirmation: true
```

- **Trigger type**: Match-state (`match.collapse_detected`)
- **Allowed compute class**: `moderate_model_compute` — deferred until coach confirms
- **Budget rules**: 1 model call, 20-second cap; compute is queued, not run immediately
- **Context requirements**: Current innings state, last 12 deliveries, bowling figures
- **Confidence requirements**: Live match data; `data_quality_confidence` based on scored deliveries
- **Review requirements**: Not required (in-match tactical insight, not youth-sensitive)
- **Fallback behavior**: `requires_user_confirmation` — collapse is flagged in UI; AI narrative
  runs only after coach taps "Show Insight"

---

### 11.4 — Video Uploaded and Analysis Completed; Coach Requests Technical Summary

**Scenario**: A coach uploads a training session video. The video job completes (`done`).
The coach then explicitly requests a technical batting summary for one player.

```yaml
compute_request_id: "cr_ex_004"
trigger_id: "trig_004"
trigger_type: "user.match_player_analysis_request"
intent_id: "generate_video_technical_summary"
skill_id: "video_batting_technique.v1"
context_package_id: "ctx_ex_004"
confidence_package_id: "conf_ex_004"
requested_by_user_id: "user_coach_001"
org_scope: "org_001"
compute_class: "high_cost_ai_generation"
estimated_cost_class: "high_cost_ai_generation"
max_runtime_seconds: 90
max_context_items: 30
max_model_calls: 2
rate_limit_key: "org_001:video_summary:user_coach_001"
requires_user_confirmation: false
requires_review: true
fallback_behavior: "deterministic_summary_only"
audit_log_required: true
no_fake_data_confirmation: true
```

- **Trigger type**: User-initiated (`user.match_player_analysis_request`) — follows
  `data.video_analysis_completed` data trigger which made compute eligible
- **Allowed compute class**: `high_cost_ai_generation` — video model + narrative generation
- **Budget rules**: 2 model calls, 90-second cap, per-user rate limit
- **Context requirements**: Video job terminal state must be `done`/`completed`; tagged clip
  data and player profile required
- **Confidence requirements**: `video_confidence >= 0.6`; `data_quality_confidence >= 0.7`
- **Review requirements**: Required — technical coaching feedback for player must enter
  review queue (may affect training/selection decisions)
- **Fallback behavior**: `deterministic_summary_only` — return video job tagging statistics
  without narrative if model call budget is exceeded

---

### 11.5 — Metadata-Only Historical ZIP Intake Completes; Full AI Analysis Blocked

**Scenario**: A bulk ZIP import of 50 historical matches completes the dry-run and apply
steps, creating games with `training_eligible = false`. An analyst requests an AI-powered
cross-match analysis report. The request is blocked until full delivery data is applied.

```yaml
compute_request_id: "cr_ex_005"
trigger_id: "trig_005"
trigger_type: "user.analyst_report_request"
intent_id: "generate_cross_match_analysis"
skill_id: "cross_match_pattern_analysis.v1"
context_package_id: "ctx_ex_005"
confidence_package_id: "conf_ex_005"
requested_by_user_id: "user_analyst_001"
org_scope: "org_001"
compute_class: "high_cost_ai_generation"
estimated_cost_class: "blocked_without_approval"
max_runtime_seconds: 180
max_context_items: 200
max_model_calls: 6
rate_limit_key: "org_001:cross_match_analysis:daily"
requires_user_confirmation: true
requires_review: true
fallback_behavior: "metadata_only_pending_full_import"
audit_log_required: true
no_fake_data_confirmation: true
```

- **Trigger type**: User-initiated (`user.analyst_report_request`) — but blocked at
  eligibility check
- **Allowed compute class**: `blocked_without_approval` — `training_eligible = false` means
  full AI analysis is not permitted; escalates to `metadata_only_pending_full_import`
- **Budget rules**: Not reached — request is blocked at the eligibility check stage
- **Context requirements**: All selected matches must have `training_eligible = true`
  (full delivery data applied and `validation_status = valid`)
- **Confidence requirements**: Not evaluated — request is blocked before confidence assembly
- **Review requirements**: Would be required on approval, but moot until eligibility passes
- **Fallback behavior**: `metadata_only_pending_full_import` — analyst receives message
  explaining that delivery data must be applied before cross-match AI analysis is available

---

## 12) Trigger Eligibility Check Flow (Future Implementation Guidance)

When a trigger fires, the following checks must be evaluated in order before a compute
request is approved. This is a governance specification; it is not a runtime implementation.

```text
1. Trigger taxonomy check
   → Is the trigger_type in the approved taxonomy?
   → If not: fallback = unsupported_trigger

2. Role + org authorization check
   → Does the requesting user have the required role for this compute class?
   → Is the org_scope valid for this user?
   → If not: fallback = not_authorized

3. Safety check
   → Does this output involve a youth player?
   → If yes: requires_review must be set to true and review path must be confirmed
   → If review path is not configured: fallback = review_required_before_generation

4. Context budget check
   → Does the Phase 6E context package return sufficient_data?
   → Is the context package within max_context_items?
   → If not: fallback = insufficient_context

5. Compute budget check
   → Is the compute_class within the approved cost class for this trigger/role?
   → Is max_model_calls within limit?
   → Is the rate_limit_key below the rate threshold?
   → If not: fallback = compute_budget_exceeded | rate_limited | blocked_by_cost_policy

6. Confidence / necessity check
   → Does the Phase 6F confidence package meet the minimum confidence threshold for
     this skill?
   → Is no_fake_data_confirmation = true?
   → If not: fallback = insufficient_context | deterministic_summary_only

7. User confirmation check (if requires_user_confirmation = true)
   → Has the user explicitly approved this compute request?
   → If not: fallback = requires_user_confirmation

8. Approved — compute proceeds
   → Compute budget package is fully populated.
   → Audit log entry is written on start.
   → Output is produced with cost/audit metadata.
   → If requires_review: route to Phase 6H review queue.
   → Audit log entry updated on completion or failure.
```

---

## 13) Relationship to Phase 6H — Validation Agents + Review Queue Spec

Phase 6G defines **when compute is allowed to run**: trigger eligibility, cost class,
budget governance, role/org authorization, context sufficiency, and audit requirements.

Phase 6H (to be defined) will define **how review is carried out** after compute
is requested or completed: validation agent mechanics, review queue routing, approval
workflows, re-submission rules, and escalation paths.

Phase 6H must not be collapsed into Phase 6G.

The `requires_review: true` flag produced by Phase 6G compute budget packages is the
input signal to the Phase 6H review queue. The mechanics of that queue — how it routes,
validates, approves, or rejects outputs — are Phase 6H's responsibility.

---

## 14) Protected Systems (Unchanged by This Phase)

- official score/runs/balls/overs/wickets/innings state/match result/scorecards/player stats
- DLS calculations
- gameplay/live bus behavior
- historical import validation/provenance/training-eligibility gates
- Phase 5M registry endpoint behavior
- Phase 6B AI boundary guard behavior (`backend/domain/ai_boundary.py`)
- Phase 6C skill contract behavior
- Phase 6D intent/skill routing boundaries
- Phase 6E context-loading boundaries
- Phase 6F confidence/uncertainty boundaries
- Coach Pro Plus/video analysis runtime
- mental analysis runtime
- auth/RBAC/org boundaries
- fake-data guard (`scripts/check-fake-data.js`)
- CI/CD gates (`.github/workflows/ci.yml`)
- `backend/services/agent_budget.py` runtime logic (extended in future but not changed here)

---

## 15) Future Event-Triggered Compute Validation Requirements

When a runtime event-triggered compute layer is implemented later, tests must include
at minimum:

- Compute budget package completeness tests (all required fields present).
- `no_fake_data_confirmation: false` blocks compute immediately.
- `requires_user_confirmation: true` pauses compute until user approves.
- `requires_review: true` routes output to Phase 6H review queue.
- `audit_log_required: true` produces a complete audit log entry.
- Blocked trigger tests — verify no expensive compute fires on: every ball, page load,
  dashboard refresh, every import file, every video frame.
- Rate limit enforcement tests for each `rate_limit_key` pattern.
- Metadata-only gate tests — `training_eligible = false` blocks `high_cost_ai_generation`
  and `blocked_without_approval` compute classes.
- Youth-safety gate tests — youth player target triggers `requires_review: true`.
- Role/org authorization tests — compute blocked when role is insufficient.
- Fallback code accuracy tests — every defined fallback code returned correctly.
- Cost class routing tests — `free_deterministic` bypasses all gates; `blocked_without_approval`
  requires administrator approval.
- Regression tests proving Phase 6B official-truth mutation guard remains intact after
  any event-triggered compute completes.
- Regression tests proving Phase 6E context-loading boundaries are not expanded by
  compute triggers.
- Regression tests proving Phase 6F confidence packages are correctly forwarded to
  compute eligibility checks.

---

## 16) Validation Notes

- Markdown formatting reviewed (headings, tables, fenced code blocks, lists).
- Phase ordering remains clear; Phase 6H remains a future phase and is not marked complete.
- This phase is architecture/spec-lock only; no runtime event bus, queue, worker, agent,
  skill, router, Supervisor logic, LLM call, migration, dependency, or production behavior
  change was added.
- No new dependencies, AWS services, migrations, or external AI provider calls added.
- `backend/services/agent_budget.py` runtime behavior is not changed.
- Phase 6B AI boundary guard, Phase 6C skill contract, Phase 6D routing contract,
  Phase 6E context-loading rules, and Phase 6F confidence package contract remain intact.

---

## 17) Confirmation Statements

- This is event-triggered compute architecture/spec only.
- No runtime event bus, queue, worker, scheduler, or agent was implemented.
- No runtime skill, router, or Supervisor logic was implemented.
- No LLM calls or external AI provider calls were added.
- No new AWS services, migrations, dependencies, or infrastructure were added.
- No production runtime behavior changed.
- No scoring, DLS, gameplay, live bus, historical import truth, or registry behavior changed.
- Phase 6B–6F boundaries remain fully intact.

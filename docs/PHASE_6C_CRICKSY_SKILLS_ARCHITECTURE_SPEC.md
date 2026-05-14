# PHASE 6C — CRICKSY SKILLS ARCHITECTURE SPEC

## Status

Spec-lock complete. Architecture only.

No runtime skills, routers, agents, Supervisor logic, LLM workflows, migrations, dependencies, or production behavior changes are implemented in this phase.

---

## 1) Purpose

Define Cricksy Skills before implementation work begins.

Core product principle:

```text
Cricksy skills are reusable, governed sports intelligence modules.
```

Failure mode to prevent:

```text
Agents repeatedly relearn cricket logic and generate inconsistent analysis.
```

Outcome enabled:

```text
Reusable, tested, versioned cricket intelligence standards used across analysts, coaches, reports, and future agents.
```

---

## 2) Pre-Phase Audit Summary

### A. Existing Phase 6A/6B governance and Intelligence System Rule

- `docs/PHASE_6A_CRICKSY_INTELLIGENCE_OS_AUDIT_AND_SPEC_LOCK.md` defines governance, protected systems, and future phase separation.
- `docs/PHASE_6B_DETERMINISTIC_AI_BOUNDARY_ENFORCEMENT.md` converts those rules into enforceable boundaries.
- Intelligence System Rule remains:

```text
Deterministic systems calculate facts.
AI systems explain, summarize, recommend, or communicate.
No LLM may calculate, overwrite, or mutate official cricket truth.
```

### B. Existing AI boundary guard module

- `backend/domain/ai_boundary.py` already enforces:
  - `AiOutputType`
  - `OFFICIAL_TRUTH_FIELDS`
  - `AiOutputMetadata`
  - `validate_no_official_truth_mutation(payload, context)`

### C. Existing AI response schemas carrying `ai_metadata`

- `backend/services/ai_commentary.py` → `AiCommentaryResponse.ai_metadata`
- `backend/sql_app/match_ai.py` → `MatchAiCommentaryResponse.ai_metadata`, `MatchAiSummaryResponse.ai_metadata`
- `backend/services/ai_player_insights.py` → `PlayerAiInsights.ai_metadata`

### D. Deterministic analytics/statistics/match data surfaces

- `backend/routes/analytics_case_study.py`
- `backend/services/analytics_case_study.py`
- `backend/routes/analytics.py`
- `backend/routes/phase_analysis.py`
- `backend/routes/player_analytics.py`
- `backend/routes/prediction.py`
- `backend/services/prediction_service.py`

### E. Historical import / registry / provenance / training eligibility foundation

- `backend/routes/historical_import.py` (dry-run/apply/rollback/training status/bulk zip)
- `backend/services/historical_import_preview.py`
- `backend/services/historical_import_apply_service.py`
- `backend/services/historical_import_backfill_service.py`
- `backend/routes/analytics_case_study.py` registry endpoint (`/analytics/matches/{match_id}/registry`)

### F. Analyst Workspace match-data surfaces

- `frontend/src/views/AnalystWorkspaceView.vue`
- `backend/routes/analytics_case_study.py` (`/analytics/matches`, `/case-study`, `/registry`, `/ai-summary`)
- `backend/services/analyst_access.py` scoped game visibility

### G. Coach Pro Plus / video-analysis outputs

- `backend/routes/coach_pro_plus.py` analysis jobs, retries, exports, and result surfaces
- `backend/services/coach_ai_pipeline.py` deterministic/rule-based pipeline
- `backend/services/coach_report_service.py` report generation surfaces
- `backend/services/pdf_export_service.py` export surfaces

### H. Fake-data guard and no-fake-data requirement

- `scripts/check-fake-data.js` enforces fake-data pattern checks.
- `.github/workflows/ci.yml` runs `npm run guard:fake-data`.

### I. Auth / RBAC / org boundaries

- `backend/security.py` user auth + `require_roles`
- `backend/services/analyst_access.py` org/user match scoping
- Existing route-level role checks across analytics and coach surfaces

### J. Tests and CI gates relevant to future skill validation

- `.github/workflows/ci.yml` runs:
  - pre-commit
  - ruff + format + mypy
  - bandit + pip-audit
  - backend fast + integration + DLS tests
  - frontend fake-data guard + type-check + build
- `backend/tests/test_phase_6b_ai_boundary.py` protects deterministic-vs-AI boundary rules.

### K. Existing “skill-like” logic already in repo

- `backend/services/ai_commentary.py` (delivery commentary module)
- `backend/services/match_ai_service.py` (match commentary/summary module)
- `backend/services/ai_player_insights.py` (player insights module)
- `backend/services/ai_match_summary.py` (structured match narrative builder)
- `backend/services/coach_report_service.py` (coach report synthesis)

These are not governed reusable skills yet; Phase 6C defines the contract needed to standardize future implementations.

---

## 3) Strict Scope Lock

### Allowed in Phase 6C

- Skills architecture spec documentation
- Skill contract definition
- Future skill categories
- Sample skill specs
- Validation/testing requirements for future implementation
- Explicit Phase 6B boundary integration rules
- Progressive disclosure/confidence/limitations/review requirements

### Not allowed in Phase 6C

- Runtime skill implementation
- Backend skill registry implementation
- Skill Router / Intent Router / Supervisor implementation
- Agent implementation
- LLM workflow/provider calls
- Migrations or dependencies
- Changes to scoring/DLS/gameplay/historical-import truth behavior

---

## 4) Required Cricksy Skill Contract (Mandatory Fields)

Every future Cricksy Skill must define all fields below:

- `skill_id`
- `name`
- `version`
- `category`
- `purpose`
- `supported_intents`
- `allowed_roles`
- `required_inputs`
- `optional_inputs`
- `deterministic_data_dependencies`
- `forbidden_inputs`
- `output_type`
- `ai_boundary_metadata`
- `confidence_fields`
- `limitations_fields`
- `validation_rules`
- `safety_rules`
- `youth_safety_rules`
- `organization_data_boundary_rules`
- `no_fake_data_rule`
- `review_required`
- `sample_output_shape`
- `tests_required`
- `rollback_or_disable_strategy`

### 4A) Reference contract shape (docs-only, non-runtime)

```yaml
skill_id: "match_momentum.v1"
name: "Match Momentum Skill"
version: "1.0.0"
category: "match_analysis"
purpose: "Explain decisive momentum swings using deterministic phase/delivery evidence."
supported_intents: ["analyze_momentum", "explain_turning_points"]
allowed_roles: ["analyst_pro", "coach_pro", "coach_pro_plus", "org_pro"]
required_inputs:
  - match_id
optional_inputs:
  - innings
  - over_range
deterministic_data_dependencies:
  - analytics_case_study.phase_breakdown
  - game.deliveries
  - prediction.win_probability_series
forbidden_inputs:
  - unrestricted_all_matches_dump
  - unrestricted_all_players_dump
output_type: "insight"
ai_boundary_metadata:
  is_official_truth: false
  output_type: "insight"
  requires_review: false
  grounded_in_data: true
confidence_fields:
  - data_quality_confidence
  - sample_size_confidence
  - tactical_confidence
  - recommendation_confidence
  - overall_confidence
limitations_fields:
  - limitations
validation_rules:
  - must_call_validate_no_official_truth_mutation
  - must_include_source_citations
safety_rules:
  - no_harmful_or_abusive_language
youth_safety_rules:
  - null_if_not_youth_context
organization_data_boundary_rules:
  - enforce_role_checks
  - enforce_org_scoping
no_fake_data_rule: "If deterministic data is unavailable, return insufficient_data."
review_required: false
sample_output_shape:
  insight: "Momentum shifted in overs 14-16 after two wickets and RR drop."
  confidence:
    overall_confidence: 0.78
tests_required:
  - contract_validation_test
  - deterministic_dependency_test
  - no_official_truth_mutation_test
  - confidence_labeling_test
rollback_or_disable_strategy: "Feature flag disable + fallback insufficient_data response."
```

---

## 5) Required Future Skill Categories

### Match Analysis Skills

- Match Momentum Skill
- Batting Collapse Skill
- Powerplay Skill
- Pressure Overs Skill
- Death Overs Skill
- Phase Comparison Skill

### Player Analysis Skills

- Spin Weakness Skill
- Pace Weakness Skill
- Bowling Fatigue Skill
- Player Form Trend Skill
- Shot Selection Skill
- Workload Risk Skill

### Team / Opposition Skills

- Opposition Scout Skill
- Team Balance Skill
- Matchup Analysis Skill
- Field Placement Skill
- Tactical Pattern Skill

### Coach / Communication Skills

- Coach Communication Skill
- Youth Safety Skill
- Report Writing Skill
- Recommendation Framing Skill
- Development Plan Skill

### Data / Validation Skills

- Data Validation Skill
- Metadata Quality Skill
- Training Eligibility Review Skill
- Confidence Calibration Skill
- Source Citation Skill

---

## 6) Required Skill Rules

### Rule 1 — Deterministic Data First

Skills must consume bounded deterministic data products, not raw unbounded context.

Approved dependency examples:

- computed metrics
- validated match registry data
- delivery subsets
- player-specific slices
- phase summaries
- video tags/clips (where available)
- confidence scores

### Rule 2 — No Official Truth Mutation (Phase 6B)

No skill may calculate, overwrite, or mutate official cricket truth.

Skills may only produce:

- insight
- summary
- recommendation
- commentary
- report draft
- reviewable output

### Rule 3 — Progressive Disclosure

Load only minimum data needed for the question.

For: “Why did Player X struggle against spin today?”

Allowed:

- Player X
- today’s innings
- spin deliveries
- recent spin weakness summary
- confidence metrics
- relevant video tags/clips

Not allowed:

- all players
- all seasons
- all matches
- all reports

### Rule 4 — Confidence Required

Skills must include:

- `data_quality_confidence`
- `sample_size_confidence`
- `tactical_confidence`
- `video_confidence` (if video used)
- `recommendation_confidence`
- `overall_confidence`
- `limitations`

Low-confidence outputs must be clearly labeled.

### Rule 5 — Review Requirements

`review_required=true` is mandatory for high-impact outputs including:

- youth player feedback
- mental/performance criticism
- coach reports
- scouting reports
- public/podcast content
- training recommendations
- injury/workload recommendations

### Rule 6 — No Fake Data

Skills must never fabricate production facts.

If required deterministic inputs are missing, return explicit `insufficient_data` / `unavailable` states.

### Rule 7 — Role and Organization Boundaries

Every skill invocation must enforce:

- user role authorization
- organization ownership boundaries
- team/player visibility rules
- analyst/coach permission scope
- youth-safety constraints where relevant

---

## 7) Protected Systems and Forbidden Behavior

Skills must not change or weaken:

- official score/runs/balls/overs/wickets/innings state/result/scorecards/player stats
- DLS calculations
- gameplay/live bus behavior
- historical import validation and apply/rollback safety gates
- metadata-only training eligibility gates
- Phase 5M registry endpoint behavior
- Coach Pro Plus/video-analysis runtime
- mental-analysis runtime
- auth/RBAC/org boundaries
- fake-data guard
- CI/CD gates
- Phase 6B AI boundary guard behavior

---

## 8) Sample Skill Specs (Fully Written Examples)

## 8.1 Match Momentum Skill

- `skill_id`: `match_momentum.v1`
- `name`: Match Momentum Skill
- `version`: `1.0.0`
- `category`: `match_analysis`
- `purpose`: Identify and explain decisive momentum swings using deterministic event evidence.
- `supported_intents`: `["analyze_momentum", "case_study_turning_points"]`
- `allowed_roles`: `["analyst_pro", "coach_pro_plus", "org_pro"]`
- `required_inputs`: `match_id`
- `optional_inputs`: `innings`, `over_range`
- `deterministic_data_dependencies`:
  - `analytics_case_study` phase breakdown
  - `game.deliveries` subsets
  - deterministic win-probability output (if available)
- `forbidden_inputs`: all-season raw corpus; cross-org data
- `output_type`: `insight`
- `ai_boundary_metadata`: `{ output_type: insight, is_official_truth: false, requires_review: false, grounded_in_data: true }`
- `confidence_fields`: data quality, sample size, tactical, recommendation, overall
- `limitations_fields`: missing delivery granularity, sparse momentum events
- `validation_rules`:
  - enforce `validate_no_official_truth_mutation`
  - verify org-scoped match access
  - require source-event citations (overs/balls/phases)
- `safety_rules`: no personal attacks or harmful language
- `youth_safety_rules`: neutral tone if youth context present
- `organization_data_boundary_rules`: user may only analyze permitted org matches
- `no_fake_data_rule`: if insufficient delivery events, return `insufficient_data`
- `review_required`: `false` (unless promoted into external/public report)
- `sample_output_shape`:
  - momentum_swings: `[{"over_range":"14.1-16.0","impact":"-18 RR swing"}]`
  - narrative: `"Momentum flipped after two wickets in 15th over."`
  - confidence: `{overall_confidence: 0.81}`
  - limitations: `["Win probability series unavailable for overs 1-3"]`
- `tests_required`:
  - contract schema test
  - deterministic dependency presence test
  - confidence + limitations presence test
  - insufficient-data fallback test
  - no-truth-mutation test
- `rollback_or_disable_strategy`: feature-flag disable; fallback to deterministic phase summary only
- Failure behavior: return honest `insufficient_data` with missing dependencies list

## 8.2 Spin Weakness Skill

- `skill_id`: `player_spin_weakness.v1`
- `name`: Spin Weakness Skill
- `version`: `1.0.0`
- `category`: `player_analysis`
- `purpose`: Explain observed player performance patterns against spin using deterministic ball-level slices.
- `supported_intents`: `["analyze_player_vs_spin", "batting_weakness_review"]`
- `allowed_roles`: `["analyst_pro", "coach_pro", "coach_pro_plus", "org_pro"]`
- `required_inputs`: `player_id`, `match_id_or_window`
- `optional_inputs`: `format_filter`, `innings_filter`
- `deterministic_data_dependencies`:
  - player delivery slices vs spin type
  - dismissal patterns
  - shot/outcome tags
  - case-study phase context
  - relevant video tags/clips (if available)
- `forbidden_inputs`: unbounded all-player context; unverified external notes
- `output_type`: `insight`
- `ai_boundary_metadata`: `{ output_type: insight, is_official_truth: false, requires_review: true, grounded_in_data: true }`
- `confidence_fields`: data quality, sample size, tactical, video (if used), recommendation, overall
- `limitations_fields`: sample size caveats, opposition-strength caveat, missing video caveat
- `validation_rules`:
  - minimum sample threshold before tactical claims
  - low-confidence label enforcement
  - cross-check against deterministic dismissal/event tags
- `safety_rules`: no abusive or humiliating framing
- `youth_safety_rules`: mandatory constructive wording for youth players
- `organization_data_boundary_rules`: enforce org and role scope for player visibility
- `no_fake_data_rule`: no synthetic deliveries or inferred clips when unavailable
- `review_required`: `true` for youth contexts or coach-facing recommendations
- `sample_output_shape`:
  - finding: `"Player struggles vs leg-spin length outside off in middle overs."`
  - evidence: `["9 dot balls", "2 dismissals", "SR 76 in sample"]`
  - recommendation_draft: `"Prioritize sweep/rotation drills vs leg-spin in overs 7-12."`
  - confidence: `{sample_size_confidence: 0.62, overall_confidence: 0.67}`
  - limitations: `["Sample only 3 matches", "No tagged video for one dismissal"]`
- `tests_required`:
  - contract schema test
  - role/org boundary test
  - youth-safe language test
  - confidence labeling + low-confidence warning test
  - insufficient-data honest fallback test
  - no-truth-mutation test
- `rollback_or_disable_strategy`: disable recommendation section first; preserve deterministic evidence table only
- Failure behavior: return `insufficient_data` when sample threshold unmet

## 8.3 Coach Communication Skill

- `skill_id`: `coach_communication.v1`
- `name`: Coach Communication Skill
- `version`: `1.0.0`
- `category`: `coach_communication`
- `purpose`: Convert deterministic findings into coach-ready communication drafts that are safe, constructive, and reviewable.
- `supported_intents`: `["draft_coach_message", "report_framing"]`
- `allowed_roles`: `["coach_pro", "coach_pro_plus", "org_pro"]`
- `required_inputs`: `finding_bundle_id`, `audience_type`
- `optional_inputs`: `tone_preference`, `age_group_context`
- `deterministic_data_dependencies`:
  - approved findings from deterministic/validated skill outputs
  - confidence + limitations metadata
  - training eligibility and provenance context where relevant
- `forbidden_inputs`: unsupported personal/medical claims; unreviewed external narratives
- `output_type`: `draft`
- `ai_boundary_metadata`: `{ output_type: draft, is_official_truth: false, requires_review: true, grounded_in_data: true }`
- `confidence_fields`: data quality, tactical, recommendation, overall
- `limitations_fields`: communication ambiguity caveats, missing context caveats
- `validation_rules`:
  - requires citation of source findings
  - blocks publication when confidence below threshold
  - enforces review queue for youth/high-impact contexts
- `safety_rules`: no harmful language, defamation, or certainty inflation
- `youth_safety_rules`: always constructive, age-appropriate, and non-stigmatizing
- `organization_data_boundary_rules`: cannot include data from non-visible players/teams/orgs
- `no_fake_data_rule`: if source findings unavailable, return unavailable state
- `review_required`: `true`
- `sample_output_shape`:
  - draft_message: `"Key focus: improve strike rotation against left-arm spin in overs 7-12."`
  - source_citations: `["spin_weakness.v1 finding #2", "match_momentum.v1 phase summary"]`
  - confidence: `{overall_confidence: 0.71}`
  - limitations: `["No video confirmation for net sessions"]`
  - review_status: `"pending_human_review"`
- `tests_required`:
  - contract schema test
  - required-review gating test
  - youth-safe language test
  - source-citation requirement test
  - no-fake-data fallback test
  - no-truth-mutation test
- `rollback_or_disable_strategy`: disable outward-facing draft generation; keep internal notes-only mode
- Failure behavior: return `unavailable` with explicit unmet requirements

---

## 9) Future-Phase Boundary (Do Not Collapse)

Phase 6C defines skill architecture only.

The following remain separate future phases:

- Phase 6D — Intent Router + Skill Router Spec
- Phase 6E — Progressive Disclosure + Context Loading Rules
- Phase 6F — Confidence + Uncertainty System Spec
- Phase 6G — Event-Triggered Intelligence Spec
- Phase 6H — Validation Agents + Review Queue Spec

None of Phase 6D–6H is implemented or marked complete in this phase.

---

## 10) Validation Notes

- Markdown formatting reviewed for headings, fenced blocks, and lists.
- Spec confirms stricter governance and no runtime expansion.
- Protected deterministic systems and Phase 6B boundary remain intact.
- This document defines architecture contracts only; no runtime behavior changes.

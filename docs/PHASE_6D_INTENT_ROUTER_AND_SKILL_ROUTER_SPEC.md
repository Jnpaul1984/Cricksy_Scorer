# PHASE 6D — INTENT ROUTER + SKILL ROUTER SPEC

## Status

Spec-lock complete. Architecture only.

No runtime Intent Router, Skill Router, Supervisor, agents, runtime skills, LLM workflows, migrations, dependencies, or production behavior changes are implemented in this phase.

---

## 1) Purpose

Define the future routing contract that safely maps requests to approved skills with minimum required context.

Failure mode to prevent:

```text
User asks a broad question → system loads too much data → wrong skill runs → AI produces unsupported or unsafe output.
```

Outcome enabled:

```text
User intent → approved skill → minimum required data → bounded output → validation/review where needed.
```

---

## 2) Required Future Architecture (Spec Only)

```text
User / Coach / Analyst Request
        ↓
Intent Classifier
        ↓
Intent Safety Gate
        ↓
Skill Eligibility Resolver
        ↓
Context Requirement Planner
        ↓
Progressive Disclosure Loader
        ↓
Skill Execution Request
        ↓
Validation / Review Routing
```

This phase defines interfaces/contracts only. Runtime implementation is deferred.

---

## 3) Pre-Phase Audit Summary

### A. Existing Phase 6A/6B/6C governance baseline

- `docs/PHASE_6A_CRICKSY_INTELLIGENCE_OS_AUDIT_AND_SPEC_LOCK.md`
- `docs/PHASE_6B_DETERMINISTIC_AI_BOUNDARY_ENFORCEMENT.md`
- `docs/PHASE_6C_CRICKSY_SKILLS_ARCHITECTURE_SPEC.md`
- `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`

### B. Existing skill contract and sample skills (Phase 6C)

- Phase 6C locked required skill fields, skill categories, and sample specs
  (Match Momentum Skill, Spin Weakness Skill, Coach Communication Skill).

### C. Existing AI boundary module and metadata enforcement

- `backend/domain/ai_boundary.py` defines `AiOutputType`, `OFFICIAL_TRUTH_FIELDS`,
  `AiOutputMetadata`, and `validate_no_official_truth_mutation`.
- AI response schemas remain non-authoritative via `ai_metadata` fields.

### D. Existing Analyst Workspace and match-data surfaces

- `frontend/src/views/AnalystWorkspaceView.vue`
- `backend/routes/analytics_case_study.py`
- `backend/services/analytics_case_study.py`
- `backend/services/analyst_access.py`

### E. Existing historical import / registry / provenance / training-eligibility surfaces

- `backend/routes/historical_import.py`
- `backend/routes/analytics_case_study.py` registry endpoint
- `backend/services/historical_import_preview.py`
- `backend/services/historical_import_apply_service.py`

### F. Existing Coach Pro Plus / video-analysis surfaces

- `backend/routes/coach_pro_plus.py`
- `backend/services/coach_ai_pipeline.py`
- `backend/services/coach_report_service.py`
- `backend/services/pdf_export_service.py`

### G. Existing AI-adjacent routes/services and current prompt-entry surfaces

- `backend/routes/ai.py` (delivery commentary request payload)
- `backend/services/ai_commentary.py` (rule-based commentary)
- `backend/services/match_ai_service.py` (rule-based/mocked match narrative)
- `backend/services/ai_player_insights.py` (insight generation surfaces)

### H. Existing auth/RBAC/org boundaries

- `backend/security.py` (`get_current_user`, `require_roles`)
- `backend/services/analyst_access.py` (org/user scoped game visibility)

### I. Existing fake-data guard and no-fake-data rules

- `scripts/check-fake-data.js`
- `.github/workflows/ci.yml` (`npm run guard:fake-data`)

### J. Existing tests and CI gates relevant to future routing

- `.github/workflows/ci.yml` jobs: pre-commit, lint, security, backend tests,
  frontend guard/type-check/build.
- `backend/tests/test_phase_6b_ai_boundary.py` enforces deterministic-vs-AI boundary.

### K. Existing ad-hoc intent-like behavior

- No centralized intent router exists today.
- AI-adjacent surfaces are endpoint-specific and hardcoded per route/service.
- Rule-based suggestion/commentary modules include local heuristics but no
  governed intent-classification pipeline.

---

## 4) Strict Scope Lock for Phase 6D

### Allowed

- This architecture/spec document.
- Master checklist update for Phase 6D completion notes.
- Intent taxonomy, routing contract, clarification/block/fallback rules.
- Role/org/youth/no-fake-data governance routing requirements.
- Future router test requirements.

### Not allowed

- Runtime Intent Router/Skill Router implementation.
- Supervisor/agent/runtime-skill implementation.
- LLM provider calls or external AI integration.
- Migrations, dependencies, infrastructure changes.
- Any scoring/DLS/gameplay/result/historical truth behavior changes.

---

## 5) Intent Taxonomy (Initial Locked Set)

### Match Analysis Intents

- `analyze_match_momentum`
- `explain_batting_collapse`
- `analyze_powerplay_performance`
- `analyze_pressure_overs`
- `compare_match_phases`

### Player Analysis Intents

- `analyze_spin_weakness`
- `analyze_pace_weakness`
- `review_player_form`
- `analyze_shot_selection`
- `review_bowling_fatigue`

### Team / Opposition Intents

- `prepare_opposition_report`
- `analyze_matchups`
- `review_team_balance`
- `analyze_field_strategy`

### Coach / Communication Intents

- `generate_coaching_notes`
- `frame_player_feedback`
- `prepare_development_plan`
- `rewrite_recommendation_safely`

### Analyst / Media Intents

- `prepare_podcast_breakdown`
- `generate_case_study_notes`
- `prepare_talking_points`
- `summarize_match_for_report`

### Data / Validation Intents

- `validate_match_data_quality`
- `review_metadata_quality`
- `review_training_eligibility`
- `cite_source_data`

### Blocked / Deterministic-Only Intents

These must not route to AI/skills:

- update official score
- change wickets/overs/balls
- override match result
- edit official player stats
- change DLS target/result
- mark metadata-only import as training eligible
- bypass validation gates

These must route to deterministic app workflows or be blocked.

---

## 6) Skill Routing Contract (Mandatory per Routeable Intent)

Every routeable intent definition must declare:

- `intent_id`
- `intent_category`
- `supported_user_phrases`
- `required_role`
- `allowed_skill_ids`
- `required_context`
- `forbidden_context`
- `clarifying_questions`
- `confidence_requirements`
- `review_requirements`
- `blocked_conditions`
- `fallback_behavior`
- `output_type`
- `ai_boundary_metadata`

### 6A) Docs-only reference shape

```yaml
intent_id: "analyze_match_momentum"
intent_category: "match_analysis"
supported_user_phrases:
  - "why did we lose momentum?"
required_role:
  - "analyst_pro"
  - "coach_pro"
  - "coach_pro_plus"
  - "org_pro"
allowed_skill_ids:
  - "match_momentum.v1"
required_context:
  - "match_id"
forbidden_context:
  - "cross_org_unscoped_dump"
clarifying_questions:
  - "Which match should I analyze?"
confidence_requirements:
  minimum_overall_confidence: 0.60
review_requirements:
  required: false
blocked_conditions:
  - "request_mutates_official_truth"
fallback_behavior:
  - "needs_clarification"
  - "insufficient_data"
output_type: "insight"
ai_boundary_metadata:
  is_official_truth: false
  grounded_in_data: true
```

---

## 7) Required Example Intent → Skill Mappings

1. **“Why did we lose momentum?”**
   - intent: `analyze_match_momentum`
   - skill: Match Momentum Skill (`match_momentum.v1`)

2. **“Why did Player X struggle against spin today?”**
   - intent: `analyze_spin_weakness`
   - skill: Spin Weakness Skill (`spin_weakness.v1`)

3. **“Prepare notes for my coach.”**
   - intent: `generate_coaching_notes`
   - skill: Coach Communication Skill (`coach_communication.v1`)

4. **“Create a podcast breakdown of this match.”**
   - intent: `prepare_podcast_breakdown`
   - skill: future Report Writing / Analyst Media Skill (`analyst_media_report.v1`)
   - review: required

5. **“Update the score to 156/4.”**
   - blocked from AI routing
   - deterministic scoring workflow only

---

## 8) Clarification Rules (Must Ask Before Routing)

Future router must ask clarifying questions when required context is missing or unsafe:

- “analyze him” with no selected player.
- “why did we lose?” with no selected match.
- report request without coach/analyst/media purpose.
- player-feedback request involving youth context without safety/review framing.
- training-eligibility request where match is metadata-only or unvalidated.

Clarification responses must return `needs_clarification` until mandatory context is provided.

---

## 9) Blocking Rules (Hard Governance Blocks)

Hard-block routing when requests:

- attempt to mutate official cricket truth via AI.
- attempt to bypass validation/training-eligibility gates.
- request invented/missing data fabrication.
- cross org/team/player visibility boundaries.
- request unsafe youth criticism framing.
- require certainty while confidence is below threshold.

---

## 10) Safe Fallback Outputs

Future router fallback statuses:

- `insufficient_data`
- `needs_clarification`
- `not_authorized`
- `deterministic_workflow_required`
- `review_required`
- `blocked_by_governance`
- `unsupported_intent`

Fallbacks must never fabricate evidence and must preserve deterministic authority boundaries.

---

## 11) Role / Org / Youth-Safety Routing Boundaries

- Role checks are mandatory before skill eligibility resolution.
- Org scoping is mandatory; cross-org data may not be loaded.
- Youth player feedback requires stricter language safety + review routing.
- High-impact coach/media outputs require explicit review routing when configured.
- No-fake-data rule applies to all routed outputs; when evidence is missing, return safe fallback.

---

## 12) Relationship to Phase 6E–6H (Separation Lock)

Phase 6D defines only:

```text
intent → skill → required context contract
```

Not in scope for Phase 6D:

- **Phase 6E**: detailed progressive disclosure/context-loading mechanics.
- **Phase 6F**: deeper confidence/uncertainty mechanics and scoring policy.
- **Phase 6G**: event-triggered compute orchestration policy.
- **Phase 6H**: validation-agent/review-queue runtime mechanics.

---

## 13) Protected Systems (Unchanged by This Phase)

- official score/runs/balls/overs/wickets/innings/result/scorecards/player stats
- DLS calculations and result logic
- gameplay/live bus behavior
- historical import validation/provenance/training-eligibility gates
- Phase 5M registry endpoint behavior
- Phase 6B AI boundary guard behavior
- Coach Pro Plus/video-analysis and mental-analysis runtime
- auth/RBAC/org boundaries
- fake-data guard
- CI/CD gates

---

## 14) Future Router Validation Requirements (Implementation Phase)

When runtime routing is later implemented, tests must include at minimum:

- intent-classification allowlist tests for all supported intents.
- deterministic-only intent block/redirect tests.
- role/org authorization routing tests.
- required-context clarification tests.
- insufficient-data/no-fake-data fallback tests.
- low-confidence review-routing tests.
- youth-safety language/review gating tests.
- ai-boundary metadata propagation tests.
- regression tests proving no mutation of official truth systems.

---

## 15) Confirmation Statements

- This phase is router architecture/spec only.
- No runtime Intent Router or Skill Router was implemented.
- No Supervisor/agent/runtime skill implementation was added.
- No production behavior changed.
- Phase 6B boundary and Phase 6C skill contract boundaries remain intact.


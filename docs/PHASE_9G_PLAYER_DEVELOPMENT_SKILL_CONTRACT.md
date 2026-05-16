# PHASE 9G — PLAYER DEVELOPMENT SKILL CONTRACT

## Status

Spec-lock complete. Contract registry added at `backend/domain/player_development_skill_contract.py`.

No runtime behavior, AI execution, live generation, migrations, or plan-activation logic is introduced
in this phase.

---

## 1) Purpose

Phase 9G locks the governed skill-contract layer for all future Cricksy Player Development
Intelligence features.

Core product principle (inherited from Phase 9A):

> Every player should leave the season measurably better than they started.

This phase defines how player-development skills are:

- **described** — versioned, named, purposeful
- **scoped** — bounded inputs, bounded outputs, role-gated access
- **validated** — evidence requirements, deterministic dependencies, review gates
- **governed** — Phase 6B/6C/6F inheritance, no official-truth mutation, no fake data
- **protected** — youth-safe language, forbidden outputs, fallback behaviors
- **reusable** — importable contract registry usable across plans, reports, dashboards,
  coach recommendations, and future AI workflows

---

## 2) Scope Lock

### Allowed in Phase 9G

- `docs/` spec document (this file)
- `backend/domain/player_development_skill_contract.py` — runtime-neutral contract registry
- `backend/tests/test_player_development_skill_contract.py` — contract-shape validation tests
- `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` checklist update
- `.mcp/checklist.yaml` and `.mcp/checklist.md` updates

### Explicitly NOT allowed in Phase 9G

- Backend migrations
- Scoring, DLS, result, or stat logic changes
- Plan activation or approval mutation
- Coach Pro Plus video-analysis pipeline or model behavior
- AI provider integrations
- Autonomous coaching workflows
- Player-facing or public-facing surfaces
- Report export or PDF behavior
- Scouting, selection, or ranking systems
- Frontend runtime changes

---

## 3) Phase 6 Governance Inheritance

Phase 9G inherits from and aligns with:

### Phase 6B — Deterministic AI Boundary Enforcement

Source: `docs/PHASE_6B_DETERMINISTIC_AI_BOUNDARY_ENFORCEMENT.md`

Intelligence System Rule (carried forward unchanged):

```text
Deterministic systems calculate facts.
AI systems explain, summarize, recommend, or communicate.
No LLM may calculate, overwrite, or mutate official cricket truth.
```

Every Phase 9G skill contract explicitly declares `no_official_truth_mutation_rule`
and calls `validate_no_official_truth_mutation` from `backend/domain/ai_boundary.py`.

### Phase 6C — Cricksy Skills Architecture Spec

Source: `docs/PHASE_6C_CRICKSY_SKILLS_ARCHITECTURE_SPEC.md`

Phase 9G uses the mandatory Cricksy Skill contract shape defined in Section 4 of Phase 6C.
Every skill in the Player Development family must define all required contract fields.
Phase 9G does NOT invent a parallel governance system — it extends Phase 6C by registering
player-development skills as a governed family within the existing architecture.

### Phase 6F — Confidence and Uncertainty System Spec

Source: `docs/PHASE_6F_CONFIDENCE_AND_UNCERTAINTY_SYSTEM_SPEC.md`

Every skill embeds:
- `confidence_fields` aligned with Phase 6F confidence taxonomy
- `limitations_fields` surfacing advisory constraints
- Fallback behaviors for low-confidence and insufficient-data states

### Phase 9A Governance Rules

Source: `docs/PHASE_9A_PLAYER_DEVELOPMENT_INTELLIGENCE_AUDIT_AND_SPEC_LOCK.md`

All contracts respect the Phase 9A locked doctrine:
- Plans must require coach approval before activation.
- Official player-truth (stats, career totals, match results) must never be mutated.
- Weaker or overlooked players must never receive negative labels.

### Phase 9B Data Model

Source: `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` Phase 9B

Contracts reference the correct deterministic data sources from the Phase 9B schema:
`PlayerDevelopmentPlan`, `PlayerDevelopmentGoal`, `PlayerWeaknessTag`,
`PlayerStrengthTag`, `PlayerDrillAssignment`, `PlayerProgressCheckpoint`.

### Phase 9C Draft-Plan Service

Source: `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` Phase 9C

`player_development_plan.v1` contract aligns with draft-only plan generation rules.
No contract can trigger automatic plan activation.

### Phase 9D Coach Workspace UI Rules

Source: `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` Phase 9D

`drill_recommendation.v1` and `player_weakness_detection.v1` output contracts match
the data shapes expected by the Coach Workspace UI.

### Phase 9E Dashboard Rules

Source: `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` Phase 9E

`team_development_overview.v1` is scoped to org_pro access, aligned with Phase 9E
dashboard aggregation boundaries.

### Phase 9F Report Safety Rules

Source: `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` Phase 9F

`player_development_report.v1` inherits Phase 9F read-only report access boundaries,
advisory disclaimer requirements, and youth-safe language enforcement.

---

## 4) Player Development Skill Contract Shape

Every skill in the Player Development family must define all fields from the Phase 6C
mandatory contract shape, plus the following Phase 9G additional fields:

**Phase 9G additional required fields (beyond Phase 6C base):**

- `allowed_outputs` — explicit list of output types and fields the skill may produce
- `forbidden_outputs` — explicit list of output types/labels the skill must never produce
- `approval_required_before_activation` — bool: plan activation must require coach approval
- `youth_safety_rules` — explicit list of youth-safe language rules (not null)
- `organization_data_boundary_rules` — role/org scoping enforcement
- `no_fake_data_rule` — explicit rule string
- `no_official_truth_mutation_rule` — explicit rule string
- `safe_language_rules` — explicit advisory language constraints
- `fallback_behaviors` — keyed dict of all required fallback states
- `evidence_ref_requirements` — mandatory evidence reference rules

The runtime-neutral contract registry lives in:
`backend/domain/player_development_skill_contract.py`

---

## 5) Required Skill Contracts

### 5.1 `player_weakness_detection.v1`

**Purpose:** Identify potential batting or bowling technique areas that match evidence
suggests could benefit from focused development. Output is advisory and coach-reviewed.

**Scope:** Produces weakness-area recommendations backed by match delivery data and form
trends. Does not rank players negatively. Does not produce "weakest player" labels.

**Allowed roles:** `coach_pro`, `coach_pro_plus`, `org_pro`

**Required inputs:** `player_profile_id`, `player_form_data`, `match_delivery_data`

**Forbidden inputs:** `unrestricted_player_dump`, `career_totals_mutation_request`,
`psychological_assessment`, `medical_data`

**Deterministic data dependencies:**
- `player_form.runs`, `player_form.wickets`, `player_form.batting_average`
- `analytics.player_analytics` (career summary slice)
- `player_improvement_tracker.monthly_stats`

**Allowed outputs:** `weakness_area_label` (advisory), `evidence_refs`, `confidence_score`,
`limitations`, `ai_metadata`, `coach_review_note`, `suggested_focus_areas`

**Forbidden outputs:** `"weakest_player"` label, `"liability"` label,
`"poor_performer"` label, talent score, ranking position, selection recommendation,
official stat overwrite, psychological diagnosis, scouting conclusion

**Output type:** `insight`

**Evidence requirements:** At least one match or form evidence ref required.
Drills/plans without evidence refs are blocked.

**Review required:** `True` — coach must review before output is surfaced.

**Approval required before activation:** `True`

**Youth safety rules:**
- No negative comparative labels (weakest, worst, liability)
- Framing must be developmental ("area to improve", "focus opportunity")
- Low-confidence outputs must use fallback language

**Fallback behaviors:**
- `insufficient_data`: return advisory placeholder, no fabricated weakness
- `low_confidence_review_required`: flag for coach review, suppress output
- `needs_more_evidence`: request additional match data before generating
- `coach_review_required`: route to review queue, do not auto-surface
- `blocked_by_youth_safety`: suppress and log if unsafe label would be generated
- `not_authorized`: block if caller role is not in `allowed_roles`
- `unsupported_claim_blocked`: block if weakness claim lacks evidence ref
- `metadata_only_pending_full_import`: return metadata stub if player data import incomplete

---

### 5.2 `player_development_plan.v1`

**Purpose:** Generate a structured, evidence-backed draft development plan for a player,
including goals, drill assignments, and expected checkpoints. Draft only.
Activation requires explicit coach approval.

**Scope:** Produces draft plans only. No automatic activation. No direct mutation of
player career totals, stats, scorecards, or match results.

**Allowed roles:** `coach_pro`, `coach_pro_plus`

**Required inputs:** `player_profile_id`, `coach_user_id`, `org_id`,
`player_form_data`, `at_least_one_evidence_ref`

**Forbidden inputs:** `career_stat_mutation_request`, `plan_activation_flag`,
`ranking_score_request`, `scouting_report_request`, `medical_data`,
`psychological_assessment`

**Deterministic data dependencies:**
- `player_form.period_start`, `player_form.period_end`
- `player_improvement_tracker.monthly_stats`
- `player_development_plan.previous_plans` (for continuity)
- `coach_player_assignment` (for scoping validity)

**Allowed outputs:** `plan_title`, `plan_summary` (advisory), `goals` (advisory),
`drill_assignments` (advisory), `progress_checkpoints` (advisory),
`confidence_score`, `evidence_refs`, `ai_metadata`, `limitations`

**Forbidden outputs:** automatic plan activation, `coach_approved=True` without
coach action, official stat overwrite, talent score, ranking, scouting conclusion,
`"should_be_selected"` claim, `"should_be_dropped"` claim, fabricated evidence_refs

**Output type:** `draft`

**Evidence requirements:** Plan summary and goals must reference at least one
deterministic evidence source. Fabricated evidence refs are blocked by `no_fake_data_rule`.

**Review required:** `True`

**Approval required before activation:** `True` — `approval_state` must be
`approved` and `coach_approved=True` before any status transition to `active`.

**Youth safety rules:**
- Developmental framing only; no comparative ranking
- Goal language must be aspirational and constructive
- Low-confidence goal suggestions suppressed pending review

**Fallback behaviors:**
- `insufficient_data`: return partial draft stub, block goal generation
- `low_confidence_review_required`: generate draft flagged for review, not auto-activated
- `needs_more_evidence`: block generation, request form or match evidence
- `coach_review_required`: route to review queue, status remains `draft`
- `blocked_by_youth_safety`: suppress unsafe goal language, flag for coach
- `not_authorized`: block if caller is not `coach_pro` / `coach_pro_plus`
- `unsupported_claim_blocked`: block goal if no evidence ref is found
- `metadata_only_pending_full_import`: return metadata stub only

---

### 5.3 `drill_recommendation.v1`

**Purpose:** Suggest targeted drills that address identified development areas,
backed by evidence from match delivery data or form trends.
Output is advisory and coach-reviewed before assignment.

**Scope:** Recommends drill types, categories, and frequencies. Does not auto-assign
drills without coach confirmation. Does not fabricate drill descriptions.

**Allowed roles:** `coach_pro`, `coach_pro_plus`

**Required inputs:** `player_profile_id`, `plan_id`, `weakness_area_label`,
`at_least_one_evidence_ref`

**Forbidden inputs:** `career_stat_mutation_request`, `auto_assign_flag`,
`scouting_report_request`, `ranking_request`, `medical_data`

**Deterministic data dependencies:**
- `player_weakness_detection.v1` output (scoped weakness areas)
- `player_form.batting_average`, `player_form.strike_rate`, `player_form.economy`
- `player_development_plan.goals`

**Allowed outputs:** `drill_category`, `drill_name`, `drill_description` (advisory),
`frequency_suggestion`, `evidence_refs`, `confidence_score`, `limitations`, `ai_metadata`

**Forbidden outputs:** automatic drill assignment, direct stat mutation,
`"this player will improve"` certainty claim, fabricated drill evidence,
talent score, ranking, scouting conclusion

**Output type:** `recommendation`

**Evidence requirements:** Each recommended drill must be linked to at least one
weakness evidence ref from `player_weakness_detection.v1` output or a match data source.

**Review required:** `True`

**Approval required before activation:** `True` — coach must confirm assignment
before `status` changes from `draft`.

**Youth safety rules:**
- Drill descriptions must use constructive language
- No comparative labels ("this player is worse than…")
- Low-confidence drill recommendations suppressed pending review

**Fallback behaviors:**
- `insufficient_data`: return empty drill list with advisory message
- `low_confidence_review_required`: return draft recommendation flagged for coach
- `needs_more_evidence`: block recommendation, request weakness evidence
- `coach_review_required`: route to review queue
- `blocked_by_youth_safety`: suppress unsafe drill description language
- `not_authorized`: block if caller is not in `allowed_roles`
- `unsupported_claim_blocked`: block drill if no weakness evidence ref
- `metadata_only_pending_full_import`: return metadata stub only

---

### 5.4 `progress_checkpoint_summary.v1`

**Purpose:** Summarize player progress against a development plan's goals and checkpoints,
using evidence from match stats and form data. Summaries are advisory and coach-reviewed.

**Scope:** Produces advisory summaries referencing checkpoint evidence.
Does not assert unsupported "has improved" claims. Does not mutate player stats.

**Allowed roles:** `coach_pro`, `coach_pro_plus`, `org_pro`

**Required inputs:** `player_profile_id`, `plan_id`, `checkpoint_ids`,
`at_least_one_evidence_ref`

**Forbidden inputs:** `career_stat_mutation_request`, `official_improvement_certification`,
`talent_score_request`, `ranking_request`, `medical_data`

**Deterministic data dependencies:**
- `player_progress_checkpoint.status`, `player_progress_checkpoint.evidence_refs`
- `player_form.period_start`, `player_form.period_end`, `player_form.form_score`
- `player_improvement_tracker.improvement_score`

**Allowed outputs:** `checkpoint_status_summary` (advisory), `progress_narrative` (advisory),
`evidence_refs`, `confidence_score`, `limitations`, `ai_metadata`,
`review_notes`

**Forbidden outputs:** `"has_improved"` certainty assertion without checkpoint evidence,
official stat overwrite, player ranking, talent score, scouting conclusion,
`"ready_to_be_selected"` claim, fabricated progress evidence

**Output type:** `summary`

**Evidence requirements:** Every progress narrative claim must reference at least one
checkpoint with a non-null `evidence_refs` list.

**Review required:** `True`

**Approval required before activation:** `True` — checkpoint status summaries must
not be surfaced without coach review.

**Youth safety rules:**
- Progress language must be constructive ("showing improvement in…", "continuing to develop…")
- No negative comparative framing
- Unverified progress claims suppressed pending checkpoint evidence

**Fallback behaviors:**
- `insufficient_data`: return advisory "insufficient checkpoint data" message
- `low_confidence_review_required`: flag summary for coach review, suppress auto-display
- `needs_more_evidence`: request more checkpoint data before summarizing
- `coach_review_required`: route to review queue
- `blocked_by_youth_safety`: suppress unsafe progress claim language
- `not_authorized`: block if caller is not in `allowed_roles`
- `unsupported_claim_blocked`: block progress claim if no checkpoint evidence
- `metadata_only_pending_full_import`: return metadata stub only

---

### 5.5 `team_development_overview.v1`

**Purpose:** Provide an org-scoped advisory overview of team-wide development activity,
highlighting aggregate plan coverage and active drill areas. Advisory only.
Does not rank players within the team.

**Scope:** Aggregates plan counts, goal categories, and drill area distribution.
Does not surface individual player names in comparative ranking lists.
Does not assert team selection recommendations.

**Allowed roles:** `org_pro`

**Required inputs:** `org_id`, `team_id_or_season_scope`

**Forbidden inputs:** `individual_player_ranking_request`, `selection_recommendation_request`,
`talent_score_request`, `scouting_report_request`, `medical_data`

**Deterministic data dependencies:**
- `player_development_plan.status` (aggregate counts)
- `player_development_goal.category` (distribution)
- `player_drill_assignment.drill_category` (distribution)
- `player_progress_checkpoint.status` (aggregate completion)

**Allowed outputs:** `plan_coverage_summary`, `goal_category_distribution`,
`drill_area_distribution`, `checkpoint_completion_rate`, `confidence_score`,
`limitations`, `ai_metadata`, `advisory_note`

**Forbidden outputs:** individual player ranking, "weakest player on team" label,
talent score, selection recommendation, scouting conclusion,
official team selection list, `"player X should be dropped"` claim,
fabricated aggregate evidence

**Output type:** `summary`

**Evidence requirements:** All aggregate claims must be derivable from stored
`PlayerDevelopmentPlan` and related records. No fabricated aggregate data.

**Review required:** `True`

**Approval required before activation:** `True`

**Youth safety rules:**
- No individual comparative ranking labels in team overview
- Team-level framing must be constructive ("strong coverage in…", "opportunity to expand…")
- Low-confidence aggregate claims suppressed pending sufficient plan data

**Fallback behaviors:**
- `insufficient_data`: return "no active plans found" advisory, no fabricated overview
- `low_confidence_review_required`: flag overview for org_pro review
- `needs_more_evidence`: request more plan data before generating
- `coach_review_required`: route individual concern areas to coach review
- `blocked_by_youth_safety`: suppress any unsafe comparative label
- `not_authorized`: block if caller is not `org_pro`
- `unsupported_claim_blocked`: block aggregate claim if no plan records support it
- `metadata_only_pending_full_import`: return metadata stub only

---

### 5.6 `player_development_report.v1`

**Purpose:** Generate an advisory, evidence-backed development report for a player
within a plan period. Readable by coach and org; not surfaced publicly or to the player
unless a future phase explicitly governs that access.

**Scope:** Read-only, advisory narrative report. Does not mutate official player stats.
Does not certify improvement. Does not expose player data cross-org.

**Allowed roles:** `coach_pro`, `coach_pro_plus`, `org_pro`

**Required inputs:** `player_profile_id`, `plan_id`, `at_least_one_evidence_ref`

**Forbidden inputs:** `public_surface_flag`, `player_facing_access_flag`,
`talent_score_request`, `scouting_report_request`, `official_improvement_certification`,
`career_stat_mutation_request`

**Deterministic data dependencies:**
- `player_development_plan.title`, `player_development_plan.summary`
- `player_development_goal.label`, `player_development_goal.status`
- `player_progress_checkpoint.evidence_refs`
- `player_form.batting_average`, `player_form.form_score`
- `player_improvement_tracker.improvement_score`

**Allowed outputs:** `report_title`, `report_narrative` (advisory),
`goals_summary`, `checkpoints_summary`, `evidence_refs`,
`confidence_score`, `limitations`, `ai_metadata`,
`advisory_disclaimer`, `review_status`

**Forbidden outputs:** official player ranking, talent score, scouting conclusion,
public report exposure, `"player is ready for selection"` claim,
`"has_improved"` certainty assertion without checkpoint evidence,
cross-org player data, fabricated report evidence,
automatic report activation or publish

**Output type:** `report`

**Evidence requirements:** Every narrative section must reference at least one
deterministic evidence source. Reports without evidence refs are blocked.

**Review required:** `True` — report must carry coach-review status before surfacing.

**Approval required before activation:** `True`

**Youth safety rules:**
- Report language must be constructive and developmental
- No comparative rankings or negative labels
- All uncertainty must be expressed with safe fallback language
- Unsupported improvement claims blocked

**Fallback behaviors:**
- `insufficient_data`: return "insufficient plan data for report generation" advisory
- `low_confidence_review_required`: generate draft report flagged for review
- `needs_more_evidence`: block report generation, request checkpoint/form data
- `coach_review_required`: route to review queue, do not publish
- `blocked_by_youth_safety`: suppress unsafe report language, flag for coach
- `not_authorized`: block if caller is not in `allowed_roles`
- `unsupported_claim_blocked`: block narrative claim if no evidence ref
- `metadata_only_pending_full_import`: return metadata stub only

---

## 6) Mandatory Safety Rules

Every player-development skill locks ALL of the following rules:

1. **AI output is advisory only.** No skill may present its output as official truth.
2. **No official stat mutation.** No skill may overwrite official match results,
   scorecards, DLS values, innings state, player career totals, or deterministic model
   outputs. The `validate_no_official_truth_mutation` guard from `backend/domain/ai_boundary.py`
   must be called at every skill output boundary.
3. **No automatic plan activation.** No skill may activate a development plan without
   `coach_approved=True` and `approval_state="approved"`.
4. **No unauthorized public output.** No skill may generate player-facing or public-facing
   outputs unless explicitly governed in a later phase.
5. **No fake data.** No skill may fabricate player evidence, drills, goals, checkpoints,
   progress data, or reports. If deterministic data is unavailable, return `insufficient_data`.
6. **No negative youth labels.** No skill may apply labels such as "weakest", "liability",
   "poor performer", "worst", or any negatively comparative label to a youth player.
7. **No talent-certainty claims.** No skill may produce talent scores, ranking positions,
   selection certainty, scouting conclusions, medical diagnoses, or psychological assessments.
8. **Safe fallbacks for low confidence.** When confidence is below threshold or data is
   insufficient, use the defined fallback behaviors. Never fabricate to fill gaps.
9. **Youth-safe language is mandatory.** All output language must be constructive,
   developmental, and non-comparative.
10. **Evidence references are mandatory.** Recommendations and reports must include at
    least one deterministic evidence reference.
11. **Org/player privacy boundaries are mandatory.** Skills must enforce `org_id` and
    `coach_user_id` scoping. Cross-org data access is forbidden.

---

## 7) Forbidden Outputs

Every contract in the Player Development Skill family explicitly forbids the following
output types and labels:

| Forbidden Output | Applies To |
|---|---|
| `"weakest_player"` label | All skills |
| `"poor_performer"` label | All skills |
| `"liability"` label | All skills |
| `"worst"` comparative label | All skills |
| `"should_be_selected"` claim | All skills |
| `"should_be_dropped"` claim | All skills |
| Deterministic talent score | All skills |
| Medical or psychological diagnosis | All skills |
| Unsupported `"has_improved"` certainty claim | All skills |
| Public scouting conclusion | All skills |
| Official player ranking | All skills |
| Automatic plan activation | `player_development_plan.v1`, `drill_recommendation.v1` |
| Mutation of official cricket truth | All skills |
| Cross-org player data | All skills |
| Fabricated evidence references | All skills |
| Individual comparative ranking in team view | `team_development_overview.v1` |

---

## 8) Fallback Behaviors

Every skill must define all of the following fallback states:

| Fallback State | Behavior |
|---|---|
| `insufficient_data` | Return advisory placeholder. Block generation. No fabricated content. |
| `low_confidence_review_required` | Generate flagged draft. Route to review queue. Suppress auto-display. |
| `needs_more_evidence` | Block generation. Request additional match/form/checkpoint data. |
| `coach_review_required` | Route to review queue. Status remains draft. Do not auto-surface. |
| `blocked_by_youth_safety` | Suppress output. Log unsafe label attempt. Flag for coach review. |
| `not_authorized` | Block output. Return 403. No partial data leak. |
| `unsupported_claim_blocked` | Block claim. Require evidence ref before re-generation. |
| `metadata_only_pending_full_import` | Return metadata stub. Block full output until import complete. |

---

## 9) Validation Rules

If a backend contract module is added (as in Phase 9G), the following validation rules
must be enforced by contract tests:

1. All required skill contracts are present in the registry.
2. Every skill has all required contract fields.
3. Every skill has a versioned `skill_id` (format: `name.v{N}`).
4. Every skill declares `no_official_truth_mutation_rule`.
5. Every skill declares `no_fake_data_rule`.
6. Every skill declares `youth_safety_rules` (non-empty list).
7. Every skill declares `evidence_ref_requirements`.
8. Every skill declares `fallback_behaviors` covering all required fallback states.
9. Every skill's `forbidden_outputs` include ranking/selection/unsafe labels.
10. The contract registry is deterministic, importable, and produces no side effects.
11. Every skill declares `review_required: True`.
12. Every skill declares `approval_required_before_activation: True`.
13. Every skill declares `tests_required` (non-empty list).

---

## 10) Future Implementation Boundaries

The following behaviors are explicitly reserved for future phases and must NOT be
implemented in Phase 9G or by any code referencing Phase 9G contracts:

- Runtime AI skill execution (future Phase 9 sub-phases)
- Live plan generation via LLM providers
- Coach approval workflow automation
- Report PDF export from skill outputs
- Player-facing development progress view
- Public development report surface
- Autonomous coaching orchestration
- Selection or scouting engine
- Talent ranking or scoring system

---

## 11) Testing Expectations

Phase 9G backend tests must validate contract shape only.
Tests live in: `backend/tests/test_player_development_skill_contract.py`

Required test coverage:

1. All required skill contracts are importable from the registry.
2. Every skill has all required fields.
3. Every skill has a versioned `skill_id`.
4. Every skill declares `no_official_truth_mutation_rule`.
5. Every skill declares `no_fake_data_rule`.
6. Every skill declares `youth_safety_rules`.
7. Every skill declares `evidence_ref_requirements`.
8. Every skill declares `fallback_behaviors` covering required states.
9. `forbidden_outputs` include at least: ranking, selection, unsafe labels, talent score.
10. Registry is deterministic and importable (no side effects, no runtime AI calls).
11. `review_required` is `True` for every skill.
12. `approval_required_before_activation` is `True` for every skill.

---

## 12) Rollback / Disable Strategy

Phase 9G introduces only documentation and a runtime-neutral contract module.
No runtime execution, live endpoints, or plan activation behavior is added.

Rollback strategy:
- Remove or revert `backend/domain/player_development_skill_contract.py`
- Remove or revert `backend/tests/test_player_development_skill_contract.py`
- Revert checklist entries
- No migrations to roll back
- No runtime behavior to disable

Disable strategy:
- Feature-flag at the importing skill implementation level (not at the contract level)
- Contract registry itself is always safe to import: it is pure data with no side effects

---

## 13) Acceptance Criteria

- [x] Player Development Skill Contract spec exists (`docs/PHASE_9G_PLAYER_DEVELOPMENT_SKILL_CONTRACT.md`)
- [x] All 6 required skill contracts are defined and versioned
- [x] Phase 6C skill-governance inheritance is explicit (Section 3)
- [x] Safety rules are explicit (Section 6)
- [x] Forbidden outputs are explicit (Section 7)
- [x] Fallback behaviors are explicit (Section 8)
- [x] Evidence/ref requirements are explicit (per skill and Section 9)
- [x] Review and coach approval requirements are explicit (per skill)
- [x] No official cricket truth mutation is allowed
- [x] No fake data is allowed
- [x] No unsafe youth labels or rankings are allowed
- [x] Backend contract registry added (`backend/domain/player_development_skill_contract.py`)
- [x] Backend contract tests pass (`backend/tests/test_player_development_skill_contract.py`)
- [x] No frontend changes
- [x] No migrations changed
- [x] No AI provider integration added
- [x] No runtime generation behavior added
- [x] No official cricket truth mutation possible
- [x] Checklist updated after validation

---

## 14) Validation Notes

- Phase 9G contract module is runtime-neutral: a plain Python dict registry, no I/O,
  no DB calls, no AI calls, no network calls.
- Contract registry is deterministically importable and produces no side effects.
- All forbidden-output and safety rules are enforced by contract shape tests.
- The Phase 6B `validate_no_official_truth_mutation` guard is referenced in every
  contract's `validation_rules` field.
- Youth-safety rules are non-null on every contract, satisfying the Phase 9A mandate.
- Evidence reference requirements are non-null on every contract.
- Review and approval requirements are `True` on every contract.
- No new routes, no new migrations, no new frontend components.

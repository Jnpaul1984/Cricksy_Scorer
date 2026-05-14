# PHASE 6H — VALIDATION AGENTS + REVIEW QUEUE SPEC

## Status

Spec-lock complete. Architecture only.

No runtime validation agents, review queue backend/UI, approval workflow code,
notifications, migrations, dependencies, infrastructure, runtime skills, runtime routers,
Supervisor logic, LLM workflows, or production behavior changes are implemented in this phase.

---

## 1) Purpose

Define what happens **after** a future intelligence output is generated:

- how it is validated,
- who can review it,
- when it is blocked,
- when it is approved,
- when it can become internal, coach-facing, team-facing, player-facing, organization-facing,
  or public/media-facing.

Failure mode to prevent:

```text
AI/skill output is generated → user treats it as approved → unsafe, incorrect,
low-confidence, or unauthorized content becomes official-facing.
```

Outcome enabled:

```text
Generated output → validation checks → review queue → approval/rejection/escalation →
approved intelligence output.
```

---

## 2) Required Future Architecture (Spec Only)

```text
Generated Insight / Report / Recommendation
        ↓
Data Validation
        ↓
Cricket Correctness Validation
        ↓
Confidence + Uncertainty Validation
        ↓
Safety + Language Validation
        ↓
Role + Org Boundary Validation
        ↓
Review Queue
        ↓
Coach / Admin / Analyst Approval
        ↓
Approved Output or Rejected / Escalated Output
```

This phase defines governance contracts only. Runtime validation/review implementation is deferred.

---

## 3) Pre-Phase Audit Summary

### A. Existing Phase 6A–6G governance/contracts baseline

- `docs/PHASE_6A_CRICKSY_INTELLIGENCE_OS_AUDIT_AND_SPEC_LOCK.md`
- `docs/PHASE_6B_DETERMINISTIC_AI_BOUNDARY_ENFORCEMENT.md`
- `docs/PHASE_6C_CRICKSY_SKILLS_ARCHITECTURE_SPEC.md`
- `docs/PHASE_6D_INTENT_ROUTER_AND_SKILL_ROUTER_SPEC.md`
- `docs/PHASE_6E_PROGRESSIVE_DISCLOSURE_AND_CONTEXT_LOADING_RULES.md`
- `docs/PHASE_6F_CONFIDENCE_AND_UNCERTAINTY_SYSTEM_SPEC.md`
- `docs/PHASE_6G_EVENT_TRIGGERED_COMPUTE_AND_COST_CONTROL_SPEC.md`

These phases already lock deterministic truth boundaries, skill/intent contracts,
context package rules, confidence package requirements, and compute gating.

### B. Existing AI boundary metadata + confidence/context/compute contract foundations

- `backend/domain/ai_boundary.py` + Phase 6B docs lock `AiOutputMetadata`,
  `OFFICIAL_TRUTH_FIELDS`, and `validate_no_official_truth_mutation`.
- Phase 6E context package contract includes `context_package_id`, sufficiency and provenance fields.
- Phase 6F confidence package contract includes `confidence_package_id`, confidence bands,
  uncertainty reasons, `review_required`, and fallback codes.
- Phase 6G compute contract includes `compute_request_id`, budget class, review flags,
  and `no_fake_data_confirmation`.

### C. Existing output surfaces that future review queue must govern

- Analyst Workspace + case-study/report surfaces:
  `frontend/src/views/AnalystWorkspaceView.vue`,
  `backend/routes/analytics_case_study.py`,
  `backend/services/analytics_case_study.py`.
- Coach Pro Plus/video analysis/report/PDF surfaces:
  `backend/routes/coach_pro_plus.py`, `backend/services/coach_ai_pipeline.py`,
  `backend/services/coach_report_service.py`, `backend/services/pdf_export_service.py`.
- Mental/performance oriented outputs are present in coach pipeline/report surfaces and
  require explicit safety/review governance before delivery.

### D. Existing auth/RBAC/org and youth-safety baseline

- `backend/security.py` (`get_current_user`, `require_roles`) and
  `backend/services/analyst_access.py` enforce scoped access.
- Phase 6D/6E/6F already lock org boundary checks, safe language expectations,
  youth-safety review requirements, and non-authoritative behavior.

### E. Existing fake-data/no-fake-data and provenance protections

- `scripts/check-fake-data.js` + CI guard enforce no fabricated data patterns.
- Historical registry/provenance/training eligibility remains deterministic in
  `backend/routes/historical_import.py` and `backend/routes/analytics_case_study.py`.
- Metadata-only import states remain blocked for training/reliance until full import.

### F. Existing audit/logging patterns relevant to future review workflows

- `backend/services/agent_budget.py` records agent runs and token usage.
- Historical import backfill writes repair audit entries to
  `game.phases["historical_import"]["_repair_log"]`.
- Phase 6H extends this into a standardized validation + reviewer decision audit trail.

### G. Existing CI/test gates relevant to future review queue validation

- `.github/workflows/ci.yml` runs lint/type/security/backend/frontend/fake-data checks.
- Existing deterministic-vs-AI boundary tests (`backend/tests/test_phase_6b_ai_boundary.py`)
  protect official truth boundaries that future review queue logic must not weaken.

### H. Current risky pattern to eliminate in future runtime implementation

Phase 6G audit identified route-triggered narrative/commentary surfaces that can generate
user-facing output on request without a standardized validation/review gate.
Phase 6H closes this governance gap by defining mandatory validation outcomes,
review states, and publication approval levels.

---

## 4) Strict Scope Lock for Phase 6H

### Allowed

- This architecture/spec document.
- Master checklist update for Phase 6H completion notes.
- Validation agent/check categories and responsibilities.
- Review queue states, contract, reviewer roles, approval levels, outcomes, fallbacks,
  and audit rules.
- Example review queue items and future validation test requirements.

### Conditionally allowed

- Docs-only review queue contract examples.

### Not allowed

- Runtime validation agent implementation.
- Runtime review queue backend/UI/notification workflow implementation.
- Runtime approval workflow code.
- Runtime skills/routers/agents/Supervisor.
- LLM provider integration/external AI calls.
- Migrations/schema changes/dependencies/infrastructure changes.
- Any production behavior changes to scoring, DLS, gameplay/live bus,
  historical import truth, registry/training eligibility, AI boundary guards,
  auth/RBAC/org boundaries, fake-data guard, or CI/CD gates.

---

## 5) Required Validation Agent Types + Checks

### 5.1 Data Validation Agent

Must verify:

- source data exists,
- no fake/demo data was used,
- provenance is available,
- metadata-only records are not treated as full imports,
- context package sufficiency is valid,
- requester has permission to access source data.

### 5.2 Cricket Correctness Validator

Must verify:

- output does not contradict official score/result/stat facts,
- cricket terminology is correct,
- tactical claim is supported by available data,
- deterministic metrics are cited/referenced,
- no LLM-generated calculation overrides official facts.

### 5.3 Confidence + Uncertainty Validator

Must verify:

- confidence package exists where required,
- low-confidence output is labelled,
- small-sample limitations are visible,
- uncertainty reasons are present,
- output does not overstate certainty.

### 5.4 Safety + Language Validator

Must verify:

- youth/player feedback uses safe developmental language,
- mental/performance criticism is not harmful or demeaning,
- recommendations are constructive,
- public/podcast content is professional and reviewable.

### 5.5 Role + Org Boundary Validator

Must verify:

- reviewer/user has correct role,
- team/org/player visibility is respected,
- cross-org leakage is blocked,
- coach/analyst/admin permission boundaries are enforced.

---

## 6) Required Review Queue States

Future review queue items must use governed states:

- `draft_generated`
- `validation_pending`
- `validation_failed`
- `review_required`
- `in_review`
- `changes_requested`
- `approved_internal`
- `approved_coach_facing`
- `approved_public`
- `rejected`
- `escalated`
- `archived`

### 6A) State progression guidance (future runtime)

```text
draft_generated → validation_pending →
  (validation_failed | review_required)
review_required → in_review →
  (changes_requested | approved_internal | approved_coach_facing | approved_public |
   rejected | escalated)
changes_requested → validation_pending (after revision)
any terminal approved/rejected/escalated state → archived (lifecycle close)
```

---

## 7) Required Review Queue Item Contract (Mandatory Fields)

Every future review queue item must define:

- `review_item_id`
- `source_output_id`
- `output_type`
- `intent_id`
- `skill_id`
- `compute_request_id`
- `context_package_id`
- `confidence_package_id`
- `created_by_system_component`
- `requested_by_user_id`
- `org_scope`
- `team_scope`
- `player_scope`
- `review_state`
- `validation_results`
- `confidence_band`
- `risk_level`
- `review_required_reason`
- `assigned_reviewer_role`
- `assigned_reviewer_user_id`
- `approval_level_required`
- `allowed_publication_targets`
- `audit_log_entries`
- `no_fake_data_confirmation`
- `provenance_references`

---

## 8) Required Review Requirements by Output Type

| Output type | Minimum validation/review requirement |
|---|---|
| youth player feedback | Safety + Language + Role/Org checks; requires coach + safety reviewer before player-facing delivery |
| mental/performance criticism | Safety + Language checks mandatory; welfare-style review required before coach/player-facing delivery |
| coach reports | Data + Cricket Correctness + Confidence checks; coach/admin review before coach-facing publication |
| scouting reports | Data + Cricket Correctness + Confidence + Role/Org checks; analyst/admin review required |
| public/podcast content | Full validator stack + media reviewer + analyst/admin review; stricter publication gate |
| training recommendations | Cricket Correctness + Confidence + Safety review before team/player-facing use |
| workload/injury-sensitive recommendations | Confidence + Safety + escalation path required; must support conservative fallback |
| low-confidence outputs | Must be labelled + review-required + restricted publication level by default |
| AI-generated tactical recommendations | Cricket Correctness + Confidence + role-bound review before any coach/team-facing release |
| model-derived recommendations | Model uncertainty and calibration checks + analyst review before publication |
| video-analysis summaries | Video certainty + confidence checks + coach/analyst review before external delivery |
| opposition reports | Org boundary + correctness checks + analyst/admin review required |

---

## 9) Required Reviewer Roles + Approval Authority

Future reviewer roles:

- `coach`
- `analyst`
- `admin`
- `organization_admin`
- `safety_reviewer`
- `media_reviewer`
- `system_validator`

### 9A) Approval authority matrix (future policy baseline)

| Reviewer role | May approve |
|---|---|
| `system_validator` | Validation pass/fail gating only; cannot grant public publication |
| `coach` | Coach/player development outputs at `coach_facing` or lower (subject to safety gates) |
| `analyst` | Analyst reports, tactical summaries, scouting/opposition outputs at `internal_only`/`coach_facing` |
| `admin` | Internal/team/org-facing approvals; escalation resolution |
| `organization_admin` | Organization-facing approvals and cross-team governance decisions |
| `safety_reviewer` | Required co-approval for youth feedback and sensitive mental/performance criticism |
| `media_reviewer` | Required co-approval for `public_media` outputs (podcast/public narrative content) |

No single non-media role may unilaterally approve `public_media` publication.

---

## 10) Required Approval Levels

Future approval levels:

- `internal_only`
- `coach_facing`
- `team_facing`
- `player_facing`
- `organization_facing`
- `public_media`

`public_media` is stricter than internal/coach-facing levels and requires full validation
plus explicit multi-role review (at minimum analyst/media/admin policy checks).

---

## 11) Required Validation Outcomes

Validation outcomes to standardize across validators:

- `passed`
- `failed`
- `warning`
- `needs_review`
- `blocked`
- `insufficient_data`
- `not_authorized`
- `low_confidence`
- `unsafe_language`
- `unsupported_claim`

---

## 12) Required Fallback Behavior

Safe fallback outcomes:

- `hold_for_review`
- `request_more_context`
- `request_human_revision`
- `block_publication`
- `return_insufficient_data`
- `downgrade_to_internal_only`
- `strip_unsupported_claims`
- `escalate_to_admin`

Fallbacks must preserve deterministic truth, no-fake-data rules, and org/youth safety boundaries.

---

## 13) Required Audit Trail Rules

Future review workflows must capture:

- who requested the output,
- what data/context was used,
- what skill/intent generated it,
- what confidence package was attached,
- what validators ran,
- validation outcomes,
- reviewer decisions,
- timestamps,
- publication target,
- approval/rejection/escalation reason.

Audit entries must be immutable enough for governance review and post-incident traceability.

---

## 14) Required Example Review Queue Items

### 14.1 Youth player feedback requiring coach/safety review

- output type: `youth_player_feedback`
- validation checks: data=passed, cricket=passed, confidence=needs_review,
  safety=needs_review, role/org=passed
- confidence band: `medium_confidence`
- review state: `review_required`
- assigned reviewer role: `coach` + `safety_reviewer`
- approval level: `player_facing`
- fallback/escalation behavior: `hold_for_review`; if unsafe wording detected,
  `request_human_revision`

### 14.2 Podcast breakdown requiring analyst/media review

- output type: `podcast_breakdown`
- validation checks: data=passed, cricket=passed, confidence=passed,
  safety=warning, role/org=passed
- confidence band: `high_confidence`
- review state: `in_review`
- assigned reviewer role: `analyst` + `media_reviewer`
- approval level: `public_media`
- fallback/escalation behavior: `block_publication` until media review passes

### 14.3 Low-confidence spin weakness recommendation requiring review

- output type: `tactical_recommendation_spin_weakness`
- validation checks: data=passed, cricket=passed, confidence=`low_confidence`,
  safety=passed, role/org=passed
- confidence band: `low_confidence`
- review state: `review_required`
- assigned reviewer role: `analyst`
- approval level: `coach_facing`
- fallback/escalation behavior: `downgrade_to_internal_only` + `request_more_context`

### 14.4 Coach report approved for coach-facing use

- output type: `coach_report`
- validation checks: data=passed, cricket=passed, confidence=passed,
  safety=passed, role/org=passed
- confidence band: `high_confidence`
- review state: `approved_coach_facing`
- assigned reviewer role: `coach`
- approval level: `coach_facing`
- fallback/escalation behavior: none required post-approval; close with `archived` on lifecycle completion

### 14.5 Unsupported claim blocked by cricket correctness validator

- output type: `opposition_report_claim`
- validation checks: data=passed, cricket=`unsupported_claim`, confidence=warning,
  safety=passed, role/org=passed
- confidence band: `medium_confidence`
- review state: `validation_failed`
- assigned reviewer role: `system_validator`
- approval level: `internal_only`
- fallback/escalation behavior: `strip_unsupported_claims` or `request_human_revision`;
  escalate to admin on repeated failures

---

## 15) Future Validation Tests for Review Queue Implementation

Future runtime implementation must include tests for:

1. validator ordering and deterministic blocking behavior,
2. required review queue item fields and schema validation,
3. state transition correctness (including forbidden transitions),
4. approval-level permission enforcement by reviewer role,
5. `public_media` stricter multi-review policy enforcement,
6. low-confidence and unsafe-language fallback behavior,
7. no-fake-data and provenance-required gating,
8. org/team/player boundary leakage prevention,
9. audit trail completeness for pass/fail/escalation decisions,
10. protection of Phase 6B official-truth boundary during validation/review workflows.

---

## 16) Phase 6A–6H Completion Summary

Together, Phase 6A–6H now define:

- Intelligence OS architecture,
- deterministic vs AI boundary,
- skills architecture,
- intent/skill routing,
- progressive disclosure/context loading,
- confidence/uncertainty system,
- event-triggered compute/cost control,
- validation/review queue governance.

This completes Phase 6 governance/spec architecture while preserving deterministic
cricket truth and protected runtime systems.

---

## 17) Recommendation for Next Phase

After Phase 6H, the project should **pause before runtime implementation** and open
an implementation-selection issue.

Preferred next step:

- `Phase 7A — Intelligence Runtime Readiness Audit + First Implementation Slice Selection`

Alternative (only with explicit approval to skip readiness audit first):

- `Phase 7A — First Governed Skill Runtime MVP: Match Momentum Skill`

Default recommendation: run readiness audit first.

---

## 18) Protected Systems (Unchanged by This Phase)

This phase does not change or weaken:

- official score/runs/balls/overs/wickets/innings/match result/scorecards/player stats,
- DLS calculations,
- gameplay/live-bus behavior,
- historical import validation and metadata-only gates,
- Phase 5M registry endpoint behavior,
- Phase 6B AI boundary guard behavior,
- Phase 6C skill contract behavior,
- Phase 6D intent/skill routing boundaries,
- Phase 6E context-loading boundaries,
- Phase 6F confidence/uncertainty boundaries,
- Phase 6G event-triggered compute boundaries,
- Coach Pro Plus/video analysis runtime,
- mental analysis runtime,
- auth/RBAC/org boundaries,
- fake-data guard,
- CI/CD gates.

---

## 19) Validation Notes

- Markdown formatting reviewed.
- Phase ordering remains clear.
- Spec-only scope preserved.
- No runtime validation agents, review queue backend/UI, approval workflow code,
  notifications, migrations, dependencies, infrastructure, routers, skills, agents,
  Supervisor logic, or external AI provider workflows were added.
- No production behavior changed.

---

## 20) Confirmation Statements

- This phase is validation/review architecture spec only.
- No runtime validation agents or runtime review queue were implemented.
- No runtime agents, skills, routers, or Supervisor were implemented.
- No runtime behavior changed.

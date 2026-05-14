# PHASE 6F — CONFIDENCE + UNCERTAINTY SYSTEM SPEC

## Status

Spec-lock complete. Architecture only.

No runtime confidence engine, validation agents, runtime skills, runtime routers,
Supervisor logic, LLM workflows, migrations, dependencies, or production behavior
changes are implemented in this phase.

---

## 1) Purpose

Define how future Cricksy intelligence outputs communicate:

- reliability
- uncertainty
- sample-size limitations
- data quality issues
- tactical confidence
- video certainty
- model confidence
- recommendation confidence
- review requirements

Failure mode to prevent:

```text
Skill produces a polished answer → user assumes it is certain → weak data or small
sample size is hidden.
```

Outcome enabled:

```text
Insight + confidence + limitations + uncertainty reason + review status.
```

---

## 2) Required Future Architecture (Spec Only)

```text
Context Package
        ↓
Data Quality Check
        ↓
Sample Size Check
        ↓
Skill-Specific Confidence Inputs
        ↓
Uncertainty Classification
        ↓
Confidence Score Package
        ↓
Output Framing Rules
        ↓
Review / Fallback Decision
```

This phase defines governance contracts only. Runtime confidence engine
implementation is deferred.

---

## 3) Pre-Phase Audit Summary

### A. Existing Phase 6A–6E governance baseline

- `docs/PHASE_6A_CRICKSY_INTELLIGENCE_OS_AUDIT_AND_SPEC_LOCK.md` — Intelligence OS audit,
  governance rules, protected systems, and future-phase separation.
- `docs/PHASE_6B_DETERMINISTIC_AI_BOUNDARY_ENFORCEMENT.md` — Enforceable code boundaries
  preventing AI from mutating cricket truth; `backend/domain/ai_boundary.py` with
  `AiOutputType`, `OFFICIAL_TRUTH_FIELDS`, `AiOutputMetadata`, and
  `validate_no_official_truth_mutation`.
- `docs/PHASE_6C_CRICKSY_SKILLS_ARCHITECTURE_SPEC.md` — Mandatory skill contract including
  `confidence_fields` and `limitations_fields`; three sample skills with
  `overall_confidence` field illustrated.
- `docs/PHASE_6D_INTENT_ROUTER_AND_SKILL_ROUTER_SPEC.md` — Intent taxonomy, routing contract
  with `confidence_requirements` and `review_requirements`; safe fallback statuses such as
  `insufficient_data`, `needs_clarification`, and `not_authorized`.
- `docs/PHASE_6E_PROGRESSIVE_DISCLOSURE_AND_CONTEXT_LOADING_RULES.md` — Context minimization
  rules; context package contract includes `confidence_inputs` and `sufficiency_status`;
  fallback statuses including `metadata_only_pending_full_import` and
  `blocked_by_youth_safety`.

### B. Existing `AiOutputMetadata` and non-authoritative AI output behavior

- `backend/domain/ai_boundary.py`:
  - `AiOutputMetadata` Pydantic model carries `output_type`, `is_official_truth = False`,
    `requires_review`, `non_authoritative_notice`.
  - `OFFICIAL_TRUTH_FIELDS` frozenset protects official cricket truth from AI mutation.
  - `validate_no_official_truth_mutation` raises `ValueError` if any AI payload attempts
    to write official truth fields.
- AI response schemas already embed `ai_metadata`:
  - `AiCommentaryResponse` (`ai_commentary.py`)
  - `MatchAiCommentaryResponse`, `MatchAiSummaryResponse` (`match_ai.py`)
  - `PlayerAiInsights` (`ai_player_insights.py`)
- Current AI services are mostly rule-based or mocked; no live confidence scores are
  exposed yet. Phase 6F defines the future contract before that changes.

### C. Existing skill contract confidence fields from Phase 6C

- Phase 6C locks `confidence_fields` and `limitations_fields` as mandatory skill contract
  fields for every future skill.
- Example from `match_momentum.v1` sample output shape:
  ```yaml
  confidence:
    overall_confidence: 0.78
  ```
- Phase 6C documents `confidence_labeling_test` as a required test for every skill.
- Phase 6C mandates `review_required` as a mandatory skill contract field, with required
  review for youth-facing coaching language and high-impact outputs.

### D. Existing context package and sufficiency rules from Phase 6E

- Phase 6E context package contract includes `confidence_inputs`, `sufficiency_status`,
  and `insufficient_data_reasons`.
- Sufficiency rules mandate that missing required context returns `insufficient_data`
  rather than fabricated data.
- Phase 6E fallback statuses include `insufficient_data`, `needs_narrower_scope`,
  `not_authorized`, `context_budget_exceeded`, `metadata_only_pending_full_import`,
  `missing_selected_match`, `missing_selected_player`, `video_context_unavailable`,
  `blocked_by_youth_safety`, and `blocked_by_org_boundary`.
- Phase 6E explicitly names Phase 6F as the layer that adds deeper confidence and
  uncertainty mechanics on top of sufficiency checks.

### E. Existing prediction/model outputs and probability/confidence values

- `backend/routes/prediction.py` and `backend/services/prediction_service.py` expose
  win-probability series and match-state probability outputs.
- Current prediction responses include probability series data but do not yet expose a
  structured confidence package or sample-size qualification.
- Phase 6F defines the future contract that governs how model probability outputs are
  wrapped in confidence metadata before reaching any intelligence output.

### F. Existing Analyst Workspace outputs

- `backend/routes/analytics_case_study.py` and
  `backend/services/analytics_case_study.py` provide:
  - Case-study narrative summaries
  - Key player summaries
  - Momentum/phase breakdown structures
  - Full analyst reports
- None of these outputs currently carry a structured confidence/limitation package.
  Phase 6F defines what that package must look like.

### G. Existing Coach Pro Plus / video-analysis outputs and confidence-like fields

- `backend/routes/coach_pro_plus.py`, `backend/services/coach_ai_pipeline.py`,
  `backend/services/coach_report_service.py`.
- Video jobs expose terminal states `done` / `completed`.
- Coach AI pipeline produces coaching notes and mental-analysis outputs; no structured
  video-certainty or confidence score is currently attached.
- Phase 6F defines `video_confidence` as a required dimension when video data is used.

### H. Existing historical import validation, registry, provenance, and training eligibility

- `backend/routes/historical_import.py`:
  - Dry-run/apply/rollback/training-status/bulk-zip endpoints.
  - `metadata_only_pending_full_import` gating is deterministic; AI must not override it.
- `GET /analytics/matches/{match_id}/registry` returns:
  - `provenance`, `validation_status`, `registration_status`, `training_eligible`.
- Phase 6F defines how these deterministic gates feed into future confidence packages
  without undermining their authority.

### I. Existing fake-data guard and no-fake-data requirements

- `scripts/check-fake-data.js` scans for fabricated/demo data patterns.
- `.github/workflows/ci.yml` runs `npm run guard:fake-data` in CI.
- Phase 6A–6E governance already prohibits fabricated data; Phase 6F extends this to
  mandate `no_fake_data_confirmation: true` in every confidence package.

### J. Existing auth/RBAC/org boundary rules

- `backend/security.py`: `get_current_user`, `get_current_active_user`, `require_roles`.
- `backend/services/analyst_access.py`: org/user-scoped game access builders.
- Auth/RBAC checks must occur before confidence packages are assembled; the
  `not_authorized_to_access_context` uncertainty reason documents this boundary.

### K. Existing tests and CI gates relevant to future confidence validation

- `backend/tests/test_phase_6b_ai_boundary.py`: 37 tests proving AI boundary and
  official-truth mutation constraints.
- `.github/workflows/ci.yml`: pre-commit, lint/type checks, security scan, backend
  tests, frontend type-check/build, and fake-data guard.
- Phase 6F defines future validation test requirements; runtime tests are deferred until
  a confidence engine is implemented.

### L. Current risky patterns to prevent in future implementation

- Model probability outputs presented without sample-size context.
- Coaching recommendation language presented without low-sample warnings.
- Video-derived insights presented without visibility/certainty qualification.
- Analyst reports generated from incomplete or metadata-only historical records without
  explicit limitations.
- Youth-facing feedback using definitive language rather than safe developmental framing.

---

## 4) Strict Scope Lock for Phase 6F

### Allowed

- This architecture/spec document.
- Master checklist update for Phase 6F completion notes.
- Confidence score package contract and validation requirements for future implementation.
- Docs-only template: `docs/confidence_templates/confidence_score_package.example.yaml`.

### Conditionally allowed

- Docs-only template examples for confidence contracts.

### Not allowed

- Runtime confidence engine implementation.
- Validation agent implementation.
- Runtime skill implementation.
- Runtime router implementation.
- Supervisor/agent implementation.
- LLM provider/external AI integration.
- Migrations, dependencies, or infrastructure changes.
- Any production behavior changes to scoring, DLS, gameplay/live bus, historical import
  truth, registry/training eligibility, or auth boundaries.

---

## 5) Required Confidence Dimensions

Every future Cricksy intelligence output confidence package must include these dimensions:

### 5.1 `data_quality_confidence`

Reflects whether the underlying data is validated, complete, and accurate.

- Factors: validation status, finalization state, presence of delivery data vs metadata-only,
  import integrity, registry linkage.

### 5.2 `sample_size_confidence`

Reflects whether sufficient observations exist to support a reliable insight.

- Factors: number of deliveries, innings, matches, opponents faced, historical lookback depth.

### 5.3 `tactical_confidence`

Reflects whether the tactical interpretation is supported by clear deterministic signals.

- Factors: strength of phase/momentum/dismissal patterns, signal-to-noise ratio across events.

### 5.4 `video_confidence`

Applies only when video data is used. Reflects video visibility and certainty.

- Factors: clip completeness, camera angle quality, tagged event coverage, analyst
  confirmation state.
- Must be set to `not_applicable` when no video data is used.

### 5.5 `model_confidence`

Applies only when a model output is used. Reflects calibration and reliability.

- Factors: model calibration status, recency of training data, match conditions similarity,
  probability spread vs certainty.
- Must be set to `not_applicable` when no model output is used.

### 5.6 `recommendation_confidence`

Reflects how confidently a coaching/selection/tactical recommendation can be made.

- Factors: combined signal strength from data quality, sample size, tactical evidence, and
  model reliability.

### 5.7 `overall_confidence`

Aggregate confidence across all applicable dimensions.

- Must be the lowest of all applicable dimension scores unless otherwise defined by
  skill-specific rules.

### 5.8 `limitations`

Free-text list of known limitations affecting this output.

- Required whenever overall confidence is below `high_confidence`.
- Must be presented to the user in plain language.

### 5.9 `uncertainty_reasons`

Structured list of uncertainty reason codes (see Section 8).

- Must always be present; empty list is valid for high-confidence outputs.

### 5.10 `review_required`

Boolean. Indicates whether human review is required before this output reaches an end user.

- See Section 10 for mandatory review trigger rules.

---

## 6) Required Confidence Package Contract

Every future Cricksy confidence package must define all fields below:

- `confidence_package_id` — unique identifier for this confidence evaluation
- `intent_id` — the intent this confidence package is tied to
- `skill_id` — the skill that produced the output
- `context_package_id` — the Phase 6E context package this was built from
- `output_type` — the `AiOutputType` classification of the output
- `data_quality_confidence` — numeric score 0.0–1.0 or `not_applicable`
- `sample_size_confidence` — numeric score 0.0–1.0 or `not_applicable`
- `tactical_confidence` — numeric score 0.0–1.0 or `not_applicable`
- `video_confidence` — numeric score 0.0–1.0 or `not_applicable`
- `model_confidence` — numeric score 0.0–1.0 or `not_applicable`
- `recommendation_confidence` — numeric score 0.0–1.0 or `not_applicable`
- `overall_confidence` — numeric score 0.0–1.0
- `confidence_band` — one of the standard bands defined in Section 7
- `limitations` — list of plain-language limitation statements
- `uncertainty_reasons` — list of uncertainty reason codes defined in Section 8
- `required_disclaimers` — list of required user-facing disclaimer strings
- `review_required` — boolean
- `review_reason` — plain-language explanation of why review is required (null if false)
- `fallback_behavior` — the safe fallback outcome code if this output cannot be delivered
- `no_fake_data_confirmation` — boolean, must be `true`; false blocks output delivery
- `provenance_references` — list of data source/registry references used in this output

### 6A) Reference contract shape (docs-only, non-runtime)

```yaml
confidence_package_id: "conf_2026_05_14_momentum_001"
intent_id: "analyze_match_momentum"
skill_id: "match_momentum.v1"
context_package_id: "ctx_2026_05_14_match_momentum_001"
output_type: "insight"
data_quality_confidence: 0.92
sample_size_confidence: 0.85
tactical_confidence: 0.81
video_confidence: "not_applicable"
model_confidence: 0.79
recommendation_confidence: 0.80
overall_confidence: 0.79
confidence_band: "medium_confidence"
limitations:
  - "Win probability model has not been re-calibrated for current season conditions."
uncertainty_reasons:
  - "model_not_calibrated"
required_disclaimers:
  - "Model outputs are non-authoritative. Official match result is always the deterministic record."
review_required: false
review_reason: null
fallback_behavior: null
no_fake_data_confirmation: true
provenance_references:
  - "analytics_case_study.match_id=match_abc"
  - "registry.validation_status=valid"
  - "prediction.win_probability_series.match_id=match_abc"
```

---

## 7) Required Confidence Bands

Standard confidence bands define how an overall_confidence score maps to a
human-meaningful reliability tier.

These thresholds are governance defaults only. They are not runtime implementation.
Skill-specific rules may apply stricter thresholds for specific output types.

| Band | Threshold | Meaning |
|------|-----------|---------|
| `high_confidence` | >= 0.80 | Strong evidence, adequate sample, validated data |
| `medium_confidence` | 0.60–0.79 | Reasonable evidence; some limitations or gaps present |
| `low_confidence` | 0.40–0.59 | Weak evidence; significant limitations; treat as early signal |
| `insufficient_data` | < 0.40 or missing required context | Cannot support any reliable output |
| `not_applicable` | — | Confidence dimension does not apply to this output |

### 7A) Conceptual thresholds (docs-only)

```text
high_confidence:     overall_confidence >= 0.80
medium_confidence:   0.60 <= overall_confidence < 0.80
low_confidence:      0.40 <= overall_confidence < 0.60
insufficient_data:   overall_confidence < 0.40  OR  required context is missing
not_applicable:      confidence dimension does not apply to this output type
```

---

## 8) Required Uncertainty Reasons

Standard uncertainty reason codes must be used in the `uncertainty_reasons` field.

| Code | Meaning |
|------|---------|
| `small_sample_size` | Insufficient observations to support reliable insight |
| `missing_delivery_data` | Ball-by-ball delivery data is absent or incomplete |
| `metadata_only_pending_full_import` | Historical record contains only metadata; full import not yet applied |
| `video_context_unavailable` | Video data was expected but is absent or incomplete |
| `low_data_quality` | Source data failed validation or is of insufficient quality |
| `conflicting_signals` | Multiple data sources present contradictory signals |
| `model_not_calibrated` | Model has not been calibrated for current conditions or season |
| `insufficient_historical_context` | Not enough historical lookback data to establish a reliable pattern |
| `not_authorized_to_access_context` | Required context is present but the user is not authorized to access it |
| `youth_safety_review_required` | Output involves a youth player and requires safe developmental language review |
| `manual_review_required` | Output requires human review for reasons beyond automated validation |

Additional skill-specific uncertainty codes may be defined per skill, but these
standard codes must always be used where applicable.

---

## 9) Required User-Facing Language Rules

These rules govern how future Cricksy intelligence outputs communicate confidence
and limitations to end users. All output framing layers must comply.

### Rule 1 — Low-confidence insights must never be written as certain

❌ Incorrect framing:
```text
This player struggles against spin bowling.
```

✅ Correct framing (low_confidence band):
```text
Early signal: based on limited evidence, this player may have vulnerability against
spin. This should be treated as an early indication rather than a confirmed pattern.
```

### Rule 2 — Insufficient-data outputs must not produce recommendations

When `confidence_band = insufficient_data`, no recommendation may be generated.

Required output:
```text
Insufficient data: not enough evidence is available to produce a reliable insight on
this topic. Additional match data or a broader historical sample is required.
```

### Rule 3 — Small-sample insights must be labelled as early signals

When `small_sample_size` is present in `uncertainty_reasons`:
```text
Limited sample size: this recommendation is based on [N] deliveries against [context],
so treat it as an early signal rather than a confirmed weakness.
```

### Rule 4 — Model outputs must not be presented as guarantees

When `model_confidence` is used:
```text
Probability estimate: model outputs represent statistical likelihoods, not guaranteed
outcomes. Official match results always supersede model estimates.
```

### Rule 5 — Video-derived insights must expose video certainty/visibility limitations

When `video_confidence` is present and below `high_confidence`:
```text
Video certainty note: some clips used in this analysis had limited visibility or
incomplete coverage. Conclusions should be confirmed against full delivery data.
```

### Rule 6 — Youth/player feedback must use safe developmental language

When `youth_safety_review_required` is in `uncertainty_reasons` or the output
targets a youth player:

- Never use definitive criticism labels such as "weakness", "problem", or "fails".
- Frame all observations as development opportunities.
- Require human review before delivery.

```text
Development note: the analysis below highlights areas where focused practice may
help this player continue to grow. All observations are intended as coaching
guidance, not performance judgements.
```

### Rule 7 — Limitations must accompany every non-high-confidence output

All outputs with `confidence_band` below `high_confidence` must include a
`limitations` summary before the insight text.

---

## 10) Required Review Rules

Human review is required before an output reaches an end user in the following
conditions. Future validation agents and review queue mechanics (Phase 6H) must
enforce these rules.

| Trigger | Review Type |
|---------|------------|
| Youth player feedback is generated | Youth safety review |
| Mental health or performance criticism is generated | Welfare review |
| Public/podcast/media content is generated | Editorial review |
| Scouting report is generated | Governance review |
| `recommendation_confidence` is `low_confidence` or `medium_confidence` | Analyst review |
| `sample_size_confidence` is `low_confidence` or `insufficient_data` | Analyst review |
| `model_confidence` is `low_confidence`, `insufficient_data`, or `model_not_calibrated` | Technical review |
| `video_confidence` is `low_confidence` or `insufficient_data` | Analyst review |
| `conflicting_signals` is present in `uncertainty_reasons` | Analyst review |
| Output may affect training, selection, workload, or player development decisions | Governance review |

When `review_required = true`, the output must include a `review_reason` explaining
which trigger was met.

---

## 11) Required Fallback Behavior

When a confidence package cannot support output delivery, the following safe fallback
outcomes must be returned. These are the only valid fallback states.

| Fallback Code | When to Use |
|---------------|------------|
| `insufficient_data` | overall_confidence < 0.40 or required context is missing |
| `low_confidence_review_required` | Output can be generated but confidence is low; human review required before delivery |
| `needs_more_context` | Context package is too narrow to support this intent; user should provide more scope |
| `sample_size_too_small` | Sample size falls below the skill-defined minimum threshold |
| `model_uncalibrated` | Model has not been calibrated; output cannot be trusted without review |
| `video_context_unavailable` | Video was required but is absent or unusable |
| `blocked_by_youth_safety` | Youth safety review is required and has not been completed |
| `not_authorized` | User does not have permission to access required context |
| `metadata_only_pending_full_import` | Historical data is metadata-only; full import must be completed before reliable insight |

Fallback outputs must never fabricate missing evidence and must preserve deterministic
authority.

---

## 12) Required Example Confidence Packages

### 12.1 — High-Confidence Match Momentum Insight

**Scenario**: Complete T20 match with validated delivery data, phase breakdown, and
calibrated win-probability model. Analyst Pro role. One selected match.

```yaml
confidence_package_id: "conf_ex_001"
intent_id: "analyze_match_momentum"
skill_id: "match_momentum.v1"
context_package_id: "ctx_ex_001"
output_type: "insight"
data_quality_confidence: 0.95
sample_size_confidence: 0.91
tactical_confidence: 0.88
video_confidence: "not_applicable"
model_confidence: 0.85
recommendation_confidence: 0.87
overall_confidence: 0.85
confidence_band: "high_confidence"
limitations: []
uncertainty_reasons: []
required_disclaimers:
  - "Model outputs are non-authoritative. Official match result is always the deterministic record."
review_required: false
review_reason: null
fallback_behavior: null
no_fake_data_confirmation: true
provenance_references:
  - "analytics_case_study.match_id=match_abc"
  - "registry.validation_status=valid"
  - "prediction.win_probability_series.match_id=match_abc"
```

**User-facing framing**:
```text
High confidence: momentum shifted decisively in overs 14–16 following two wickets
and a run-rate drop from 11.2 to 7.4. The bowling side capitalised on pressure
phase execution to swing the match.
```

---

### 12.2 — Low-Sample Spin Weakness Insight

**Scenario**: One player with only 18 deliveries against spin across two innings.
Analyst Pro role. Single match context.

```yaml
confidence_package_id: "conf_ex_002"
intent_id: "analyze_spin_weakness"
skill_id: "player_spin_weakness.v1"
context_package_id: "ctx_ex_002"
output_type: "insight"
data_quality_confidence: 0.88
sample_size_confidence: 0.32
tactical_confidence: 0.55
video_confidence: "not_applicable"
model_confidence: "not_applicable"
recommendation_confidence: 0.34
overall_confidence: 0.32
confidence_band: "insufficient_data"
limitations:
  - "Only 18 deliveries against spin are available. Minimum reliable threshold is 40 deliveries."
  - "Single-match context; no cross-match historical lookback available."
uncertainty_reasons:
  - "small_sample_size"
  - "insufficient_historical_context"
required_disclaimers:
  - "This output is based on a very limited sample and must not be treated as a confirmed pattern."
review_required: true
review_reason: "sample_size_confidence is insufficient_data; recommendation_confidence is insufficient_data."
fallback_behavior: "sample_size_too_small"
no_fake_data_confirmation: true
provenance_references:
  - "analytics_case_study.match_id=match_xyz"
  - "registry.validation_status=valid"
```

**User-facing framing**:
```text
Limited sample size: this observation is based on only 18 deliveries against spin,
so treat it as an early signal rather than a confirmed weakness. A reliable
assessment requires at least 40 deliveries against spin bowling.
```

---

### 12.3 — Video-Analysis Insight with Medium Video Certainty

**Scenario**: Coach Pro Plus video job completed for a batting session. Some clips
have limited angle coverage. Coach Pro Plus role.

```yaml
confidence_package_id: "conf_ex_003"
intent_id: "analyze_batting_technique"
skill_id: "coach_batting_technique.v1"
context_package_id: "ctx_ex_003"
output_type: "recommendation"
data_quality_confidence: 0.80
sample_size_confidence: 0.72
tactical_confidence: 0.68
video_confidence: 0.63
model_confidence: "not_applicable"
recommendation_confidence: 0.63
overall_confidence: 0.63
confidence_band: "medium_confidence"
limitations:
  - "Three of seven clips have limited camera angle coverage of foot movement."
  - "Analysis is based on a single training session; match-condition context is absent."
uncertainty_reasons:
  - "video_context_unavailable"
  - "small_sample_size"
required_disclaimers:
  - "Video certainty is medium. Some clips had limited visibility. Confirm observations in match context."
review_required: true
review_reason: "video_confidence is medium_confidence; recommendation_confidence is medium_confidence."
fallback_behavior: "low_confidence_review_required"
no_fake_data_confirmation: true
provenance_references:
  - "coach_pro_plus.job_id=job_789"
  - "coach_pro_plus.status=done"
```

**User-facing framing**:
```text
Video certainty note: some clips used in this analysis had limited visibility.
The following observations are based on available footage and should be confirmed
with live match footage before inclusion in a formal coaching report.
```

---

### 12.4 — Metadata-Only Historical Import Training Eligibility Review

**Scenario**: Historical import batch applied with metadata only; full delivery import
not yet completed. Training eligibility gate is blocked by deterministic rule.

```yaml
confidence_package_id: "conf_ex_004"
intent_id: "review_training_eligibility"
skill_id: "training_eligibility_review.v1"
context_package_id: "ctx_ex_004"
output_type: "insight"
data_quality_confidence: 0.55
sample_size_confidence: "not_applicable"
tactical_confidence: "not_applicable"
video_confidence: "not_applicable"
model_confidence: "not_applicable"
recommendation_confidence: 0.00
overall_confidence: 0.00
confidence_band: "insufficient_data"
limitations:
  - "Import batch has metadata only; delivery-level data has not been applied."
  - "Training eligibility is blocked by deterministic gate until full import is complete."
uncertainty_reasons:
  - "metadata_only_pending_full_import"
  - "missing_delivery_data"
required_disclaimers:
  - "Training eligibility is a deterministic gate. It cannot be overridden by AI output."
  - "Complete the full delivery import before this record is eligible for training use."
review_required: true
review_reason: "metadata_only_pending_full_import; training_eligible gate is blocked."
fallback_behavior: "metadata_only_pending_full_import"
no_fake_data_confirmation: true
provenance_references:
  - "registry.batch_id=batch_456"
  - "registry.validation_status=metadata_only"
  - "registry.training_eligible=false"
```

**User-facing framing**:
```text
Training eligibility blocked: this historical record has been imported at the
metadata level only. Full delivery data must be applied before this match is
eligible for training use. This status is determined by the Cricksy registry
and cannot be overridden.
```

---

### 12.5 — Podcast/Analyst Media Output Requiring Review

**Scenario**: Analyst Pro prepares a podcast breakdown for a completed match. Output
is intended for public/media use. Review required before release.

```yaml
confidence_package_id: "conf_ex_005"
intent_id: "prepare_podcast_breakdown"
skill_id: "analyst_media_report.v1"
context_package_id: "ctx_ex_005"
output_type: "report"
data_quality_confidence: 0.90
sample_size_confidence: 0.86
tactical_confidence: 0.82
video_confidence: "not_applicable"
model_confidence: 0.77
recommendation_confidence: 0.79
overall_confidence: 0.77
confidence_band: "medium_confidence"
limitations:
  - "Win probability model not yet calibrated for this season."
  - "Two key over phases have limited delivery tagging."
uncertainty_reasons:
  - "model_not_calibrated"
  - "missing_delivery_data"
required_disclaimers:
  - "This content is prepared for editorial review. It must not be published without analyst approval."
  - "Model outputs are non-authoritative and must be clearly labelled in any public content."
review_required: true
review_reason: "Public/podcast content requires editorial review before release. model_confidence is medium_confidence."
fallback_behavior: "low_confidence_review_required"
no_fake_data_confirmation: true
provenance_references:
  - "analytics_case_study.match_id=match_pub_001"
  - "registry.validation_status=valid"
  - "prediction.win_probability_series.match_id=match_pub_001"
```

**User-facing framing**:
```text
Editorial review required: this podcast breakdown is ready for analyst review.
Some probability estimates are based on a model pending seasonal calibration —
these should be clearly labelled as estimates in any published content.
The official match scorecard is always the authoritative record.
```

---

## 13) Relationship to Phase 6G — Event-Triggered Intelligence Spec

Phase 6F defines **how reliable an output is**: confidence dimensions, bands,
limitations, uncertainty reasons, user-facing framing, and review triggers.

Phase 6G (to be defined) will define **when compute is triggered and how expensive
AI/model processing is controlled**: event triggers, always-on cheap signals vs
expensive triggered AI, cost/budget governance, and orchestration rules.

Phase 6G must not be collapsed into Phase 6F.

Confidence packages defined in Phase 6F will be consumed by Phase 6G event-triggered
workflows, but Phase 6G is a separate governance layer.

---

## 14) Relationship to Phase 6H — Validation Agents + Review Queue Spec

Phase 6F defines **what requires review** via the `review_required` field and
`review_reason` explanation.

Phase 6H (to be defined) will define **how review is carried out**: validation agent
mechanics, review queue routing, approval workflows, re-submission rules, and
escalation paths.

Phase 6H must not be collapsed into Phase 6F.

Review requirement flags set by Phase 6F confidence packages are the inputs to the
Phase 6H review queue, but Phase 6H mechanics are a separate governance layer.

---

## 15) Protected Systems (Unchanged by This Phase)

- official score/runs/balls/overs/wickets/innings state/match result/scorecards/player stats
- DLS calculations
- gameplay/live bus behavior
- historical import validation/provenance/training-eligibility gates
- Phase 5M registry endpoint behavior
- Phase 6B AI boundary guard behavior
- Phase 6C skill contract behavior
- Phase 6D intent/skill routing boundaries
- Phase 6E context-loading boundaries
- Coach Pro Plus/video analysis runtime
- mental analysis runtime
- auth/RBAC/org boundaries
- fake-data guard
- CI/CD gates

---

## 16) Future Confidence Validation Requirements

When a runtime confidence engine is implemented later, tests must include at minimum:

- confidence package contract completeness tests (all required fields present).
- `no_fake_data_confirmation: true` enforcement — output blocked if false.
- confidence band assignment correctness tests for each band threshold.
- `review_required = true` trigger correctness for all mandatory review conditions.
- user-facing framing rule enforcement tests (no certain language for low-confidence).
- `insufficient_data` fallback tests when required context is missing.
- `metadata_only_pending_full_import` blocking tests for training eligibility outputs.
- `blocked_by_youth_safety` review-gate tests.
- `model_not_calibrated` flagging and review-gate tests.
- regression tests proving Phase 6B official-truth mutation guard remains intact.
- regression tests proving Phase 6C skill contract confidence fields are correctly
  populated by any skill that produces a confidence package.
- regression tests proving Phase 6D routing contract `confidence_requirements` and
  `review_requirements` align with Phase 6F rules.
- regression tests proving Phase 6E `confidence_inputs` and `sufficiency_status` are
  correctly forwarded to Phase 6F confidence evaluation.

---

## 17) Validation Notes

- Markdown formatting reviewed (headings, tables, lists, fenced YAML blocks).
- Phase ordering remains clear; Phase 6G–6H remain future and are not marked complete.
- This phase is architecture/spec-lock only; no runtime implementation was added.
- No new dependencies, migrations, external AI provider calls, or production behavior
  changes were introduced.
- Template file `docs/confidence_templates/confidence_score_package.example.yaml`
  is clearly non-runtime documentation only.

---

## 18) Confirmation Statements

- This is confidence architecture/spec only.
- No runtime confidence engine was implemented.
- No validation agents, runtime skills, runtime routers, or Supervisor logic were implemented.
- No agents were built.
- No LLM workflows or external AI provider calls were added.
- No migrations or dependencies were added.
- No runtime behavior changed.
- Phase 6B boundary, Phase 6C skill contract, Phase 6D routing boundaries, and
  Phase 6E context-loading boundaries remain intact.

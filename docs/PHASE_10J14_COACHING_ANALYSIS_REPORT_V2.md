# Phase 10J.14 — Coaching Analysis Report V2 & Governed Cricket Coaching Actions

## Scope and authority

Issue #503 and the merged Phase 10J.1–10J.13 implementation are authoritative. This is an
additive report-interpretation change. It does not alter video analysis, V2 metric generation,
RBAC, player isolation, goal/intervention persistence, Player Development, Match Setup, or
legacy analysis records.

## Audit findings

### Existing analysis and persistence

- `VideoAnalysisJob.quick_results` and `deep_results` persist the analysis artifacts used by the
  export route. The worker already writes `results.v2.repetitions`, `results.v2.phases`, and
  discipline-prefixed `results.v2.metric_results`.
- `coach_strength_consistency.attach_strength_consistency_engine` adds the same persisted
  `v2_session_analysis` under `results.findings` and `results.report`. It contains strengths,
  recurring concerns, consistency observations, representative repetitions, and excluded
  metrics. PDF generation therefore needs no re-analysis or CV/model call.
- Batting, pace bowling, spin bowling, wicketkeeping, and fielding already have V2 metric packs.
  Their validity, confidence, classification, phase, evidence references, and limitations are
  authoritative. A report must not recompute or reverse-engineer metric direction.

### Existing UI interpretation

- `CoachProPlusVideoSessionsView.vue` uses
  `frontend/src/utils/coachVideoAnalysisRepetitions.ts` to read the selected persisted result
  payload (`deep_results`, otherwise `quick_results`).
- The UI reads the V2 repetitions, phases, discipline-prefixed metric results, and
  `v2_session_analysis`. The new PDF adapter reads those same persisted fields and selection
  order. This gives UI/PDF evidence parity without a duplicate frontend model.

### Root cause of report drift

`pdf_export_service.generate_analysis_pdf` previously ignored persisted V2 interpretation. It
merged `quick_findings` and `deep_findings` through `findings_adapter`, then rendered legacy
finding definitions, free-form coaching suggestions, and generated weekly actions. That path:

- could disagree with the V2 UI;
- could turn missing frame/detection values into zero;
- could infer Pass/Fail from a generic 0.5 threshold without knowing metric direction;
- could expose legacy stop/suspend, injury-risk, fitness, conditioning, or physio language; and
- had no discipline/phase-governed action registry.

The failures share one architectural cause: the PDF had a second, legacy interpretation path
instead of consuming the persisted V2 evidence contract.

## Design decision

### Authoritative V2 report adapter

`backend/services/coach_report_v2.py` is a pure, deterministic adapter. It performs no I/O and
no analysis. It:

- accepts only the already-selected persisted result payload;
- retains only known V2 discipline metric prefixes;
- bounds confidence and normalized values to 0–1 and rejects NaN, infinity, negative frame/time,
  and malformed integer values;
- preserves persisted classifications only for measurable metrics;
- emits `Unavailable` plus a reason for non-measurable evidence rather than a numeric fallback;
- uses valid persisted recurring concerns (or valid `NEEDS_ATTENTION` classifications) to select
  at most three technical priorities;
- retains strength, consistency, representative-repetition, evidence-reference, limitation,
  coach-intervention, and longitudinal evidence provenance; and
- explicitly marks longitudinal comparisons as observational, not causal.

### Governed coaching-action registry

`backend/services/coaching_action_registry.py` is a static, versioned, deterministic registry.
It maps action candidates by exact discipline and phase/metric term. The metric prefix is
authoritative, and generic `bowling` never guesses pace versus spin.

Each action has a stable ID and version, technical area, objective, cue, bounded drills, coach
observation, reassessment criterion, source provenance, review status, and player-facing policy.
Registry entries are coach-facing candidates only: `requires_coach_approval=true` and
`player_facing_eligible=false`. They do not create or activate a Player Development plan and do
not bypass existing coach approval.

Source basis:

- [ECB Core Coach briefing](https://resources.ecb.co.uk/ecb/document/2021/11/09/abb54d97-4dc5-4f9c-aef1-e3642fd9dc0d/ECB_SUP_FND_I_Core_Coach_briefing.pdf): player-centred planning, practice design, safety, and
  discipline-specific core principles.
- [ICC Coaching Course Level 2](https://www.icc-cricket.com/media-releases/icc-strengthens-training-and-education-programme-with-launch-of-level-2-coaching-course):
  biomechanics, video analysis, skill acquisition, and specialist batter, bowler, and
  wicketkeeper coaching.
- Cricksy's Phase 9G Player Development skill contract and Phase 10J V2 discipline/phase
  contracts define the in-product evidence, approval, safety, and organization boundaries.

The action wording is an internal adaptation for coach review, not a claim that either external
source prescribes a specific automated correction.

### Rendering and compatibility boundary

For a result payload containing persisted V2 repetitions, phases, or metrics, the PDF renders:

1. Executive Coaching Summary
2. Repetition & Phase Analysis
3. Technical Development Areas
4. Strengths & Consistency
5. Coach-Approved Action Plan
6. Progress / Longitudinal Evidence, when available
7. Appendix: Evidence & Limitations

The section title requested by Issue #503 is retained, but the copy distinguishes registry
candidates from actions actually approved or recorded by a coach. Free-form legacy suggestions
and legacy findings are never merged into a V2 report.

Jobs without persisted V2 evidence keep the existing historical renderer. No legacy record is
rewritten, no V2 data is backfilled, and no re-analysis is triggered.

## Safety and isolation evidence

- The existing export route continues to own entitlement, coach access, session/job lookup, and
  organization/player isolation. This phase changes no route or query.
- The adapter sees only the already-authorized job payload passed by that route.
- Registry actions cannot become player-facing automatically and contain no medical,
  injury-risk, rehabilitation, workload, strength/conditioning, or stop/suspend prescription.
- Dynamic report text is escaped before ReportLab paragraph rendering.
- Missing/invalid evidence is explicit and cannot become a zero score or generic Pass/Fail.

## Persistence, migration, and performance

No migration is required. V2 artifacts, goal/intervention evidence, and longitudinal evidence
already live in existing JSON fields and records. The registry is versioned source code, not a
new player, plan, or action persistence model.

PDF work is linear in the size of the persisted report payload. It performs no database query,
network request, model inference, pose calculation, frame extraction, or video re-analysis.

## Test strategy

- Batting and pace-bowling reports verify persisted repetitions, phases, priorities,
  consistency, representative repetitions, and discipline-correct actions.
- Registry parameterization covers batting, pace bowling, spin bowling, wicketkeeping, and
  fielding plus cross-discipline rejection and generic-bowling ambiguity.
- Non-measurable zero-like data and NaN are rendered unavailable rather than treated as scores.
- Action governance, coach-recorded interventions, and non-causal longitudinal evidence are
  asserted.
- V2 PDF tests make legacy finding consolidation and free-form suggestion rendering fail if
  invoked, proving unsafe legacy text cannot leak into the V2 path.
- A legacy-only PDF regression verifies historical jobs remain exportable.

## Rollback

Revert the report adapter, registry, V2 renderer, and the small V2 dispatch block in
`pdf_export_service.py`. Because there is no schema migration or persisted-data mutation,
rollback immediately restores the prior export renderer without data conversion.

## Deferred work and risks

- The registry is intentionally small. Additional discipline/phase actions require a new
  registry version, source review, safety review, and tests; they are not inferred at runtime.
- A dedicated coach UI for accepting registry candidates into Player Development is outside
  Phase 10J.14. Existing coach-created/approved goal and intervention workflows remain the
  activation mechanism.
- Historical reports can still contain legacy language because compatibility requires the old
  path. The safety boundary applies to authoritative V2 reports; retroactive legacy migration
  was not authorized.

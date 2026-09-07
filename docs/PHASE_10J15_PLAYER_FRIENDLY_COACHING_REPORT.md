# Phase 10J.15 — Player-Friendly Coaching Report and V2 UI Simplification

## Pre-implementation audit and scope lock

Audit completed against `main` at `868cd00d89cfe67ac399caf4aec78bd0e275681e`, after
Phase 10J.14 was merged.

### Presentation paths

- `backend/routes/coach_pro_plus.py` loads the persisted `quick_results` / `deep_results`
  JSON for a completed analysis job and passes it to
  `backend/services/pdf_export_service.py` for export.
- `pdf_export_service.generate_analysis_pdf` selects `deep_results` before
  `quick_results`. When `coach_report_v2.has_persisted_v2_evidence` detects persisted
  repetitions, phases, or discipline metrics, it builds the Phase 10J.14 report adapter
  and calls `reports/coach_report_template.render_coaching_analysis_report_v2`. Jobs
  without V2 evidence stay on `_render_legacy_report`.
- `coach_report_v2.py` sanitizes persisted measurements, selects evidence-supported
  priorities, resolves governed actions through `coaching_action_registry.py`, and
  carries strengths, consistency, representative repetitions, limitations, and
  longitudinal goal evidence without rerunning analysis.
- The current V2 PDF renderer prints raw metric IDs, repetition IDs, phase IDs/enums,
  exact confidence decimals, and proxy states in the player-facing pages. Its metrics,
  repetition, and phase tables contain plain strings rather than wrapping paragraphs;
  long identifiers therefore create the observed width/overflow pressure on pages 2–3.
  The appendix already has a deliberate page break, but does not yet contain the full
  repetition/phase trace needed after those identifiers move out of the main report.
- `frontend/src/views/CoachProPlusVideoSessionsView.vue` receives persisted job result
  JSON through `coachPlusVideoService.ts`. `coachVideoAnalysisRepetitions.ts` selects
  deep before quick evidence and normalizes repetitions, phases, metrics, recurring
  signals, consistency, and representative repetitions for the Analysis Results modal.
- The legacy `Priorities` block is built by
  `frontend/src/utils/coachVideoAnalysisNarrative.ts`: `buildCoachNarrative` reads
  `results.findings` / `results.coach.findings`, creates legacy priorities and drills,
  and the view renders them unconditionally after the V2 sections. This is the exact
  path that can contradict V2 evidence and reintroduce legacy safety language.
- The frontend currently title-cases identifiers locally. It displays `Rep N`, raw
  supporting repetition IDs, percent confidence, title-cased validity enums, the word
  `proxy`, consistency method/value details, and a technical longitudinal card.
  `PlayerLongitudinalProgress.vue` renders per-metric tables even where comparison is
  not yet meaningful.
- Existing report coverage is concentrated in
  `backend/tests/test_coach_report_v2.py`, with legacy PDF coverage in the existing PDF
  and report service tests. Analysis Results coverage is in
  `frontend/tests/unit/CoachProPlusVideoSessionsView.spec.ts` and the normalization
  utility tests.
- No reusable V2 player-presentation contract currently spans backend and frontend.
  Phase 10J.14 governed action wording and the longitudinal API's `metric_label` are
  reusable. The strength/consistency engine already uses deterministic confidence
  boundaries of `0.8` and `0.6`, and recurring concerns require three valid comparable
  repetitions. These existing thresholds remain authoritative.

### Implementation architecture

One deterministic backend presentation layer will map exact production metric IDs,
phase IDs, discipline/action repetition names, confidence bands, validity/proxy text,
consistency states, progress states, and insufficient-evidence summaries. The existing
technical report remains unchanged underneath and gains a player-presentation view.
PDF rendering consumes that view. Job read responses expose the same computed view to
the V2 UI, so UI and PDF agree on priority/action presence without persisting new data
or coupling Vue to Python implementation details.

### Expected files to change

- `backend/services/coach_report_presentation.py` (new)
- `backend/services/coach_report_v2.py`
- `backend/services/pdf_export_service.py`
- `backend/services/reports/coach_report_template.py`
- `backend/routes/coach_pro_plus.py`
- targeted backend report, route, and presentation tests
- `frontend/src/services/coachPlusVideoService.ts`
- `frontend/src/views/CoachProPlusVideoSessionsView.vue`
- `frontend/src/components/PlayerLongitudinalProgress.vue`
- targeted frontend Analysis Results and longitudinal tests
- this document and the Phase 10J execution/checklist entries

### Protected files and behavior

- All pose/CV, repetition segmentation, phase recognition, and V2 metric-pack code.
- `backend/services/coaching_action_registry.py` and its governance decisions.
- `backend/services/coach_findings.py`; legacy infrastructure remains available only
  for historical/non-V2 rendering.
- Database models, schemas, migrations, authentication, scoring, Match Setup, and
  Player Development core logic.
- Persisted V2 IDs, measurements, validity, proxy state, confidence, evidence
  references, and longitudinal calculations.

### Migration and performance decision

No migration is needed. Presentation is computed deterministically from already-loaded
persisted evidence. It performs bounded mapping and formatting only; it does not invoke
pose extraction, segmentation, phase recognition, metric computation, or additional
database queries.

## Implemented presentation contract

- The technical Phase 10J.14 report remains authoritative and unchanged; its derived
  `player_presentation` is used by both the V2 PDF renderer and Analysis Results API.
- Explicit maps cover every production metric/action-registry contract and every
  production phase. Unknown IDs fall back to neutral labels and never use fuzzy matching.
- Confidence bands use the existing `0.8` high and `0.6` low-confidence boundaries.
  Validity and proxy enums are translated without changing or discarding their exact
  appendix values.
- Repetition names are ordered by persisted timing and use Shot, Delivery, Take,
  Stumping, Catch, Throw, or discipline-neutral attempt labels as supported by the
  persisted discipline/action contract.
- Sessions below the existing three-comparable-repetition minimum receive one summary,
  retain readable phase review, and cannot create a priority or governed action from
  insufficient evidence.
- Longitudinal calculations remain in the existing engine. The API adds a deterministic
  player view: zero series is `Cannot compare yet`, fewer than two comparable sessions is
  `Not enough sessions yet`, and two or more use the existing trend state in plain language.
- The PDF uses wrapped single-column cards and deliberate page breaks. Exact job,
  repetition, phase, metric, confidence, validity, proxy, evidence, and governed-action
  identifiers are isolated in the technical appendix.
- V2 jobs are gated away from `buildCoachNarrative` output in the UI; historical jobs
  continue to render the legacy Priorities path.

# PHASE 10J.0 — Coaching Analysis Engine V2 Repository Audit + Spec Lock

## 1. Executive Summary

Phase 10J.0 audit completed against current `main` with read-only runtime analysis and no runtime code modification. The repository already has a production-grade Coach Pro Plus pipeline (session + upload + staged quick/deep analysis + findings + governed recommendations + PDF export), but it remains **video-job-centric** and **context-level**, not yet fully **player-discipline-repetition-phase-metric longitudinal**.

Spec lock decision:
- Reuse existing Coach Pro Plus, governance, player development, worker, and reporting infrastructure.
- Add V2 as dependency-ordered extensions.
- Keep deterministic ownership for measurements; AI remains interpretation-only.
- Require compatibility guards for progress comparisons.
- Keep implementation phases pending user approval.

## 2. Current Architecture Map

- Backend API orchestration: `backend/routes/coach_pro_plus.py`
- Session/job persistence: `backend/sql_app/models.py` (`VideoSession`, `VideoAnalysisJob`, chunk models)
- Worker execution: `backend/workers/analysis_worker.py`
- Deep chunk finalization: `backend/services/chunk_aggregation.py`
- Deterministic pose metrics: `backend/services/pose_metrics.py`
- Findings/report synthesis: `backend/services/coach_findings.py`, `backend/services/coach_report_service.py`
- AI narrative/suggestions: `backend/services/coach_ai_pipeline.py`, `backend/services/coach_suggestions.py`
- Ball tracking: `backend/services/ball_tracking_service.py`
- Upload/chunk/recovery: `backend/services/video_chunking.py`, `backend/services/video_job_recovery.py`
- Comparison/goals: `backend/services/session_comparison.py`, `backend/services/goal_compliance.py`
- PDF export: `backend/services/pdf_export_service.py`
- Player development governance (9G/9H): player-dev services/routes/contracts and audit trail
- Frontend workflow: `frontend/src/views/CoachProPlusVideoSessionsView.vue`, `frontend/src/stores/coachPlusVideoStore.ts`, `frontend/src/services/coachPlusVideoService.ts`

## 3. Current Coach/Player Session Workflow

Current flow:
1. Coach creates video session (`/api/coaches/plus/sessions`) with `title`, optional `analysis_context`, `camera_view`, and `player_ids` list.
2. Frontend currently captures player IDs as manual comma-separated text.
3. Upload initiated (`/videos/upload/initiate`) creates job and S3 key.
4. Upload complete (`/videos/upload/complete`) queues job.
5. Worker runs quick/deep analysis and persists findings/report artifacts.
6. Coach reviews outputs and optional governed recommendation integrations.

## 4. Current Analysis Engine Architecture

- Staged lifecycle present (`awaiting_upload`, `queued`, `quick_running`, `quick_done`, `deep_running`, `done` + legacy states).
- Deterministic metric calculation and threshold findings are implemented.
- Evidence markers attached (`worst_frames`, `bad_segments`, timestamps).
- Ball-tracking augmentation exists (primarily bowling utility).
- CPU and GPU/chunk paths coexist.
- Known consistency risk: deep chunk aggregation has `analysis_mode` fallback chain where other paths enforce mode more strictly.

## 5. Existing Reusable Infrastructure

Strong reuse candidates:
- RBAC/feature gating and owner scoping for Coach Pro Plus.
- VideoSession/VideoAnalysisJob schema and upload lifecycle.
- S3/SQS worker framework.
- Deterministic pose and findings/report layers.
- Session comparison and goal/outcome primitives.
- Coach suggestions and governed recommendation review card integration.
- Player development contracts, approval states, evidence mapping, audit logs (Phase 9G/9H).
- PDF export pipeline.

## 6. Existing Metric Inventory

Current deterministic metrics (pose-based):
- `head_stability_score`
- `balance_drift_score`
- `front_knee_brace_score`
- `hip_shoulder_separation_timing`
- `elbow_drop_score`

Current properties:
- Source: `backend/services/pose_metrics.py`
- Findings thresholds/mode interpretation: `backend/services/coach_findings.py`
- Evidence output: per-metric threshold + poor segments/frames
- Confidence influenced by pose quality/coverage

Current gap:
- No standardized V2 metric version contract spanning repetition/phase longitudinal compatibility.

## 7. Discipline-by-Discipline Capability Matrix

- Batting: partial support through generic pose metrics (A/B mix).
- Bowling (combined): best supported due to existing ball-tracking integration (A/B mix).
- Wicketkeeping: context exists but specialist metric coverage is limited (mostly C/D).
- Fielding: context exists but specialist action segmentation/throw/catch analysis limited (mostly C/D).
- Pace vs spin split: not yet first-class; currently mostly generalized bowling logic.

## 8. Current Progress/Comparison Architecture

- Existing compare endpoint compares jobs (session-oriented) rather than full player metric history compatibility graph.
- UI component exists (`SessionComparison.vue`) but not yet player-longitudinal V2 contract with metric-version/camera-condition safeguards.

## 9. Player Development / Phase 9G / Phase 9H Integration

- Completed governed recommendation and player-development review stack already exists.
- Evidence mapping service already links video analysis outputs to development contracts.
- Approval controls and player-facing suppression are present.
- 10J must extend this, not duplicate it.

## 10. Current Goals/Outcomes/Intervention Architecture

- Goals/outcomes/compliance and coaching suggestions exist in Coach Pro Plus stack.
- Missing piece is stronger deterministic linkage from repetition/phase metric states to longitudinal intervention effectiveness tracking.

## 11. Confidence/Safety Gaps

Missing/partial for V2:
- Unified validity-state taxonomy at metric/phase/repetition/session levels.
- Explicit unsupported camera/FPS gating per metric.
- Robust physically implausible range guards across all future metrics.
- Strong compatibility guards for trend comparisons.

## 12. Object Tracking / Vision Gaps

- Ball tracking exists (heuristic/OpenCV style).
- No robust bat detection contract for bat-path/contact reliability.
- No dedicated glove/stump detection pipeline.
- Pose alone is insufficient for some specialist wicketkeeping/fielding and bat-contact metrics.

## 13. Data Model Gap Analysis

Current model strengths:
- Session/job entities, staged artifacts, context/camera fields, player ID array.

Gaps:
- No first-class V2 entities for repetitions/phases/metric-versioned metric results.
- No explicit compatibility metadata for safe longitudinal compare (capture setup, validity envelope).

## 14. API Gap Analysis

Current endpoints cover session/job lifecycle, compare-jobs, goals/outcomes, suggestions, PDF.

Gaps for V2:
- Player-centered creation flow with validated player selection.
- Repetition/phase result retrieval.
- Longitudinal trend endpoints keyed by player/discipline/metric.
- Version-aware compatibility signaling for compare/report consumers.

## 15. Frontend Gap Analysis

Current strengths:
- Mature Coach Pro Plus view/store/service with staged job handling and recommendation review integration.

Gaps:
- Session creation still relies on manual comma-separated player IDs.
- No dedicated player-select/create + discipline-specific focus wizard.
- No repetition timeline/phase editor/correction UI.
- No full player-longitudinal V2 dashboard contract.

## 16. Worker/Performance Gap Analysis

Current strengths:
- Async pipeline, quick/deep split, chunk support, recovery utilities.

Gaps:
- Segmentation + phase recognition + per-repetition evidence expansion will increase compute and storage pressure.
- Need staged rollout with CPU-first deterministic subset and optional heavier object tracking tiers.

## 17. Storage Gap Analysis

Current storage includes video, staged JSON artifacts, optional frame payloads, PDFs.

Gaps:
- Repetition/phase metadata and per-metric evidence references need durable storage model.
- Must avoid storing all frames; prefer references/timestamps/keyframes.

## 18. RBAC/Governance Gap Analysis

Current strengths:
- Coach Pro Plus access control and governed recommendation approval.

Gaps:
- Parent-facing layer requirements are not explicit in current Coach Pro Plus flows.
- Must ensure player/parent outputs remain derived only from approved governed evidence.

## 19. V2 Metric Contract Specification

Recommended contract (field-optional by metric):
- identity: `schema_version`, `metric_version`, `metric_id`, `discipline`, `action_type`, `phase`
- value: `raw_value`, `unit`, `normalized_score` (optional), `classification_status`
- quality: `confidence_score`, `validity_state`, `unavailable_reason`, `limitations`
- capture context: `camera_requirements`, `source_model`, `capture_profile`
- evidence: `evidence_refs`, `timestamp_refs`, `frame_refs`
- aggregation/progress: `repetition_values`, `aggregate_stats`, `consistency`, `baseline`, `previous_value`, `personal_best`, `coach_target`, `trend`

Rules:
- no forced 0–100 normalization;
- metric version required for compare eligibility;
- invalid/unsupported states are first-class outcomes.

## 20. Repetition/Action Contract Specification

Recommended entity fields:
- `repetition_id`, `session_id`, `job_id`, `discipline`, `action_type`
- `start_ts`, `end_ts`, `start_frame`, `end_frame`
- `segmentation_method`, `segmentation_confidence`, `manual_override`
- `validity_state`, `insufficient_reason`
- evidence links and metric result references

## 21. Phase Contract Specification

Recommended fields:
- `phase_id`, `repetition_id`, `phase_name`
- `start/end` frame/time
- `detection_method`, `confidence`
- `requires_object_evidence` flags
- `camera_view_compatibility`
- `manual_correction_supported`

## 22. Longitudinal Progress Contract Specification

Comparison key:
`player_id + discipline + metric_id + metric_version + capture_profile_compatibility`

Required outputs:
- baseline/current/previous/delta/personal-best
- trend windows
- consistency trend
- persistent/resolved/emerging issue flags
- compatibility warnings (camera/FPS/view mismatch)

## 23. Goal/Intervention Integration Specification

Target chain:
`Finding → Priority → Goal → Intervention → Target → Reassessment → Outcome → Coach Decision`

Reuse:
- existing goals/outcomes/compliance/recommendation approval stack.

Extension:
- deterministic linkage from metric state changes to reassessment outcomes and progress evidence.

## 24. Coach/Player/Parent Interpretation Specification

Single governed evidence source with layered outputs:
- Coach: technical detail + limits.
- Player: simplified actionable explanation.
- Parent: non-technical progress framing.

Constraints:
- no extra claims beyond approved evidence;
- youth/privacy/RBAC constraints enforced;
- unapproved recommendations never player-facing.

## 25. PDF V2 Data Requirements

Required data dependencies before template redesign:
- player/session identity + discipline
- confidence/coverage block
- strengths/priorities
- metric scorecards by phase/repetition
- evidence references
- progress/trends
- goals/interventions/reassessment
- coach-approved player/parent summary section

## 26. Protected Existing Systems

Must preserve and extend (not replace):
- Coach Pro Plus upload/worker architecture
- existing deterministic metrics/findings/reporting
- player development governance and approvals (9G/9H)
- RBAC and feature gating
- existing PDF/export infrastructure

## 27. Files Likely to Change by Future Sub-Phase

Likely hotspots:
- backend routes/services/models/schemas/alembic for video-analysis V2 extensions
- worker + chunk aggregation for segmentation/phase pipelines
- frontend Coach Pro Plus flow/components/store/service
- tests across backend/frontend/integration/RBAC
- docs/checklists/governance artifacts

## 28. Files That Must Not Change Without Separate Approval

- core unrelated gameplay scoring domain
- unrelated analytics modules outside Coach Pro Plus/player-development scope
- existing governance protections that block unapproved player-facing recommendations

## 29. Required Migrations

Expected migration themes (implementation phases only):
- repetition/phase entities
- metric result/versioning entities (or carefully bounded JSON+index approach)
- longitudinal compatibility/capture-profile metadata
- intervention linkage enrichment

No migration executed in 10J.0.

## 30. Required Tests

Per sub-phase test mix required:
- deterministic metric unit tests + sanity/invalid-range tests
- segmentation/phase service tests
- API tests for compatibility and RBAC
- migration tests
- worker pipeline regression and recovery tests
- frontend flow tests and state sync tests
- longitudinal comparison compatibility tests

## 31. CPU/GPU Cost Classification

- Low-cost CPU deterministic: metadata validation, threshold/classification, compatibility checks
- Heavier CPU: segmentation heuristics, phase detection logic
- GPU beneficial: dense object-tracking inference over long videos
- GPU required (advanced optional tiers only): heavier multi-object or high-resolution multi-stream analytics

## 32. Dependency Map

Dependency chain:
1. Contracts/spec + compatibility rules
2. Data/API foundation
3. Session flow/player anchoring
4. Segmentation/phase backbone
5. Discipline-specific metric rollout
6. Strength/consistency + progress engine
7. Goal/intervention/report integration
8. Hardening/perf/CI finalization

## 33. Risk Register

Top risks:
- mode/discipline compatibility drift across quick/deep paths
- false precision from pose-only unsupported metrics
- longitudinal comparisons across incompatible capture setups
- duplication of existing 9G/9H governance flows
- worker/storage cost escalation from dense evidence payloads

Mitigations:
- explicit validity states, versioned contracts, compatibility gates, staged rollout.

## 34. Recommended Final Phase 10J Sub-Phase Sequence

### 10J.1 — V2 Contract + Compatibility Foundations
- Objective: lock metric/repetition/phase/progress contracts and compatibility rules in code-level schema/API design.
- Why: all downstream work depends on stable contract.
- Dependencies: 10J.0.
- Reuse: existing findings/report schemas and staged artifacts.
- Likely files: models/schemas/routes/services for contract plumbing, docs.
- Migrations: likely yes (version/compat metadata).
- API impact: additive V2 payloads.
- Frontend impact: read-path adaptation for new contracts.
- Worker impact: none/minimal initial.
- Model/AI impact: none.
- Tests: schema+serialization+compatibility tests.
- Risk: Medium.
- Rollback: keep legacy payloads and feature flag V2 fields.
- Acceptance: contract fields/version rules available and backward compatibility validated.

### 10J.2 — Player-Centered Session Flow Upgrade
- Objective: move Coach Pro Plus creation flow to validated player-select/create + discipline/focus inputs.
- Why: remove manual ID entry and anchor sessions to player development lifecycle.
- Dependencies: 10J.1.
- Reuse: existing player profiles, coach-player assignment, VideoSession.
- Likely files: coach routes, player routes/services, CoachProPlusVideoSessionsView/store/service.
- Migrations: likely light (session linkage metadata).
- API impact: create/list enhancements.
- Frontend impact: session wizard UX.
- Worker impact: none.
- Model/AI impact: none.
- Tests: API RBAC + frontend creation flow.
- Risk: Medium.
- Rollback: keep legacy `player_ids` path temporarily.
- Acceptance: coach can select player without manual IDs; governance access intact.

### 10J.3 — Repetition Segmentation Backbone
- Objective: add deterministic repetition/action segmentation entities and extraction path.
- Why: V2 metrics require repetition granularity.
- Dependencies: 10J.1, 10J.2.
- Reuse: chunking, timestamps, pose/ball data streams.
- Likely files: worker/services/models/routes/tests.
- Migrations: yes (repetition storage).
- API impact: repetition retrieval endpoints.
- Frontend impact: repetition list/timeline display.
- Worker impact: moderate.
- Model/AI impact: none required.
- Tests: segmentation correctness + fallback behavior.
- Risk: High.
- Rollback: disable repetition pipeline and preserve session-level outputs.
- Acceptance: segmented repetitions produced with confidence/validity states.

### 10J.4 — Phase Recognition Backbone
- Objective: add per-repetition phase detection contract and baseline heuristics.
- Why: discipline metrics depend on phase windows.
- Dependencies: 10J.3.
- Reuse: pose and time-series infrastructure.
- Likely files: services/worker/models/routes/tests.
- Migrations: yes (phase storage).
- API impact: phase-level payloads.
- Frontend impact: phase visualization + manual correction hooks.
- Worker impact: moderate.
- Model/AI impact: none initially.
- Tests: phase detection + unsupported camera/FPS cases.
- Risk: High.
- Rollback: phase optional, keep repetition-only metrics.
- Acceptance: phase objects generated with confidence/validity and camera constraints.

### 10J.5 — Batting V2 Deterministic Metric Pack
- Objective: deliver batting-specific reliable metrics over repetition/phase structure.
- Why: highest user-facing impact.
- Dependencies: 10J.3, 10J.4.
- Reuse: existing metric engine and findings/report pipes.
- Likely files: pose_metrics/findings/report/worker/frontend results views/tests.
- Migrations: maybe (metric catalogs/versioning).
- API impact: additive batting V2 fields.
- Frontend impact: batting technical scorecards.
- Worker impact: medium.
- Model/AI impact: optional later object tracking.
- Tests: deterministic metric/unit + regression.
- Risk: High.
- Rollback: keep old batting metrics and gate V2 via config.
- Acceptance: vetted batting metric set with validity states and evidence references.

### 10J.6 — Pace + Spin Bowling V2 Deterministic Metric Packs
- Objective: ship production-safe pace and spin bowling metric packs with additive ball-tracking-aware evidence hardening.
- Why: existing bowling capability is strongest and must be formalized without silently reusing pace assumptions for spin.
- Dependencies: 10J.3, 10J.4, 10J.5 foundations.
- Reuse: ball_tracking_service + current bowling findings + batting V2 contract patterns.
- Likely files: bowling metric pack/findings/worker/report/frontend/tests.
- Migrations: none preferred; keep additive JSON payloads.
- API impact: additive pace/spin metric fields.
- Frontend impact: bowling metric panels in the existing V2 results view.
- Worker impact: medium, CPU-first pose math with optional confidence uplift from existing ball tracking.
- Model/AI impact: deterministic first.
- Tests: pace/spin metric validity, compatibility, and ball-evidence safety.
- Risk: High.
- Rollback: fallback to existing bowling summary and omit bowling V2 metric pack.
- Acceptance: pace and spin metric packs expose stable confidence/validity behavior with explicit limitations.

### 10J.7 — Wicketkeeping V2 Deterministic Metric Pack
- Objective: deliver production-safe wicketkeeping-specific deterministic metrics over repetition/phase windows.
- Why: wicketkeeping support was previously generic and needed specialist, validity-aware coverage.
- Dependencies: 10J.1–10J.6.
- Reuse: existing V2 metric contract, repetition segmentation, phase recognition, and findings/report plumbing.
- Likely files: wicketkeeping metric pack service, analysis orchestration, tests, and existing V2 results views.
- Migrations: none preferred (additive JSON payload extension).
- API impact: additive `wicketkeeping_*` metric results and `meta.wicketkeeping_v2_metric_pack`.
- Frontend impact: existing V2 metric extraction accepts wicketkeeping prefixes.
- Worker impact: low-cost CPU pose math.
- Model/AI impact: deterministic first; no new LLM measurement behavior.
- Tests: wicketkeeping metric validity, context gating, and regression coverage.
- Risk: High.
- Rollback: disable wicketkeeping V2 pack while retaining legacy outputs.
- Acceptance: wicketkeeping V2 metrics are deterministic, evidence-aware, and compatibility-safe.

### 10J.8 — Fielding V2 Foundations
- Objective: deliver specialist baseline metrics and action classes for fielding.
- Why: current support is limited and required by final 10J target.
- Dependencies: 10J.3, 10J.4.
- Reuse: existing context modes, pose pipeline.
- Likely files: services/worker/routes/frontend/tests.
- Migrations: possible action-type catalogs.
- API impact: new specialist outputs.
- Frontend impact: specialist review views.
- Worker impact: medium-heavy.
- Model/AI impact: some metrics gated pending object evidence.
- Tests: specialist action/metric validity tests.
- Risk: High.
- Rollback: retain context-only baseline outputs.
- Acceptance: usable specialist baseline without unsupported claims.

### 10J.9 — Confidence, Validity & Metric Sanity Hardening
- Objective: harden V2 confidence, validity, sanity bounds, capture suitability, unsupported-state handling, and comparability safeguards.
- Why: metric outputs must refuse unsupported or misleading calculations before later progress/reporting phases build on them.
- Dependencies: 10J.5–10J.8.
- Reuse: V2 contracts, metric packs, findings/report structures, comparison/frontend presentation.
- Likely files: contracts/metric packs/findings/report/comparison/frontend/tests.
- Migrations: no/low.
- API impact: additive validity/confidence/comparability metadata.
- Frontend impact: minimal limitation/proxy visibility.
- Worker impact: low-medium.
- Model/AI impact: none.
- Tests: validity/confidence/comparability regression and unsupported-state safety tests.
- Risk: Medium.
- Rollback: keep legacy outputs readable while disabling additive hardening paths.
- Acceptance: invalid or unsupported metrics fail safely, stay out of negative findings, and compare only when technically defensible.

### 10J.10 — Strength + Consistency Engine
- Objective: add deterministic within-session strength, recurring-concern, repeatability, and representative-repetition analysis on top of V2 metric evidence.
- Why: coaches need transparent reproducibility signals without introducing opaque overall scores or longitudinal trend claims.
- Dependencies: 10J.1-10J.9 metric, validity, repetition, and phase foundations.
- Reuse: existing V2 metric packs, findings/report payloads, session-comparison comparability rules, and Coach Pro Plus UI patterns.
- Likely files: V2 metric packs, analysis aggregation services, findings/report payload extenders, frontend results rendering, tests.
- Migrations: no; additive JSON payload extension is sufficient for existing results storage.
- API impact: additive findings/report/result fields only.
- Frontend impact: minimal additive session-analysis sections in existing results surfaces.
- Worker impact: low.
- Model/AI impact: none.
- Tests: metric-pack regression, validity/confidence safety, session-analysis, and representative-repetition selection.
- Risk: High.
- Rollback: disable additive strength/consistency payloads while preserving legacy findings/report behavior.
- Acceptance: valid comparable repetition evidence deterministically yields strengths, recurring concerns, consistency observations, and transparent best/needs-work repetition selection.

### 10J.11 — Player Longitudinal Progress Engine
- Objective: compare technically comparable player evidence across sessions and expose deterministic baseline/latest/best/trend/stability outputs without introducing an opaque overall development score.
- Why: coaches need transparent progress evidence built on the 10J.9 comparability safeguards and 10J.10 within-session consistency outputs before any future goals/interventions layer.
- Dependencies: 10J.9, 10J.10.
- Reuse: V2 metric contracts, compatibility metadata, strength/consistency payloads, player-centered session ownership, and existing Coach Pro Plus comparison surfaces.
- Likely files: session comparison/history services, coach pro plus routes, player-facing progress service/frontend components/tests.
- Migrations: none preferred; derive longitudinal outputs from additive JSON results when possible.
- API impact: additive player longitudinal progress data only.
- Frontend impact: minimal player → discipline/skill → metric progress views.
- Worker impact: low; no pose/video recomputation.
- Model/AI impact: none; deterministic evidence only.
- Tests: comparability, baseline/latest/best, trend, across-session stability, RBAC, and regression coverage.
- Risk: High.
- Rollback: disable additive longitudinal progress views while preserving legacy comparison/report/PDF behavior.
- Acceptance: only technically comparable valid observations influence player longitudinal claims, and non-comparable history remains visible with limitations.

### 10J.12 — Hardening, Performance, CI, and Rollout Controls
- Objective: finalize perf budgets, safety checks, CI coverage, and production rollout gates.
- Why: reduces risk before broad enablement.
- Dependencies: all prior implementation phases.
- Reuse: current CI/docs-only governance and existing validation suites.
- Likely files: tests, CI workflows, config docs.
- Migrations: none expected.
- API impact: none/minor telemetry.
- Frontend impact: minor UX hardening.
- Worker impact: profiling/tuning.
- Model/AI impact: none.
- Tests: full regression matrix and failure-injection cases.
- Risk: Medium.
- Rollback: feature-flag rollback by phase.
- Acceptance: CI green with declared commands, rollback playbook validated.

## 35. Recommended GitHub Issue Breakdown

Recommended issue count: 12 (one per implementation sub-phase above).

For each issue template:
- Title: `PHASE 10J.X — <sub-phase title>`
- Objective/dependencies: from Section 34
- Strict scope: only files/functions in sub-phase
- Out-of-scope: all later phases and runtime redesigns
- Likely files/protected files: include section references 27/28
- Tests and CI commands: Section 38 baseline + sub-phase specific suites
- Acceptance criteria: exact bullets from Section 34

No issue auto-creation in 10J.0; user approval required.

## 36. Acceptance Criteria for Every Proposed Sub-Phase

Each sub-phase is accepted only if:
- backward compatibility preserved or explicitly gated;
- RBAC/governance tests pass;
- validity/compatibility constraints enforced;
- required tests for that phase pass;
- no unsupported metric claims are emitted.

Sub-phase-specific acceptance criteria are defined in Section 34.

## 37. Rollback Principles

- Keep legacy endpoints/payload compatibility until replacement is validated.
- Add V2 fields additively first; avoid destructive schema changes early.
- Use feature flags/controlled activation per discipline and UI layer.
- Preserve coach approval workflow as non-negotiable safety gate.
- Roll back by phase boundary, not by ad-hoc partial patches.

## 38. CI Validation Commands

Per implementation phase, at minimum reuse existing commands:
- `cd backend && pytest tests/ -q`
- `cd frontend && npm run test:unit`
- `cd frontend && npm run build`
- checklist/governance validation commands as applicable

For Phase 10J.0 docs/checklist validation:
- `python scripts/checklist.py status`

## 39. Explicit Duplication Check Against Completed Work

Do not duplicate:
- governed recommendation approvals/review and player-facing suppression from 9G/9H
- existing player development contract and evidence mapping infrastructure
- existing upload/worker staged architecture

10J extends these systems with player-centered V2 metric/repetition/progress capabilities.

## 40. Final Spec-Lock Statement

Phase 10J.0 spec lock is complete for audit scope. The final dependency-ordered implementation sequence is defined in Section 34, all implementation sub-phases remain **PENDING USER APPROVAL**, and no runtime implementation is authorized by this document.

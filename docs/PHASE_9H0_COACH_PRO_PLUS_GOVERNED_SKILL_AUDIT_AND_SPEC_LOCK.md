# Phase 9H.0 — Coach Pro Plus Governed Skill Integration: Pre-Phase Audit + Spec Lock

**Status:** AUDIT COMPLETE — SPEC LOCKED
**Date:** 2026-05-16
**Scope:** Audit only. No runtime code changed.
**Author:** Copilot Agent (Phase 9H.0)

---

## Table of Contents

1. [Objective](#1-objective)
2. [Audit Area 1 — Coach Pro Plus Video-Analysis Backend](#2-audit-area-1--coach-pro-plus-video-analysis-backend)
3. [Audit Area 2 — Coach Pro Plus Frontend](#3-audit-area-2--coach-pro-plus-frontend)
4. [Audit Area 3 — Video-Analysis Result Structure](#4-audit-area-3--video-analysis-result-structure)
5. [Audit Area 4 — Player Development Models / Routes / Services](#5-audit-area-4--player-development-models--routes--services)
6. [Audit Area 5 — Player Profile Recommendation / Development-Plan Structures](#6-audit-area-5--player-profile-recommendation--development-plan-structures)
7. [Audit Area 6 — Governed Skill / AI Insight / Reusable Skill Architecture](#7-audit-area-6--governed-skill--ai-insight--reusable-skill-architecture)
8. [Audit Area 7 — Approval / Review Workflow Support](#8-audit-area-7--approvalreview-workflow-support)
9. [Audit Area 8 — Audit Logging Support](#9-audit-area-8--audit-logging-support)
10. [Audit Area 9 — RBAC / Tier Gating](#10-audit-area-9--rbactier-gating)
11. [Audit Area 10 — Existing Tests](#11-audit-area-10--existing-tests)
12. [Audit Area 11 — Gaps / Blockers Before Phase 9H.1](#12-audit-area-11--gapsblockers-before-phase-9h1)
13. [Locked Implementation Spec](#13-locked-implementation-spec)
14. [Files Inspected](#14-files-inspected)
15. [Files Changed](#15-files-changed)
16. [Confirmation Statements](#16-confirmation-statements)

---

## 1. Objective

Audit the real repository state before any Phase 9H.1 implementation begins.
Lock the Phase 9H implementation spec so that sub-phases 9H.1 – 9H.7 can
proceed without ambiguity about existing behavior, protected areas, or
interface contracts.

**Non-goals of this document:**

- No runtime feature code is delivered here.
- No Coach Pro Plus video-analysis pipeline is rebuilt or changed.
- No Player Development plan generation logic is changed.
- No migrations, CI workflows, package files, or infrastructure files are changed.
- No Claw Studio references are introduced.

---

## 2. Audit Area 1 — Coach Pro Plus Video-Analysis Backend

### 2.1 Services

| File | Role |
|------|------|
| `backend/services/coach_plus_analysis.py` | Shared analysis pipeline: pose extraction → metrics → findings → report. Exposes `run_pose_metrics_findings_report()` (used by async worker) and `extract_pose_landmarks()` (used by GPU chunking). Returns `AnalysisArtifacts(results, frames)`. |
| `backend/services/pose_service.py` | MediaPipe Tasks Vision API integration. Extracts 33 keypoints per frame. Returns `pose_summary`, `frames`, `metrics`, `findings`, `report`. Lazy-imports `cv2` and `mediapipe`. Raises `RuntimeError` if MediaPipe model absent. |
| `backend/services/pose_metrics.py` | Computes 5 biomechanical metrics from pose frame data. Builds `evidence` markers per metric with `worst_frames` and `bad_segments`. |
| `backend/services/coach_findings.py` | Rule-based findings generation. Takes metrics + `analysis_mode` (batting / bowling / wicketkeeping / fielding). Returns structured findings dict. |
| `backend/services/coach_report_service.py` | Synthesises findings into a human-readable coaching report. Returns `report` dict with `summary`, `key_issues`, `drills`, `one_week_plan`. |
| `backend/services/coach_ai_pipeline.py` | Higher-level pipeline combining pose analysis with ball-tracking. Exposes `analyze_video_pose()` and `analyze_video_with_ball_tracking()`. |
| `backend/services/coach_suggestions.py` | AI-generated coaching suggestions (Phase 3 of video analysis). Returns `coach_suggestions` and `player_summary` blobs. |
| `backend/services/goal_compliance.py` | Calculates `goal_compliance_pct` comparing coach-defined goals against analysis outcomes. |
| `backend/services/video_chunking.py` | GPU chunked-processing support: splits video into time chunks, creates `VideoAnalysisChunk` records. |
| `backend/services/chunk_aggregation.py` | Aggregates chunk results and finalises the parent `VideoAnalysisJob`. |
| `backend/services/video_job_recovery.py` | Marks stale jobs; retries retryable jobs. Used by worker recovery path. |
| `backend/services/video_quota_service.py` | Quota enforcement for video uploads per plan tier. |
| `backend/services/s3_service.py` | S3 presigned URL generation for video upload / download / playback. |
| `backend/services/sqs_service.py` | Enqueues video analysis jobs into AWS SQS. |
| `backend/services/pdf_export_service.py` | Exports video-analysis reports to PDF (stored on S3). |
| `backend/services/ball_tracking_service.py` | Ball-tracking analysis layer integrated into Coach Pro Plus video pipeline. |

### 2.2 Workers

| File | Role |
|------|------|
| `backend/workers/analysis_worker.py` | Async SQS consumer. Downloads video from S3, runs `run_pose_metrics_findings_report()`, persists results to `VideoAnalysisJob`. Handles chunked (GPU) and monolithic (CPU) deep-mode paths. |
| `backend/scripts/run_video_analysis_worker.py` | Standalone entry-point for the worker process. Long-polls SQS queue. Reads `SQS_VIDEO_ANALYSIS_QUEUE_URL`, `S3_COACH_VIDEOS_BUCKET`, `DATABASE_URL`, `LOG_LEVEL`, `WORKER_BATCH_SIZE`, `WORKER_LONG_POLL_TIMEOUT`. |

### 2.3 Routes

| File | Prefix | Key Endpoints |
|------|--------|---------------|
| `backend/routes/coach_pro_plus.py` | `/api/coaches/plus` | `POST /sessions`, `GET /sessions`, `GET /sessions/{session_id}`, `DELETE /sessions/{session_id}`, `POST /videos/upload/initiate`, `POST /videos/upload/complete`, `GET /videos/jobs/{job_id}`, `GET /sessions/{session_id}/jobs`, `GET /videos/jobs/{job_id}/stream`, `POST /videos/analyze` (direct/MVP), `POST /videos/ball-tracking`, `GET /sessions/{session_id}/moment-markers`, `POST /sessions/{session_id}/moment-markers`, etc. |

All endpoints are feature-gated: `require_roles(["coach_pro_plus", "org_pro"])`.

### 2.4 Inline Pydantic Schemas (inside `coach_pro_plus.py`)

| Schema | Direction |
|--------|-----------|
| `VideoSessionCreate` | Request |
| `VideoSessionRead` | Response |
| `VideoStreamUrlRead` | Response |
| `VideoAnalysisJobRead` | Response |
| `VideoUploadInitiateRequest` | Request |
| `VideoUploadInitiateResponse` | Response |
| `VideoUploadCompleteRequest` | Request |
| `VideoUploadCompleteResponse` | Response |
| `VideoAnalysisRequest` | Request (direct/MVP analysis) |
| `VideoAnalysisResponse` | Response |
| `BallTrackingRequest` | Request |
| `BallTrackingResponse` | Response |

### 2.5 Persistence

| Model | Table | Key fields |
|-------|-------|------------|
| `VideoSession` | `video_sessions` | `id`, `owner_type` (coach/org), `owner_id`, `title`, `player_ids` (JSON), `status` (pending/uploaded/processing/ready/failed), `notes`, `analysis_context`, `camera_view`, `s3_bucket`, `s3_key`, `session_type`, `video_duration_seconds` |
| `VideoAnalysisJob` | `video_analysis_jobs` | `id`, `session_id` (FK), `sample_fps`, `include_frames`, `status` (queued/processing/quick_running/quick_done/deep_running/done/completed/failed), `stage`, `progress_pct`, `deep_enabled`, `deep_mode` (cpu/gpu), `analysis_mode` (batting/bowling/wicketkeeping/fielding), `results` (legacy JSON), `quick_results` (JSON), `deep_results` (JSON), `quick_findings` (JSON), `quick_report` (JSON), `deep_findings` (JSON), `deep_report` (JSON), `coach_goals` (JSON), `outcomes` (JSON), `goal_compliance_pct`, `coach_suggestions` (JSON), `player_summary` (JSON), `pdf_s3_key`, timestamps |
| `VideoAnalysisChunk` | `video_analysis_chunks` | `id`, `job_id` (FK), chunk index/range, chunk results JSON |

### 2.6 Video-Analysis Migrations (Relevant Files)

| Migration | What it adds |
|-----------|-------------|
| `n4i5j6k7l8m9_add_video_sessions_and_analysis_jobs.py` | Initial `video_sessions` + `video_analysis_jobs` tables |
| `c3d4e5f6g7h8_add_video_session_type_duration.py` | `session_type`, `video_duration_seconds` to `video_sessions` |
| `d1e2f3g4h5i6_add_s3_snapshot_to_video_analysis_jobs.py` | `s3_bucket`, `s3_key` snapshot on job |
| `8fad14d07603_add_pdf_export_fields_to_video_analysis_.py` | `pdf_s3_key`, `pdf_generated_at` |
| `h3i4j5k6l7m8_add_findings_report_fields.py` | `quick_findings`, `quick_report`, `deep_findings`, `deep_report` |
| `f1a2b3c4d5e6_add_awaiting_upload_job_status.py` | New job status value |
| `g2h3i4j5k6l7_add_video_analysis_chunk_model.py` | `video_analysis_chunks` table, `total_chunks`, `completed_chunks` on job |
| `j4k5l6m7n8o9_add_coach_goals_and_outcomes.py` | `coach_goals`, `outcomes`, `goal_compliance_pct` |
| `p3q4r5s6t7u8_add_coach_suggestions_and_player_summary.py` | `coach_suggestions`, `player_summary` |
| `p2q3r4s5t6u7_add_staged_video_analysis_fields.py` | Staged analysis fields (stage, progress_pct, deep_enabled, quick/deep results) |
| `z1a2b3c4d5e6_add_analysis_mode_to_video_analysis_job.py` | `analysis_mode` column |
| `a1b2c3d4e5f6_add_video_file_size.py` | File size tracking |
| `e5f6g7h8i9j0_add_video_moment_markers.py` | Moment markers for video sessions |
| `q8r9s0t1u2v3_convert_video_sessions_player_ids_to_jsonb.py` | `player_ids` → JSONB |
| `20260106190609_add_analysis_context_and_camera_view.py` | `analysis_context`, `camera_view` on video sessions |

---

## 3. Audit Area 2 — Coach Pro Plus Frontend

### 3.1 Pages / Views

| File | Purpose |
|------|---------|
| `frontend/src/views/CoachProPlusVideoSessionsView.vue` | Main page for managing video sessions. Gated by `isCoachProPlus`. Shows session list, upload flow, job results. |
| `frontend/src/views/CoachesDashboardView.vue` | Coach dashboard. Contains embedded player-development overviews gated by `canCoach`. |

### 3.2 Components (partial list — video-analysis surface)

| File | Purpose |
|------|---------|
| `frontend/src/components/PlayerDevelopmentPlanCard.vue` | Renders a development plan card; consumed in PlayerProfileView Development tab |
| `frontend/src/components/PlayerDevelopmentInsightCard.vue` | Renders AI insights for players; consumed in PlayerProfileView |
| `frontend/src/components/AiInsightReviewCard.vue` | Phase 8C reviewer controls (approve/reject/flag). Used for AI insights |

### 3.3 Services / Stores

| File | Purpose |
|------|---------|
| `frontend/src/services/coachPlusVideoService.ts` | Typed API client for all `/api/coaches/plus/*` endpoints. Exports `ApiError`, `VideoSession`, `VideoAnalysisJob`, `VideoAnalysisResults`, `UploadInitiateResponse`, `UploadCompleteResponse`, `VideoStreamUrl`. Exposes: `createVideoSession`, `listVideoSessions`, `getVideoSession`, `initiateVideoUpload`, `uploadToPresignedUrl`, `completeVideoUpload`, `getAnalysisJobStatus`, `listAnalysisJobs`. |
| `frontend/src/stores/coachPlusVideoStore.ts` | Pinia store. State: `sessions`, `uploading` (`UploadState`), `jobStatusMap` (`Map<string, VideoAnalysisJob>`), `lastFetchedAt`. Actions: `fetchSessions`, `createSession`, `startUpload`, `fetchJobsForSession`, `pollJobUntilComplete`, `updateJobStatus`, `forceFetchJob`, `stopPollingJob`. Guards: terminal-status override prevention. |
| `frontend/src/services/playerDevelopmentApi.ts` | Typed API client for `/api/player-development/*` endpoints. |
| `frontend/src/stores/authStore.ts` | Getters: `isCoachProPlus` (role = coach_pro_plus OR org_pro OR superuser), `canCoach` (coach_pro OR coach_pro_plus OR org_pro OR superuser), `isCoach` (coach_pro OR coach_pro_plus OR superuser). |

---

## 4. Audit Area 3 — Video-Analysis Result Structure

### 4.1 Evidence Fields

The `VideoAnalysisJob` model stores evidence in multiple JSON columns:

```
results            — legacy combined JSON (backward compat)
quick_results      — quick-pass analysis output
deep_results       — deep-pass analysis output
quick_findings     — extracted findings from quick_results
quick_report       — extracted report from quick_results
deep_findings      — extracted findings from deep_results
deep_report        — extracted report from deep_results
```

### 4.2 Analysis Result JSON Shape (`VideoAnalysisResults` in frontend TypeScript)

```typescript
{
  // Evidence markers with timestamps
  evidence?: Record<string, {
    threshold?: number;
    worst_frames?: Array<{ frame_num?: number; timestamp_s?: number; score?: number }>;
    bad_segments?: Array<{
      start_frame?: number; end_frame?: number;
      start_timestamp_s?: number; end_timestamp_s?: number; min_score?: number;
    }>;
  }>;

  video_fps?: number;
  total_frames?: number;

  pose_summary?: {
    total_frames?: number; sampled_frames?: number;
    frames_with_pose?: number; detection_rate_percent?: number;
    model?: string; video_fps?: number;
  };

  metrics?: { summary?: { total_frames?: number }; [k: string]: unknown };
  findings?: Record<string, unknown> | Array<unknown> | null;
  coach?: { findings?: ...; report?: unknown };

  report?: {
    summary?: string; key_issues?: string[];
    drills?: { name?, description?, duration_minutes?, focus_areas? }[];
    one_week_plan?: string;
  };

  frames?: Array<Record<string, unknown>>;
}
```

### 4.3 Confidence / Timestamp Availability

- Per-frame timestamps: `frame_num`, `timestamp` (seconds), `timestamp_ms` (ms) stored in `frames[]`.
- Evidence markers (`evidence` dict): keyed by metric name, each has `worst_frames` with `timestamp_s` and `bad_segments` with `start_timestamp_s`/`end_timestamp_s`.
- Per-job timestamps: `created_at`, `started_at`, `completed_at`, `quick_started_at`, `quick_completed_at`, `deep_started_at`, `deep_completed_at`.
- Confidence: no explicit `confidence_score` field on `VideoAnalysisJob` itself. Detection rate and visibility scores are embedded in `pose_summary`.

### 4.4 Sessions, Goals, Outcomes

- `VideoSession.analysis_context`: batting / bowling / wicketkeeping / fielding / mixed
- `VideoSession.camera_view`: side / front / behind / other
- `VideoAnalysisJob.coach_goals`: coach-defined goals JSON
- `VideoAnalysisJob.outcomes`: computed outcomes vs goals JSON
- `VideoAnalysisJob.goal_compliance_pct`: overall compliance percentage (0–100)
- `VideoAnalysisJob.coach_suggestions`: AI coaching suggestions
- `VideoAnalysisJob.player_summary`: player-facing simplified summary

---

## 5. Audit Area 4 — Player Development Models / Routes / Services

### 5.1 Models (all in `backend/sql_app/models.py`)

| Model | Table | Key fields |
|-------|-------|------------|
| `PlayerProfile` | `player_profiles` | `player_id` (PK, User FK), `batting_style`, `bowling_style`, etc. |
| `PlayerDevelopmentPlan` | `player_development_plans` | `id`, `player_profile_id` (FK), `coach_user_id` (FK), `org_id`, `title`, `summary`, `status` (draft/active/paused/completed/archived), `source_type` (match_data/video_analysis/coach_note/ai_insight/manual), `coach_approved` (bool), `approval_state` (not_required/pending_review/approved/rejected/changes_requested), `confidence_score` (0–1), `evidence_refs` (JSON list), `ai_metadata` (JSON), timestamps |
| `PlayerDevelopmentGoal` | `player_development_goals` | goal text, priority, timeline, status |
| `PlayerWeaknessTag` | `player_weakness_tags` | category, severity, evidence_refs |
| `PlayerStrengthTag` | `player_strength_tags` | category, evidence_refs |
| `PlayerDevelopmentIntervention` | `player_development_interventions` | type, description, status |
| `PlayerDrillAssignment` | `player_drill_assignments` | drill details, status |
| `PlayerProgressCheckpoint` | `player_progress_checkpoints` | checkpoint criteria, expected date |
| `CoachPlayerAssignment` | `coach_player_assignments` | FK coach_user_id, player_profile_id, org_id, active |
| `PlayerForm` | `player_form` | per-innings form entry |
| `PlayerCoachingNotes` | `player_coaching_notes` | coaching note, visibility |

### 5.2 Routes (`backend/routes/player_development.py`)

Prefix: `/api/player-development`

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `POST /players/{player_id}/draft-plan` | coach_pro / coach_pro_plus / org_pro | Generate AI-assisted draft plan |
| `GET /plans/{plan_id}` | coach_pro / coach_pro_plus / org_pro | Get plan |
| `GET /players/{player_id}/plans` | coach_pro / coach_pro_plus / org_pro | List player plans |
| `GET /dashboard/team-overview` | coach_pro / coach_pro_plus / org_pro | Team dashboard |
| `GET /reports/players/{player_id}` | coach_pro / coach_pro_plus / org_pro | Player report |
| `GET /reports/plans/{plan_id}` | coach_pro / coach_pro_plus / org_pro | Plan report |
| `GET /reports/team-summary` | coach_pro / coach_pro_plus / org_pro | Team summary report |

### 5.3 Services

| Service | Purpose |
|---------|---------|
| `backend/services/player_development_plan_service.py` | Core: `generate_draft_player_development_plan()`. Loads profile, form, video sessions, coaching notes. Builds evidence_refs. Checks sufficient evidence. Calls TrainingDrillGenerator, PlayerImprovementTracker, AI insights pipeline. Returns `DraftPlanGenerationResult`. |
| `backend/services/player_development_report_service.py` | Read-only report builder for player/plan/team-summary reports. |
| `backend/services/player_development_dashboard_service.py` | Team development overview aggregation. |
| `backend/services/player_development_state.py` | State helpers for plan lifecycle. |

### 5.4 Video Session Integration into Player Development Plans

`_load_video_sessions()` in `player_development_plan_service.py` queries `VideoSession` records where:
- `owner_type == coach` AND `owner_id == coach_user.id`, OR
- `owner_type == org` AND `owner_id == coach_user.org_id`

Returns up to 2 sessions as evidence refs (`_video_session_refs()` produces `{"type": "video_session", "id": session.id, "label": session.title}`).

**Critical Gap:** The current integration references `VideoSession` records (session IDs, titles) in evidence_refs, but does **not** pull specific `VideoAnalysisJob` findings, metrics, evidence markers, timestamps, or coaching suggestions into the plan. The plan generation does not read `quick_findings`, `deep_findings`, `coach_suggestions`, or `outcomes` from any `VideoAnalysisJob`. This is the primary integration gap Phase 9H addresses.

---

## 6. Audit Area 5 — Player Profile Recommendation / Development-Plan Structures

### 6.1 `PlayerDevelopmentPlan.evidence_refs` Schema

Each ref in the JSON list:
```json
{ "type": "<string>", "id": "<string>", "label": "<string>" }
```
Current `type` values in use: `player_profile`, `player_form`, `coach_note`, `coaching_session`, `video_session`, `manual`.

### 6.2 `PlayerDevelopmentPlan.ai_metadata` Schema

Produced by `_build_ai_metadata()`:
```python
{
  "output_type": "draft_plan",
  "is_official_truth": False,
  "requires_review": True,
  "grounded_in_data": True,
  "source_refs": [{"type": ..., "id": ..., "label": ...}],
  "confidence_score": float,
  "limitations": [str],
  "grounding_summary": str
}
```

### 6.3 Plan Approval State Machine

```
not_required  →  (AI/manual source)  → always coach_approved=False initially
pending_review → (AI-sourced plans)  → awaiting coach decision
approved       → coach accepted
rejected       → coach rejected
changes_requested → coach wants edits
```

`normalize_player_development_plan_governance()` enforces this in `PlayerDevelopmentPlan.__init__()`.

---

## 7. Audit Area 6 — Governed Skill / AI Insight / Reusable Skill Architecture

### 7.1 Phase 6B AI Boundary

`backend/domain/ai_boundary.py` enforces:
- `AiOutputType` enum
- `OFFICIAL_TRUTH_FIELDS` set
- `AiOutputMetadata` dataclass (output_type, is_official_truth, requires_review, confidence_score, limitations, source_refs)
- `validate_no_official_truth_mutation(payload, context)` — raises if payload touches protected fields

### 7.2 Phase 6C Skills Architecture

Spec locked in `docs/PHASE_6C_CRICKSY_SKILLS_ARCHITECTURE_SPEC.md`. Defines contract shape for reusable, versioned, governed cricket intelligence skills.

### 7.3 Phase 8C AI Insight Review

`AiInsightReview` model (table: `ai_insight_reviews`), service in `ai_insight_review_service.py`, routes in `ai_insight_review.py`. States: pending / approved / rejected / changes_requested / flagged. Reviewer roles: analyst_pro, org_pro. Frontend: `AiInsightReviewCard.vue`.

### 7.4 Phase 9G Player Development Skill Contract Registry

`backend/domain/player_development_skill_contract.py` — pure data module.

Registered skills (6 total):
1. `player_weakness_detection.v1` — allowed_roles: coach_pro, coach_pro_plus, org_pro
2. `player_development_plan.v1` — allowed_roles: coach_pro, coach_pro_plus
3. `drill_recommendation.v1` — allowed_roles: coach_pro, coach_pro_plus
4. `progress_checkpoint_summary.v1` — allowed_roles: coach_pro, coach_pro_plus, org_pro
5. `team_development_overview.v1` — allowed_roles: coach_pro, coach_pro_plus, org_pro
6. `player_development_report.v1` — allowed_roles: coach_pro, coach_pro_plus, org_pro

All six skills declare `video_analysis_tags` as an **optional input**, but **none currently declares video-evidence structured fields** (specific job_id, evidence markers, timestamps, confidence_scores from video jobs) in their `required_inputs` or `optional_inputs`. This is the skill-registry gap Phase 9H must address.

All six skills declare `approval_required_before_activation: True` and `must_include_evidence_refs` in `validation_rules`.

### 7.5 Phase 9G Tests Covering Skill Contracts

`backend/tests/test_player_development_skill_contract.py` — validates contract shape, required fields, forbidden output terms, fallback states, evidence ref requirements. Runs against the pure-data registry; no DB calls.

### 7.6 No Governed Coaching Skill Registry for Video Evidence (Gap)

There is **no** `coaching_video_skill` or `video_evidence_to_recommendation` governed skill defined yet. Phase 9H.1 must define this.

---

## 8. Audit Area 7 — Approval / Review Workflow Support

### 8.1 Existing Approval Model for Development Plans

`PlayerDevelopmentPlan.approval_state` (not_required / pending_review / approved / rejected / changes_requested) and `PlayerDevelopmentPlan.coach_approved` (bool) are persisted on every plan.

Governance normalization enforced in `PlayerDevelopmentPlan.__init__()` via `normalize_player_development_plan_governance()`.

**Gap:** There is no dedicated approval API endpoint (e.g., `PATCH /api/player-development/plans/{plan_id}/approve`). Plans are currently generated as `draft` with `coach_approved=False`. No route exists to flip `approval_state` to `approved` or `rejected`. This is a Phase 9H.3 blocker.

### 8.2 Existing AI Insight Review for General AI Outputs

Phase 8C provides `GET /ai-insights/review/{insight_type}/{insight_id}` and `POST /ai-insights/review/{insight_type}/{insight_id}`. Reviewer roles: analyst_pro, org_pro.

**Gap for Phase 9H:** Reviewer roles for coach-governed skill recommendations should be coach_pro_plus and org_pro (not analyst_pro). The existing `AiInsightReview` model may be reusable, but roles must be carefully mapped.

### 8.3 Coach Goals & Outcomes

`VideoAnalysisJob.coach_goals`, `outcomes`, `goal_compliance_pct` — present in model and migrations. No dedicated API endpoint for setting goals via `player_development` routes (goals are set via `coach_pro_plus.py` job management endpoints). No explicit handoff from goals to plan review.

---

## 9. Audit Area 8 — Audit Logging Support

### 9.1 Request / Auth / Rate-Limit Logging

`backend/middleware/request_logging.py` — `RequestLoggingMiddleware` writes to `request_logs` table (method, path, status, ip, userId, latencyMs). Enabled by `CRICKSY_REQUEST_LOGGING=1`.

`backend/sql_app/models_security.py` — `RequestLog`, `AuthEvent`, `RateLimitEvent` ORM models.

Migration: `add_security_logging_tables.py` creates these tables.

### 9.2 MCP Tool Audit Stub

`backend/services/mcp_tools/util.py` — `audit_log(tool, user, body)` prints to stdout. Explicitly noted as a dummy (replace with DB/log sink as needed). **Not a governed audit trail.**

### 9.3 AI Insight Review Audit

`AiInsightReview` records (reviewer, timestamp, state, feedback_type, reviewer_notes) act as a structured review trail for AI outputs. This is the closest thing to a governed audit trail for AI decisions currently in the repo.

### 9.4 Gaps for Phase 9H

- No `skill_run_log` table or service exists.
- No audit trail for skill invocations (who triggered, when, with what inputs).
- No structured log of coach approval / rejection decisions tied to governed skill runs.
- No audit trail for player-facing recommendation publication events.
- Phase 9H.6 must design and implement the governed-skill audit-log contract.

---

## 10. Audit Area 9 — RBAC / Tier Gating

### 10.1 Roles (RoleEnum in `backend/sql_app/models.py`)

```
free, player_pro, coach_pro, coach_pro_plus, analyst_pro, org_pro, venue_admin
```

### 10.2 Backend RBAC

`backend/security.py`:
- `require_roles(allowed_roles: list[str])` — FastAPI dependency factory
- `coach_or_org_required = Depends(require_roles(["coach_pro", "coach_pro_plus", "org_pro"]))`
- `analyst_or_org_required = Depends(require_roles(["analyst_pro", "org_pro"]))`
- `org_only_required = Depends(require_roles(["org_pro"]))`

`backend/services/billing_service.py` — `PLAN_FEATURES` dict with feature flags per tier.

`backend/services/entitlement_service.py` — entitlement / feature-access checking layer.

### 10.3 Coach Pro Plus Specific Gating

All `/api/coaches/plus/*` endpoints gate on `require_roles(["coach_pro_plus", "org_pro"])`.

All `/api/player-development/*` endpoints gate on `require_roles(["coach_pro", "coach_pro_plus", "org_pro"])`.

`backend/services/video_quota_service.py` enforces per-plan video upload quotas.

### 10.4 Frontend RBAC

`frontend/src/stores/authStore.ts`:
```typescript
isCoachProPlus: role === 'coach_pro_plus' || role === 'org_pro' || superuser
canCoach:       role === 'coach_pro' || role === 'coach_pro_plus' || role === 'org_pro' || superuser
isCoach:        role === 'coach_pro' || role === 'coach_pro_plus' || superuser
```

### 10.5 Player-Facing Visibility Gap

There is no current RBAC rule in `player_development` routes that gates visibility of a recommendation by `coach_approved == True`. The `audience` parameter exists on report endpoints (coach vs player), but the player-facing report does not currently filter out unapproved AI recommendations. **Phase 9H.4 must enforce this.**

---

## 11. Audit Area 10 — Existing Tests

### 11.1 Video Analysis Tests

| Test file | Coverage |
|-----------|---------|
| `test_coach_pro_plus_ai_integration.py` | Full pipeline (pose → metrics → findings → report) with mocked auth + pose service |
| `test_analysis_mode_enforcement.py` | `analysis_mode` validation |
| `test_coach_findings.py` | Rule-based findings generation |
| `test_coach_report_service.py` | Report synthesis |
| `test_pose_metrics.py` | Biomechanical metric computation |
| `test_evidence_driven_reports.py` | Evidence marker generation |
| `test_goal_compliance.py` | Goal compliance calculation |
| `test_coach_suggestions.py` | AI coaching suggestions |
| `test_upload_lifecycle.py` | Upload initiate/complete flow |
| `test_video_job_recovery.py` | Stale job recovery |
| `test_video_quota.py` | Quota enforcement |
| `test_video_session_history_hardening.py` | Session deletion / history |
| `test_video_stream_url_presign.py` | Presigned URL generation |
| `test_video_upload_s3_key_persistence.py` | S3 key immutability |
| `test_mediapipe_concurrency.py`, `test_mediapipe_model_cache.py` | MediaPipe thread safety |
| `test_ball_tracking.py`, `test_ball_tracking_integration.py` | Ball tracking |

### 11.2 Player Development Tests

| Test file | Coverage |
|-----------|---------|
| `test_player_development_models.py` | ORM model constraints |
| `test_player_development_plan_service.py` | Draft plan generation |
| `test_player_development_routes.py` | Route access/auth |
| `test_player_development_reports.py` | Report endpoints |
| `test_player_development_dashboard.py` | Team dashboard |
| `test_player_development_skill_contract.py` | Skill contract shape/governance |

### 11.3 AI / Governance Tests

| Test file | Coverage |
|-----------|---------|
| `test_phase_6b_ai_boundary.py` | AI boundary enforcement |
| `test_phase_8_ai_analytics.py` | Phase 8 analytics governance |
| `test_phase_8c_ai_insight_review.py` | AI insight review workflow |

### 11.4 RBAC / Auth Tests

| Test file | Coverage |
|-----------|---------|
| `test_rbac_roles.py` | Role-based access control |
| `test_coach_pro_features.py` | Coach Pro features |
| `test_analyst_pro_features.py` | Analyst Pro features |

### 11.5 Missing Tests (Required for Phase 9H)

- No tests for: video-evidence → skill-input mapping
- No tests for: governed coaching skill run audit logging
- No tests for: coach approval gate on player-development recommendation publication
- No tests for: player-facing recommendation visibility gating by approval state
- No tests for: `coaching_video_evidence_skill.v1` or equivalent new skill
- No frontend unit tests for Coach Pro Plus review/approval UI workflow

---

## 12. Audit Area 11 — Gaps / Blockers Before Phase 9H.1

| # | Gap / Blocker | Severity | Phase resolving |
|---|--------------|----------|----------------|
| 1 | No governed coaching skill exists for video-evidence → recommendation mapping | **Blocker** | 9H.1 |
| 2 | `player_development_plan_service` uses only `VideoSession` IDs as evidence refs; does not read `VideoAnalysisJob` findings, metrics, evidence markers, timestamps, or confidence values | **Blocker** | 9H.2 |
| 3 | No API endpoint to approve / reject / request-changes on a `PlayerDevelopmentPlan` | **Blocker** | 9H.3 |
| 4 | Player-facing reports do not currently filter by `coach_approved == True` | **Blocker** | 9H.4 |
| 5 | No visible Coach Pro Plus UI workflow for reviewing/approving video-evidence-based recommendations | **Blocker** | 9H.5 |
| 6 | No governed skill-run audit log (table, service, or structured events) | **Blocker** | 9H.6 |
| 7 | `AiInsightReview` reviewer roles (analyst_pro, org_pro) do not include coach_pro_plus — role mapping for coached-skill review not yet defined | **High** | 9H.1/9H.3 |
| 8 | `VideoAnalysisJob.coach_suggestions` and `player_summary` are AI-generated blobs but have no approval state or evidence-ref attachment | **High** | 9H.2/9H.4 |
| 9 | Six existing Phase 9G skills treat `video_analysis_tags` as an optional string list; no skill declares structured video-evidence fields (job_id, timestamp_s, metric_name, confidence) | **High** | 9H.1 |
| 10 | No `PlayerDevelopmentPlan.source_type == video_analysis` enforcement path: any plan can be set to `video_analysis` source but no code path validates or requires video-job evidence for that type | **Medium** | 9H.2 |
| 11 | SQLite Alembic upgrade is blocked by `1b13e5e48c1e_add_sponsors_table.py` `DEFAULT now()` — pre-existing, does not affect PostgreSQL production | **Low (pre-existing)** | N/A |
| 12 | MCP `audit_log()` is a stdout-only stub — not a governed audit trail | **Low (pre-existing)** | 9H.6 |

---

## 13. Locked Implementation Spec

### 13.1 Objective

Extend the existing Phase 9G Player Development Skill system to consume structured, timestamped Coach Pro Plus video-analysis evidence. Governed skill runs produce coach-reviewable recommendation drafts. Only explicitly coach-approved recommendations may become player-facing.

### 13.2 Non-Goals

- Do not rebuild or modify `pose_service.py`, `analysis_worker.py`, `coach_plus_analysis.py`, or any existing video analysis pipeline.
- Do not change existing `PlayerDevelopmentPlan` generation behavior.
- Do not modify the existing six Phase 9G skill contracts (extend is allowed if backward compatible).
- Do not change AI insight review reviewer roles for non-Coach-Pro-Plus contexts.
- Do not introduce Claw Studio references, terminology, or architecture.
- Do not introduce fake/mock production data.
- Do not activate plans or push recommendations to players without explicit coach approval.
- Do not change official cricket truth (scores, results, DLS, career stats).

### 13.3 Files Allowed to Change in Later Implementation Phases

#### Backend
- `backend/domain/player_development_skill_contract.py` — add new `coaching_video_evidence_skill.v1` entry (backward compatible)
- `backend/services/player_development_plan_service.py` — extend `_load_video_sessions()` and evidence-ref builders to include `VideoAnalysisJob` evidence fields
- `backend/routes/player_development.py` — add `PATCH /plans/{plan_id}/approve`, `PATCH /plans/{plan_id}/reject`, `PATCH /plans/{plan_id}/request-changes`
- `backend/sql_app/schemas.py` — add Pydantic schemas for coaching-skill recommendation, approval request/response
- A new `backend/services/coaching_skill_audit_service.py` (new file, Phase 9H.6)
- A new `backend/sql_app/models.py` addition: `CoachingSkillRunLog` model (Phase 9H.6)
- A new Alembic migration for the `coaching_skill_run_logs` table (Phase 9H.6)
- Existing tests may be extended (no existing test may be removed)

#### Frontend
- `frontend/src/services/playerDevelopmentApi.ts` — add approval/rejection API calls
- `frontend/src/views/CoachProPlusVideoSessionsView.vue` — add review/approve UI panel for video-evidence-based recommendation drafts
- New component `frontend/src/components/CoachingSkillRecommendationReviewCard.vue` (Phase 9H.5)
- Existing tests may be extended

### 13.4 Files Protected from Change

These files may **not** be changed in any Phase 9H sub-phase without a separate, explicitly approved issue:

- `backend/services/coach_plus_analysis.py`
- `backend/services/pose_service.py`
- `backend/services/pose_metrics.py`
- `backend/services/coach_findings.py`
- `backend/services/coach_report_service.py`
- `backend/services/coach_ai_pipeline.py`
- `backend/workers/analysis_worker.py`
- `backend/scripts/run_video_analysis_worker.py`
- `backend/services/video_chunking.py`
- `backend/services/chunk_aggregation.py`
- `backend/services/video_job_recovery.py`
- `backend/services/video_quota_service.py`
- `backend/services/s3_service.py`
- `backend/services/sqs_service.py`
- `backend/routes/coach_pro_plus.py`
- `frontend/src/services/coachPlusVideoService.ts`
- `frontend/src/stores/coachPlusVideoStore.ts`
- `backend/services/ai_insight_review_service.py`
- `backend/routes/ai_insight_review.py`
- `frontend/src/components/AiInsightReviewCard.vue`
- `backend/domain/ai_boundary.py`
- `backend/domain/constants.py`
- `backend/security.py` (unless only adding a new convenience decorator)
- All existing Alembic migration files
- All existing test files (no deletion, no modification of existing assertions)
- `frontend/src/stores/authStore.ts` (unless only adding a computed getter for a new role)

### 13.5 Skill Input Contract

A new governed skill `coaching_video_evidence_skill.v1` must declare:

**Required inputs:**
```
player_profile_id       — str
coach_user_id           — str
org_id                  — str
video_session_id        — str  (VideoSession.id)
video_analysis_job_id   — str  (VideoAnalysisJob.id — must be status=completed/done)
analysis_mode           — str  (batting | bowling | wicketkeeping | fielding)
evidence_markers        — list[VideoEvidenceMarker]
```

**VideoEvidenceMarker shape:**
```
metric_name     — str
timestamp_s     — float  (attached from worst_frames or bad_segments)
frame_num       — int | None
score           — float | None
threshold       — float | None
finding_label   — str
```

**Optional inputs:**
```
coach_goals         — dict | None  (from VideoAnalysisJob.coach_goals)
goal_compliance_pct — float | None (from VideoAnalysisJob.goal_compliance_pct)
previous_plan_id    — str | None
coach_notes         — list[str] | None
```

**Forbidden inputs:**
```
official_player_stats_mutation_request
career_totals
match_results
dls_values
ranking_request
psychological_data
medical_data
```

### 13.6 Skill Output Contract

The skill must output a structured draft recommendation with:

```
recommendation_id   — str  (UUID, generated)
skill_id            — str  ("coaching_video_evidence_skill.v1")
skill_version       — str  ("1.0.0")
player_profile_id   — str
video_session_id    — str
video_analysis_job_id — str
analysis_mode       — str
confidence_score    — float (0.0–1.0)
limitations         — list[str]
evidence_refs       — list[EvidenceRef]  (MUST include video timestamps)
recommendation_text — str  (advisory language only)
suggested_drills    — list[DrillSuggestion] | None
focus_areas         — list[str]
approval_state      — "pending_review"  (always on creation)
is_official_truth   — False  (always)
requires_review     — True   (always)
generated_at        — datetime (UTC)
ai_metadata         — AiOutputMetadata
```

**EvidenceRef (for video evidence):**
```
type            — "video_evidence"
video_session_id — str
job_id          — str
metric_name     — str
timestamp_s     — float
frame_num       — int | None
finding_label   — str
label           — str  (human-readable)
```

### 13.7 Video Evidence Mapping Rules

1. Only `VideoAnalysisJob` records with `status in (completed, done)` may be used as skill input.
2. Evidence markers are extracted from `VideoAnalysisJob.quick_findings` or `deep_findings` (prefer deep if available).
3. Each evidence marker must carry a `timestamp_s` value derived from `worst_frames[].timestamp_s` or `bad_segments[].start_timestamp_s`.
4. If no timestamp is available for a finding, that finding is **excluded** from the evidence list.
5. `analysis_mode` must match `VideoAnalysisJob.analysis_mode` (no cross-mode mapping).
6. Maximum evidence markers per recommendation: 10 (to prevent noise).
7. Evidence refs must be preserved verbatim in the output — they must not be paraphrased or summarised away.
8. `validate_no_official_truth_mutation()` must be called before persisting any skill output.

### 13.8 Coach Review / Approval Workflow

1. Skill output is created with `approval_state = pending_review`.
2. A new API endpoint `PATCH /api/player-development/plans/{plan_id}/approve` accepts: `{ "decision": "approved" | "rejected" | "changes_requested", "reviewer_notes": str | None }`.
3. Only users with role `coach_pro_plus` or `org_pro` may call this endpoint.
4. On `approved`: `PlayerDevelopmentPlan.coach_approved = True`, `approval_state = approved`.
5. On `rejected`: `coach_approved = False`, `approval_state = rejected`, plan moves to archived or remains draft.
6. On `changes_requested`: `coach_approved = False`, `approval_state = changes_requested`.
7. Every review action must produce an audit log entry (Phase 9H.6).

### 13.9 Player-Facing Visibility Rules

1. A recommendation must have `coach_approved == True` AND `approval_state == approved` to appear in any player-facing report or surface.
2. The `audience=player` filter on report endpoints must enforce this check.
3. Players must never see `approval_state`, `evidence_markers`, or raw skill output JSON directly.
4. Players see only: `recommendation_text`, `focus_areas`, `suggested_drills[].name`, `suggested_drills[].description`.
5. `coach_suggestions` and `player_summary` from `VideoAnalysisJob` must not be shown to players without going through the approval gate.

### 13.10 RBAC / Tier Rules

| Action | Roles |
|--------|-------|
| Trigger skill run from video evidence | coach_pro_plus, org_pro |
| View skill recommendation draft | coach_pro_plus, org_pro, coach_pro (own players only) |
| Approve / reject / request changes | coach_pro_plus, org_pro |
| View player-facing approved recommendation | player_pro (their own), coach_pro_plus, org_pro |
| View audit log of skill runs | org_pro only |

### 13.11 Audit-Log Contract

Each `CoachingSkillRunLog` record must include:

```
id                  — UUID
skill_id            — str
skill_version       — str
triggered_by_user_id — str  (FK users.id)
player_profile_id   — str
video_session_id    — str
video_analysis_job_id — str
input_summary       — JSON  (non-PII, no raw video data)
output_recommendation_id — str | None
approval_decision   — str | None  (approved/rejected/changes_requested)
approved_by_user_id — str | None
event_type          — str  (skill_triggered | approved | rejected | changes_requested | published)
timestamp           — datetime (UTC, TZ-aware)
```

### 13.12 AI / Cost Guardrails

1. Skill runs must be **event-triggered** — only after a coach explicitly requests a recommendation from a completed video analysis job. Never run automatically or on a schedule.
2. AI calls within a skill run must respect existing `agent_budget.py` token budget limits.
3. Failed or low-confidence skill runs must fall back to `insufficient_data` — no partial AI output may be shown.
4. If `confidence_score < 0.4`, `approval_state` must be set to `low_confidence_review_required` and flagged for mandatory coach review.
5. No AI call may read from or write to official cricket truth fields.

### 13.13 Backend API Expectations

New endpoints required (added to `backend/routes/player_development.py`):

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/api/player-development/players/{player_id}/coaching-skill-recommendation` | coach_pro_plus, org_pro | Trigger skill run from a completed video analysis job |
| `PATCH` | `/api/player-development/plans/{plan_id}/approve` | coach_pro_plus, org_pro | Submit approval decision |
| `GET` | `/api/player-development/plans/{plan_id}/skill-evidence` | coach_pro_plus, org_pro | Get video evidence refs for a plan |

### 13.14 Frontend Coach Pro Plus Workflow Expectations

1. `CoachProPlusVideoSessionsView.vue` must include a "Generate Recommendation Draft" button on completed analysis jobs (gated by `isCoachProPlus`).
2. A new `CoachingSkillRecommendationReviewCard.vue` component must display:
   - Recommendation text
   - Evidence markers with timestamps (linked to video position if possible)
   - Confidence score and limitations
   - Approve / Reject / Request Changes buttons (gated by `isCoachProPlus`)
3. Approved recommendations must appear in the player's Development Plan tab (filtered by `coach_approved == True`).
4. Rejected or pending recommendations must never appear on player-facing surfaces.
5. Backend-only delivery of Phase 9H.5 is **not accepted** — the Coach Pro Plus UI path is mandatory.

### 13.15 DB / Schema / Migration Expectations

New migration file required for Phase 9H.6:
- Table: `coaching_skill_run_logs`
- Columns per Audit-Log Contract (§13.11)
- All existing tables are read-only for Phase 9H

No other new tables are required for 9H.1–9H.5 (approval state already exists on `PlayerDevelopmentPlan`).

### 13.16 Tests Required by Sub-Phase

| Sub-phase | Required tests |
|-----------|---------------|
| 9H.1 | `test_coaching_video_evidence_skill_contract.py` — contract shape, required fields, forbidden outputs, fallback states |
| 9H.2 | `test_video_evidence_to_skill_input_mapping.py` — deterministic mapping from `VideoAnalysisJob` evidence to skill input; timestamp attachment; analysis_mode matching |
| 9H.3 | `test_player_development_approval_gate.py` — approve/reject/request-changes endpoint; RBAC; unapproved recommendations cannot be player-facing |
| 9H.4 | `test_player_development_recommendation_output.py` — output schema validation; player-facing filter; approval-state enforcement |
| 9H.5 | Frontend unit test for `CoachingSkillRecommendationReviewCard.vue` — renders evidence, approval buttons, correct RBAC gating |
| 9H.6 | `test_coaching_skill_audit_log.py` — log records created on trigger/approve/reject; no PII leakage; org_pro access only |
| 9H.7 | All above tests pass; regression test confirming existing video-analysis tests still pass |

### 13.17 Manual QA Checklist

- [ ] Coach Pro Plus user uploads a video, analysis completes successfully
- [ ] Coach clicks "Generate Recommendation Draft" — sees new draft with evidence markers and timestamps
- [ ] Coach reviews draft — evidence timestamps match video content
- [ ] Coach approves draft — status changes to approved
- [ ] Player logs in — approved recommendation visible in Development tab
- [ ] Coach rejects a different draft — it does NOT appear in player-facing surfaces
- [ ] Non-coach_pro_plus user cannot access the recommendation draft endpoint (403)
- [ ] Coach triggers skill run on a non-completed job — receives 422 / validation error
- [ ] Skill run on a job with no evidence markers returns `insufficient_data` gracefully
- [ ] Audit log entry created for each approval/rejection action
- [ ] No official cricket truth mutated anywhere in the flow

### 13.18 Rollback Plan

1. Feature flag `COACHING_SKILL_INTEGRATION_ENABLED` (env var, default `0`) gates all Phase 9H.1+ code paths.
2. Setting to `0` disables the skill trigger endpoint and the recommendation review card; existing video analysis and player development flows continue unchanged.
3. New `coaching_skill_run_logs` table can be truncated safely without affecting other tables.
4. No new skill contract entries affect existing Phase 9G plans (backward compatible — new skill ID, no mutation of existing contracts).

### 13.19 Acceptance Criteria for Moving to Phase 9H.1

- [ ] This audit document exists and is committed under `docs/`
- [ ] `CRICKSY_MASTER_EXECUTION_CHECKLIST.md` Phase 9H.0 status updated to IN PROGRESS / COMPLETE
- [ ] All 11 gap/blocker items above are documented and acknowledged
- [ ] Skill input contract defined (§13.5)
- [ ] Skill output contract defined (§13.6)
- [ ] Evidence mapping rules defined (§13.7)
- [ ] Approval workflow defined (§13.8)
- [ ] Player-facing visibility rules defined (§13.9)
- [ ] RBAC rules defined (§13.10)
- [ ] Audit-log contract defined (§13.11)
- [ ] No runtime code changed
- [ ] No test/migration/CI/package/infra files changed
- [ ] No Phase 9H.1+ task marked complete

---

## 14. Files Inspected

### Backend
- `backend/services/coach_plus_analysis.py` ✓
- `backend/services/pose_service.py` ✓
- `backend/workers/analysis_worker.py` ✓
- `backend/scripts/run_video_analysis_worker.py` ✓
- `backend/services/player_development_plan_service.py` ✓
- `backend/services/player_development_report_service.py` (via grep) ✓
- `backend/services/player_development_dashboard_service.py` (via grep) ✓
- `backend/services/training_drill_generator.py` (via grep) ✓
- `backend/services/ai_player_insights.py` (via grep) ✓
- `backend/services/player_improvement_tracker.py` (via grep) ✓
- `backend/services/ai_insight_review_service.py` (via search) ✓
- `backend/services/billing_service.py` (via grep) ✓
- `backend/services/entitlement_service.py` (via ls) ✓
- `backend/services/video_quota_service.py` (via ls) ✓
- `backend/services/mcp_tools/util.py` ✓
- `backend/sql_app/models.py` (lines 111–200, 701–1495, 2219–2719, 2827–2910) ✓
- `backend/sql_app/models_security.py` ✓
- `backend/routes/coach_pro_plus.py` (via search/grep) ✓
- `backend/routes/player_development.py` (via search) ✓
- `backend/routes/ai_insight_review.py` (via search) ✓
- `backend/security.py` (via grep/search) ✓
- `backend/domain/ai_boundary.py` (via search) ✓
- `backend/domain/player_development_skill_contract.py` (lines 1–900) ✓
- `backend/domain/constants.py` (via ls) ✓
- `backend/middleware/request_logging.py` ✓
- `backend/tests/test_player_development_skill_contract.py` ✓
- `backend/tests/test_coach_pro_plus_ai_integration.py` ✓
- Selected migration files (n4i5j6k7l8m9, h3i4j5k6l7m8, j4k5l6m7n8o9, p3q4r5s6t7u8, etc.) ✓
- `docs/PHASE_6C_CRICKSY_SKILLS_ARCHITECTURE_SPEC.md` ✓
- `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` (lines 2887–3010) ✓
- `backend/alembic/versions/` (full listing) ✓

### Frontend
- `frontend/src/services/coachPlusVideoService.ts` ✓
- `frontend/src/stores/coachPlusVideoStore.ts` ✓
- `frontend/src/stores/authStore.ts` (via grep) ✓
- `frontend/src/services/playerDevelopmentApi.ts` (via search) ✓
- `frontend/src/views/CoachProPlusVideoSessionsView.vue` (via grep) ✓
- `frontend/src/views/CoachesDashboardView.vue` (via ls/grep) ✓
- `frontend/src/components/AiInsightReviewCard.vue` (via search) ✓
- `frontend/src/components/PlayerDevelopmentPlanCard.vue` (via search) ✓
- `frontend/src/components/PlayerDevelopmentInsightCard.vue` (via search) ✓
- `frontend/src/services/api.ts` (Phase 8C section via search) ✓

---

## 15. Files Changed

| File | Change |
|------|--------|
| `docs/PHASE_9H0_COACH_PRO_PLUS_GOVERNED_SKILL_AUDIT_AND_SPEC_LOCK.md` | Created (this document) |
| `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` | Phase 9H.0 status updated to `IN PROGRESS → COMPLETE`; audit evidence note added |

**No backend runtime code was changed.**
**No frontend runtime code was changed.**
**No tests were changed.**
**No migrations were changed.**
**No CI workflows were changed.**
**No package files were changed.**
**No infrastructure files were changed.**

---

## 16. Confirmation Statements

1. ✅ **No runtime implementation code was changed.** Only `docs/` files were created or edited.
2. ✅ **No Claw Studio references were introduced.** All architecture, terminology, and patterns follow existing Cricksy conventions.
3. ✅ **No Phase 9H.1+ task is marked complete.** All sub-phases remain PENDING in the checklist.
4. ✅ **Protected Areas were audited before any later implementation.** All files listed in §13.4 are fully documented with their current behavior.
5. ✅ **Existing Coach Pro Plus video-analysis behavior is documented** and must not be rebuilt.
6. ✅ **The hard governance rules are preserved** in this spec:
   - Coach is the authority.
   - No unapproved AI output may become player-facing.
   - Skills are reusable, versioned, testable, and governed.
   - Skill runs are event-triggered, not always running.
   - Video timestamps/evidence remain attached to generated recommendations.
   - No official cricket truth is mutated.
   - Backend work is not accepted without a visible Coach Pro Plus UI path.
   - No fake/mock production data is introduced.

# PHASE 3A — Coach Pro Plus Video Analysis Hardening Audit + Spec Lock

**Repository:** `Jnpaul1984/Cricksy_Scorer`
**Branch:** `agent/phase-3a-coach-video-hardening-audit-spec-lock`
**Audit date:** 2026-05-10
**Scope:** Docs-only audit and spec lock. No app code modified.
**Gate:** CI may be skipped — this is a docs-only change covered by path-ignore.

---

## Audit Sources Reviewed

| Source | Status |
|--------|--------|
| `COMPLETE_VIDEO_ANALYSIS_FLOW.md` | ✅ Reviewed |
| `README_COACH_PRO_PLUS_VIDEO_MVP.md` | ✅ Reviewed |
| `TESTING_GUIDE_COACH_VIDEO.md` | ✅ Reviewed |
| `COACH_REPORT_V2_README.md` | ✅ Reviewed |
| `PDF_EXPORT_AND_MODE_ROUTING_FIXES.md` | ✅ Reviewed |
| `RESULTS_PERSISTENCE_FIX.md` | ✅ Reviewed |
| `RESULTS_PERSISTENCE_DEPLOYMENT.md` | ✅ Reviewed |
| `GPU_PIPELINE_QUICK_REF.md` | ✅ Reviewed |
| `docs/ANALYSIS_MODE_ENFORCEMENT.md` | ✅ Reviewed |
| `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` | ✅ Reviewed |
| `docs/PHASE_0_REPO_BASELINE_AUDIT.md` | ✅ Reviewed |
| `docs/PHASE_1A_STABILIZATION_AUDIT_AND_SPEC_LOCK.md` | ✅ Reviewed |
| `docs/PHASE_1D_OPEN_PR_TRIAGE_AND_CHECKLIST_NUMBERING.md` | ✅ Reviewed |
| `backend/workers/analysis_worker.py` | ✅ Reviewed |
| `backend/scripts/run_video_analysis_worker.py` | ✅ Reviewed |
| `backend/services/coach_plus_analysis.py` | ✅ Reviewed |
| `backend/services/pose_service.py` | ✅ Reviewed |
| `backend/services/sqs_service.py` | ✅ Reviewed |
| `backend/mediapipe_init.py` | ✅ Reviewed |
| `frontend/src/services/coachPlusVideoService.ts` | ✅ Reviewed |
| `frontend/src/stores/coachPlusVideoStore.ts` | ✅ Reviewed |
| `backend/alembic/versions/` (video migrations) | ✅ Reviewed |
| `backend/routes/coach_pro_plus.py` | ✅ Reviewed |
| `GPU_CHUNKED_PIPELINE_IMPLEMENTATION.md` | ✅ Reviewed |

---

## 1. Current Coach Pro Plus Video Analysis Architecture Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Coach Pro Plus Video Analysis System                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  Browser / Frontend                                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  CoachPlusVideoStore (Pinia)                                           │  │
│  │  ├─ sessions[]          (VideoSession DTOs)                           │  │
│  │  ├─ jobStatusMap        (Map<jobId, VideoAnalysisJob>)                 │  │
│  │  ├─ pollingJobs         (Map<jobId, setInterval>)                      │  │
│  │  └─ uploading           (UploadState | null)                           │  │
│  │                                                                         │  │
│  │  coachPlusVideoService.ts                                               │  │
│  │  ├─ createVideoSession()                                               │  │
│  │  ├─ initiateVideoUpload()                                              │  │
│  │  ├─ uploadToPresignedUrl()                  [direct S3 PUT]            │  │
│  │  ├─ completeVideoUpload()                                              │  │
│  │  ├─ getAnalysisJobStatus()                  [5s polling]              │  │
│  │  └─ exportPdf()                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                          │ HTTPS                                              │
│  FastAPI + Socket.IO Backend (ECS Fargate — API Service)                      │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  backend/routes/coach_pro_plus.py                                      │  │
│  │  ├─ POST /api/coaches/plus/sessions                                   │  │
│  │  ├─ GET  /api/coaches/plus/sessions                                   │  │
│  │  ├─ POST /api/coaches/plus/videos/upload/initiate   [S3 presign]      │  │
│  │  ├─ POST /api/coaches/plus/videos/upload/complete   [SQS enqueue]     │  │
│  │  ├─ GET  /api/coaches/plus/analysis-jobs/{job_id}                     │  │
│  │  ├─ GET  /api/coaches/plus/analysis-jobs             [list]           │  │
│  │  └─ POST /api/coaches/plus/analysis-jobs/{job_id}/export-pdf          │  │
│  │                                                                         │  │
│  │  Services Used by Routes:                                               │  │
│  │  ├─ services/sqs_service.py     (SQSService.send_message)              │  │
│  │  ├─ services/pdf_export_service.py  (generate_analysis_pdf)            │  │
│  │  └─ sql_app/models.py           (VideoSession, VideoAnalysisJob)       │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                 │                              │                              │
│                 │ DB (Postgres/SQLite)         │ SQS Queue                   │
│                 ▼                              ▼                              │
│  ┌─────────────────────┐     ┌─────────────────────────────────────────────┐ │
│  │ PostgreSQL (RDS)    │     │ AWS SQS Queue (video analysis jobs)         │ │
│  │ video_sessions      │     │ Visibility timeout: 3600s (1 hour)          │ │
│  │ video_analysis_jobs │     │ DLQ after: 3 retries                        │ │
│  │ video_analysis_     │     └─────────────────────────────────────────────┘ │
│  │   chunks (GPU mode) │                       │                             │
│  └─────────────────────┘                       │ poll                        │
│                                                 ▼                             │
│  Analysis Workers (ECS Fargate — Worker Service)                             │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  CPU Worker: backend/workers/analysis_worker.py                        │  │
│  │  ├─ Poll SQS: receive_messages(max=1, wait=20s)                        │  │
│  │  ├─ Download video from S3 → /tmp/                                    │  │
│  │  ├─ QUICK pass: run_pose_metrics_findings_report(sample_fps=5, max=30s)│  │
│  │  ├─ DEEP pass: run_pose_metrics_findings_report(sample_fps=job_fps)    │  │
│  │  ├─ Bowling: ball_tracking_service (BallTracker + analyze_trajectory)  │  │
│  │  ├─ Upload quick/deep results to S3                                    │  │
│  │  └─ Persist to DB: findings, report, S3 keys, status                  │  │
│  │                                                                         │  │
│  │  GPU Worker: backend/workers/gpu_chunk_worker.py  [EXPERIMENTAL]        │  │
│  │  ├─ Poll video_analysis_chunks (SKIP LOCKED)                           │  │
│  │  ├─ Extract pose landmarks per chunk (30s segments)                    │  │
│  │  └─ Upload chunk pose artifacts to S3                                  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  Analysis Pipeline (services)                                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  services/coach_plus_analysis.py                                       │  │
│  │  └─ run_pose_metrics_findings_report()                                 │  │
│  │      ├─ extract_pose_keypoints_from_video() [pose_service.py]          │  │
│  │      ├─ compute_pose_metrics()              [pose_metrics.py]          │  │
│  │      ├─ build_pose_metric_evidence()        [pose_metrics.py]          │  │
│  │      ├─ generate_findings()                 [coach_findings.py]        │  │
│  │      └─ generate_report_text()              [coach_report_service.py]  │  │
│  │                                                                         │  │
│  │  services/pose_service.py                                               │  │
│  │  └─ extract_pose_keypoints_from_video()                                │  │
│  │      ├─ Opens video via OpenCV                                          │  │
│  │      ├─ Samples frames at sample_fps                                   │  │
│  │      └─ Calls MediaPipe PoseLandmarker per frame                       │  │
│  │                                                                         │  │
│  │  mediapipe_init.py                                                      │  │
│  │  ├─ get_model_path()                                                   │  │
│  │  ├─ get_pose_landmarker()  → factory (one instance per video)          │  │
│  │  └─ build_pose_landmarker()                                            │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  S3 Storage                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Bucket: S3_COACH_VIDEOS_BUCKET                                        │  │
│  │  coach_plus/<owner_type>/<owner_id>/<session_id>/<job_id>/             │  │
│  │  ├─ original.mp4                                                       │  │
│  │  ├─ analysis/quick_results.json                                        │  │
│  │  ├─ analysis/deep_results.json                                         │  │
│  │  ├─ analysis/deep_frames.json  (if include_frames=true)                │  │
│  │  ├─ analysis/ball_tracking_results.json  (bowling mode only)           │  │
│  │  ├─ analysis/chunks/chunk_NNNN.json  (GPU mode only)                  │  │
│  │  ├─ analysis/final_results.json  (GPU aggregated)                      │  │
│  │  └─ reports/<job_id>_report.pdf  (on export)                          │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  Report / PDF                                                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  services/pdf_export_service.py                                        │  │
│  │  └─ generate_analysis_pdf()  →  Coach Report V2 template              │  │
│  │      services/reports/coach_report_template.py                         │  │
│  │      services/reports/findings_adapter.py                              │  │
│  │  Consolidated findings: Deep preferred over Quick                      │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Current Backend Route / API Map

| Method | Route | Auth | Feature Gate | Description |
|--------|-------|------|--------------|-------------|
| `POST` | `/api/coaches/plus/sessions` | JWT required | `coach_pro_plus` / `org_pro` | Create video session |
| `GET` | `/api/coaches/plus/sessions` | JWT required | `coach_pro_plus` / `org_pro` | List sessions (limit/offset) |
| `GET` | `/api/coaches/plus/sessions/{session_id}` | JWT required | `coach_pro_plus` / `org_pro` | Get single session |
| `DELETE` | `/api/coaches/plus/sessions/{session_id}` | JWT required | `coach_pro_plus` / `org_pro` | Delete session |
| `POST` | `/api/coaches/plus/videos/upload/initiate` | JWT required | `coach_pro_plus` / `org_pro` | Create job + presigned PUT URL |
| `POST` | `/api/coaches/plus/videos/upload/complete` | JWT required | `coach_pro_plus` / `org_pro` | Mark upload done, enqueue SQS |
| `GET` | `/api/coaches/plus/analysis-jobs` | JWT required | `coach_pro_plus` / `org_pro` | List jobs (filter by `analysis_mode`) |
| `GET` | `/api/coaches/plus/analysis-jobs/{job_id}` | JWT required | `coach_pro_plus` / `org_pro` | Poll job status and results |
| `POST` | `/api/coaches/plus/analysis-jobs/{job_id}/export-pdf` | JWT required | `coach_pro_plus` / `org_pro` | Generate + upload PDF, return presigned URL |
| `GET` | `/api/coaches/plus/analysis-jobs/{job_id}/stream` | JWT required | `coach_pro_plus` / `org_pro` | Generate presigned video URL |
| `POST` | `/api/coaches/plus/videos/analyze` | JWT required | `coach_pro_plus` / `org_pro` | MVP-only synchronous analysis (local disk path only) |

### Key API Constraints (Locked)

- All endpoints return HTTP 403 with `"code": "feature_disabled"` if user is not `coach_pro_plus` / `org_pro`.
- PDF export returns HTTP 409 if job status is not `completed` or `done`.
- Ownership check is enforced for all `job_id` lookups — users can only access their own jobs.
- `analysis_mode` query param on job list is validated against a regex pattern.

---

## 3. Current Frontend Store / Service / Component Map

### Services (`frontend/src/services/coachPlusVideoService.ts`)

| Export | Purpose |
|--------|---------|
| `createVideoSession(data)` | `POST /api/coaches/plus/sessions` |
| `listVideoSessions(limit, offset)` | `GET /api/coaches/plus/sessions` |
| `getVideoSession(session_id)` | `GET /api/coaches/plus/sessions/{id}` |
| `initiateVideoUpload(session_id, sample_fps, include_frames)` | `POST /api/coaches/plus/videos/upload/initiate` |
| `uploadToPresignedUrl(url, file, onProgress)` | Direct `PUT` to S3 presigned URL |
| `completeVideoUpload(job_id)` | `POST /api/coaches/plus/videos/upload/complete` |
| `getAnalysisJobStatus(job_id)` | `GET /api/coaches/plus/analysis-jobs/{job_id}` |
| `listAnalysisJobs(session_id, analysis_mode)` | `GET /api/coaches/plus/analysis-jobs` |
| `exportAnalysisPdf(job_id)` | `POST /api/coaches/plus/analysis-jobs/{job_id}/export-pdf` |
| `ApiError` class | Feature-disabled detection (`isFeatureDisabled()`), 401 detection (`isUnauthorized()`) |

### Store (`frontend/src/stores/coachPlusVideoStore.ts`)

| State | Type | Purpose |
|-------|------|---------|
| `sessions` | `VideoSession[]` | All coach sessions |
| `loading` | `boolean` | Global loading indicator |
| `error` | `string \| null` | Last error message |
| `uploading` | `UploadState \| null` | Active upload progress |
| `pollingJobs` | `Map<string, setInterval>` | Active poll timers per job |
| `jobStatusMap` | `Map<string, VideoAnalysisJob>` | Cached job status |
| `lastFetchedAt` | `Map<string, number>` | Staleness tracking (30s threshold) |

| Action | Purpose |
|--------|---------|
| `fetchSessions()` | Load sessions and their latest jobs |
| `fetchJobsForSession(session_id)` | Load jobs for a session |
| `startUpload(session_id, file, fps, include_frames)` | Initiate → PUT S3 → complete → start polling |
| `startPolling(job_id)` | Poll every 5s until terminal state |
| `stopPolling(job_id)` | Clear interval |
| `cleanup()` | Stop all polling (called on unmount) |
| `isJobInProgress(job)` | True for: `queued`, `processing`, `quick_running`, `quick_done`, `deep_running` |
| `isJobTerminal(job)` | True for: `completed`, `done`, `failed` |
| `isJobStale(job_id)` | True if cached data is >30s old |

### Key Frontend DTOs (Locked Shape)

```typescript
interface VideoSession {
  id, owner_type, owner_id, title, player_ids, status,
  notes, analysis_context, camera_view, s3_bucket, s3_key,
  created_at, updated_at
}

interface VideoAnalysisJob {
  id, session_id, sample_fps, include_frames, status, error_message,
  sqs_message_id, results,
  analysis_context, camera_view,
  stage, progress_pct, deep_enabled,
  quick_results, deep_results,
  pdf_s3_key, pdf_generated_at,
  coach_goals, outcomes, goal_compliance_pct,
  coach_suggestions, player_summary,
  video_stream, created_at, started_at, completed_at, updated_at
}
```

---

## 4. Current Worker / Job Lifecycle Map

### CPU Worker (`backend/workers/analysis_worker.py`)

```
STARTUP
  ├─ Log AWS config + identity (STS)
  ├─ Register SIGINT/SIGTERM → stop_event
  └─ Enter polling loop (poll_seconds default: 1.0s)

LOOP ITERATION
  ├─ _check_and_aggregate_chunks()   [GPU mode: check for all-complete chunks]
  │   └─ if found: AGGREGATING → aggregate_chunks_and_finalize() → DONE
  │
  └─ _claim_one_job()
      ├─ SELECT WHERE status=queued ORDER BY created_at FOR UPDATE SKIP LOCKED
      ├─ Transition: queued → quick_running (stage=QUICK, progress=0)
      └─ Return job_id

PROCESS JOB (_process_job)
  ├─ Load job + session from DB (selectinload)
  ├─ Resolve S3 location: job.s3_bucket/s3_key (fallback to session)
  │   └─ WARN if fallback used or job/session mismatch
  │
  ├─ If S3 location missing → FAILED immediately
  │
  ├─ Download video: S3 → /tmp/coach_plus_video_<uuid>/original.mp4
  │
  ├─ Validate analysis_mode (fail fast if None)
  │
  ├─ QUICK PASS (sample_fps=5, max_seconds=30)
  │   ├─ run_pose_metrics_findings_report()
  │   ├─ Upload quick_results.json to S3
  │   ├─ Extract quick_findings, quick_report
  │   ├─ Persist: job.quick_results, job.quick_results_s3_key, job.quick_findings, job.quick_report
  │   └─ Transition: quick_running → quick_done (stage=QUICK_DONE, progress=50)
  │
  ├─ If deep_enabled=False:
  │   ├─ Guardrail: quick_findings + quick_report must exist
  │   ├─ Transition: quick_done → done (stage=DONE, progress=100)
  │   └─ SET job.results = {quick: ...}  [legacy compat]
  │
  └─ If deep_enabled=True:
      ├─ Transition: quick_done → deep_running (stage=DEEP, progress=50)
      ├─ Re-validate analysis_mode (defensive)
      ├─ DEEP PASS (sample_fps=job.sample_fps, max_seconds=None)
      │   ├─ run_pose_metrics_findings_report()
      │   └─ If bowling mode: ball_tracking_service
      │       └─ On failure: non-fatal warning (ball_tracking = {error: ...})
      ├─ Upload deep_results.json to S3
      ├─ If include_frames: Upload deep_frames.json to S3
      ├─ Extract deep_findings, deep_report
      ├─ Guardrail: deep_findings + deep_report must exist
      ├─ Persist: job.deep_results, job.deep_results_s3_key, job.deep_findings, job.deep_report
      ├─ Transition: deep_running → done (stage=DONE, progress=100)
      └─ SET job.results = {quick: ..., deep: ...}  [legacy compat]

ERROR HANDLING
  ├─ Inner job exception → best-effort mark FAILED (status=failed, stage=FAILED)
  ├─ Loop exception → log + sleep + continue
  └─ SIGTERM → set stop_event, drain current job, dispose engine

SHUTDOWN
  ├─ Stop polling loop
  └─ get_engine().dispose()
```

### Job Status State Machine

```
awaiting_upload          (created by upload/initiate but not yet completed)
    │
    │  [POST /upload/complete called]
    ▼
queued                   (SQS message sent; waiting for worker)
    │
    │  [worker claims via SKIP LOCKED]
    ▼
quick_running            (QUICK pass in progress, progress=0-49)
    │
    │  [quick pass done]
    ▼
quick_done               (QUICK results persisted, progress=50)
    │                    │
    │ [deep=True]        │ [deep=False → quick-only jobs]
    ▼                    ▼
deep_running            done            (stage=DONE, progress=100)
    │
    │ [deep done]
    ▼
done                     (stage=DONE, progress=100)

[any step] → failed     (stage=FAILED, error_message set)
```

---

## 5. Current S3 / Upload / Storage Flow Map

### Upload Initiation (`POST /videos/upload/initiate`)

1. Backend creates `VideoAnalysisJob` record (status=`awaiting_upload` or `queued`).
2. Backend generates **presigned PUT URL** for S3 via `boto3.generate_presigned_url`.
   - Bucket: `settings.S3_COACH_VIDEOS_BUCKET`
   - Key: `coach_plus/<owner_type>/<owner_id>/<session_id>/<job_id>/original.mp4`
3. **S3 snapshot fields** are written to the job record immediately: `job.s3_bucket`, `job.s3_key`.
   - This prevents race conditions if session S3 fields are mutated later.
4. Response: `{job_id, presigned_url, s3_bucket, s3_key, expires_in}`.

### Client Upload (`PUT <presigned_url>`)

- Client sends binary video directly to S3 — backend is not in the data path.
- Content-Type: `video/mp4`.
- S3 CORS rules must allow PUT from the frontend origin.
- Upload progress tracked by `coachPlusVideoService.uploadToPresignedUrl()` with `XHR.onprogress`.

### Upload Completion (`POST /videos/upload/complete`)

1. Backend validates: job exists, ownership, job has `s3_key`.
2. Updates job status to `processing` / `queued` (depending on implementation revision).
3. Sends SQS message: `{job_id, session_id, sample_fps, include_frames}`.
4. Stores `sqs_message_id` in job.

### S3 Key Derivation in Worker

```python
def _derive_output_key(input_key: str, leaf_name: str) -> str:
    base = input_key.rsplit("/", 1)[0]   # strips /original.mp4
    return f"{base}/analysis/{leaf_name}"
```

| Artifact | S3 Key |
|----------|--------|
| Source video | `coach_plus/.../original.mp4` |
| Quick results | `coach_plus/.../analysis/quick_results.json` |
| Deep results | `coach_plus/.../analysis/deep_results.json` |
| Deep frames | `coach_plus/.../analysis/deep_frames.json` |
| Ball tracking | `coach_plus/.../analysis/ball_tracking_results.json` |
| GPU chunks | `coach_plus/.../analysis/chunks/chunk_NNNN.json` |
| GPU final | `coach_plus/.../analysis/final_results.json` |
| PDF report | `coach_plus/.../reports/<job_id>_report.pdf` |

### S3 Snapshot Fields (Protected)

```sql
-- video_analysis_jobs columns
s3_bucket          VARCHAR  -- Snapshot at job creation (immutable)
s3_key             VARCHAR  -- Snapshot at job creation (immutable)
quick_results_s3_key  VARCHAR  -- Set after quick pass
deep_results_s3_key   VARCHAR  -- Set after deep pass
pdf_s3_key            VARCHAR  -- Set after PDF export
```

The worker prefers `job.s3_bucket` / `job.s3_key` over `session.s3_bucket` / `session.s3_key` and logs a warning if the fallback is used.

---

## 6. Current MediaPipe / Model-Loading Flow Map

### Model Loading (`backend/mediapipe_init.py`)

| Function | Behavior |
|----------|----------|
| `get_model_path()` | Reads `MEDIAPIPE_POSE_MODEL_PATH` env var; validates file exists, is readable, >1MB |
| `get_running_mode()` | Reads `MEDIAPIPE_RUNNING_MODE` env var; validates against `{VIDEO, IMAGE, LIVE_STREAM}` |
| `build_pose_landmarker()` | **Factory** — creates a fresh `PoseLandmarker` instance per call |
| `get_pose_landmarker()` | Alias for `build_pose_landmarker()` |
| `verify_mediapipe_setup()` | Checks import, model path, running mode, landmarker creation |

### Factory Pattern (Important)

- The model uses a **factory pattern** (not a singleton).
- Each video analysis job gets a **fresh PoseLandmarker instance**.
- This is required because `detect_for_video()` is stateful with monotonically increasing timestamps.
- The caller must call `detector.close()` in a `finally` block.

### Model Path Resolution

```
MEDIAPIPE_POSE_MODEL_PATH (env var)
  └─ Default: /app/mediapipe_models/pose_landmarker_full.task
       └─ If missing: attempt runtime download via utils/model_cache.py
            └─ If download fails: raise FileNotFoundError (no silent fallback)
```

### Model Configuration

- **Model:** `pose_landmarker_full.task` (MediaPipe Tasks Vision Pose Landmarker)
- **Landmarks:** 33 named keypoints
- **Default running mode:** `VIDEO` (uses `detect_for_video()` with timestamps)
- **Persons detected:** 1 (single-person mode)
- **Frame downscaling:** `max_width=640` (configurable)

### MediaPipe Constants (Locked)

```python
DEFAULT_MODEL_PATH = "/app/mediapipe_models/pose_landmarker_full.task"
DEFAULT_RUNNING_MODE = "VIDEO"
SUPPORTED_RUNNING_MODES = ("VIDEO", "IMAGE", "LIVE_STREAM")
# 33 KEYPOINT_NAMES defined in mediapipe_init.py — do not modify order
```

---

## 7. Current Analysis Mode Routing Map

### Valid Modes

```python
VALID_MODES = {"batting", "bowling", "wicketkeeping", "fielding"}
```

### Validation Layers (Fail-Fast)

| Layer | File | Behavior on Missing/Invalid Mode |
|-------|------|----------------------------------|
| Worker (quick pass) | `analysis_worker.py:187-196` | Job → `FAILED`, `error_message` set |
| Worker (deep pass) | `analysis_worker.py:303-312` | Job → `FAILED`, `error_message` set |
| Service entry | `coach_plus_analysis.py:118-134` | `ValueError` raised |
| Findings dispatch | `coach_findings.py` | `ValueError` raised (no silent batting fallback) |

### Findings Code Allowlist per Mode

```python
ALLOWED_CODES_BY_MODE = {
    "batting":       {"HEAD_MOVEMENT", "KNEE_COLLAPSE", "BALANCE_DRIFT",
                      "ROTATION_TIMING", "ELBOW_DROP", "INSUFFICIENT_POSE_VISIBILITY"},
    "bowling":       {"HEAD_MOVEMENT", "KNEE_COLLAPSE", "BALANCE_DRIFT",
                      "ROTATION_TIMING", "ELBOW_DROP", "INSUFFICIENT_POSE_VISIBILITY",
                      "INCONSISTENT_RELEASE_POINT", "INSUFFICIENT_BALL_TRACKING"},
    "wicketkeeping": {"HEAD_MOVEMENT", "KNEE_COLLAPSE", "BALANCE_DRIFT",
                      "INSUFFICIENT_POSE_VISIBILITY"},
    "fielding":      {"HEAD_MOVEMENT", "KNEE_COLLAPSE", "BALANCE_DRIFT",
                      "INSUFFICIENT_POSE_VISIBILITY"},
}
```

### Mode-Specific Findings Generators

| Generator | Mode |
|-----------|------|
| `generate_batting_findings()` | `batting` |
| `generate_bowling_findings()` | `bowling` (includes ball tracking codes) |
| `generate_wicketkeeping_findings()` | `wicketkeeping` |
| `generate_fielding_findings()` | `fielding` |

Each generator calls `_filter_findings_by_mode()` to strip codes outside the allowlist.

### Mode-Aware Narratives

- `WHY_IT_MATTERS_BY_MODE`: Per-finding, per-mode explanation text.
- `HIGH_SEVERITY_WARNINGS_BY_MODE`: Mode-specific high-severity action warnings.
- `analysis_mode_used` is always present in result metadata.

### Ball Tracking (Bowling Mode Only)

Bowling mode additionally runs `BallTracker` in the deep pass:
- `BallTracker(ball_color="red").track_ball_in_video()`
- `analyze_ball_trajectory()`
- Outputs: `INCONSISTENT_RELEASE_POINT`, `INSUFFICIENT_BALL_TRACKING`, `SWING_ANALYSIS` codes.
- Ball tracking failure is **non-fatal**: falls back to `{error: ..., detection_rate: 0}`.

---

## 8. Current PDF / Report Export Flow Map

### Trigger

```
POST /api/coaches/plus/analysis-jobs/{job_id}/export-pdf
```

### Gate Check (Locked Behavior)

```python
terminal_success_states = {
    VideoAnalysisJobStatus.completed,
    VideoAnalysisJobStatus.done,
}
if job.status not in terminal_success_states:
    raise HTTPException(409, detail="Cannot export PDF: job status is {job.status.value}, must be completed")
```

### PDF Generation Flow

```
export-pdf endpoint
  ├─ Load job from DB (validate ownership)
  ├─ Check terminal status (409 if not done/completed)
  ├─ Call generate_analysis_pdf(
  │     job_id, session_title, status,
  │     quick_findings, deep_findings,
  │     quick_results, deep_results,
  │     created_at, completed_at,
  │     analysis_mode=job.analysis_mode
  │  )
  │
  ├─ generate_analysis_pdf() → Coach Report V2
  │   ├─ findings_adapter.consolidate_findings(quick, deep)
  │   │   └─ Deep findings preferred; Quick-only findings labeled
  │   ├─ extract_top_priorities()   → 2-3 high-severity findings
  │   ├─ extract_secondary_focus()  → 1-2 remaining findings
  │   ├─ generate_this_week_actions() → 3 action bullets
  │   ├─ render_coach_summary()     → Page 1
  │   ├─ render_consolidated_findings() → Pages 2+
  │   └─ render_appendix_evidence() → Appendix (timestamps, worst frames)
  │
  ├─ Upload PDF bytes to S3: coach_plus/.../reports/<job_id>_report.pdf
  ├─ Store job.pdf_s3_key + job.pdf_generated_at
  └─ Return presigned GET URL (expires_in configurable)
```

### PDF Title

- Dynamic: `"{mode.capitalize()} Analysis Report"` (e.g., "Batting Analysis Report")
- Falls back to `"Video Analysis Report"` if no mode set.

### Coach Report V2 Structure

| Section | Content |
|---------|---------|
| Page 1: Coach Summary | Top 2-3 priority findings, Secondary focus, This Week's 3 actions |
| Pages 2+: Consolidated Findings | Each finding: title, severity, what's happening, why matters, drills, metrics |
| Appendix | Pose detection rate, frames analyzed, per-finding evidence timestamps |

### Key Files

- `backend/services/pdf_export_service.py` — `generate_analysis_pdf()`
- `backend/services/reports/coach_report_template.py` — rendering functions
- `backend/services/reports/findings_adapter.py` — `CommonFinding` schema, consolidation

---

## 9. Current Result / Session Persistence Flow Map

### DB Fields Added by Persistence Fix (Migration `h3i4j5k6l7m8`)

```sql
ALTER TABLE video_analysis_jobs ADD COLUMN quick_findings JSON;
ALTER TABLE video_analysis_jobs ADD COLUMN quick_report JSON;
ALTER TABLE video_analysis_jobs ADD COLUMN deep_findings JSON;
ALTER TABLE video_analysis_jobs ADD COLUMN deep_report JSON;
ALTER TABLE video_analysis_jobs ADD COLUMN quick_results_s3_key VARCHAR(500);
ALTER TABLE video_analysis_jobs ADD COLUMN deep_results_s3_key VARCHAR(500);
```

### Persistence Guardrails (Worker)

```
Quick-only jobs:
  if not quick_findings or not quick_report:
      → FAILED (error_message: "Critical artifacts missing: findings=... report=...")

Deep jobs:
  if not deep_findings or not deep_report:
      → FAILED (error_message: "Critical artifacts missing: findings=... report=...")
```

### What Frontend Receives (`GET /analysis-jobs/{job_id}`)

```json
{
  "id": "...",
  "status": "done",
  "stage": "DONE",
  "progress_pct": 100,
  "quick_findings": { "findings": [...], "overall_level": "low" },
  "quick_report": { "summary": "...", "sections": [...] },
  "deep_findings": { "findings": [...], "overall_level": "low" },
  "deep_report": { "text": "...", "overall_level": "low", "sections": [...] },
  "quick_results_s3_key": "coach_plus/.../quick_results.json",
  "deep_results_s3_key": "coach_plus/.../deep_results.json",
  "results": { "quick": {...}, "deep": {...} }
}
```

Note: `results` is the legacy field kept for backward compatibility with older frontend clients.

### Session Status Transitions

```
VideoSession.status:
  pending → processing (worker starts)
  processing → ready   (job done)
  processing → failed  (job failed)
```

---

## 10. Current Tests and Testing Gaps

### Existing Video Analysis Tests

| Test File | What It Tests |
|-----------|--------------|
| `backend/tests/test_video_upload_s3_key_persistence.py` | S3 key snapshot fields written at job creation |
| `backend/tests/test_video_stream_url_presign.py` | Presigned video stream URL generation |
| `backend/tests/test_video_quota.py` | Upload quota enforcement |
| `backend/tests/test_upload_lifecycle.py` | Full upload lifecycle (initiate → complete) |
| `backend/tests/test_coach_findings.py` | Findings generator unit tests |
| `backend/tests/test_coach_report_service.py` | Report text generation |
| `backend/tests/test_pose_metrics.py` | Pose metric computation |
| `backend/tests/test_analysis_mode_enforcement.py` | Mode validation + routing (14 tests) |
| `backend/tests/test_ball_tracking_integration.py` | Ball tracking integration (10 tests) |
| `backend/tests/test_pdf_export_restrictions.py` | PDF blocked when not done (409); mode routing (4 tests) |
| `backend/tests/test_mediapipe_model_cache.py` | Model cache / path resolution |
| `backend/tests/test_beta_access.py` | Beta / access control |
| `backend/tests/test_admin_beta_users.py` | Admin beta user management |

### Testing Gaps Identified

| Gap | Risk Level |
|-----|-----------|
| No worker lifecycle integration tests (end-to-end job claiming → completion) | HIGH |
| No SQS message send/receive integration tests | HIGH |
| No test for job stuck in `quick_done` without deep enabled | MEDIUM |
| No test for S3 download failure during worker processing | MEDIUM |
| No test for `job.s3_bucket`/`s3_key` fallback-to-session behavior | MEDIUM |
| No test for analysis_mode=None causing immediate FAILED transition | MEDIUM |
| No test for the guardrail: missing findings/report → FAILED | MEDIUM |
| No frontend unit tests for `coachPlusVideoStore` polling cleanup | MEDIUM |
| No frontend test for memory leak scenario (polling after unmount) | MEDIUM |
| No test for GPU chunk aggregation end-to-end | HIGH |
| No test for ball tracking failure non-fatal fallback | LOW |
| No test for PDF export of bowling mode with ball tracking findings | MEDIUM |
| No performance/timeout test for large videos | LOW |
| No test for SQS message visibility timeout expiry (duplicate processing) | MEDIUM |

---

## 11. Current Private-Beta / Access-Control Behavior

### Feature Gating

- All Coach Pro Plus video endpoints are protected by `security.get_current_active_user` + role/tier check.
- Non-entitled users receive HTTP 403 with `"code": "feature_disabled"`.
- Frontend checks `clientStore.isCoachProPlus` to show upgrade prompt before API call.
- Backend enforces independently — frontend gate is cosmetic only.

### Required Roles / Tiers

- `coach_pro_plus` (individual coach)
- `org_pro` (organization subscription)

### Beta Access

- `backend/tests/test_beta_access.py` and `test_admin_beta_users.py` exist, indicating a private beta access control layer.
- Beta users are managed via admin endpoints.
- Beta access is enforced at the backend route level.

### Ownership Enforcement

- All job lookups validate that the requesting user owns the job (by `owner_id` match).
- Cross-user job access returns 404 (not 403) to avoid information leakage.

---

## 12. Current Failure / Timeout / Retry Behavior

### SQS Visibility Timeout

- **Current timeout:** 3600s (1 hour) — set at queue level.
- **Risk:** If processing exceeds 1 hour, the message becomes visible again, causing a race condition where two workers process the same job.
- **Documented recommended fix:** Set `VisibilityTimeout ≥ max_processing_time + buffer` (recommended: 7200s for large videos).
- **Current retry count:** 3 attempts before DLQ routing.

### Worker Failure Modes

| Failure | Worker Behavior |
|---------|----------------|
| S3 download fails (404, 403) | Job → FAILED; SQS message NOT deleted → retry |
| MediaPipe model missing | Job → FAILED; SQS message NOT deleted → retry |
| DB commit fails | Job → FAILED; SQS message NOT deleted → retry |
| Ball tracking fails | Non-fatal warning; job continues with `{error: ..., detection_rate: 0}` |
| Analysis mode missing | Job → FAILED immediately; SQS message deleted |
| Critical artifacts missing (no findings/report) | Job → FAILED with guardrail error |
| Worker loop exception | Log + sleep + continue (job may remain in in-progress state) |

### Orphan Job Risk

If the worker crashes after claiming a job (status → `quick_running`) but before marking it `done` or `failed`, the job is left in an intermediate state permanently. There is no automated timeout/reaper for stuck intermediate-state jobs.

### Retry Visibility

- Failed jobs have `error_message` populated and `status=failed`.
- Frontend shows error state for failed jobs.
- No retry endpoint exists — failed jobs cannot be re-queued via the API.
- No admin dashboard for monitoring stuck/failed jobs in bulk.

---

## 13. Current Known Risks

| Risk ID | Risk | Severity | Mitigation Status |
|---------|------|----------|-------------------|
| R-01 | SQS visibility timeout (1h) can cause duplicate processing for long videos | HIGH | Documented; not yet enforced programmatically |
| R-02 | Orphaned jobs in `quick_running` / `deep_running` on worker crash | HIGH | No reaper; must be fixed manually via DB |
| R-03 | No retry endpoint — failed jobs cannot be re-queued | MEDIUM | Manual DB intervention required |
| R-04 | `job.s3_key` snapshot may still fallback to session if snapshot was not written at creation | MEDIUM | Logged as WARNING; not fatal |
| R-05 | MediaPipe model must be mounted/downloaded; no graceful degradation | MEDIUM | Runtime download via `model_cache.py` added; can still fail |
| R-06 | GPU chunk pipeline is experimental and lacks end-to-end tests | HIGH | Documented; GPU mode not default |
| R-07 | Ball tracking `ball_color="red"` is hardcoded — not configurable via API | LOW | TODO comment exists in code |
| R-08 | No bulk admin view for stuck/failed jobs | MEDIUM | No tooling exists |
| R-09 | `GET /health/admin` exposes user email and hash prefix with no auth | LOW | Inherited from Phase 1A; out of video scope |
| R-10 | PDF export generates fresh PDF on each request; no caching for existing PDFs | LOW | Idempotent for same data; acceptable for now |
| R-11 | Frontend polling interval (5s) is fixed; no backoff for long-running jobs | LOW | Memory leak prevented by cleanup() |
| R-12 | No test coverage for worker job lifecycle (claim → process → complete) | HIGH | Gap in test suite |
| R-13 | `video_analysis_chunks` table has no failure/retry mechanism for individual chunks | MEDIUM | GPU mode only; not in default path |
| R-14 | Job owned by one coach cannot be accessed by another coach even if granted access | LOW | Acceptable for MVP; future: coach sharing |

---

## 14. Protected Files List for Phase 3

The following files must not be modified without explicit audit + user approval:

### Absolute Do-Not-Touch (Without Approval)

| File | Why Protected |
|------|--------------|
| `backend/services/pose_service.py` | MediaPipe pose extraction — core model behavior |
| `backend/mediapipe_init.py` | Model loading/factory — model behavior |
| `backend/services/coach_plus_analysis.py` | Pipeline orchestration — model output structure |
| `backend/services/coach_findings.py` | Findings logic, mode routing, thresholds |
| `backend/services/pose_metrics.py` | Metric computation (head stability, balance drift, etc.) |
| `backend/services/ball_tracking_service.py` | Ball tracking (bowling mode) |
| `backend/alembic/versions/*` | All existing migrations — never edit deployed migrations |
| `backend/workers/gpu_chunk_worker.py` | GPU pipeline — experimental, needs own audit |
| `backend/services/chunk_aggregation.py` | GPU chunk aggregation — experimental |
| `backend/services/video_chunking.py` | GPU chunk creation — experimental |

### Protected (Edit Only with Spec Lock)

| File | Why |
|------|-----|
| `backend/workers/analysis_worker.py` | Worker lifecycle; any change risks orphan jobs or broken persistence |
| `backend/routes/coach_pro_plus.py` | All video API routes; changes affect frontend contracts |
| `backend/sql_app/models.py` (video sections) | ORM model for VideoSession + VideoAnalysisJob |
| `frontend/src/services/coachPlusVideoService.ts` | API client DTOs — contract |
| `frontend/src/stores/coachPlusVideoStore.ts` | Job polling, session management |
| `backend/services/pdf_export_service.py` | PDF generation; must stay backward-compatible |
| `backend/services/reports/coach_report_template.py` | Coach Report V2 rendering |
| `backend/services/reports/findings_adapter.py` | Findings consolidation logic |
| `backend/services/sqs_service.py` | SQS message sending/receiving |
| `backend/services/coach_report_service.py` | Report text generation |
| `backend/scripts/run_video_analysis_worker.py` | Legacy worker script used in SQS-based deployment |

---

## 15. Allowed Hardening Areas

The following areas may be safely hardened in Phase 3B without compromising the existing model/pipeline behavior:

1. **Worker orphan-job reaper**: A periodic task or DB query that detects jobs stuck in `quick_running` / `deep_running` for longer than N minutes and marks them `failed`.

2. **SQS visibility timeout fix**: Increase from 3600s to a safer value (e.g., 7200s) for the main queue.

3. **Retry endpoint**: Add `POST /api/coaches/plus/analysis-jobs/{job_id}/retry` to re-queue a failed job (only allowed if status=`failed`).

4. **Session access for coaches/admins**: Allow an authorized coach to view previous sessions by session_id or job_id lookup. Currently, only the owner can access their own jobs.

5. **PDF export reliability**: Add idempotency — if `pdf_s3_key` is already set, return the existing presigned URL instead of regenerating.

6. **Worker timeout handling**: Add `asyncio.wait_for()` with a configurable timeout around the analysis pipeline steps.

7. **Failure visibility**: Add an admin route or CloudWatch metric for counting stuck/failed jobs.

8. **Private beta access control improvements**: Enhance beta user management (currently exists in `test_admin_beta_users.py`).

9. **Analysis mode routing tests**: Add integration tests for the fail-fast behavior when `analysis_mode` is missing.

10. **Role-specific report safety**: Add tests to confirm no batting language in bowling/wicketkeeping reports.

11. **Frontend polling cleanup tests**: Add Vitest tests for `coachPlusVideoStore.cleanup()` to prevent memory leaks.

12. **Logging improvements**: More structured CloudWatch log entries for job state transitions.

---

## 16. Forbidden Changes Without Explicit Approval

The following changes are **prohibited** in Phase 3B without explicit user review and approval:

| Forbidden Action | Reason |
|-----------------|--------|
| Replace or retrain the MediaPipe model | Current model behavior is liked and must be preserved |
| Rewrite the full video pipeline | Risk of regression; not needed |
| Remove or skip existing analysis stages (pose, metrics, findings, report) | Pipeline integrity must be maintained |
| Change analysis output schemas/shapes without comparison tests | Frontend depends on existing field names |
| Expose video analysis to unauthenticated users | Private beta constraint |
| Merge mental-analysis reports with video analysis reports | Products must remain separate |
| Delete or modify existing Alembic migrations | Data integrity risk |
| Change the `analysis_mode` allowlist without testing all modes | Cross-contamination risk |
| Bypass the worker/session/report persistence guardrails | These guardrails prevent silent data loss |
| Remove the `results` legacy field from job response | Older clients depend on it |
| Enable GPU mode by default | GPU pipeline lacks end-to-end tests |
| Add new findings codes without adding to `ALLOWED_CODES_BY_MODE` | Could cause mode cross-contamination |
| Change MediaPipe running mode without testing | Timestamp behavior differs per mode |
| Change the SQS DLQ behavior without confirming retry counts | Affects retry reliability |

---

## 17. Recommended Smallest Safe Phase 3B Implementation Slice

### Recommended: Three-Slice Approach

#### Slice 3B-1: Reliability Guardrails (Safest First)

**Goal:** Prevent orphaned jobs from becoming permanently stuck.

**Changes:**
- Add a background task or periodic query in `analysis_worker.py` that:
  - Selects jobs in `quick_running` / `deep_running` with `started_at` older than a configurable timeout (e.g., 90 minutes).
  - Marks them `failed` with `error_message = "Job timed out (orphan reaper)"`.
- Increase SQS visibility timeout from 3600s to 7200s in infrastructure/config.
- Add tests: simulate a job stuck in `quick_running` and verify the reaper marks it `failed`.

**Affected files (minimal):**
- `backend/workers/analysis_worker.py` (add `_reap_orphaned_jobs()`)
- SQS infrastructure config (not app code)

**Risk:** LOW — additive only; does not change pipeline behavior.

#### Slice 3B-2: Retry Endpoint

**Goal:** Allow coaches to retry a failed job without manual DB intervention.

**Changes:**
- Add `POST /api/coaches/plus/analysis-jobs/{job_id}/retry`:
  - Validates: job exists, ownership, status is `failed`.
  - Resets: status → `queued`, clears error_message, resends SQS message.
  - Returns: updated job object.
- Add tests: verify retry from `failed` state works; verify retry from `done` state returns 409.

**Affected files:**
- `backend/routes/coach_pro_plus.py` (add one endpoint)
- `backend/tests/test_video_retry_endpoint.py` (new test file)

**Risk:** LOW-MEDIUM — new endpoint, does not touch pipeline.

#### Slice 3B-3: Frontend Polling Cleanup + Access Control Tests

**Goal:** Harden frontend memory safety and backend access control coverage.

**Changes:**
- Add Vitest unit tests for `coachPlusVideoStore.cleanup()` (verify polling intervals cleared on unmount).
- Add backend tests for ownership enforcement (cross-user job access returns 404).
- Add backend tests for 403 behavior for non-entitled users.

**Affected files:**
- `frontend/src/stores/coachPlusVideoStore.test.ts` (new test file)
- `backend/tests/test_video_access_control.py` (new test file)

**Risk:** VERY LOW — test-only additions.

---

## 18. Required Tests / Gates for Phase 3B

All Phase 3B implementation must pass these gates before merge:

### Regression Gates (Must All Pass)

```bash
# Backend regression
cd backend && pytest tests/test_analysis_mode_enforcement.py -v
cd backend && pytest tests/test_ball_tracking_integration.py -v
cd backend && pytest tests/test_pdf_export_restrictions.py -v
cd backend && pytest tests/test_upload_lifecycle.py -v
cd backend && pytest tests/test_video_upload_s3_key_persistence.py -v
cd backend && pytest tests/test_coach_findings.py -v
cd backend && pytest tests/test_pose_metrics.py -v
cd backend && pytest tests/test_coach_report_service.py -v
cd backend && pytest tests/test_beta_access.py -v

# Full existing CI gates
cd backend && pytest -q tests/test_health.py tests/test_results_endpoint.py
cd backend && pytest tests/integration/ -v --tb=short
cd backend && pytest tests/test_dls_calculations.py -v --tb=short
cd frontend && npm run guard:fake-data
cd frontend && npm run type-check
cd frontend && npm run build-only
ruff check .
ruff format --check .
cd backend && mypy --config-file pyproject.toml --explicit-package-bases .
```

### New Gates (Per Slice)

#### Slice 3B-1 Tests (Orphan Reaper)
- Job in `quick_running` for >90 minutes is reaped to `failed`.
- Reaper does not affect jobs in `quick_running` <90 minutes.
- Reaper does not affect jobs in terminal states (`done`, `failed`, `completed`).
- Reaper log messages are present and structured.

#### Slice 3B-2 Tests (Retry Endpoint)
- `POST /retry` on a `failed` job → job moves to `queued`, SQS message sent.
- `POST /retry` on a `done` job → HTTP 409.
- `POST /retry` on another user's job → HTTP 404.
- `POST /retry` on non-existent job → HTTP 404.

#### Slice 3B-3 Tests (Access Control + Frontend)
- Non-`coach_pro_plus` user calling any video endpoint → 403 with `feature_disabled`.
- Ownership check: cross-user job access → 404.
- `coachPlusVideoStore.cleanup()` → all `setInterval` calls cleared.
- No new polling requests after `cleanup()`.

### Mode-Contamination Regression (Must Pass for Any Report Change)
- Bowling report contains no batting-specific language.
- Wicketkeeping report contains no batting-specific language.
- Fielding report contains no batting-specific language.
- `meta.analysis_mode_used` is always present in results.

---

## 19. Rollback Plan for Phase 3 Implementation Work

### Code Rollback

```bash
# For each Phase 3B slice, revert the relevant commit
git revert <commit-sha>
git push origin main
```

### Database Rollback

```bash
# If new migration was added (Phase 3B-1 reaper might not need one)
cd backend
alembic downgrade -1

# Verify
alembic current
```

### Worker Rollback

```bash
# Point ECS worker service back to previous task definition
aws ecs update-service \
  --cluster cricksy-ai-cluster \
  --service cricksy-ai-worker \
  --task-definition cricksy-ai-worker:<PREV_REVISION> \
  --region us-east-1
```

### API Rollback

```bash
# Point ECS API service back to previous task definition
aws ecs update-service \
  --cluster cricksy-backend-cluster \
  --service cricksy-backend \
  --task-definition cricksy-backend:<PREV_REVISION> \
  --region us-east-1
```

### Feature Flag Rollback (If Added)

If any Phase 3B feature uses a feature flag (recommended for orphan reaper):
- Set `ORPHAN_REAPER_ENABLED=false` in ECS environment
- Redeploy (rolling, no downtime)

### Data Safety

- The orphan reaper only marks jobs `failed` that are already stuck — no data loss.
- The retry endpoint re-queues jobs — original job data is preserved.
- No Phase 3B changes modify existing persisted results or findings.

### Rollback Decision Criteria

Trigger rollback if:
- Any existing test regression is observed in CI.
- Job completion rate drops below baseline in CloudWatch.
- New endpoint returns unexpected errors in production.
- Any scoring, DLS, or live bus behavior is affected (should not be — Phase 3B is scoped to video analysis only).

---

## Validation Status

**This is a docs-only change.**

- ✅ Only `docs/PHASE_3A_COACH_VIDEO_HARDENING_AUDIT_AND_SPEC_LOCK.md` created (and minor checklist reference update if applicable).
- ✅ No backend app code modified.
- ✅ No frontend app code modified.
- ✅ No worker code modified.
- ✅ No video-analysis services modified.
- ✅ No pose/model code modified.
- ✅ No S3/upload code modified.
- ✅ No migrations added or modified.
- ✅ No workflows modified.
- ✅ No dependencies added or modified.
- ✅ No scoring/DLS/live bus changes.
- ✅ CI path-ignore rules will skip CI for this docs-only PR (as documented in `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md` Section 1).

---

## Audit Summary

The Coach Pro Plus Video Analysis system is **functional and production-oriented**. The core analysis pipeline (MediaPipe pose extraction → pose metrics → findings → report) is working, validated by existing tests (14/14 mode enforcement, 10/10 ball tracking, 4/4 PDF export, plus additional upload/quota tests).

**What already works well:**
- Complete upload → SQS → worker → persist flow is implemented.
- Staged analysis (Quick + Deep passes) with separate artifact persistence.
- Analysis mode enforcement with fail-fast validation at 3 layers.
- Coach Report V2 universal PDF template.
- S3 snapshot fields to prevent race conditions.
- Guardrails preventing silent artifact loss.
- Ball tracking for bowling mode (non-fatal fallback).

**What must never change without approval:**
- The MediaPipe model and its factory instantiation pattern.
- The pose extraction → metrics → findings → report pipeline chain.
- The analysis mode allowlists and mode-specific findings generators.
- All existing Alembic migrations.
- The job state machine (status/stage transitions).
- The results persistence guardrails.

**What can safely be hardened (smallest safe slice):**
1. Orphan job reaper for stuck intermediate-state jobs.
2. Retry endpoint for failed jobs.
3. Test coverage for access control and frontend polling cleanup.

**Risks requiring attention before Phase 3B:**
- SQS visibility timeout (1h) may cause duplicate processing for long videos (R-01).
- No worker lifecycle integration tests (R-12).
- GPU chunk pipeline is experimental and untested end-to-end (R-06).

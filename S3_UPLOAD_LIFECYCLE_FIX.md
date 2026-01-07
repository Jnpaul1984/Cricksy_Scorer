# S3 Upload Lifecycle Fix - Implementation Summary

## Problem
Intermittent S3 HeadObject 404 errors in `analysis_worker` because workers started downloading videos before client uploads completed. Jobs were immediately set to `queued` status at upload initiation, making them claimable before the S3 object existed.

## Solution
Implement a two-phase job lifecycle:
1. **Initiate**: Create job with `awaiting_upload` status (NOT claimable)
2. **Complete**: Verify S3 object exists, then transition to `queued` (claimable)

## Changes Made

### 1. Database Model ([backend/sql_app/models.py](backend/sql_app/models.py))
**Added new status to `VideoAnalysisJobStatus` enum:**
```python
class VideoAnalysisJobStatus(str, enum.Enum):
    awaiting_upload = "awaiting_upload"  # NEW: Job created, waiting for upload
    queued = "queued"  # Upload confirmed, ready for worker
    # ... existing statuses
```

### 2. Upload Initiate ([backend/routes/coach_pro_plus.py](backend/routes/coach_pro_plus.py#L557))
**Changed default status from `queued` to `awaiting_upload`:**
```python
job = VideoAnalysisJob(
    id=job_id,
    session_id=request.session_id,
    status=VideoAnalysisJobStatus.awaiting_upload,  # Changed from queued
    stage="AWAITING_UPLOAD",  # Changed from QUEUED
    # ... other fields
)
```

### 3. Upload Complete ([backend/routes/coach_pro_plus.py](backend/routes/coach_pro_plus.py#L693))
**Added idempotency checks and S3 verification before queueing:**

#### Idempotency Logic
```python
# Return success if already queued/processing/completed
if job.status in (
    VideoAnalysisJobStatus.queued,
    VideoAnalysisJobStatus.quick_running,
    VideoAnalysisJobStatus.quick_done,
    VideoAnalysisJobStatus.deep_running,
    VideoAnalysisJobStatus.done,
    VideoAnalysisJobStatus.completed,
):
    return success_response("Job already processed - no action taken")
```

#### S3 Preflight Check
```python
try:
    s3.head_object(Bucket=bucket, Key=key)
    logger.info("S3 preflight check PASSED")
except ClientError as e:
    if error_code in ("404", "NoSuchKey"):
        job.status = VideoAnalysisJobStatus.failed
        job.stage = "FAILED"
        raise HTTPException(400, "Upload not found in S3")
```

#### Transition to Queued
```python
# Only after preflight passes:
job.status = VideoAnalysisJobStatus.queued
job.stage = "QUEUED"
job.progress_pct = 0
session.status = VideoSessionStatus.uploaded
```

### 4. Worker ([backend/workers/analysis_worker.py](backend/workers/analysis_worker.py#L267))
**Explicit documentation that only `queued` jobs are claimed:**
```python
async def _claim_one_job() -> str | None:
    """Claim a single queued job for processing.

    Only jobs with status=queued are eligible for claiming.
    Jobs in awaiting_upload status are NOT claimed (upload not yet confirmed).
    """
    stmt = (
        select(VideoAnalysisJob)
        .where(VideoAnalysisJob.status == VideoAnalysisJobStatus.queued)
        # ... rest of query
    )
```

### 5. Migration ([backend/alembic/versions/f1a2b3c4d5e6_add_awaiting_upload_job_status.py](backend/alembic/versions/f1a2b3c4d5e6_add_awaiting_upload_job_status.py))
**Alembic migration to add new enum value:**
```python
def upgrade() -> None:
    op.execute("""
        ALTER TYPE video_analysis_job_status
        ADD VALUE IF NOT EXISTS 'awaiting_upload' BEFORE 'queued';
    """)
```

### 6. Tests ([backend/tests/test_upload_lifecycle.py](backend/tests/test_upload_lifecycle.py))
**Comprehensive integration tests:**
- ✅ Jobs start as `awaiting_upload` (not claimable)
- ✅ Worker cannot claim jobs until upload completes
- ✅ Upload-complete transitions job to `queued`
- ✅ Worker can claim `queued` jobs
- ✅ Upload-complete is idempotent (safe to call multiple times)
- ✅ Upload-complete fails gracefully on S3 404

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Client: POST /videos/upload/initiate                    │
│    → Creates VideoAnalysisJob                               │
│    → Status: awaiting_upload (NOT claimable)                │
│    → Returns presigned PUT URL                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Client: Uploads video to S3 using presigned URL         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Client: POST /videos/upload/complete                    │
│    → Verifies S3 object exists (head_object)                │
│    → If exists: Status → queued (NOW claimable)             │
│    → If missing: Status → failed, return 400                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Worker: Claims job (only if status=queued)              │
│    → Downloads video from S3 (guaranteed to exist)          │
│    → Processes video → Status: quick_running → done         │
└─────────────────────────────────────────────────────────────┘
```

## Status Transitions

```
awaiting_upload → queued → quick_running → quick_done → deep_running → done
       │              │
       └──────────────┴─────────────────────────────────────────→ failed
```

## Idempotency Guarantees

| Job Status | upload-complete Action |
|------------|------------------------|
| `awaiting_upload` | Verify S3 → transition to `queued` |
| `failed` | Retry verification → transition to `queued` or `failed` |
| `queued` | Return success (no changes) |
| `quick_running` | Return success (no changes) |
| `quick_done` | Return success (no changes) |
| `deep_running` | Return success (no changes) |
| `done` | Return success (no changes) |

## Testing

Run the new test suite:
```powershell
$env:PYTHONPATH = "C:\Users\Hp\Cricksy_Scorer"
$env:CRICKSY_IN_MEMORY_DB = "1"
cd backend
pytest tests/test_upload_lifecycle.py -v
```

## Migration Steps

1. **Run migration:**
   ```powershell
   cd backend
   alembic upgrade head
   ```

2. **Verify enum update:**
   ```sql
   SELECT enumlabel FROM pg_enum
   WHERE enumtypid = 'video_analysis_job_status'::regtype
   ORDER BY enumsortorder;
   ```

3. **Deploy code:**
   - Deploy backend with new code
   - Worker will automatically only claim `queued` jobs

## Backward Compatibility

- Existing jobs with `status=queued` remain claimable (no migration needed)
- New enum value added BEFORE `queued` for logical ordering
- Worker query unchanged (still filters by `status=queued`)
- Migration is forward-only (cannot remove enum values in PostgreSQL)

## Monitoring

**Key metrics to watch:**
- **S3 404 errors**: Should drop to zero after deployment
- **Job stuck in awaiting_upload**: Indicates client upload failures
- **Job failed with S3 verification errors**: Indicates network/S3 issues

**Log queries:**
```python
# Find jobs stuck awaiting upload for >5 minutes
SELECT id, created_at FROM video_analysis_jobs
WHERE status = 'awaiting_upload'
AND created_at < NOW() - INTERVAL '5 minutes';

# Count jobs by status
SELECT status, COUNT(*) FROM video_analysis_jobs
GROUP BY status;
```

## Rollback Plan

If issues arise:
1. **Database**: Enum value can stay (backward compatible)
2. **Code**: Revert to previous version
3. **Stuck jobs**: Manually transition to `queued`:
   ```sql
   UPDATE video_analysis_jobs
   SET status = 'queued', stage = 'QUEUED'
   WHERE status = 'awaiting_upload' AND created_at < NOW() - INTERVAL '10 minutes';
   ```

## Files Changed

| File | Lines Changed | Purpose |
|------|---------------|---------|
| `backend/sql_app/models.py` | +1 | Add enum value |
| `backend/routes/coach_pro_plus.py` | +50 | Upload lifecycle logic |
| `backend/workers/analysis_worker.py` | +8 | Documentation update |
| `backend/alembic/versions/f1a2b3c4d5e6_*.py` | +43 | Database migration |
| `backend/tests/test_upload_lifecycle.py` | +253 | Integration tests |

**Total: ~355 lines added/modified**

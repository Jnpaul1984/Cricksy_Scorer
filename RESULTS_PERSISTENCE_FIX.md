# Results Persistence Fix - Implementation Summary

## Problem Statement

**SYMPTOM**: UI shows "analysis not working" despite production logs proving that:
- Quick analysis runs: 151 frames processed
- Deep analysis runs: 3653 frames processed
- Metrics computed (5 metrics)
- Findings generated (4 findings with overall level: low)
- Report generated successfully
- Job marked as `done` with `stage=DONE` and `progress=100%`

**ROOT CAUSE**: Findings and report were computed correctly but **NOT persisted** to database fields the frontend could access. The data was buried inside the `deep_results` JSON blob that the UI wasn't parsing.

## Solution Architecture

### 1. Database Schema Changes

Added 6 new fields to `VideoAnalysisJob` model:

```python
# Extracted artifacts for frontend consumption
quick_findings: Mapped[dict[str, Any] | None]  # Findings from quick pass
quick_report: Mapped[dict[str, Any] | None]    # Report from quick pass
deep_findings: Mapped[dict[str, Any] | None]   # Findings from deep pass
deep_report: Mapped[dict[str, Any] | None]     # Report from deep pass

# S3 artifact keys for large payloads
quick_results_s3_key: Mapped[str | None]  # S3 key for quick_results.json
deep_results_s3_key: Mapped[str | None]   # S3 key for deep_results.json
```

**Migration**: `h3i4j5k6l7m8_add_findings_report_fields.py`

### 2. Worker Changes (analysis_worker.py)

#### Quick Pass Persistence

```python
# Extract findings and report from artifacts
quick_findings = quick_payload.get("findings")
quick_report = quick_payload.get("report")

# Persist to DB
job.quick_results = quick_payload
job.quick_results_s3_key = quick_out_key
job.quick_findings = quick_findings
job.quick_report = quick_report

# Log persisted artifacts
logger.info(
    f"Persisted quick artifacts: job_id={job.id} "
    f"results_s3_key={quick_out_key} "
    f"findings_len={len(quick_findings.get('findings', []))} "
    f"report_len={len(str(quick_report.get('text', '')))}"
)
```

#### Deep Pass Persistence

```python
# Extract findings and report
deep_findings = deep_payload.get("findings")
deep_report = deep_payload.get("report")

# GUARDRAIL: Verify critical artifacts exist
if not deep_findings or not deep_report:
    error_msg = (
        f"Critical artifacts missing: "
        f"findings={'present' if deep_findings else 'MISSING'} "
        f"report={'present' if deep_report else 'MISSING'}"
    )
    logger.error(f"Deep job failed validation: job_id={job.id} {error_msg}")
    job.status = VideoAnalysisJobStatus.failed
    job.stage = "FAILED"
    job.error_message = error_msg
    raise ValueError(error_msg)

# Persist to DB
job.deep_results = deep_payload
job.deep_results_s3_key = deep_out_key
job.deep_findings = deep_findings
job.deep_report = deep_report
```

### 3. API Response Changes (VideoAnalysisJobRead)

```python
class VideoAnalysisJobRead(BaseModel):
    # ... existing fields ...

    # Extracted artifacts for frontend consumption
    quick_findings: dict | None = None
    quick_report: dict | None = None
    deep_findings: dict | None = None
    deep_report: dict | None = None

    # S3 keys for downloading full results
    quick_results_s3_key: str | None = None
    deep_results_s3_key: str | None = None
```

### 4. Enhanced Logging

New log entries added:

```
INFO: Saving quick results to S3: job_id=... bucket=... key=...
INFO: Saving deep results to S3: job_id=... bucket=... key=...
INFO: Saving deep frames to S3: job_id=... frames_count=3653
INFO: Persisted quick artifacts: job_id=... results_s3_key=... findings_len=4 report_len=1234
INFO: [PERSISTED] Deep job completed: job_id=... deep_results_s3_key=... findings_len=4 report_len=1234
```

### 5. Guardrails Added

**Before marking job as `done`, worker now validates:**

1. `quick_findings` is not None (quick-only jobs)
2. `quick_report` is not None (quick-only jobs)
3. `deep_findings` is not None (deep jobs)
4. `deep_report` is not None (deep jobs)

**If validation fails:**
- Job status → `failed`
- Job stage → `FAILED`
- `error_message` populated with details
- Session status → `failed`
- Exception raised with clear message

## Verification Points

### Production Logs (Expected)

```
INFO: Saving deep results to S3: job_id=0184a7d5-... bucket=cricksy-coach-videos-prod key=coach_plus/.../deep_results.json
INFO: [PERSISTED] Deep job completed: job_id=0184a7d5-... status_after=done stage=DONE progress=100% deep_results_s3_key=coach_plus/.../deep_results.json findings_len=4 report_len=1234
```

### Database Verification

```sql
SELECT
    id,
    status,
    stage,
    progress_pct,
    deep_findings IS NOT NULL as has_findings,
    deep_report IS NOT NULL as has_report,
    deep_results_s3_key
FROM video_analysis_jobs
WHERE id = '0184a7d5-8f73-4348-a410-f638b85a3ba0';
```

Expected result:
- `status = 'done'`
- `stage = 'DONE'`
- `progress_pct = 100`
- `has_findings = true`
- `has_report = true`
- `deep_results_s3_key` contains S3 path

### Frontend Verification

GET `/api/coaches/plus/analysis-jobs/{job_id}` should return:

```json
{
  "id": "0184a7d5-...",
  "status": "done",
  "stage": "DONE",
  "progress_pct": 100,
  "deep_findings": {
    "findings": [
      {
        "metric": "head_stability_score",
        "level": "low",
        "message": "...",
        "evidence": {...}
      }
    ],
    "overall_level": "low"
  },
  "deep_report": {
    "text": "**Overall Assessment**: Your technique analysis shows...",
    "overall_level": "low",
    "sections": [...]
  },
  "deep_results_s3_key": "coach_plus/.../deep_results.json"
}
```

## Migration Instructions

### Development

```bash
# Apply migration
cd backend
alembic upgrade head
```

### Production

```sql
-- Migration will add these columns:
ALTER TABLE video_analysis_jobs ADD COLUMN quick_findings JSON;
ALTER TABLE video_analysis_jobs ADD COLUMN quick_report JSON;
ALTER TABLE video_analysis_jobs ADD COLUMN deep_findings JSON;
ALTER TABLE video_analysis_jobs ADD COLUMN deep_report JSON;
ALTER TABLE video_analysis_jobs ADD COLUMN quick_results_s3_key VARCHAR(500);
ALTER TABLE video_analysis_jobs ADD COLUMN deep_results_s3_key VARCHAR(500);
```

### ECS Worker Deployment

1. Deploy updated worker image with new persistence logic
2. Existing jobs will complete without new fields (backward compatible)
3. New jobs will populate all fields
4. Frontend checks for `deep_findings` presence before rendering

## Rollback Plan

If issues arise:

1. **Code rollback**: Revert commit `f907a0c`
2. **Database rollback**: `alembic downgrade -1` (removes columns)
3. **No data loss**: Old `deep_results` JSON still contains findings/report

## Files Changed

- `backend/sql_app/models.py` - Added 6 new fields to VideoAnalysisJob
- `backend/workers/analysis_worker.py` - Extract and persist findings/report
- `backend/routes/coach_pro_plus.py` - Updated VideoAnalysisJobRead schema
- `backend/alembic/versions/h3i4j5k6l7m8_add_findings_report_fields.py` - Migration

## Commit

**Commit Hash**: `f907a0c`
**Branch**: `main`
**Pushed**: Yes (06a9615..f907a0c)

## Next Steps

1. Monitor production logs for new persistence messages
2. Verify `deep_findings` and `deep_report` populated in DB
3. Confirm UI can render findings and report
4. Check ECS task logs for guardrail failures (should be zero)

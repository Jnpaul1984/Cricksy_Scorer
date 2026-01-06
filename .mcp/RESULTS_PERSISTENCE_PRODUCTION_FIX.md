# Results Persistence Production Fix - Implementation Summary

## Problem Analysis (from prod logs)

**Production Evidence**: Job `e39a834b-43c0-4f43-8f27-ba55ef4b6579`
```
INFO: [PERSISTED] Deep job completed ... status_after=done stage=DONE progress=100%
INFO: deep_results_s3_key=.../deep_results.json findings_len=4 report_len=0
```

### Issues Identified

1. **report_len=0**: Worker logging `report.get('text', '')` but report service returns `{summary, top_issues, drills, one_week_plan, notes}` without `text` key
2. **No presigned URLs**: S3 keys persisted but frontend has no URLs to download results
3. **Polling stops at timeout**: Frontend stops polling after 5 minutes even if job still running
4. **No modal refetch**: Modal doesn't refetch job when opened

## Solutions Implemented

### 1. Fixed Report Logging (Backend)

**File**: `backend/workers/analysis_worker.py`

**Problem**: Worker looking for non-existent `text` key in report object

**Fix**: Changed from `report.get('text', '')` to `report.get('summary', '')` and enhanced logging

```python
# Before
f"report_len={len(str(quick_report.get('text', ''))) if quick_report else 0}"

# After  
f"report_summary_len={len(str(quick_report.get('summary', ''))) if quick_report else 0} "
f"report_keys={list(deep_report.keys()) if deep_report else []}"
```

**New Logs**:
```
INFO: [PERSISTED] Deep job completed: job_id=...
  deep_findings='present' 
  deep_report='present'
  findings_len=4
  report_summary_len=123
  report_keys=['summary', 'top_issues', 'drills', 'one_week_plan', 'notes']
```

### 2. Added Presigned URLs for Results (Backend)

**File**: `backend/routes/coach_pro_plus.py`

**Changes**:
1. Updated `VideoAnalysisJobRead` schema with new fields:
   ```python
   quick_results_url: str | None = None
   deep_results_url: str | None = None
   ```

2. Added presigned URL generation in `GET /analysis-jobs/{job_id}`:
   ```python
   if job.quick_results_s3_key:
       quick_url = s3_service.generate_presigned_get_url(
           bucket=settings.S3_COACH_VIDEOS_BUCKET,
           key=job.quick_results_s3_key,
           expires_in=settings.S3_STREAM_URL_EXPIRES_SECONDS,
       )
       updates["quick_results_url"] = quick_url
   
   if job.deep_results_s3_key:
       deep_url = s3_service.generate_presigned_get_url(...)
       updates["deep_results_url"] = deep_url
   ```

**API Response Now Includes**:
```json
{
  "id": "e39a834b...",
  "status": "done",
  "deep_findings": {...},
  "deep_report": {...},
  "deep_results_s3_key": "coach_plus/.../deep_results.json",
  "deep_results_url": "https://s3...?X-Amz-Signature=...",
  "quick_results_url": "https://s3...?X-Amz-Signature=..."
}
```

### 3. Fixed Frontend Polling (Frontend)

**File**: `frontend/src/views/CoachProPlusVideoSessionsView.vue`

**Problem**: Polling stops completely after 5-minute timeout

**Before**:
```typescript
if (Date.now() - startedAt > timeoutMs) {
  pollTimedOut.value = true;
  stopUiPolling();  // STOPS POLLING
  videoStore.stopPollingJob(jobId);  // STOPS STORE POLLING TOO
}
```

**After**:
```typescript
// Show timeout message but KEEP POLLING until terminal status
if (Date.now() - startedAt > timeoutMs && !pollTimedOut.value) {
  pollTimedOut.value = true;
  // DO NOT stop polling - keep checking until done/failed
}
```

**Behavior Now**:
- Polls every 1 second indefinitely
- Shows "taking longer than expected" message after 5 minutes
- Continues polling until `status === 'done' || 'failed' || 'completed'`
- Only stops on terminal status

### 4. Report Structure (Backend - for future)

**Context**: `coach_report_service.generate_report_text()` returns:
```python
{
  "summary": str,           # ← Used for logging
  "top_issues": [...],
  "drills": [...],
  "one_week_plan": [...],
  "notes": str,
  "generated_with_llm": bool
}
```

**No `text` key exists** - this is by design. The frontend uses:
- `deep_findings.findings[]` array for priorities
- `deep_report.summary` for overall assessment
- `deep_report.drills` for drill recommendations

## Deployment Steps

### 1. Backend Deployment

```bash
# Already committed (commits f907a0c, 39a1cc3, and new changes)
git pull origin main

# Deploy updated worker
docker build -t cricksy-worker:results-fix-v2 .
docker push <ECR_URI>:latest
aws ecs update-service --cluster cricksy-ai-cluster --service cricksy-ai-worker --force-new-deployment

# Deploy updated API
docker build -t cricksy-api:results-fix-v2 .
docker push <ECR_URI>:latest
aws ecs update-service --cluster cricksy-backend-cluster --service cricksy-backend --force-new-deployment
```

### 2. Frontend Deployment

```bash
cd frontend
npm run build
# Deploy dist/ to your hosting (S3, CloudFront, etc.)
```

### 3. Database Migration

Already applied from previous fix:
```bash
cd backend
alembic upgrade head
# Confirms h3i4j5k6l7m8 (findings/report fields)
```

## Verification

### Worker Logs (Expected)

```
INFO: Saving deep results to S3: job_id=... bucket=cricksy-coach-videos-prod key=.../deep_results.json
INFO: [PERSISTED] Deep job completed: job_id=...
  status_after=done stage=DONE progress=100%
  deep_results_s3_key=coach_plus/.../deep_results.json
  deep_findings='present'
  deep_report='present'
  findings_len=4
  report_summary_len=145
  report_keys=['summary', 'top_issues', 'drills', 'one_week_plan', 'notes']
```

### API Response (Expected)

```bash
curl -H "Authorization: Bearer $TOKEN" \
  https://api.cricksy.com/api/coaches/plus/analysis-jobs/e39a834b-43c0-4f43-8f27-ba55ef4b6579
```

```json
{
  "id": "e39a834b-43c0-4f43-8f27-ba55ef4b6579",
  "status": "done",
  "stage": "DONE",
  "progress_pct": 100,
  "deep_findings": {
    "findings": [
      {"metric": "head_stability_score", "severity": "low", ...}
    ],
    "overall_level": "low"
  },
  "deep_report": {
    "summary": "Your's Analysis: Your technique demonstrates solid fundamentals...",
    "top_issues": [...],
    "drills": [...],
    "one_week_plan": [...]
  },
  "deep_results_s3_key": "coach_plus/.../deep_results.json",
  "deep_results_url": "https://cricksy-coach-videos-prod.s3.amazonaws.com/...?X-Amz-Signature=..."
}
```

### Frontend Behavior (Expected)

1. **During Analysis**:
   - Polls every 1 second
   - Shows progress UI with status
   - After 5 minutes, shows "taking longer than expected"
   - **Keeps polling** until done

2. **On Completion**:
   - Renders findings from `deep_findings.findings`
   - Shows summary from `deep_report.summary`
   - Displays drills from `deep_report.drills`
   - Provides "Jump to" for evidence markers

3. **Database Check**:
```sql
SELECT 
    id,
    status,
    stage,
    deep_findings IS NOT NULL as has_findings,
    deep_report IS NOT NULL as has_report,
    deep_results_s3_key,
    completed_at
FROM video_analysis_jobs
WHERE id = 'e39a834b-43c0-4f43-8f27-ba55ef4b6579';
```

Expected:
- `has_findings = true`
- `has_report = true`  
- `deep_results_s3_key` populated
- `status = 'done'`, `stage = 'DONE'`

## Files Changed

### Backend
- `backend/workers/analysis_worker.py` - Fixed report logging, enhanced post-commit verification
- `backend/routes/coach_pro_plus.py` - Added presigned URL generation, updated schema

### Frontend
- `frontend/src/views/CoachProPlusVideoSessionsView.vue` - Fixed polling to continue on timeout

## Known Issues

### Report Structure Mismatch (Non-Breaking)

The worker logs `report_summary_len` instead of `report_len` now. This is cosmetic - the actual `deep_report` object is persisted correctly to the database with all keys:
- `summary` ← Used in frontend
- `top_issues`
- `drills`
- `one_week_plan`
- `notes`

The frontend uses these keys directly via `buildCoachNarrative()` which extracts data from:
- `deep_findings.findings[]` for priorities
- `deep_report.summary` for overall text
- `deep_report.drills` for drill recommendations

## Success Criteria

✅ Worker logs show `deep_findings='present'` and `deep_report='present'`
✅ Worker logs show `report_summary_len > 0` and `report_keys=[...]`
✅ Database has `deep_findings` and `deep_report` populated  
✅ API response includes `deep_results_url` presigned URL
✅ Frontend continues polling past 5-minute timeout
✅ UI displays findings and report even if job takes long
✅ No "analysis not working" messages from users

## Rollback Plan

If issues occur:
```bash
# Code rollback
git revert <commit_hash>

# Redeploy previous versions
aws ecs update-service \
  --cluster cricksy-ai-cluster \
  --service cricksy-ai-worker \
  --task-definition cricksy-ai-worker:<PREV_REVISION>

aws ecs update-service \
  --cluster cricksy-backend-cluster \
  --service cricksy-backend \
  --task-definition cricksy-backend:<PREV_REVISION>
```

No database rollback needed - new fields are nullable and backward compatible.

## Related Documentation

- [RESULTS_PERSISTENCE_FIX.md](../RESULTS_PERSISTENCE_FIX.md) - Original persistence fix
- [RESULTS_PERSISTENCE_DEPLOYMENT.md](../RESULTS_PERSISTENCE_DEPLOYMENT.md) - Deployment guide

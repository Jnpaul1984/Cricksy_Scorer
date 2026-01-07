# S3 Upload Fix - Quick Reference

## 🎯 Problem Fixed
Workers downloading from S3 before upload completes → 404 errors

## 🔧 Solution
Two-phase job lifecycle with S3 verification gate

## 📊 Status Flow
```
awaiting_upload → queued → processing → done
     (NEW)      (claimable)
```

## 🚀 Key Changes

### Job Creation (Initiate)
```python
# OLD
status=VideoAnalysisJobStatus.queued  # ❌ Immediately claimable

# NEW
status=VideoAnalysisJobStatus.awaiting_upload  # ✅ Not claimable
```

### Upload Complete
```python
# NEW: S3 verification before queueing
s3.head_object(Bucket=bucket, Key=key)  # Preflight check
if object_exists:
    job.status = VideoAnalysisJobStatus.queued  # ✅ NOW claimable
else:
    job.status = VideoAnalysisJobStatus.failed  # ❌ Fail early
```

### Worker Claiming
```python
# Unchanged - already correct
.where(VideoAnalysisJob.status == VideoAnalysisJobStatus.queued)
```

## 🔐 Safety Features

✅ **Idempotency**: Calling upload-complete multiple times is safe
✅ **S3 Verification**: HeadObject confirms upload before queueing
✅ **Early Failure**: 404s caught before worker attempts download
✅ **Backward Compatible**: Existing `queued` jobs still work

## 📝 Migration

```powershell
cd backend
alembic upgrade head
```

## 🧪 Testing

```powershell
$env:PYTHONPATH = "C:\Users\Hp\Cricksy_Scorer"
$env:CRICKSY_IN_MEMORY_DB = "1"
cd backend
pytest tests/test_upload_lifecycle.py -v
```

## 📁 Files Modified

- ✏️ `backend/sql_app/models.py` - Add enum value
- ✏️ `backend/routes/coach_pro_plus.py` - Upload lifecycle
- ✏️ `backend/workers/analysis_worker.py` - Documentation
- 🆕 `backend/alembic/versions/f1a2b3c4d5e6_*.py` - Migration
- 🆕 `backend/tests/test_upload_lifecycle.py` - Tests

## 🔍 Monitoring Queries

```sql
-- Jobs awaiting upload >5 min (stuck uploads)
SELECT id, created_at FROM video_analysis_jobs
WHERE status = 'awaiting_upload'
AND created_at < NOW() - INTERVAL '5 minutes';

-- Job status distribution
SELECT status, COUNT(*) FROM video_analysis_jobs
GROUP BY status;
```

## 🆘 Manual Recovery

If jobs get stuck in `awaiting_upload`:

```sql
-- Force to queued (after confirming S3 upload)
UPDATE video_analysis_jobs
SET status = 'queued', stage = 'QUEUED'
WHERE id = '<job_id>';
```

## ✅ Success Metrics

After deployment:
- **S3 404 errors**: Should be 0
- **Job failures**: Only on legitimate upload failures
- **Processing time**: Unchanged (no performance impact)

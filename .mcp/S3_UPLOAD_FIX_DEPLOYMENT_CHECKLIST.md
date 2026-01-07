# S3 Upload Fix - Deployment Checklist

## Pre-Deployment Validation

### 1. Code Review ✅
- [x] Enum value added to `VideoAnalysisJobStatus`
- [x] Upload initiate sets `awaiting_upload` status
- [x] Upload complete has idempotency checks
- [x] Upload complete verifies S3 object exists
- [x] Worker only claims `queued` jobs
- [x] Migration file created
- [x] Tests added

### 2. Static Analysis
```powershell
# Check for syntax errors
cd backend
python -m py_compile sql_app/models.py
python -m py_compile routes/coach_pro_plus.py
python -m py_compile workers/analysis_worker.py
```

### 3. Run Tests
```powershell
$env:PYTHONPATH = "C:\Users\Hp\Cricksy_Scorer"
$env:CRICKSY_IN_MEMORY_DB = "1"
cd backend
pytest tests/test_upload_lifecycle.py -v
```

Expected output:
```
test_upload_lifecycle_prevents_premature_claiming PASSED
test_upload_complete_idempotency PASSED
test_upload_complete_fails_on_missing_s3_object PASSED
```

## Deployment Steps

### Phase 1: Database Migration
```powershell
# Backup database first!
pg_dump -h <host> -U <user> -d cricksy_scorer > backup_$(date +%Y%m%d).sql

# Run migration
cd backend
alembic upgrade head
```

**Verification:**
```sql
-- Check enum values
SELECT enumlabel FROM pg_enum
WHERE enumtypid = 'video_analysis_job_status'::regtype
ORDER BY enumsortorder;

-- Expected output includes 'awaiting_upload' before 'queued'
```

### Phase 2: Deploy Backend
```powershell
# Option A: Docker
docker compose build backend
docker compose up -d backend

# Option B: Direct deployment
# Copy files to server
# Restart backend service
```

**Verification:**
```powershell
# Check backend logs for startup
docker compose logs backend -f

# Test initiate endpoint
curl -X POST http://localhost:8000/api/coaches/plus/videos/upload/initiate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","sample_fps":10,"include_frames":false}'

# Verify response includes awaiting_upload status in database
```

### Phase 3: Monitor Worker
```powershell
# Worker doesn't need restart - will automatically use new query
# Monitor for any issues
docker compose logs worker -f
```

## Post-Deployment Validation

### 1. Check Job Status Distribution
```sql
SELECT status, COUNT(*) as count
FROM video_analysis_jobs
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY status
ORDER BY count DESC;
```

Expected:
- `awaiting_upload`: Jobs waiting for upload completion
- `queued`: Jobs ready for processing
- No premature `quick_running` for new jobs

### 2. Monitor S3 Errors
```powershell
# Check worker logs for 404 errors (should be 0)
docker compose logs worker | grep "404"
docker compose logs worker | grep "NoSuchKey"
```

Expected: **No results** for new jobs created after deployment

### 3. Test End-to-End Flow
```powershell
# 1. Create session
POST /api/coaches/plus/sessions

# 2. Initiate upload
POST /api/coaches/plus/videos/upload/initiate
# → Verify job.status = awaiting_upload

# 3. Upload to S3 using presigned URL
# → Use actual file upload

# 4. Complete upload
POST /api/coaches/plus/videos/upload/complete
# → Verify job.status = queued

# 5. Check worker picks up job
# → Verify job.status transitions to quick_running
```

## Rollback Plan

### If Issues Detected:

#### Option 1: Revert Code (Recommended)
```powershell
# Rollback to previous version
git revert HEAD
docker compose build backend
docker compose up -d backend
```

#### Option 2: Manual Job Fix
```sql
-- Fix stuck jobs (only if needed)
UPDATE video_analysis_jobs
SET status = 'queued', stage = 'QUEUED'
WHERE status = 'awaiting_upload'
  AND created_at < NOW() - INTERVAL '10 minutes';
```

**Note:** Database enum cannot be easily rolled back. It's harmless to leave it.

## Success Criteria

✅ **Migration complete**: Enum has `awaiting_upload` value
✅ **No backend errors**: Service starts without errors
✅ **Jobs created correctly**: New jobs start with `awaiting_upload`
✅ **Upload flow works**: Jobs transition `awaiting_upload` → `queued` → `processing`
✅ **Worker claims jobs**: Only `queued` jobs are claimed
✅ **No S3 404s**: Zero HeadObject errors for new jobs
✅ **Idempotency works**: Calling complete twice doesn't break anything

## Monitoring Alerts

Set up alerts for:
```sql
-- Jobs stuck in awaiting_upload >5 minutes
SELECT COUNT(*) FROM video_analysis_jobs
WHERE status = 'awaiting_upload'
  AND created_at < NOW() - INTERVAL '5 minutes';
-- Alert if count > 5

-- Job failure rate spike
SELECT COUNT(*) FROM video_analysis_jobs
WHERE status = 'failed'
  AND created_at > NOW() - INTERVAL '1 hour';
-- Alert if count > 10
```

## Communication

**Internal Team:**
> Deployed fix for S3 upload race condition. Jobs now require upload completion before processing. Monitor for any stuck uploads in `awaiting_upload` status.

**Users (if customer-facing):**
> Improved video upload reliability. Upload status tracking is more accurate.

## Cleanup (After 1 Week)

If successful, document learnings:
```markdown
# Lessons Learned
- Always gate async processing on confirmed resource availability
- S3 HeadObject is cheap - preflight checks prevent expensive failures
- Two-phase workflows (initiate → complete) provide better control
```

## Contact

**On-call Engineer:** [Your Name]
**Escalation:** Team Lead
**Monitoring:** Grafana Dashboard → Video Processing

---

**Deployment Date:** _____________
**Deployed By:** _____________
**Sign-off:** _____________

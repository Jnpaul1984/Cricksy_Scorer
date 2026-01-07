# Results Persistence Fix - Deployment Quick Reference

## Commits
- **f907a0c**: Main fix (add findings/report fields, guardrails, logging)
- **39a1cc3**: Linting fixes (E501 line length)

## Deployment Checklist

### 1. Database Migration (Production)

```bash
# SSH into ECS task or RDS bastion
cd /app/backend
alembic upgrade head

# Verify migration applied
alembic current
# Should show: h3i4j5k6l7m8 (head)
```

**Migration adds 6 columns**:
- `quick_findings` (JSON)
- `quick_report` (JSON)
- `deep_findings` (JSON)
- `deep_report` (JSON)
- `quick_results_s3_key` (VARCHAR 500)
- `deep_results_s3_key` (VARCHAR 500)

### 2. Deploy Updated Worker

```bash
# Build and push new image
docker build -t cricksy-worker:results-fix .
docker tag cricksy-worker:results-fix <ECR_URI>:latest
docker push <ECR_URI>:latest

# Update ECS task
aws ecs update-service \
  --cluster cricksy-ai-cluster \
  --service cricksy-ai-worker \
  --force-new-deployment \
  --region us-east-1
```

### 3. Deploy Updated API

```bash
# Backend already has updated VideoAnalysisJobRead schema
# Just redeploy to pick up new model fields
docker build -t cricksy-api:results-fix .
docker tag cricksy-api:results-fix <ECR_URI>:latest
docker push <ECR_URI>:latest

# Update ECS task
aws ecs update-service \
  --cluster cricksy-backend-cluster \
  --service cricksy-backend \
  --force-new-deployment \
  --region us-east-1
```

### 4. Verify Deployment

#### Check Logs (CloudWatch)

**Worker logs should show**:
```
INFO: Saving deep results to S3: job_id=... bucket=cricksy-coach-videos-prod key=...
INFO: [PERSISTED] Deep job completed: job_id=... deep_results_s3_key=... findings_len=4 report_len=1234
```

**API logs should show** (on GET /analysis-jobs/{id}):
```
Response includes deep_findings and deep_report fields
```

#### Check Database

```sql
-- Check a completed job
SELECT
    id,
    status,
    stage,
    deep_findings IS NOT NULL as has_findings,
    deep_report IS NOT NULL as has_report,
    deep_results_s3_key,
    completed_at
FROM video_analysis_jobs
WHERE status = 'done'
ORDER BY completed_at DESC
LIMIT 1;
```

Expected:
- `has_findings = true`
- `has_report = true`
- `deep_results_s3_key` populated

#### Test API Response

```bash
curl -H "Authorization: Bearer $TOKEN" \
  https://api.cricksy.com/api/coaches/plus/analysis-jobs/<JOB_ID>
```

Response should include:
```json
{
  "deep_findings": {
    "findings": [...],
    "overall_level": "low"
  },
  "deep_report": {
    "text": "**Overall Assessment**: ...",
    "sections": [...]
  }
}
```

### 5. Monitor for Guardrail Failures

**Watch for these ERROR logs**:
```
ERROR: Deep job failed validation: job_id=... Critical artifacts missing: findings=MISSING report=MISSING
ERROR: Quick-only job failed validation: job_id=...
```

If you see these:
1. Check S3 uploads succeeded
2. Check `run_pose_metrics_findings_report()` returned complete data
3. Check `coach_findings.generate_findings()` is working
4. Check `coach_report_service.generate_report_text()` is working

### 6. Rollback Plan

If issues occur:

```bash
# Database rollback
cd /app/backend
alembic downgrade -1

# Code rollback
git revert 39a1cc3 f907a0c
docker build -t cricksy-worker:rollback .
# ... push and deploy

# Or point ECS to previous task definition
aws ecs update-service \
  --cluster cricksy-ai-cluster \
  --service cricksy-ai-worker \
  --task-definition cricksy-ai-worker:<PREV_REVISION> \
  --region us-east-1
```

## Expected Impact

### Before Fix
- UI shows "analysis not working"
- `GET /analysis-jobs/{id}` returns only `deep_results` blob
- Frontend has no findings/report to display

### After Fix
- UI receives `deep_findings` and `deep_report` directly
- No JSON parsing needed on frontend
- Logs show "Persisted job artifacts: findings_len=4 report_len=1234"
- Jobs fail fast if artifacts missing (guardrails)

## Timeline

1. **Database migration**: ~5 seconds (adds columns, no data backfill)
2. **Worker deployment**: ~2 minutes (ECS task replacement)
3. **API deployment**: ~2 minutes (ECS task replacement)
4. **Total downtime**: ~0 (rolling deployment)
5. **First fixed job**: Next job after worker deployment completes

## Success Criteria

✅ Worker logs show "Persisted job artifacts" with findings_len > 0
✅ Database has `deep_findings` and `deep_report` populated
✅ API response includes `deep_findings` and `deep_report`
✅ UI can display findings and report
✅ No "Critical artifacts missing" errors in logs

## Files Changed

- `backend/sql_app/models.py` - Added 6 fields
- `backend/workers/analysis_worker.py` - Extract + persist artifacts
- `backend/routes/coach_pro_plus.py` - Updated response schema
- `backend/alembic/versions/h3i4j5k6l7m8_add_findings_report_fields.py` - Migration

## Contact

If deployment issues occur:
1. Check CloudWatch logs for ERROR messages
2. Verify migration applied: `alembic current`
3. Check RDS for new columns: `\d video_analysis_jobs`
4. Test API endpoint manually with curl
5. Roll back if needed (see Rollback Plan above)

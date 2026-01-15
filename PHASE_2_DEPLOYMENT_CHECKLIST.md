# Phase 2 Deployment Checklist

**Feature:** Coach Intent → Outcomes Tracking (Goals vs Outcomes)
**Branch:** `feat/coach-analysis-phase2`
**Date:** January 15, 2026

---

## ✅ PRE-DEPLOYMENT VERIFICATION

### 1. Backend Tests
- [x] **All 23 Phase 2 tests passing**
  ```bash
  cd backend
  pytest tests/test_goal_compliance.py tests/test_session_comparison.py -v
  ```
  **Result:** ✅ 23 passed

### 2. Database Migration
- [ ] **Apply migration to development database**
  ```bash
  cd backend
  alembic upgrade head
  ```
  **Expected:** New columns added to `video_analysis_jobs` and `target_zones`

- [ ] **Verify migration in database**
  ```sql
  -- Check video_analysis_jobs columns
  SELECT column_name, data_type
  FROM information_schema.columns
  WHERE table_name = 'video_analysis_jobs'
  AND column_name IN ('coach_goals', 'outcomes', 'goal_compliance_pct');

  -- Check target_zones columns
  SELECT column_name, data_type
  FROM information_schema.columns
  WHERE table_name = 'target_zones'
  AND column_name IN ('target_accuracy', 'is_active');
  ```

### 3. Code Quality
- [ ] **Run linters**
  ```bash
  cd backend
  ruff check . --fix
  mypy backend/services/goal_compliance.py
  mypy backend/services/session_comparison.py
  ```

- [ ] **Check imports**
  ```bash
  # Ensure all new files are importable
  python -c "from backend.services.goal_compliance import calculate_compliance"
  python -c "from backend.services.session_comparison import compare_jobs"
  ```

### 4. API Endpoint Testing
- [ ] **Test set-goals endpoint**
  - Method: POST
  - Path: `/api/coaches/plus/analysis-jobs/{job_id}/set-goals`
  - Auth: Required
  - Payload:
    ```json
    {
      "zones": [{"zone_id": "zone123", "target_accuracy": 0.80}],
      "metrics": [{"code": "HEAD_MOVEMENT", "target_score": 0.70}]
    }
    ```
  - Expected: 200 OK with updated job

- [ ] **Test calculate-compliance endpoint**
  - Method: POST
  - Path: `/api/coaches/plus/analysis-jobs/{job_id}/calculate-compliance`
  - Auth: Required
  - Expected: 200 OK with outcomes JSON

- [ ] **Test get-outcomes endpoint**
  - Method: GET
  - Path: `/api/coaches/plus/analysis-jobs/{job_id}/outcomes`
  - Auth: Required
  - Expected: 200 OK with outcomes (or 404 if not calculated)

- [ ] **Test compare-jobs endpoint**
  - Method: POST
  - Path: `/api/coaches/plus/sessions/{session_id}/compare-jobs`
  - Auth: Required
  - Payload:
    ```json
    {
      "job_ids": ["job1_id", "job2_id", "job3_id"]
    }
    ```
  - Expected: 200 OK with comparison JSON

### 5. PDF Generation
- [ ] **Test PDF export with goals**
  - Create job → Set goals → Calculate compliance → Export PDF
  - Verify Page 2 contains "Your Goals vs Outcomes" table
  - Verify pass/fail indicators (✅/❌)
  - Verify delta calculations

- [ ] **Test PDF export without goals**
  - Create job → Export PDF (no goals set)
  - Verify no Page 2 (or graceful message)
  - Verify existing pages render correctly

---

## 🚀 DEPLOYMENT STEPS

### Phase 2A: Backend Deployment (Ready Now)

1. **Merge to main:**
   ```bash
   git checkout main
   git merge feat/coach-analysis-phase2
   git push origin main
   ```

2. **Deploy backend to staging:**
   - Run database migration: `alembic upgrade head`
   - Restart backend service
   - Verify health check passes

3. **Smoke test in staging:**
   - Create session → Upload video → Set goals → Calculate compliance
   - Verify API responses
   - Export PDF and verify Goals page appears

### Phase 2B: Frontend Deployment (Pending UI Components)

**⏳ Blocked by missing components:**
- GoalSetter.vue
- OutcomesViewer.vue
- SessionComparison.vue
- CoachProPlusVideoSessionsView.vue updates

**To complete:**
1. Implement 4 Vue components (see PHASE_2_IMPLEMENTATION_SUMMARY.md)
2. Test frontend in development
3. Build production bundle: `npm run build`
4. Deploy frontend assets to CDN/hosting

---

## 🔍 POST-DEPLOYMENT VALIDATION

### Backend Health Checks
- [ ] API endpoints respond with 200 OK for valid requests
- [ ] API endpoints respond with 40x/50x for invalid requests
- [ ] Database writes succeed (goals saved correctly)
- [ ] PDF generation completes without errors
- [ ] Logs show no exceptions

### Performance Checks
- [ ] Set goals API completes in < 500ms
- [ ] Calculate compliance API completes in < 2s
- [ ] Compare jobs API completes in < 3s (for 10 jobs)
- [ ] PDF generation completes in < 5s

### Data Validation
- [ ] `coach_goals` JSON structure is valid
- [ ] `outcomes` JSON structure is valid
- [ ] `goal_compliance_pct` is between 0-100
- [ ] Zone compliance calculations are accurate
- [ ] Metric compliance calculations are accurate

---

## 🐛 ROLLBACK PLAN

### If Critical Issues Found:

**1. Database Rollback:**
```bash
cd backend
alembic downgrade -1  # Roll back migration j4k5l6m7n8o9
```

**2. Code Rollback:**
```bash
git revert <commit_hash>  # Revert Phase 2 merge commit
git push origin main
```

**3. Service Restart:**
- Restart backend service to clear any cached state
- Verify old API contracts still work

### Known Safe Rollback:
- Migration is **additive only** (no data loss)
- New columns are **nullable** (existing code unaffected)
- New endpoints are **opt-in** (no breaking changes to existing endpoints)

---

## 📋 FILES CHANGED SUMMARY

### Backend (8 files)
```
✅ backend/alembic/versions/j4k5l6m7n8o9_add_coach_goals_and_outcomes.py
✅ backend/sql_app/models.py
✅ backend/services/goal_compliance.py (NEW)
✅ backend/services/session_comparison.py (NEW)
✅ backend/routes/coach_pro_plus.py
✅ backend/services/reports/coach_report_template.py
✅ backend/services/pdf_export_service.py
✅ backend/tests/test_goal_compliance.py (NEW)
✅ backend/tests/test_session_comparison.py (NEW)
```

### Frontend (1 file)
```
✅ frontend/src/services/coachPlusVideoService.ts
⏳ frontend/src/components/GoalSetter.vue (NOT CREATED)
⏳ frontend/src/components/OutcomesViewer.vue (NOT CREATED)
⏳ frontend/src/components/SessionComparison.vue (NOT CREATED)
⏳ frontend/src/views/CoachProPlusVideoSessionsView.vue (NOT UPDATED)
```

### Documentation (2 files)
```
✅ PHASE_2_READINESS_INVENTORY.md
✅ PHASE_2_IMPLEMENTATION_SUMMARY.md
✅ PHASE_2_DEPLOYMENT_CHECKLIST.md
```

---

## ✨ FEATURE FLAGS (Optional)

If gradual rollout is desired, add feature flag:

```python
# backend/config.py
PHASE_2_GOALS_ENABLED: bool = True  # Toggle via env var

# backend/routes/coach_pro_plus.py (in each Phase 2 endpoint)
if not settings.PHASE_2_GOALS_ENABLED:
    raise HTTPException(
        status_code=503,
        detail="Goals feature is not yet enabled"
    )
```

Set `PHASE_2_GOALS_ENABLED=false` to disable feature in production.

---

## 🎯 SUCCESS METRICS

### Technical Metrics
- [ ] API error rate < 1%
- [ ] PDF generation success rate > 99%
- [ ] Database write success rate 100%
- [ ] No 500 errors in logs

### Business Metrics
- [ ] Coaches use set-goals feature
- [ ] PDF downloads include Goals page
- [ ] Session comparison feature used

### User Feedback
- [ ] No critical bugs reported
- [ ] Goals feature is intuitive
- [ ] Outcomes are accurate

---

**Ready for Backend Deployment:** ✅
**Ready for Full Deployment:** ⏳ (Pending frontend UI)

**Next Action:** Complete 4 frontend Vue components before full deployment.

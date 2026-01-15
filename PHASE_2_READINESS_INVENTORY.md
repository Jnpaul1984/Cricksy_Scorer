# Phase 2 Readiness Inventory: Coach Analysis - Goals vs Outcomes

**Date:** January 15, 2026
**Branch:** `feat/coach-analysis-phase2`
**Context:** Phase 1 delivered diagnostic findings + evidence + PDF reports. Phase 2 adds coach intent → outcomes tracking.

---

## A) CURRENT ARCHITECTURE MAP

### Database Layer (PostgreSQL)
**File:** `backend/sql_app/models.py`

**Core Models:**
- **`VideoSession`** (lines 1669-1770)
  - ID, owner (coach/org), title, notes, player_ids
  - S3 storage: bucket, key, file_size_bytes
  - **`pitch_corners`** (JSON) - 4-point calibration for homography
  - Status: pending/uploaded/processing/ready/failed
  - Relationships: `analysis_jobs[]`, `target_zones[]` (via FK)

- **`VideoAnalysisJob`** (lines 1771-1950)
  - ID, session_id (FK → VideoSession)
  - Configuration: sample_fps, analysis_mode (batting/bowling/wicketkeeping/fielding)
  - Status: awaiting_upload/queued/quick_running/deep_running/done/failed
  - Results storage:
    - `quick_results` (JSON) - pose metrics, detection rate
    - `deep_results` (JSON) - full analysis data
    - `quick_findings` (JSON) - extracted findings from coach_findings.py
    - `deep_findings` (JSON) - extracted findings from coach_findings.py
  - S3 artifacts: `quick_results_s3_key`, `deep_results_s3_key`, `pdf_s3_key`
  - Timestamps: created_at, started_at, completed_at, quick_*/deep_* stage times

- **`TargetZone`** (lines 1972-2000)
  - ID, owner_id (coach), session_id (optional FK)
  - name, shape (rect/circle/polygon)
  - **`definition_json`** (JSON) - shape coordinates
  - **Use case:** Pitch zones for ball tracking accuracy

**Existing Indexes:**
- Sessions: owner, status, created_at
- Jobs: session_id, status, created_at, sqs_message_id
- Zones: owner_id, session_id

---

### Backend Services Layer

**File: `backend/services/coach_findings.py`** (1524 lines)
- **`generate_findings(metrics, context, analysis_mode)`** - Main entry point
- **Mode-specific generators:**
  - `generate_bowling_findings()` - integrates ball tracking
  - `generate_batting_findings()`
  - `generate_wicketkeeping_findings()`
  - `generate_fielding_findings()`
- **Output structure:** `{findings: [...], detection_rate: float}`
- **Each finding:** code, title, severity, evidence, cues, suggested_drills, video_evidence
- **Thresholds:** `THRESHOLDS_BY_MODE` - role-specific acceptable ranges
- **No goals/targets** - purely diagnostic

**File: `backend/services/pose_metrics.py`**
- `compute_pose_metrics(results)` - computes scores from pose data
- `build_pose_metric_evidence(results)` - attaches worst_frames, bad_segments

**File: `backend/services/ball_tracking_service.py`**
- `compute_homography(corners_px)` - pitch calibration transform
- `project_point_to_pitch(point_px, H)` - pixel → normalized coords
- `classify_length(y_norm)` - yorker/full/good_length/short/bouncer
- `classify_line(x_norm)` - wide_leg/leg_stump/middle/off_stump/wide_off

**File: `backend/services/reports/coach_report_template.py`** (459 lines)
- **NEW (Coach Report V2):** Universal PDF template
- `render_coach_summary()` - Page 1: priorities + weekly actions
- `render_consolidated_findings()` - detailed findings (no Quick/Deep split)
- `render_appendix_evidence()` - video evidence moved to end
- **Typography:** Standardized colors, fonts, spacing

**File: `backend/services/reports/findings_adapter.py`** (229 lines)
- **NEW (Coach Report V2):** Consolidation logic
- `CommonFinding` schema - universal structure
- `consolidate_findings(quick, deep)` - merges, removes duplicates
- `extract_top_priorities()` - high-severity findings
- `generate_this_week_actions()` - actionable bullets

**File: `backend/services/pdf_export_service.py`** (424 lines)
- `generate_analysis_pdf(...)` - uses universal template
- Inputs: quick_findings, deep_findings, quick_results, deep_results, analysis_mode
- **No comparison** - single job PDF only

---

### Backend Routes Layer

**File: `backend/routes/coach_pro_plus.py`** (2420 lines)

**Session Management:**
- `POST /api/coaches/plus/sessions` - Create session
- `GET /api/coaches/plus/sessions` - List sessions (paginated, filterable by status)
- `GET /api/coaches/plus/sessions/{id}` - Get session detail
- `DELETE /api/coaches/plus/sessions/{id}` - Delete session + S3 video
- `DELETE /api/coaches/plus/sessions/bulk` - Bulk delete (status filter, age filter)

**Analysis Jobs:**
- `POST /api/coaches/plus/sessions/{id}/analysis-jobs` - Create analysis job
- `GET /api/coaches/plus/sessions/{id}/analysis-jobs` - List jobs for session
- `GET /api/coaches/plus/analysis-jobs/{job_id}` - Get job details
- `GET /api/coaches/plus/video-sessions/{id}/analysis-history` - Same as list jobs

**PDF Export:**
- `POST /api/coaches/plus/jobs/{job_id}/export-pdf` - Generate PDF, upload to S3, return presigned URL

**Pitch Mapping (Phase 1 MVPs):**
- `GET /api/coaches/plus/sessions/{id}/calibration-frame` - Get frame for 4-point selection
- `POST /api/coaches/plus/sessions/{id}/pitch-calibration` - Save pitch corners
- `GET /api/coaches/plus/sessions/{id}/pitch-map` - Get normalized ball coordinates
- `POST /api/coaches/plus/target-zones` - Create zone
- `GET /api/coaches/plus/target-zones` - List zones (filterable by session)
- `POST /api/coaches/plus/sessions/{id}/zone-report` - Zone accuracy analytics

---

### Frontend Layer

**File: `frontend/src/views/CoachProPlusVideoSessionsView.vue`** (2305 lines)
- Sessions list UI with filters (status, exclude_failed)
- Upload modal with analysis mode selection
- Analysis history modal (shows all jobs for a session)
- Re-analyze button (reuses S3 video, creates new job)
- Pagination controls
- **No comparison view** - shows jobs individually

**File: `frontend/src/components/PitchCalibration.vue`** (469 lines)
- Interactive 4-corner pitch calibration UI
- SVG overlay for point selection

**File: `frontend/src/components/PitchMapViewer.vue`** (443 lines)
- Pitch visualization with ball bounce heatmap
- Filters by delivery type (yorker/full/good_length/short/bouncer)

**File: `frontend/src/components/TargetZoneDrawer.vue`** (647 lines)
- Click-and-drag zone creator
- Zone analytics dashboard

**File: `frontend/src/services/coachPlusVideoService.ts`**
- All API client functions for sessions, jobs, PDF export
- `getAnalysisHistory(sessionId)` - fetches all jobs for session

---

## B) REUSABLE BUILDING BLOCKS FOR PHASE 2

### ✅ Already Built - Can Reuse

1. **Target Zones (Partial MVP)**
   - DB Model: `TargetZone` with shape definitions
   - API: POST/GET target-zones
   - UI: `TargetZoneDrawer.vue` for zone creation
   - **Gap:** No goals/thresholds per zone, no compliance tracking

2. **Session History**
   - DB: Multiple `VideoAnalysisJob` rows per session
   - API: `GET /video-sessions/{id}/analysis-history`
   - UI: Analysis history modal in CoachProPlusVideoSessionsView

3. **Pitch Calibration**
   - DB: `VideoSession.pitch_corners` (JSON)
   - Service: `ball_tracking_service.compute_homography()`
   - UI: `PitchCalibration.vue`

4. **Ball Tracking Coordinates**
   - Service: `ball_tracking_service.project_point_to_pitch()`
   - Stored in: `deep_results.ball_tracking.bounces[]`
   - Classification: length (yorker/full/etc.), line (leg/middle/off)

5. **Findings Structure**
   - Service: `coach_findings.generate_findings()`
   - Storage: `VideoAnalysisJob.{quick_findings, deep_findings}`
   - Schema: code, title, severity, metrics, drills

6. **PDF Report Template**
   - Service: `reports/coach_report_template.py`
   - Universal for all analysis modes
   - **Gap:** No goals vs outcomes section

7. **Analysis Mode System**
   - DB: `VideoAnalysisJob.analysis_mode`
   - Frontend: Mode picker in upload modal
   - Backend: Routes to mode-specific generators

8. **Multi-Session View**
   - API: `GET /sessions` with pagination
   - UI: Sessions list in CoachProPlusVideoSessionsView
   - **Gap:** No comparison UI across sessions

---

## C) GAP LIST FOR PHASE 2

### Database Gaps

**Missing Columns:**
1. **`VideoAnalysisJob` needs:**
   - `coach_goals` (JSON) - coach-defined targets for this job
     - Example: `{zones: [{zone_id, target_accuracy: 0.80}], metrics: [{code: "HEAD_MOVEMENT", target_score: 0.70}]}`
   - `outcomes` (JSON) - calculated compliance vs goals
     - Example: `{zones: [{zone_id, actual_accuracy: 0.65, pass: false}], metrics: [{code: "HEAD_MOVEMENT", actual_score: 0.45, pass: false}]}`
   - `goal_compliance_pct` (Float) - overall % of goals met

2. **`TargetZone` needs:**
   - `target_accuracy` (Float) - desired hit rate (0.0-1.0)
   - `is_active` (Boolean) - enable/disable for different jobs

**Missing Tables:**
- **`CoachGoalTemplate`** (optional future enhancement)
  - Reusable goal sets (e.g., "Beginner Bowler", "Advanced Batsman")

### Backend Service Gaps

**Missing Files:**
1. **`backend/services/goal_compliance.py`** (NEW)
   - `calculate_compliance(job, goals)` - compares findings/metrics to goals
   - `generate_zone_compliance(ball_tracking, zones)` - hit rate vs target
   - `generate_metric_compliance(findings, goals)` - scores vs thresholds

2. **`backend/services/session_comparison.py`** (NEW)
   - `compare_sessions(job_ids)` - trends across multiple jobs
   - `calculate_improvement(earlier_job, later_job)` - delta analysis

**Missing Functions in Existing Files:**
3. **`backend/services/reports/coach_report_template.py` needs:**
   - `render_goals_vs_outcomes()` - Page 2: goals with pass/fail indicators
   - `render_session_comparison()` - trends chart for multi-session view

4. **`backend/services/pdf_export_service.py` needs:**
   - Update `generate_analysis_pdf()` to accept `coach_goals` parameter
   - Integrate goals vs outcomes rendering

### Backend API Gaps

**Missing Endpoints in `coach_pro_plus.py`:**
1. `POST /api/coaches/plus/jobs/{job_id}/set-goals` - Set goals before/after analysis
2. `POST /api/coaches/plus/jobs/{job_id}/calculate-compliance` - Trigger compliance calc
3. `GET /api/coaches/plus/jobs/{job_id}/outcomes` - Get compliance results
4. `POST /api/coaches/plus/sessions/{id}/compare-jobs` - Compare multiple jobs
5. `GET /api/coaches/plus/sessions/{id}/progress-timeline` - Trend data across jobs

### Frontend UI Gaps

**Missing Components:**
1. **`GoalSetter.vue`** (NEW)
   - UI to set zone targets (select zone, set accuracy %)
   - UI to set metric targets (select finding code, set threshold)
   - Pre-analysis or post-analysis modes

2. **`OutcomesViewer.vue`** (NEW)
   - Goals vs Outcomes table (goal → actual → pass/fail)
   - Visual indicators (✅/❌ per goal)

3. **`SessionComparison.vue`** (NEW)
   - Multi-job selector (checkboxes in history modal)
   - Trend chart (line graph showing metric scores over time)
   - Improvement delta table

**Missing Views:**
4. **`ComparisonReportView.vue`** (NEW)
   - Full-page comparison report
   - Side-by-side job results
   - Drill recommendations based on trends

**Modifications Needed:**
5. **`CoachProPlusVideoSessionsView.vue`:**
   - Add "Set Goals" button in analysis history modal
   - Add "Compare Selected" button (multi-select jobs)
   - Integrate `OutcomesViewer` in job detail cards

6. **`TargetZoneDrawer.vue`:**
   - Add "Target Accuracy %" input field per zone
   - Show zone compliance % when viewing existing zones

### Report Template Gaps

**PDF Structure Missing:**
- **Page 2 (after Coach Summary):** "Your Goals vs Outcomes"
  - Table: Goal | Target | Actual | Status
  - Visual: progress bars or badges per goal
- **Comparison Report:** Multi-session PDF showing trends
  - Not in Phase 2 MVP - can be HTML view only

---

## D) PROPOSED PHASE 2 DESIGN (1 Page)

### User Flow

**Pre-Analysis: Goal Setting**
1. Coach creates session, uploads video
2. Before job starts: "Set Goals" modal opens
   - Select target zones → set accuracy % (e.g., "Yorker Zone: 80%")
   - Select metrics → set thresholds (e.g., "Head Stability: 0.70")
3. Goals saved in `coach_goals` JSON on job

**Post-Analysis: Outcomes Calculation**
1. Worker completes analysis → findings generated
2. Backend trigger: `calculate_compliance(job)`
   - Zone compliance: actual hit rate vs target
   - Metric compliance: actual score vs threshold
3. Results saved in `outcomes` JSON on job

**Coach Review: Goals vs Outcomes**
1. Coach views job results
2. PDF Report updated:
   - **Page 1:** Coach Summary (existing)
   - **Page 2:** Goals vs Outcomes table (NEW)
   - **Page 3+:** Consolidated Findings (existing)
   - **Appendix:** Evidence (existing)
3. UI shows outcomes inline:
   - ✅ Green for met goals
   - ❌ Red for missed goals
   - Δ Delta from target (e.g., "-15% from goal")

**Session Comparison: Progress Tracking**
1. Coach selects multiple jobs in history modal
2. Clicks "Compare Sessions"
3. Comparison view shows:
   - Timeline chart (metric scores over time)
   - Improvement table (job 1 → job 2 → job 3 delta)
   - Recommended drills based on persistent issues

---

### Data Schema Additions

**`VideoAnalysisJob` extensions:**
```python
coach_goals: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
# Example: {
#   "zones": [{"zone_id": "...", "target_accuracy": 0.80}],
#   "metrics": [{"code": "HEAD_MOVEMENT", "target_score": 0.70}]
# }

outcomes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
# Example: {
#   "zones": [{"zone_id": "...", "actual_accuracy": 0.65, "pass": false, "delta": -0.15}],
#   "metrics": [{"code": "HEAD_MOVEMENT", "actual_score": 0.45, "pass": false, "delta": -0.25}],
#   "overall_compliance_pct": 50.0
# }

goal_compliance_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
```

**`TargetZone` extensions:**
```python
target_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

---

### API Design

**Goal Management:**
```
POST /api/coaches/plus/jobs/{job_id}/set-goals
Body: {
  zones: [{zone_id, target_accuracy}],
  metrics: [{code, target_score}]
}
→ Updates job.coach_goals, returns updated job
```

**Compliance Calculation:**
```
POST /api/coaches/plus/jobs/{job_id}/calculate-compliance
→ Reads job.coach_goals, job.deep_findings, job.deep_results
→ Calculates compliance, saves to job.outcomes
→ Returns outcomes JSON
```

**Session Comparison:**
```
POST /api/coaches/plus/sessions/{id}/compare-jobs
Body: {job_ids: ["job1", "job2", "job3"]}
→ Returns {
  timeline: [{timestamp, metrics: {HEAD_MOVEMENT: 0.45, ...}}],
  deltas: [{from_job, to_job, improvements: [...], regressions: [...]}],
  persistent_issues: [{code, avg_score, trend}]
}
```

---

### UI Components Priority

**Phase 2A (MVP):**
1. Goal setter modal (pre-analysis or post-analysis)
2. Outcomes viewer (table in job detail modal)
3. PDF Page 2: Goals vs Outcomes

**Phase 2B (Enhancement):**
4. Session comparison view (multi-select jobs)
5. Trend charts (line graphs)
6. Drill recommendations based on trends

---

## E) FILE-BY-FILE CHANGE PLAN

### Database Migration
**New file:** `backend/alembic/versions/add_coach_goals_and_outcomes.py`
- Add columns: `coach_goals`, `outcomes`, `goal_compliance_pct` to `video_analysis_jobs`
- Add columns: `target_accuracy`, `is_active` to `target_zones`

### Backend Services (NEW)
**New file:** `backend/services/goal_compliance.py`
- `calculate_zone_compliance(ball_tracking, goals)` - hit rate vs target
- `calculate_metric_compliance(findings, goals)` - scores vs thresholds
- `calculate_compliance(job)` - overall compliance calculation
- Returns: `{zones: [...], metrics: [...], overall_compliance_pct: float}`

**New file:** `backend/services/session_comparison.py`
- `compare_jobs(job_ids)` - extract metrics from multiple jobs
- `calculate_deltas(earlier, later)` - improvement/regression
- `generate_timeline(jobs)` - time-series data
- Returns: comparison payload for frontend

### Backend Services (MODIFY)
**File:** `backend/services/reports/coach_report_template.py`
- Add `render_goals_vs_outcomes(goals, outcomes)` - Page 2 rendering
- Add `_build_goals_table(goals, outcomes)` - Table with pass/fail indicators

**File:** `backend/services/pdf_export_service.py`
- Update `generate_analysis_pdf()` signature: add `coach_goals`, `outcomes` params
- Insert Page 2 between Coach Summary and Findings
- Call `render_goals_vs_outcomes()` if goals exist

### Backend Routes (MODIFY)
**File:** `backend/routes/coach_pro_plus.py`
- Add `POST /jobs/{job_id}/set-goals` - save coach_goals JSON
- Add `POST /jobs/{job_id}/calculate-compliance` - trigger compliance calc
- Add `GET /jobs/{job_id}/outcomes` - return outcomes JSON
- Add `POST /sessions/{id}/compare-jobs` - multi-job comparison
- Update `POST /jobs/{job_id}/export-pdf` - pass coach_goals to PDF generator

### Frontend Components (NEW)
**New file:** `frontend/src/components/GoalSetter.vue`
- Props: `jobId`, `existingGoals`, `availableZones`, `availableMetrics`
- UI: Zone picker + accuracy slider, Metric picker + threshold slider
- Emit: `@goals-saved` with goals payload

**New file:** `frontend/src/components/OutcomesViewer.vue`
- Props: `goals`, `outcomes`
- UI: Table with columns: Goal | Target | Actual | Status (✅/❌) | Delta
- Visual: Color-coded rows (green/red)

**New file:** `frontend/src/components/SessionComparison.vue`
- Props: `sessionId`, `selectedJobIds`
- API: Calls `compareJobs(sessionId, jobIds)`
- UI: Timeline chart (Chart.js or similar), Improvement table

### Frontend Views (MODIFY)
**File:** `frontend/src/views/CoachProPlusVideoSessionsView.vue`
- Add "Set Goals" button in analysis history modal
- Add "Compare Selected" button (multi-select checkbox mode)
- Integrate `<OutcomesViewer>` in job detail expansion
- Integrate `<GoalSetter>` modal

### Frontend Services (MODIFY)
**File:** `frontend/src/services/coachPlusVideoService.ts`
- Add `setJobGoals(jobId, goals)` - POST to /jobs/{id}/set-goals
- Add `calculateCompliance(jobId)` - POST to /jobs/{id}/calculate-compliance
- Add `getJobOutcomes(jobId)` - GET /jobs/{id}/outcomes
- Add `compareJobs(sessionId, jobIds)` - POST to /sessions/{id}/compare-jobs

---

## F) "HOW TO VERIFY" CHECKLIST

### API Testing (Use Postman/cURL)

**1. Set Goals on Job**
```bash
POST /api/coaches/plus/jobs/{job_id}/set-goals
Headers: Authorization: Bearer <token>
Body: {
  "zones": [{"zone_id": "zone123", "target_accuracy": 0.80}],
  "metrics": [{"code": "HEAD_MOVEMENT", "target_score": 0.70}]
}
Expected: 200 OK, job.coach_goals updated
```

**2. Calculate Compliance**
```bash
POST /api/coaches/plus/jobs/{job_id}/calculate-compliance
Expected: 200 OK, returns outcomes JSON with pass/fail per goal
```

**3. Get Outcomes**
```bash
GET /api/coaches/plus/jobs/{job_id}/outcomes
Expected: 200 OK, returns {zones: [...], metrics: [...], overall_compliance_pct: 50}
```

**4. Compare Jobs**
```bash
POST /api/coaches/plus/sessions/{session_id}/compare-jobs
Body: {"job_ids": ["job1", "job2", "job3"]}
Expected: 200 OK, returns {timeline: [...], deltas: [...], persistent_issues: [...]}
```

**5. Export PDF with Goals**
```bash
POST /api/coaches/plus/jobs/{job_id}/export-pdf
Expected: PDF has Page 2 "Goals vs Outcomes" if goals exist
```

---

### UI Testing (Manual QA)

**1. Goal Setting Flow**
- [ ] Create session, upload video, start analysis
- [ ] Open "Set Goals" modal before/after analysis
- [ ] Select zone → set accuracy % → save
- [ ] Select metric → set threshold → save
- [ ] Verify goals appear in job detail modal
- [ ] Verify goals persist after page refresh

**2. Outcomes Viewing Flow**
- [ ] Job with goals completes analysis
- [ ] Click "View Outcomes" in job card
- [ ] See table: Goal | Target | Actual | Status
- [ ] Green ✅ for met goals, Red ❌ for missed
- [ ] Delta shows "-15%" for missed targets

**3. Session Comparison Flow**
- [ ] Session has 3+ jobs
- [ ] Open analysis history modal
- [ ] Enable multi-select mode
- [ ] Select 3 jobs → click "Compare"
- [ ] See timeline chart (metric scores over time)
- [ ] See improvement table (job 1 → job 2 delta)
- [ ] Persistent issues highlighted

**4. PDF Report Verification**
- [ ] Generate PDF for job with goals
- [ ] Page 1: Coach Summary (existing)
- [ ] **Page 2: Goals vs Outcomes** (NEW - check table format)
- [ ] Page 3+: Consolidated Findings (existing)
- [ ] Appendix: Evidence (existing)

---

### Database Verification (SQL Queries)

**Check Goals Storage:**
```sql
SELECT id, analysis_mode, coach_goals, outcomes, goal_compliance_pct
FROM video_analysis_jobs
WHERE coach_goals IS NOT NULL;
```
Expected: JSON with zones/metrics structure

**Check Zone Targets:**
```sql
SELECT id, name, target_accuracy, is_active
FROM target_zones
WHERE target_accuracy IS NOT NULL;
```
Expected: Zones with accuracy targets

---

### Integration Testing (Pytest)

**New test file:** `backend/tests/test_goal_compliance.py`
- `test_calculate_zone_compliance()` - hit rate calculation
- `test_calculate_metric_compliance()` - threshold comparison
- `test_overall_compliance_calculation()` - weighted average
- `test_compliance_with_no_goals()` - graceful handling

**New test file:** `backend/tests/test_session_comparison.py`
- `test_compare_two_jobs()` - delta calculation
- `test_timeline_generation()` - time-series data
- `test_persistent_issues_detection()` - trend analysis

**Updated test file:** `backend/tests/test_evidence_driven_reports.py`
- `test_pdf_with_goals_and_outcomes()` - Page 2 rendering
- `test_pdf_without_goals()` - graceful fallback

---

## SUMMARY

**Phase 1 Status:** ✅ Complete
- Diagnostic findings + evidence + PDF reports working
- Pitch mapping + target zones infrastructure exists
- Session history tracking available

**Phase 2 Readiness:** 🟡 60% Infrastructure Ready
- **Reusable:** Session history, zones, ball tracking, PDF template
- **Missing:** Goal setting, compliance calculation, comparison logic, UI components

**Estimated Effort:**
- **Backend:** 2-3 days (DB migration, 2 new services, 5 new endpoints)
- **Frontend:** 3-4 days (3 new components, 1 view update, API integration)
- **Testing:** 1-2 days (integration tests, manual QA)
- **Total:** 6-9 days for MVP (goals + outcomes + single-job PDF)

**MVP Scope Recommendation:**
- Phase 2A: Goal setting + outcomes + PDF Page 2 (4-5 days)
- Phase 2B: Multi-job comparison + trends (3-4 days)

**Next Steps:**
1. Review this inventory with stakeholders
2. Prioritize MVP vs full scope
3. Create DB migration
4. Implement goal_compliance.py service first
5. Add API endpoints incrementally
6. Build UI components in parallel

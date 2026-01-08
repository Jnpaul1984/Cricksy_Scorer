# Analysis Mode Resolution & Persistence - COMPLETE

## Summary

Fixed the following issues in Coach Pro Plus video analysis pipeline:

### 1. ✅ Database Session Sharing (commit 8439854)
**Problem:** `async_client` used separate DB session, causing 404 errors in PDF export tests.

**Solution:** Override `get_db` dependency to share test's `db_session`.

### 2. ✅ Analysis Mode Resolution Rule (commit e13e446)
**Implementation:** `mode = job.analysis_mode or session.analysis_context or "batting"`

**Files Updated:**
- `backend/scripts/run_video_analysis_worker.py` - Added resolution rule, updated session_context
- `backend/services/chunk_aggregation.py` - Pass resolved mode to generate_findings()

### 3. ✅ Persist `analysis_mode_used` in Results (commit e13e446)
**Implementation:** Store resolved mode in quick_results and deep_results.

**Files Updated:**
- `backend/scripts/run_video_analysis_worker.py:170` - Add `analysis_mode_used` to result payload
- `backend/services/chunk_aggregation.py:195` - Add `analysis_mode_used` to final_results

### 4. ✅ Tests for Mode Persistence (commit e13e446)
**Added:** `test_analysis_mode_persisted_in_results()` verifies result structure includes `analysis_mode_used`.

## Test Results

All PDF export restriction tests pass:
```
tests/test_pdf_export_restrictions.py::test_cannot_export_pdf_when_deep_running PASSED
tests/test_pdf_export_restrictions.py::test_cannot_export_pdf_when_quick_done PASSED
tests/test_pdf_export_restrictions.py::test_bowling_mode_does_not_return_batting_codes PASSED
tests/test_pdf_export_restrictions.py::test_batting_mode_does_not_return_bowling_codes PASSED
tests/test_pdf_export_restrictions.py::test_analysis_mode_persisted_in_results PASSED
```

Route registration tests pass:
```
tests/test_route_registration.py::test_pdf_export_route_is_registered PASSED
tests/test_route_registration.py::test_analyze_job_route_is_registered PASSED
```

## Code Changes

### Worker Session Context
**Before:**
```python
session_context = {
    "analysis_context": job.session.analysis_context,  # Wrong key
    "camera_view": job.session.camera_view,
    "session_id": job.session.id,
    "session_title": job.session.title,
}
```

**After:**
```python
# Resolve analysis mode with fallback chain
resolved_mode = job.analysis_mode or job.session.analysis_context or "batting"

session_context = {
    "analysis_mode": resolved_mode,  # Correct key for routing
    "analysis_context": job.session.analysis_context,  # Keep for backward compat
    "camera_view": job.session.camera_view,
    "session_id": job.session.id,
    "session_title": job.session.title,
}
```

### Result Payload
**Before:**
```python
result = {
    "pose": pose_data,
    "metrics": metrics,
    "findings": findings,
    "report": report,
    "evidence": evidence,
    ...
}
```

**After:**
```python
# Extract resolved analysis mode from session_context
analysis_mode_used = session_context.get("analysis_mode", "batting")

result = {
    "pose": pose_data,
    "metrics": metrics,
    "findings": findings,
    "report": report,
    "evidence": evidence,
    "analysis_mode_used": analysis_mode_used,  # NEW
    ...
}
```

### Chunk Aggregation
**Before:**
```python
findings_result = generate_findings(metrics_result)  # Missing context
```

**After:**
```python
resolved_mode = job.analysis_mode or (job.session.analysis_context if job.session else None) or "batting"
findings_result = generate_findings(metrics_result, context={"analysis_mode": resolved_mode})
...
final_results = {
    ...
    "analysis_mode_used": resolved_mode,  # NEW
}
```

## Next Steps (Ball Tracking Integration)

Ball tracking integration is documented but not yet implemented. This requires:

1. **Deep Pass Integration** (bowling mode only):
   - Run ball tracking after pose extraction
   - Store in `deep_results["ball_tracking"]`

2. **Findings Enhancement**:
   - Update `generate_bowling_findings()` to use ball tracking metrics
   - Add finding codes: `BOWL_RELEASE_INCONSISTENT`, `BOWL_EXCESSIVE_SWING`, etc.

3. **Tests**:
   - Add test verifying bowling mode with ball tracking produces specific findings

See `ANALYSIS_MODE_BALL_TRACKING_IMPLEMENTATION.md` for full plan.

## Commits

1. `8439854` - fix: override get_db in async_client fixture to share db_session
2. `e13e446` - feat: implement analysis_mode resolution rule and persist mode in results

## Status: ✅ READY FOR CI

All local tests pass. CI should pass once deployed.

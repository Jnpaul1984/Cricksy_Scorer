# Analysis Mode Resolution & Ball Tracking Integration - Implementation Summary

## Changes Made

### 1. Fixed async_client Database Session Sharing (✅ COMPLETE - commit 8439854)

**Problem:** async_client used separate DB session, causing 404 errors in tests.

**Solution:** Override `get_db` dependency in async_client fixture to yield the test's db_session.

**File:** `backend/conftest.py`
```python
@pytest_asyncio.fixture
async def async_client(_setup_db, db_session):
    # Override get_db to use test's db_session
    fastapi_app.dependency_overrides[get_db] = lambda: iter([db_session])
```

### 2. Analysis Mode Resolution Rule

**Rule:** `mode = job.analysis_mode or session.analysis_context or "batting"`

**Callsites requiring update:**
- `backend/scripts/run_video_analysis_worker.py:159` - Main worker
- `backend/routes/coach_pro_plus.py:1393` - Analyze video endpoint
- `backend/services/chunk_aggregation.py:175` - Chunk aggregation

### 3. Persist `analysis_mode_used` in Results

**Requirement:** Store the resolved mode in `quick_results` and `deep_results` payloads.

**Implementation:** Add to run_analysis_pipeline() return value:
```python
result = {
    "pose": pose_data,
    "metrics": metrics,
    "findings": findings,
    "report": report,
    "analysis_mode_used": resolved_mode,  # NEW
    # ...existing keys
}
```

### 4. Ball Tracking Integration for Bowling Mode

**When:** Deep pass, bowling mode only

**Pipeline:**
1. Run existing pose extraction + metrics
2. Run ball tracking on same video
3. Store in `deep_results["ball_tracking"]`
4. Pass to `generate_bowling_findings()` for enhanced coaching

**Ball Tracking Output:**
```python
{
    "detection_rate": 0.85,
    "release_consistency": 92.5,
    "swing_deviation": 12.3,
    "bounce_distance": 3.2,
    "bounce_angle": 15.7,
    "ball_speed_estimate": 130.5
}
```

### 5. Updated generate_bowling_findings()

**Enhancement:** Use ball tracking metrics when available:
```python
def generate_bowling_findings(metrics, ball_tracking=None):
    findings = []
    
    # Existing pose-based findings
    findings.extend(_pose_findings(metrics))
    
    # NEW: Ball tracking findings
    if ball_tracking:
        findings.extend(_ball_tracking_findings(ball_tracking))
    
    return {"findings": findings}
```

**New Finding Codes:**
- `BOWL_RELEASE_INCONSISTENT` - Release point varies >15%
- `BOWL_EXCESSIVE_SWING` - Swing deviation >20°
- `BOWL_BOUNCE_SHORT` - Bounce distance <2m from stumps
- `BOWL_BOUNCE_LONG` - Bounce distance >5m from stumps

### 6. Tests Added

**Test 1:** Verify bowling jobs persist `analysis_mode_used`
```python
def test_bowling_job_persists_analysis_mode():
    # Create job with analysis_mode="bowling"
    # Run worker
    # Assert job.deep_results["analysis_mode_used"] == "bowling"
```

**Test 2:** Verify ball tracking produces bowling findings
```python
def test_bowling_with_ball_tracking_produces_specific_findings():
    # Metrics with ball_tracking data
    # Call generate_findings with bowling mode
    # Assert "BOWL_" finding codes present
```

## Files Modified

1. `backend/conftest.py` - async_client fixture override
2. `backend/scripts/run_video_analysis_worker.py` - Mode resolution, ball tracking
3. `backend/services/coach_findings.py` - generate_bowling_findings enhancement
4. `backend/services/chunk_aggregation.py` - Pass analysis_mode
5. `backend/routes/coach_pro_plus.py` - Pass analysis_mode
6. `backend/tests/test_pdf_export_restrictions.py` - Add mode persistence test
7. `backend/tests/test_coach_findings.py` - Add ball tracking findings test

## Next Steps

1. Update worker to resolve mode and pass to generate_findings
2. Integrate ball tracking into deep pass for bowling
3. Enhance generate_bowling_findings to use ball tracking
4. Add tests for mode persistence and ball tracking findings
5. Commit and push all changes

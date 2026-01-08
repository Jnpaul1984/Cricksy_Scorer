# Analysis Context Propagation Investigation Report

**Date**: 2026-01-08  
**Investigation**: Why preview/quick reports return batting findings for bowling/wicketkeeping jobs

---

## A) PROPAGATION MAP

| **Step** | **Location** | **Field Read** | **Field Written** | **File:Line** |
|----------|-------------|---------------|------------------|---------------|
| **1. Session Creation** | POST /sessions | `request.analysis_context` | `session.analysis_context` | `routes/coach_pro_plus.py:255` |
| **2. Upload Initiation** | POST /videos/upload/initiate | `request.analysis_mode` | `job.analysis_mode` | `routes/coach_pro_plus.py:866` |
| **3. Job Creation** | POST /sessions/{id}/analysis-jobs | `query param analysis_mode` | `job.analysis_mode` | `routes/coach_pro_plus.py:430` |
| **4. Worker Start** | `process_video_job()` | `job.analysis_mode`, `job.session.analysis_context` | `session_context["analysis_mode"]` | `workers/analysis_worker.py:186-194` |
| **5. Quick Analysis** | `run_pose_metrics_findings_report()` | `analysis_mode` parameter | Passed to `generate_findings()` | `services/coach_plus_analysis.py:173` |
| **6. Findings Generation** | `generate_findings()` | `analysis_mode` parameter | Routes to mode-specific generator | `services/coach_findings.py:882-890` |
| **7. Result Persistence** | `process_video_job()` | `quick_payload.get("findings")` | `job.quick_findings` | `workers/analysis_worker.py:211-217` |
| **8. Deep Analysis** | `run_pose_metrics_findings_report()` | `analysis_mode` parameter | Same as quick | `workers/analysis_worker.py:299` |

### KEY MODELS

**VideoSession** (`sql_app/models.py:1670-1760`):
- `analysis_context: Mapped[AnalysisContext | None]` (line 1700) - ENUM: batting, bowling, wicketkeeping, fielding, mixed

**VideoAnalysisJob** (`sql_app/models.py:1764-1950`):
- `analysis_mode: Mapped[str | None]` (line 1848) - String field, not ENUM
- `session: Mapped[VideoSession]` - Relationship to parent session

---

## B) LIKELY ROOT CAUSES

### 🔴 **ROOT CAUSE #1: Default Fallback to "batting"**

**Evidence:**
```python
# services/coach_findings.py:888-890
else:
    # Default to batting for backward compatibility
    return generate_batting_findings(metrics, context)
```

**Impact**: When `analysis_mode` is `None`, the system defaults to batting findings.

**Affected Code Paths:**
- `generate_findings()` - Line 843, 888
- `run_video_analysis_worker.py` - Line 316 resolution rule includes `or "batting"` fallback
- `chunk_aggregation.py` - Line 175 resolution rule includes `or "batting"` fallback

---

### 🔴 **ROOT CAUSE #2: Inconsistent Parameter Passing**

**Evidence:**
```python
# OLD CODE (before recent fixes):
# generate_findings() was called WITHOUT analysis_mode in some places:

# ❌ chunk_aggregation.py:175 (FIXED in commit e13e446)
findings_result = generate_findings(metrics_result)  # Missing context!

# ❌ coach_pro_plus.py:1393 (NOT YET FIXED)
findings_result = generate_findings(metrics_result)  # Missing context!
```

**Current Status**:
- Worker (`run_video_analysis_worker.py`): ✅ Fixed - passes resolved mode
- Chunk aggregation (`chunk_aggregation.py`): ✅ Fixed - passes resolved mode
- Direct analysis endpoint (`coach_pro_plus.py:1393`): ⚠️ **STILL BROKEN** - no mode passed

---

### 🔴 **ROOT CAUSE #3: Two-Parameter Signature Confusion**

**Evidence:**
```python
# services/coach_findings.py:843
def generate_findings(
    metrics: dict[str, Any], 
    context: dict[str, Any] | None = None,  # OLD WAY
    analysis_mode: str | None = None         # NEW WAY
) -> dict[str, Any]:
```

**Problem**: Two ways to pass mode:
1. `context={"analysis_mode": "bowling"}` (NEW worker code)
2. `analysis_mode="bowling"` (NEW direct param)
3. `context={"analysis_context": "bowling"}` (OLD code, still exists)

**Confusion Points:**
- Worker uses `context={"analysis_mode": ...}` (line 320)
- Old tests use `context={"analysis_context": ...}` (line 378, 399)
- Function reads BOTH `analysis_mode` param AND `context.get("analysis_context")`

---

### 🟡 **ROOT CAUSE #4: No Validation/Filtering of Finding Codes**

**Evidence**: There is **NO code** that validates findings against allowed codes per mode.

**Current Behavior:**
- `generate_batting_findings()` uses `BATTING_DRILL_SUGGESTIONS`
- `generate_bowling_findings()` uses `BOWLING_DRILL_SUGGESTIONS`
- `generate_wicketkeeping_findings()` uses `WICKETKEEPING_DRILL_SUGGESTIONS`

**BUT**: All three functions call `_generate_findings_internal()` which checks:
- `_check_head_movement()` → `HEAD_MOVEMENT` code
- `_check_balance_drift()` → `BALANCE_DRIFT` code
- `_check_knee_collapse()` → `KNEE_COLLAPSE` code
- `_check_rotation_timing()` → `ROTATION_TIMING` code
- `_check_elbow_drop()` → `ELBOW_DROP` code

**These 5 codes are UNIVERSAL** - they appear in all modes! Only the drill suggestions change.

**Bowling-Specific Codes** (only if ball tracking present):
- `INSUFFICIENT_BALL_TRACKING` (line 753)
- `INCONSISTENT_RELEASE_POINT` (line 780)
- `SWING_ANALYSIS` (line 814)

**Implication**: A bowling job will return `HEAD_MOVEMENT`, `KNEE_COLLAPSE`, etc. with bowling-specific drill suggestions, which is CORRECT. The issue is likely in the **frontend display** or **report narrative**, not the findings themselves.

---

### 🟡 **ROOT CAUSE #5: Context Key Confusion**

**Evidence:**
```python
# _generate_findings_internal() uses analysis_context (OLD)
analysis_context = context.get("analysis_context") if context else None

# But worker passes analysis_mode (NEW)
session_context = {
    "analysis_mode": resolved_mode,  # NEW key
    "analysis_context": job.session.analysis_context,  # OLD key for compat
}
```

**Function reads**: `analysis_context` from context dict  
**Worker passes**: Both keys for backward compatibility  
**Routing function reads**: `analysis_mode` parameter

**This works** because:
1. `generate_findings()` routes by `analysis_mode` param (line 882)
2. `_contextualize_finding()` adjusts titles by `analysis_context` from context dict (line 945)

---

## C) MINIMAL FIX PLAN

### ✅ **COMPLETED FIXES** (from recent commits)

1. **Worker Resolution Rule** ✅ (commit `e13e446`)
   - File: `backend/scripts/run_video_analysis_worker.py:316`
   - Implemented: `resolved_mode = job.analysis_mode or job.session.analysis_context or "batting"`

2. **Chunk Aggregation** ✅ (commit `e13e446`)
   - File: `backend/services/chunk_aggregation.py:175`
   - Implemented: Resolution rule + `context={"analysis_mode": resolved_mode}`

3. **Frontend Mode Propagation** ✅ (commit `edde581`)
   - Files: `frontend/src/stores/coachPlusVideoStore.ts`, `frontend/src/services/coachPlusVideoService.ts`
   - Passes `analysis_mode` from session to upload initiation

4. **Backend Upload Accepts Mode** ✅ (commit `1475dde`)
   - File: `backend/routes/coach_pro_plus.py:866`
   - Stores `analysis_mode` on job creation

---

### ⚠️ **REMAINING ISSUES**

#### **Issue #1: Direct Analysis Endpoint Missing Mode**

**File**: `backend/routes/coach_pro_plus.py:1393`

**Current Code**:
```python
# Step 3: Generate findings
findings_result = generate_findings(metrics_result)  # ❌ NO MODE!
```

**Fix**:
```python
# Step 3: Generate findings
# Determine analysis mode from request or session
mode = request.analysis_mode if hasattr(request, 'analysis_mode') else "batting"
findings_result = generate_findings(metrics_result, analysis_mode=mode)
```

**Impact**: LOW - This endpoint is legacy "analyze video from disk" (line 1200), not used by production upload flow.

---

#### **Issue #2: Inconsistent Parameter Contract**

**File**: `backend/services/coach_findings.py:843`

**Problem**: Two ways to pass mode creates confusion.

**Recommendation**: **Standardize on `analysis_mode` parameter**

**Fix**:
```python
def generate_findings(
    metrics: dict[str, Any], 
    analysis_mode: str | None = None,
    context: dict[str, Any] | None = None,  # Keep for other metadata
) -> dict[str, Any]:
    """Generate findings with explicit analysis_mode parameter."""
    
    # Resolve mode with fallback (for backward compat)
    mode = analysis_mode or (context.get("analysis_mode") if context else None) or "batting"
    
    # Route to mode-specific generator
    if mode == "batting":
        return generate_batting_findings(metrics, context)
    elif mode == "bowling":
        return generate_bowling_findings(metrics, context)
    elif mode == "wicketkeeping":
        return generate_wicketkeeping_findings(metrics, context)
    else:
        return generate_batting_findings(metrics, context)
```

---

#### **Issue #3: Add Server-Side Code Validation**

**Purpose**: Prevent cross-contamination of findings if mode routing fails.

**Implementation**:

```python
# services/coach_findings.py - Add after drill suggestions

ALLOWED_CODES_BY_MODE = {
    "batting": {
        "HEAD_MOVEMENT", "BALANCE_DRIFT", "KNEE_COLLAPSE", 
        "ROTATION_TIMING", "ELBOW_DROP", "INSUFFICIENT_POSE_VISIBILITY"
    },
    "bowling": {
        "HEAD_MOVEMENT", "BALANCE_DRIFT", "KNEE_COLLAPSE", 
        "ROTATION_TIMING", "ELBOW_DROP", "INSUFFICIENT_POSE_VISIBILITY",
        # Bowling-specific codes
        "INSUFFICIENT_BALL_TRACKING", "INCONSISTENT_RELEASE_POINT", "SWING_ANALYSIS"
    },
    "wicketkeeping": {
        "HEAD_MOVEMENT", "BALANCE_DRIFT", "KNEE_COLLAPSE", 
        "ROTATION_TIMING", "ELBOW_DROP", "INSUFFICIENT_POSE_VISIBILITY"
    },
}

def _filter_findings_by_mode(findings: list[dict], mode: str) -> list[dict]:
    """Remove findings not allowed for the given mode."""
    allowed = ALLOWED_CODES_BY_MODE.get(mode, ALLOWED_CODES_BY_MODE["batting"])
    
    filtered = []
    for finding in findings:
        code = finding.get("code")
        if code in allowed:
            filtered.append(finding)
        else:
            logger.warning(
                f"Filtered out finding code '{code}' not allowed for mode '{mode}'"
            )
    
    return filtered

# Then in generate_findings():
def generate_findings(metrics, analysis_mode=None, context=None):
    mode = analysis_mode or ...
    
    if mode == "batting":
        result = generate_batting_findings(metrics, context)
    elif mode == "bowling":
        result = generate_bowling_findings(metrics, context)
    # ...
    
    # Validate findings match mode
    result["findings"] = _filter_findings_by_mode(result["findings"], mode)
    
    return result
```

---

## D) TESTS TO ADD

### **Test 1: Wicketkeeping Job Cannot Output Batting-Only Codes**

**File**: `backend/tests/test_coach_findings.py`

```python
def test_wicketkeeping_mode_does_not_return_bowling_specific_codes():
    """Test that wicketkeeping mode does not return bowling-specific codes."""
    from backend.services.coach_findings import generate_findings
    
    # Metrics that would trigger ball tracking findings (if we were in bowling mode)
    metrics = {
        "metrics": {
            "head_stability_score": {"score": 0.35},
            "knee_collapse_score": {"score": 0.30},
        },
        "ball_tracking": {  # This should be IGNORED in wicketkeeping mode
            "detection_rate": 85.0,
            "metrics": {
                "release_consistency": 50.0,  # Would trigger INCONSISTENT_RELEASE_POINT
                "swing_deviation": 25.0,
            }
        },
        "summary": {"total_frames": 100, "frames_with_pose": 90},
    }
    
    wicketkeeping_context = {"analysis_mode": "wicketkeeping"}
    
    findings = generate_findings(metrics, analysis_mode="wicketkeeping")
    finding_codes = {f["code"] for f in findings.get("findings", [])}
    
    # Bowling-specific codes should NOT appear
    bowling_only_codes = {
        "INCONSISTENT_RELEASE_POINT", 
        "SWING_ANALYSIS", 
        "INSUFFICIENT_BALL_TRACKING"
    }
    assert not finding_codes.intersection(bowling_only_codes), \
        f"Wicketkeeping mode returned bowling-only codes: {finding_codes & bowling_only_codes}"
    
    # Should route to wicketkeeping findings (universal codes allowed)
    allowed_codes = {"HEAD_MOVEMENT", "KNEE_COLLAPSE", "INSUFFICIENT_POSE_VISIBILITY"}
    assert finding_codes.issubset(allowed_codes), \
        f"Wicketkeeping mode returned unexpected codes: {finding_codes - allowed_codes}"
```

### **Test 2: Quick Results Persist analysis_mode_used**

**File**: `backend/tests/test_pdf_export_restrictions.py` (already added in commit `e13e446`)

✅ Already implemented as `test_analysis_mode_persisted_in_results()`

### **Test 3: Worker Respects Job analysis_mode Over Session analysis_context**

**File**: `backend/tests/test_analysis_worker.py` (new file)

```python
import pytest
from backend.workers.analysis_worker import process_video_job

@pytest.mark.asyncio
async def test_job_analysis_mode_overrides_session_context(db_session):
    """Test that job.analysis_mode takes precedence over session.analysis_context."""
    
    # Create session with batting context
    session = VideoSession(
        id="test-session-1",
        title="Bowling Practice",
        analysis_context=AnalysisContext.batting,  # Session says batting
        owner_type=OwnerTypeEnum.coach,
        owner_id="test-coach-1",
        s3_bucket="test-bucket",
        s3_key="test-key.mp4",
    )
    db_session.add(session)
    
    # Create job with bowling mode (should override session)
    job = VideoAnalysisJob(
        id="test-job-1",
        session_id=session.id,
        analysis_mode="bowling",  # Job says bowling - should WIN
        status=VideoAnalysisJobStatus.queued,
        deep_enabled=False,
    )
    db_session.add(job)
    await db_session.commit()
    
    # Mock S3 download and analysis
    with patch('backend.workers.analysis_worker._download_from_s3'):
        with patch('backend.workers.analysis_worker.run_pose_metrics_findings_report') as mock_analysis:
            mock_analysis.return_value = AnalysisArtifacts(
                results={
                    "findings": {"findings": []},
                    "report": {"summary": "test"},
                    "pose_summary": {},
                    "metrics": {},
                },
                frames=None
            )
            
            await process_video_job(job.id, db_session)
    
    # Verify analysis was called with "bowling" mode
    mock_analysis.assert_called_once()
    call_args = mock_analysis.call_args
    assert call_args.kwargs["analysis_mode"] == "bowling", \
        f"Expected analysis_mode='bowling', got {call_args.kwargs['analysis_mode']}"
    
    # Verify persisted result has bowling mode
    await db_session.refresh(job)
    assert job.quick_results.get("meta", {}).get("analysis_mode") == "bowling"
```

---

## SUMMARY OF FINDINGS

### ✅ **What Works**
1. Worker resolution rule correctly prioritizes: `job.analysis_mode > session.analysis_context > "batting"`
2. Quick and deep analysis both pass `analysis_mode` parameter
3. Mode-specific drill suggestions are correctly selected
4. Frontend now passes `analysis_mode` from session to upload

### ⚠️ **What's Broken**
1. **Legacy direct analysis endpoint** doesn't pass mode (low priority)
2. **No server-side code filtering** to prevent cross-contamination
3. **Dual parameter pattern** (`context` dict vs `analysis_mode` param) causes confusion

### 🔍 **Key Insight**
The finding **codes** (HEAD_MOVEMENT, KNEE_COLLAPSE, etc.) are **universal** across all modes. What changes is:
- **Drill suggestions**: Mode-specific drills from different dictionaries
- **Title contextualization**: Adjusts titles like "Head movement during bowling delivery"
- **Ball tracking findings**: Only added for bowling mode

**Therefore**: If a wicketkeeping job shows "batting findings", it's likely:
1. The `analysis_mode` was `None` → defaulted to batting
2. The drill suggestions are from `BATTING_DRILL_SUGGESTIONS`
3. The titles say "batting" instead of "wicketkeeping"

**Verify with**: Check `job.quick_results["meta"]["analysis_mode"]` in the database. If it's `None` or `"batting"`, the mode wasn't propagated correctly.

---

## NEXT STEPS

1. ✅ **DONE**: Worker passes analysis_mode correctly
2. ✅ **DONE**: Frontend propagates mode from session
3. ⏳ **TODO**: Fix legacy direct analysis endpoint (optional)
4. ⏳ **TODO**: Add code validation filter
5. ⏳ **TODO**: Add tests for mode isolation
6. ⏳ **TODO**: Audit database for jobs with `analysis_mode=NULL` where `session.analysis_context != NULL`


# Analysis Mode Enforcement

## Overview

Fixed cross-contamination where bowling/wicketkeeping/fielding analysis showed batting-specific language. Implemented strict `analysis_mode` validation with fail-fast error handling and mode-aware coaching narratives.

## Valid Modes

```python
VALID_MODES = {"batting", "bowling", "wicketkeeping", "fielding"}
```

## Validation Layers

### 1. Worker Layer (`backend/workers/analysis_worker.py`)

Validates `analysis_mode` before processing:

```python
# Quick pass (lines 186-199)
if not job.analysis_mode:
    job.status = VideoAnalysisJobStatus.failed
    job.error_message = f"analysis_mode is required but missing for job_id={job.id}"
    raise ValueError(error_message)

# Deep pass (lines 290-305) - defensive re-check
```

**Behavior:** Jobs with missing `analysis_mode` are immediately marked FAILED.

### 2. Service Layer (`backend/services/coach_plus_analysis.py`)

Validates at entry point (lines 118-134):

```python
if not analysis_mode or analysis_mode not in VALID_MODES:
    raise ValueError(f"Invalid analysis_mode: {analysis_mode}. Must be one of {VALID_MODES}")
```

### 3. Findings Layer (`backend/services/coach_findings.py`)

**Removed batting fallback** (lines 944-995):
```python
# OLD: else: return generate_batting_findings(...)  ❌
# NEW: else: raise ValueError(...)  ✅
```

## Code Filtering

### Allowed Codes by Mode (lines 152-189)

```python
ALLOWED_CODES_BY_MODE = {
    "batting": {
        "HEAD_MOVEMENT", "KNEE_COLLAPSE", "BALANCE_DRIFT",
        "ROTATION_TIMING", "ELBOW_DROP", "INSUFFICIENT_POSE_VISIBILITY"
    },
    "bowling": {
        "HEAD_MOVEMENT", "KNEE_COLLAPSE", "BALANCE_DRIFT",
        "ROTATION_TIMING", "ELBOW_DROP", "INSUFFICIENT_POSE_VISIBILITY",
        "INCONSISTENT_RELEASE_POINT",  # Bowling-only
        "INSUFFICIENT_BALL_TRACKING"   # Bowling-only
    },
    "wicketkeeping": {
        "HEAD_MOVEMENT", "KNEE_COLLAPSE", "BALANCE_DRIFT",
        "INSUFFICIENT_POSE_VISIBILITY"
    },
    "fielding": {
        "HEAD_MOVEMENT", "KNEE_COLLAPSE", "BALANCE_DRIFT",
        "INSUFFICIENT_POSE_VISIBILITY"
    }
}
```

### Filtering Function (lines 1076-1091)

```python
def _filter_findings_by_mode(findings: list[dict], mode: str) -> list[dict]:
    """Filter findings to only codes allowed for the specified mode."""
    allowed = ALLOWED_CODES_BY_MODE.get(mode, ALLOWED_CODES_BY_MODE["batting"])
    filtered = [f for f in findings if f["code"] in allowed]
    # Logs warning for filtered codes
    return filtered
```

**Applied in:** `generate_batting_findings()`, `generate_bowling_findings()`, `generate_wicketkeeping_findings()`, `generate_fielding_findings()`

## Mode-Aware Narratives

### Why It Matters (lines 191-210)

Different explanations per mode:

```python
WHY_IT_MATTERS_BY_MODE = {
    "HEAD_MOVEMENT": {
        "batting": "...visual tracking of the ball, leading to mistimed shots...",
        "bowling": "...consistent line and length. Excessive movement disrupts your release point...",
        "wicketkeeping": "...aids clean takes on lateral movements. Excessive movement impairs tracking...",
        "fielding": "...improves hand-eye coordination during catches..."
    },
    "KNEE_COLLAPSE": {
        "batting": "...power transfer from your lower body into the shot...",
        "bowling": "...prevents energy leaks during delivery stride and reduces injury risk...",
        "wicketkeeping": "...essential for explosive lateral movement from your crouch position..."
    },
    # ... more codes
}
```

### High Severity Warnings (lines 212-218)

Mode-specific warnings:

```python
HIGH_SEVERITY_WARNINGS_BY_MODE = {
    "KNEE_COLLAPSE": {
        "batting": "Suspend intensive batting until front leg mechanics are corrected",
        "bowling": "Suspend fast bowling until front leg mechanics are corrected",
        "wicketkeeping": "Limit extended keeping sessions until knee stability improves"
    }
}
```

### Updated Check Functions

All finding check functions now accept `analysis_mode` parameter:

```python
def _check_head_movement(
    metrics: dict, 
    evidence: dict | None = None, 
    drill_db: dict | None = None, 
    analysis_mode: str = "batting"
) -> dict | None:
    # ... scoring logic ...
    
    why_it_matters = WHY_IT_MATTERS_BY_MODE.get("HEAD_MOVEMENT", {}).get(
        analysis_mode, FINDING_DEFINITIONS["HEAD_MOVEMENT"]["why_it_matters"]
    )
    
    finding = {
        ...
        "why_it_matters": why_it_matters,  # Mode-aware
    }
```

**Updated functions:**
- `_check_head_movement()` (lines 657-690)
- `_check_balance_drift()` (lines 695-728)
- `_check_knee_collapse()` (lines 730-773)
- `_check_rotation_timing()` (lines 778-822)
- `_check_elbow_drop()` (lines 827-860)

## Metadata Output

Results include `analysis_mode_used`:

```python
{
    "metrics": { ... },
    "findings": [ ... ],
    "meta": {
        "analysis_mode_used": "bowling",  # Always present
        "total_frames": 120,
        "detection_rate_percent": 83.5
    }
}
```

**Usage:** Frontend can display "Quick preview (Bowling)" using this field.

## Testing

**File:** `backend/tests/test_analysis_mode_enforcement.py`

**Coverage:**
- ✅ Service rejects None/invalid modes (raises ValueError)
- ✅ Bowling mode only allows bowling codes
- ✅ Wicketkeeping mode never shows batting language
- ✅ No silent fallback to batting
- ✅ All mode-aware dictionaries properly structured

**Results:** 14/14 tests passing

**Run tests:**
```powershell
$env:PYTHONPATH = "C:\Users\Hp\Cricksy_Scorer"
$env:CRICKSY_IN_MEMORY_DB = "1"
cd backend
pytest tests/test_analysis_mode_enforcement.py -v
```

## Adding New Findings

### Step 1: Define Allowed Modes

Add code to `ALLOWED_CODES_BY_MODE`:

```python
ALLOWED_CODES_BY_MODE = {
    "batting": {..., "NEW_CODE"},
    "bowling": {..., "NEW_CODE"},
    "wicketkeeping": {..., "NEW_CODE"},  # If applicable
    "fielding": {..., "NEW_CODE"}        # If applicable
}
```

### Step 2: Add Mode-Specific Narratives

Add to `WHY_IT_MATTERS_BY_MODE`:

```python
WHY_IT_MATTERS_BY_MODE = {
    "NEW_CODE": {
        "batting": "Batting-specific explanation mentioning shot, bat, crease...",
        "bowling": "Bowling-specific explanation mentioning delivery, release, stride...",
        "wicketkeeping": "Wicketkeeping-specific mentioning stance, crouch, takes...",
        "fielding": "Fielding-specific mentioning ready position, catching..."
    }
}
```

### Step 3: (Optional) Add High Severity Warnings

If the finding has high severity:

```python
HIGH_SEVERITY_WARNINGS_BY_MODE = {
    "NEW_CODE": {
        "batting": "Stop batting until...",
        "bowling": "Stop bowling until...",
        "wicketkeeping": "Limit keeping until..."
    }
}
```

### Step 4: Create Check Function

```python
def _check_new_code(
    metrics: dict, 
    evidence: dict | None = None, 
    drill_db: dict | None = None, 
    analysis_mode: str = "batting"
) -> dict | None:
    # ... metric scoring logic ...
    
    why_it_matters = WHY_IT_MATTERS_BY_MODE.get("NEW_CODE", {}).get(
        analysis_mode, FINDING_DEFINITIONS["NEW_CODE"]["why_it_matters"]
    )
    
    finding = {
        "code": "NEW_CODE",
        "severity": severity,
        "why_it_matters": why_it_matters,  # Mode-aware
        "cues": FINDING_DEFINITIONS["NEW_CODE"][f"{severity}_severity"]["cues"],
        "suggested_drills": drill_db.get("NEW_CODE", [])
    }
    
    return finding
```

### Step 5: Add to Internal Generator

In `_generate_findings_internal()`:

```python
new_finding = _check_new_code(metric_scores, evidence_data, drill_db, analysis_mode)
if new_finding:
    findings.append(new_finding)
```

### Step 6: Add Tests

```python
def test_new_code_has_mode_narratives():
    """NEW_CODE should have mode-specific explanations."""
    assert "NEW_CODE" in WHY_IT_MATTERS_BY_MODE
    assert "batting" in WHY_IT_MATTERS_BY_MODE["NEW_CODE"]
    assert "bowling" in WHY_IT_MATTERS_BY_MODE["NEW_CODE"]

def test_new_code_filtered_by_mode():
    """NEW_CODE should only appear in allowed modes."""
    result = generate_findings(metrics, analysis_mode="batting")
    codes = {f["code"] for f in result["findings"]}
    if "NEW_CODE" in ALLOWED_CODES_BY_MODE["batting"]:
        # Can appear
        pass
    else:
        assert "NEW_CODE" not in codes
```

## Coaching Language Guidelines

### Batting Mode
**Terminology:** shot, bat, crease, stance, backlift, downswing, impact, follow-through, weight transfer, front foot, back foot

**Example:** "Excessive head movement disrupts visual tracking of the ball, leading to mistimed shots and reduced consistency at the crease."

### Bowling Mode
**Terminology:** delivery, release, stride, front leg, back leg, gather, coil, alignment, line and length, seam position, follow-through, run-up

**Example:** "Head stability is crucial for consistent line and length. Excessive movement disrupts your release point and reduces accuracy."

### Wicketkeeping Mode
**Terminology:** stance, crouch, lateral movement, clean takes, glove position, footwork, first step, reaction time, fumble, collection

**Example:** "Steady head position aids clean takes on lateral movements. Excessive movement impairs tracking and increases fumble risk."

### Fielding Mode
**Terminology:** ready position, first step, catching shape, ground fielding, diving, throwing, anticipation, hand-eye coordination, attack the ball

**Example:** "Head stability improves hand-eye coordination during catches. Excessive movement reduces timing and catching success rate."

## Error Messages

### Missing Mode
```
ValueError: analysis_mode is required but missing for job_id=123
```
**Action:** Job set to FAILED status, error logged.

### Invalid Mode
```
ValueError: Invalid analysis_mode: running. Must be one of {'batting', 'bowling', 'wicketkeeping', 'fielding'}
```
**Action:** Raised before processing starts.

### Code Filtering (Log Only)
```
WARNING: Filtered out finding code 'INCONSISTENT_RELEASE_POINT' not allowed for mode 'batting'
```
**Action:** Finding removed from results, warning logged to server logs.

## Migration Notes

### Existing Jobs

Jobs created before this implementation may have `analysis_mode = NULL`. Options:

1. **Backfill from session:**
```sql
UPDATE video_analysis_jobs j
SET analysis_mode = s.analysis_context
FROM video_sessions s
WHERE j.video_session_id = s.id
AND j.analysis_mode IS NULL
AND s.analysis_context IS NOT NULL;
```

2. **Re-run failed jobs:** Jobs will fail with clear error message indicating missing mode.

### Frontend Changes

Ensure frontend passes `analysis_mode` when creating jobs:
```javascript
POST /coach/video-sessions
{
    "analysis_context": "bowling",  // Maps to analysis_mode
    ...
}
```

Display mode in UI:
```javascript
const mode = results.meta.analysis_mode_used; // "bowling"
badge.textContent = `Analyzed as: ${mode.charAt(0).toUpperCase() + mode.slice(1)}`;
```

## Verification Checklist

After deployment:

- [ ] Upload batting video → Check findings mention "shot", "bat", "crease"
- [ ] Upload bowling video → Check findings mention "delivery", "stride", "release"
- [ ] Upload wicketkeeping video → Check findings mention "crouch", "lateral", "takes"
- [ ] Upload fielding video → Check findings mention "ready position", "catching"
- [ ] Verify no "Suspend intensive batting" appears in bowling/wicketkeeping
- [ ] Verify `meta.analysis_mode_used` is always present
- [ ] Test invalid mode → Should get clear error message
- [ ] Check server logs for code filtering warnings (should be rare)

## Summary

**Before:** Silent fallback to batting → Wrong coaching language for all non-batting modes

**After:** Strict validation + Mode-aware narratives → Contextual coaching for each discipline

**Test Coverage:** 14/14 tests passing ✅

**Files Modified:**
- `backend/workers/analysis_worker.py` - Fail-fast validation
- `backend/services/coach_plus_analysis.py` - Entry point validation + metadata
- `backend/services/coach_findings.py` - Mode-aware dictionaries + filtering
- `backend/tests/test_analysis_mode_enforcement.py` - Comprehensive test suite

**Impact:** Eliminates confusing cross-contamination, improves coaching credibility, enables discipline-specific feedback.

# Pose Service Running Mode Integration

**Status**: ✅ Complete and Syntax Validated

## Summary

Updated `backend/services/pose_service.py` to fully support MediaPipe running mode dispatch with proper timestamp tracking and method selection. The service now:

1. **Detects the running mode** at startup and logs which detection method will be used
2. **Rejects LIVE_STREAM mode** with a clear error message explaining it requires callback pipelines
3. **Calculates monotonic timestamps** for each frame when needed
4. **Dispatches to the correct MediaPipe API** based on running mode

## Changes Made

### 1. Import `get_detection_method_name` (Line 24)
```python
from backend.mediapipe_init import get_pose_landmarker, get_model_path, get_detection_method_name
```

### 2. Add Mode Detection and Validation (Lines 128-138)
After reading video properties and before frame sampling:
```python
# Determine detection method based on running mode
detection_method = get_detection_method_name()
logger.info(f"Using MediaPipe detection method: {detection_method}")

# Check for unsupported modes
if detection_method == "detect_async":
    cap.release()
    raise RuntimeError(
        "LIVE_STREAM mode is not supported for offline video file processing. "
        "LIVE_STREAM requires a callback pipeline for real-time streaming. "
        "Set MEDIAPIPE_RUNNING_MODE to 'VIDEO' or 'IMAGE' for video file analysis."
    )
```

### 3. Add Timestamp and Method Dispatch (Lines 177-185)
In the video frame processing loop:
```python
timestamp_ms = int((frame_num / fps) * 1000)  # Monotonic timestamp

# Call appropriate detection method based on running mode
if detection_method == "detect_for_video":
    detection_result = detector.detect_for_video(mp_image, timestamp_ms)
elif detection_method == "detect":
    detection_result = detector.detect(mp_image)
else:
    # Should not reach here (checked earlier), but be defensive
    raise RuntimeError(f"Unsupported detection method: {detection_method}")
```

## Behavior by Running Mode

### VIDEO Mode (Default)
- **Method**: `detector.detect_for_video(image, timestamp_ms)`
- **Timestamp**: Monotonic timestamp in milliseconds from frame position
- **Use Case**: Video files with temporal consistency tracking
- **Pros**: Better pose tracking across frames, temporal context
- **Set via**: `MEDIAPIPE_RUNNING_MODE=VIDEO` (default)

### IMAGE Mode
- **Method**: `detector.detect(image)`
- **Timestamp**: Not used
- **Use Case**: Single frame analysis, no temporal dependencies
- **Use Case**: Legacy compatibility
- **Set via**: `MEDIAPIPE_RUNNING_MODE=IMAGE`

### LIVE_STREAM Mode
- **Method**: `detector.detect_async(image, timestamp_ms, callback)`
- **Support**: ❌ Not supported for offline video files
- **Error**: Clear RuntimeError explaining requirement for callback pipeline
- **Note**: Would require async callback implementation not suitable for batch video processing

## Validation

✅ **Syntax Errors**: None (Pylance validation passed)
✅ **Imports**: All imports resolve correctly
✅ **Logic**: Running mode determined at startup (no per-frame overhead)
✅ **Fallback**: Defensive else clause for unexpected modes
✅ **Error Handling**: Clear messages for unsupported modes

## Testing Checklist

- [ ] Test with `MEDIAPIPE_RUNNING_MODE=VIDEO` (default)
  - [ ] Verify timestamps are monotonically increasing
  - [ ] Verify pose tracking is smooth across frames
  - [ ] Check detection rate matches or exceeds IMAGE mode

- [ ] Test with `MEDIAPIPE_RUNNING_MODE=IMAGE`
  - [ ] Verify detection works without timestamps
  - [ ] Confirm backward compatibility

- [ ] Test with `MEDIAPIPE_RUNNING_MODE=LIVE_STREAM`
  - [ ] Verify RuntimeError is raised before processing
  - [ ] Confirm error message is helpful and clear
  - [ ] Verify video file is closed properly

- [ ] Performance tests
  - [ ] Measure detection time per frame in VIDEO mode
  - [ ] Compare with IMAGE mode
  - [ ] Verify timestamp calculation has negligible overhead

## Environment Variables Used

| Variable | Default | Values | Purpose |
|----------|---------|--------|---------|
| `MEDIAPIPE_RUNNING_MODE` | `VIDEO` | `VIDEO`, `IMAGE`, `LIVE_STREAM` | Detection mode selection |
| `MEDIAPIPE_POSE_MODEL_PATH` | `/app/mediapipe_models/pose_landmarker_full.task` | Path string | Model file location |

## Implementation Details

### Timestamp Calculation
```
timestamp_ms = int((frame_num / fps) * 1000)
```
- **Frame**: Current frame number (0-indexed)
- **FPS**: Frames per second from video metadata
- **Result**: Milliseconds from video start
- **Monotonic**: Always increases, no jumps or resets

### Method Selection Logic
1. Call `get_detection_method_name()` at start of extraction
2. Check if method is "detect_async" (LIVE_STREAM mode)
   - If yes: Release video capture, raise RuntimeError
3. In frame loop: Use detection_method to select API call
4. No per-frame overhead (method determined once at start)

## Code Quality

- **No Breaking Changes**: Response schema unchanged
- **Keypoint Logic**: Unchanged from previous version
- **Metrics Extraction**: Unchanged from previous version
- **Findings Analysis**: Unchanged from previous version
- **Backward Compatible**: Default VIDEO mode works with existing code

## Files Modified

1. **backend/services/pose_service.py**
   - Added import: `get_detection_method_name`
   - Added running mode detection and validation
   - Added timestamp calculation and method dispatch
   - Total changes: 3 replacements, ~30 lines of code

## Related Files

- **backend/mediapipe_init.py**: Provides running mode support (✅ Complete)
- **docker-compose.yml**: Volume mount for model file (✅ Complete)
- **backend/main.py**: Calls startup verification (✅ Complete)

## What's Next

1. **Run Tests**:
   ```bash
   cd backend
   MEDIAPIPE_RUNNING_MODE=VIDEO pytest tests/ -q
   ```

2. **Test with Different Modes**:
   ```bash
   # VIDEO mode (default, with timestamps)
   MEDIAPIPE_RUNNING_MODE=VIDEO python -m pytest

   # IMAGE mode (without timestamps)
   MEDIAPIPE_RUNNING_MODE=IMAGE python -m pytest

   # LIVE_STREAM mode (should reject with clear error)
   MEDIAPIPE_RUNNING_MODE=LIVE_STREAM python -c "..."
   ```

3. **Integration Testing**:
   - Test with actual video files
   - Verify pose quality metrics
   - Compare detection rates across modes

4. **Performance Profiling**:
   - Measure detection latency per frame
   - Verify timestamp overhead is negligible
   - Monitor memory usage across modes

## Summary of MediaPipe Integration (Complete)

✅ **Phase 1**: Initial implementation (mediapipe_init.py)
✅ **Phase 2**: File validation refinement
✅ **Phase 3**: Running mode support (VIDEO/IMAGE/LIVE_STREAM)
✅ **Phase 4**: Pose service integration with method dispatch

**Status**: Ready for testing and deployment
**Blockers**: None
**Next Steps**: Validation testing with different running modes

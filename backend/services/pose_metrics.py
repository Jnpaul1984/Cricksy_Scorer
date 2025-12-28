"""
Cricket Coaching Metrics from Pose Keypoints

Computes biomechanical metrics (head stability, balance, knee brace, etc.)
from 2D pose keypoint sequences using pure Python/numpy.

No external ML libs required. Handles missing keypoints gracefully.
"""

from __future__ import annotations

import logging
import math
from typing import Any, cast

logger = logging.getLogger(__name__)


# =========================================================================
# Evidence Markers (Coach Pro Plus)
# =========================================================================

# Bad thresholds are used for evidence markers (per-frame series). These are
# intentionally conservative and align with the MVP thresholds used in findings.
EVIDENCE_BAD_THRESHOLDS: dict[str, float] = {
    "head_stability_score": 0.60,
    "balance_drift_score": 0.55,
    "front_knee_brace_score": 0.50,
    # NOTE: the aggregate metric is lag seconds; per-frame proxy score is a 0..1
    # hip/shoulder separation angle score (higher is better).
    "hip_shoulder_separation_timing": 0.35,
    "elbow_drop_score": 0.55,
}

EVIDENCE_WORST_FRAMES_COUNT = 5
EVIDENCE_MERGE_GAP_FRAMES = 3


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    try:
        if isinstance(value, str):
            v = float(value)
            return v if math.isfinite(v) else None
    except Exception:
        return None
    return None


def _frame_identity(frame: dict[str, Any], fallback_index: int) -> tuple[int, float | None]:
    """Return (frame_num, timestamp_s) for a pose frame.

    Supports multiple schema versions (frame_num/frame_id/frame_index).
    """
    frame_num = (
        frame.get("frame_num")
        if frame.get("frame_num") is not None
        else frame.get("frame_id")
        if frame.get("frame_id") is not None
        else frame.get("frame_index")
        if frame.get("frame_index") is not None
        else fallback_index
    )

    try:
        frame_num_int = int(fallback_index) if frame_num is None else int(str(frame_num))
    except Exception:
        frame_num_int = int(fallback_index)

    timestamp_s = _to_float(frame.get("timestamp"))
    if timestamp_s is None:
        timestamp_s = _to_float(frame.get("t"))
    return frame_num_int, timestamp_s


def _looks_detected(frame: dict[str, Any]) -> bool:
    """Best-effort detection flag across schema versions."""
    if bool(frame.get("pose_detected")) or bool(frame.get("detected")):
        return True

    # Some fixtures omit detected flags; treat non-empty keypoints/landmarks as detected.
    keypoints = frame.get("keypoints")
    if isinstance(keypoints, dict) and len(keypoints) > 0:
        return True
    landmarks = frame.get("landmarks")
    return isinstance(landmarks, list) and len(landmarks) > 0


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _score_from_head_movement(movement: float) -> float:
    # Match compute_head_stability_score scale (movement ~0.3 => 0)
    return _clamp01(1.0 - (movement / 0.3))


def _score_from_balance_drift(drift: float) -> float:
    # Match compute_balance_drift_score scale (drift ~0.2 => 0)
    return _clamp01(1.0 - (drift / 0.2))


def _score_from_knee_angle(angle_deg: float) -> float:
    # Match compute_front_knee_brace_score scale (80 => 0, 180 => 1)
    return _clamp01((angle_deg - 80.0) / 100.0)


def _score_from_elbow_drop(drop: float) -> float:
    # Match compute_elbow_drop_score scale
    return _clamp01((drop - 0.05) / 0.25)


def _score_from_separation_angle(separation_deg: float) -> float:
    # Per-frame proxy: larger hip/shoulder separation angle is better.
    # 0..90 degrees mapped to 0..1.
    return _clamp01(abs(separation_deg) / 90.0)


def _compute_per_frame_series(frames: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Compute per-frame score series for each metric.

    Returns per metric:
      {
        "scores": [float...],
        "frame_nums": [int...],
        "timestamps_s": [float|None...]
      }

    Series includes only frames where pose is detected and required keypoints exist.
    """

    series: dict[str, dict[str, Any]] = {
        k: {"scores": [], "frame_nums": [], "timestamps_s": []} for k in EVIDENCE_BAD_THRESHOLDS
    }

    # Head stability (movement between consecutive valid nose frames)
    prev_nose: list[float] | None = None
    for idx, frame in enumerate(frames):
        if not _looks_detected(frame):
            continue

        frame = ensure_keypoints_dict(frame)
        keypoints = frame.get("keypoints", {})
        shoulder_width = normalize_by_shoulder_width(keypoints)
        nose = get_keypoint_value(keypoints, "nose")
        if nose is None or shoulder_width < 0.01:
            continue

        movement = 0.0
        if prev_nose is not None:
            movement = distance(prev_nose, nose) / shoulder_width
        prev_nose = nose

        score = _score_from_head_movement(movement)
        frame_num, ts = _frame_identity(frame, idx)
        series["head_stability_score"]["scores"].append(score)
        series["head_stability_score"]["frame_nums"].append(frame_num)
        series["head_stability_score"]["timestamps_s"].append(ts)

    # Balance drift
    for idx, frame in enumerate(frames):
        if not _looks_detected(frame):
            continue
        frame = ensure_keypoints_dict(frame)
        keypoints = frame.get("keypoints", {})

        left_hip = get_keypoint_value(keypoints, "left_hip")
        right_hip = get_keypoint_value(keypoints, "right_hip")
        left_ankle = get_keypoint_value(keypoints, "left_ankle")
        right_ankle = get_keypoint_value(keypoints, "right_ankle")
        if not (left_hip and right_hip and left_ankle and right_ankle):
            continue

        hip_mid = [(left_hip[0] + right_hip[0]) / 2, (left_hip[1] + right_hip[1]) / 2]
        ankle_mid = [(left_ankle[0] + right_ankle[0]) / 2, (left_ankle[1] + right_ankle[1]) / 2]
        drift = abs(hip_mid[0] - ankle_mid[0])

        score = _score_from_balance_drift(drift)
        frame_num, ts = _frame_identity(frame, idx)
        series["balance_drift_score"]["scores"].append(score)
        series["balance_drift_score"]["frame_nums"].append(frame_num)
        series["balance_drift_score"]["timestamps_s"].append(ts)

    # Front knee brace
    for idx, frame in enumerate(frames):
        if not _looks_detected(frame):
            continue
        frame = ensure_keypoints_dict(frame)
        keypoints = frame.get("keypoints", {})

        angles: list[float] = []

        left_hip = get_keypoint_value(keypoints, "left_hip")
        left_knee = get_keypoint_value(keypoints, "left_knee")
        left_ankle = get_keypoint_value(keypoints, "left_ankle")
        if left_hip and left_knee and left_ankle:
            angles.append(angle(left_hip, left_knee, left_ankle))

        right_hip = get_keypoint_value(keypoints, "right_hip")
        right_knee = get_keypoint_value(keypoints, "right_knee")
        right_ankle = get_keypoint_value(keypoints, "right_ankle")
        if right_hip and right_knee and right_ankle:
            angles.append(angle(right_hip, right_knee, right_ankle))

        if not angles:
            continue

        # Use the worst (minimum) angle for the frame
        min_angle = min(angles)
        score = _score_from_knee_angle(min_angle)
        frame_num, ts = _frame_identity(frame, idx)
        series["front_knee_brace_score"]["scores"].append(score)
        series["front_knee_brace_score"]["frame_nums"].append(frame_num)
        series["front_knee_brace_score"]["timestamps_s"].append(ts)

    # Hip/shoulder separation timing (per-frame proxy score)
    for idx, frame in enumerate(frames):
        if not _looks_detected(frame):
            continue
        frame = ensure_keypoints_dict(frame)
        keypoints = frame.get("keypoints", {})

        left_hip = get_keypoint_value(keypoints, "left_hip")
        right_hip = get_keypoint_value(keypoints, "right_hip")
        left_shoulder = get_keypoint_value(keypoints, "left_shoulder")
        right_shoulder = get_keypoint_value(keypoints, "right_shoulder")
        if not (left_hip and right_hip and left_shoulder and right_shoulder):
            continue

        hip_ang = line_angle(left_hip, right_hip)
        shoulder_ang = line_angle(left_shoulder, right_shoulder)
        sep = shoulder_ang - hip_ang
        score = _score_from_separation_angle(sep)
        frame_num, ts = _frame_identity(frame, idx)
        series["hip_shoulder_separation_timing"]["scores"].append(score)
        series["hip_shoulder_separation_timing"]["frame_nums"].append(frame_num)
        series["hip_shoulder_separation_timing"]["timestamps_s"].append(ts)

    # Elbow drop
    for idx, frame in enumerate(frames):
        if not _looks_detected(frame):
            continue
        frame = ensure_keypoints_dict(frame)
        keypoints = frame.get("keypoints", {})

        drops: list[float] = []

        left_shoulder = get_keypoint_value(keypoints, "left_shoulder")
        left_elbow = get_keypoint_value(keypoints, "left_elbow")
        if left_shoulder and left_elbow:
            drops.append(left_elbow[1] - left_shoulder[1])

        right_shoulder = get_keypoint_value(keypoints, "right_shoulder")
        right_elbow = get_keypoint_value(keypoints, "right_elbow")
        if right_shoulder and right_elbow:
            drops.append(right_elbow[1] - right_shoulder[1])

        if not drops:
            continue

        avg_drop = sum(drops) / len(drops)
        score = _score_from_elbow_drop(avg_drop)
        frame_num, ts = _frame_identity(frame, idx)
        series["elbow_drop_score"]["scores"].append(score)
        series["elbow_drop_score"]["frame_nums"].append(frame_num)
        series["elbow_drop_score"]["timestamps_s"].append(ts)

    return series


def build_pose_metric_evidence(
    pose_data: dict[str, Any],
    metrics_result: dict[str, Any],
) -> dict[str, Any]:
    """Build coach-friendly evidence markers from per-frame metric series.

    Output shape:
      results.evidence[metric_key] = {
        threshold: number,
        worst_frames: [{frame_num, timestamp_s?, score}],
        bad_segments: [{start_frame, end_frame, start_timestamp_s?, end_timestamp_s?, min_score}]
      }
    """

    frames: list[dict[str, Any]] = []
    if isinstance(pose_data.get("frames"), list):
        frames = cast(list[dict[str, Any]], pose_data.get("frames"))
    elif isinstance(pose_data.get("frames_data"), list):
        frames = cast(list[dict[str, Any]], pose_data.get("frames_data"))

    per_frame = _compute_per_frame_series(frames)

    # Attach per-frame series to metrics_result (extend only, do not remove)
    metrics_block = metrics_result.get("metrics")
    if isinstance(metrics_block, dict):
        for metric_key, data in per_frame.items():
            metric_obj = metrics_block.get(metric_key)
            if isinstance(metric_obj, dict):
                metric_obj.setdefault("per_frame_scores", data["scores"])
                metric_obj.setdefault("per_frame_frame_nums", data["frame_nums"])
                metric_obj.setdefault("per_frame_timestamps_s", data["timestamps_s"])

    evidence: dict[str, Any] = {}
    for metric_key, threshold in EVIDENCE_BAD_THRESHOLDS.items():
        scores = per_frame.get(metric_key, {}).get("scores", [])
        frame_nums = per_frame.get(metric_key, {}).get("frame_nums", [])
        timestamps_s = per_frame.get(metric_key, {}).get("timestamps_s", [])

        # Worst frames (lowest scores)
        indexed = list(enumerate(scores))
        indexed.sort(key=lambda x: x[1])
        worst_frames = []
        for i, score in indexed[:EVIDENCE_WORST_FRAMES_COUNT]:
            frame_num = int(frame_nums[i]) if i < len(frame_nums) else int(i)
            ts = _to_float(timestamps_s[i]) if i < len(timestamps_s) else None
            worst_frames.append(
                {
                    "frame_num": frame_num,
                    **({"timestamp_s": ts} if ts is not None else {}),
                    "score": float(score),
                }
            )

        # Bad segments: contiguous runs where score < threshold, merged if gaps <= 3 frames
        raw_segments: list[dict[str, Any]] = []
        seg_start: int | None = None
        seg_min = 1.0
        for i, score in enumerate(scores):
            if score < threshold:
                if seg_start is None:
                    seg_start = i
                    seg_min = float(score)
                else:
                    seg_min = min(seg_min, float(score))
            else:
                if seg_start is not None:
                    raw_segments.append({"start": seg_start, "end": i - 1, "min": seg_min})
                    seg_start = None
                    seg_min = 1.0
        if seg_start is not None:
            raw_segments.append({"start": seg_start, "end": len(scores) - 1, "min": seg_min})

        merged: list[dict[str, Any]] = []
        for seg in raw_segments:
            if not merged:
                merged.append(seg)
                continue
            prev = merged[-1]
            gap = int(seg["start"]) - int(prev["end"]) - 1
            if gap <= EVIDENCE_MERGE_GAP_FRAMES:
                prev["end"] = seg["end"]
                prev["min"] = min(float(prev["min"]), float(seg["min"]))
            else:
                merged.append(seg)

        bad_segments: list[dict[str, Any]] = []
        for seg in merged:
            s_idx = int(seg["start"])
            e_idx = int(seg["end"])
            start_frame = int(frame_nums[s_idx]) if s_idx < len(frame_nums) else int(s_idx)
            end_frame = int(frame_nums[e_idx]) if e_idx < len(frame_nums) else int(e_idx)
            start_ts = _to_float(timestamps_s[s_idx]) if s_idx < len(timestamps_s) else None
            end_ts = _to_float(timestamps_s[e_idx]) if e_idx < len(timestamps_s) else None
            bad_segments.append(
                {
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                    **({"start_timestamp_s": start_ts} if start_ts is not None else {}),
                    **({"end_timestamp_s": end_ts} if end_ts is not None else {}),
                    "min_score": float(seg["min"]),
                }
            )

        evidence[metric_key] = {
            "threshold": float(threshold),
            "worst_frames": worst_frames,
            "bad_segments": bad_segments,
        }

    return evidence


# ============================================================================
# Helper Functions
# ============================================================================


def angle(a: list[float], b: list[float], c: list[float]) -> float:
    """
    Compute angle ABC in degrees (angle at point B).

    Args:
        a: [x, y] point A
        b: [x, y] point B (vertex)
        c: [x, y] point C

    Returns:
        Angle in degrees [0, 180]
    """
    if len(a) < 2 or len(b) < 2 or len(c) < 2:
        return 0.0

    ax, ay = a[0], a[1]
    bx, by = b[0], b[1]
    cx, cy = c[0], c[1]

    # Vectors BA and BC
    ba_x, ba_y = ax - bx, ay - by
    bc_x, bc_y = cx - bx, cy - by

    # Dot product and magnitudes
    dot_product = ba_x * bc_x + ba_y * bc_y
    mag_ba = math.sqrt(ba_x * ba_x + ba_y * ba_y)
    mag_bc = math.sqrt(bc_x * bc_x + bc_y * bc_y)

    if mag_ba == 0 or mag_bc == 0:
        return 0.0

    # Cosine of angle
    cos_angle = dot_product / (mag_ba * mag_bc)
    cos_angle = max(-1.0, min(1.0, cos_angle))  # Clamp to [-1, 1]

    # Angle in radians, convert to degrees
    angle_rad = math.acos(cos_angle)
    angle_deg = math.degrees(angle_rad)

    return angle_deg


def line_angle(p1: list[float], p2: list[float]) -> float:
    """
    Compute angle of line from p1 to p2 relative to horizontal (in degrees).

    Args:
        p1: [x, y] point 1
        p2: [x, y] point 2

    Returns:
        Angle in degrees [-180, 180]
    """
    if len(p1) < 2 or len(p2) < 2:
        return 0.0

    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad)

    return angle_deg


def distance(p1: list[float], p2: list[float]) -> float:
    """
    Compute Euclidean distance between two points.

    Args:
        p1: [x, y] point 1
        p2: [x, y] point 2

    Returns:
        Distance
    """
    if len(p1) < 2 or len(p2) < 2:
        return 0.0

    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    return math.sqrt(dx * dx + dy * dy)


def smooth_series(values: list[float], window: int = 3) -> list[float]:
    """
    Simple moving average smoothing.

    Args:
        values: List of numeric values
        window: Smoothing window size (default 3)

    Returns:
        Smoothed list (same length as input, padded at edges)
    """
    if len(values) == 0:
        return []

    if window < 1:
        window = 1

    result = []
    half_window = window // 2

    for i in range(len(values)):
        start = max(0, i - half_window)
        end = min(len(values), i + half_window + 1)
        avg = sum(values[start:end]) / (end - start)
        result.append(avg)

    return result


def normalize_by_shoulder_width(keypoints: dict[str, list[float]]) -> float:
    """
    Get shoulder width for normalization.

    Args:
        keypoints: Dict of keypoint name -> [x, y, confidence] or {"x": ..., "y": ..., "visibility": ...}

    Returns:
        Shoulder width (distance between shoulders), or 0.1 if missing
    """
    left_shoulder = keypoints.get("left_shoulder")
    right_shoulder = keypoints.get("right_shoulder")

    if not left_shoulder or not right_shoulder:
        return 0.1  # Default fallback

    # Handle both dict and list formats
    if isinstance(left_shoulder, (list, tuple)):
        left_coords = left_shoulder[:2]
    else:
        left_coords = [left_shoulder.get("x"), left_shoulder.get("y")]

    if isinstance(right_shoulder, (list, tuple)):
        right_coords = right_shoulder[:2]
    else:
        right_coords = [right_shoulder.get("x"), right_shoulder.get("y")]

    # Filter out None values
    if any(c is None for c in left_coords) or any(c is None for c in right_coords):
        return 0.1

    width = distance(left_coords, right_coords)

    # Return at least 0.1 to avoid division by zero
    return max(0.1, width)


def get_keypoint_value(keypoints: dict[str, Any], name: str) -> list[float] | None:
    """
    Get keypoint with confidence filtering.

    Args:
        keypoints: Dict of keypoint name -> [x, y, confidence] or {"x": ..., "y": ..., "visibility": ...}
        name: Keypoint name

    Returns:
        [x, y] if present and confidence > 0.5, else None
    """
    kp = keypoints.get(name)
    if kp is None:
        return None

    # Handle dict format: {"x": float, "y": float, "z": float, "visibility": float}
    if isinstance(kp, dict):
        x = kp.get("x")
        y = kp.get("y")
        visibility = kp.get("visibility")

        if x is None or y is None:
            return None

        if visibility is not None and visibility < 0.5:
            return None

        return [float(x), float(y)]

    # Handle list format: [x, y, confidence, ...]
    if isinstance(kp, (list, tuple)):
        if len(kp) < 2:
            return None

        # Confidence is at index 2, visibility might be at index 3
        confidence = kp[2] if len(kp) > 2 else None
        if confidence is not None and confidence < 0.5:
            return None

        return [float(kp[0]), float(kp[1])]

    return None


def ensure_keypoints_dict(frame: dict[str, Any]) -> dict[str, Any]:
    """
    Ensure frame has keypoints dict; convert from landmarks list if needed.

    Args:
        frame: Frame dict potentially with only landmarks list

    Returns:
        Updated frame with keypoints dict guaranteed to exist

    Note:
        - If frame["keypoints"] exists and is dict, returns frame as-is
        - If only frame["landmarks"] exists, converts to keypoints dict
        - Handles landmarks as both list of dicts and list of coordinate values
        - If both missing, returns frame unchanged (graceful fallback)
    """
    # If keypoints already a dict, we're good
    if isinstance(frame.get("keypoints"), dict):
        return frame

    # If landmarks list exists but keypoints doesn't, convert
    landmarks = frame.get("landmarks")
    if isinstance(landmarks, list) and landmarks:
        # Import KEYPOINT_NAMES from mediapipe_init if available
        try:
            from backend.mediapipe_init import KEYPOINT_NAMES
        except ImportError:
            # Fallback if import not available
            KEYPOINT_NAMES = [
                "nose",
                "left_eye",
                "right_eye",
                "left_ear",
                "right_ear",
                "left_shoulder",
                "right_shoulder",
                "left_elbow",
                "right_elbow",
                "left_wrist",
                "right_wrist",
                "left_hip",
                "right_hip",
                "left_knee",
                "right_knee",
                "left_ankle",
                "right_ankle",
                "left_heel",
                "right_heel",
                "left_foot_index",
                "right_foot_index",
                "left_eye_inner",
                "right_eye_inner",
                "left_eye_outer",
                "right_eye_outer",
                "left_mouth_corner",
                "right_mouth_corner",
                "left_mouth_center",
                "right_mouth_center",
                "left_pinky",
                "right_pinky",
                "left_index",
                "right_index",
            ]

        # Convert landmarks list to keypoints dict
        # Landmarks can be list of dicts ({"x": ..., "y": ...}) or list of lists/tuples
        keypoints_dict = {}
        for i, landmark in enumerate(landmarks):
            if i < len(KEYPOINT_NAMES):
                keypoints_dict[KEYPOINT_NAMES[i]] = landmark

        frame["keypoints"] = keypoints_dict

    return frame


# ============================================================================
# Metric Calculation Functions
# ============================================================================


def compute_head_stability_score(frames: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute head stability score [0,1] based on nose movement over time.

    Normalize by shoulder width each frame to account for depth variation.

    Args:
        frames: List of frame dicts with 't', 'keypoints', 'pose_detected'

    Returns:
        {
            "score": float [0, 1],
            "avg_movement": float,
            "num_frames": int,
            "debug": {...}
        }
    """
    nose_movements: list[float] = []
    prev_nose = None

    for _i, frame in enumerate(frames):
        # Handle both 'pose_detected' and 'detected' field names
        if not (frame.get("pose_detected") or frame.get("detected")):
            continue

        # Ensure frame has keypoints dict (convert from landmarks if needed)
        frame = ensure_keypoints_dict(frame)
        keypoints = frame.get("keypoints", {})
        shoulder_width = normalize_by_shoulder_width(keypoints)
        nose = get_keypoint_value(keypoints, "nose")

        if nose is None or shoulder_width < 0.01:
            continue

        if prev_nose is None:
            prev_nose = nose
            continue

        # Movement normalized by shoulder width
        movement = distance(prev_nose, nose) / shoulder_width
        nose_movements.append(movement)
        prev_nose = nose

    if not nose_movements:
        return {
            "score": 0.5,
            "avg_movement": 0.0,
            "num_frames": 0,
            "debug": {"reason": "No valid nose keypoints"},
        }

    # Average movement (lower is more stable)
    avg_movement = sum(nose_movements) / len(nose_movements)

    # Convert to [0, 1] score: higher movement = lower score
    # Assume max reasonable movement is ~0.3 shoulder widths per frame
    score = max(0.0, min(1.0, 1.0 - (avg_movement / 0.3)))

    return {
        "score": score,
        "avg_movement": avg_movement,
        "num_frames": len(nose_movements),
        "debug": {"movements": nose_movements[:5]},  # First 5 for inspection
    }


def compute_balance_drift_score(frames: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute balance drift score [0,1] based on hip-ankle alignment over time.

    Compare midpoint of hips vs midpoint of ankles, normalized by frame scale.

    Args:
        frames: List of frame dicts

    Returns:
        {
            "score": float [0, 1],
            "avg_drift": float,
            "num_frames": int,
            "debug": {...}
        }
    """
    drifts = []

    for frame in frames:
        # Handle both 'pose_detected' and 'detected' field names
        if not (frame.get("pose_detected") or frame.get("detected")):
            continue

        # Ensure frame has keypoints dict (convert from landmarks if needed)
        frame = ensure_keypoints_dict(frame)
        keypoints = frame.get("keypoints", {})

        # Get hip and ankle positions
        left_hip = get_keypoint_value(keypoints, "left_hip")
        right_hip = get_keypoint_value(keypoints, "right_hip")
        left_ankle = get_keypoint_value(keypoints, "left_ankle")
        right_ankle = get_keypoint_value(keypoints, "right_ankle")

        if not (left_hip and right_hip and left_ankle and right_ankle):
            continue

        # Compute midpoints
        hip_mid = [(left_hip[0] + right_hip[0]) / 2, (left_hip[1] + right_hip[1]) / 2]
        ankle_mid = [(left_ankle[0] + right_ankle[0]) / 2, (left_ankle[1] + right_ankle[1]) / 2]

        # Horizontal drift (x-direction)
        drift = abs(hip_mid[0] - ankle_mid[0])
        drifts.append(drift)

    if not drifts:
        return {
            "score": 0.5,
            "avg_drift": 0.0,
            "num_frames": 0,
            "debug": {"reason": "No valid hip/ankle keypoints"},
        }

    avg_drift = sum(drifts) / len(drifts)

    # Score: lower drift = higher score
    # Assume max reasonable drift is ~0.2 (normalized coords)
    score = max(0.0, min(1.0, 1.0 - (avg_drift / 0.2)))

    return {
        "score": score,
        "avg_drift": avg_drift,
        "num_frames": len(drifts),
        "debug": {"drifts": drifts[:5]},
    }


def compute_front_knee_brace_score(frames: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute front knee brace score [0,1] based on knee angle during motion.

    Lower knee angles indicate collapse (worse). Higher angles = better brace.
    Use minimum knee angle observed (most collapsed state).

    Args:
        frames: List of frame dicts

    Returns:
        {
            "score": float [0, 1],
            "min_knee_angle": float,
            "num_frames": int,
            "debug": {...}
        }
    """
    knee_angles = []

    for frame in frames:
        # Handle both 'pose_detected' and 'detected' field names
        if not (frame.get("pose_detected") or frame.get("detected")):
            continue

        # Ensure frame has keypoints dict (convert from landmarks if needed)
        frame = ensure_keypoints_dict(frame)
        keypoints = frame.get("keypoints", {})

        # Left knee angle: hip-knee-ankle
        left_hip = get_keypoint_value(keypoints, "left_hip")
        left_knee = get_keypoint_value(keypoints, "left_knee")
        left_ankle = get_keypoint_value(keypoints, "left_ankle")

        if left_hip and left_knee and left_ankle:
            l_angle = angle(left_hip, left_knee, left_ankle)
            knee_angles.append(l_angle)

        # Right knee angle: hip-knee-ankle
        right_hip = get_keypoint_value(keypoints, "right_hip")
        right_knee = get_keypoint_value(keypoints, "right_knee")
        right_ankle = get_keypoint_value(keypoints, "right_ankle")

        if right_hip and right_knee and right_ankle:
            r_angle = angle(right_hip, right_knee, right_ankle)
            knee_angles.append(r_angle)

    if not knee_angles:
        return {
            "score": 0.5,
            "min_knee_angle": 0.0,
            "num_frames": 0,
            "debug": {"reason": "No valid knee keypoints"},
        }

    min_angle = min(knee_angles)
    max_angle = max(knee_angles)

    # Score based on minimum angle observed
    # Healthy knee brace: angle > 120 degrees
    # Collapse: angle < 90 degrees
    # Score [0, 1]: 180 deg = 1.0, 80 deg = 0.0
    score = max(0.0, min(1.0, (min_angle - 80) / 100))

    return {
        "score": score,
        "min_knee_angle": min_angle,
        "max_knee_angle": max_angle,
        "num_frames": len(knee_angles),
        "debug": {"angles": knee_angles[:5]},
    }


def compute_hip_shoulder_separation_timing(frames: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute lag (seconds) between peak hip rotation velocity and peak shoulder rotation velocity.

    Higher lag = more separation = better cricket technique.

    Args:
        frames: List of frame dicts with 't' (timestamp) and keypoints

    Returns:
        {
            "score": float (lag in seconds),
            "hip_peak_time": float,
            "shoulder_peak_time": float,
            "num_frames": int,
            "debug": {...}
        }
    """
    hip_angles: list[float | None] = []
    shoulder_angles: list[float | None] = []
    times: list[float] = []

    for frame in frames:
        # Handle both 'pose_detected' and 'detected' field names
        if not (frame.get("pose_detected") or frame.get("detected")):
            continue

        # Ensure frame has keypoints dict (convert from landmarks if needed)
        frame = ensure_keypoints_dict(frame)
        keypoints = frame.get("keypoints", {})
        t = frame.get("t", 0.0)

        times.append(t)

        # Hip angle: line from left_hip to right_hip
        left_hip = get_keypoint_value(keypoints, "left_hip")
        right_hip = get_keypoint_value(keypoints, "right_hip")

        if left_hip and right_hip:
            h_angle = line_angle(left_hip, right_hip)
            hip_angles.append(h_angle)
        else:
            hip_angles.append(None)

        # Shoulder angle: line from left_shoulder to right_shoulder
        left_shoulder = get_keypoint_value(keypoints, "left_shoulder")
        right_shoulder = get_keypoint_value(keypoints, "right_shoulder")

        if left_shoulder and right_shoulder:
            s_angle = line_angle(left_shoulder, right_shoulder)
            shoulder_angles.append(s_angle)
        else:
            shoulder_angles.append(None)

    if not times or len([x for x in hip_angles if x is not None]) < 3:
        return {
            "score": 0.0,
            "hip_peak_time": 0.0,
            "shoulder_peak_time": 0.0,
            "num_frames": 0,
            "debug": {"reason": "Insufficient hip/shoulder data"},
        }

    # Compute velocities (simple derivative)
    hip_velocities: list[tuple[float, float]] = []
    for i in range(1, len(hip_angles)):
        if hip_angles[i] is not None and hip_angles[i - 1] is not None:
            dt = times[i] - times[i - 1]
            if dt > 0:
                hip_a = cast(float, hip_angles[i])
                hip_b = cast(float, hip_angles[i - 1])
                vel = (hip_a - hip_b) / dt
                hip_velocities.append((times[i], abs(vel)))
            else:
                hip_velocities.append((times[i], 0.0))

    shoulder_velocities: list[tuple[float, float]] = []
    for i in range(1, len(shoulder_angles)):
        if shoulder_angles[i] is not None and shoulder_angles[i - 1] is not None:
            dt = times[i] - times[i - 1]
            if dt > 0:
                shoulder_a = cast(float, shoulder_angles[i])
                shoulder_b = cast(float, shoulder_angles[i - 1])
                vel = (shoulder_a - shoulder_b) / dt
                shoulder_velocities.append((times[i], abs(vel)))
            else:
                shoulder_velocities.append((times[i], 0.0))

    if not hip_velocities or not shoulder_velocities:
        return {
            "score": 0.0,
            "hip_peak_time": 0.0,
            "shoulder_peak_time": 0.0,
            "num_frames": len(times),
            "debug": {"reason": "Cannot compute velocities"},
        }

    # Find peak velocities
    hip_peak_t = max(hip_velocities, key=lambda x: x[1])[0]
    shoulder_peak_t = max(shoulder_velocities, key=lambda x: x[1])[0]

    # Lag: hip should peak before shoulder (positive lag is good)
    lag = shoulder_peak_t - hip_peak_t

    return {
        "score": lag,
        "hip_peak_time": hip_peak_t,
        "shoulder_peak_time": shoulder_peak_t,
        "num_frames": len(times),
        "debug": {
            "hip_velocities_sample": [v for t, v in hip_velocities[:3]],
            "shoulder_velocities_sample": [v for t, v in shoulder_velocities[:3]],
        },
    }


def compute_elbow_drop_score(frames: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute elbow drop score [0,1] based on elbow y-position relative to shoulder.

    Lower elbows (higher y value in image coords) = higher score.
    Compare average elbow height to shoulder height.

    Args:
        frames: List of frame dicts

    Returns:
        {
            "score": float [0, 1],
            "avg_elbow_drop": float,
            "num_frames": int,
            "debug": {...}
        }
    """
    elbow_drops = []

    for frame in frames:
        # Handle both 'pose_detected' and 'detected' field names
        if not (frame.get("pose_detected") or frame.get("detected")):
            continue

        # Ensure frame has keypoints dict (convert from landmarks if needed)
        frame = ensure_keypoints_dict(frame)
        keypoints = frame.get("keypoints", {})

        # Left side
        left_shoulder = get_keypoint_value(keypoints, "left_shoulder")
        left_elbow = get_keypoint_value(keypoints, "left_elbow")

        if left_shoulder and left_elbow:
            # Drop is positive y difference (elbow below shoulder)
            drop = left_elbow[1] - left_shoulder[1]
            elbow_drops.append(drop)

        # Right side
        right_shoulder = get_keypoint_value(keypoints, "right_shoulder")
        right_elbow = get_keypoint_value(keypoints, "right_elbow")

        if right_shoulder and right_elbow:
            drop = right_elbow[1] - right_shoulder[1]
            elbow_drops.append(drop)

    if not elbow_drops:
        return {
            "score": 0.5,
            "avg_elbow_drop": 0.0,
            "num_frames": 0,
            "debug": {"reason": "No valid elbow/shoulder keypoints"},
        }

    avg_drop = sum(elbow_drops) / len(elbow_drops)

    # Score: higher drop (elbows lower) = better = higher score
    # Assume good drop is ~0.15-0.25 in normalized coords
    # Drop < 0.05 is high elbows (bad), Drop > 0.3 is too low
    score = max(0.0, min(1.0, (avg_drop - 0.05) / 0.25))

    return {
        "score": score,
        "avg_elbow_drop": avg_drop,
        "num_frames": len(elbow_drops),
        "debug": {"drops": elbow_drops[:5]},
    }


# ============================================================================
# Main Metrics Computation
# ============================================================================


def compute_pose_metrics(pose_data: dict[str, Any]) -> dict[str, Any]:
    """
    Compute all cricket coaching metrics from pose data.

    Args:
        pose_data: Output from pose_service.extract_pose_keypoints_from_video()

    Returns:
        {
            "metrics": {
                "head_stability_score": {...},
                "balance_drift_score": {...},
                "front_knee_brace_score": {...},
                "hip_shoulder_separation_timing": {...},
                "elbow_drop_score": {...}
            },
            "summary": {
                "total_frames": int,
                "frames_with_pose": int
            },
            "computed_at": str (ISO timestamp)
        }
    """
    frames = pose_data.get("frames", [])

    logger.info(f"Computing metrics for {len(frames)} frames")

    # Compute all metrics
    metrics = {
        "head_stability_score": compute_head_stability_score(frames),
        "balance_drift_score": compute_balance_drift_score(frames),
        "front_knee_brace_score": compute_front_knee_brace_score(frames),
        "hip_shoulder_separation_timing": compute_hip_shoulder_separation_timing(frames),
        "elbow_drop_score": compute_elbow_drop_score(frames),
    }

    # Extend metric objects with per-frame score series (do not change existing keys)
    try:
        per_frame = _compute_per_frame_series(frames)
        for metric_key, data in per_frame.items():
            metric_obj = metrics.get(metric_key)
            if isinstance(metric_obj, dict):
                metric_obj.setdefault("per_frame_scores", data["scores"])
                metric_obj.setdefault("per_frame_frame_nums", data["frame_nums"])
                metric_obj.setdefault("per_frame_timestamps_s", data["timestamps_s"])
    except Exception:
        # Evidence is best-effort; metrics must remain robust.
        logger.exception("Failed to compute per-frame metric series")

    # Summary stats
    frames_with_pose = sum(1 for f in frames if f.get("pose_detected") or f.get("detected", False))

    result = {
        "metrics": metrics,
        "summary": {
            "total_frames": len(frames),
            "frames_with_pose": frames_with_pose,
        },
        "computed_at": "2025-12-21T00:00:00Z",  # Timestamp added by caller if needed
    }

    logger.info(f"Metrics computed: {list(metrics.keys())}")

    return result

from __future__ import annotations

import math
from statistics import median
from typing import Any

from backend.domain.coach_analysis_v2_contract import (
    EvidenceRef,
    RepetitionActionRecordV2,
    ValidityState,
)

_GENERIC_ACTION_TYPES = {
    "batting": "batting_shot",
    "bowling": "bowling_delivery",
    "wicketkeeping": "wicketkeeping_action",
    "fielding": "fielding_action",
}

_JOINTS_BY_DISCIPLINE = {
    "batting": (
        "left_wrist",
        "right_wrist",
        "left_elbow",
        "right_elbow",
        "left_shoulder",
        "right_shoulder",
        "left_hip",
        "right_hip",
        "left_ankle",
        "right_ankle",
    ),
    "bowling": (
        "left_wrist",
        "right_wrist",
        "left_elbow",
        "right_elbow",
        "left_shoulder",
        "right_shoulder",
        "left_hip",
        "right_hip",
        "left_knee",
        "right_knee",
        "left_ankle",
        "right_ankle",
    ),
    "wicketkeeping": (
        "left_wrist",
        "right_wrist",
        "left_elbow",
        "right_elbow",
        "left_shoulder",
        "right_shoulder",
        "left_hip",
        "right_hip",
    ),
    "fielding": (
        "left_wrist",
        "right_wrist",
        "left_elbow",
        "right_elbow",
        "left_shoulder",
        "right_shoulder",
        "left_hip",
        "right_hip",
        "left_knee",
        "right_knee",
    ),
}

_MIN_SAMPLE_FPS = {
    "batting": 4.0,
    "bowling": 5.0,
    "wicketkeeping": 5.0,
    "fielding": 4.0,
}

_MIN_SOURCE_FPS = {
    "batting": 12.0,
    "bowling": 15.0,
    "wicketkeeping": 15.0,
    "fielding": 12.0,
}

_SUPPORTED_CAMERA_VIEWS = {
    "batting": {"side", "front", "behind"},
    "bowling": {"side", "front", "behind"},
    "wicketkeeping": {"side", "front", "behind"},
    "fielding": {"side", "front", "behind"},
}

_MIN_DURATION_SECONDS = {
    "batting": 0.25,
    "bowling": 0.25,
    "wicketkeeping": 0.25,
    "fielding": 0.25,
}

_MAX_DURATION_SECONDS = {
    "batting": 4.0,
    "bowling": 6.0,
    "wicketkeeping": 4.5,
    "fielding": 5.0,
}


def attach_repetition_segmentation(
    *,
    results_payload: dict[str, Any],
    discipline: str,
    frames: list[dict[str, Any]] | None,
    session_id: str | None = None,
    job_id: str | None = None,
    sample_fps: float | None = None,
    source_video_fps: float | None = None,
    camera_view: str | None = None,
    metric_refs: list[str] | None = None,
    ball_tracking: dict[str, Any] | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    repetitions, summary = segment_repetitions(
        discipline=discipline,
        frames=frames or [],
        session_id=session_id,
        job_id=job_id,
        sample_fps=sample_fps,
        source_video_fps=source_video_fps,
        camera_view=camera_view,
        metric_refs=metric_refs or [],
        ball_tracking=ball_tracking,
        enabled=enabled,
    )
    results_payload.setdefault("meta", {})
    if isinstance(results_payload["meta"], dict):
        results_payload["meta"]["repetition_segmentation"] = summary

    v2_payload = results_payload.get("v2")
    if isinstance(v2_payload, dict):
        v2_payload["repetitions"] = [item.model_dump(mode="json") for item in repetitions]
    return results_payload


def extract_repetition_segmentation(
    payload: dict[str, Any] | None,
) -> tuple[list[RepetitionActionRecordV2], dict[str, Any] | None]:
    if not isinstance(payload, dict):
        return ([], None)
    repetitions_payload = payload.get("v2", {}).get("repetitions")
    repetitions: list[RepetitionActionRecordV2] = []
    if isinstance(repetitions_payload, list):
        for item in repetitions_payload:
            try:
                repetitions.append(RepetitionActionRecordV2.model_validate(item))
            except Exception:
                continue
    summary = payload.get("meta", {}).get("repetition_segmentation")
    return (repetitions, summary if isinstance(summary, dict) else None)


def segment_repetitions(
    *,
    discipline: str,
    frames: list[dict[str, Any]],
    session_id: str | None = None,
    job_id: str | None = None,
    sample_fps: float | None = None,
    source_video_fps: float | None = None,
    camera_view: str | None = None,
    metric_refs: list[str] | None = None,
    ball_tracking: dict[str, Any] | None = None,
    enabled: bool = True,
) -> tuple[list[RepetitionActionRecordV2], dict[str, Any]]:
    normalized_discipline = (discipline or "").strip().lower()
    metric_refs = metric_refs or []
    summary = {
        "enabled": bool(enabled),
        "discipline": normalized_discipline,
        "segmentation_method": "disabled",
        "validity_state": ValidityState.NOT_MEASURABLE.value,
        "segmentation_confidence": 0.0,
        "repetitions_count": 0,
        "insufficient_reason": "Repetition segmentation is disabled.",
    }
    if not enabled:
        return ([], summary)

    if normalized_discipline not in _GENERIC_ACTION_TYPES:
        summary.update(
            {
                "segmentation_method": "unsupported_discipline",
                "insufficient_reason": f"Discipline '{discipline}' is not supported.",
            }
        )
        return ([], summary)

    supported_views = _SUPPORTED_CAMERA_VIEWS[normalized_discipline]
    if camera_view is not None and camera_view not in supported_views:
        summary.update(
            {
                "segmentation_method": "capture_gated",
                "validity_state": ValidityState.UNSUPPORTED_CAMERA_VIEW.value,
                "insufficient_reason": (
                    f"Camera view '{camera_view}' is not supported for safe "
                    f"{normalized_discipline} repetition segmentation."
                ),
            }
        )
        return ([], summary)

    min_sample_fps = _MIN_SAMPLE_FPS[normalized_discipline]
    min_source_fps = _MIN_SOURCE_FPS[normalized_discipline]
    if sample_fps is not None and sample_fps < min_sample_fps:
        summary.update(
            {
                "segmentation_method": "capture_gated",
                "validity_state": ValidityState.INSUFFICIENT_FRAME_RATE.value,
                "insufficient_reason": (
                    f"Sample FPS {sample_fps:.2f} is below the minimum "
                    f"{min_sample_fps:.2f} required for safe segmentation."
                ),
            }
        )
        return ([], summary)
    if source_video_fps is not None and source_video_fps < min_source_fps:
        summary.update(
            {
                "segmentation_method": "capture_gated",
                "validity_state": ValidityState.INSUFFICIENT_FRAME_RATE.value,
                "insufficient_reason": (
                    f"Source FPS {source_video_fps:.2f} is below the minimum "
                    f"{min_source_fps:.2f} required for safe segmentation."
                ),
            }
        )
        return ([], summary)

    sampled_frames = _normalize_frames(frames)
    if not sampled_frames:
        summary.update(
            {
                "segmentation_method": "pose_motion_v1",
                "validity_state": ValidityState.INSUFFICIENT_VISIBILITY.value,
                "insufficient_reason": "No pose frames were available for segmentation.",
            }
        )
        return ([], summary)

    detected_frames = [
        frame for frame in sampled_frames if frame["detected"] and frame["keypoints"]
    ]
    if len(detected_frames) < 2:
        summary.update(
            {
                "segmentation_method": "pose_motion_v1",
                "validity_state": ValidityState.INSUFFICIENT_VISIBILITY.value,
                "insufficient_reason": "Not enough detected pose frames were available for segmentation.",
            }
        )
        return ([], summary)

    motion_scores = _compute_motion_scores(detected_frames, normalized_discipline)
    windows, threshold = _build_candidate_windows(
        detected_frames=detected_frames,
        motion_scores=motion_scores,
        discipline=normalized_discipline,
    )
    repetitions = _build_repetition_records(
        windows=windows,
        all_frames=sampled_frames,
        detected_frames=detected_frames,
        motion_scores=motion_scores,
        threshold=threshold,
        discipline=normalized_discipline,
        session_id=session_id,
        job_id=job_id,
        metric_refs=metric_refs,
    )

    summary_method = "pose_motion_v1"
    if normalized_discipline == "bowling" and ball_tracking:
        repetitions, used_ball_tracking = refine_bowling_repetitions_with_ball_tracking(
            repetitions=repetitions,
            ball_tracking=ball_tracking,
            job_id=job_id,
            session_id=session_id,
            metric_refs=metric_refs,
        )
        if used_ball_tracking:
            summary_method = "pose_motion_ball_hybrid_v1"

    if not repetitions:
        summary.update(
            {
                "segmentation_method": summary_method,
                "validity_state": ValidityState.NOT_MEASURABLE.value,
                "segmentation_confidence": 0.0,
                "insufficient_reason": "Insufficient motion/action evidence for safe repetition segmentation.",
            }
        )
        return ([], summary)

    confidences = [
        rep.segmentation_confidence
        for rep in repetitions
        if rep.segmentation_confidence is not None
    ]
    summary.update(
        {
            "segmentation_method": summary_method,
            "validity_state": _summary_validity_state(repetitions).value,
            "segmentation_confidence": round(sum(confidences) / len(confidences), 3)
            if confidences
            else 0.0,
            "repetitions_count": len(repetitions),
            "insufficient_reason": None,
        }
    )
    return (repetitions, summary)


def refine_bowling_repetitions_with_ball_tracking(
    *,
    repetitions: list[RepetitionActionRecordV2],
    ball_tracking: dict[str, Any],
    job_id: str | None = None,
    session_id: str | None = None,
    metric_refs: list[str] | None = None,
) -> tuple[list[RepetitionActionRecordV2], bool]:
    trajectory = ball_tracking.get("trajectory") if isinstance(ball_tracking, dict) else None
    if not isinstance(trajectory, dict):
        return (repetitions, False)
    release_point = trajectory.get("release_point")
    bounce_point = trajectory.get("bounce_point")
    if not isinstance(release_point, dict) or not isinstance(bounce_point, dict):
        return (repetitions, False)
    release_ts = _safe_float(release_point.get("timestamp"))
    bounce_ts = _safe_float(bounce_point.get("timestamp"))
    if release_ts is None or bounce_ts is None or bounce_ts <= release_ts:
        return (repetitions, False)

    release_frame = _safe_int(release_point.get("frame_num"))
    bounce_frame = _safe_int(bounce_point.get("frame_num"))
    evidence = EvidenceRef(ref_type="ball_tracking", label="release_to_bounce_window")
    if not repetitions:
        created = RepetitionActionRecordV2(
            repetition_id=_repetition_id(job_id, 1),
            session_id=session_id,
            job_id=job_id,
            discipline="bowling",
            action_type="bowling_delivery",
            start_ts=round(max(0.0, release_ts - 0.25), 3),
            end_ts=round(bounce_ts + 0.25, 3),
            start_frame=release_frame,
            end_frame=bounce_frame,
            segmentation_method="ball_tracking_assist_v1",
            segmentation_confidence=round(
                min(
                    0.95,
                    max(0.6, (_safe_float(trajectory.get("detection_rate"), scale=100.0) or 0.6)),
                ),
                3,
            ),
            validity_state=ValidityState.VALID,
            evidence_refs=[evidence],
            metric_refs=metric_refs or [],
        )
        return ([created], True)

    updated: list[RepetitionActionRecordV2] = []
    matched = False
    for repetition in repetitions:
        if repetition.end_ts is None or repetition.start_ts is None:
            updated.append(repetition)
            continue
        overlap = not (bounce_ts < repetition.start_ts or release_ts > repetition.end_ts)
        if not overlap:
            updated.append(repetition)
            continue
        matched = True
        start_ts = min(repetition.start_ts, max(0.0, release_ts - 0.25))
        end_ts = max(repetition.end_ts, bounce_ts + 0.25)
        confidence = repetition.segmentation_confidence or 0.6
        updated.append(
            repetition.model_copy(
                update={
                    "start_ts": round(start_ts, 3),
                    "end_ts": round(end_ts, 3),
                    "start_frame": release_frame
                    if release_frame is not None
                    else repetition.start_frame,
                    "end_frame": bounce_frame if bounce_frame is not None else repetition.end_frame,
                    "segmentation_method": "pose_motion_ball_hybrid_v1",
                    "segmentation_confidence": round(min(0.98, confidence + 0.08), 3),
                    "evidence_refs": [*repetition.evidence_refs, evidence],
                }
            )
        )
    return (updated if matched else repetitions, matched)


def _build_repetition_records(
    *,
    windows: list[dict[str, float | int]],
    all_frames: list[dict[str, Any]],
    detected_frames: list[dict[str, Any]],
    motion_scores: list[float],
    threshold: float,
    discipline: str,
    session_id: str | None,
    job_id: str | None,
    metric_refs: list[str],
) -> list[RepetitionActionRecordV2]:
    repetitions: list[RepetitionActionRecordV2] = []
    last_end_frame: int | None = None
    min_duration = _MIN_DURATION_SECONDS[discipline]
    max_duration = _MAX_DURATION_SECONDS[discipline]

    for index, window in enumerate(windows, start=1):
        start_idx = int(window["start_idx"])
        end_idx = int(window["end_idx"])
        start_frame = int(window["start_frame"])
        end_frame = int(window["end_frame"])
        start_ts = float(window["start_ts"])
        end_ts = float(window["end_ts"])
        duration = end_ts - start_ts
        if end_frame <= start_frame or duration <= 0:
            continue
        if last_end_frame is not None and start_frame <= last_end_frame:
            continue
        if duration < min_duration or duration > max_duration:
            continue

        full_window_frames = [
            frame
            for frame in all_frames
            if _safe_int(frame.get("frame_num")) is not None
            and start_frame <= int(frame["frame_num"]) <= end_frame
        ]
        detected_window_frames = detected_frames[start_idx : end_idx + 1]
        if len(detected_window_frames) < 2:
            continue

        coverage = (
            len([frame for frame in full_window_frames if frame["detected"]])
            / len(full_window_frames)
            if full_window_frames
            else 0.0
        )
        peak_motion = max(motion_scores[start_idx : end_idx + 1], default=0.0)
        duration_fit = 1.0 - min(
            1.0, abs(duration - ((min_duration + max_duration) / 2.0)) / max_duration
        )
        motion_fit = min(1.0, peak_motion / max(threshold * 2.0, 0.001))
        confidence = round(
            max(0.0, min(1.0, coverage * 0.45 + motion_fit * 0.4 + duration_fit * 0.15)),
            3,
        )

        subtype, subtype_confidence = _infer_action_type(discipline, detected_window_frames)
        action_type = subtype if subtype_confidence >= 0.72 else _GENERIC_ACTION_TYPES[discipline]
        confidence = round(
            min(1.0, max(confidence, subtype_confidence if action_type == subtype else confidence)),
            3,
        )

        validity_state = ValidityState.VALID
        insufficient_reason = None
        if coverage < 0.55:
            validity_state = ValidityState.INSUFFICIENT_VISIBILITY
            insufficient_reason = "Pose visibility within the repetition window was insufficient."
        elif confidence < 0.6:
            validity_state = ValidityState.LOW_CONFIDENCE
            insufficient_reason = "Segmentation confidence was below the preferred threshold."

        repetitions.append(
            RepetitionActionRecordV2(
                repetition_id=_repetition_id(job_id, index),
                session_id=session_id,
                job_id=job_id,
                discipline=discipline,
                action_type=action_type,
                start_ts=round(start_ts, 3),
                end_ts=round(end_ts, 3),
                start_frame=start_frame,
                end_frame=end_frame,
                segmentation_method="pose_motion_v1",
                segmentation_confidence=confidence,
                manual_override=False,
                validity_state=validity_state,
                insufficient_reason=insufficient_reason,
                evidence_refs=[
                    EvidenceRef(
                        ref_type="pose_window",
                        ref_id=f"{start_frame}:{end_frame}",
                        label=f"frames {start_frame}-{end_frame}",
                    )
                ],
                metric_refs=metric_refs,
            )
        )
        last_end_frame = end_frame

    return repetitions


def _build_candidate_windows(
    *,
    detected_frames: list[dict[str, Any]],
    motion_scores: list[float],
    discipline: str,
) -> tuple[list[dict[str, float | int]], float]:
    if not motion_scores:
        return ([], 0.0)

    non_zero_scores = [score for score in motion_scores if score > 0]
    if not non_zero_scores:
        return ([], 0.0)

    baseline = median(non_zero_scores)
    peak = max(non_zero_scores)
    threshold = max(0.08, min(0.4, baseline + ((peak - baseline) * 0.45)))
    if peak < threshold:
        return ([], threshold)

    active = [score >= threshold for score in motion_scores]
    min_active_len = 2
    gap_allowance = 1
    padding = 1
    windows: list[tuple[int, int]] = []
    current_start: int | None = None
    inactive_run = 0

    for idx, is_active in enumerate(active):
        if is_active:
            if current_start is None:
                current_start = idx
            inactive_run = 0
            continue
        if current_start is None:
            continue
        inactive_run += 1
        if inactive_run <= gap_allowance:
            continue
        current_end = idx - inactive_run
        if current_end - current_start + 1 >= min_active_len:
            windows.append(
                (max(0, current_start - padding), min(len(active) - 1, current_end + padding))
            )
        current_start = None
        inactive_run = 0

    if current_start is not None:
        current_end = len(active) - 1
        if current_end - current_start + 1 >= min_active_len:
            windows.append((max(0, current_start - padding), current_end))

    merged: list[tuple[int, int]] = []
    for start, end in windows:
        if not merged:
            merged.append((start, end))
            continue
        prev_start, prev_end = merged[-1]
        prev_end_ts = float(detected_frames[prev_end]["timestamp"])
        start_ts = float(detected_frames[start]["timestamp"])
        if start_ts - prev_end_ts <= 0.6:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))

    return (
        [
            {
                "start_idx": start,
                "end_idx": end,
                "start_frame": int(detected_frames[start]["frame_num"]),
                "end_frame": int(detected_frames[end]["frame_num"]),
                "start_ts": float(detected_frames[start]["timestamp"]),
                "end_ts": float(detected_frames[end]["timestamp"]),
            }
            for start, end in merged
        ],
        threshold,
    )


def _compute_motion_scores(
    detected_frames: list[dict[str, Any]],
    discipline: str,
) -> list[float]:
    joints = _JOINTS_BY_DISCIPLINE[discipline]
    scores: list[float] = [0.0]
    for current, previous in zip(detected_frames[1:], detected_frames[:-1], strict=False):
        dt = float(current["timestamp"]) - float(previous["timestamp"])
        if dt <= 0:
            scores.append(0.0)
            continue
        distances: list[float] = []
        for joint in joints:
            current_point = _extract_xy(current["keypoints"].get(joint))
            previous_point = _extract_xy(previous["keypoints"].get(joint))
            if current_point is None or previous_point is None:
                continue
            distances.append(
                math.dist(
                    (current_point[0], current_point[1]), (previous_point[0], previous_point[1])
                )
            )
        if not distances:
            scores.append(0.0)
            continue
        dominant_distances = sorted(distances, reverse=True)[: min(4, len(distances))]
        scores.append(sum(dominant_distances) / len(dominant_distances) / dt)
    return _smooth_scores(scores)


def _smooth_scores(values: list[float]) -> list[float]:
    if len(values) < 3:
        return values
    smoothed: list[float] = []
    for index in range(len(values)):
        left = max(0, index - 1)
        right = min(len(values), index + 2)
        window = values[left:right]
        smoothed.append(sum(window) / len(window))
    return smoothed


def _infer_action_type(
    discipline: str, detected_window_frames: list[dict[str, Any]]
) -> tuple[str, float]:
    if discipline == "bowling":
        return ("bowling_delivery", 0.88)
    if discipline == "batting":
        return ("batting_shot", 0.82)

    start_frame = detected_window_frames[0]
    end_frame = detected_window_frames[-1]
    left_wrist_start = _extract_xy(start_frame["keypoints"].get("left_wrist"))
    right_wrist_start = _extract_xy(start_frame["keypoints"].get("right_wrist"))
    left_wrist_end = _extract_xy(end_frame["keypoints"].get("left_wrist"))
    right_wrist_end = _extract_xy(end_frame["keypoints"].get("right_wrist"))
    left_shoulder_end = _extract_xy(end_frame["keypoints"].get("left_shoulder"))
    right_shoulder_end = _extract_xy(end_frame["keypoints"].get("right_shoulder"))

    wrist_distance_start = _pair_distance(left_wrist_start, right_wrist_start)
    wrist_distance_end = _pair_distance(left_wrist_end, right_wrist_end)
    convergence = (
        wrist_distance_start - wrist_distance_end
        if wrist_distance_start is not None and wrist_distance_end is not None
        else 0.0
    )
    avg_wrist_lift = _average_vertical_lift(
        left_wrist_start,
        right_wrist_start,
        left_wrist_end,
        right_wrist_end,
    )
    dominant_travel = max(
        _pair_distance(left_wrist_start, left_wrist_end) or 0.0,
        _pair_distance(right_wrist_start, right_wrist_end) or 0.0,
    )

    if discipline == "wicketkeeping":
        if convergence > 0.08 and avg_wrist_lift > 0.03:
            return ("wicketkeeping_take", 0.76)
        return (_GENERIC_ACTION_TYPES[discipline], 0.58)

    if left_shoulder_end is not None or right_shoulder_end is not None:
        shoulder_height = _mean(
            [point[1] for point in (left_shoulder_end, right_shoulder_end) if point is not None]
        )
    else:
        shoulder_height = None

    wrists_above_shoulders = False
    if shoulder_height is not None:
        for wrist in (left_wrist_end, right_wrist_end):
            if wrist is not None and wrist[1] < shoulder_height:
                wrists_above_shoulders = True
                break

    if convergence > 0.09 and avg_wrist_lift > 0.03:
        return ("fielding_catch", 0.78)
    if dominant_travel > 0.16 and wrists_above_shoulders:
        return ("fielding_throw", 0.69)
    return (_GENERIC_ACTION_TYPES[discipline], 0.57)


def _normalize_frames(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in frames:
        if not isinstance(raw, dict):
            continue
        frame_num = _safe_int(raw.get("frame_num"))
        timestamp = _safe_float(raw.get("timestamp"))
        if frame_num is None:
            frame_num = _safe_int(raw.get("frame_index"))
        if frame_num is None:
            frame_num = _safe_int(raw.get("frame_id"))
        if timestamp is None:
            timestamp = _safe_float(raw.get("t"))
        if frame_num is None or timestamp is None or timestamp < 0:
            continue
        keypoints_raw = raw.get("keypoints")
        keypoints = keypoints_raw if isinstance(keypoints_raw, dict) else {}
        normalized.append(
            {
                "frame_num": frame_num,
                "timestamp": round(timestamp, 3),
                "detected": bool(raw.get("detected")),
                "keypoints": keypoints,
            }
        )
    normalized.sort(key=lambda item: (item["timestamp"], item["frame_num"]))
    return normalized


def _repetition_id(job_id: str | None, index: int) -> str:
    if job_id:
        return f"{job_id}:rep:{index}"
    return f"rep:{index}"


def _summary_validity_state(repetitions: list[RepetitionActionRecordV2]) -> ValidityState:
    states = {item.validity_state for item in repetitions}
    if states == {ValidityState.VALID}:
        return ValidityState.VALID
    if ValidityState.INSUFFICIENT_VISIBILITY in states:
        return ValidityState.INSUFFICIENT_VISIBILITY
    return ValidityState.LOW_CONFIDENCE


def _extract_xy(point: Any) -> tuple[float, float] | None:
    if isinstance(point, dict):
        x = _safe_float(point.get("x"))
        y = _safe_float(point.get("y"))
        if x is not None and y is not None:
            return (x, y)
    if isinstance(point, (list, tuple)) and len(point) >= 2:
        x = _safe_float(point[0])
        y = _safe_float(point[1])
        if x is not None and y is not None:
            return (x, y)
    return None


def _pair_distance(
    left: tuple[float, float] | None, right: tuple[float, float] | None
) -> float | None:
    if left is None or right is None:
        return None
    return math.dist((left[0], left[1]), (right[0], right[1]))


def _average_vertical_lift(
    left_start: tuple[float, float] | None,
    right_start: tuple[float, float] | None,
    left_end: tuple[float, float] | None,
    right_end: tuple[float, float] | None,
) -> float:
    deltas: list[float] = []
    for start, end in ((left_start, left_end), (right_start, right_end)):
        if start is None or end is None:
            continue
        deltas.append(start[1] - end[1])
    return _mean(deltas) or 0.0


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _safe_float(value: Any, *, scale: float = 1.0) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric / scale


def _safe_int(value: Any) -> int | None:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return None
    return numeric

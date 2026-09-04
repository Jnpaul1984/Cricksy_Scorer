from __future__ import annotations

import math
from typing import Any

from backend.domain.coach_analysis_v2_contract import (
    EvidenceRef,
    PhaseRecordV2,
    RepetitionActionRecordV2,
    ValidityState,
)

_MIN_SAMPLE_FPS = {
    "batting": 5.0,
    "pace_bowling": 6.0,
    "spin_bowling": 6.0,
    "wicketkeeping": 6.0,
    "fielding": 5.0,
}

_MIN_SOURCE_FPS = {
    "batting": 12.0,
    "pace_bowling": 15.0,
    "spin_bowling": 15.0,
    "wicketkeeping": 15.0,
    "fielding": 12.0,
}

_SUPPORTED_CAMERA_VIEWS = {
    "batting": {"side", "front", "behind"},
    "pace_bowling": {"side", "front", "behind"},
    "spin_bowling": {"side", "front", "behind"},
    "wicketkeeping": {"side", "front", "behind"},
    "fielding": {"side", "front", "behind"},
}

_PHASE_SEGMENTS: dict[str, list[tuple[str, float]]] = {
    "batting": [
        ("setup", 0.2),
        ("trigger", 0.12),
        ("backlift", 0.2),
        ("downswing", 0.2),
        ("contact_proxy_window", 0.08),
        ("follow_through", 0.2),
    ],
    "pace_bowling": [
        ("approach", 0.22),
        ("gather", 0.14),
        ("back_foot_contact", 0.12),
        ("delivery_stride", 0.18),
        ("front_foot_contact", 0.12),
        ("release_proxy_window", 0.1),
        ("follow_through", 0.12),
    ],
    "spin_bowling": [
        ("approach", 0.2),
        ("coil", 0.16),
        ("pivot", 0.16),
        ("delivery_stride", 0.16),
        ("release_proxy_window", 0.12),
        ("follow_through", 0.2),
    ],
    "wicketkeeping": [
        ("set", 0.18),
        ("reaction_read", 0.16),
        ("movement", 0.2),
        ("collection", 0.2),
        ("action", 0.12),
        ("recovery", 0.14),
    ],
    "fielding": [
        ("ready", 0.16),
        ("reaction", 0.16),
        ("approach", 0.18),
        ("collection", 0.18),
        ("transfer", 0.12),
        ("throw_action", 0.1),
        ("recovery", 0.1),
    ],
}


def attach_phase_recognition(
    *,
    results_payload: dict[str, Any],
    discipline: str,
    sample_fps: float | None = None,
    source_video_fps: float | None = None,
    camera_view: str | None = None,
    session_discipline: str | None = None,
    ball_tracking: dict[str, Any] | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    repetitions = _extract_repetitions(results_payload)
    phases, summary = recognize_repetition_phases(
        discipline=discipline,
        repetitions=repetitions,
        sample_fps=sample_fps,
        source_video_fps=source_video_fps,
        camera_view=camera_view,
        session_discipline=session_discipline,
        ball_tracking=ball_tracking,
        enabled=enabled,
    )

    results_payload.setdefault("meta", {})
    if isinstance(results_payload.get("meta"), dict):
        results_payload["meta"]["phase_recognition"] = summary

    v2_payload = results_payload.get("v2")
    if isinstance(v2_payload, dict):
        v2_payload["phases"] = [phase.model_dump(mode="json") for phase in phases]
    return results_payload


def extract_phase_recognition(
    payload: dict[str, Any] | None,
) -> tuple[list[PhaseRecordV2], dict[str, Any] | None]:
    if not isinstance(payload, dict):
        return ([], None)
    phases_payload = payload.get("v2", {}).get("phases")
    phases: list[PhaseRecordV2] = []
    if isinstance(phases_payload, list):
        for item in phases_payload:
            try:
                phases.append(PhaseRecordV2.model_validate(item))
            except Exception:
                continue
    summary = payload.get("meta", {}).get("phase_recognition")
    return (phases, summary if isinstance(summary, dict) else None)


def recognize_repetition_phases(
    *,
    discipline: str,
    repetitions: list[RepetitionActionRecordV2],
    sample_fps: float | None = None,
    source_video_fps: float | None = None,
    camera_view: str | None = None,
    session_discipline: str | None = None,
    ball_tracking: dict[str, Any] | None = None,
    enabled: bool = True,
) -> tuple[list[PhaseRecordV2], dict[str, Any]]:
    phase_discipline = _resolve_phase_discipline(discipline, session_discipline)
    summary = {
        "enabled": bool(enabled),
        "discipline": phase_discipline,
        "detection_method": "disabled",
        "validity_state": ValidityState.NOT_MEASURABLE.value,
        "phases_count": 0,
        "recognized_repetitions": 0,
        "insufficient_reason": "Phase recognition is disabled.",
    }
    if not enabled:
        return ([], summary)

    if phase_discipline not in _PHASE_SEGMENTS:
        summary.update(
            {
                "detection_method": "unsupported_discipline",
                "insufficient_reason": f"Discipline '{discipline}' is not supported.",
            }
        )
        return ([], summary)

    supported_views = _SUPPORTED_CAMERA_VIEWS[phase_discipline]
    if camera_view is not None and camera_view not in supported_views:
        summary.update(
            {
                "detection_method": "capture_gated",
                "validity_state": ValidityState.UNSUPPORTED_CAMERA_VIEW.value,
                "insufficient_reason": (
                    f"Camera view '{camera_view}' is not supported for safe {phase_discipline} "
                    "phase recognition."
                ),
            }
        )
        return ([], summary)

    min_sample_fps = _MIN_SAMPLE_FPS[phase_discipline]
    if sample_fps is not None and sample_fps < min_sample_fps:
        summary.update(
            {
                "detection_method": "capture_gated",
                "validity_state": ValidityState.INSUFFICIENT_FRAME_RATE.value,
                "insufficient_reason": (
                    f"Sample FPS {sample_fps:.2f} is below the minimum {min_sample_fps:.2f} "
                    "required for safe phase recognition."
                ),
            }
        )
        return ([], summary)

    min_source_fps = _MIN_SOURCE_FPS[phase_discipline]
    if source_video_fps is not None and source_video_fps < min_source_fps:
        summary.update(
            {
                "detection_method": "capture_gated",
                "validity_state": ValidityState.INSUFFICIENT_FRAME_RATE.value,
                "insufficient_reason": (
                    f"Source FPS {source_video_fps:.2f} is below the minimum {min_source_fps:.2f} "
                    "required for safe phase recognition."
                ),
            }
        )
        return ([], summary)

    phases: list[PhaseRecordV2] = []
    recognized_repetitions = 0
    low_confidence_only = True
    for repetition in repetitions:
        repetition_phases = _build_repetition_phases(
            repetition=repetition,
            phase_discipline=phase_discipline,
            supported_views=sorted(supported_views),
            ball_tracking=ball_tracking,
        )
        if repetition_phases:
            recognized_repetitions += 1
            if any(phase.validity_state == ValidityState.VALID for phase in repetition_phases):
                low_confidence_only = False
            phases.extend(repetition_phases)

    if not phases:
        summary.update(
            {
                "detection_method": "repetition_relative_heuristic_v1",
                "validity_state": ValidityState.NOT_MEASURABLE.value,
                "insufficient_reason": (
                    "No safe phase windows were measurable from the repetition data."
                ),
            }
        )
        return ([], summary)

    summary.update(
        {
            "detection_method": "repetition_relative_heuristic_v1",
            "validity_state": (
                ValidityState.LOW_CONFIDENCE.value
                if low_confidence_only
                else ValidityState.VALID.value
            ),
            "phases_count": len(phases),
            "recognized_repetitions": recognized_repetitions,
            "insufficient_reason": (
                None
                if not low_confidence_only
                else "Only low-confidence phase windows were available."
            ),
        }
    )
    return (phases, summary)


def _extract_repetitions(results_payload: dict[str, Any]) -> list[RepetitionActionRecordV2]:
    repetitions_payload = results_payload.get("v2", {}).get("repetitions")
    repetitions: list[RepetitionActionRecordV2] = []
    if not isinstance(repetitions_payload, list):
        return repetitions
    for item in repetitions_payload:
        try:
            repetitions.append(RepetitionActionRecordV2.model_validate(item))
        except Exception:
            continue
    return repetitions


def _build_repetition_phases(
    *,
    repetition: RepetitionActionRecordV2,
    phase_discipline: str,
    supported_views: list[str],
    ball_tracking: dict[str, Any] | None,
) -> list[PhaseRecordV2]:
    bounds = _resolve_repetition_bounds(repetition)
    if bounds is None:
        return []
    start_ts, end_ts, start_frame, end_frame = bounds
    ts_points = _segment_points(start_ts, end_ts, _PHASE_SEGMENTS[phase_discipline])
    frame_points = (
        _segment_points(float(start_frame), float(end_frame), _PHASE_SEGMENTS[phase_discipline])
        if start_frame is not None and end_frame is not None
        else None
    )

    release_evidence = _resolve_ball_evidence(ball_tracking, evidence_type="release")
    contact_evidence = _resolve_ball_evidence(ball_tracking, evidence_type="contact")

    phases: list[PhaseRecordV2] = []
    for index, (phase_name, _weight) in enumerate(_PHASE_SEGMENTS[phase_discipline], start=1):
        raw_start_ts = ts_points[index - 1]
        raw_end_ts = ts_points[index]
        if raw_end_ts <= raw_start_ts:
            continue

        raw_start_frame: int | None = None
        raw_end_frame: int | None = None
        if frame_points is not None:
            raw_start_frame = int(round(frame_points[index - 1]))
            raw_end_frame = int(round(frame_points[index]))
            if raw_end_frame <= raw_start_frame:
                raw_end_frame = raw_start_frame + 1
            raw_start_frame = max(start_frame or 0, raw_start_frame)
            raw_end_frame = min(end_frame or raw_end_frame, raw_end_frame)
            if raw_end_frame <= raw_start_frame:
                continue

        normalized_name = phase_name
        requires_object = False
        evidence_refs = [
            EvidenceRef(
                ref_type="repetition_window",
                ref_id=repetition.repetition_id,
                label=f"repetition:{repetition.repetition_id}",
            )
        ]
        limitations: list[str] = []

        confidence = repetition.segmentation_confidence or 0.58
        confidence = max(0.35, min(0.95, confidence))
        validity_state = (
            ValidityState.VALID
            if repetition.validity_state == ValidityState.VALID
            else ValidityState.LOW_CONFIDENCE
        )
        detection_method = "repetition_relative_heuristic_v1"

        if phase_discipline == "batting" and phase_name == "contact_proxy_window":
            requires_object = True
            if contact_evidence and _within_ts(
                raw_start_ts,
                raw_end_ts,
                contact_evidence.get("timestamp"),
            ):
                normalized_name = "contact"
                confidence = min(0.96, confidence + 0.12)
                detection_method = "pose_ball_hybrid_v1"
                evidence_refs.append(EvidenceRef(ref_type="ball_tracking", label="impact_point"))
            else:
                limitations.append(
                    "Bat/ball contact evidence was unavailable; "
                    "contact is reported as a proxy window."
                )
                confidence = min(confidence, 0.59)
                validity_state = ValidityState.LOW_CONFIDENCE

        if (
            phase_discipline in {"pace_bowling", "spin_bowling"}
            and phase_name == "release_proxy_window"
        ):
            requires_object = True
            if release_evidence and _within_ts(
                raw_start_ts,
                raw_end_ts,
                release_evidence.get("timestamp"),
            ):
                normalized_name = "release"
                confidence = min(0.97, confidence + 0.1)
                detection_method = "pose_ball_hybrid_v1"
                evidence_refs.append(EvidenceRef(ref_type="ball_tracking", label="release_point"))
            else:
                limitations.append(
                    "Ball release evidence was unavailable; release is reported as a proxy window."
                )
                confidence = min(confidence, 0.6)
                validity_state = ValidityState.LOW_CONFIDENCE

        if repetition.validity_state == ValidityState.INSUFFICIENT_VISIBILITY:
            confidence = min(confidence, 0.55)
            validity_state = ValidityState.INSUFFICIENT_VISIBILITY
            limitations.append(
                "Parent repetition visibility was insufficient for robust phase timing."
            )

        phase_id = f"{repetition.repetition_id}:phase:{index}"
        phases.append(
            PhaseRecordV2(
                phase_id=phase_id,
                repetition_id=repetition.repetition_id,
                phase_name=normalized_name,
                start_ts=round(max(start_ts, raw_start_ts), 3),
                end_ts=round(min(end_ts, raw_end_ts), 3),
                start_frame=raw_start_frame,
                end_frame=raw_end_frame,
                detection_method=detection_method,
                confidence=round(max(0.0, min(1.0, confidence)), 3),
                requires_object_evidence=requires_object,
                camera_view_compatibility=supported_views,
                manual_correction_supported=False,
                validity_state=validity_state,
                evidence_refs=evidence_refs,
                limitations=limitations,
            )
        )
    return phases


def _resolve_repetition_bounds(
    repetition: RepetitionActionRecordV2,
) -> tuple[float, float, int | None, int | None] | None:
    start_ts = _safe_float(repetition.start_ts)
    end_ts = _safe_float(repetition.end_ts)
    if start_ts is None or end_ts is None or end_ts <= start_ts:
        return None
    start_frame = repetition.start_frame if repetition.start_frame is not None else None
    end_frame = repetition.end_frame if repetition.end_frame is not None else None
    if (
        start_frame is not None
        and end_frame is not None
        and isinstance(start_frame, int)
        and isinstance(end_frame, int)
        and end_frame <= start_frame
    ):
        start_frame = None
        end_frame = None
    return (start_ts, end_ts, start_frame, end_frame)


def _segment_points(
    start: float,
    end: float,
    segments: list[tuple[str, float]],
) -> list[float]:
    total = sum(weight for _, weight in segments)
    if total <= 0:
        return [start, end]
    cursor = start
    points = [start]
    span = end - start
    for _, weight in segments[:-1]:
        cursor += span * (weight / total)
        points.append(cursor)
    points.append(end)
    return points


def _resolve_phase_discipline(discipline: str, session_discipline: str | None) -> str:
    normalized_session = (session_discipline or "").strip().lower()
    if normalized_session in {"pace_bowling", "spin_bowling"}:
        return normalized_session
    normalized = (discipline or "").strip().lower()
    if normalized == "bowling":
        return "pace_bowling"
    return normalized


def _resolve_ball_evidence(
    ball_tracking: dict[str, Any] | None, *, evidence_type: str
) -> dict[str, Any] | None:
    trajectory = ball_tracking.get("trajectory") if isinstance(ball_tracking, dict) else None
    if not isinstance(trajectory, dict):
        return None
    if evidence_type == "release":
        payload = trajectory.get("release_point")
    else:
        payload = trajectory.get("impact_point")
    return payload if isinstance(payload, dict) else None


def _within_ts(start_ts: float, end_ts: float, value: Any) -> bool:
    timestamp = _safe_float(value)
    if timestamp is None:
        return False
    return start_ts <= timestamp <= end_ts


def _safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric

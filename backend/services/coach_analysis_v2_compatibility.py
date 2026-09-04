from __future__ import annotations

import math
from numbers import Real
from typing import Any

from backend.domain.coach_analysis_v2_contract import (
    COACH_ANALYSIS_V2_SCHEMA_VERSION,
    DEFAULT_POSE_METRIC_VERSION,
    LOW_CONFIDENCE_THRESHOLD,
    CameraRequirements,
    CaptureProfile,
    CoachingAnalysisV2Contract,
    CoachingMetricResultV2,
    CompatibilityReasonCode,
    EvidenceRef,
    FrameRef,
    LongitudinalCompareMetadata,
    MetricCompareEligibilityResult,
    TimestampRef,
    ValidityState,
)

_METRIC_UNITS: dict[str, str] = {
    "head_stability_score": "score",
    "balance_drift_score": "score",
    "front_knee_brace_score": "score",
    "hip_shoulder_separation_timing": "seconds",
    "elbow_drop_score": "score",
}


def infer_validity_state(
    *,
    raw_value: Any,
    confidence_score: float | None = None,
    visibility_sufficient: bool = True,
    camera_view: str | None = None,
    camera_requirements: CameraRequirements | None = None,
    sample_fps: float | None = None,
    repetitions_count: int | None = None,
    min_repetitions: int | None = None,
    valid_range: tuple[float, float] | None = None,
) -> tuple[ValidityState, str | None]:
    if (
        camera_requirements
        and camera_requirements.supported_views
        and (camera_view is None or camera_view not in camera_requirements.supported_views)
    ):
        return (
            ValidityState.UNSUPPORTED_CAMERA_VIEW,
            "Capture camera view is not supported for this contract.",
        )
    if (
        camera_requirements
        and camera_requirements.minimum_sample_fps is not None
        and (sample_fps is None or sample_fps < camera_requirements.minimum_sample_fps)
    ):
        return (
            ValidityState.INSUFFICIENT_FRAME_RATE,
            "Sample FPS is below the minimum required for safe analysis.",
        )
    if min_repetitions is not None and (
        repetitions_count is None or repetitions_count < min_repetitions
    ):
        return (
            ValidityState.INSUFFICIENT_REPETITIONS,
            "Not enough repetitions are available for this measurement.",
        )
    if not visibility_sufficient:
        return (
            ValidityState.INSUFFICIENT_VISIBILITY,
            "Visibility was insufficient for a reliable measurement.",
        )
    if raw_value is None:
        return (
            ValidityState.NOT_MEASURABLE,
            "The metric could not be measured from the available input.",
        )
    numeric_raw_value = _safe_float(raw_value)
    if (
        numeric_raw_value is not None
        and valid_range
        and (numeric_raw_value < valid_range[0] or numeric_raw_value > valid_range[1])
    ):
        return (
            ValidityState.INVALID_RANGE,
            "Measured value falls outside the supported validation range.",
        )
    if confidence_score is not None and confidence_score < LOW_CONFIDENCE_THRESHOLD:
        return (
            ValidityState.LOW_CONFIDENCE,
            "Measurement is available but confidence is below the preferred threshold.",
        )
    return (ValidityState.VALID, None)


def build_capture_profile(
    *,
    discipline: str,
    metric_version: str,
    sample_fps: float | None,
    source_video_fps: float | None,
    camera_view: str | None,
    source_model: str | None,
    resolution_class: str | None = None,
    effective_analysis_fps: float | None = None,
) -> CaptureProfile:
    compatibility_flags: list[str] = []
    if camera_view:
        compatibility_flags.append(f"camera_view:{camera_view}")
    if sample_fps is not None:
        compatibility_flags.append(f"sample_fps:{sample_fps}")
    if effective_analysis_fps is not None:
        compatibility_flags.append(f"effective_analysis_fps:{effective_analysis_fps}")
    if resolution_class:
        compatibility_flags.append(f"resolution_class:{resolution_class}")
    return CaptureProfile(
        camera_view=camera_view,
        sample_fps=sample_fps,
        effective_analysis_fps=effective_analysis_fps
        if effective_analysis_fps is not None
        else sample_fps,
        source_video_fps=source_video_fps,
        resolution_class=resolution_class,
        analysis_mode=discipline,
        discipline=discipline,
        metric_version=metric_version,
        source_model=source_model,
        compatibility_flags=compatibility_flags,
    )


def build_analysis_v2_contract(
    *,
    discipline: str,
    sample_fps: float,
    source_video_fps: float | None,
    camera_view: str | None,
    source_model: str | None,
    metrics_payload: dict[str, Any],
    metric_version: str = DEFAULT_POSE_METRIC_VERSION,
) -> CoachingAnalysisV2Contract:
    capture_profile = build_capture_profile(
        discipline=discipline,
        metric_version=metric_version,
        sample_fps=sample_fps,
        source_video_fps=source_video_fps,
        camera_view=camera_view,
        source_model=source_model,
    )
    metric_results = build_metric_results(
        metrics_payload=metrics_payload,
        discipline=discipline,
        metric_version=metric_version,
        capture_profile=capture_profile,
        sample_fps=sample_fps,
    )
    overall_state, _ = infer_validity_state(
        raw_value=metric_results or None,
        confidence_score=_safe_float(metrics_payload.get("detection_rate_percent"), scale=100.0),
        visibility_sufficient=bool(metrics_payload.get("frames_with_pose", 0)),
    )
    return CoachingAnalysisV2Contract(
        schema_version=COACH_ANALYSIS_V2_SCHEMA_VERSION,
        capture_profile=capture_profile,
        validity_state=overall_state,
        metric_results=metric_results,
        repetitions=[],
        phases=[],
        longitudinal_compare=LongitudinalCompareMetadata(),
    )


def build_metric_results(
    *,
    metrics_payload: dict[str, Any],
    discipline: str,
    metric_version: str,
    capture_profile: CaptureProfile,
    sample_fps: float,
) -> list[CoachingMetricResultV2]:
    metrics = metrics_payload.get("metrics", {})
    if not isinstance(metrics, dict):
        return []

    evidence_map = metrics_payload.get("evidence", {})
    if not isinstance(evidence_map, dict):
        evidence_map = {}

    frames_with_pose = _safe_int(metrics_payload.get("frames_with_pose"))
    sampled_frames = _safe_int(metrics_payload.get("sampled_frames"))
    results: list[CoachingMetricResultV2] = []

    for metric_id, raw_metric in metrics.items():
        if not isinstance(raw_metric, dict):
            continue

        raw_value = raw_metric.get("score")
        num_frames = _safe_int(raw_metric.get("num_frames"))
        confidence = _estimate_metric_confidence(
            num_frames=num_frames,
            frames_with_pose=frames_with_pose,
            sampled_frames=sampled_frames,
        )
        camera_requirements = CameraRequirements()
        validity_state, unavailable_reason = infer_validity_state(
            raw_value=raw_value,
            confidence_score=confidence,
            visibility_sufficient=num_frames > 0,
            camera_view=capture_profile.camera_view,
            camera_requirements=camera_requirements,
            sample_fps=sample_fps,
        )
        evidence_payload = evidence_map.get(metric_id)
        results.append(
            CoachingMetricResultV2(
                metric_version=metric_version,
                metric_id=str(metric_id),
                discipline=discipline,
                raw_value=raw_value,
                unit=_METRIC_UNITS.get(str(metric_id)),
                normalized_score=_normalized_score_for_metric(str(metric_id), raw_value),
                confidence_score=confidence,
                validity_state=validity_state,
                unavailable_reason=unavailable_reason,
                limitations=_build_metric_limitations(
                    validity_state=validity_state,
                    sample_fps=sample_fps,
                    confidence_score=confidence,
                ),
                camera_requirements=camera_requirements,
                source_model=capture_profile.source_model,
                capture_profile=capture_profile,
                evidence_refs=_build_evidence_refs(str(metric_id), evidence_payload),
                timestamp_refs=_build_timestamp_refs(evidence_payload),
                frame_refs=_build_frame_refs(evidence_payload),
                aggregate_stats=_extract_aggregate_stats(raw_metric),
            )
        )
    return results


def get_v2_contract(payload: dict[str, Any] | None) -> CoachingAnalysisV2Contract | None:
    if not isinstance(payload, dict):
        return None
    v2_payload = payload.get("v2")
    if not isinstance(v2_payload, dict):
        return None
    return CoachingAnalysisV2Contract.model_validate(v2_payload)


def extract_metric_results(payload: dict[str, Any] | None) -> list[CoachingMetricResultV2]:
    contract = get_v2_contract(payload)
    if contract is None:
        return []
    return contract.metric_results


def compare_metric_results(
    left: CoachingMetricResultV2 | dict[str, Any],
    right: CoachingMetricResultV2 | dict[str, Any],
    *,
    player_id_left: str | None,
    player_id_right: str | None,
) -> MetricCompareEligibilityResult:
    left_metric = _as_metric_result(left)
    right_metric = _as_metric_result(right)
    reasons: list[str] = []
    reason_codes: list[CompatibilityReasonCode] = []

    if not player_id_left or not player_id_right:
        _add_reason(
            reason_codes,
            reasons,
            CompatibilityReasonCode.MISSING_PLAYER_ID,
            "Player identity is required for longitudinal comparison.",
        )
    elif player_id_left != player_id_right:
        _add_reason(
            reason_codes,
            reasons,
            CompatibilityReasonCode.PLAYER_ID_MISMATCH,
            "Metric results belong to different players.",
        )

    if left_metric.metric_id != right_metric.metric_id:
        _add_reason(
            reason_codes,
            reasons,
            CompatibilityReasonCode.METRIC_ID_MISMATCH,
            "Metric identifiers do not match.",
        )
    if left_metric.discipline != right_metric.discipline:
        _add_reason(
            reason_codes,
            reasons,
            CompatibilityReasonCode.DISCIPLINE_MISMATCH,
            "Disciplines do not match.",
        )
    if left_metric.metric_version != right_metric.metric_version:
        _add_reason(
            reason_codes,
            reasons,
            CompatibilityReasonCode.METRIC_VERSION_MISMATCH,
            "Metric versions do not match.",
        )
    if left_metric.validity_state not in {ValidityState.VALID, ValidityState.LOW_CONFIDENCE}:
        _add_reason(
            reason_codes,
            reasons,
            CompatibilityReasonCode.INCOMPATIBLE_VALIDITY_STATE,
            f"Left metric is not comparable in state {left_metric.validity_state}.",
        )
    if right_metric.validity_state not in {ValidityState.VALID, ValidityState.LOW_CONFIDENCE}:
        _add_reason(
            reason_codes,
            reasons,
            CompatibilityReasonCode.INCOMPATIBLE_VALIDITY_STATE,
            f"Right metric is not comparable in state {right_metric.validity_state}.",
        )

    _compare_capture_profiles(
        left_metric.capture_profile,
        right_metric.capture_profile,
        reason_codes=reason_codes,
        reasons=reasons,
    )

    return MetricCompareEligibilityResult(
        comparable=not reasons,
        reason_codes=reason_codes,
        reasons=reasons,
        comparison_identity=(
            {
                "player_id": player_id_left,
                "discipline": left_metric.discipline,
                "metric_id": left_metric.metric_id,
                "metric_version": left_metric.metric_version,
            }
            if not reasons and player_id_left
            else None
        ),
    )


def _compare_capture_profiles(
    left: CaptureProfile | None,
    right: CaptureProfile | None,
    *,
    reason_codes: list[CompatibilityReasonCode],
    reasons: list[str],
) -> None:
    if left is None or right is None:
        _add_reason(
            reason_codes,
            reasons,
            CompatibilityReasonCode.MISSING_CAPTURE_PROFILE,
            "Capture profile metadata is required for safe comparison.",
        )
        return

    critical_fields = (
        ("camera_view", CompatibilityReasonCode.MISSING_CAPTURE_METADATA),
        ("sample_fps", CompatibilityReasonCode.MISSING_CAPTURE_METADATA),
        ("effective_analysis_fps", CompatibilityReasonCode.MISSING_CAPTURE_METADATA),
        ("capture_profile_version", CompatibilityReasonCode.MISSING_CAPTURE_METADATA),
        ("source_model", CompatibilityReasonCode.MISSING_CAPTURE_METADATA),
    )
    for field_name, code in critical_fields:
        if getattr(left, field_name) is None or getattr(right, field_name) is None:
            _add_reason(
                reason_codes,
                reasons,
                code,
                f"Capture metadata field '{field_name}' is missing.",
            )

    if left.capture_profile_version != right.capture_profile_version:
        _add_reason(
            reason_codes,
            reasons,
            CompatibilityReasonCode.CAPTURE_PROFILE_VERSION_MISMATCH,
            "Capture profile versions do not match.",
        )
    if left.camera_view != right.camera_view:
        _add_reason(
            reason_codes,
            reasons,
            CompatibilityReasonCode.CAMERA_VIEW_MISMATCH,
            "Camera views do not match.",
        )
    if left.sample_fps != right.sample_fps:
        _add_reason(
            reason_codes,
            reasons,
            CompatibilityReasonCode.SAMPLE_FPS_MISMATCH,
            "Sample FPS values do not match.",
        )
    if left.effective_analysis_fps != right.effective_analysis_fps:
        _add_reason(
            reason_codes,
            reasons,
            CompatibilityReasonCode.EFFECTIVE_FPS_MISMATCH,
            "Effective analysis FPS values do not match.",
        )
    if (
        left.source_video_fps is not None
        and right.source_video_fps is not None
        and left.source_video_fps != right.source_video_fps
    ):
        _add_reason(
            reason_codes,
            reasons,
            CompatibilityReasonCode.SOURCE_VIDEO_FPS_MISMATCH,
            "Source video FPS values do not match.",
        )
    if left.resolution_class != right.resolution_class:
        _add_reason(
            reason_codes,
            reasons,
            CompatibilityReasonCode.RESOLUTION_CLASS_MISMATCH,
            "Resolution classes do not match.",
        )
    if left.source_model != right.source_model:
        _add_reason(
            reason_codes,
            reasons,
            CompatibilityReasonCode.SOURCE_MODEL_MISMATCH,
            "Source model identifiers do not match.",
        )


def _as_metric_result(metric: CoachingMetricResultV2 | dict[str, Any]) -> CoachingMetricResultV2:
    if isinstance(metric, CoachingMetricResultV2):
        return metric
    return CoachingMetricResultV2.model_validate(metric)


def _add_reason(
    reason_codes: list[CompatibilityReasonCode],
    reasons: list[str],
    code: CompatibilityReasonCode,
    message: str,
) -> None:
    reason_codes.append(code)
    reasons.append(message)


def _estimate_metric_confidence(
    *, num_frames: int, frames_with_pose: int, sampled_frames: int
) -> float | None:
    if sampled_frames <= 0:
        return None
    coverage_ratio = frames_with_pose / sampled_frames if sampled_frames > 0 else 0.0
    frame_ratio = num_frames / max(frames_with_pose, 1) if frames_with_pose > 0 else 0.0
    return round(max(0.0, min(1.0, (coverage_ratio + frame_ratio) / 2)), 3)


def _build_metric_limitations(
    *,
    validity_state: ValidityState,
    sample_fps: float,
    confidence_score: float | None,
) -> list[str]:
    limitations: list[str] = []
    if confidence_score is not None and confidence_score < LOW_CONFIDENCE_THRESHOLD:
        limitations.append(
            "Low confidence measurement; confirm with additional compatible capture."
        )
    if sample_fps < 5:
        limitations.append("Low sampling rate may reduce motion timing fidelity.")
    if validity_state != ValidityState.VALID:
        limitations.append(f"Metric validity state: {validity_state}.")
    return limitations


def _build_evidence_refs(metric_id: str, evidence_payload: Any) -> list[EvidenceRef]:
    if not isinstance(evidence_payload, dict):
        return []
    return [
        EvidenceRef(
            ref_type="metric_evidence",
            ref_id=metric_id,
            label=f"{metric_id}:evidence",
        )
    ]


def _build_timestamp_refs(evidence_payload: Any) -> list[TimestampRef]:
    if not isinstance(evidence_payload, dict):
        return []
    refs: list[TimestampRef] = []
    for segment in evidence_payload.get("bad_segments", []):
        if not isinstance(segment, dict):
            continue
        refs.append(
            TimestampRef(
                start_ts=_safe_float(segment.get("start_timestamp_s")),
                end_ts=_safe_float(segment.get("end_timestamp_s")),
            )
        )
    for frame in evidence_payload.get("worst_frames", []):
        if not isinstance(frame, dict):
            continue
        ts = _safe_float(frame.get("timestamp_s"))
        if ts is not None:
            refs.append(TimestampRef(start_ts=ts, end_ts=ts))
    return refs


def _build_frame_refs(evidence_payload: Any) -> list[FrameRef]:
    if not isinstance(evidence_payload, dict):
        return []
    refs: list[FrameRef] = []
    worst_frames = []
    for frame in evidence_payload.get("worst_frames", []):
        if not isinstance(frame, dict):
            continue
        frame_num = _safe_int(frame.get("frame_num"))
        if frame_num >= 0:
            worst_frames.append(frame_num)
    if worst_frames:
        refs.append(FrameRef(frame_numbers=worst_frames))
    for segment in evidence_payload.get("bad_segments", []):
        if not isinstance(segment, dict):
            continue
        refs.append(
            FrameRef(
                start_frame=_safe_optional_int(segment.get("start_frame")),
                end_frame=_safe_optional_int(segment.get("end_frame")),
            )
        )
    return refs


def _extract_aggregate_stats(raw_metric: dict[str, Any]) -> dict[str, Any] | None:
    aggregate_stats = {
        key: value
        for key, value in raw_metric.items()
        if key
        not in {"score", "per_frame_scores", "per_frame_frame_nums", "per_frame_timestamps_s"}
    }
    return aggregate_stats or None


def _normalized_score_for_metric(metric_id: str, raw_value: Any) -> float | None:
    if metric_id == "hip_shoulder_separation_timing":
        return None
    if isinstance(raw_value, Real):
        raw = float(raw_value)
        if 0.0 <= raw <= 1.0:
            return raw
    return None


def _safe_float(value: Any, scale: float | None = None) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        result = float(value)
    elif isinstance(value, float):
        if not math.isfinite(value):
            return None
        result = value
    elif isinstance(value, Real):
        result = float(value)
        if not math.isfinite(result):
            return None
    else:
        return None
    if scale and scale != 0:
        result /= scale
    return result


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return 0
        return int(value)
    return 0


def _safe_optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return int(value)
    return None

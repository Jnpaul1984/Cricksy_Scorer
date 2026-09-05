from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import mean, median, pstdev
from typing import Any

from backend.domain.coach_analysis_v2_contract import (
    CameraRequirements,
    CaptureProfile,
    CoachingMetricResultV2,
    EvidenceRef,
    FrameRef,
    PhaseRecordV2,
    RepetitionActionRecordV2,
    TimestampRef,
    ValidityState,
)
from backend.services.coach_analysis_v2_compatibility import (
    has_measurable_validity_state,
    infer_validity_state,
    resolve_metric_unavailability,
    sanitize_metric_output,
)
from backend.services.coach_strength_consistency import build_metric_consistency

_BOWLING_V2_METRIC_VERSION = "bowling_pose_metrics.v2.0.0"
_PACE_BOWLING_METRIC_IDS = {
    "pace_bowling_approach_head_stability_score",
    "pace_bowling_gather_balance_drift_ratio",
    "pace_bowling_front_foot_contact_front_knee_angle_deg",
    "pace_bowling_release_proxy_bowling_arm_angle_deg",
    "pace_bowling_release_proxy_trunk_lean_deg",
    "pace_bowling_follow_through_balance_drift_ratio",
}
_SPIN_BOWLING_METRIC_IDS = {
    "spin_bowling_approach_head_stability_score",
    "spin_bowling_coil_balance_drift_ratio",
    "spin_bowling_pivot_shoulder_hip_separation_deg",
    "spin_bowling_delivery_stride_head_base_offset_ratio",
    "spin_bowling_release_proxy_bowling_arm_angle_deg",
    "spin_bowling_follow_through_balance_drift_ratio",
}
_ALL_BOWLING_V2_METRIC_IDS = _PACE_BOWLING_METRIC_IDS | _SPIN_BOWLING_METRIC_IDS
_SUPPORTED_BOWLING_DISCIPLINES = {"pace_bowling", "spin_bowling"}


@dataclass(frozen=True)
class _NormalizedFrame:
    frame_num: int
    timestamp_s: float | None
    detected: bool
    keypoints: dict[str, tuple[float, float]]


@dataclass(frozen=True)
class _MetricSample:
    repetition_id: str
    phase_id: str | None
    value: float
    confidence: float
    visibility: float
    start_ts: float | None
    end_ts: float | None
    start_frame: int | None
    end_frame: int | None
    evidence_refs: list[EvidenceRef] = field(default_factory=list)


def attach_bowling_v2_metric_pack(
    *,
    results_payload: dict[str, Any],
    discipline: str,
    session_discipline: str | None,
    frames: list[dict[str, Any]] | None,
    sample_fps: float | None,
    source_video_fps: float | None,
    camera_view: str | None,
    source_model: str | None,
) -> dict[str, Any]:
    if (discipline or "").strip().lower() != "bowling":
        return results_payload
    v2_payload = results_payload.get("v2")
    if not isinstance(v2_payload, dict):
        return results_payload

    repetitions = _parse_repetitions(v2_payload.get("repetitions"))
    phases = _parse_phases(v2_payload.get("phases"))
    capture_profile = _parse_capture_profile(v2_payload.get("capture_profile"))
    metric_discipline = _resolve_metric_discipline(
        session_discipline=session_discipline,
        capture_profile=capture_profile,
        phases=phases,
    )
    if metric_discipline is None:
        return results_payload

    phase_lookup = _build_phase_lookup(phases)
    normalized_frames = _normalize_frames(frames or [])
    metric_results_payload = v2_payload.get("metric_results")
    existing_results = metric_results_payload if isinstance(metric_results_payload, list) else []

    built_results = _build_bowling_metric_results(
        metric_discipline=metric_discipline,
        repetitions=repetitions,
        phase_lookup=phase_lookup,
        frames=normalized_frames,
        sample_fps=sample_fps,
        source_video_fps=source_video_fps,
        camera_view=camera_view,
        source_model=source_model,
        capture_profile=capture_profile,
    )

    retained = [
        item
        for item in existing_results
        if not (
            isinstance(item, dict)
            and isinstance(item.get("metric_id"), str)
            and item.get("metric_id") in _ALL_BOWLING_V2_METRIC_IDS
        )
    ]
    v2_payload["metric_results"] = [
        *retained,
        *[item.model_dump(mode="json") for item in built_results],
    ]

    results_payload.setdefault("meta", {})
    if isinstance(results_payload["meta"], dict):
        results_payload["meta"]["bowling_v2_metric_pack"] = _build_metric_pack_summary(
            built_results,
            metric_discipline=metric_discipline,
        )

    insights = build_bowling_v2_findings_insights(built_results)
    findings_payload = results_payload.get("findings")
    if isinstance(findings_payload, dict):
        findings_payload["bowling_v2"] = insights
    report_payload = results_payload.get("report")
    if isinstance(report_payload, dict):
        report_payload["bowling_v2"] = insights

    return results_payload


def build_bowling_v2_findings_insights(
    metric_results: list[CoachingMetricResultV2],
) -> dict[str, Any]:
    strengths: list[dict[str, str]] = []
    concerns: list[dict[str, str]] = []
    limitations: list[dict[str, str]] = []
    for metric in metric_results:
        label = (
            metric.metric_id.replace("pace_bowling_", "")
            .replace("spin_bowling_", "")
            .replace("_", " ")
        )
        if (
            metric.validity_state == ValidityState.VALID
            and metric.classification_status == "STRONG"
        ):
            strengths.append({"metric_id": metric.metric_id, "summary": f"Strong {label}."})
        elif metric.validity_state == ValidityState.VALID:
            concerns.append({"metric_id": metric.metric_id, "summary": f"Refine {label}."})
        else:
            limitations.append(
                {
                    "metric_id": metric.metric_id,
                    "summary": metric.unavailable_reason
                    or (
                        "Measurement confidence was too low to treat this as a coaching weakness."
                        if metric.validity_state == ValidityState.LOW_CONFIDENCE
                        else "Metric unavailable for this capture."
                    ),
                }
            )
    return {
        "strengths": strengths,
        "concerns": concerns,
        "limitations": limitations,
    }


def _build_bowling_metric_results(
    *,
    metric_discipline: str,
    repetitions: list[RepetitionActionRecordV2],
    phase_lookup: dict[tuple[str, str], PhaseRecordV2],
    frames: list[_NormalizedFrame],
    sample_fps: float | None,
    source_video_fps: float | None,
    camera_view: str | None,
    source_model: str | None,
    capture_profile: CaptureProfile | None,
) -> list[CoachingMetricResultV2]:
    capture = _resolve_capture_profile(
        capture_profile=capture_profile,
        metric_discipline=metric_discipline,
        sample_fps=sample_fps,
        source_video_fps=source_video_fps,
        camera_view=camera_view,
        source_model=source_model,
    )
    if metric_discipline == "pace_bowling":
        return _build_pace_metric_results(
            repetitions=repetitions,
            phase_lookup=phase_lookup,
            frames=frames,
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture,
        )
    return _build_spin_metric_results(
        repetitions=repetitions,
        phase_lookup=phase_lookup,
        frames=frames,
        sample_fps=sample_fps,
        source_video_fps=source_video_fps,
        camera_view=camera_view,
        capture_profile=capture,
    )


def _build_pace_metric_results(
    *,
    repetitions: list[RepetitionActionRecordV2],
    phase_lookup: dict[tuple[str, str], PhaseRecordV2],
    frames: list[_NormalizedFrame],
    sample_fps: float | None,
    source_video_fps: float | None,
    camera_view: str | None,
    capture_profile: CaptureProfile,
) -> list[CoachingMetricResultV2]:
    repetitions_available = bool(repetitions)
    phases_available = bool(phase_lookup)
    candidate_repetition_count = sum(
        1
        for repetition in repetitions
        if str(repetition.action_type or "").strip().lower() == "bowling_delivery"
        and has_measurable_validity_state(repetition.validity_state)
    )
    return [
        _build_metric_result(
            metric_id="pace_bowling_approach_head_stability_score",
            metric_discipline="pace_bowling",
            phase="approach",
            unit="score",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("approach",),
                measure_fn=_measure_head_stability_score,
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture_profile,
            camera_requirements=CameraRequirements(
                supported_views=["side", "front", "behind"],
                minimum_sample_fps=6.0,
                minimum_source_video_fps=15.0,
            ),
            valid_range=(0.0, 1.0),
            classification_fn=lambda value: (
                "STRONG" if value >= 0.7 else "DEVELOPING" if value >= 0.55 else "NEEDS_ATTENTION"
            ),
            limitations=["Head stability score is a pose-only movement proxy over the approach."],
            repetitions_available=repetitions_available,
            phases_available=phases_available,
            candidate_repetition_count=candidate_repetition_count,
        ),
        _build_metric_result(
            metric_id="pace_bowling_gather_balance_drift_ratio",
            metric_discipline="pace_bowling",
            phase="gather",
            unit="ratio",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("gather",),
                measure_fn=_measure_balance_drift_ratio,
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture_profile,
            camera_requirements=CameraRequirements(
                supported_views=["side", "front", "behind"],
                minimum_sample_fps=6.0,
                minimum_source_video_fps=15.0,
            ),
            valid_range=(0.0, 1.5),
            classification_fn=lambda value: (
                "STRONG" if value <= 0.18 else "DEVELOPING" if value <= 0.28 else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Gather balance uses hip-to-ankle horizontal offset normalized by shoulder width."
            ],
            repetitions_available=repetitions_available,
            phases_available=phases_available,
            candidate_repetition_count=candidate_repetition_count,
        ),
        _build_metric_result(
            metric_id="pace_bowling_front_foot_contact_front_knee_angle_deg",
            metric_discipline="pace_bowling",
            phase="front_foot_contact",
            unit="degrees",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("front_foot_contact",),
                measure_fn=_measure_front_knee_angle_proxy,
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture_profile,
            camera_requirements=CameraRequirements(
                supported_views=["side", "front", "behind"],
                minimum_sample_fps=6.0,
                minimum_source_video_fps=15.0,
            ),
            valid_range=(40.0, 200.0),
            classification_fn=lambda value: (
                "STRONG"
                if 145.0 <= value <= 178.0
                else "DEVELOPING"
                if 130.0 <= value <= 185.0
                else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Lead-leg side is inferred as the straighter knee visible during front-foot contact."
            ],
            repetitions_available=repetitions_available,
            phases_available=phases_available,
            candidate_repetition_count=candidate_repetition_count,
        ),
        _build_metric_result(
            metric_id="pace_bowling_release_proxy_bowling_arm_angle_deg",
            metric_discipline="pace_bowling",
            phase="release_proxy_window",
            unit="degrees",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("release", "release_proxy_window"),
                measure_fn=_measure_bowling_arm_angle_deg,
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture_profile,
            camera_requirements=CameraRequirements(
                supported_views=["side", "front", "behind"],
                minimum_sample_fps=6.0,
                minimum_source_video_fps=15.0,
            ),
            valid_range=(0.0, 160.0),
            classification_fn=lambda value: (
                "STRONG" if value <= 35.0 else "DEVELOPING" if value <= 50.0 else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Arm angle is measured against vertical from shoulder to wrist.",
                "Without ball evidence this remains a release-proxy window, not an exact release claim.",
            ],
            repetitions_available=repetitions_available,
            phases_available=phases_available,
            candidate_repetition_count=candidate_repetition_count,
        ),
        _build_metric_result(
            metric_id="pace_bowling_release_proxy_trunk_lean_deg",
            metric_discipline="pace_bowling",
            phase="release_proxy_window",
            unit="degrees",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("release", "release_proxy_window"),
                measure_fn=_measure_trunk_lean_deg,
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture_profile,
            camera_requirements=CameraRequirements(
                supported_views=["side", "front", "behind"],
                minimum_sample_fps=6.0,
                minimum_source_video_fps=15.0,
            ),
            valid_range=(0.0, 90.0),
            classification_fn=lambda value: (
                "STRONG"
                if 5.0 <= value <= 35.0
                else "DEVELOPING"
                if value <= 45.0
                else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Trunk lean uses hip-midpoint to nose orientation and is sensitive to depth perspective."
            ],
            repetitions_available=repetitions_available,
            phases_available=phases_available,
            candidate_repetition_count=candidate_repetition_count,
        ),
        _build_metric_result(
            metric_id="pace_bowling_follow_through_balance_drift_ratio",
            metric_discipline="pace_bowling",
            phase="follow_through",
            unit="ratio",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("follow_through",),
                measure_fn=_measure_balance_drift_ratio,
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture_profile,
            camera_requirements=CameraRequirements(
                supported_views=["side", "front", "behind"],
                minimum_sample_fps=6.0,
                minimum_source_video_fps=15.0,
            ),
            valid_range=(0.0, 1.5),
            classification_fn=lambda value: (
                "STRONG" if value <= 0.25 else "DEVELOPING" if value <= 0.38 else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Follow-through balance uses hip-to-ankle horizontal offset as a recovery proxy."
            ],
            repetitions_available=repetitions_available,
            phases_available=phases_available,
            candidate_repetition_count=candidate_repetition_count,
        ),
    ]


def _build_spin_metric_results(
    *,
    repetitions: list[RepetitionActionRecordV2],
    phase_lookup: dict[tuple[str, str], PhaseRecordV2],
    frames: list[_NormalizedFrame],
    sample_fps: float | None,
    source_video_fps: float | None,
    camera_view: str | None,
    capture_profile: CaptureProfile,
) -> list[CoachingMetricResultV2]:
    repetitions_available = bool(repetitions)
    phases_available = bool(phase_lookup)
    candidate_repetition_count = sum(
        1
        for repetition in repetitions
        if str(repetition.action_type or "").strip().lower() == "bowling_delivery"
        and has_measurable_validity_state(repetition.validity_state)
    )
    return [
        _build_metric_result(
            metric_id="spin_bowling_approach_head_stability_score",
            metric_discipline="spin_bowling",
            phase="approach",
            unit="score",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("approach",),
                measure_fn=_measure_head_stability_score,
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture_profile,
            camera_requirements=CameraRequirements(
                supported_views=["side", "front", "behind"],
                minimum_sample_fps=6.0,
                minimum_source_video_fps=15.0,
            ),
            valid_range=(0.0, 1.0),
            classification_fn=lambda value: (
                "STRONG" if value >= 0.68 else "DEVELOPING" if value >= 0.52 else "NEEDS_ATTENTION"
            ),
            limitations=["Head stability score is a pose-only movement proxy over the approach."],
            repetitions_available=repetitions_available,
            phases_available=phases_available,
            candidate_repetition_count=candidate_repetition_count,
        ),
        _build_metric_result(
            metric_id="spin_bowling_coil_balance_drift_ratio",
            metric_discipline="spin_bowling",
            phase="coil",
            unit="ratio",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("coil",),
                measure_fn=_measure_balance_drift_ratio,
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture_profile,
            camera_requirements=CameraRequirements(
                supported_views=["side", "front", "behind"],
                minimum_sample_fps=6.0,
                minimum_source_video_fps=15.0,
            ),
            valid_range=(0.0, 1.5),
            classification_fn=lambda value: (
                "STRONG" if value <= 0.2 else "DEVELOPING" if value <= 0.32 else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Coil balance uses hip-to-ankle horizontal offset normalized by shoulder width."
            ],
            repetitions_available=repetitions_available,
            phases_available=phases_available,
            candidate_repetition_count=candidate_repetition_count,
        ),
        _build_metric_result(
            metric_id="spin_bowling_pivot_shoulder_hip_separation_deg",
            metric_discipline="spin_bowling",
            phase="pivot",
            unit="degrees",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("pivot",),
                measure_fn=_measure_shoulder_hip_separation_deg,
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture_profile,
            camera_requirements=CameraRequirements(
                supported_views=["side", "front", "behind"],
                minimum_sample_fps=6.0,
                minimum_source_video_fps=15.0,
            ),
            valid_range=(0.0, 90.0),
            classification_fn=lambda value: (
                "STRONG"
                if 12.0 <= value <= 40.0
                else "DEVELOPING"
                if 8.0 <= value <= 55.0
                else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Pivot rotation uses the visible shoulder-versus-hip orientation gap and does not estimate wrist or finger action."
            ],
            repetitions_available=repetitions_available,
            phases_available=phases_available,
            candidate_repetition_count=candidate_repetition_count,
        ),
        _build_metric_result(
            metric_id="spin_bowling_delivery_stride_head_base_offset_ratio",
            metric_discipline="spin_bowling",
            phase="delivery_stride",
            unit="ratio",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("delivery_stride",),
                measure_fn=_measure_head_base_offset_ratio,
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture_profile,
            camera_requirements=CameraRequirements(
                supported_views=["side", "front", "behind"],
                minimum_sample_fps=6.0,
                minimum_source_video_fps=15.0,
            ),
            valid_range=(0.0, 2.0),
            classification_fn=lambda value: (
                "STRONG" if value <= 0.25 else "DEVELOPING" if value <= 0.4 else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Delivery-stride head alignment uses ankle midpoint as a front-foot stability proxy."
            ],
            repetitions_available=repetitions_available,
            phases_available=phases_available,
            candidate_repetition_count=candidate_repetition_count,
        ),
        _build_metric_result(
            metric_id="spin_bowling_release_proxy_bowling_arm_angle_deg",
            metric_discipline="spin_bowling",
            phase="release_proxy_window",
            unit="degrees",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("release", "release_proxy_window"),
                measure_fn=_measure_bowling_arm_angle_deg,
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture_profile,
            camera_requirements=CameraRequirements(
                supported_views=["side", "front", "behind"],
                minimum_sample_fps=6.0,
                minimum_source_video_fps=15.0,
            ),
            valid_range=(0.0, 160.0),
            classification_fn=lambda value: (
                "STRONG" if value <= 55.0 else "DEVELOPING" if value <= 70.0 else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Arm angle is measured against vertical from shoulder to wrist.",
                "This metric does not claim spin rate, seam axis, or wrist/finger release mechanics.",
            ],
            repetitions_available=repetitions_available,
            phases_available=phases_available,
            candidate_repetition_count=candidate_repetition_count,
        ),
        _build_metric_result(
            metric_id="spin_bowling_follow_through_balance_drift_ratio",
            metric_discipline="spin_bowling",
            phase="follow_through",
            unit="ratio",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("follow_through",),
                measure_fn=_measure_balance_drift_ratio,
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture_profile,
            camera_requirements=CameraRequirements(
                supported_views=["side", "front", "behind"],
                minimum_sample_fps=6.0,
                minimum_source_video_fps=15.0,
            ),
            valid_range=(0.0, 1.5),
            classification_fn=lambda value: (
                "STRONG" if value <= 0.3 else "DEVELOPING" if value <= 0.42 else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Follow-through balance uses hip-to-ankle horizontal offset as a recovery proxy."
            ],
            repetitions_available=repetitions_available,
            phases_available=phases_available,
            candidate_repetition_count=candidate_repetition_count,
        ),
    ]


def _build_metric_result(
    *,
    metric_id: str,
    metric_discipline: str,
    phase: str,
    unit: str,
    samples: list[_MetricSample],
    sample_fps: float | None,
    source_video_fps: float | None,
    camera_view: str | None,
    capture_profile: CaptureProfile,
    camera_requirements: CameraRequirements,
    valid_range: tuple[float, float],
    classification_fn: Any,
    limitations: list[str],
    repetitions_available: bool = True,
    phases_available: bool = True,
    candidate_repetition_count: int | None = None,
    unavailable_hint: str | None = None,
) -> CoachingMetricResultV2:
    values = [sample.value for sample in samples]
    raw_value = round(mean(values), 4) if values else None
    avg_confidence = round(mean([sample.confidence for sample in samples]), 3) if samples else None
    avg_visibility = mean([sample.visibility for sample in samples]) if samples else 0.0

    validity_state, unavailable_reason = infer_validity_state(
        raw_value=raw_value,
        confidence_score=avg_confidence,
        visibility_sufficient=bool(samples and avg_visibility >= 0.55),
        camera_view=camera_view,
        camera_requirements=camera_requirements,
        sample_fps=sample_fps,
        repetitions_count=len(samples),
        min_repetitions=1,
        valid_range=valid_range,
    )
    if (
        camera_requirements.minimum_source_video_fps is not None
        and source_video_fps is not None
        and source_video_fps < camera_requirements.minimum_source_video_fps
    ):
        validity_state = ValidityState.INSUFFICIENT_FRAME_RATE
        unavailable_reason = (
            f"Source FPS {source_video_fps:.2f} is below minimum "
            f"{camera_requirements.minimum_source_video_fps:.2f}."
        )

    validity_state, unavailable_reason = resolve_metric_unavailability(
        validity_state=validity_state,
        unavailable_reason=unavailable_reason,
        repetitions_available=repetitions_available,
        phases_available=phases_available,
        unavailable_hint=unavailable_hint,
    )
    normalized_score = raw_value if unit == "score" and isinstance(raw_value, float) else None
    safe_raw_value, safe_normalized_score, safe_repetition_values = sanitize_metric_output(
        validity_state=validity_state,
        raw_value=raw_value,
        normalized_score=normalized_score,
        repetition_values=[round(value, 4) for value in values],
    )
    aggregate_stats = _aggregate_stats(
        values,
        candidate_repetition_count or len(samples),
        measurable=has_measurable_validity_state(validity_state),
    )
    classification_status = (
        classification_fn(safe_raw_value)
        if safe_raw_value is not None and has_measurable_validity_state(validity_state)
        else None
    )
    consistency = build_metric_consistency(
        metric_id=metric_id,
        unit=unit,
        samples=samples,
        valid_range=valid_range,
        classification_fn=classification_fn,
        validity_state=validity_state,
        confidence_score=avg_confidence,
        candidate_repetition_count=candidate_repetition_count,
        unavailable_reason=unavailable_reason,
    )
    metric_limitations = list(limitations)
    if validity_state != ValidityState.VALID:
        metric_limitations.append(f"Metric validity state: {validity_state.value}.")

    return CoachingMetricResultV2(
        metric_version=_BOWLING_V2_METRIC_VERSION,
        metric_id=metric_id,
        discipline=metric_discipline,
        action_type="bowling_delivery",
        phase=phase,
        raw_value=safe_raw_value,
        unit=unit,
        normalized_score=safe_normalized_score,
        classification_status=classification_status,
        confidence_score=avg_confidence,
        validity_state=validity_state,
        unavailable_reason=unavailable_reason,
        limitations=metric_limitations,
        camera_requirements=camera_requirements,
        source_model=capture_profile.source_model,
        capture_profile=capture_profile,
        evidence_refs=_evidence_refs(samples),
        timestamp_refs=_timestamp_refs(samples),
        frame_refs=_frame_refs(samples),
        repetition_values=safe_repetition_values,
        aggregate_stats=aggregate_stats,
        consistency=consistency,
    )


def _aggregate_stats(
    values: list[float], repetition_count: int, *, measurable: bool
) -> dict[str, Any] | None:
    if not values or not measurable:
        return {"count": 0, "valid_repetition_count": 0, "repetition_count": repetition_count}
    payload: dict[str, Any] = {
        "count": len(values),
        "valid_repetition_count": len(values),
        "repetition_count": repetition_count,
        "mean": round(mean(values), 4),
        "median": round(median(values), 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "spread": round(pstdev(values), 4) if len(values) > 1 else 0.0,
    }
    payload["repeatability"] = "stable" if payload["spread"] <= 0.08 else "variable"
    return payload


def _single_phase_metric(
    *,
    repetitions: list[RepetitionActionRecordV2],
    phase_lookup: dict[tuple[str, str], PhaseRecordV2],
    frames: list[_NormalizedFrame],
    phase_names: tuple[str, ...],
    measure_fn: Any,
) -> list[_MetricSample]:
    samples: list[_MetricSample] = []
    for repetition in repetitions:
        if str(repetition.action_type or "").strip().lower() != "bowling_delivery":
            continue
        if not has_measurable_validity_state(repetition.validity_state):
            continue
        phase = _phase_for_names(repetition.repetition_id, phase_lookup, phase_names)
        if phase is None:
            continue
        if not has_measurable_validity_state(phase.validity_state):
            continue
        window = _window_frames(frames, phase)
        value, visibility = measure_fn(window)
        if value is None:
            continue
        samples.append(
            _MetricSample(
                repetition_id=repetition.repetition_id,
                phase_id=phase.phase_id,
                value=value,
                confidence=_window_confidence(repetition, phase, visibility),
                visibility=visibility,
                start_ts=phase.start_ts,
                end_ts=phase.end_ts,
                start_frame=phase.start_frame,
                end_frame=phase.end_frame,
                evidence_refs=list(phase.evidence_refs),
            )
        )
    return samples


def _window_confidence(
    repetition: RepetitionActionRecordV2,
    phase: PhaseRecordV2,
    visibility: float,
) -> float:
    rep_conf = (
        repetition.segmentation_confidence
        if repetition.segmentation_confidence is not None
        else 0.58
    )
    phase_conf = phase.confidence if phase.confidence is not None else 0.58
    confidence = rep_conf * 0.45 + phase_conf * 0.4 + visibility * 0.15
    return round(max(0.0, min(1.0, confidence)), 3)


def _measure_head_stability_score(window: list[_NormalizedFrame]) -> tuple[float | None, float]:
    movement_values: list[float] = []
    prev_nose: tuple[float, float] | None = None
    for frame in window:
        if not frame.detected:
            continue
        nose = frame.keypoints.get("nose")
        left = frame.keypoints.get("left_shoulder")
        right = frame.keypoints.get("right_shoulder")
        if not (nose and left and right):
            continue
        shoulder_width = _distance(left, right)
        if shoulder_width <= 0.001:
            continue
        if prev_nose is not None:
            movement_values.append(_distance(prev_nose, nose) / shoulder_width)
        prev_nose = nose
    if not movement_values:
        return (None, 0.0)
    score = max(0.0, min(1.0, 1.0 - (mean(movement_values) / 0.35)))
    return (score, _visibility(window, movement_values))


def _measure_balance_drift_ratio(window: list[_NormalizedFrame]) -> tuple[float | None, float]:
    values: list[float] = []
    for frame in window:
        if not frame.detected:
            continue
        left_hip = frame.keypoints.get("left_hip")
        right_hip = frame.keypoints.get("right_hip")
        left_ankle = frame.keypoints.get("left_ankle")
        right_ankle = frame.keypoints.get("right_ankle")
        left_shoulder = frame.keypoints.get("left_shoulder")
        right_shoulder = frame.keypoints.get("right_shoulder")
        if not (
            left_hip
            and right_hip
            and left_ankle
            and right_ankle
            and left_shoulder
            and right_shoulder
        ):
            continue
        shoulder_width = _distance(left_shoulder, right_shoulder)
        if shoulder_width <= 0.001:
            continue
        hip_mid_x = (left_hip[0] + right_hip[0]) / 2.0
        ankle_mid_x = (left_ankle[0] + right_ankle[0]) / 2.0
        values.append(abs(hip_mid_x - ankle_mid_x) / shoulder_width)
    return (_mean_or_none(values), _visibility(window, values))


def _measure_front_knee_angle_proxy(window: list[_NormalizedFrame]) -> tuple[float | None, float]:
    values: list[float] = []
    for frame in window:
        if not frame.detected:
            continue
        left = _knee_angle(frame, "left")
        right = _knee_angle(frame, "right")
        candidates = [angle for angle in (left, right) if angle is not None]
        if not candidates:
            continue
        values.append(max(candidates))
    return (_mean_or_none(values), _visibility(window, values))


def _measure_bowling_arm_angle_deg(window: list[_NormalizedFrame]) -> tuple[float | None, float]:
    values: list[float] = []
    for frame in window:
        if not frame.detected:
            continue
        candidates: list[float] = []
        for side in ("left", "right"):
            shoulder = frame.keypoints.get(f"{side}_shoulder")
            wrist = frame.keypoints.get(f"{side}_wrist")
            if not (shoulder and wrist):
                continue
            vector = (wrist[0] - shoulder[0], wrist[1] - shoulder[1])
            magnitude = math.sqrt(vector[0] ** 2 + vector[1] ** 2)
            if magnitude <= 0.001:
                continue
            cos_theta = max(-1.0, min(1.0, (-vector[1]) / magnitude))
            candidates.append(math.degrees(math.acos(cos_theta)))
        if candidates:
            values.append(min(candidates))
    return (_mean_or_none(values), _visibility(window, values))


def _measure_trunk_lean_deg(window: list[_NormalizedFrame]) -> tuple[float | None, float]:
    values: list[float] = []
    for frame in window:
        if not frame.detected:
            continue
        nose = frame.keypoints.get("nose")
        left_hip = frame.keypoints.get("left_hip")
        right_hip = frame.keypoints.get("right_hip")
        if not (nose and left_hip and right_hip):
            continue
        hip_mid = ((left_hip[0] + right_hip[0]) / 2.0, (left_hip[1] + right_hip[1]) / 2.0)
        vector = (nose[0] - hip_mid[0], nose[1] - hip_mid[1])
        magnitude = math.sqrt(vector[0] ** 2 + vector[1] ** 2)
        if magnitude <= 0.001:
            continue
        cos_theta = max(-1.0, min(1.0, (-vector[1]) / magnitude))
        values.append(math.degrees(math.acos(cos_theta)))
    return (_mean_or_none(values), _visibility(window, values))


def _measure_shoulder_hip_separation_deg(
    window: list[_NormalizedFrame],
) -> tuple[float | None, float]:
    values: list[float] = []
    for frame in window:
        if not frame.detected:
            continue
        left_hip = frame.keypoints.get("left_hip")
        right_hip = frame.keypoints.get("right_hip")
        left_shoulder = frame.keypoints.get("left_shoulder")
        right_shoulder = frame.keypoints.get("right_shoulder")
        if not (left_hip and right_hip and left_shoulder and right_shoulder):
            continue
        hip_angle = _line_orientation_deg(left_hip, right_hip)
        shoulder_angle = _line_orientation_deg(left_shoulder, right_shoulder)
        separation = abs(shoulder_angle - hip_angle)
        if separation > 90.0:
            separation = 180.0 - separation
        values.append(separation)
    return (_mean_or_none(values), _visibility(window, values))


def _measure_head_base_offset_ratio(window: list[_NormalizedFrame]) -> tuple[float | None, float]:
    values: list[float] = []
    for frame in window:
        if not frame.detected:
            continue
        nose = frame.keypoints.get("nose")
        left_ankle = frame.keypoints.get("left_ankle")
        right_ankle = frame.keypoints.get("right_ankle")
        left_shoulder = frame.keypoints.get("left_shoulder")
        right_shoulder = frame.keypoints.get("right_shoulder")
        if not (nose and left_ankle and right_ankle and left_shoulder and right_shoulder):
            continue
        shoulder_width = _distance(left_shoulder, right_shoulder)
        if shoulder_width <= 0.001:
            continue
        base_mid_x = (left_ankle[0] + right_ankle[0]) / 2.0
        values.append(abs(nose[0] - base_mid_x) / shoulder_width)
    return (_mean_or_none(values), _visibility(window, values))


def _knee_angle(frame: _NormalizedFrame, side: str) -> float | None:
    hip = frame.keypoints.get(f"{side}_hip")
    knee = frame.keypoints.get(f"{side}_knee")
    ankle = frame.keypoints.get(f"{side}_ankle")
    if not (hip and knee and ankle):
        return None
    return _angle_degrees(hip, knee, ankle)


def _build_metric_pack_summary(
    metric_results: list[CoachingMetricResultV2], *, metric_discipline: str
) -> dict[str, Any]:
    valid_count = sum(
        1
        for metric in metric_results
        if metric.validity_state in {ValidityState.VALID, ValidityState.LOW_CONFIDENCE}
    )
    return {
        "enabled": True,
        "version": _BOWLING_V2_METRIC_VERSION,
        "discipline": metric_discipline,
        "metrics_count": len(metric_results),
        "valid_metrics_count": valid_count,
        "invalid_metrics_count": len(metric_results) - valid_count,
        "cost_classification": "low_cost_cpu_pose_math",
    }


def _resolve_metric_discipline(
    *,
    session_discipline: str | None,
    capture_profile: CaptureProfile | None,
    phases: list[PhaseRecordV2],
) -> str | None:
    for candidate in (
        (session_discipline or "").strip().lower(),
        (capture_profile.discipline or "").strip().lower() if capture_profile else "",
    ):
        if candidate in _SUPPORTED_BOWLING_DISCIPLINES:
            return candidate
    phase_names = {phase.phase_name for phase in phases}
    if phase_names & {"gather", "back_foot_contact", "front_foot_contact"}:
        return "pace_bowling"
    if phase_names & {"coil", "pivot"}:
        return "spin_bowling"
    return None


def _resolve_capture_profile(
    *,
    capture_profile: CaptureProfile | None,
    metric_discipline: str,
    sample_fps: float | None,
    source_video_fps: float | None,
    camera_view: str | None,
    source_model: str | None,
) -> CaptureProfile:
    if capture_profile is not None:
        return capture_profile.model_copy(update={"discipline": metric_discipline})
    return CaptureProfile(
        camera_view=camera_view,
        sample_fps=sample_fps,
        effective_analysis_fps=sample_fps,
        source_video_fps=source_video_fps,
        analysis_mode="bowling",
        discipline=metric_discipline,
        metric_version=_BOWLING_V2_METRIC_VERSION,
        source_model=source_model,
    )


def _phase_for_names(
    repetition_id: str,
    phase_lookup: dict[tuple[str, str], PhaseRecordV2],
    names: tuple[str, ...],
) -> PhaseRecordV2 | None:
    for name in names:
        phase = phase_lookup.get((repetition_id, name))
        if phase is not None:
            return phase
    return None


def _window_frames(frames: list[_NormalizedFrame], phase: PhaseRecordV2) -> list[_NormalizedFrame]:
    if phase.start_frame is not None and phase.end_frame is not None:
        return [
            frame for frame in frames if phase.start_frame <= frame.frame_num <= phase.end_frame
        ]
    if phase.start_ts is None or phase.end_ts is None:
        return []
    return [
        frame
        for frame in frames
        if frame.timestamp_s is not None and phase.start_ts <= frame.timestamp_s <= phase.end_ts
    ]


def _evidence_refs(samples: list[_MetricSample]) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    for sample in samples:
        refs.append(EvidenceRef(ref_type="repetition_window", ref_id=sample.repetition_id))
        if sample.phase_id:
            refs.append(EvidenceRef(ref_type="phase_window", ref_id=sample.phase_id))
        refs.extend(sample.evidence_refs)
    dedup: dict[tuple[str, str | None, str | None], EvidenceRef] = {}
    for ref in refs:
        dedup[(ref.ref_type, ref.ref_id, ref.label)] = ref
    return list(dedup.values())


def _timestamp_refs(samples: list[_MetricSample]) -> list[TimestampRef]:
    return [TimestampRef(start_ts=sample.start_ts, end_ts=sample.end_ts) for sample in samples]


def _frame_refs(samples: list[_MetricSample]) -> list[FrameRef]:
    return [
        FrameRef(start_frame=sample.start_frame, end_frame=sample.end_frame) for sample in samples
    ]


def _parse_capture_profile(payload: Any) -> CaptureProfile | None:
    if not isinstance(payload, dict):
        return None
    try:
        return CaptureProfile.model_validate(payload)
    except Exception:
        return None


def _parse_repetitions(payload: Any) -> list[RepetitionActionRecordV2]:
    if not isinstance(payload, list):
        return []
    repetitions: list[RepetitionActionRecordV2] = []
    for item in payload:
        try:
            repetitions.append(RepetitionActionRecordV2.model_validate(item))
        except Exception:
            continue
    return repetitions


def _parse_phases(payload: Any) -> list[PhaseRecordV2]:
    if not isinstance(payload, list):
        return []
    phases: list[PhaseRecordV2] = []
    for item in payload:
        try:
            phases.append(PhaseRecordV2.model_validate(item))
        except Exception:
            continue
    return phases


def _build_phase_lookup(phases: list[PhaseRecordV2]) -> dict[tuple[str, str], PhaseRecordV2]:
    lookup: dict[tuple[str, str], PhaseRecordV2] = {}
    for phase in phases:
        lookup[(phase.repetition_id, phase.phase_name)] = phase
    return lookup


def _normalize_frames(frames: list[dict[str, Any]]) -> list[_NormalizedFrame]:
    normalized: list[_NormalizedFrame] = []
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            continue
        frame_num = _as_int(
            frame.get("frame_num")
            if frame.get("frame_num") is not None
            else frame.get("frame_id")
            if frame.get("frame_id") is not None
            else frame.get("frame_index")
        )
        if frame_num is None:
            frame_num = index
        timestamp = _as_float(frame.get("timestamp"))
        if timestamp is None:
            timestamp = _as_float(frame.get("t"))
        keypoints = _normalize_keypoints(frame.get("keypoints"))
        detected = bool(frame.get("pose_detected") or frame.get("detected") or keypoints)
        normalized.append(
            _NormalizedFrame(
                frame_num=frame_num,
                timestamp_s=timestamp,
                detected=detected,
                keypoints=keypoints,
            )
        )
    normalized.sort(key=lambda item: item.frame_num)
    return normalized


def _normalize_keypoints(payload: Any) -> dict[str, tuple[float, float]]:
    if not isinstance(payload, dict):
        return {}
    normalized: dict[str, tuple[float, float]] = {}
    for key, raw_point in payload.items():
        if not isinstance(key, str):
            continue
        point = _as_xy(raw_point)
        if point is not None:
            normalized[key] = point
    return normalized


def _as_xy(value: Any) -> tuple[float, float] | None:
    if isinstance(value, dict):
        x = _as_float(value.get("x"))
        y = _as_float(value.get("y"))
        if x is not None and y is not None:
            return (x, y)
        return None
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        x = _as_float(value[0])
        y = _as_float(value[1])
        if x is not None and y is not None:
            return (x, y)
    return None


def _visibility(window: list[_NormalizedFrame], values: list[float]) -> float:
    if not window:
        return 0.0
    return min(1.0, max(0.0, len(values) / len(window)))


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _angle_degrees(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    ab = (a[0] - b[0], a[1] - b[1])
    cb = (c[0] - b[0], c[1] - b[1])
    mag_ab = math.sqrt(ab[0] ** 2 + ab[1] ** 2)
    mag_cb = math.sqrt(cb[0] ** 2 + cb[1] ** 2)
    if mag_ab == 0 or mag_cb == 0:
        return 0.0
    cos_theta = max(-1.0, min(1.0, (ab[0] * cb[0] + ab[1] * cb[1]) / (mag_ab * mag_cb)))
    return math.degrees(math.acos(cos_theta))


def _line_orientation_deg(a: tuple[float, float], b: tuple[float, float]) -> float:
    angle = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    angle %= 180.0
    return angle


def _mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return mean(values)


def _as_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def _as_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None

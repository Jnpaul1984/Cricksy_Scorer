from __future__ import annotations

import math
from collections.abc import Callable
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
from backend.services.coach_analysis_v2_compatibility import infer_validity_state

_FIELDING_V2_METRIC_VERSION = "fielding_pose_metrics.v2.0.0"
_FIELDING_V2_METRIC_IDS = {
    "fielding_ready_stance_width_ratio",
    "fielding_reaction_head_stability_score",
    "fielding_approach_balance_drift_ratio",
    "fielding_ground_collection_body_drop_ratio",
    "fielding_ground_collection_knee_flexion_angle_deg",
    "fielding_ground_collection_head_base_offset_ratio",
    "fielding_transfer_balance_drift_ratio",
    "fielding_catch_collection_wrist_compactness_ratio",
    "fielding_throw_action_shoulder_hip_separation_deg",
    "fielding_recovery_balance_drift_ratio",
}


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


def attach_fielding_v2_metric_pack(
    *,
    results_payload: dict[str, Any],
    discipline: str,
    frames: list[dict[str, Any]] | None,
    sample_fps: float | None,
    source_video_fps: float | None,
    camera_view: str | None,
    source_model: str | None,
) -> dict[str, Any]:
    if (discipline or "").strip().lower() != "fielding":
        return results_payload

    v2_payload = results_payload.get("v2")
    if not isinstance(v2_payload, dict):
        return results_payload

    repetitions = _parse_repetitions(v2_payload.get("repetitions"))
    phases = _parse_phases(v2_payload.get("phases"))
    phase_lookup = _build_phase_lookup(phases)
    normalized_frames = _normalize_frames(frames or [])
    capture_profile = _parse_capture_profile(v2_payload.get("capture_profile"))

    metric_results_payload = v2_payload.get("metric_results")
    existing_results = metric_results_payload if isinstance(metric_results_payload, list) else []

    built_results = _build_fielding_metric_results(
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
            and item.get("metric_id") in _FIELDING_V2_METRIC_IDS
        )
    ]
    v2_payload["metric_results"] = [
        *retained,
        *[item.model_dump(mode="json") for item in built_results],
    ]

    results_payload.setdefault("meta", {})
    if isinstance(results_payload["meta"], dict):
        results_payload["meta"]["fielding_v2_metric_pack"] = _build_metric_pack_summary(
            built_results,
            repetitions=repetitions,
            phase_lookup=phase_lookup,
        )

    insights = build_fielding_v2_findings_insights(built_results)
    findings_payload = results_payload.get("findings")
    if isinstance(findings_payload, dict):
        findings_payload["fielding_v2"] = insights
    report_payload = results_payload.get("report")
    if isinstance(report_payload, dict):
        report_payload["fielding_v2"] = insights

    return results_payload


def build_fielding_v2_findings_insights(
    metric_results: list[CoachingMetricResultV2],
) -> dict[str, Any]:
    strengths: list[dict[str, str]] = []
    concerns: list[dict[str, str]] = []
    limitations: list[dict[str, str]] = []
    for metric in metric_results:
        label = metric.metric_id.replace("fielding_", "").replace("_", " ")
        if (
            metric.validity_state == ValidityState.VALID
            and metric.classification_status == "STRONG"
        ):
            strengths.append({"metric_id": metric.metric_id, "summary": f"Strong {label}."})
        elif metric.validity_state in {ValidityState.VALID, ValidityState.LOW_CONFIDENCE}:
            concerns.append({"metric_id": metric.metric_id, "summary": f"Refine {label}."})
        else:
            limitations.append(
                {
                    "metric_id": metric.metric_id,
                    "summary": metric.unavailable_reason
                    or "Metric unavailable for this fielding capture.",
                }
            )
    return {
        "strengths": strengths,
        "concerns": concerns,
        "limitations": limitations,
    }


def _build_fielding_metric_results(
    *,
    repetitions: list[RepetitionActionRecordV2],
    phase_lookup: dict[tuple[str, str], PhaseRecordV2],
    frames: list[_NormalizedFrame],
    sample_fps: float | None,
    source_video_fps: float | None,
    camera_view: str | None,
    source_model: str | None,
    capture_profile: CaptureProfile | None,
) -> list[CoachingMetricResultV2]:
    capture = capture_profile or CaptureProfile(
        camera_view=camera_view,
        sample_fps=sample_fps,
        effective_analysis_fps=sample_fps,
        source_video_fps=source_video_fps,
        analysis_mode="fielding",
        discipline="fielding",
        metric_version=_FIELDING_V2_METRIC_VERSION,
        source_model=source_model,
    )
    base_requirements = CameraRequirements(
        supported_views=["side", "front", "behind"],
        minimum_sample_fps=5.0,
        minimum_source_video_fps=12.0,
    )
    subtype_map = _infer_repetition_subtypes(repetitions, phase_lookup)

    return [
        _build_metric_result(
            metric_id="fielding_ready_stance_width_ratio",
            action_type="fielding_action",
            phase="ready",
            unit="ratio",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("ready",),
                measure_fn=_measure_stance_width_ratio,
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture,
            camera_requirements=base_requirements,
            valid_range=(0.2, 3.0),
            classification_fn=lambda value: (
                "STRONG"
                if 0.85 <= value <= 1.75
                else "DEVELOPING"
                if 0.7 <= value <= 2.0
                else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Ready stance width is a pose-only base-width proxy and can shift with perspective.",
            ],
        ),
        _build_metric_result(
            metric_id="fielding_reaction_head_stability_score",
            action_type="fielding_action",
            phase="reaction",
            unit="score",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("reaction",),
                measure_fn=_measure_head_stability_score,
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture,
            camera_requirements=base_requirements,
            valid_range=(0.0, 1.0),
            classification_fn=lambda value: (
                "STRONG" if value >= 0.72 else "DEVELOPING" if value >= 0.58 else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Reaction score is a movement-control proxy only; exact reaction timing is not inferred.",
            ],
        ),
        _build_metric_result(
            metric_id="fielding_approach_balance_drift_ratio",
            action_type="fielding_action",
            phase="approach",
            unit="ratio",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("approach",),
                measure_fn=_measure_balance_drift_ratio,
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture,
            camera_requirements=base_requirements,
            valid_range=(0.0, 2.0),
            classification_fn=lambda value: (
                "STRONG" if value <= 0.2 else "DEVELOPING" if value <= 0.32 else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Approach control uses hip-to-base drift normalized by shoulder width.",
                "Boundary awareness is not inferred; this remains a generic approach-control proxy.",
            ],
        ),
        _build_metric_result(
            metric_id="fielding_ground_collection_body_drop_ratio",
            action_type="fielding_action",
            phase="collection",
            unit="ratio",
            samples=_ready_to_collection_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                subtype_map=subtype_map,
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture,
            camera_requirements=base_requirements,
            valid_range=(0.0, 3.0),
            classification_fn=lambda value: (
                "STRONG"
                if 0.15 <= value <= 0.95
                else "DEVELOPING"
                if 0.08 <= value <= 1.15
                else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Body-drop ratio compares ready and collection hip height as a ground-fielding posture proxy.",
                "This metric is withheld for catch-tagged repetitions to avoid unsupported pickup assumptions.",
            ],
            unavailable_hint=(
                "No non-catching fielding repetitions were available for a deterministic body-drop proxy."
            ),
        ),
        _build_metric_result(
            metric_id="fielding_ground_collection_knee_flexion_angle_deg",
            action_type="fielding_action",
            phase="collection",
            unit="degrees",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("collection",),
                measure_fn=_measure_knee_flexion_angle_deg,
                repetition_filter=lambda rep: not subtype_map.get(rep.repetition_id, {}).get(
                    "catch", False
                ),
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture,
            camera_requirements=base_requirements,
            valid_range=(35.0, 175.0),
            classification_fn=lambda value: (
                "STRONG"
                if 75.0 <= value <= 130.0
                else "DEVELOPING"
                if 65.0 <= value <= 145.0
                else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Knee flexion is a pickup-depth proxy and is not reported for catch-tagged repetitions.",
            ],
            unavailable_hint=(
                "No non-catching fielding repetitions were available for ground-collection knee flexion."
            ),
        ),
        _build_metric_result(
            metric_id="fielding_ground_collection_head_base_offset_ratio",
            action_type="fielding_action",
            phase="collection",
            unit="ratio",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("collection",),
                measure_fn=_measure_head_base_offset_ratio,
                repetition_filter=lambda rep: not subtype_map.get(rep.repetition_id, {}).get(
                    "catch", False
                ),
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture,
            camera_requirements=base_requirements,
            valid_range=(0.0, 2.5),
            classification_fn=lambda value: (
                "STRONG" if value <= 0.26 else "DEVELOPING" if value <= 0.4 else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Head-over-base offset is a body-alignment proxy; exact ball position is not inferred.",
            ],
            unavailable_hint=(
                "No non-catching fielding repetitions were available for a deterministic pickup-alignment proxy."
            ),
        ),
        _build_metric_result(
            metric_id="fielding_transfer_balance_drift_ratio",
            action_type="fielding_action",
            phase="transfer",
            unit="ratio",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("transfer",),
                measure_fn=_measure_balance_drift_ratio,
                repetition_filter=lambda rep: not subtype_map.get(rep.repetition_id, {}).get(
                    "catch", False
                ),
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture,
            camera_requirements=base_requirements,
            valid_range=(0.0, 2.0),
            classification_fn=lambda value: (
                "STRONG" if value <= 0.22 else "DEVELOPING" if value <= 0.35 else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Transfer metric is a balance proxy only; exact pickup-to-release timing is not inferred.",
            ],
            unavailable_hint=(
                "No non-catching fielding repetitions were available for a deterministic transfer metric."
            ),
        ),
        _build_metric_result(
            metric_id="fielding_catch_collection_wrist_compactness_ratio",
            action_type="fielding_catch",
            phase="collection",
            unit="ratio",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("collection",),
                measure_fn=_measure_wrist_compactness_ratio,
                repetition_filter=lambda rep: subtype_map.get(rep.repetition_id, {}).get(
                    "catch", False
                ),
                confidence_adjuster=lambda _rep, phase: (
                    0.08
                    if _phase_has_object_hint(
                        phase,
                        {"ball", "catch_window", "object_tracking", "ball_tracking"},
                    )
                    else -0.05
                ),
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture,
            camera_requirements=base_requirements,
            valid_range=(0.0, 2.5),
            classification_fn=lambda value: (
                "STRONG" if value <= 1.05 else "DEVELOPING" if value <= 1.35 else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Catch compactness is a glove/hand-preparation proxy only.",
                "One-hand versus two-hand catch technique is not classified unless future visibility evidence supports it.",
                "Exact catch-completion timing is not inferred.",
            ],
            unavailable_hint="No catch-tagged repetitions were available, so catching compactness was not inferred.",
        ),
        _build_metric_result(
            metric_id="fielding_throw_action_shoulder_hip_separation_deg",
            action_type="fielding_throw",
            phase="throw_action",
            unit="degrees",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("throw_action",),
                measure_fn=_measure_shoulder_hip_separation_deg,
                repetition_filter=lambda rep: subtype_map.get(rep.repetition_id, {}).get(
                    "throw", False
                ),
                confidence_adjuster=lambda _rep, phase: (
                    0.08
                    if _phase_has_object_hint(
                        phase,
                        {"release", "target", "ball_tracking", "object_tracking"},
                    )
                    else -0.04
                ),
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture,
            camera_requirements=base_requirements,
            valid_range=(0.0, 90.0),
            classification_fn=lambda value: (
                "STRONG"
                if 12.0 <= value <= 45.0
                else "DEVELOPING"
                if 6.0 <= value <= 60.0
                else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Throw metric measures trunk/shoulder separation only; exact release timing, speed, and accuracy are not inferred.",
            ],
            unavailable_hint=(
                "No throw-tagged repetitions were available, so throwing rotation was not inferred."
            ),
        ),
        _build_metric_result(
            metric_id="fielding_recovery_balance_drift_ratio",
            action_type="fielding_action",
            phase="recovery",
            unit="ratio",
            samples=_single_phase_metric(
                repetitions=repetitions,
                phase_lookup=phase_lookup,
                frames=frames,
                phase_names=("recovery",),
                measure_fn=_measure_balance_drift_ratio,
            ),
            sample_fps=sample_fps,
            source_video_fps=source_video_fps,
            camera_view=camera_view,
            capture_profile=capture,
            camera_requirements=base_requirements,
            valid_range=(0.0, 2.0),
            classification_fn=lambda value: (
                "STRONG" if value <= 0.22 else "DEVELOPING" if value <= 0.35 else "NEEDS_ATTENTION"
            ),
            limitations=[
                "Recovery metric describes post-action balance only and does not infer boundary awareness.",
            ],
        ),
    ]


def _build_metric_result(
    *,
    metric_id: str,
    action_type: str,
    phase: str,
    unit: str,
    samples: list[_MetricSample],
    sample_fps: float | None,
    source_video_fps: float | None,
    camera_view: str | None,
    capture_profile: CaptureProfile,
    camera_requirements: CameraRequirements,
    valid_range: tuple[float, float],
    classification_fn: Callable[[float], str],
    limitations: list[str],
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
    if (
        not samples
        and unavailable_hint is not None
        and validity_state in {ValidityState.NOT_MEASURABLE, ValidityState.INSUFFICIENT_REPETITIONS}
    ):
        unavailable_reason = unavailable_hint

    aggregate_stats = _aggregate_stats(values, len(samples))
    classification_status = (
        classification_fn(raw_value)
        if raw_value is not None
        and validity_state in {ValidityState.VALID, ValidityState.LOW_CONFIDENCE}
        else None
    )

    metric_limitations = list(limitations)
    if validity_state != ValidityState.VALID:
        metric_limitations.append(f"Metric validity state: {validity_state.value}.")

    return CoachingMetricResultV2(
        metric_version=_FIELDING_V2_METRIC_VERSION,
        metric_id=metric_id,
        discipline="fielding",
        action_type=action_type,
        phase=phase,
        raw_value=raw_value,
        unit=unit,
        normalized_score=raw_value if unit == "score" and isinstance(raw_value, float) else None,
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
        repetition_values=[round(value, 4) for value in values],
        aggregate_stats=aggregate_stats,
    )


def _aggregate_stats(values: list[float], repetition_count: int) -> dict[str, Any] | None:
    if not values:
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
    measure_fn: Callable[[list[_NormalizedFrame]], tuple[float | None, float]],
    repetition_filter: Callable[[RepetitionActionRecordV2], bool] | None = None,
    confidence_adjuster: Callable[[RepetitionActionRecordV2, PhaseRecordV2], float] | None = None,
) -> list[_MetricSample]:
    samples: list[_MetricSample] = []
    for repetition in repetitions:
        action_type = str(repetition.action_type or "").strip().lower()
        if not action_type.startswith("fielding"):
            continue
        if repetition_filter is not None and not repetition_filter(repetition):
            continue
        phase = _phase_for_names(repetition.repetition_id, phase_lookup, phase_names)
        if phase is None:
            continue
        window = _window_frames(frames, phase)
        value, visibility = measure_fn(window)
        if value is None:
            continue
        confidence = _window_confidence(repetition, phase, visibility)
        if confidence_adjuster is not None:
            confidence = round(
                max(0.0, min(1.0, confidence + confidence_adjuster(repetition, phase))),
                3,
            )
        samples.append(
            _MetricSample(
                repetition_id=repetition.repetition_id,
                phase_id=phase.phase_id,
                value=value,
                confidence=confidence,
                visibility=visibility,
                start_ts=phase.start_ts,
                end_ts=phase.end_ts,
                start_frame=phase.start_frame,
                end_frame=phase.end_frame,
                evidence_refs=list(phase.evidence_refs),
            )
        )
    return samples


def _ready_to_collection_metric(
    *,
    repetitions: list[RepetitionActionRecordV2],
    phase_lookup: dict[tuple[str, str], PhaseRecordV2],
    frames: list[_NormalizedFrame],
    subtype_map: dict[str, dict[str, bool]],
) -> list[_MetricSample]:
    samples: list[_MetricSample] = []
    for repetition in repetitions:
        action_type = str(repetition.action_type or "").strip().lower()
        if not action_type.startswith("fielding"):
            continue
        if subtype_map.get(repetition.repetition_id, {}).get("catch", False):
            continue

        ready_phase = _phase_for_names(repetition.repetition_id, phase_lookup, ("ready",))
        collection_phase = _phase_for_names(repetition.repetition_id, phase_lookup, ("collection",))
        if ready_phase is None or collection_phase is None:
            continue

        ready_window = _window_frames(frames, ready_phase)
        collection_window = _window_frames(frames, collection_phase)
        value, visibility = _measure_body_drop_ratio(ready_window, collection_window)
        if value is None:
            continue

        samples.append(
            _MetricSample(
                repetition_id=repetition.repetition_id,
                phase_id=collection_phase.phase_id,
                value=value,
                confidence=_window_confidence(
                    repetition,
                    collection_phase,
                    visibility,
                    fallback=ready_phase.confidence,
                ),
                visibility=visibility,
                start_ts=collection_phase.start_ts,
                end_ts=collection_phase.end_ts,
                start_frame=collection_phase.start_frame,
                end_frame=collection_phase.end_frame,
                evidence_refs=list(collection_phase.evidence_refs),
            )
        )
    return samples


def _window_confidence(
    repetition: RepetitionActionRecordV2,
    phase: PhaseRecordV2,
    visibility: float,
    *,
    fallback: float | None = None,
) -> float:
    rep_conf = (
        repetition.segmentation_confidence
        if repetition.segmentation_confidence is not None
        else 0.58
    )
    phase_conf = (
        phase.confidence
        if phase.confidence is not None
        else fallback
        if fallback is not None
        else 0.58
    )
    return round(max(0.0, min(1.0, rep_conf * 0.45 + phase_conf * 0.4 + visibility * 0.15)), 3)


def _measure_stance_width_ratio(window: list[_NormalizedFrame]) -> tuple[float | None, float]:
    values: list[float] = []
    for frame in window:
        if not frame.detected:
            continue
        left_ankle = frame.keypoints.get("left_ankle")
        right_ankle = frame.keypoints.get("right_ankle")
        left_shoulder = frame.keypoints.get("left_shoulder")
        right_shoulder = frame.keypoints.get("right_shoulder")
        if not (left_ankle and right_ankle and left_shoulder and right_shoulder):
            continue
        shoulder_width = _distance(left_shoulder, right_shoulder)
        ankle_width = _distance(left_ankle, right_ankle)
        if shoulder_width <= 0.001:
            continue
        values.append(ankle_width / shoulder_width)
    return (_mean_or_none(values), _visibility(window, values))


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


def _measure_knee_flexion_angle_deg(window: list[_NormalizedFrame]) -> tuple[float | None, float]:
    values: list[float] = []
    for frame in window:
        if not frame.detected:
            continue
        left = _knee_angle(frame, "left")
        right = _knee_angle(frame, "right")
        candidates = [angle for angle in (left, right) if angle is not None]
        if not candidates:
            continue
        values.append(min(candidates))
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


def _measure_wrist_compactness_ratio(window: list[_NormalizedFrame]) -> tuple[float | None, float]:
    values: list[float] = []
    for frame in window:
        if not frame.detected:
            continue
        left_wrist = frame.keypoints.get("left_wrist")
        right_wrist = frame.keypoints.get("right_wrist")
        left_shoulder = frame.keypoints.get("left_shoulder")
        right_shoulder = frame.keypoints.get("right_shoulder")
        if not (left_wrist and right_wrist and left_shoulder and right_shoulder):
            continue
        shoulder_width = _distance(left_shoulder, right_shoulder)
        if shoulder_width <= 0.001:
            continue
        values.append(_distance(left_wrist, right_wrist) / shoulder_width)
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


def _measure_body_drop_ratio(
    ready_window: list[_NormalizedFrame],
    collection_window: list[_NormalizedFrame],
) -> tuple[float | None, float]:
    ready_hips = _hip_midpoints(ready_window)
    collection_hips = _hip_midpoints(collection_window)
    if not ready_hips or not collection_hips:
        return (None, 0.0)

    shoulder_widths = [
        width
        for width in (_mean_shoulder_width(ready_window), _mean_shoulder_width(collection_window))
        if width
    ]
    if not shoulder_widths:
        return (None, 0.0)

    ready_mid = _mean_point(ready_hips)
    collection_mid = _mean_point(collection_hips)
    if ready_mid is None or collection_mid is None:
        return (None, 0.0)

    value = max(0.0, (collection_mid[1] - ready_mid[1]) / mean(shoulder_widths))
    total = len(ready_window) + len(collection_window)
    visibility = (len(ready_hips) + len(collection_hips)) / total if total > 0 else 0.0
    return (value, max(0.0, min(1.0, visibility)))


def _hip_midpoints(window: list[_NormalizedFrame]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for frame in window:
        if not frame.detected:
            continue
        left = frame.keypoints.get("left_hip")
        right = frame.keypoints.get("right_hip")
        if left and right:
            points.append(((left[0] + right[0]) / 2.0, (left[1] + right[1]) / 2.0))
    return points


def _mean_shoulder_width(window: list[_NormalizedFrame]) -> float | None:
    widths: list[float] = []
    for frame in window:
        if not frame.detected:
            continue
        left = frame.keypoints.get("left_shoulder")
        right = frame.keypoints.get("right_shoulder")
        if left and right:
            width = _distance(left, right)
            if width > 0.001:
                widths.append(width)
    return _mean_or_none(widths)


def _phase_has_object_hint(phase: PhaseRecordV2, hints: set[str]) -> bool:
    tokens: list[str] = [phase.phase_name, phase.detection_method or ""]
    for ref in phase.evidence_refs:
        tokens.extend([ref.ref_type, ref.ref_id or "", ref.label or ""])
    combined = " ".join(tokens).lower()
    return any(hint in combined for hint in hints)


def _build_metric_pack_summary(
    metric_results: list[CoachingMetricResultV2],
    *,
    repetitions: list[RepetitionActionRecordV2],
    phase_lookup: dict[tuple[str, str], PhaseRecordV2],
) -> dict[str, Any]:
    valid_count = sum(
        1
        for metric in metric_results
        if metric.validity_state in {ValidityState.VALID, ValidityState.LOW_CONFIDENCE}
    )
    subtype_counts = _summarize_repetition_subtypes(
        _infer_repetition_subtypes(repetitions, phase_lookup)
    )
    return {
        "enabled": True,
        "version": _FIELDING_V2_METRIC_VERSION,
        "metrics_count": len(metric_results),
        "valid_metrics_count": valid_count,
        "invalid_metrics_count": len(metric_results) - valid_count,
        "repetition_count": len(repetitions),
        "subtype_counts": subtype_counts,
        "cost_classification": {
            "base_pose_metrics": "low_cost_cpu",
            "subtype_gating": "low_cost_cpu",
            "boundary_specific_awareness": "ball_or_object_evidence_dependent",
        },
    }


def _infer_repetition_subtypes(
    repetitions: list[RepetitionActionRecordV2],
    phase_lookup: dict[tuple[str, str], PhaseRecordV2],
) -> dict[str, dict[str, bool]]:
    payload: dict[str, dict[str, bool]] = {}
    for repetition in repetitions:
        text_parts = [str(repetition.action_type or "")]
        for phase_name in (
            "ready",
            "reaction",
            "approach",
            "collection",
            "transfer",
            "throw_action",
            "recovery",
        ):
            phase = phase_lookup.get((repetition.repetition_id, phase_name))
            if phase is None:
                continue
            text_parts.extend([str(ref.ref_type) for ref in phase.evidence_refs])
            text_parts.extend([str(ref.ref_id or "") for ref in phase.evidence_refs])
            text_parts.extend([str(ref.label or "") for ref in phase.evidence_refs])
        combined = " ".join(text_parts).lower()
        payload[repetition.repetition_id] = {
            "catch": "catch" in combined,
            "throw": "throw" in combined,
            "boundary": any(
                token in combined for token in ("boundary", "rope", "line_save", "line-save")
            ),
        }
    return payload


def _summarize_repetition_subtypes(subtype_map: dict[str, dict[str, bool]]) -> dict[str, int]:
    counts = {
        "catch": 0,
        "throw": 0,
        "boundary": 0,
        "generic": 0,
    }
    for subtype in subtype_map.values():
        is_counted = False
        for key in ("catch", "throw", "boundary"):
            if subtype.get(key):
                counts[key] += 1
                is_counted = True
        if not is_counted:
            counts["generic"] += 1
    return counts


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


def _distance(left: tuple[float, float], right: tuple[float, float]) -> float:
    return math.dist((left[0], left[1]), (right[0], right[1]))


def _visibility(window: list[_NormalizedFrame], measured_values: list[float]) -> float:
    detected = sum(1 for frame in window if frame.detected)
    if detected <= 0:
        return 0.0
    return max(0.0, min(1.0, len(measured_values) / detected))


def _knee_angle(frame: _NormalizedFrame, side: str) -> float | None:
    hip = frame.keypoints.get(f"{side}_hip")
    knee = frame.keypoints.get(f"{side}_knee")
    ankle = frame.keypoints.get(f"{side}_ankle")
    if not (hip and knee and ankle):
        return None
    return _angle_degrees(hip, knee, ankle)


def _mean_point(points: list[tuple[float, float]]) -> tuple[float, float] | None:
    if not points:
        return None
    return (
        mean([point[0] for point in points]),
        mean([point[1] for point in points]),
    )


def _angle_degrees(
    point_a: tuple[float, float],
    point_b: tuple[float, float],
    point_c: tuple[float, float],
) -> float:
    vector_ab = (point_a[0] - point_b[0], point_a[1] - point_b[1])
    vector_cb = (point_c[0] - point_b[0], point_c[1] - point_b[1])
    magnitude = math.sqrt(vector_ab[0] ** 2 + vector_ab[1] ** 2) * math.sqrt(
        vector_cb[0] ** 2 + vector_cb[1] ** 2
    )
    if magnitude <= 1e-9:
        return 180.0
    cosine = max(
        -1.0,
        min(1.0, ((vector_ab[0] * vector_cb[0]) + (vector_ab[1] * vector_cb[1])) / magnitude),
    )
    return math.degrees(math.acos(cosine))


def _line_orientation_deg(a: tuple[float, float], b: tuple[float, float]) -> float:
    angle = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    angle %= 180.0
    return angle


def _mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return mean(values)


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        if math.isfinite(numeric):
            return numeric
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            numeric = float(stripped)
        except ValueError:
            return None
        if math.isfinite(numeric):
            return numeric
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(float(stripped))
        except ValueError:
            return None
    return None

from __future__ import annotations

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from backend.domain.coach_analysis_v2_contract import (
    DEFAULT_POSE_METRIC_VERSION,
    CameraRequirements,
    CaptureProfile,
    CoachingMetricResultV2,
    CompatibilityReasonCode,
    RepetitionActionRecordV2,
    ValidityState,
)
from backend.services.coach_analysis_v2_compatibility import (
    build_analysis_v2_contract,
    compare_metric_results,
    extract_metric_results,
    infer_validity_state,
)
from backend.services.coach_plus_analysis import run_pose_metrics_findings_report


def _capture_profile(
    *,
    camera_view: str | None = "side",
    sample_fps: float | None = 10.0,
    effective_analysis_fps: float | None = 10.0,
    source_video_fps: float | None = 30.0,
    source_model: str | None = "MediaPipe Pose Landmarker Full",
) -> CaptureProfile:
    return CaptureProfile(
        camera_view=camera_view,
        sample_fps=sample_fps,
        effective_analysis_fps=effective_analysis_fps,
        source_video_fps=source_video_fps,
        discipline="bowling",
        analysis_mode="bowling",
        metric_version=DEFAULT_POSE_METRIC_VERSION,
        source_model=source_model,
    )


def _metric_result(
    *,
    metric_version: str = DEFAULT_POSE_METRIC_VERSION,
    discipline: str = "bowling",
    camera_view: str | None = "side",
    sample_fps: float | None = 10.0,
    effective_analysis_fps: float | None = 10.0,
    source_video_fps: float | None = 30.0,
    source_model: str | None = "MediaPipe Pose Landmarker Full",
    validity_state: ValidityState = ValidityState.VALID,
) -> CoachingMetricResultV2:
    return CoachingMetricResultV2(
        metric_version=metric_version,
        metric_id="head_stability_score",
        discipline=discipline,
        raw_value=0.81,
        unit="score",
        normalized_score=0.81,
        confidence_score=0.91,
        validity_state=validity_state,
        unavailable_reason=(
            "Visibility was insufficient for a reliable measurement."
            if validity_state == ValidityState.INSUFFICIENT_VISIBILITY
            else None
        ),
        capture_profile=_capture_profile(
            camera_view=camera_view,
            sample_fps=sample_fps,
            effective_analysis_fps=effective_analysis_fps,
            source_video_fps=source_video_fps,
            source_model=source_model,
        ),
    )


def test_metric_contract_requires_versioned_identity_fields() -> None:
    metric = _metric_result()

    assert metric.schema_version
    assert metric.metric_version == DEFAULT_POSE_METRIC_VERSION
    assert metric.metric_id == "head_stability_score"
    assert metric.discipline == "bowling"
    assert metric.validity_state == ValidityState.VALID


def test_metric_contract_allows_optional_serialization_without_normalized_score() -> None:
    metric = CoachingMetricResultV2(
        metric_version="timing_metric.v1",
        metric_id="hip_shoulder_separation_timing",
        discipline="batting",
        raw_value=0.14,
        unit="seconds",
        confidence_score=0.87,
        validity_state=ValidityState.VALID,
        capture_profile=_capture_profile(),
        repetition_values=[0.11, 0.14, 0.17],
        aggregate_stats={"mean": 0.14, "count": 3},
    )

    payload = metric.model_dump(mode="json")
    assert payload["normalized_score"] is None
    assert payload["repetition_values"] == [0.11, 0.14, 0.17]
    assert payload["aggregate_stats"]["count"] == 3


def test_metric_contract_rejects_invalid_validity_state() -> None:
    with pytest.raises(ValidationError):
        CoachingMetricResultV2.model_validate(
            {
                "metric_version": "pose_metrics.v1",
                "metric_id": "head_stability_score",
                "discipline": "bowling",
                "raw_value": 0.8,
                "unit": "score",
                "confidence_score": 0.9,
                "validity_state": "UNKNOWN_STATE",
                "capture_profile": _capture_profile().model_dump(mode="json"),
            }
        )


@pytest.mark.parametrize(
    ("kwargs", "expected_state"),
    [
        (
            {
                "raw_value": 0.8,
                "confidence_score": 0.9,
            },
            ValidityState.VALID,
        ),
        (
            {
                "raw_value": 0.8,
                "confidence_score": 0.2,
            },
            ValidityState.LOW_CONFIDENCE,
        ),
        (
            {
                "raw_value": None,
            },
            ValidityState.NOT_MEASURABLE,
        ),
        (
            {
                "raw_value": 0.8,
                "visibility_sufficient": False,
            },
            ValidityState.INSUFFICIENT_VISIBILITY,
        ),
        (
            {
                "raw_value": 0.8,
                "camera_view": "front",
                "camera_requirements": CameraRequirements(supported_views=["side"]),
            },
            ValidityState.UNSUPPORTED_CAMERA_VIEW,
        ),
        (
            {
                "raw_value": 0.8,
                "sample_fps": 4,
                "camera_requirements": CameraRequirements(minimum_sample_fps=5),
            },
            ValidityState.INSUFFICIENT_FRAME_RATE,
        ),
        (
            {
                "raw_value": 1.5,
                "valid_range": (0.0, 1.0),
            },
            ValidityState.INVALID_RANGE,
        ),
        (
            {
                "raw_value": 0.8,
                "repetitions_count": 1,
                "min_repetitions": 3,
            },
            ValidityState.INSUFFICIENT_REPETITIONS,
        ),
    ],
)
def test_infer_validity_state_supports_required_taxonomy(
    kwargs: dict[str, object], expected_state: ValidityState
) -> None:
    state, _ = infer_validity_state(**kwargs)
    assert state == expected_state


def test_repetition_contract_exists_without_segmentation_logic() -> None:
    repetition = RepetitionActionRecordV2(
        repetition_id="rep-1",
        session_id="session-1",
        job_id="job-1",
        discipline="batting",
        action_type="cover_drive",
        segmentation_method="pending_v2_segmentation",
        segmentation_confidence=0.42,
        manual_override=False,
        validity_state=ValidityState.LOW_CONFIDENCE,
        insufficient_reason="Deterministic placeholder until segmentation is implemented.",
        metric_refs=["head_stability_score"],
    )

    assert repetition.repetition_id == "rep-1"
    assert repetition.segmentation_method == "pending_v2_segmentation"


def test_build_analysis_v2_contract_is_additive_and_keeps_empty_phase_repetition_lists() -> None:
    contract = build_analysis_v2_contract(
        discipline="bowling",
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
        metrics_payload={
            "metrics": {
                "head_stability_score": {
                    "score": 0.82,
                    "num_frames": 18.0,
                    "avg_movement": 0.07,
                },
                "hip_shoulder_separation_timing": {
                    "score": 0.12,
                    "num_frames": 18,
                    "hip_peak_time": 0.4,
                    "shoulder_peak_time": 0.52,
                },
            },
            "evidence": {
                "head_stability_score": {
                    "worst_frames": [{"frame_num": 8, "timestamp_s": 0.8, "score": 0.45}],
                    "bad_segments": [{"start_frame": 7, "end_frame": 9, "start_timestamp_s": 0.7}],
                }
            },
            "frames_with_pose": 18.0,
            "sampled_frames": 20.0,
            "detection_rate_percent": 90.0,
        },
    )

    dumped = contract.model_dump(mode="json")
    assert dumped["capture_profile"]["metric_version"] == DEFAULT_POSE_METRIC_VERSION
    assert dumped["metric_results"][0]["metric_version"] == DEFAULT_POSE_METRIC_VERSION
    assert dumped["repetitions"] == []
    assert dumped["phases"] == []
    hip_metric = next(
        item
        for item in dumped["metric_results"]
        if item["metric_id"] == "hip_shoulder_separation_timing"
    )
    assert hip_metric["normalized_score"] is None


def test_build_analysis_v2_contract_ignores_non_finite_numeric_metadata() -> None:
    contract = build_analysis_v2_contract(
        discipline="bowling",
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
        metrics_payload={
            "metrics": {
                "head_stability_score": {
                    "score": 0.82,
                    "num_frames": float("inf"),
                }
            },
            "frames_with_pose": float("nan"),
            "sampled_frames": 20.0,
            "detection_rate_percent": 90.0,
        },
    )

    metric = contract.metric_results[0]
    assert metric.validity_state == ValidityState.INSUFFICIENT_VISIBILITY


def test_compare_metric_results_allows_same_player_metric_version_and_capture() -> None:
    result = compare_metric_results(
        _metric_result(),
        _metric_result(),
        player_id_left="player-1",
        player_id_right="player-1",
    )

    assert result.comparable is True
    assert result.reason_codes == []
    assert result.comparison_identity == {
        "player_id": "player-1",
        "discipline": "bowling",
        "metric_id": "head_stability_score",
        "metric_version": DEFAULT_POSE_METRIC_VERSION,
    }


@pytest.mark.parametrize(
    ("left", "right", "expected_reason"),
    [
        (
            _metric_result(metric_version="pose_metrics.v1"),
            _metric_result(metric_version="pose_metrics.v2"),
            CompatibilityReasonCode.METRIC_VERSION_MISMATCH,
        ),
        (
            _metric_result(discipline="bowling"),
            _metric_result(discipline="batting"),
            CompatibilityReasonCode.DISCIPLINE_MISMATCH,
        ),
        (
            _metric_result(camera_view="side"),
            _metric_result(camera_view="front"),
            CompatibilityReasonCode.CAMERA_VIEW_MISMATCH,
        ),
        (
            _metric_result(sample_fps=10.0, effective_analysis_fps=10.0),
            _metric_result(sample_fps=5.0, effective_analysis_fps=5.0),
            CompatibilityReasonCode.SAMPLE_FPS_MISMATCH,
        ),
    ],
)
def test_compare_metric_results_returns_explicit_incompatibility_reasons(
    left: CoachingMetricResultV2,
    right: CoachingMetricResultV2,
    expected_reason: CompatibilityReasonCode,
) -> None:
    result = compare_metric_results(
        left,
        right,
        player_id_left="player-1",
        player_id_right="player-1",
    )

    assert result.comparable is False
    assert expected_reason in result.reason_codes


def test_compare_metric_results_fails_safe_on_missing_capture_metadata() -> None:
    result = compare_metric_results(
        _metric_result(camera_view=None),
        _metric_result(),
        player_id_left="player-1",
        player_id_right="player-1",
    )

    assert result.comparable is False
    assert CompatibilityReasonCode.MISSING_CAPTURE_METADATA in result.reason_codes


def test_extract_metric_results_keeps_legacy_payloads_readable() -> None:
    legacy_payload = {
        "pose_summary": {"frames_with_pose": 20},
        "metrics": {"head_stability_score": {"score": 0.8}},
        "findings": {"findings": []},
        "report": {"summary": "legacy"},
    }

    assert extract_metric_results(legacy_payload) == []


def test_run_pose_metrics_findings_report_embeds_v2_contract_without_breaking_legacy_keys() -> None:
    with patch("backend.services.pose_service.extract_pose_keypoints_from_video") as mock_extract:
        mock_extract.return_value = {
            "frames": [
                {
                    "frame_id": index,
                    "t": index / 10,
                    "detected": True,
                    "keypoints": {
                        "nose": [0.5, 0.5, 0.9],
                        "left_shoulder": [0.4, 0.6, 0.9],
                        "right_shoulder": [0.6, 0.6, 0.9],
                        "left_hip": [0.4, 0.8, 0.9],
                        "right_hip": [0.6, 0.8, 0.9],
                        "left_knee": [0.4, 1.0, 0.9],
                        "right_knee": [0.6, 1.0, 0.9],
                        "left_ankle": [0.4, 1.2, 0.9],
                        "right_ankle": [0.6, 1.2, 0.9],
                        "left_elbow": [0.35, 0.7, 0.9],
                        "right_elbow": [0.65, 0.7, 0.9],
                    },
                }
                for index in range(12)
            ],
            "total_frames": 12,
            "sampled_frames": 12,
            "frames_with_pose": 12,
            "detection_rate_percent": 100.0,
            "video_fps": 30.0,
            "model": "MediaPipe Pose Landmarker Full",
        }

        result = run_pose_metrics_findings_report(
            video_path="dummy.mp4",
            sample_fps=10,
            include_frames=False,
            player_context={"camera_view": "side"},
            analysis_mode="bowling",
        )

    payload = result.results
    assert "pose_summary" in payload
    assert "metrics" in payload
    assert "findings" in payload
    assert "report" in payload
    assert "v2" in payload
    assert payload["v2"]["capture_profile"]["camera_view"] == "side"
    assert payload["v2"]["metric_results"]

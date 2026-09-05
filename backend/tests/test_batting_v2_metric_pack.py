from __future__ import annotations

from typing import Any

from backend.domain.coach_analysis_v2_contract import (
    CaptureProfile,
    PhaseRecordV2,
    RepetitionActionRecordV2,
    ValidityState,
)
from backend.services.batting_v2_metric_pack import attach_batting_v2_metric_pack


def _frame(frame_num: int, timestamp: float, *, stance_scale: float = 1.0) -> dict[str, object]:
    return {
        "frame_num": frame_num,
        "timestamp": timestamp,
        "detected": True,
        "keypoints": {
            "nose": {"x": 0.50, "y": 0.20},
            "left_shoulder": {"x": 0.42, "y": 0.42},
            "right_shoulder": {"x": 0.58, "y": 0.42},
            "left_elbow": {"x": 0.40, "y": 0.50},
            "right_elbow": {"x": 0.60, "y": 0.50},
            "left_wrist": {"x": 0.39, "y": 0.57},
            "right_wrist": {"x": 0.61, "y": 0.57},
            "left_hip": {"x": 0.45, "y": 0.68},
            "right_hip": {"x": 0.55, "y": 0.68},
            "left_knee": {"x": 0.45, "y": 0.84},
            "right_knee": {"x": 0.55, "y": 0.84},
            "left_ankle": {"x": 0.50 - (0.08 * stance_scale), "y": 0.96},
            "right_ankle": {"x": 0.50 + (0.08 * stance_scale), "y": 0.96},
        },
    }


def _payload() -> dict[str, Any]:
    repetition = RepetitionActionRecordV2(
        repetition_id="rep-1",
        discipline="batting",
        action_type="batting_shot",
        start_ts=0.0,
        end_ts=0.6,
        start_frame=0,
        end_frame=6,
        segmentation_method="pose_motion_v1",
        segmentation_confidence=0.84,
        validity_state=ValidityState.VALID,
    )
    phases = [
        PhaseRecordV2(
            phase_id="rep-1:1",
            repetition_id="rep-1",
            phase_name=name,
            start_ts=start_ts,
            end_ts=end_ts,
            start_frame=start_frame,
            end_frame=end_frame,
            detection_method="repetition_relative_heuristic_v1",
            confidence=0.82,
            validity_state=ValidityState.VALID,
        )
        for name, start_ts, end_ts, start_frame, end_frame in (
            ("setup", 0.0, 0.1, 0, 1),
            ("trigger", 0.1, 0.2, 1, 2),
            ("downswing", 0.2, 0.4, 2, 4),
            ("contact_proxy_window", 0.4, 0.5, 4, 5),
            ("follow_through", 0.5, 0.6, 5, 6),
        )
    ]
    return {
        "v2": {
            "capture_profile": CaptureProfile(
                camera_view="side",
                sample_fps=10.0,
                source_video_fps=30.0,
                effective_analysis_fps=10.0,
                discipline="batting",
                analysis_mode="batting",
                metric_version="pose_metrics.v1",
                source_model="MediaPipe Pose Landmarker Full",
            ).model_dump(mode="json"),
            "metric_results": [],
            "repetitions": [repetition.model_dump(mode="json")],
            "phases": [phase.model_dump(mode="json") for phase in phases],
        },
        "findings": {"findings": []},
        "report": {"summary": "ok"},
        "meta": {},
    }


def test_attach_batting_v2_metric_pack_generates_phase_aware_metric_results() -> None:
    payload = _payload()
    frames = [_frame(index, index * 0.1) for index in range(7)]

    updated = attach_batting_v2_metric_pack(
        results_payload=payload,
        discipline="batting",
        frames=frames,
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    metrics = updated["v2"]["metric_results"]
    assert len(metrics) == 6
    assert {item["phase"] for item in metrics} >= {
        "setup",
        "trigger",
        "downswing",
        "contact_proxy_window",
        "follow_through",
    }
    assert all(item["metric_id"].startswith("batting_") for item in metrics)
    assert updated["meta"]["batting_v2_metric_pack"]["metrics_count"] == 6
    assert "batting_v2" in updated["findings"]
    assert "batting_v2" in updated["report"]


def test_attach_batting_v2_metric_pack_flags_unsupported_camera() -> None:
    payload = _payload()
    frames = [_frame(index, index * 0.1) for index in range(7)]

    updated = attach_batting_v2_metric_pack(
        results_payload=payload,
        discipline="batting",
        frames=frames,
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="overhead",
        source_model="MediaPipe Pose Landmarker Full",
    )

    assert all(
        item["validity_state"] == ValidityState.UNSUPPORTED_CAMERA_VIEW.value
        for item in updated["v2"]["metric_results"]
    )


def test_attach_batting_v2_metric_pack_flags_insufficient_frame_rate() -> None:
    payload = _payload()
    frames = [_frame(index, index * 0.1) for index in range(7)]

    updated = attach_batting_v2_metric_pack(
        results_payload=payload,
        discipline="batting",
        frames=frames,
        sample_fps=3.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    assert all(
        item["validity_state"] == ValidityState.INSUFFICIENT_FRAME_RATE.value
        for item in updated["v2"]["metric_results"]
    )


def test_attach_batting_v2_metric_pack_flags_invalid_physical_range() -> None:
    payload = _payload()
    frames = [_frame(index, index * 0.1, stance_scale=5.0) for index in range(7)]

    updated = attach_batting_v2_metric_pack(
        results_payload=payload,
        discipline="batting",
        frames=frames,
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    stance_metric = next(
        item
        for item in updated["v2"]["metric_results"]
        if item["metric_id"] == "batting_setup_stance_width_ratio"
    )
    assert stance_metric["validity_state"] == ValidityState.INVALID_RANGE.value


def test_attach_batting_v2_metric_pack_handles_missing_phase_data_safely() -> None:
    payload = _payload()
    payload["v2"]["phases"] = []
    frames = [_frame(index, index * 0.1) for index in range(7)]

    updated = attach_batting_v2_metric_pack(
        results_payload=payload,
        discipline="batting",
        frames=frames,
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    assert all(
        item["validity_state"] == ValidityState.MISSING_PHASE.value
        for item in updated["v2"]["metric_results"]
    )

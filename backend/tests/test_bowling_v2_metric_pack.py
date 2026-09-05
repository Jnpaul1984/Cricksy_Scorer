from __future__ import annotations

from typing import Any

from backend.domain.coach_analysis_v2_contract import (
    CaptureProfile,
    PhaseRecordV2,
    RepetitionActionRecordV2,
    ValidityState,
)
from backend.services.bowling_v2_metric_pack import attach_bowling_v2_metric_pack


def _frame(
    frame_num: int,
    timestamp: float,
    *,
    nose_x: float = 0.50,
    nose_y: float = 0.20,
    left_shoulder: tuple[float, float] = (0.40, 0.40),
    right_shoulder: tuple[float, float] = (0.60, 0.40),
    left_wrist: tuple[float, float] = (0.41, 0.60),
    right_wrist: tuple[float, float] = (0.59, 0.60),
    left_hip: tuple[float, float] = (0.45, 0.68),
    right_hip: tuple[float, float] = (0.55, 0.68),
    left_knee: tuple[float, float] = (0.44, 0.82),
    right_knee: tuple[float, float] = (0.56, 0.82),
    left_ankle: tuple[float, float] = (0.42, 0.96),
    right_ankle: tuple[float, float] = (0.58, 0.96),
) -> dict[str, object]:
    return {
        "frame_num": frame_num,
        "timestamp": timestamp,
        "detected": True,
        "keypoints": {
            "nose": {"x": nose_x, "y": nose_y},
            "left_shoulder": {"x": left_shoulder[0], "y": left_shoulder[1]},
            "right_shoulder": {"x": right_shoulder[0], "y": right_shoulder[1]},
            "left_elbow": {"x": 0.43, "y": 0.52},
            "right_elbow": {"x": 0.57, "y": 0.52},
            "left_wrist": {"x": left_wrist[0], "y": left_wrist[1]},
            "right_wrist": {"x": right_wrist[0], "y": right_wrist[1]},
            "left_hip": {"x": left_hip[0], "y": left_hip[1]},
            "right_hip": {"x": right_hip[0], "y": right_hip[1]},
            "left_knee": {"x": left_knee[0], "y": left_knee[1]},
            "right_knee": {"x": right_knee[0], "y": right_knee[1]},
            "left_ankle": {"x": left_ankle[0], "y": left_ankle[1]},
            "right_ankle": {"x": right_ankle[0], "y": right_ankle[1]},
        },
    }


def _payload(session_discipline: str, phases: list[PhaseRecordV2]) -> dict[str, Any]:
    repetition = RepetitionActionRecordV2(
        repetition_id=f"{session_discipline}-rep-1",
        discipline="bowling",
        action_type="bowling_delivery",
        start_ts=0.0,
        end_ts=0.6,
        start_frame=0,
        end_frame=6,
        segmentation_method="pose_motion_v1",
        segmentation_confidence=0.84,
        validity_state=ValidityState.VALID,
    )
    return {
        "v2": {
            "capture_profile": CaptureProfile(
                camera_view="side",
                sample_fps=10.0,
                source_video_fps=30.0,
                effective_analysis_fps=10.0,
                discipline=session_discipline,
                analysis_mode="bowling",
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


def _pace_phases(*, release_with_ball: bool) -> list[PhaseRecordV2]:
    phase_defs = (
        ("approach", 0.0, 0.2, 0, 2, 0.84),
        ("gather", 0.2, 0.3, 2, 3, 0.84),
        ("back_foot_contact", 0.3, 0.4, 3, 4, 0.84),
        ("delivery_stride", 0.4, 0.45, 4, 4, 0.84),
        ("front_foot_contact", 0.45, 0.5, 4, 5, 0.84),
        (
            ("release" if release_with_ball else "release_proxy_window"),
            0.5,
            0.55,
            5,
            5,
            (0.9 if release_with_ball else 0.58),
        ),
        ("follow_through", 0.55, 0.6, 5, 6, 0.82),
    )
    phases: list[PhaseRecordV2] = []
    for index, (name, start_ts, end_ts, start_frame, end_frame, confidence) in enumerate(
        phase_defs, start=1
    ):
        evidence_refs = []
        if name == "release":
            evidence_refs = [{"ref_type": "ball_tracking", "label": "release_point"}]
        phases.append(
            PhaseRecordV2(
                phase_id=f"pace-rep-1:phase:{index}",
                repetition_id="pace_bowling-rep-1",
                phase_name=name,
                start_ts=start_ts,
                end_ts=end_ts,
                start_frame=start_frame,
                end_frame=end_frame,
                detection_method="pose_ball_hybrid_v1"
                if name == "release"
                else "repetition_relative_heuristic_v1",
                confidence=confidence,
                requires_object_evidence=name in {"release", "release_proxy_window"},
                validity_state=(
                    ValidityState.VALID
                    if name != "release_proxy_window"
                    else ValidityState.LOW_CONFIDENCE
                ),
                evidence_refs=evidence_refs,
            )
        )
    return phases


def _spin_phases() -> list[PhaseRecordV2]:
    phase_defs = (
        ("approach", 0.0, 0.15, 0, 1, 0.84),
        ("coil", 0.15, 0.25, 1, 2, 0.83),
        ("pivot", 0.25, 0.35, 2, 3, 0.82),
        ("delivery_stride", 0.35, 0.45, 3, 4, 0.82),
        ("release_proxy_window", 0.45, 0.55, 4, 5, 0.58),
        ("follow_through", 0.55, 0.65, 5, 6, 0.8),
    )
    return [
        PhaseRecordV2(
            phase_id=f"spin-rep-1:phase:{index}",
            repetition_id="spin_bowling-rep-1",
            phase_name=name,
            start_ts=start_ts,
            end_ts=end_ts,
            start_frame=start_frame,
            end_frame=end_frame,
            detection_method="repetition_relative_heuristic_v1",
            confidence=confidence,
            requires_object_evidence=name == "release_proxy_window",
            validity_state=(
                ValidityState.LOW_CONFIDENCE
                if name == "release_proxy_window"
                else ValidityState.VALID
            ),
        )
        for index, (name, start_ts, end_ts, start_frame, end_frame, confidence) in enumerate(
            phase_defs, start=1
        )
    ]


def _pace_frames() -> list[dict[str, object]]:
    return [
        _frame(0, 0.0, nose_x=0.50),
        _frame(1, 0.1, nose_x=0.505),
        _frame(2, 0.2, left_hip=(0.45, 0.68), right_hip=(0.55, 0.68)),
        _frame(3, 0.3, left_ankle=(0.41, 0.96), right_ankle=(0.59, 0.96)),
        _frame(
            4,
            0.45,
            left_knee=(0.43, 0.82),
            left_ankle=(0.42, 0.96),
            right_knee=(0.60, 0.82),
            right_ankle=(0.58, 0.96),
        ),
        _frame(
            5,
            0.52,
            nose_x=0.58,
            left_wrist=(0.43, 0.16),
            right_wrist=(0.60, 0.60),
            left_hip=(0.49, 0.68),
            right_hip=(0.59, 0.68),
            left_ankle=(0.50, 0.96),
            right_ankle=(0.66, 0.96),
        ),
        _frame(6, 0.6, left_hip=(0.47, 0.68), right_hip=(0.57, 0.68)),
    ]


def _spin_frames() -> list[dict[str, object]]:
    return [
        _frame(0, 0.0, nose_x=0.50),
        _frame(1, 0.1, nose_x=0.505, left_hip=(0.46, 0.68), right_hip=(0.56, 0.68)),
        _frame(
            2,
            0.22,
            left_shoulder=(0.40, 0.42),
            right_shoulder=(0.60, 0.34),
            left_hip=(0.45, 0.70),
            right_hip=(0.55, 0.68),
        ),
        _frame(3, 0.35, nose_x=0.52, left_ankle=(0.44, 0.96), right_ankle=(0.60, 0.96)),
        _frame(4, 0.45, nose_x=0.53, left_ankle=(0.44, 0.96), right_ankle=(0.60, 0.96)),
        _frame(
            5,
            0.52,
            left_wrist=(0.50, 0.20),
            right_wrist=(0.61, 0.60),
            left_shoulder=(0.42, 0.42),
            right_shoulder=(0.60, 0.40),
        ),
        _frame(6, 0.6, left_hip=(0.46, 0.68), right_hip=(0.56, 0.68)),
    ]


def test_attach_bowling_v2_metric_pack_generates_pace_metrics_and_ball_evidence() -> None:
    payload = _payload("pace_bowling", _pace_phases(release_with_ball=True))

    updated = attach_bowling_v2_metric_pack(
        results_payload=payload,
        discipline="bowling",
        session_discipline="pace_bowling",
        frames=_pace_frames(),
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    metrics = updated["v2"]["metric_results"]
    assert len(metrics) == 6
    assert all(item["metric_id"].startswith("pace_bowling_") for item in metrics)
    assert updated["meta"]["bowling_v2_metric_pack"]["discipline"] == "pace_bowling"
    release_metric = next(
        item
        for item in metrics
        if item["metric_id"] == "pace_bowling_release_proxy_bowling_arm_angle_deg"
    )
    assert any(
        ref["ref_type"] == "ball_tracking" and ref.get("label") == "release_point"
        for ref in release_metric["evidence_refs"]
    )
    assert "bowling_v2" in updated["findings"]
    assert "bowling_v2" in updated["report"]


def test_attach_bowling_v2_metric_pack_generates_spin_specific_metrics() -> None:
    payload = _payload("spin_bowling", _spin_phases())

    updated = attach_bowling_v2_metric_pack(
        results_payload=payload,
        discipline="bowling",
        session_discipline="spin_bowling",
        frames=_spin_frames(),
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    metrics = updated["v2"]["metric_results"]
    assert len(metrics) == 6
    assert all(item["metric_id"].startswith("spin_bowling_") for item in metrics)
    assert any(
        item["metric_id"] == "spin_bowling_pivot_shoulder_hip_separation_deg" for item in metrics
    )
    assert updated["meta"]["bowling_v2_metric_pack"]["discipline"] == "spin_bowling"


def test_attach_bowling_v2_metric_pack_release_proxy_confidence_improves_with_ball_evidence() -> (
    None
):
    proxy_payload = _payload("pace_bowling", _pace_phases(release_with_ball=False))
    evidence_payload = _payload("pace_bowling", _pace_phases(release_with_ball=True))

    proxy_updated = attach_bowling_v2_metric_pack(
        results_payload=proxy_payload,
        discipline="bowling",
        session_discipline="pace_bowling",
        frames=_pace_frames(),
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )
    evidence_updated = attach_bowling_v2_metric_pack(
        results_payload=evidence_payload,
        discipline="bowling",
        session_discipline="pace_bowling",
        frames=_pace_frames(),
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    proxy_metric = next(
        item
        for item in proxy_updated["v2"]["metric_results"]
        if item["metric_id"] == "pace_bowling_release_proxy_bowling_arm_angle_deg"
    )
    evidence_metric = next(
        item
        for item in evidence_updated["v2"]["metric_results"]
        if item["metric_id"] == "pace_bowling_release_proxy_bowling_arm_angle_deg"
    )
    assert proxy_metric["confidence_score"] < evidence_metric["confidence_score"]
    assert not any(ref["ref_type"] == "ball_tracking" for ref in proxy_metric["evidence_refs"])


def test_attach_bowling_v2_metric_pack_flags_unsupported_camera() -> None:
    payload = _payload("pace_bowling", _pace_phases(release_with_ball=False))

    updated = attach_bowling_v2_metric_pack(
        results_payload=payload,
        discipline="bowling",
        session_discipline="pace_bowling",
        frames=_pace_frames(),
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="overhead",
        source_model="MediaPipe Pose Landmarker Full",
    )

    assert all(
        item["validity_state"] == ValidityState.UNSUPPORTED_CAMERA_VIEW.value
        for item in updated["v2"]["metric_results"]
    )


def test_attach_bowling_v2_metric_pack_flags_insufficient_frame_rate() -> None:
    payload = _payload("spin_bowling", _spin_phases())

    updated = attach_bowling_v2_metric_pack(
        results_payload=payload,
        discipline="bowling",
        session_discipline="spin_bowling",
        frames=_spin_frames(),
        sample_fps=4.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    assert all(
        item["validity_state"] == ValidityState.INSUFFICIENT_FRAME_RATE.value
        for item in updated["v2"]["metric_results"]
    )


def test_attach_bowling_v2_metric_pack_flags_invalid_physical_range() -> None:
    payload = _payload("pace_bowling", _pace_phases(release_with_ball=False))
    frames = _pace_frames()
    frames[-2] = _frame(
        5,
        0.52,
        left_hip=(0.88, 0.68),
        right_hip=(0.98, 0.68),
        left_ankle=(0.40, 0.96),
        right_ankle=(0.56, 0.96),
    )
    frames[-1] = _frame(
        6,
        0.6,
        left_hip=(0.90, 0.68),
        right_hip=(1.00, 0.68),
        left_ankle=(0.40, 0.96),
        right_ankle=(0.56, 0.96),
    )

    updated = attach_bowling_v2_metric_pack(
        results_payload=payload,
        discipline="bowling",
        session_discipline="pace_bowling",
        frames=frames,
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    follow_through_metric = next(
        item
        for item in updated["v2"]["metric_results"]
        if item["metric_id"] == "pace_bowling_follow_through_balance_drift_ratio"
    )
    assert follow_through_metric["validity_state"] == ValidityState.INVALID_RANGE.value


def test_attach_bowling_v2_metric_pack_handles_missing_phase_data_safely() -> None:
    payload = _payload("spin_bowling", [])

    updated = attach_bowling_v2_metric_pack(
        results_payload=payload,
        discipline="bowling",
        session_discipline="spin_bowling",
        frames=_spin_frames(),
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    assert all(
        item["validity_state"] == ValidityState.MISSING_PHASE.value
        for item in updated["v2"]["metric_results"]
    )

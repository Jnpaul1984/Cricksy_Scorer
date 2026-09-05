from __future__ import annotations

from typing import Any

from backend.domain.coach_analysis_v2_contract import (
    CaptureProfile,
    PhaseRecordV2,
    RepetitionActionRecordV2,
    ValidityState,
)
from backend.services.wicketkeeping_v2_metric_pack import attach_wicketkeeping_v2_metric_pack


def _frame(
    frame_num: int,
    timestamp: float,
    *,
    nose_x: float = 0.5,
    left_ankle_x: float = 0.42,
    right_ankle_x: float = 0.58,
    left_knee_x: float = 0.45,
    right_knee_x: float = 0.55,
    left_wrist_x: float = 0.46,
    right_wrist_x: float = 0.54,
    hip_shift: float = 0.0,
) -> dict[str, object]:
    return {
        "frame_num": frame_num,
        "timestamp": timestamp,
        "detected": True,
        "keypoints": {
            "nose": {"x": nose_x, "y": 0.2},
            "left_shoulder": {"x": 0.42, "y": 0.42},
            "right_shoulder": {"x": 0.58, "y": 0.42},
            "left_elbow": {"x": 0.43, "y": 0.52},
            "right_elbow": {"x": 0.57, "y": 0.52},
            "left_wrist": {"x": left_wrist_x, "y": 0.58},
            "right_wrist": {"x": right_wrist_x, "y": 0.58},
            "left_hip": {"x": 0.45 + hip_shift, "y": 0.68},
            "right_hip": {"x": 0.55 + hip_shift, "y": 0.68},
            "left_knee": {"x": left_knee_x, "y": 0.83},
            "right_knee": {"x": right_knee_x, "y": 0.83},
            "left_ankle": {"x": left_ankle_x, "y": 0.96},
            "right_ankle": {"x": right_ankle_x, "y": 0.96},
        },
    }


def _phases(
    repetition_id: str,
    offset_frame: int,
    offset_ts: float,
    *,
    action_evidence: list[dict[str, str]] | None = None,
) -> list[PhaseRecordV2]:
    phase_defs = (
        ("set", 0, 1),
        ("reaction_read", 2, 3),
        ("movement", 4, 6),
        ("collection", 7, 8),
        ("action", 9, 10),
        ("recovery", 10, 11),
    )
    phases: list[PhaseRecordV2] = []
    for idx, (name, start, end) in enumerate(phase_defs, start=1):
        evidence_refs = action_evidence if name == "action" and action_evidence else []
        phases.append(
            PhaseRecordV2(
                phase_id=f"{repetition_id}:phase:{idx}",
                repetition_id=repetition_id,
                phase_name=name,
                start_ts=offset_ts + (start * 0.1),
                end_ts=offset_ts + (end * 0.1),
                start_frame=offset_frame + start,
                end_frame=offset_frame + end,
                detection_method="repetition_relative_heuristic_v1",
                confidence=0.84,
                validity_state=ValidityState.VALID,
                evidence_refs=evidence_refs,
            )
        )
    return phases


def _payload(
    repetitions: list[RepetitionActionRecordV2],
    phases: list[PhaseRecordV2],
) -> dict[str, Any]:
    return {
        "v2": {
            "capture_profile": CaptureProfile(
                camera_view="side",
                sample_fps=10.0,
                source_video_fps=30.0,
                effective_analysis_fps=10.0,
                discipline="wicketkeeping",
                analysis_mode="wicketkeeping",
                metric_version="pose_metrics.v1",
                source_model="MediaPipe Pose Landmarker Full",
            ).model_dump(mode="json"),
            "metric_results": [],
            "repetitions": [rep.model_dump(mode="json") for rep in repetitions],
            "phases": [phase.model_dump(mode="json") for phase in phases],
        },
        "findings": {"findings": []},
        "report": {"summary": "ok"},
        "meta": {},
    }


def _repetitions() -> list[RepetitionActionRecordV2]:
    action_types = (
        "wicketkeeping_standing_back_take",
        "wicketkeeping_standing_up_take",
        "wicketkeeping_leg_side_take",
        "wicketkeeping_stumping_attempt",
    )
    reps: list[RepetitionActionRecordV2] = []
    for idx, action_type in enumerate(action_types, start=1):
        reps.append(
            RepetitionActionRecordV2(
                repetition_id=f"rep-{idx}",
                discipline="wicketkeeping",
                action_type=action_type,
                start_ts=(idx - 1) * 1.2,
                end_ts=(idx - 1) * 1.2 + 1.1,
                start_frame=(idx - 1) * 12,
                end_frame=((idx - 1) * 12) + 11,
                segmentation_method="pose_motion_v1",
                segmentation_confidence=0.86,
                validity_state=ValidityState.VALID,
            )
        )
    return reps


def _frames() -> list[dict[str, object]]:
    frames: list[dict[str, object]] = []
    for rep_index in range(4):
        base_frame = rep_index * 12
        base_ts = rep_index * 1.2
        is_leg_side = rep_index == 2
        is_stumping = rep_index == 3
        for local_idx in range(12):
            phase_shift = 0.0
            nose_x = 0.5
            hip_shift = 0.0
            left_wrist_x = 0.46
            right_wrist_x = 0.54
            if 4 <= local_idx <= 6:  # movement
                phase_shift = 0.05 if is_leg_side else 0.02
                nose_x = 0.5 + phase_shift * (local_idx - 3)
            elif 7 <= local_idx <= 8:  # collection
                hip_shift = 0.01 if local_idx == 8 else 0.0
            elif 9 <= local_idx <= 10 and is_stumping:
                left_wrist_x = 0.48
                right_wrist_x = 0.52
            frames.append(
                _frame(
                    base_frame + local_idx,
                    base_ts + (local_idx * 0.1),
                    nose_x=nose_x,
                    left_wrist_x=left_wrist_x,
                    right_wrist_x=right_wrist_x,
                    hip_shift=hip_shift,
                )
            )
    return frames


def _build_payload(*, include_stump_evidence: bool) -> dict[str, Any]:
    repetitions = _repetitions()
    phases: list[PhaseRecordV2] = []
    for idx, repetition in enumerate(repetitions):
        evidence = None
        if repetition.action_type == "wicketkeeping_stumping_attempt" and include_stump_evidence:
            evidence = [{"ref_type": "object_tracking", "label": "stumps_center"}]
        phases.extend(
            _phases(repetition.repetition_id, idx * 12, idx * 1.2, action_evidence=evidence)
        )
    return _payload(repetitions, phases)


def test_attach_wicketkeeping_v2_metric_pack_generates_phase_and_context_metrics() -> None:
    payload = _build_payload(include_stump_evidence=True)

    updated = attach_wicketkeeping_v2_metric_pack(
        results_payload=payload,
        discipline="wicketkeeping",
        frames=_frames(),
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    metrics = updated["v2"]["metric_results"]
    assert len(metrics) == 9
    assert all(item["metric_id"].startswith("wicketkeeping_") for item in metrics)
    assert updated["meta"]["wicketkeeping_v2_metric_pack"]["metrics_count"] == 9
    assert "wicketkeeping_v2" in updated["findings"]
    assert "wicketkeeping_v2" in updated["report"]
    standing_metric = next(
        item
        for item in metrics
        if item["metric_id"] == "wicketkeeping_context_standing_set_depth_delta_ratio"
    )
    assert standing_metric["validity_state"] in {
        ValidityState.VALID.value,
        ValidityState.LOW_CONFIDENCE.value,
    }


def test_attach_wicketkeeping_v2_metric_pack_stumping_confidence_improves_with_object_evidence() -> (
    None
):
    without_evidence = attach_wicketkeeping_v2_metric_pack(
        results_payload=_build_payload(include_stump_evidence=False),
        discipline="wicketkeeping",
        frames=_frames(),
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )
    with_evidence = attach_wicketkeeping_v2_metric_pack(
        results_payload=_build_payload(include_stump_evidence=True),
        discipline="wicketkeeping",
        frames=_frames(),
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    without_metric = next(
        item
        for item in without_evidence["v2"]["metric_results"]
        if item["metric_id"] == "wicketkeeping_stumping_action_wrist_compactness_ratio"
    )
    with_metric = next(
        item
        for item in with_evidence["v2"]["metric_results"]
        if item["metric_id"] == "wicketkeeping_stumping_action_wrist_compactness_ratio"
    )
    assert without_metric["confidence_score"] < with_metric["confidence_score"]


def test_attach_wicketkeeping_v2_metric_pack_flags_unsupported_camera() -> None:
    updated = attach_wicketkeeping_v2_metric_pack(
        results_payload=_build_payload(include_stump_evidence=True),
        discipline="wicketkeeping",
        frames=_frames(),
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="overhead",
        source_model="MediaPipe Pose Landmarker Full",
    )

    assert all(
        item["validity_state"] == ValidityState.UNSUPPORTED_CAMERA_VIEW.value
        for item in updated["v2"]["metric_results"]
    )


def test_attach_wicketkeeping_v2_metric_pack_flags_insufficient_frame_rate() -> None:
    updated = attach_wicketkeeping_v2_metric_pack(
        results_payload=_build_payload(include_stump_evidence=True),
        discipline="wicketkeeping",
        frames=_frames(),
        sample_fps=4.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    assert all(
        item["validity_state"] == ValidityState.INSUFFICIENT_FRAME_RATE.value
        for item in updated["v2"]["metric_results"]
    )


def test_attach_wicketkeeping_v2_metric_pack_flags_invalid_physical_range() -> None:
    payload = _build_payload(include_stump_evidence=True)
    frames = _frames()
    set_frames = {0, 1, 12, 13, 24, 25, 36, 37}
    for frame in frames:
        frame_num = frame.get("frame_num")
        if not isinstance(frame_num, int) or frame_num not in set_frames:
            continue
        keypoints = frame["keypoints"]
        assert isinstance(keypoints, dict)
        keypoints["left_ankle"] = {"x": -0.2, "y": 0.96}
        keypoints["right_ankle"] = {"x": 1.2, "y": 0.96}

    updated = attach_wicketkeeping_v2_metric_pack(
        results_payload=payload,
        discipline="wicketkeeping",
        frames=frames,
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    stance_metric = next(
        item
        for item in updated["v2"]["metric_results"]
        if item["metric_id"] == "wicketkeeping_set_stance_width_ratio"
    )
    assert stance_metric["validity_state"] == ValidityState.INVALID_RANGE.value


def test_attach_wicketkeeping_v2_metric_pack_handles_missing_phase_data_safely() -> None:
    payload = _build_payload(include_stump_evidence=False)
    payload["v2"]["phases"] = []

    updated = attach_wicketkeeping_v2_metric_pack(
        results_payload=payload,
        discipline="wicketkeeping",
        frames=_frames(),
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    assert all(
        item["validity_state"] == ValidityState.MISSING_PHASE.value
        for item in updated["v2"]["metric_results"]
    )


def test_attach_wicketkeeping_v2_metric_pack_requires_object_evidence_for_stumping_metric() -> None:
    updated = attach_wicketkeeping_v2_metric_pack(
        results_payload=_build_payload(include_stump_evidence=False),
        discipline="wicketkeeping",
        frames=_frames(),
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    stumping_metric = next(
        item
        for item in updated["v2"]["metric_results"]
        if item["metric_id"] == "wicketkeeping_stumping_action_wrist_compactness_ratio"
    )
    assert stumping_metric["validity_state"] == ValidityState.MISSING_OBJECT_EVIDENCE.value
    assert stumping_metric["raw_value"] is None

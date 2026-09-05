from __future__ import annotations

from typing import Any

from backend.domain.coach_analysis_v2_contract import (
    CaptureProfile,
    PhaseRecordV2,
    RepetitionActionRecordV2,
    ValidityState,
)
from backend.services.fielding_v2_metric_pack import attach_fielding_v2_metric_pack


def _frame(
    frame_num: int,
    timestamp: float,
    *,
    nose: tuple[float, float] = (0.50, 0.20),
    left_shoulder: tuple[float, float] = (0.40, 0.40),
    right_shoulder: tuple[float, float] = (0.60, 0.40),
    left_wrist: tuple[float, float] = (0.45, 0.56),
    right_wrist: tuple[float, float] = (0.55, 0.56),
    left_hip: tuple[float, float] = (0.45, 0.68),
    right_hip: tuple[float, float] = (0.55, 0.68),
    left_knee: tuple[float, float] = (0.43, 0.82),
    right_knee: tuple[float, float] = (0.57, 0.82),
    left_ankle: tuple[float, float] = (0.42, 0.96),
    right_ankle: tuple[float, float] = (0.58, 0.96),
) -> dict[str, object]:
    return {
        "frame_num": frame_num,
        "timestamp": timestamp,
        "detected": True,
        "keypoints": {
            "nose": {"x": nose[0], "y": nose[1]},
            "left_shoulder": {"x": left_shoulder[0], "y": left_shoulder[1]},
            "right_shoulder": {"x": right_shoulder[0], "y": right_shoulder[1]},
            "left_elbow": {"x": 0.44, "y": 0.50},
            "right_elbow": {"x": 0.56, "y": 0.50},
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


def _phases(
    repetition_id: str,
    offset_frame: int,
    offset_ts: float,
    *,
    collection_evidence: list[dict[str, str]] | None = None,
    throw_evidence: list[dict[str, str]] | None = None,
) -> list[PhaseRecordV2]:
    phase_defs = (
        ("ready", 0, 1),
        ("reaction", 2, 3),
        ("approach", 4, 5),
        ("collection", 6, 7),
        ("transfer", 8, 8),
        ("throw_action", 9, 10),
        ("recovery", 10, 11),
    )
    phases: list[PhaseRecordV2] = []
    for idx, (name, start, end) in enumerate(phase_defs, start=1):
        evidence_refs = []
        if name == "collection" and collection_evidence:
            evidence_refs = collection_evidence
        elif name == "throw_action" and throw_evidence:
            evidence_refs = throw_evidence
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
                discipline="fielding",
                analysis_mode="fielding",
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
    action_types = ("fielding_action", "fielding_catch", "fielding_throw")
    reps: list[RepetitionActionRecordV2] = []
    for idx, action_type in enumerate(action_types, start=1):
        reps.append(
            RepetitionActionRecordV2(
                repetition_id=f"rep-{idx}",
                discipline="fielding",
                action_type=action_type,
                start_ts=(idx - 1) * 1.2,
                end_ts=((idx - 1) * 1.2) + 1.1,
                start_frame=(idx - 1) * 12,
                end_frame=((idx - 1) * 12) + 11,
                segmentation_method="pose_motion_v1",
                segmentation_confidence=0.86 if action_type != "fielding_throw" else 0.78,
                validity_state=ValidityState.VALID,
            )
        )
    return reps


def _frames() -> list[dict[str, object]]:
    frames: list[dict[str, object]] = []
    for rep_index in range(3):
        base_frame = rep_index * 12
        base_ts = rep_index * 1.2
        is_catch = rep_index == 1
        is_throw = rep_index == 2
        for local_idx in range(12):
            kwargs: dict[str, object] = {}
            if local_idx in {2, 3}:  # reaction
                kwargs["nose"] = (0.50 + (0.006 if local_idx == 3 else 0.0), 0.20)
            elif local_idx in {4, 5}:  # approach
                kwargs["left_hip"] = (0.46 if local_idx == 5 else 0.45, 0.68)
                kwargs["right_hip"] = (0.56 if local_idx == 5 else 0.55, 0.68)
                kwargs["left_ankle"] = (0.43, 0.96)
                kwargs["right_ankle"] = (0.59, 0.96)
            elif local_idx in {6, 7}:  # collection
                if is_catch:
                    kwargs["left_wrist"] = (0.48, 0.48)
                    kwargs["right_wrist"] = (0.52, 0.48)
                    kwargs["nose"] = (0.50, 0.18)
                else:
                    kwargs["nose"] = (0.50, 0.26)
                    kwargs["left_hip"] = (0.45, 0.82)
                    kwargs["right_hip"] = (0.55, 0.82)
                    kwargs["left_knee"] = (0.40, 0.88)
                    kwargs["right_knee"] = (0.60, 0.88)
                    kwargs["left_ankle"] = (0.44, 0.96)
                    kwargs["right_ankle"] = (0.56, 0.96)
            elif local_idx == 8:  # transfer
                kwargs["left_hip"] = (0.46, 0.74)
                kwargs["right_hip"] = (0.56, 0.74)
                kwargs["left_ankle"] = (0.44, 0.96)
                kwargs["right_ankle"] = (0.56, 0.96)
            elif local_idx in {9, 10}:  # throw action / recovery overlap
                if is_throw:
                    kwargs["left_shoulder"] = (0.40, 0.40)
                    kwargs["right_shoulder"] = (0.58, 0.30)
                    kwargs["left_hip"] = (0.45, 0.70)
                    kwargs["right_hip"] = (0.56, 0.72)
                else:
                    kwargs["left_hip"] = (0.45, 0.70)
                    kwargs["right_hip"] = (0.55, 0.70)
            elif local_idx == 11:  # recovery
                kwargs["left_hip"] = (0.45, 0.68)
                kwargs["right_hip"] = (0.55, 0.68)
                kwargs["left_ankle"] = (0.43, 0.96)
                kwargs["right_ankle"] = (0.57, 0.96)

            frames.append(_frame(base_frame + local_idx, base_ts + (local_idx * 0.1), **kwargs))
    return frames


def _build_payload(*, include_action_evidence: bool) -> dict[str, Any]:
    repetitions = _repetitions()
    phases: list[PhaseRecordV2] = []
    for idx, repetition in enumerate(repetitions):
        collection_evidence = None
        throw_evidence = None
        if repetition.action_type == "fielding_catch" and include_action_evidence:
            collection_evidence = [{"ref_type": "object_tracking", "label": "catch_window"}]
        if repetition.action_type == "fielding_throw" and include_action_evidence:
            throw_evidence = [{"ref_type": "object_tracking", "label": "throw_release_proxy"}]
        phases.extend(
            _phases(
                repetition.repetition_id,
                idx * 12,
                idx * 1.2,
                collection_evidence=collection_evidence,
                throw_evidence=throw_evidence,
            )
        )
    return _payload(repetitions, phases)


def test_attach_fielding_v2_metric_pack_generates_fielding_metrics_and_findings() -> None:
    updated = attach_fielding_v2_metric_pack(
        results_payload=_build_payload(include_action_evidence=True),
        discipline="fielding",
        frames=_frames(),
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    metrics = updated["v2"]["metric_results"]
    assert len(metrics) == 10
    assert all(item["metric_id"].startswith("fielding_") for item in metrics)
    assert updated["meta"]["fielding_v2_metric_pack"]["metrics_count"] == 10
    assert updated["meta"]["fielding_v2_metric_pack"]["subtype_counts"] == {
        "catch": 1,
        "throw": 1,
        "boundary": 0,
        "generic": 1,
    }
    assert "fielding_v2" in updated["findings"]
    assert "fielding_v2" in updated["report"]

    ground_metric = next(
        item
        for item in metrics
        if item["metric_id"] == "fielding_ground_collection_body_drop_ratio"
    )
    assert ground_metric["validity_state"] in {
        ValidityState.VALID.value,
        ValidityState.LOW_CONFIDENCE.value,
    }

    catch_metric = next(
        item
        for item in metrics
        if item["metric_id"] == "fielding_catch_collection_wrist_compactness_ratio"
    )
    throw_metric = next(
        item
        for item in metrics
        if item["metric_id"] == "fielding_throw_action_shoulder_hip_separation_deg"
    )
    assert catch_metric["action_type"] == "fielding_catch"
    assert throw_metric["action_type"] == "fielding_throw"


def test_attach_fielding_v2_metric_pack_confidence_improves_with_phase_evidence() -> None:
    without_evidence = attach_fielding_v2_metric_pack(
        results_payload=_build_payload(include_action_evidence=False),
        discipline="fielding",
        frames=_frames(),
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )
    with_evidence = attach_fielding_v2_metric_pack(
        results_payload=_build_payload(include_action_evidence=True),
        discipline="fielding",
        frames=_frames(),
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    without_metric = next(
        item
        for item in without_evidence["v2"]["metric_results"]
        if item["metric_id"] == "fielding_catch_collection_wrist_compactness_ratio"
    )
    with_metric = next(
        item
        for item in with_evidence["v2"]["metric_results"]
        if item["metric_id"] == "fielding_catch_collection_wrist_compactness_ratio"
    )
    assert without_metric["confidence_score"] < with_metric["confidence_score"]


def test_attach_fielding_v2_metric_pack_flags_unsupported_camera() -> None:
    updated = attach_fielding_v2_metric_pack(
        results_payload=_build_payload(include_action_evidence=True),
        discipline="fielding",
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


def test_attach_fielding_v2_metric_pack_flags_insufficient_frame_rate() -> None:
    updated = attach_fielding_v2_metric_pack(
        results_payload=_build_payload(include_action_evidence=True),
        discipline="fielding",
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


def test_attach_fielding_v2_metric_pack_flags_invalid_physical_range() -> None:
    payload = _build_payload(include_action_evidence=True)
    frames = _frames()
    collection_frames = {6, 7, 30, 31}
    for frame in frames:
        frame_num = frame.get("frame_num")
        if not isinstance(frame_num, int) or frame_num not in collection_frames:
            continue
        keypoints = frame["keypoints"]
        assert isinstance(keypoints, dict)
        keypoints["nose"] = {"x": 1.5, "y": 0.26}

    updated = attach_fielding_v2_metric_pack(
        results_payload=payload,
        discipline="fielding",
        frames=frames,
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    head_base_metric = next(
        item
        for item in updated["v2"]["metric_results"]
        if item["metric_id"] == "fielding_ground_collection_head_base_offset_ratio"
    )
    assert head_base_metric["validity_state"] == ValidityState.INVALID_RANGE.value


def test_attach_fielding_v2_metric_pack_handles_missing_phase_data_safely() -> None:
    payload = _build_payload(include_action_evidence=False)
    payload["v2"]["phases"] = []

    updated = attach_fielding_v2_metric_pack(
        results_payload=payload,
        discipline="fielding",
        frames=_frames(),
        sample_fps=10.0,
        source_video_fps=30.0,
        camera_view="side",
        source_model="MediaPipe Pose Landmarker Full",
    )

    assert all(
        item["validity_state"]
        in {
            ValidityState.NOT_MEASURABLE.value,
            ValidityState.INSUFFICIENT_VISIBILITY.value,
            ValidityState.INSUFFICIENT_REPETITIONS.value,
        }
        for item in updated["v2"]["metric_results"]
    )
